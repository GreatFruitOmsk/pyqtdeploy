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


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QSplitter,
        QTreeView, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
        QVBoxLayout, QWidget)

from ..metadata import external_libraries_metadata, get_python_metadata
from ..project import ExternalLibrary


SUPPORTED_PYTHON_VERSIONS = ((2, 6), (2, 7), (3, 3), (3, 4))


class StandardLibraryPage(QSplitter):
    """ The GUI for the standard library page of a project. """

    # The page's label.
    label = "Standard Library"

    @property
    def project(self):
        """ The project property getter. """

        return self._project

    @project.setter
    def project(self, value):
        """ The project property setter. """

        if self._project != value:
            self._project = value

            self._update_page()

    def __init__(self):
        """ Initialise the page. """

        super().__init__()

        self._project = None

        # Create the page's GUI.
        stdlib_pane = QWidget()
        stdlib_layout = QVBoxLayout()

        self._stdlib_edit = QTreeWidget()
        self._stdlib_edit.setHeaderLabels(["Module"])
        self._stdlib_edit.itemChanged.connect(self._module_changed)

        stdlib_layout.addWidget(self._stdlib_edit)

        stdlib_pane.setLayout(stdlib_layout)
        self.addWidget(stdlib_pane)

        extlib_pane = QWidget()
        extlib_layout = QVBoxLayout()
        extlib_sublayout = QFormLayout()

        self._version_edit = QComboBox()
        self._version_edit.addItems(
                ['{0}.{1}'.format(major, minor)
                        for major, minor in SUPPORTED_PYTHON_VERSIONS])
        self._version_edit.currentIndexChanged.connect(self._version_changed)
        extlib_sublayout.addRow("Target Python version", self._version_edit)

        self._ssl_edit = QCheckBox(stateChanged=self._ssl_changed)
        extlib_sublayout.addRow("Use SSL support", self._ssl_edit)

        extlib_layout.addLayout(extlib_sublayout)

        self._extlib_edit = QTreeView()
        self._extlib_edit.setEditTriggers(
                QTreeView.DoubleClicked|QTreeView.SelectedClicked|
                QTreeView.EditKeyPressed)

        model = QStandardItemModel(self._extlib_edit)
        model.setHorizontalHeaderLabels(
                ("External Library", 'DEFINES', 'INCLUDEPATH', 'LIBS'))
        model.itemChanged.connect(self._extlib_changed)

        for extlib in external_libraries_metadata:
            name_itm = QStandardItem(extlib.user_name)

            extlib._items = (name_itm, QStandardItem(), QStandardItem(),
                    QStandardItem())

            model.appendRow(extlib._items)

        self._extlib_edit.setModel(model)

        for col in range(3):
            self._extlib_edit.resizeColumnToContents(col)

        extlib_layout.addWidget(self._extlib_edit)

        extlib_pane.setLayout(extlib_layout)
        self.addWidget(extlib_pane)

    def _update_page(self):
        """ Update the page using the current project. """

        project = self.project

        blocked = self._version_edit.blockSignals(True)
        self._version_edit.setCurrentIndex(
                SUPPORTED_PYTHON_VERSIONS.index(project.python_target_version))
        self._version_edit.blockSignals(blocked)

        blocked = self._ssl_edit.blockSignals(True)
        self._ssl_edit.setCheckState(
                Qt.Checked if project.python_ssl else Qt.Unchecked)
        self._ssl_edit.blockSignals(blocked)

        self._update_extlib_editor()
        self._update_stdlib_editor()

    def _update_stdlib_editor(self):
        """ Update the standard library module editor. """

        project = self.project
        editor = self._stdlib_edit

        metadata = get_python_metadata(project.python_target_version)

        blocked = editor.blockSignals(True)

        editor.clear()

        def add_module(name, module, parent):
            itm = QTreeWidgetItem(parent, name.split('.')[-1:])
            itm.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
            itm._name = name

            # Handle any sub-modules.
            if module.modules is not None:
                for submodule in module.modules:
                    add_module(submodule, metadata[submodule], itm)

        for name, module in metadata.items():
            if not module.internal and '.' not in name:
                add_module(name, module, editor)

        editor.sortItems(0, Qt.AscendingOrder)

        editor.blockSignals(blocked)

        self._set_dependencies()

    def _set_dependencies(self):
        """ Set the dependency information. """

        project = self.project
        editor = self._stdlib_edit

        required_modules, required_libraries = project.get_stdlib_requirements()

        blocked = editor.blockSignals(True)

        it = QTreeWidgetItemIterator(editor)
        itm = it.value()
        while itm is not None:
            external = required_modules.get(itm._name)
            if external is None:
                state = Qt.Unchecked
            else:
                state = Qt.Checked if external else Qt.PartiallyChecked

            itm.setCheckState(0, state)

            it += 1
            itm = it.value()

        editor.blockSignals(blocked)

        model = self._extlib_edit.model()

        blocked = model.blockSignals(True)

        for extlib in external_libraries_metadata:
            if extlib.name in required_libraries:
                for idx, itm in enumerate(extlib._items):
                    itm.setFlags(
                            Qt.ItemIsEnabled|Qt.ItemIsEditable if idx != 0
                                    else Qt.ItemIsEnabled)
            else:
                for itm in extlib._items:
                    itm.setFlags(Qt.NoItemFlags)

        model.blockSignals(blocked)

    def _update_extlib_editor(self):
        """ Update the external library editor. """

        project = self.project
        model = self._extlib_edit.model()

        blocked = model.blockSignals(True)

        for extlib in external_libraries_metadata:
            _, defs, incp, libs = extlib._items

            for prj_extlib in project.external_libraries:
                if prj_extlib.name == extlib.name:
                    defs.setText(prj_extlib.defines)
                    incp.setText(prj_extlib.includepath)
                    libs.setText(prj_extlib.libs)
                    break
            else:
                defs.setText('')
                incp.setText('')
                libs.setText(extlib.libs)

        model.blockSignals(blocked)

    def _version_changed(self, idx):
        """ Invoked when the target Python version changes. """

        project = self.project

        project.python_target_version = SUPPORTED_PYTHON_VERSIONS[idx]
        self._update_page()

        project.modified = True

    def _ssl_changed(self, state):
        """ Invoked when the SSL support changes. """

        project = self.project

        project.python_ssl = (state == Qt.Checked)
        self._set_dependencies()

        project.modified = True

    def _module_changed(self, itm, col):
        """ Invoked when a standard library module has changed. """

        project = self._project
        name = itm._name

        if name in project.standard_library:
            project.standard_library.remove(name)
        else:
            project.standard_library.append(name)

        self._set_dependencies()

        project.modified = True

    def _extlib_changed(self, itm):
        """ Invoked when an external library has changed. """

        project = self.project

        idx = self._extlib_edit.model().indexFromItem(itm)
        extlib = external_libraries_metadata[idx.row()]
        col = idx.column()

        # Get the project entry, creating it if necessary.
        for prj_extlib in project.external_libraries:
            if prj_extlib.name == extlib.name:
                break
        else:
            prj_extlib = ExternalLibrary(extlib.name, '', '', extlib.libs)
            project.external_libraries.append(prj_extlib)

        # Update the project.
        text = itm.text().strip()

        if col == 1:
            prj_extlib.defines = text
        elif col == 2:
            prj_extlib.includepath = text
        elif col == 3:
            if text == '':
                text = extlib.libs
                itm.setText(text)

            prj_extlib.libs = text

        # If the project entry corresponds to the default then remove it.
        if prj_extlib.defines == '' and prj_extlib.includepath == '' and prj_extlib.libs == extlib.libs:
            project.external_libraries.remove(prj_extlib)

        project.modified = True
