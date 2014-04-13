// Copyright (c) 2014, Riverbank Computing Limited
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
// 
// 1. Redistributions of source code must retain the above copyright notice,
//    this list of conditions and the following disclaimer.
// 
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.


#include <Python.h>
#include <marshal.h>
#include <structmember.h>

#include <QByteArray>
#include <QChar>
#include <QFileInfo>
#include <QString>
#include <QStringList>
#include <QVector>

#include "pyqtdeploy_version.h"


#if QT_VERSION < 0x040200
#error "Qt v4.2.0 or later is required"
#endif


extern "C" {

#if PY_MAJOR_VERSION >= 3
#if PY_MINOR_VERSION < 3
#error "Python v3.3 or later is required"
#endif

#define PYQTDEPLOY_INIT                 PyInit_pyqtdeploy
#define PYQTDEPLOY_TYPE                 PyObject *
#define PYQTDEPLOY_MODULE_DISCARD(m)    Py_DECREF(m)
#define PYQTDEPLOY_FATAL(s)             return NULL
#define PYQTDEPLOY_RETURN(m)            return (m)
#define PYQTDEPLOY_PARSE_STR            "U"

// The module definition structure.
static struct PyModuleDef pyqtdeploymodule = {
    PyModuleDef_HEAD_INIT,
    "pyqtdeploy",
    NULL,
    -1,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
};
#else
#if PY_MINOR_VERSION < 6
#error "Python v2.6 or later is required"
#endif

#define PYQTDEPLOY_INIT                 initpyqtdeploy
#define PYQTDEPLOY_TYPE                 void
#define PYQTDEPLOY_MODULE_DISCARD(m)
#define PYQTDEPLOY_FATAL(s)             Py_FatalError(s)
#define PYQTDEPLOY_RETURN(m)
#define PYQTDEPLOY_PARSE_STR            "S"
#endif


// The importer object structure.
typedef struct _qrcimporter
{
    PyObject_HEAD

    // The path that the importer handles.  It will be the name of a directory.
    QString *path;
} QrcImporter;


// C linkage forward declarations.
static int qrcimporter_init(PyObject *self, PyObject *args, PyObject *kwds);
static void qrcimporter_dealloc(PyObject *self);
#if PY_MAJOR_VERSION >= 3
static PyObject *qrcimporter_find_loader(PyObject *self, PyObject *args);
#else
static PyObject *qrcimporter_find_module(PyObject *self, PyObject *args);
#endif
static PyObject *qrcimporter_load_module(PyObject *self, PyObject *args);
PYQTDEPLOY_TYPE PYQTDEPLOY_INIT();


// The method table.
static PyMethodDef qrcimporter_methods[] = {
#if PY_MAJOR_VERSION >= 3
    {"find_loader", qrcimporter_find_loader, METH_VARARGS, NULL},
#else
    {"find_module", qrcimporter_find_module, METH_VARARGS, NULL},
#endif
    {"load_module", qrcimporter_load_module, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};


// The importer type structure.
static PyTypeObject QrcImporter_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pyqtdeploy.qrcimporter",
    sizeof (QrcImporter),
    0,                                          // tp_itemsize
    qrcimporter_dealloc,                        // tp_dealloc
    0,                                          // tp_print
    0,                                          // tp_getattr
    0,                                          // tp_setattr
    0,                                          // tp_reserved
    0,                                          // tp_repr
    0,                                          // tp_as_number
    0,                                          // tp_as_sequence
    0,                                          // tp_as_mapping
    0,                                          // tp_hash
    0,                                          // tp_call
    0,                                          // tp_str
    0,                                          // tp_getattro
    0,                                          // tp_setattro
    0,                                          // tp_as_buffer
    Py_TPFLAGS_DEFAULT,                         // tp_flags
    0,                                          // tp_doc
    0,                                          // tp_traverse
    0,                                          // tp_clear
    0,                                          // tp_richcompare
    0,                                          // tp_weaklistoffset
    0,                                          // tp_iter
    0,                                          // tp_iternext
    qrcimporter_methods,                        // tp_methods
    0,                                          // tp_members
    0,                                          // tp_getset
    0,                                          // tp_base
    0,                                          // tp_dict
    0,                                          // tp_descr_get
    0,                                          // tp_descr_set
    0,                                          // tp_dictoffset
    qrcimporter_init,                           // tp_init
    0,                                          // tp_alloc
    0,                                          // tp_new
    0,                                          // tp_free
    0,                                          // tp_is_gc
    0,                                          // tp_bases
    0,                                          // tp_mro
    0,                                          // tp_cache
    0,                                          // tp_subclasses
    0,                                          // tp_weaklist
    0,                                          // tp_del
    0,                                          // tp_version_tag
#if PY_VERSION_HEX >= 0x03040000
    0,                                          // tp_finalize
#endif
};

}


// The different results that can be returned by find_module().
enum ModuleType {
    ModuleNotFound,
    ModuleIsModule,
    ModuleIsPackage,
    ModuleIsNamespace
};


// Other forward declarations.
static ModuleType find_module(QrcImporter *self, const QString &fqmn,
        QString &pathname, QString &filename);
static QString str_to_qstring(PyObject *str);
static PyObject *qstring_to_str(const QString &qstring);


// The importer initialisation function.
static int qrcimporter_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *path;

    // It's not clear if this is part of the public API.
    if (!_PyArg_NoKeywords("qrcimporter()", kwds))
        return -1;

#if PY_MAJOR_VERSION >= 3
    if (!PyArg_ParseTuple(args, "O&:qrcimporter", PyUnicode_FSDecoder, &path))
        return -1;
#else
    if (!PyArg_ParseTuple(args, PYQTDEPLOY_PARSE_STR ":qrcimporter", &path))
        return -1;
#endif

    QString *q_path = new QString(str_to_qstring(path));

    if (!QFileInfo(*q_path).isDir())
    {
        delete q_path;

        PyErr_SetString(PyExc_ImportError, "qrcimporter: not a qrc file");
        return -1;
    }

    if (!q_path->endsWith(QChar('/')))
        q_path->append(QChar('/'));

    ((QrcImporter *)self)->path = q_path;

    return 0;
}


// The importer deallocation function.
static void qrcimporter_dealloc(PyObject *self)
{
    if (((QrcImporter *)self)->path)
    {
        delete ((QrcImporter *)self)->path;
        ((QrcImporter *)self)->path = 0;
    }

    Py_TYPE(self)->tp_free(self);
}


#if PY_MAJOR_VERSION >= 3
// Implement the standard find_loader() method for the importer.
static PyObject *qrcimporter_find_loader(PyObject *self, PyObject *args)
{
    PyObject *py_fqmn;

    if (!PyArg_ParseTuple(args, PYQTDEPLOY_PARSE_STR ":qrcimporter.find_loader", &py_fqmn))
        return NULL;

    QString fqmn = str_to_qstring(py_fqmn);
    QString pathname, filename;
    PyObject *result;

    switch (find_module((QrcImporter *)self, fqmn, pathname, filename))
    {
    case ModuleIsModule:
    case ModuleIsPackage:
        result = Py_BuildValue("O[]", self);
        break;

    case ModuleIsNamespace:
        {
            PyObject *py_pathname = qstring_to_str(pathname);
            if (!py_pathname)
                return NULL;

            result = Py_BuildValue("O[N]", Py_None, py_pathname);
            break;
        }

    case ModuleNotFound:
        {
            static bool recursing = false;

            // If we have failed to find a sub-package then it may be because
            // it is a builtin so start a high-level search for it while
            // watching for recursing back here.
            if (fqmn.contains(QChar('.')) && !recursing)
            {
                static PyObject *find_loader = 0;

                if (!find_loader)
                {
                    PyObject *importlib = PyImport_ImportModule("importlib");

                    if (!importlib)
                        return NULL;

                    find_loader = PyObject_GetAttrString(importlib,
                            "find_loader");

                    Py_DECREF(importlib);

                    if (!find_loader)
                        return NULL;
                }

                recursing = true;
                PyObject *loader = PyObject_CallObject(find_loader, args);
                recursing = false;

                if (!loader)
                    return NULL;

                result = Py_BuildValue("N[]", loader);
            }
            else
            {
                result = Py_BuildValue("O[]", Py_None);
            }
        }

        break;
    }

    return result;
}
#endif


#if PY_MAJOR_VERSION < 3
// Implement the standard find_module() method for the importer.
static PyObject *qrcimporter_find_module(PyObject *self, PyObject *args)
{
    PyObject *py_fqmn, *path;

    if (!PyArg_ParseTuple(args, PYQTDEPLOY_PARSE_STR "|O:qrcimporter.find_module", &py_fqmn, &path))
        return NULL;

    QString fqmn = str_to_qstring(py_fqmn);
    QString pathname, filename;
    PyObject *result;

    if (find_module((QrcImporter *)self, fqmn, pathname, filename) == ModuleNotFound)
    {
        result = Py_None;

        // If we have failed to find a sub-package then it may be because it is
        // a builtin.
        if (fqmn.contains(QChar('.')))
            for (struct _inittab *p = PyImport_Inittab; p->name; ++p)
                if (fqmn == p->name)
                {
                    result = self;
                    break;
                }
    }
    else
    {
        result = self;
    }

    Py_INCREF(result);
    return result;
}
#endif


// Implement the standard load_module() method for the importer.
static PyObject *qrcimporter_load_module(PyObject *self, PyObject *args)
{
    PyObject *py_fqmn, *code, *py_filename, *mod_dict;

    if (!PyArg_ParseTuple(args, PYQTDEPLOY_PARSE_STR ":qrcimporter.load_module", &py_fqmn))
        return NULL;

    QString fqmn = str_to_qstring(py_fqmn);
    QString pathname, filename;

    ModuleType mt = find_module((QrcImporter *)self, fqmn, pathname, filename);

#if PY_MAJOR_VERSION < 3
    if (mt == ModuleNotFound)
    {
        // We use the imp module to load sub-packages that are statically
        // linked extension modules.
        static PyObject *init_builtin = 0;

        if (!init_builtin)
        {
            PyObject *imp_module = PyImport_ImportModule("imp");
            if (!imp_module)
                return NULL;

            init_builtin = PyObject_GetAttrString(imp_module, "init_builtin");
            Py_DECREF(imp_module);

            if (!init_builtin)
                return NULL;
        }

        return PyObject_CallObject(init_builtin, args);
    }
#endif

    if (mt != ModuleIsModule && mt != ModuleIsPackage)
    {
        PyErr_Format(PyExc_ImportError, "qrcimporter: can't find module %s",
                fqmn.toLatin1().constData());
        return NULL;
    }

    // Read in the code object from the file.
    QFile mfile(filename);

    if (!mfile.open(QIODevice::ReadOnly))
    {
        PyErr_Format(PyExc_ImportError,
                "qrcimporter: error opening file for module %s",
                        fqmn.toLatin1().constData());
        return NULL;
    }

    QByteArray data = mfile.readAll();

    mfile.close();

    code = PyMarshal_ReadObjectFromString(data.data(), data.size());
    if (!code)
        return NULL;

    // Get the module object and its dict.
#if PY_MAJOR_VERSION >= 3
    PyObject *mod = PyImport_AddModuleObject(py_fqmn);
#else
    PyObject *mod = PyImport_AddModule(PyString_AS_STRING(py_fqmn));
#endif
    if (!mod)
        goto error;

    mod_dict = PyModule_GetDict(mod);

    // Set the loader object.
    if (PyDict_SetItemString(mod_dict, "__loader__", self) != 0)
        goto error;

    if (mt == ModuleIsPackage)
    {
        // Add __path__ to the module before the code gets executed.

        PyObject *py_pathname = qstring_to_str(pathname);
        if (!py_pathname)
            goto error;

        PyObject *path_list = Py_BuildValue("[N]", py_pathname);
        if (!path_list)
            goto error;

        int rc = PyDict_SetItemString(mod_dict, "__path__", path_list);
        Py_DECREF(path_list);

        if (rc != 0)
            goto error;
    }

    py_filename = qstring_to_str(filename);
    if (!py_filename)
        goto error;

#if PY_MAJOR_VERSION >= 3
    mod = PyImport_ExecCodeModuleObject(py_fqmn, code, py_filename, NULL);
#else
    mod = PyImport_ExecCodeModuleEx(PyString_AS_STRING(py_fqmn), code,
            PyString_AS_STRING(py_filename));
#endif

    Py_DECREF(py_filename);
    Py_DECREF(code);

    return mod;

error:
    Py_DECREF(code);
    return NULL;
}


// Find a fully qualified module name handled by an importer and return its
// type, path name and file name.
static ModuleType find_module(QrcImporter *self, const QString &fqmn,
        QString &pathname, QString &filename)
{
    pathname = *self->path + fqmn.split(QChar('.')).last();

    // See if it is an ordinary module.
    filename = pathname + ".pyf";

    if (QFileInfo(filename).isFile())
        return ModuleIsModule;

    // See if it is a package.
    filename = pathname + "/__init__.pyf";

    if (QFileInfo(filename).isFile())
        return ModuleIsPackage;

    // See if it is a namespace.
    filename = pathname;

    if (QFileInfo(filename).isDir())
        return ModuleIsNamespace;

    // Nothing was found.
    return ModuleNotFound;
}


// Convert a Python str object to a QString.
static QString str_to_qstring(PyObject *str)
{
#if PY_MAJOR_VERSION >= 3
    Py_ssize_t len = PyUnicode_GET_LENGTH(str);

    switch (PyUnicode_KIND(str))
    {
    case PyUnicode_1BYTE_KIND:
        return QString::fromLatin1((char *)PyUnicode_1BYTE_DATA(str), len);

    case PyUnicode_2BYTE_KIND:
        // The (QChar *) cast should be safe.
        return QString((QChar *)PyUnicode_2BYTE_DATA(str), len);

    case PyUnicode_4BYTE_KIND:
        return QString::fromUcs4(PyUnicode_4BYTE_DATA(str), len);
    }

    return QString();
#else
    return QString(QLatin1String(PyString_AS_STRING(str)));
#endif
}


// Convert a QString to a Python str object.
static PyObject *qstring_to_str(const QString &qstring)
{
#if PY_MAJOR_VERSION >= 3
    QVector<uint> ucs4 = qstring.toUcs4();

    return PyUnicode_FromKindAndData(PyUnicode_4BYTE_KIND, ucs4.data(),
            ucs4.size());
#else
    return PyString_FromString(qstring.toLatin1().constData());
#endif
}


// The module initialisation function.
PYQTDEPLOY_TYPE PYQTDEPLOY_INIT()
{
    PyObject *mod;

    // Just in case we are linking against Python as a Windows DLL.
    QrcImporter_Type.tp_new = PyType_GenericNew;

    if (PyType_Ready(&QrcImporter_Type) < 0)
        PYQTDEPLOY_FATAL("Failed to initialise pyqtdeploy.qrcimporter type");

#if PY_MAJOR_VERSION >= 3
    mod = PyModule_Create(&pyqtdeploymodule);
#else
    mod = Py_InitModule("pyqtdeploy", NULL);
#endif
    if (mod == NULL)
        PYQTDEPLOY_FATAL("Failed to initialise pyqtdeploy module");

    if (PyModule_AddIntConstant(mod, "hexversion", PYQTDEPLOY_HEXVERSION) < 0)
    {
        PYQTDEPLOY_MODULE_DISCARD(mod);
        PYQTDEPLOY_FATAL("Failed to add hexversion to pyqtdeploy module");
    }

    Py_INCREF(&QrcImporter_Type);
    if (PyModule_AddObject(mod, "qrcimporter", (PyObject *)&QrcImporter_Type) < 0)
    {
        PYQTDEPLOY_MODULE_DISCARD(mod);
        PYQTDEPLOY_FATAL("Failed to add qrcimporter to pyqtdeploy module");
    }

    PYQTDEPLOY_RETURN(mod);
}
