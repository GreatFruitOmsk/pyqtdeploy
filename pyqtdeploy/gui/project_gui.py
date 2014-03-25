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

from PyQt5.QtCore import QPoint, QSettings, QSize
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QFileDialog, QMainWindow, QMessageBox, QTabWidget,
        QWhatsThis)

from ..builder import Builder
from ..project import Project
from ..user_exception import UserException

from .application_page import ApplicationPage
from .extension_modules_page import ExtensionModulesPage
from .pyqt_page import PyQtPage
from .python_page import PythonPage
from .site_packages_page import SitePackagesPage
from .stdlib_page import StdlibPage


class ProjectGUI(QMainWindow):
    """ The GUI for a project. """

    # The filter string to use with file dialogs.
    file_dialog_filter = "Projects (*.pdy)"

    def __init__(self, project):
        """ Initialise the GUI for a project. """

        super().__init__()

        self._create_menus()
        self._create_central_widget()
        self._load_settings()

        self._set_project(project)

    @classmethod
    def load(cls, filename):
        """ Create a project from the given file.  Return None if there was an
        error.
        """

        return cls._load_project(filename) if os.path.isfile(filename) else Project(filename)

    def closeEvent(self, event):
        """ Handle a close event. """

        if self._current_project_done():
            self._save_settings()
            event.accept()
        else:
            event.ignore()

    def _set_project(self, project):
        """ Set the GUI's project. """

        self._project = project

        self._project.modified_changed.connect(self.setWindowModified)
        self._project.name_changed.connect(self._name_changed)

        self._name_changed(self._project.name)

        tabs = self.centralWidget()

        for p in range(tabs.count()):
            page = tabs.widget(p)
            page.project = self._project

    def _name_changed(self, name):
        """ Invoked when the project's name changes. """

        title = os.path.basename(name) if name != '' else "Unnamed"
        self.setWindowTitle(title + '[*]')

        self._save_action.setEnabled(name != '')

    def _create_menus(self):
        """ Create the menus. """

        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&New", self._new_project, QKeySequence.New)
        file_menu.addAction("&Open...", self._open_project, QKeySequence.Open)
        self._save_action = file_menu.addAction("&Save", self._save_project,
                QKeySequence.Save)
        file_menu.addAction("Save &As...", self._save_as_project,
                QKeySequence.SaveAs)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, QKeySequence.Quit)

        build_menu = menu_bar.addMenu("&Build")
        build_menu.addAction("Build Project...", self._build_project)

        menu_bar.addSeparator()

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(QWhatsThis.createAction(help_menu))

    def _create_central_widget(self):
        """ Create the central widget. """

        tabs = QTabWidget()

        for page_factory in (ApplicationPage, PyQtPage, StdlibPage, SitePackagesPage, ExtensionModulesPage, PythonPage):
            page = page_factory()
            tabs.addTab(page, page.label)

        self.setCentralWidget(tabs)

    def _new_project(self):
        """ Create a new, unnamed project. """

        if self._current_project_done():
            self._set_project(Project())

    def _open_project(self):
        """ Open an existing project. """

        if self._current_project_done():
            filename, _ = QFileDialog.getOpenFileName(self, "Open",
                    filter=self.file_dialog_filter)

            if filename != '':
                project = self._load_project(filename, self)
                if project is not None:
                    self._set_project(project)

    def _save_project(self):
        """ Save the project and return True if it was saved. """

        try:
            self._project.save()
        except UserException as e:
            self._handle_exception(e, "Save", self)
            return False

        return True

    def _save_as_project(self):
        """ Save the project under a new name and return True if it was saved.
        """

        filename, _ = QFileDialog.getSaveFileName(self, "Save As",
                    filter=self.file_dialog_filter)

        if filename == '':
            return False

        try:
            self._project.save_as(filename)
        except UserException as e:
            self._handle_exception(e, "Save", self)
            return False

        return True

    def _build_project(self):
        """ Build the project. """

        project = self._project

        # Check the prerequisites.  Note that we don't disable the menu option
        # if these are missing because (as they are spread across the GUI) the
        # user would have difficulty knowing what needed fixing.
        if project.application_script == '':
            self._missing_prereq("main script file")
            return

        if project.python_host_interpreter == '':
            self._missing_prereq("host interpreter")
            return

        if project.application_script == '':
            self._missing_prereq("target Python include directory")
            return

        if project.application_script == '':
            self._missing_prereq("target Python library")
            return

        build_dir = QFileDialog.getExistingDirectory(self, "Build Project")
        if build_dir == '':
            return

        try:
            Builder(project).build(build_dir)
            QMessageBox.information(self, "Build Project",
                    "The project was built successfully.")
        except UserException as e:
            self._handle_exception(e, "Build Project", self)

    def _missing_prereq(self, missing):
        """ Tell the user about a missing prerequisite. """

        QMessageBox.warning(self, "Build Project",
                "The project cannot be built because the name of the {0} has "
                        "not been set.".format(missing))

    @classmethod
    def _load_project(cls, filename, parent=None):
        """ Create a project from the given file.  Return None if there was an
        error.
        """

        try:
            project = Project.load(filename)
        except UserException as e:
            cls._handle_exception(e, "Open", parent)
            project = None

        return project

    @staticmethod
    def _handle_exception(e, title, parent):
        """ Handle a UserException. """

        msg_box = QMessageBox(QMessageBox.Warning, title, e.text,
                parent=parent)

        if e.detail != '':
            msg_box.setDetailedText(e.detail)

        msg_box.exec()

    def _current_project_done(self):
        """ Return True if the user has finished with any current project. """

        if self._project.modified:
            msg_box = QMessageBox(QMessageBox.Question, "Save",
                    "The project has been modified.",
                    QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,
                    parent=self)

            msg_box.setDefaultButton(QMessageBox.Save)
            msg_box.setInformativeText("Do you want to save your changes?")

            ans = msg_box.exec()

            if ans == QMessageBox.Cancel:
                return False

            if ans == QMessageBox.Save:
                return self._save_project() if self._project.name != "" else self._save_as_project()

        return True

    def _load_settings(self):
        """ Load the user specific settings. """

        settings = QSettings()

        self.resize(settings.value('size', QSize(600, 400)))
        self.move(settings.value('pos', QPoint(200, 200)))

    def _save_settings(self):
        """ Save the user specific settings. """

        settings = QSettings()

        settings.setValue('size', self.size())
        settings.setValue('pos', self.pos())
