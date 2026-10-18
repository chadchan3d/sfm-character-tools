# -*- coding: utf-8 -*-
"""TEST-ONLY: runs the L-4 GUI in its own process for the window-killed case. Never shipped.

  gui_driver.py CFG PIDFILE WORKER_ARGV_JSON

Opens the real GUI (withdrawn) on CFG with the given test worker and chooses Update Using SFM's
TXT, which installs directly while SFM is closed. When the worker reports that it holds at its
barrier (the test worker's --hold-marker file, named in WORKER_ARGV_JSON), writes
"<gui pid> <worker pid>" to PIDFILE and keeps running until the controller kills this process.
"""
import json
import os
import sys
import tkinter as tk

UPDATER = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, UPDATER)

from sfm_character_tools_updater.gui import app as gapp  # noqa: E402


def main():
    cfg, pidfile, argv = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    marker = argv[argv.index("--hold-marker") + 1]
    root = tk.Tk()
    root.withdraw()
    a = gapp.App(root, installations=[cfg], worker_argv=argv, env=dict(os.environ))
    stage = {"n": 0}

    def tick():
        if a.run is None and a.screen == "home" and stage["n"] == 0:
            stage["n"] = 1
            a.buttons["rebuild"].invoke()
        elif stage["n"] == 1 and a.phase == "install" and os.path.exists(marker) and a.run is not None:
            stage["n"] = 3
            with open(pidfile, "x", encoding="ascii") as f:
                f.write("%d %d\n" % (os.getpid(), a.run.pid))
        root.after(100, tick)
    root.after(100, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
