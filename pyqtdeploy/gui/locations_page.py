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
from PyQt5.QtWidgets import (QFormLayout, QGroupBox, QMessageBox, QVBoxLayout,
        QWidget, QWidgetItem)

from .filename_editor import FilenameEditor


class LocationsPage(QWidget):
    """ The GUI for the locations page of a project. """

    # The page's label.
    label = "Locations"

    @property
    def project(self):
        """ The project property getter. """

        return self._project

    @project.setter
    def project(self, value):
        """ The project property setter. """

        if self._project != value:
            self._project = value
            self._host_interp_edit.set_project(value)
            self._target_inc_edit.set_project(value)
            self._target_lib_edit.set_project(value)
            self._target_stdlib_edit.set_project(value)
            self._update_page()

    def __init__(self):
        """ Initialise the page. """

        super().__init__()

        self._project = None

        # Create the page's GUI.
        py_host_group = QGroupBox("Host Python Locations")
        py_host_layout = QFormLayout(
                fieldGrowthPolicy=QFormLayout.ExpandingFieldsGrow)

        self._host_interp_edit = FilenameEditor("Host Interpreter",
                placeholderText="Interpreter executable",
                whatsThis="The name of the host interpreter's executable. "
                        "This must be on PATH or be an absolute pathname.",
                textEdited=self._host_interp_changed)
        py_host_layout.addRow("Interpreter", self._host_interp_edit)

        py_host_group.setLayout(py_host_layout)

        py_target_group = QGroupBox("Target Python Locations")
        py_target_layout = QFormLayout(
                fieldGrowthPolicy=QFormLayout.ExpandingFieldsGrow)

        self._target_inc_edit = FilenameEditor("Target Include Directory",
                placeholderText="Include directory name",
                whatsThis="The target interpreter's include directory.",
                textEdited=self._target_inc_changed, directory=True)
        py_target_layout.addRow("Include directory", self._target_inc_edit)

        self._target_lib_edit = FilenameEditor("Python Library",
                placeholderText="Library name",
                whatsThis="The target interpreter's Python library.",
                textEdited=self._target_lib_changed)
        py_target_layout.addRow("Python library", self._target_lib_edit)

        self._target_stdlib_edit = FilenameEditor(
                "Target Standard Library Directory",
                placeholderText="Standard library directory name",
                whatsThis="The target interpreter's standard library directory.",
                textEdited=self._target_stdlib_changed, directory=True)
        py_target_layout.addRow("Standard library directory",
                self._target_stdlib_edit)

        py_target_group.setLayout(py_target_layout)

        layout = QVBoxLayout()
        layout.addWidget(py_host_group)
        layout.addWidget(py_target_group)
        layout.addStretch()

        self.setLayout(layout)

        self._align_forms(py_host_layout, py_target_layout)

    def _align_forms(self, *forms):
        """ Align a set of forms. """

        # Find the widest label.
        max_width = 0

        for form in forms:
            # Force the layout to be calculated.
            form.update()
            form.activate()

            for label in self._get_labels(form):
                width = label.width()
                if max_width < width:
                    max_width = width

        for form in forms:
            alignment = form.labelAlignment() | Qt.AlignVCenter

            for label in self._get_labels(form):
                label.setMinimumWidth(max_width)
                label.setAlignment(alignment)

    def _get_labels(self, form):
        """ A generator returning the labels of a form. """

        for row in range(form.rowCount()):
            itm = form.itemAt(row, QFormLayout.LabelRole)
            if isinstance(itm, QWidgetItem):
                yield itm.widget()

    def _update_page(self):
        """ Update the page using the current project. """

        project = self.project

        self._host_interp_edit.setText(project.python_host_interpreter)
        self._target_inc_edit.setText(project.python_target_include_dir)
        self._target_lib_edit.setText(project.python_target_library)
        self._target_stdlib_edit.setText(project.python_target_stdlib_dir)

    def _host_interp_changed(self, value):
        """ Invoked when the user edits the host interpreter name. """

        self.project.python_host_interpreter = value
        self.project.modified = True

    def _target_inc_changed(self, value):
        """ Invoked when the user edits the target include directory name. """

        self.project.python_target_include_dir = value
        self.project.modified = True

    def _target_lib_changed(self, value):
        """ Invoked when the user edits the target Python library name. """

        self.project.python_target_library = value
        self.project.modified = True

    def _target_stdlib_changed(self, value):
        """ Invoked when the user edits the target standard library directory
        name.
        """

        self.project.python_target_stdlib_dir = value
        self.project.modified = True
