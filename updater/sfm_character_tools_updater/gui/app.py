# -*- coding: utf-8 -*-
"""SFM Control Group Updater -- the Tkinter GUI of the SFM Character Tools updater (L-4, with the
owner-approved usability refinement and final polish of 2026-10-18).

The updater builds and installs Character Tools data that corresponds to SFM's animation-group TXT;
it never edits the contents of a TXT. Three equally prominent primary actions -- Get Published
Version, Update Using SFM's TXT, Choose Another TXT File -- an SFM folder selector, one clear
confirmation where the installed TXT is replaced, a recovery mode and an About window. Every
operation runs the unchanged backend worker command in a bounded worker process
(supervisor.WorkerRun); the GUI never touches installed files itself and never reports success unless
the worker's result confirms the verified installed state.

    python -m sfm_character_tools_updater.gui
"""
import json
import os
import re
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import VERSION, supervisor
from ..messages import MESSAGES

TITLE = "SFM Control Group Updater"
SFM_CFG = os.path.join("steamapps", "common", "SourceFilmmaker", "game", "usermod", "cfg")
MASTER = "sfm_defaultanimationgroups.txt"
BACKUP_DIR = "sfm_character_tools_backups"
REMINDER = "Close SFM before updating its animation-group TXT or Character Tools data."
FOLDER_PICKER_TITLE = "Select your SourceFilmmaker folder"
STATUS_MATCH = "Installed animation-group TXT and Character Tools data match."
UPDATING = "Updating Character Tools data…"
ABOUT_TITLE = "About SFM Control Group Updater"
ABOUT = ("SFM uses an animation-group TXT file to organize flex and bone controls.\n\n"
         "ChadChan3D publishes an expanded version of this TXT for SFM Character Tools. If your models have flex or "
         "bone names missing from the published TXT, you can add them by editing your own copy.\n\n"
         "This updater builds matching Character Tools data from whichever animation-group TXT you choose.")

ACTIONS = (
    ("official", "Get Published Version", "Download the flex and bone organization maintained by ChadChan3D."),
    ("rebuild", "Update Using SFM's TXT",
     "Build Character Tools data from the animation-group TXT already in your SFM folder."),
    ("import", "Choose Another TXT File", "Select a different animation-group TXT to use in SFM."),
)
COLORS = {"success": "#1b6e20", "info": "#1f4e8c", "warning": "#8a5a00", "error": "#a11818", "recovery": "#a11818"}
SUBTLE = "#666666"
WORKER_OUTCOMES = ("WORKER_MEMORY_LIMIT", "WORKER_FAILED", "WORKER_STOPPED")
# Install / recovery outcomes after which the installation must be re-examined for unfinished work.
UNSETTLED = WORKER_OUTCOMES + ("STOPPED", "CONFLICT", "ERROR")
MESSAGE_KEYS = {v: k for k, v in MESSAGES.items()}

# User-facing (heading, text) for worker outcomes and message keys. Technical detail stays in the
# worker results kept by the window (App.diagnostics, Ctrl+Shift+D copies them for support).
TEXT = {
    "WORKER_MEMORY_LIMIT": ("The update was stopped", "It needed more memory than this program allows. Nothing was "
                                                      "installed."),
    "WORKER_FAILED": ("The update stopped unexpectedly", "Nothing was installed."),
    "WORKER_STOPPED": ("The update was stopped", "Nothing was installed."),
    "SOURCE_INVALID": ("This file can't be used", "Choose an SFM animation-group TXT that contains usable flex and "
                                                  "bone group definitions. Nothing was changed."),
    "SOURCE_UNREADABLE": ("This file couldn't be read", "Check that it still exists and isn't open in another "
                                                        "program. Nothing was changed."),
    "SOURCE_TOO_LARGE": ("This file can't be used", "It is too large to be an animation-group TXT. Nothing was "
                                                    "changed."),
    "SOURCE_CHANGED": ("The file you chose changed", "It changed after it was checked, so nothing was replaced. "
                                                     "Choose the file again."),
    "REBUILD_INVALID": ("SFM's TXT has errors", "Character Tools data can't be built from the animation-group TXT "
                                                "in SFM because it has errors. Nothing was changed. Fix the TXT, or "
                                                "choose another TXT file."),
    "DESTINATION_CHANGED": ("Your animation groups changed", "SFM's animation-group TXT changed after it was "
                                                             "checked, so nothing was replaced. Try again to review "
                                                             "the change."),
    "PREPARE_AGAIN": ("Your data changed", "Something changed after it was checked. Nothing was changed. Try "
                                          "again."),
    "BACKUP_FAILED": ("Nothing was replaced", "Your current animation-group TXT couldn't be saved to the Backups "
                                              "folder, so it was not replaced."),
    "MISSING": ("Animation-group TXT not found", "This SFM folder has no animation-group TXT, or it can't be read. "
                                                 "Nothing was changed."),
    "PATH_TOO_LONG": ("SFM folder path too long", "This SFM folder's path is too long for Character Tools to read. "
                                                  "Nothing was changed."),
    "FOLDER_CHANGED": ("Unexpected files found", "The data folder contains something unexpected, so nothing was "
                                                 "changed."),
    "RELEASE_RECORD_BUSY": ("Another window is busy", "Another updater window is using this SFM folder. Close it, "
                                                      "then try again."),
    "UNVERIFIED": ("The update couldn't be verified", "The update finished, but the result couldn't be verified. "
                                                      "Choose Update Using SFM's TXT before using Character Tools."),
    # Get Published Version
    "NONE_PUBLISHED": ("Nothing published yet", "ChadChan3D hasn't published a version yet. Nothing was changed."),
    "CHECK_FAILED": ("Couldn't check for a published version", "Check your internet connection and try again. "
                                                              "Nothing was changed."),
    "NEEDS_NEWER_UPDATER": ("This program needs an update", "A newer published version needs a newer version of "
                                                            "this program. Nothing was changed."),
    "OFFICIAL_INCOMPATIBLE": ("Published version not compatible", "The published version found isn't compatible "
                                                                  "with the Character Tools installed here. Nothing "
                                                                  "was changed."),
    "OFFICIAL_UNVERIFIED": ("Published version rejected", "A published version was found, but it couldn't be "
                                                          "verified as coming from ChadChan3D, so it wasn't used. "
                                                          "Nothing was changed."),
    "RELEASE_CONFLICT": ("Published version rejected", "The published versions found don't match each other or "
                                                       "versions seen before, so they weren't used. Nothing was "
                                                       "changed."),
    "DOWNLOAD_FAILED": ("Download failed", "Check your internet connection and try again. Nothing was changed."),
    "RELEASE_CHANGED": ("The published version changed", "It changed after it was checked. Nothing was changed. "
                                                         "Choose Get Published Version again."),
    "PACKAGE_UNTRUSTED": ("Published version rejected", "It couldn't be verified as coming from ChadChan3D, so it "
                                                        "wasn't used. Nothing was changed."),
    "PACKAGE_DAMAGED": ("Published version rejected", "The download was damaged or altered, so it wasn't used. "
                                                      "Nothing was changed. Try again."),
    "PACKAGE_INVALID": ("Published version rejected", "The download was incomplete, so it wasn't used. Nothing was "
                                                      "changed. Try again."),
    "PACKAGE_NEEDS_NEWER": ("This program needs an update", "This published version needs a newer version of this "
                                                            "program. Nothing was changed."),
    "PACKAGE_INCOMPATIBLE": ("Published version not compatible", "It isn't compatible with the Character Tools "
                                                                 "installed here. Nothing was changed."),
    "PACKAGE_OLDER": ("No newer published version", "This published version is older than one already used here. "
                                                    "Nothing was changed."),
    "PACKAGE_CONFLICT": ("Published version rejected", "It doesn't match a published version seen before, so it "
                                                       "wasn't used. Nothing was changed."),
}


# ---------------------------------------------------------------- SFM folders
def _steam_roots():
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.append(winreg.QueryValueEx(k, "SteamPath")[0])
    except OSError:
        pass
    pf = os.environ.get("ProgramFiles(x86)")
    if pf:
        roots.append(os.path.join(pf, "Steam"))
    return roots


def detect_installations():
    """Read-only: SFM `usermod\\cfg` folders in the Steam libraries listed by Steam."""
    libs = []
    for root in _steam_roots():
        libs.append(root)
        try:
            vdf = open(os.path.join(root, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace").read()
            libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', vdf)]
        except OSError:
            pass
    found = []
    for lib in libs:
        cfg = os.path.normpath(os.path.join(lib, SFM_CFG))
        if os.path.isdir(cfg) and os.path.normcase(cfg) not in [os.path.normcase(f) for f in found]:
            found.append(cfg)
    return found


def normalize_choice(folder):
    """A chosen folder -> its usermod\\cfg folder, or None if it isn't part of an SFM installation."""
    folder = os.path.normpath(folder)
    for cand in (folder, os.path.join(folder, "cfg"), os.path.join(folder, "usermod", "cfg"),
                 os.path.join(folder, "game", "usermod", "cfg")):
        if os.path.basename(cand).lower() == "cfg" and os.path.isfile(os.path.join(cand, MASTER)):
            return cand
    return None


def sfm_folder(cfg):
    """The SFM folder a user recognizes (…\\SourceFilmmaker) for a `game\\usermod\\cfg` folder."""
    parts = os.path.normpath(cfg).split(os.sep)
    if len(parts) > 3 and [p.lower() for p in parts[-3:]] == ["game", "usermod", "cfg"]:
        return os.sep.join(parts[:-3])
    return os.path.normpath(cfg)


def center_over(win, parent):
    """Place `win` centered over `parent`."""
    win.update_idletasks()
    parent.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))


# ---------------------------------------------------------------- the application
class App(object):
    """The view and its controller. Construction arguments other than `root` exist for the
    qualification harness; the shipping entry point (main) passes none of them."""

    def __init__(self, root, installations=None, worker_argv=None, memory_limit=None, env=None, pick_file=None,
                 pick_folder=None, confirm_close=None, open_folder=None):
        self.root = root
        self.worker_argv = worker_argv
        self.memory_limit = memory_limit
        self.env = env
        self.pick_file = pick_file or (lambda: filedialog.askopenfilename(
            parent=root, title="Choose an animation-group TXT",
            filetypes=[("Animation-group TXT", "*.txt"), ("All files", "*.*")]))
        self.pick_folder = pick_folder or (lambda: filedialog.askdirectory(
            parent=root, title=FOLDER_PICKER_TITLE, mustexist=True,
            initialdir=sfm_folder(self.cfg) if self.cfg else None))
        self.confirm_close = confirm_close or (lambda text: messagebox.askyesno(TITLE, text, parent=root,
                                                                                icon="warning"))
        self.open_folder = open_folder or (lambda path: subprocess.Popen(["explorer", "/select," + path]))
        self.run = None            # the active WorkerRun
        self.phase = None          # what the active worker does: status | check | prepare | install | recover | discard
        self.prepared = None       # the result of the last successful preparation
        self.recovery_needed = False
        self.screen = None         # home | busy | checking | confirm | wait | result | recovery
        self.history = []          # every worker result of this session (App.diagnostics)
        self.closed = False
        self.cfg = None
        self.folders = {}          # displayed SFM folder -> its usermod\cfg folder
        self.about = None
        self.status = ("", "")     # the installed-data status: ("ok" | "alert" | "", text)
        self._build()
        self.set_installations(installations if installations is not None else [])

    # ------------------------------------------------------------ layout
    def _build(self):
        r = self.root
        r.title(TITLE)
        r.minsize(760, 500)
        r.protocol("WM_DELETE_WINDOW", self.on_close)
        r.bind("<Control-Shift-D>", lambda e: self.copy_diagnostics())
        style = ttk.Style(r)
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(10, 8))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 12, "bold"))
        outer = ttk.Frame(r, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=TITLE, style="Title.TLabel").pack(anchor="w")

        row = ttk.Frame(outer)
        row.pack(fill="x", pady=(12, 0))
        ttk.Label(row, text="SFM folder:").pack(side="left")
        self.inst_var = tk.StringVar(master=r)
        self.inst_box = ttk.Combobox(row, textvariable=self.inst_var, state="readonly")
        self.inst_box.pack(side="left", fill="x", expand=True, padx=8)
        self.inst_box.bind("<<ComboboxSelected>>",
                           lambda e: self.select_installation(self.folders.get(self.inst_var.get())))
        self.folder_btn = ttk.Button(row, text="Change Folder", command=self.on_choose_folder)
        self.folder_btn.pack(side="left")
        # Prominent only for a genuine mismatch, error or required recovery; empty otherwise.
        self.alert_label = ttk.Label(outer, text="", wraplength=720, justify="left")
        self.alert_label.pack(anchor="w", pady=(6, 0))

        grid = ttk.Frame(outer)
        grid.pack(fill="x", pady=(10, 0))
        self.buttons = {}
        for col, (key, label, text) in enumerate(ACTIONS):
            grid.columnconfigure(col, weight=1, uniform="actions")
            b = ttk.Button(grid, text=label, style="Primary.TButton",
                           command={"official": self.on_official, "rebuild": self.on_rebuild,
                                    "import": self.on_import}[key])
            b.grid(row=0, column=col, sticky="ew", padx=6)
            ttk.Label(grid, text=text, wraplength=220, justify="left").grid(row=1, column=col, sticky="nw",
                                                                              padx=8, pady=(6, 0))
            self.buttons[key] = b
        ttk.Label(outer, text=REMINDER).pack(anchor="w", padx=8, pady=(12, 0))

        self.panel = ttk.Frame(outer, padding=(0, 12, 0, 0))
        self.panel.pack(fill="both", expand=True)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", side="bottom", pady=(10, 0))
        ttk.Button(bottom, text="About", command=self.show_about).pack(side="left")
        ttk.Button(bottom, text="Close", command=self.on_close).pack(side="right")
        self.state_label = ttk.Label(bottom, text="", foreground=SUBTLE, font=("Segoe UI", 9))
        self.state_label.pack(side="left", padx=(12, 0))

    # ------------------------------------------------------------ installed-data status
    def set_status(self, kind, text, color=None):
        """kind "ok": subtle text at the bottom; "alert": prominent text under the folder; "" clears."""
        self.status = (kind, text)
        self._show_status()
        if kind == "alert":
            self.alert_label.configure(foreground=color or COLORS["warning"])

    def _show_status(self, hidden=False):
        kind, text = self.status
        self.state_label.configure(text="" if hidden or kind != "ok" else text)
        self.alert_label.configure(text=text if kind == "alert" else "")

    # ------------------------------------------------------------ About and diagnostics
    def diagnostics(self):
        """Technical detail for developer troubleshooting (Ctrl+Shift+D copies it); never shown."""
        return json.dumps({"program": TITLE, "version": VERSION, "cfg": self.cfg, "screen": self.screen,
                           "results": self.history}, indent=1, sort_keys=True, default=str)

    def copy_diagnostics(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.diagnostics())

    def show_about(self):
        if self.about is not None:
            self.about.lift()
            return
        w = self.about = tk.Toplevel(self.root)
        w.title(ABOUT_TITLE)
        w.resizable(False, False)
        w.transient(self.root)
        w.protocol("WM_DELETE_WINDOW", self.close_about)
        f = ttk.Frame(w, padding=16)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=ABOUT_TITLE, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(f, text=ABOUT, wraplength=460, justify="left").pack(anchor="w", pady=(8, 12))
        for label, value in (("Version:", VERSION), ("Author:", "ChadChan3D")):
            line = ttk.Frame(f)
            line.pack(anchor="w")
            ttk.Label(line, text=label, font=("Segoe UI", 9, "bold")).pack(side="left")
            ttk.Label(line, text=value).pack(side="left", padx=(4, 0))
        ttk.Button(f, text="Close", command=self.close_about).pack(side="right", pady=(12, 0))
        center_over(w, self.root)

    def close_about(self):
        if self.about is not None:
            self.about.destroy()
            self.about = None

    def _record(self, label, res):
        res = dict(res)
        res.pop("trace", None)
        self.history.append({"step": label, "result": res})

    # ------------------------------------------------------------ screens
    def _clear_panel(self):
        for w in self.panel.winfo_children():
            w.destroy()
        self.panel_text = ""
        self.panel_heading = ""
        self.panel_buttons = {}

    def _enable_actions(self, on):
        st = "normal" if on and self.cfg else "disabled"
        for b in self.buttons.values():
            b.configure(state=st)
        busy = self.screen in ("busy", "checking")
        self.inst_box.configure(state="disabled" if busy else "readonly")
        self.folder_btn.configure(state="disabled" if busy else "normal")
        self._show_status(hidden=busy or self.screen in ("confirm", "wait"))

    def _message(self, kind, heading, text):
        self._clear_panel()
        self.panel_kind = kind
        self.panel_heading = heading
        self.panel_text = text
        if heading:
            ttk.Label(self.panel, text=heading, style="Heading.TLabel", foreground=COLORS[kind]).pack(anchor="w")
        if text:
            ttk.Label(self.panel, text=text, wraplength=720, justify="left").pack(anchor="w", pady=(4, 10))

    def _button(self, key, text, command, primary=False):
        if "row" not in self.panel_buttons:
            self.panel_buttons["row"] = ttk.Frame(self.panel)
            self.panel_buttons["row"].pack(anchor="w")
        b = ttk.Button(self.panel_buttons["row"], text=text, command=command,
                       style="Primary.TButton" if primary else "TButton")
        b.pack(side="left", padx=(0, 8))
        self.panel_buttons[key] = b
        return b

    def show_home(self):
        self.screen = "home"
        self._message("info", "", "")
        self.panel_kind = "home"
        self._enable_actions(True)

    def show_busy(self, text):
        # One stable message per operation: a following step with the same text keeps the same
        # progress bar instead of rebuilding it.
        if not (self.screen == "busy" and getattr(self, "panel_heading", None) == text):
            self._message("info", text, "")
            self.panel_kind = "busy"
            bar = ttk.Progressbar(self.panel, mode="indeterminate", length=420)
            bar.pack(anchor="w", pady=10)
            bar.start(12)
            self.busy_bar = bar
        self.screen = "busy"
        self._enable_actions(False)

    def show_result(self, kind, heading, text, buttons=()):
        self.screen = "result"
        self._message(kind, heading, text)
        for key, label, command in buttons:
            self._button(key, label, command, primary=key != "cancel")
        self._enable_actions(True)

    def show_recovery(self, text):
        self.screen = "recovery"
        self.recovery_needed = True
        self._message("recovery", "Recovery needed", text)
        self._button("recover", "Recover", self.on_recover, primary=True)
        self._enable_actions(False)

    # ------------------------------------------------------------ SFM folders
    def set_installations(self, paths):
        self.folders = {sfm_folder(p): p for p in paths}
        self.inst_box.configure(values=list(self.folders))
        if paths:
            self.inst_var.set(sfm_folder(paths[0]))
            self.select_installation(paths[0])
        else:
            self.set_status("alert", "No SFM folder was found. Choose Change Folder and select your SourceFilmmaker "
                                     "folder.")
            self.show_home()

    def on_choose_folder(self):
        folder = self.pick_folder()
        if not folder:
            return
        cfg = normalize_choice(folder)
        if not cfg:
            self.show_result("warning", "This isn't an SFM folder", "Choose the SourceFilmmaker folder that contains "
                                                                    "game\\usermod\\cfg.")
            return
        self.folders[sfm_folder(cfg)] = cfg
        self.inst_box.configure(values=list(self.folders))
        self.inst_var.set(sfm_folder(cfg))
        self.select_installation(cfg)

    def select_installation(self, cfg):
        if not cfg:
            return
        self.cfg = cfg
        self.prepared = None
        self.recovery_needed = False
        self._start("status", ["status"], None, self._after_status)

    def _after_status(self, res, note=None):
        if res.get("outcome") != "STATUS":
            self.set_status("alert", "This SFM folder couldn't be checked.", COLORS["error"])
            self.show_result("error", *self._text(res))
            return
        if res.get("recovery_needed"):
            self.set_status("alert", "The last update was interrupted.", COLORS["error"])
            lead = (note + " ") if isinstance(note, str) else ""
            self.show_recovery(lead + "The last update was interrupted. Close SFM, then choose Recover. Other "
                                      "actions are unavailable until it is recovered.")
            return
        self.recovery_needed = False
        if (res.get("correspondence") or {}).get("ok"):
            self.set_status("ok", STATUS_MATCH)
        else:
            self.set_status("alert", "Character Tools data doesn't match the animation-group TXT in SFM. Choose "
                                     "Update Using SFM's TXT to fix this.")
        if note:
            self.show_result(*note)
        else:
            self.show_home()

    # ------------------------------------------------------------ worker
    def _start(self, phase, args, busy_text, then):
        self.phase = phase
        if busy_text is None:
            # A quick read-only check: a short line of text, not a flashing progress bar.
            self.screen = "checking"
            self.status = ("ok", "Checking animation-group data…")
            self._enable_actions(False)
            self.state_label.configure(text=self.status[1])
        else:
            self.show_busy(busy_text)
        try:
            self.run = supervisor.WorkerRun(args + ["--installation", self.cfg], worker_argv=self.worker_argv,
                                            memory_limit=self.memory_limit, env=self.env).start()
        except Exception as e:
            self.run = None
            res = {"outcome": "WORKER_FAILED", "details": {"start_error": "%s: %s" % (type(e).__name__, e)}}
            self._record(args[0], res)
            self._finish_worker(phase, res, then)
            return
        self.root.after(100, self._poll, args[0], then)

    def _poll(self, label, then):
        if self.closed:
            return
        run = self.run
        if run is None or not run.done.is_set():
            self.root.after(100, self._poll, label, then)
            return
        self.run = None
        res = run.result
        self._record(label, res)
        self._finish_worker(self.phase, res, then)

    def _finish_worker(self, phase, res, then):
        self.phase = None
        if res["outcome"] in WORKER_OUTCOMES and phase in ("install", "recover"):
            # The worker ended without a verified result while it may have been changing files:
            # never report success; look at the installation again.
            self._recheck(res)
            return
        then(res)

    def _recheck(self, res):
        heading, text = self._text(res)
        self._start("status", ["status"], None, lambda st: self._after_status(
            st, note=heading + ". " + text if st.get("recovery_needed") else ("error", heading, text)))

    @staticmethod
    def _key(res):
        o = res.get("outcome")
        if o in WORKER_OUTCOMES or o in TEXT:
            return o
        return MESSAGE_KEYS.get(res.get("message"))

    def _text(self, res):
        key = self._key(res)
        if key in TEXT:
            return TEXT[key]
        return "Not completed", res.get("message") or MESSAGES["ERROR"]

    # ------------------------------------------------------------ Get Published Version
    def on_official(self):
        self._start("check", ["check-official"], "Checking for a published version…", self._after_check)

    def _after_check(self, res):
        o = res.get("outcome")
        note = (" A newer published version needs a newer version of this program."
                if res.get("newer_needs_newer_updater") else "")
        if o == "AVAILABLE":
            offer = res["offer"]
            self.screen = "confirm"
            self._message("info", "Published version available",
                          "A published animation-group TXT and matching Character Tools data are available to "
                          "install." + note)
            self._button("download", "Download and Install", lambda: self._start(
                "prepare", ["download-official", "--release-tag", offer["release_tag"], "--descriptor-sha",
                            offer["descriptor_sha256"]], "Downloading the published version…",
                self._after_prepare), primary=True)
            self._button("cancel", "Cancel", self.show_home)
            self._enable_actions(False)
        elif o == "INSTALLED_CURRENT":
            v = res["installed_release"]["data_version"]
            self.show_result("info", "Published version already installed",
                             "Published animation-group version %s is already installed. Nothing was changed.%s"
                             % (v, note))
        elif o == "OLDER_ONLY":
            self.show_result("info", "No newer published version",
                             "The published version found (%s) is older than one already used here, so it wasn't "
                             "offered. Nothing was changed." % res["older_release"]["data_version"])
        else:
            heading, text = self._text(res)
            self.show_result("info" if o == "NONE_PUBLISHED" else "warning", heading, text + note)

    # ------------------------------------------------------------ Update Using SFM's TXT
    def on_rebuild(self):
        self._start("prepare", ["prepare-rebuild"], UPDATING, self._after_prepare)

    # ------------------------------------------------------------ Choose Another TXT File
    def on_import(self):
        path = self.pick_file()
        if not path:
            return
        self.chosen = os.path.abspath(path)
        self._start("prepare", ["prepare-import", "--source", self.chosen], "Checking the file you chose…",
                    self._after_prepare)

    # ------------------------------------------------------------ preparation -> installation
    def _after_prepare(self, res):
        if res.get("outcome") != "PREPARED":
            self.prepared = None
            self.show_result("warning", *self._text(res))
            return
        self.prepared = res
        if res.get("consent_required"):
            self.show_replace_confirmation()
        elif (res.get("process_status") or ["UNKNOWN"])[0] == "CLEAR":
            self.on_install()
        else:
            self.show_wait_for_sfm()

    def _backup_folder(self):
        return os.path.join(self.cfg, BACKUP_DIR)

    def show_replace_confirmation(self):
        p = self.prepared
        self.screen = "confirm"
        if p["workflow"] == "official":
            # Proposed wording (not owner-approved verbatim): a published version replacing a TXT that
            # doesn't match any published version.
            lead = ("This will replace SFM's animation-group TXT with published version %s and build matching "
                    "Character Tools data." % p["official"]["data_version"])
        else:
            lead = ("This will replace SFM's animation-group TXT with your chosen file and build matching Character "
                    "Tools data.")
        text = "%s\n\nYour current animation-group TXT will be saved in the Backups folder.\n%s" % (
            lead, self._backup_folder())
        self._message("info", "Replace your animation groups?", text)
        self._button("replace", "Replace Groups", lambda: self.on_install(replace=True), primary=True)
        self._button("cancel", "Cancel", self.cancel_prepared)
        self._enable_actions(False)

    def show_wait_for_sfm(self, replace=False):
        self.screen = "wait"
        label = "Replace Groups" if replace else "Finish Update"
        self._message("warning", "Close SFM to finish",
                      "SFM appears to be open. Save your work, close SFM, then choose %s. Nothing has been changed "
                      "yet." % label)
        self._button("finish", label, lambda: self.on_install(replace=replace), primary=True)
        self._button("cancel", "Cancel", self.cancel_prepared)
        self._enable_actions(False)

    def cancel_prepared(self):
        p, self.prepared = self.prepared, None
        if p and p.get("prepid"):
            self._start("discard", ["discard-prepared", "--prepared", p["prepid"]], "Cancelling…",
                        lambda res: self.show_result("info", "Nothing was changed", ""))
        else:
            self.show_result("info", "Nothing was changed", "")

    def on_install(self, replace=False):
        p = self.prepared
        if not p:
            return
        args = ["install", "--prepared", p["prepid"], "--confirm-sha", p["confirm_sha"]]
        if p.get("consent_required"):
            if not replace:
                return
            args += ["--accept-replacement", "--backup-txt"]
        self._start("install", args, UPDATING, lambda res: self._after_install(res, replace))

    def _after_install(self, res, replace=False):
        o = res.get("outcome")
        p = self.prepared or {}
        if o == "COMPLETE":
            self.prepared = None
            self.set_status("ok", STATUS_MATCH)
            wf = res.get("workflow")
            backup = res.get("user_backup") or {}
            saved = backup.get("previous_txt_replaced") is True
            if wf == "rebuild":
                heading = "Character Tools data updated"
                text = "Character Tools data now matches the animation-group TXT in SFM."
            elif wf == "import":
                heading = "Animation groups updated"
                text = "Your chosen animation-group TXT and matching Character Tools data are installed."
            else:
                v = (p.get("official") or {}).get("data_version", "")
                heading = "Published version %s installed" % v
                text = ("Published animation-group version %s and matching Character Tools data are installed." % v)
            if saved:
                text += "\n\nYour previous animation-group TXT was saved in the Backups folder.\n%s" % os.path.join(
                    backup["folder"], backup["name"])
            if res.get("restart_required"):
                text += "\n\nSFM was opened during the update. Close and reopen SFM before using Character Tools."
            buttons = [("open_backup", "Open Backup Folder",
                        lambda: self.open_folder(os.path.join(backup["folder"], backup["name"])))] if saved else []
            self.show_result("success", heading, text, buttons)
        elif o == "NOOP":
            self.prepared = None
            self.set_status("ok", STATUS_MATCH)
            self.show_result("success", "Your data already matches",
                             "Character Tools data already matches the animation-group TXT in SFM. Nothing was "
                             "changed.")
        elif o == "UNVERIFIED":
            self.prepared = None
            self.show_result("error", *TEXT["UNVERIFIED"])
        elif o == "REFUSED" and (res.get("details") or {}).get("gate"):
            self.show_wait_for_sfm(replace)
        elif o in UNSETTLED:
            self._recheck(res)
        else:
            self.prepared = None
            self.show_result("warning", *self._text(res))

    # ------------------------------------------------------------ recovery
    def on_recover(self):
        self._start("recover", ["recover"], "Recovering. Keep SFM closed until this finishes.", self._after_recover)

    def _after_recover(self, res):
        o = res.get("outcome")
        if o == "REFUSED" and (res.get("details") or {}).get("gate"):
            self.show_recovery("SFM appears to be open. Close SFM, then choose Recover.")
            return
        if o in ("OK", "NOTHING_TO_RECOVER"):
            note = (("success", "Recovered", "Your animation groups and Character Tools data were restored to a "
                                             "working state.") if res.get("installed_state") == "WORKING" else
                    ("warning", "Recovered", "Your previous files were restored. Choose Update Using SFM's TXT to "
                                             "update Character Tools data."))
            self._start("status", ["status"], None,
                        lambda st: self._after_status(st, note=note[1] + ". " + note[2]
                                                      if st.get("recovery_needed") else note))
        else:
            self._recheck(res)

    # ------------------------------------------------------------ closing
    def on_close(self):
        if self.run is not None and not self.run.done.is_set():
            text = ("An update is running. If you close now it is stopped, and you will need to choose Recover next "
                    "time. Close anyway?" if self.phase in ("install", "recover") else
                    "An operation is running. Closing stops it. Close anyway?")
            if not self.confirm_close(text):
                return
            self.run.request_stop()
            self.run.wait(30)
        self.closed = True
        self.close_about()
        self.root.destroy()


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root, installations=detect_installations())
    root.mainloop()
