# -*- coding: utf-8 -*-
"""SFM Character Tools Updater -- the Tkinter GUI (L-4; card §1 and §5).

Three equally prominent primary actions -- Get Official Data, Rebuild My Data, Use Another TXT --
an installation selector, preparation and installation screens with explicit consent, progress,
a recovery mode and a Details area. Every operation runs the unchanged backend worker command in a
bounded worker process (supervisor.WorkerRun); the GUI never touches installed files itself and
never reports success unless the worker's result confirms the verified installed state.

    python -m sfm_character_tools_updater.gui
"""
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import VERSION, supervisor
from ..messages import MESSAGES

TITLE = "SFM Character Tools Updater"
SFM_CFG = os.path.join("steamapps", "common", "SourceFilmmaker", "game", "usermod", "cfg")
MASTER = "sfm_defaultanimationgroups.txt"

ACTIONS = (
    ("official", "Get Official Data",
     "Check for official animation-group data, then download and install it."),
    ("rebuild", "Rebuild My Data",
     "Rebuild the data from the animation-group TXT already in SFM, including your changes. Your TXT is not "
     "changed."),
    ("import", "Use Another TXT",
     "Install an animation-group TXT file you choose. Your current TXT is kept as a backup, and the file you "
     "choose is not changed."),
)
HEADINGS = {"success": "Done", "info": "Nothing to install", "warning": "Not installed", "error": "Not completed",
            "recovery": "Recovery needed"}
COLORS = {"success": "#1b6e20", "info": "#1f4e8c", "warning": "#8a5a00", "error": "#a11818", "recovery": "#a11818"}
WORKER_OUTCOMES = ("WORKER_MEMORY_LIMIT", "WORKER_FAILED", "WORKER_STOPPED")
# Install / recovery outcomes after which the installation must be re-examined for unfinished work.
UNSETTLED = WORKER_OUTCOMES + ("STOPPED", "CONFLICT", "ERROR")


# ---------------------------------------------------------------- installations
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


# ---------------------------------------------------------------- the application
class App(object):
    """The view and its controller. Construction arguments other than `root` exist for the
    qualification harness; the shipping entry point (main) passes none of them."""

    def __init__(self, root, installations=None, worker_argv=None, memory_limit=None, env=None, pick_file=None,
                 pick_folder=None, confirm_close=None):
        self.root = root
        self.worker_argv = worker_argv
        self.memory_limit = memory_limit
        self.env = env
        self.pick_file = pick_file or (lambda: filedialog.askopenfilename(
            parent=root, title="Choose an animation-group TXT",
            filetypes=[("Animation-group TXT", "*.txt"), ("All files", "*.*")]))
        self.pick_folder = pick_folder or (lambda: filedialog.askdirectory(
            parent=root, title="Choose the SFM installation folder", mustexist=True))
        self.confirm_close = confirm_close or (lambda text: messagebox.askyesno(TITLE, text, parent=root,
                                                                                icon="warning"))
        self.run = None            # the active WorkerRun
        self.phase = None          # what the active worker does: status | prepare | install | recover | discard
        self.prepared = None       # the result of the last successful preparation
        self.recovery_needed = False
        self.screen = None         # home | busy | confirm | result | recovery
        self.history = []          # every result of this session (shown in Details)
        self.closed = False
        self._build()
        self.set_installations(installations if installations is not None else [])

    # ------------------------------------------------------------ layout
    def _build(self):
        r = self.root
        r.title(TITLE)
        r.minsize(760, 560)
        r.protocol("WM_DELETE_WINDOW", self.on_close)
        style = ttk.Style(r)
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(10, 8))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 12, "bold"))
        outer = ttk.Frame(r, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=TITLE, style="Title.TLabel").pack(anchor="w")

        row = ttk.Frame(outer)
        row.pack(fill="x", pady=(12, 0))
        ttk.Label(row, text="SFM installation:").pack(side="left")
        self.inst_var = tk.StringVar()
        self.inst_box = ttk.Combobox(row, textvariable=self.inst_var, state="readonly")
        self.inst_box.pack(side="left", fill="x", expand=True, padx=8)
        self.inst_box.bind("<<ComboboxSelected>>", lambda e: self.select_installation(self.inst_var.get()))
        self.folder_btn = ttk.Button(row, text="Choose Folder", command=self.on_choose_folder)
        self.folder_btn.pack(side="left")
        self.state_label = ttk.Label(outer, text="", foreground="#444444")
        self.state_label.pack(anchor="w", pady=(6, 0))
        ttk.Label(outer, text=MESSAGES["CLOSE_NOTE"] + " You can check and prepare data while SFM is open.",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 8))

        grid = ttk.Frame(outer)
        grid.pack(fill="x")
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

        self.panel = ttk.Frame(outer, padding=(0, 14, 0, 0))
        self.panel.pack(fill="both", expand=True)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x")
        self.details_btn = ttk.Button(bottom, text="Show Details", command=self.toggle_details)
        self.details_btn.pack(side="left")
        ttk.Label(bottom, text="Version %s" % VERSION, foreground="#777777").pack(side="right")
        self.details = tk.Text(outer, height=12, wrap="none", font=("Consolas", 9))
        self.details_shown = False
        # Tk variables live as long as the window: one that became garbage could be collected on the
        # worker-wait thread, which Tk does not allow.
        self.consent_var = tk.BooleanVar(master=r, value=False)
        self.consent_shown = False

    def toggle_details(self):
        self.details_shown = not self.details_shown
        if self.details_shown:
            self.details.pack(fill="both", expand=True, pady=(8, 0))
            self.details_btn.configure(text="Hide Details")
        else:
            self.details.pack_forget()
            self.details_btn.configure(text="Show Details")

    def _record(self, label, res):
        res = dict(res)
        res.pop("trace", None)
        self.history.append({"step": label, "result": res})
        self.details.configure(state="normal")
        self.details.insert("end", "== %s\n%s\n" % (label, json.dumps(res, indent=1, sort_keys=True, default=str)))
        self.details.see("end")
        self.details.configure(state="disabled")

    # ------------------------------------------------------------ screens
    def _clear_panel(self):
        for w in self.panel.winfo_children():
            w.destroy()
        self.panel_text = ""
        self.panel_buttons = {}
        self.consent_var.set(False)
        self.consent_shown = False

    def _enable_actions(self, on):
        st = "normal" if on else "disabled"
        for b in self.buttons.values():
            b.configure(state=st)
        self.inst_box.configure(state="readonly" if on or self.screen == "recovery" else "disabled")
        self.folder_btn.configure(state=st if self.screen != "recovery" else "normal")

    def _message(self, kind, text, heading=None):
        self._clear_panel()
        self.panel_kind = kind
        self.panel_text = text
        ttk.Label(self.panel, text=heading or HEADINGS[kind], style="Heading.TLabel",
                  foreground=COLORS[kind]).pack(anchor="w")
        ttk.Label(self.panel, text=text, wraplength=700, justify="left").pack(anchor="w", pady=(4, 10))

    def _button(self, key, text, command, primary=False, state="normal"):
        if "row" not in self.panel_buttons:
            self.panel_buttons["row"] = ttk.Frame(self.panel)
            self.panel_buttons["row"].pack(anchor="w")
        b = ttk.Button(self.panel_buttons["row"], text=text, command=command,
                       style="Primary.TButton" if primary else "TButton", state=state)
        b.pack(side="left", padx=(0, 8))
        self.panel_buttons[key] = b
        return b

    def show_home(self, text=None):
        self.screen = "home"
        self._enable_actions(True)
        self._clear_panel()
        self.panel_kind = "home"
        self.panel_text = text or ""
        if text:
            ttk.Label(self.panel, text=text, wraplength=700, justify="left").pack(anchor="w")

    def show_busy(self, text):
        self.screen = "busy"
        self._enable_actions(False)
        self._clear_panel()
        self.panel_kind = "busy"
        self.panel_text = text
        ttk.Label(self.panel, text=text, style="Heading.TLabel").pack(anchor="w")
        bar = ttk.Progressbar(self.panel, mode="indeterminate", length=420)
        bar.pack(anchor="w", pady=10)
        bar.start(12)

    def show_result(self, kind, text, heading=None, retry=None):
        self.screen = "result"
        self._message(kind, text, heading)
        if retry:
            self._button("retry", "Try Again", retry, primary=True)
            self._button("cancel", "Cancel", self.cancel_prepared)
            self._enable_actions(False)
        else:
            self._enable_actions(True)

    def show_recovery(self, text=None):
        self.screen = "recovery"
        self.recovery_needed = True
        self._message("recovery", text or MESSAGES["RECOVERY_NEEDED"])
        self._button("recover", "Recover", self.on_recover, primary=True)
        self._enable_actions(False)

    # ------------------------------------------------------------ installations
    def set_installations(self, paths):
        self.inst_box.configure(values=list(paths))
        if paths:
            self.inst_var.set(paths[0])
            self.select_installation(paths[0])
        else:
            self.show_home("No SFM installation was found. Choose the SFM installation folder.")
            for b in self.buttons.values():
                b.configure(state="disabled")

    def on_choose_folder(self):
        folder = self.pick_folder()
        if not folder:
            return
        cfg = normalize_choice(folder)
        if not cfg:
            self.show_result("warning", "This folder isn't part of an SFM installation. Choose the SFM folder "
                                        "that contains game\\usermod\\cfg.", heading="Folder not recognized")
            return
        values = list(self.inst_box.cget("values"))
        if cfg not in values:
            values.append(cfg)
            self.inst_box.configure(values=values)
        self.inst_var.set(cfg)
        self.select_installation(cfg)

    def select_installation(self, cfg):
        self.cfg = cfg
        self.prepared = None
        self.recovery_needed = False
        self._start("status", ["status"], "Checking this SFM installation", self._after_status)

    def _after_status(self, res, note=None):
        if res.get("outcome") != "STATUS":
            self.state_label.configure(text="")
            self.show_result("error", self._text(res, "This installation couldn't be checked."))
            return
        if res.get("recovery_needed"):
            self.state_label.configure(text="An earlier update was interrupted.")
            self.show_recovery(note + " " + MESSAGES["INTERRUPTED"] if note else MESSAGES["RECOVERY_NEEDED"])
            return
        self.recovery_needed = False
        ok = (res.get("correspondence") or {}).get("ok")
        self.state_label.configure(text="Installed data matches the TXT." if ok else
                                   "Installed data doesn't match the TXT. Rebuild My Data fixes this.")
        if note:
            self.show_result(note[0], note[1])
        else:
            self.show_home("Choose an action.")

    # ------------------------------------------------------------ worker
    def _start(self, phase, args, busy_text, then):
        self.phase = phase
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
        lead = self._text(res)
        self._start("status", ["status"], "Checking this SFM installation",
                    lambda st: self._after_status(st, note=lead if st.get("recovery_needed") else ("error", lead)))

    @staticmethod
    def _text(res, fallback=None):
        o = res.get("outcome")
        if o in WORKER_OUTCOMES:
            return MESSAGES[o]
        return res.get("message") or fallback or MESSAGES["ERROR"]

    # ------------------------------------------------------------ actions
    def on_official(self):
        self._start("check", ["check-official"], "Checking for official data", self._after_check)

    def _after_check(self, res):
        o = res.get("outcome")
        if o == "AVAILABLE":
            offer = res["offer"]
            self.screen = "confirm"
            self._message("info", res["message"] + " Download it and prepare it for installation? Nothing is "
                                                   "installed until you confirm.", heading="Official data found")
            self._button("download", "Download", lambda: self._start(
                "prepare", ["download-official", "--release-tag", offer["release_tag"], "--descriptor-sha",
                            offer["descriptor_sha256"]], "Downloading and checking official data",
                self._after_prepare), primary=True)
            self._button("cancel", "Cancel", lambda: self.show_home("Nothing was changed."))
            self._enable_actions(False)
        elif o in ("NONE_PUBLISHED", "INSTALLED_CURRENT"):
            self.show_result("info", res["message"], heading="Official data")
        else:
            self.show_result("warning" if o != "CHECK_FAILED" else "error", self._text(res), heading="Official data")

    def on_rebuild(self):
        self._start("prepare", ["prepare-rebuild"], "Rebuilding your data from your current TXT", self._after_prepare)

    def on_import(self):
        path = self.pick_file()
        if not path:
            return
        self.chosen = os.path.abspath(path)
        self._start("prepare", ["prepare-import", "--source", self.chosen], "Checking the TXT you chose",
                    self._after_prepare)

    def _after_prepare(self, res):
        if res.get("outcome") != "PREPARED":
            self.prepared = None
            self.show_result("warning", self._text(res))
            return
        self.prepared = res
        self.screen = "confirm"
        wf = res["workflow"]
        heading = {"rebuild": "Rebuilt data is ready", "import": "Your TXT is ready",
                   "official": "Official data is ready"}[wf]
        lines = [res["message"]]
        if wf == "import":
            lines.append("File: %s" % res["source"].get("path", ""))
        lines.append("Installs into: %s" % self.cfg)
        self._message("info", "\n".join(lines), heading=heading)
        if res.get("consent_required"):
            # Consent comes before the Install button, which stays disabled until it is given.
            self.consent_shown = True
            ttk.Checkbutton(self.panel, variable=self.consent_var,
                            text="Replace the animation-group TXT in this installation. My current TXT is kept as "
                                 "a backup.",
                            command=lambda: self.panel_buttons["install"].configure(
                                state="normal" if self.consent_var.get() else "disabled")).pack(anchor="w",
                                                                                                  pady=(0, 10))
        self._button("install", "Install", self.on_install, primary=True,
                     state="disabled" if res.get("consent_required") else "normal")
        self._button("cancel", "Cancel", self.cancel_prepared)
        self._enable_actions(False)

    def cancel_prepared(self):
        p, self.prepared = self.prepared, None
        if p and p.get("prepid"):
            self._start("discard", ["discard-prepared", "--prepared", p["prepid"]], "Discarding the prepared data",
                        lambda res: self.show_home("Nothing was installed."))
        else:
            self.show_home("Nothing was installed.")

    def on_install(self):
        p = self.prepared
        if not p:
            return
        args = ["install", "--prepared", p["prepid"], "--confirm-sha", p["confirm_sha"]]
        if p.get("consent_required"):
            if not (self.consent_shown and self.consent_var.get()):
                return
            args.append("--accept-replacement")
        self._start("install", args, "Installing. Keep SFM closed until this finishes.", self._after_install)

    def _after_install(self, res):
        o = res.get("outcome")
        if o == "COMPLETE":
            self.prepared = None
            self.state_label.configure(text="Installed data matches the TXT.")
            self.show_result("success", res["message"],
                             heading={"rebuild": "Your data was rebuilt", "import": "Your TXT is installed",
                                      "official": "Official data is installed"}.get(res.get("workflow"), "Done"))
        elif o == "NOOP":
            self.prepared = None
            self.show_result("info", res["message"], heading="Already installed")
        elif o == "UNVERIFIED":
            self.prepared = None
            self.show_result("error", res["message"], heading="Installed, but not verified")
        elif o == "REFUSED" and (res.get("details") or {}).get("gate"):
            self.show_result("warning", "SFM appears to be open. Close SFM, then try again. Nothing was changed.",
                             heading="Close SFM first", retry=self.on_install)
        elif o in UNSETTLED:
            self._recheck(res)
        else:
            self.prepared = None
            self.show_result("warning", self._text(res))

    def on_recover(self):
        self._start("recover", ["recover"], "Recovering. Keep SFM closed until this finishes.", self._after_recover)

    def _after_recover(self, res):
        o = res.get("outcome")
        if o == "REFUSED" and (res.get("details") or {}).get("gate"):
            self.show_recovery("SFM appears to be open. Close SFM, then choose Recover.")
            return
        lead = self._text(res)
        if o in ("OK", "NOTHING_TO_RECOVER"):
            kind = "success" if res.get("installed_state") == "WORKING" else "warning"
            self._start("status", ["status"], "Checking this SFM installation",
                        lambda st: self._after_status(st, note=lead if st.get("recovery_needed") else (kind, lead)))
        else:
            self._recheck(res)

    # ------------------------------------------------------------ closing
    def on_close(self):
        if self.run is not None and not self.run.done.is_set():
            text = ("An installation is running. If you close now it is stopped, and you will need to choose "
                    "Recover next time. Close anyway?" if self.phase in ("install", "recover") else
                    "An operation is running. Closing stops it. Close anyway?")
            if not self.confirm_close(text):
                return
            self.run.request_stop()
            self.run.wait(30)
        self.closed = True
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
