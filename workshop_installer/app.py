"""Small, synchronous Windows Setup window. No background installation or service."""
import argparse
import os
import sys
from pathlib import Path

from . import core, release
from .window import Window

FRESH = ("Install Control Group Normalizer, Character Preset Manager, Control Group Updater "
         "and the CPM toolbar button.\n\nSetup will install the included Animation Groups. "
         "If an Animation Groups file already exists, it will be backed up before replacement."
         "\n\nClose Source Filmmaker before installing.")
UPDATE = ("Setup will replace the installed Character Tools programs and Animation Groups "
          "with this Workshop package.\n\nYour current Animation Groups file will be backed up "
          "before replacement. Custom edits will not be combined with the replacement."
          "\n\nClose Source Filmmaker before continuing.")
REMOVE = ("This will remove Character Tools, its toolbar button, scripts and supporting files, "
          "including edited program files.\n\nYour Animation Groups file and its backups will remain."
          "\n\nClose Source Filmmaker before uninstalling.")


class SetupWindow:
    def __init__(self, game, package, helper):
        self.game, self.package, self.helper = game, package, helper
        self.prepared = None
        self.busy = False
        self.details = ""
        self.window = Window("SFM Character Tools Setup")
        self.refresh()

    def page(self, title, message, buttons):
        subtitle = "Version included: " + release.VERSION + "\nInstall location: " + str(self.game / "usermod")
        self.window.page(title, subtitle, message, buttons)

    def capture(self):
        if self.prepared is None:
            if not self.package or not self.package.is_file():
                raise core.Refusal("Obtain the Workshop package and launch Setup from its Workshop menu entry.")
            self.prepared = core.prepare(self.package, self.helper)
        return self.prepared

    def refresh(self):
        try:
            core._legacy_record_clear(self.game)
            op = core._operation(self.game)
            if op:
                core._resume_states(self.game, op)
                if op["kind"] == "uninstall":
                    self.page("Removal incomplete", "Close SFM, then finish removing Character Tools.",
                              [("Finish Uninstall", lambda: self.perform(self.finish_remove)), ("Close", self.close)])
                else:
                    available = False
                    try:
                        p = self.capture()
                        available = p.package == op["package"] and p.files == op["files"]
                    except Exception as exc:
                        self.details = str(exc)
                    message = "Setup could not finish. Keep SFM closed and run Setup again to complete the installation."
                    if not available:
                        message += ("\n\nObtain the exact Workshop package used for this unfinished installation. "
                                    "Required package SHA-256: " + op["package"])
                    buttons = [("Retry", lambda: self.perform(self.retry))] if available else []
                    buttons += [("Details", self.show_details), ("Close", self.close)]
                    self.page("Installation incomplete", message, buttons)
                return
            # Removal is available even if the payload or Autoinit Manager is absent.
            removal = core.removal_preview(self.game)
            existing = bool(core._current_record(self.game) or any(
                h is not None for p, h in removal.items() if core._program_path(p)))
            try:
                summary = core.preview(self.game, self.capture())
            except Exception as exc:
                self.details = str(exc)
                buttons = [("Uninstall…", self.confirm_remove)] if existing else []
                buttons += [("Details", self.show_details), ("Close", self.close)]
                self.page("Setup needs attention", str(exc), buttons)
                return
            self.snapshot = summary["snapshot"]
            message = UPDATE if summary["existing"] else FRESH
            if summary["installed_version"]:
                message = "Installed version: " + summary["installed_version"] + "\n\n" + message
            buttons = [("Update / Reinstall" if summary["existing"] else "Install",
                        lambda: self.perform(self.install))]
            if existing:
                buttons.append(("Uninstall…", self.confirm_remove))
            buttons.append(("Cancel", self.close))
            self.page("SFM Character Tools Setup", message, buttons)
        except Exception as exc:
            self.error(exc)

    def perform(self, action):
        if self.busy:
            return
        self.busy = True
        self.window.set_busy(True)
        try:
            action()
        except Exception as exc:
            self.error(exc)
        finally:
            self.busy = False
            self.window.set_busy(False)

    def error(self, exc):
        self.details = str(exc)
        if isinstance(exc, core.RecoveryConflict):
            self.page("Recovery blocked", str(exc),
                      [("Details", self.show_details), ("Close", self.close)])
            return
        try:
            op = core._operation(self.game)
        except Exception:
            op = None
        message = ("Removal incomplete. Keep SFM closed and run Setup again to finish removal."
                   if op and op["kind"] == "uninstall" else
                   "Setup could not finish. Keep SFM closed and run Setup again to complete the installation."
                   if op else "Setup could not complete this action.\n\n" + str(exc))
        if op:
            message += "\n\n" + str(exc)
        self.page("Setup needs attention", message,
                  [("Review / Retry", self.refresh), ("Details", self.show_details), ("Close", self.close)])

    def show_details(self):
        # Details stay in the same owned window; no nested modal event loop.
        if not self.details:
            self.details = "Finish the recorded operation using the required package."
        self.window.details(self.details)

    def install(self):
        result = core.install(self.game, self.capture(), self.snapshot)
        self.success(result)

    def retry(self):
        result = core.recover(self.game, self.capture())
        self.success(result)

    def success(self, result):
        message = ("SFM Character Tools is installed. Open SFM and choose Scripts → SFM Character Tools."
                   "\n\nIf the CPM toolbar button is disabled, enable it in Autoinit Manager and restart SFM.")
        buttons = []
        if result["backup"]:
            buttons.append(("Open Backups", lambda: os.startfile(str(core._state_path(self.game, "backups")))))
        buttons.append(("Close", self.close))
        self.page("Installation complete", message, buttons)

    def confirm_remove(self):
        try:
            self.remove_snapshot = core.removal_preview(self.game)
            self.page("Uninstall SFM Character Tools?", REMOVE,
                      [("Uninstall", lambda: self.perform(self.finish_remove)), ("Cancel", self.refresh)])
        except Exception as exc:
            self.error(exc)

    def finish_remove(self):
        result = core.uninstall(self.game, getattr(self, "remove_snapshot", None))
        message = ("SFM Character Tools has been removed. Your Animation Groups file and backups remain."
                   "\n\nUnsubscribe from the Workshop item to remove its Setup menu entry.")
        if result["remaining_helper"]:
            message += "\n\nAfter closing Setup, delete the remaining Setup file:\n" + str(core._target(self.game, core.HELPER))
        if result["authority_remaining"]:
            message += "\n\nThe sidecar folder remains because it contains unrelated files:\n" + ", ".join(result["authority_remaining"])
        if result["remaining_directories"]:
            self.details = "Folders retained because they are nonempty or unavailable:\n" + "\n".join(result["remaining_directories"])
            buttons = [("Details", self.show_details), ("Close", self.close)]
        else:
            buttons = [("Close", self.close)]
        self.page("Removal complete", message, buttons)

    def close(self):
        if not self.busy:
            self.window.close()

    def run(self):
        try:
            self.window.run()
        finally:
            if self.prepared:
                self.prepared.close()


class _SetupParser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        # A windowed executable has no stdout/stderr. argparse help/errors must
        # not create a bootloader exception dialog before Setup opens.
        output = file or sys.stderr or sys.stdout
        if message and output is not None:
            output.write(message)


def main(argv=None):
    parser = _SetupParser()
    parser.add_argument("--game", required=True)
    parser.add_argument("--manage", action="store_true")
    args = parser.parse_args(argv)
    try:
        game = core._validate_game(args.game)
    except Exception as exc:
        window = Window("SFM Character Tools Setup")
        window.page("Setup needs attention", "", "Setup could not use this SFM location.\n\n" + str(exc),
                    [("Close", window.close)])
        window.run()
        return 1
    executable = Path(sys.executable)
    # Installed management can uninstall without this source. Install/retry still
    # require the exact verified package; never use installed application files.
    candidates = [executable.parent / release.ARCHIVE,
                  game / "workshop" / "scripts" / "sfm" / "mainmenu" /
                  "SFM Character Tools" / "_workshop_installer" / release.ARCHIVE]
    package = next((p for p in candidates if p.is_file()), None)
    SetupWindow(game, package, executable).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
