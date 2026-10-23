# -*- coding: ascii -*-
# SFM Control Group Updater -- Scripts-menu launcher (release assembly, 2026-10-22).
#
# RUN TYPE: MAINMENU. Deployed as
# <SFM game>/usermod/scripts/sfm/mainmenu/ChadChan3D/SFM_Control_Group_Updater.py.
# Not part of the signed 31-file compatibility inventory; listed in the software archive manifest.
#
# Starts the external one-folder updater
#   <SFM game>/usermod/tools/SFM Control Group Updater/SFM Control Group Updater.exe
# as an independent process with --sfm-folder <this SourceFilmmaker folder>, and returns at once.
# It never waits for or talks to the updater, and loads no updater, CPM or authority code into
# SFM. The updater itself refuses to install data while SFM is running, so SFM must be closed
# before any installation; this script does not change that.
#
# SFM runs every Scripts-menu script in one shared, process-lifetime namespace. This launcher
# keeps its imports and working state local, adds nothing to sys.path, and deletes its own
# function before returning. Its one retained object is the reusable "not found" notice.
#
# (Comments, not a docstring: a module docstring would rebind __doc__ in SFM's shared
# Scripts-menu namespace.)


def _chadchan3d_updater_launcher_v1():
    import os
    import subprocess
    import sys

    notice_attr = "_chadchan3d_updater_launch_notice_v1"
    notice_name = "chadchan3d_updater_launch_notice_v1"
    detached_process = 0x00000008
    create_new_process_group = 0x00000200

    def console(text):
        try:
            sys.stdout.write("[ChadChan3D Updater launcher] %s\n" % (text,))
        except Exception:
            pass

    def notice(text):
        """One retained, parentless, non-modal notice; never shown over an active modal dialog."""
        try:
            from PySide import QtCore
            from PySide import QtGui
        except Exception as exc:
            console("notice unavailable (%r): %s" % (exc, text))
            return "no-qt"
        try:
            app = QtGui.QApplication.instance()
            if app is None:
                console("notice unavailable (no QApplication): %s" % (text,))
                return "no-qapplication"
            if app.activeModalWidget() is not None:
                console("notice suppressed (a modal dialog is active): %s" % (text,))
                return "suppressed-modal"
            box = getattr(app, notice_attr, None)
            if box is None:
                box = QtGui.QMessageBox()
                box.setObjectName(notice_name)
                box.setWindowTitle("SFM Control Group Updater")
                box.setIcon(QtGui.QMessageBox.Warning)
                box.setStandardButtons(QtGui.QMessageBox.Ok)
                box.setModal(False)
                box.setWindowModality(QtCore.Qt.NonModal)
                box.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
                box.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
                setattr(app, notice_attr, box)
            elif not (isinstance(box, QtGui.QMessageBox) and box.objectName() == notice_name):
                console("notice slot foreign; left untouched: %s" % (text,))
                return "slot-foreign"
            box.setText(text)
            box.show()
            box.raise_()
            return "shown"
        except Exception as exc:
            console("notice failed (%r): %s" % (exc, text))
            return "failed"

    game = os.path.dirname(os.path.abspath(sys.executable))
    sfm_folder = os.path.dirname(game)
    tools = os.path.join(game, "usermod", "tools", "SFM Control Group Updater")
    exe = os.path.join(tools, "SFM Control Group Updater.exe")

    if not os.path.isfile(exe):
        console("outcome=not-found path=%s" % (exe,))
        notice(
            "SFM Control Group Updater isn't installed in this SFM.\n\n"
            "Expected:\n%s\n\n"
            "Download \"SFM Control Group Updater\" from the SFM Character Tools release, and extract "
            "its \"SFM Control Group Updater\" folder into:\n%s\n\n"
            "Then choose this menu entry again." % (exe, os.path.dirname(tools)))
        return
    try:
        subprocess.Popen([exe, "--sfm-folder", sfm_folder], cwd=tools, close_fds=True,
                         creationflags=detached_process | create_new_process_group)
    except Exception as exc:
        console("outcome=start-failed error=%r path=%s" % (exc, exe))
        notice(
            "SFM Control Group Updater couldn't be started.\n\n%s\n\n"
            "Check that this file exists and isn't blocked, then try again." % (exe,))
        return
    console("outcome=started sfm_folder=%s (close SFM before installing data)" % (sfm_folder,))


try:
    _chadchan3d_updater_launcher_v1()
finally:
    try:
        del _chadchan3d_updater_launcher_v1
    except NameError:
        pass
