# Copyright (c) 2014, Riverbank Computing Limited
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import os
import shutil
import subprocess
import tempfile

from PyQt5.QtCore import QDir, QFile, QFileInfo, QIODevice

from ..project import QrcDirectory, QrcFile
from ..user_exception import UserException
from ..version import PYQTDEPLOY_HEXVERSION


class Builder():
    """ The builder for a project. """

    # Map PyQt modules to the corresponding qmake QT or CONFIG values.  A
    # module that doesn't need any of these values can be omitted
    class _QtMetaData:
        def __init__(self, qt=None, config=None):
            self.qt = qt
            self.config = config

    _pyqt5_module_map = {
        'QAxContainer':         _QtMetaData(qt=['axcontainer']),
        'QtBluetooth':          _QtMetaData(qt=['bluetooth']),
        'QtCore':               _QtMetaData(qt=['-gui']),
        'QtDBus':               _QtMetaData(qt=['dbus', '-gui']),
        'QtDesigner':           _QtMetaData(qt=['designer']),
        'QtHelp':               _QtMetaData(qt=['help']),
        'QtMacExtras':          _QtMetaData(qt=['macextras']),
        'QtMultimedia':         _QtMetaData(qt=['multimedia']),
        'QtMultimediaWidgets':  _QtMetaData(
                                        qt=['multimediawidgets',
                                                'multimedia']),
        'QtNetwork':            _QtMetaData(qt=['network', '-gui']),
        'QtOpenGL':             _QtMetaData(qt=['opengl']),
        'QtPositioning':        _QtMetaData(qt=['positioning']),
        'QtPrintSupport':       _QtMetaData(qt=['printsupport']),
        'QtQml':                _QtMetaData(qt=['qml']),
        'QtQuick':              _QtMetaData(qt=['quick']),
        'QtSensors':            _QtMetaData(qt=['sensors']),
        'QtSerialPort':         _QtMetaData(qt=['serialport']),
        'QtSql':                _QtMetaData(qt=['sql', 'widgets']),
        'QtSvg':                _QtMetaData(qt=['svg']),
        'QtTest':               _QtMetaData(qt=['testlib', 'widgets']),
        'QtWebKit':             _QtMetaData(qt=['webkit', 'network']),
        'QtWebKitWidgets':      _QtMetaData(qt=['webkitwidgets']),
        'QtWidgets':            _QtMetaData(qt=['widgets']),
        'QtWinExtras':          _QtMetaData(qt=['winextras', 'widgets']),
        'QtX11Extras':          _QtMetaData(qt=['x11extras']),
        'QtXmlPatterns':        _QtMetaData(
                                        qt=['xmlpatterns', '-gui', 'network']),

        'QtChart':              _QtMetaData(config=['qtcommercialchart']),
        'QtDataVisualization':  _QtMetaData(qt=['datavisualization']),
        'Qsci':                 _QtMetaData(config=['qscintilla2']),
    }

    _pyqt4_module_map = {
        'QAxContainer':         _QtMetaData(config=['qaxcontainer']),
        'QtCore':               _QtMetaData(qt=['-gui']),
        'QtDBus':               _QtMetaData(qt=['dbus', '-gui']),
        'QtDeclarative':        _QtMetaData(qt=['declarative', 'network']),
        'QtDesigner':           _QtMetaData(config=['designer']),
        'QtHelp':               _QtMetaData(config=['help']),
        'QtMultimedia':         _QtMetaData(qt=['multimedia']),
        'QtNetwork':            _QtMetaData(qt=['network', '-gui']),
        'QtOpenGL':             _QtMetaData(qt=['opengl']),
        'QtScript':             _QtMetaData(qt=['script', '-gui']),
        'QtScriptTools':        _QtMetaData(qt=['scripttools', 'script']),
        'QtSql':                _QtMetaData(qt=['sql']),
        'QtSvg':                _QtMetaData(qt=['svg']),
        'QtTest':               _QtMetaData(qt=['testlib']),
        'QtWebKit':             _QtMetaData(qt=['webkit', 'network']),
        'QtXml':                _QtMetaData(qt=['xml', '-gui']),
        'QtXmlPatterns':        _QtMetaData(
                                        qt=['xmlpatterns', '-gui', 'network']),
        'phonon':               _QtMetaData(qt=['phonon']),

        'QtChart':              _QtMetaData(config=['qtcommercialchart']),
        'Qsci':                 _QtMetaData(config=['qscintilla2']),
    }

    def __init__(self, project, verbose=False):
        """ Initialise the builder for a project. """

        super().__init__()

        self._project = project
        self._verbose = verbose

    def build(self, build_dir):
        """ Build the project in a given directory.  Raise a UserException if
        there is an error.
        """

        project = self._project

        self._create_directory(build_dir)

        freeze = self._copy_lib_file('freeze.py')

        self._write_qmake(build_dir, freeze)

        resources_dir = os.path.join(build_dir, 'resources')
        self._create_directory(resources_dir)

        for resource in self.resources():
            if resource == '':
                package = project.application_package
                self._write_resource(resources_dir, resource, package, 
                        project.absolute_path(package.name), freeze)
            elif resource == 'stdlib':
                self._write_resource(resources_dir, resource,
                        project.stdlib_package,
                        os.path.join(project.python_target_stdlib_dir, ''),
                        freeze)
            else:
                # Add the PyQt package to a temporary copy of the site-packages
                # package.
                site_packages_package = project.site_packages_package.copy()
                pyqt_dir = 'PyQt5' if project.application_is_pyqt5 else 'PyQt4'

                if len(project.pyqt_modules) != 0:
                    pyqt_pkg_init = QrcFile('__init__.py')
                    pyqt_pkg_dir = QrcDirectory(pyqt_dir)
                    pyqt_pkg_dir.contents.append(pyqt_pkg_init)
                    site_packages_package.contents.append(pyqt_pkg_dir)

                    # Add uic if requested.
                    if 'uic' in project.pyqt_modules:
                        self._add_uic_dir(pyqt_pkg_dir,
                                os.path.join(
                                        self._project.python_target_stdlib_dir,
                                        'site-packages', pyqt_dir),
                                'uic', [])

                self._write_resource(resources_dir, resource,
                        site_packages_package,
                        os.path.join(project.python_target_stdlib_dir,
                                'site-packages', ''),
                        freeze)

        os.remove(freeze)

    def _add_uic_dir(self, package, pyqt_dir, dirname, dir_stack):
        """ Add a uic directory to a package. """

        dir_pkg = QrcDirectory(dirname)
        package.contents.append(dir_pkg)

        dirpath = [pyqt_dir] + dir_stack + [dirname]
        dirpath = os.path.join(*dirpath)

        for content in os.listdir(dirpath):
            if content in ('port_v2', '__pycache__'):
                continue

            content_path = os.path.join(dirpath, content)

            if os.path.isfile(content_path):
                dir_pkg.contents.append(QrcFile(content))
            elif os.path.isdir(content_path):
                dir_stack.append(dirname)
                self._add_uic_dir(dir_pkg, pyqt_dir, content, dir_stack)
                dir_stack.pop()

    def _write_qmake(self, build_dir, freeze):
        """ Create the .pro file for qmake. """

        project = self._project

        app_name = os.path.basename(project.application_script)
        app_name, _ = os.path.splitext(app_name)

        f = self._create_file(build_dir, app_name + '.pro')

        f.write('TEMPLATE = app\n')
        f.write('CONFIG += release warn_on\n')

        # Configure the QT value.
        f.write('\n')

        no_gui = True
        qmake_qt = []
        qmake_config = []

        module_map = self._pyqt5_module_map if project.application_is_pyqt5 else self._pyqt4_module_map

        for pyqt_m in project.pyqt_modules:
            needs_gui = True

            metadata = module_map.get(pyqt_m, self._QtMetaData())

            if metadata.qt is not None:
                for qt in metadata.qt:
                    if qt == '-gui':
                        needs_gui = False
                    elif qt not in qmake_qt:
                        qmake_qt.append(qt)

            if metadata.config is not None:
                for config in metadata.config:
                    if config not in qmake_config:
                        qmake_config.append(config)

            if needs_gui:
                no_gui = False

        if no_gui:
            f.write('QT -= gui\n')

        if len(qmake_qt) != 0:
            f.write('QT += {0}\n'.format(' '.join(qmake_qt)))

        if len(qmake_config) != 0:
            f.write('CONFIG += {0}\n'.format(' '.join(qmake_config)))

        # Determine the extension modules and link against them.
        extensions = {}

        for extension_module in project.extension_modules:
            if extension_module.name != '':
                extensions[extension_module.name] = extension_module.path

        if len(project.pyqt_modules) > 0:
            sitepackages = project.absolute_path(
                    project.python_target_stdlib_dir) + '/site-packages'
            pyqt_version = 'PyQt5' if project.application_is_pyqt5 else 'PyQt4'

            for pyqt in project.pyqt_modules:
                if pyqt != 'uic':
                    extensions[pyqt_version + '.' + pyqt] = sitepackages + '/' + pyqt_version

            # Add the implicit sip module.
            extensions['sip'] = sitepackages

        if len(extensions) > 0:
            f.write('\n')

            # Get the list of unique module directories.
            mod_dirs = []
            for mod_dir in extensions.values():
                if mod_dir not in mod_dirs:
                    mod_dirs.append(mod_dir)

            mod_dir_flags = ['-L' + md for md in mod_dirs]
            mod_flags = ['-l' + m.split('.')[-1] for m in extensions.keys()]

            f.write(
                    'LIBS += {0} {1}\n'.format(' '.join(mod_dir_flags),
                            ' '.join(mod_flags)))

        # Configure the target Python interpreter.
        f.write('\n')

        if project.python_target_include_dir != '':
            f.write(
                    'INCLUDEPATH += {0}\n'.format(
                            project.python_target_include_dir))

        if project.python_target_library != '':
            lib_dir = os.path.dirname(project.python_target_library)
            lib, _ = os.path.splitext(
                    os.path.basename(project.python_target_library))

            if lib.startswith('lib'):
                lib = lib[3:]

            f.write('LIBS += -L{0} -l{1}\n'.format(lib_dir, lib))

        # Add the platform specific stuff.
        platforms_f = QFile(self._lib_filename('platforms.pro'))

        if not platforms_f.open(QIODevice.ReadOnly|QIODevice.Text):
            raise UserException(
                    "Unable to open file {0}.".format(platforms_f.fileName()),
                    platforms_f.errorString())

        platforms = platforms_f.readAll()
        platforms_f.close()

        f.write('\n')
        f.write(platforms.data().decode('latin1'))

        # Specify any resource files.
        resources = self.resources()

        if len(resources) != 0:
            f.write('\n')

            f.write('RESOURCES =')

            for resource in resources:
                if resource == '':
                    resource = 'pyqtdeploy'

                f.write(' \\\n    resources/{0}.qrc'.format(resource))

            f.write('\n')

        # Specify the source and header files.
        f.write('\n')

        f.write('SOURCES = main.c pyqtdeploy_main.c pyqtdeploy_module.cpp\n')
        self._write_main_c(build_dir, app_name, extensions.keys())
        self._copy_lib_file('pyqtdeploy_main.c', build_dir)
        self._copy_lib_file('pyqtdeploy_module.cpp', build_dir)

        f.write('HEADERS = frozen_bootstrap.h frozen_main.h pyqtdeploy_version.h\n')

        bootstrap_f = self._create_file(build_dir, '__bootstrap__.py')
        bootstrap_f.write('''import sys
import pyqtdeploy

sys.path = [{0}]
sys.path_hooks = [pyqtdeploy.qrcimporter]
'''.format(', '.join(["':/{0}'".format(resource) for resource in resources])))
        bootstrap_f.close()

        self._freeze(os.path.join(build_dir, 'frozen_bootstrap.h'),
                os.path.join(build_dir, '__bootstrap__.py'), freeze)

        self._freeze(os.path.join(build_dir, 'frozen_main.h'),
                project.absolute_path(project.application_script), freeze,
                main=True)

        version_f = self._create_file(build_dir, 'pyqtdeploy_version.h')
        version_f.write(
                '#define PYQTDEPLOY_HEXVERSION %s\n' % hex(
                        PYQTDEPLOY_HEXVERSION))
        version_f.close()

        # All done.
        f.close()

    def resources(self):
        """ Return the list of resources needed. """

        project = self._project

        resources = []

        for content in project.application_package.contents:
            if content.included:
                resources.append('')
                break

        resources.append('stdlib')

        if len(project.pyqt_modules) != 0:
            resources.append('site-packages')
        else:
            for content in project.site_packages_package.contents:
                if content.included:
                    resources.append('site-packages')
                    break

        return resources

    def _write_resource(self, resources_dir, resource, package, src, freeze):
        """ Create a .qrc file for a resource and the corresponding contents.
        """

        # The main application resource does not go in a sub-directory.
        if resource == '':
            qrc_file = 'pyqtdeploy.qrc'
            dst_root_dir = resources_dir
        else:
            qrc_file = resource + '.qrc'
            dst_root_dir = os.path.join(resources_dir, resource)
            self._create_directory(dst_root_dir)

        f = self._create_file(resources_dir, qrc_file)

        f.write('''<!DOCTYPE RCC>
<RCC version="1.0">
    <qresource>
''')

        src_root_dir, src_root = os.path.split(src)

        self._write_package_contents(package.contents, dst_root_dir,
                src_root_dir, [src_root], freeze, f)

        f.write('''    </qresource>
</RCC>
''')

        f.close()

    def _write_package_contents(self, contents, dst_root_dir, src_root_dir, dir_stack, freeze, f):
        """ Write the contents of a single package directory. """

        dir_tail = os.path.join(*dir_stack)

        if dir_tail == '':
            dir_stack = []
            dst_dir = dst_root_dir
        else:
            if dir_tail == '.':
                dir_stack = []

            dst_dir = os.path.join(dst_root_dir, dir_tail)
            self._create_directory(dst_dir)

        prefix = os.path.basename(dst_root_dir)
        if prefix != 'resources':
            prefix = [prefix]
        else:
            prefix = []

        for content in contents:
            if not content.included:
                continue

            if isinstance(content, QrcDirectory):
                dir_stack.append(content.name)
                self._write_package_contents(content.contents, dst_root_dir,
                        src_root_dir, dir_stack, freeze, f)
                dir_stack.pop()
            else:
                freeze_file = True
                src_file = content.name
                src_path = os.path.join(src_root_dir, dir_tail, src_file)

                if src_file.endswith('.py'):
                    dst_file = src_file[:-3] + '.pyf'
                elif src_file.endswith('.pyw'):
                    dst_file = src_file[:-4] + '.pyf'
                else:
                    # Just copy the file.
                    dst_file = src_file
                    freeze_file = False

                dst_path = os.path.join(dst_dir, dst_file)

                file_path = list(prefix)

                if dir_tail != '':
                    file_path.extend(dir_stack)

                file_path.append(dst_file)

                f.write(
                        '        <file>{0}</file>\n'.format(
                                '/'.join(file_path)))

                if freeze_file:
                    self._freeze(dst_path, src_path, freeze, as_data=True)
                else:
                    shutil.copyfile(src_path, dst_path)

    @classmethod
    def _write_main_c(cls, build_dir, app_name, extension_names):
        """ Create the application specific main.c file. """

        f = cls._create_file(build_dir, 'main.c')

        f.write('''#include <wchar.h>
#include <Python.h>

int main(int argc, char **argv)
{
''')

        if len(extension_names) > 0:
            inittab = 'extension_modules'

            f.write('#if PY_MAJOR_VERSION >= 3\n')
            cls._write_inittab(f, extension_names, inittab, py3=True)
            f.write('#else\n')
            cls._write_inittab(f, extension_names, inittab, py3=False)
            f.write('#endif\n\n')
        else:
            inittab = 'NULL'

        f.write('#if PY_MAJOR_VERSION >= 3\n')
        cls._write_main_call(f, app_name, inittab, py3=True)
        f.write('#else\n')
        cls._write_main_call(f, app_name, inittab, py3=False)
        f.write('#endif\n}\n')

        f.close()

    @staticmethod
    def _write_inittab(f, extension_names, inittab, py3):
        """ Write the Python version specific extension module inittab. """

        if py3:
            init_type = 'PyObject *'
            init_prefix = 'PyInit_'
        else:
            init_type = 'void '
            init_prefix = 'init'

        for ext in extension_names:
            base_ext = ext.split('.')[-1]

            f.write('    extern %s%s%s(void);\n' % (init_type, init_prefix,
                    base_ext))

        f.write('''
    static struct _inittab %s[] = {
''' % inittab)

        for ext in extension_names:
            base_ext = ext.split('.')[-1]

            f.write('        {"%s", %s%s},\n' % (ext, init_prefix, base_ext))

        f.write('''        {NULL, NULL}
    };
''')

    @staticmethod
    def _write_main_call(f, app_name, inittab, py3):
        """ Write the Python version specific call to pyqtdeploy_main(). """

        if py3:
            name_type = 'wchar_t'
            name_prefix = 'L'
        else:
            name_type = 'char'
            name_prefix = ''

        f.write('''    extern int pyqtdeploy_main(int argc, char **argv, %s *py_main,
            struct _inittab *extension_modules);

    return pyqtdeploy_main(argc, argv, %s"%s", %s);
''' % (name_type, name_prefix, app_name, inittab))

    def _freeze(self, output, py_filename, freeze, main=False, as_data=False):
        """ Freeze a Python source file to a C header file or a data file. """

        args = [self._project.python_host_interpreter, freeze]
        
        if main:
            args.append('--main')

        args.append('--as-data' if as_data else '--as-c')
        args.append(output)
        args.append(py_filename)

        self._log("Running '{0}'".format(' '.join(args)))

        try:
            subprocess.check_output(args, stderr=subprocess.STDOUT,
                    universal_newlines=True)
        except subprocess.CalledProcessError as e:
            self._log(e.output)
            raise UserException("Unable to freeze {0}.".format(py_filename),
                    e.output)

    @staticmethod
    def _lib_filename(filename):
        """ Get name of a file in the 'lib' directory that can be used by
        QFile.
        """

        lib_dir = QFileInfo(__file__).dir()
        lib_dir.cd('lib')

        return lib_dir.filePath(filename)

    @classmethod
    def _copy_lib_file(cls, filename, dirname=None):
        """ Copy a library file to a directory and return the full pathname of
        the copy.  If the directory wasn't specified then copy it to a
        temporary directory.
        """

        # Note that we use the Qt file operations to support the possibility
        # that pyqtdeploy itself has been deployed as a single executable.

        # The destination filename.
        if dirname is None:
            dirname = tempfile.gettempdir()

        d_filename = os.path.join(dirname, filename)

        # The source filename.
        s_filename = cls._lib_filename(filename)

        # Make sure the destination doesn't exist.
        QFile.remove(d_filename)

        if not QFile.copy(s_filename, QDir.fromNativeSeparators(d_filename)):
            raise UserException("Unable to copy file {0}.".format(filename))

        return d_filename

    @staticmethod
    def _create_file(build_dir, filename):
        """ Create a text file in the build directory. """

        pathname = os.path.join(build_dir, filename)

        try:
            return open(pathname, 'wt')
        except Exception as e:
            raise UserException("Unable to create file {0}.".format(pathname),
                    str(e))

    @staticmethod
    def _create_directory(dir_name):
        """ Create a directory which may already exist. """

        try:
            os.makedirs(dir_name, exist_ok=True)
        except Exception as e:
            raise UserException(
                    "Unable to create the '{0}' directory.".format(dir_name),
                    str(e))

    def _log(self, message):
        """ Log a message if requested. """

        if self._verbose:
            print(message)
