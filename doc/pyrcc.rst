Applications that use :program:`pyrcc`
======================================

The :program:`pyrcc5` and :program:`pyrcc4` programs are the Python equivalents
(for PyQt5 and PyQt4 respectively) of Qt's :program:`rcc` program.  They
convert a collection of resource files into a Python source file that is then
imported by the application.  :program:`rcc` similarly converts the collection
of resource files to C++ code.

Using :program:`rcc` makes it possible to create a C++ application as a single
executable file.  Having a single file makes such an application easier to
deploy.  However with :program:`pyrcc5` and :program:`pyrcc4`, while they
reduce the number of files that need to be deployed, there will always be at
least two.  Of course the standard Python distribution tools are designed to
cope with multiple source files, so using :program:`pyrcc5` and
:program:`pyrcc4` doesn't offer any significant benefits.

:program:`pyqtdeploy` itself uses :program:`rcc` to embed all the files
that make up the applications and does not support the use of the output of
:program:`pyrcc5` and :program:`pyrcc4` in a deployed application.  In fact it
is recommended that these programs are simply not used irrespective of whether
:program:`pyqtdeploy` is going to be used or not.

That leaves the problem of exactly where the resource files are located.
Fortunately the same technique (and code) will work for an ordinary application
and for one that has been produced by :program:`pyqtdeploy`.  Lets say we have
a Python module that creates a number of :class:`~PyQt5.QtGui.QIcon` instances
that each have the icon loaded from a PNG file.  The PNG files are in a
sub-directory called ``images`` in the same directory as the Python module.
The following code will work in all cases::

    from PyQt5.QtCore import QFileInfo
    from PyQt5.QtGui import QIcon

    # Get the name of the directory containing the images directory, either a
    # directory in the real filesystem, or in the in-memory filesystem created
    # by rcc.
    _root = QFileInfo(__file__).absolutePath()

    # Now create the icons.  Qt is clever enough to do the right thing on all
    # platforms.
    new_icon = QIcon(_root + '/images/new.png')
    open_icon = QIcon(_root + '/images/open.png')
    save_icon = QIcon(_root + '/images/save.png')
