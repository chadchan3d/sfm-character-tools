# -*- coding: ascii -*-
"""F-01 UA-1: the capture script on the candidate's real dialogs (SFM's Python 2.7.5 with PySide, through the R15
harness's real window, with sfmApp faked at its boundary). The candidate is read from commit d3d23d1 (CPM 8eccf172...).

- The capture answers every dialog as Cancel: the confirmations return False, and exec_ is restored afterwards,
  also when the captured function raises.
- The captured content of the real Update Pose, Delete Pose, Update Preset and Trash dialogs passes the comparator's
  own checks (ua_compare.message_problems / trash_problems), and a wrong expectation does not.
- An end-to-end step (A7) through ua_capture finds the CPM module and window and writes its capture file once.
They show nothing about SFM itself.

Usage: <SFM python 2.7.5> -E -B test_ua_capture.py
"""
from __future__ import print_function

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, os.path.join(REPO, "cpm", "convergence", "tests"))
sys.path.insert(0, os.path.join(KIT, "tools"))
import test_cpm_app_r15_namespace_isolation as r15  # noqa: E402
import ua_compare as C  # noqa: E402

CANDIDATE = "8eccf1723fef395fcf0678ea25c0dbdf145ba77d1558ca318887aa6cfe057194"
CAPTURE = os.path.join(KIT, "observer", "F01_UA_Capture.py")
TRASH_FOLDER = u"C:/Library/Trash"
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def capture_namespace():
    """The capture script's functions, without running its final call."""
    with open(CAPTURE, "rb") as f:
        src = f.read()
    tail = b"ua_capture(globals())"
    if not src.rstrip().endswith(tail):
        raise AssertionError("the capture script no longer ends with its single call")
    ns = {"__name__": "ua_capture_under_test"}
    exec(compile(src.rstrip()[:-len(tail)], CAPTURE, "exec"), ns)
    return ns


def main():
    raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                   "d3d23d1:cpm/app/SFM_Character_Preset_Manager.py"])
    if hashlib.sha256(raw).hexdigest() != CANDIDATE:
        print("RESULT: the candidate at d3d23d1 is not %s" % CANDIDATE)
        return 1
    out_dir = tempfile.mkdtemp(prefix="ua_capture_q_")
    # The harness reads APP_PATH through its own file redirection; it is handed the candidate's exact bytes instead.
    sentinel = "<d3d23d1 candidate>"
    real_read = r15._read
    r15._read = lambda path: raw if path == sentinel else real_read(path)
    r15.APP_PATH = sentinel
    try:
        env = r15.Env("real", os.path.join(tempfile.gettempdir(), "cpm_ua_capture_fixture"))
        QtGui = env.QtGui
        sfm = sys.modules["sfmApp"]
        sfm.HasDocument = lambda: False
        sfm.GetShotAtCurrentTime = lambda: None
        env.click()
        env.settle()
        window = env.slot()
        g = window.render.im_func.func_globals
        check("U0 the harness runs the d3d23d1 candidate (its build hash, its new helpers)",
              g.get("__chadchan3d_cpm_build_sha256__") in (None, CANDIDATE) and
              all(n in g for n in ("tool_confirm_action", "tool_confirm_trash", "prod_pose_session_project")),
              g.get("__chadchan3d_cpm_build_sha256__"))
        ns = capture_namespace()
        run = ns["ua_run_captured"]
        real = (QtGui.QDialog.exec_, QtGui.QMessageBox.exec_)
        answers = []

        def answered(fn):
            return lambda: answers.append(fn())
        seen, error = run(QtGui, answered(lambda: window.confirm_pose_update(u"UA Pose", u"Full body")))
        cap = {"dialogs": seen, "error": error}
        check("U1 Update Pose: captured, answered as Cancel, passes the comparator's check",
              answers == [False] and not C.message_problems(cap, C.UPDATE_POSE % u"UA Pose", u"Update Pose"),
              (answers, C.message_problems(cap, C.UPDATE_POSE % u"UA Pose", u"Update Pose")))
        check("U1 a wrong expectation fails the same check",
              C.message_problems(cap, C.UPDATE_POSE % u"Other", u"Update Pose") != [])
        del answers[:]
        seen, error = run(QtGui, answered(lambda: window.confirm_pose_trash(u"UA <Pose>", TRASH_FOLDER)))
        cap = {"dialogs": seen, "error": error}
        p = C.trash_problems(cap, C.TRASH["trash_pose"] % u"UA <Pose>", TRASH_FOLDER)
        check("U2 Delete Pose: captured, answered as Cancel, name escaped, folder selectable, passes the check",
              answers == [False] and not p, (answers, p, seen))
        check("U2 a wrong folder fails the same check",
              C.trash_problems(cap, C.TRASH["trash_pose"] % u"UA <Pose>", u"C:/Elsewhere") != [])
        for kind, name, question, trash_question in (("body", u"UA Body", C.UPDATE_BODY, C.TRASH["trash_body"]),
                                                     ("expression", u"UA Expr", C.UPDATE_EXPRESSION,
                                                      C.TRASH["trash_expression"])):
            del answers[:]
            seen, error = run(QtGui, answered(lambda: g["tool_confirm_action"](window, question % name,
                                                                               u"Update Preset")))
            p1 = C.message_problems({"dialogs": seen, "error": error}, question % name, u"Update Preset")
            seen, error = run(QtGui, answered(lambda: g["tool_confirm_trash"](window, trash_question % name,
                                                                              TRASH_FOLDER)))
            p2 = C.trash_problems({"dialogs": seen, "error": error}, trash_question % name, TRASH_FOLDER)
            check("U3 %s preset Update and Trash dialogs: captured, Cancel, pass the checks" % kind,
                  answers == [False, False] and not p1 and not p2, (answers, p1, p2))
        consts = []
        for name in ("update_kind", "delete_kind"):
            code = getattr(window, name).im_func.func_code
            consts += [k for k in code.co_consts if isinstance(k, basestring)]
            for sub in code.co_consts:
                if hasattr(sub, "co_consts"):
                    consts += [k for k in sub.co_consts if isinstance(k, basestring)]
        check("U3 the window's preset dialogs use exactly the comparator's questions",
              all(t in consts for t in (C.UPDATE_BODY, C.UPDATE_EXPRESSION, C.TRASH["trash_body"],
                                        C.TRASH["trash_expression"])), [t for t in consts if u"saved" in t])

        def boom():
            QtGui.QMessageBox(window).exec_()
            raise RuntimeError("boom")
        seen, error = run(QtGui, boom)
        check("U4 a raising function is recorded and exec_ is restored",
              error == u"RuntimeError: boom" and len(seen) == 1 and
              (QtGui.QDialog.exec_, QtGui.QMessageBox.exec_) == real, error)
        check("U4 exec_ restored after every capture", (QtGui.QDialog.exec_, QtGui.QMessageBox.exec_) == real)
        QtGui.QApplication.clipboard().setText(TRASH_FOLDER)
        step = {"UA_DIR": out_dir, "UA_STEP": "A7"}
        os.makedirs(os.path.join(out_dir, "observations"))
        cap_ns = dict(ns)
        cap_ns.update(step)
        cap_ns["ua_capture"](cap_ns)
        path = os.path.join(out_dir, "observations", "UA-A7.json")
        data = json.load(open(path)) if os.path.isfile(path) else {}
        check("U5 ua_capture A7 finds the CPM module and window and writes its capture (clipboard, pid, build)",
              data.get("step") == "A7" and data.get("clipboard") == TRASH_FOLDER and data.get("pid") == os.getpid()
              and data.get("captures") == {} and "cpm_build_sha256" in data, data)
        try:
            cap_ns["ua_capture"](cap_ns)
            again = False
        except RuntimeError:
            again = True
        check("U5 each step is captured once", again)
        try:
            window.close()
        except Exception:
            pass
    finally:
        r15._read = real_read
        shutil.rmtree(out_dir, True)
    passed = sum(1 for _, ok in RESULTS if ok)
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
