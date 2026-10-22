# -*- coding: utf-8 -*-
"""CPM -- focused offline check of the production model-list empty states.

Runs the ACTUAL launcher and application through the R15 harness
(test_cpm_app_r15_namespace_isolation.Env, real PySide 1.2 / Qt 4.8 under
SFM's Python 2.7.5) with sfmApp faked at its boundary, and checks the five
approved outcomes of ProdWindow.populate (startup and the Refresh Models
button):
  1. no SFM document           -> neutral guidance, no popup
  2. document, no current shot -> neutral guidance, no popup
  3. shot without supported models (real discovery on an empty shot)
                               -> neutral guidance, no popup
  4. models found              -> the existing "%d model(s) found" behavior
  5. genuine failure (discovery raises; also HasDocument raising)
                               -> the existing error popup, red status and
                                  traceback logging
Message boxes are recorded at the Qt boundary instead of being shown, so no
modal can block the run. Cases 4 and 5 stub g09a_candidates in the private
module (discovery itself is unchanged and not under test there).

Usage: <SFM python 2.7.5> -E -B test_cpm_app_empty_states.py
"""
from __future__ import print_function

import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cpm_app_r15_namespace_isolation as r15  # noqa: E402

RESULTS = []
NO_SESSION = u"Open an SFM session to use Character Preset Manager."
NO_SHOT = u"Move the playhead into a shot to choose a character model."
NO_MODELS = u"Add a character model in the Animation Set Editor to get started."
REFRESH_ERROR = (u"Can't refresh model list", u"Model list could not be refreshed. Try again.")


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


class Shot(object):
    animationSets = []


def main():
    env = r15.Env("real", os.path.join(tempfile.gettempdir(), "cpm_empty_states_fixture"))
    QtGui = env.QtGui
    boxes = []
    QtGui.QMessageBox.exec_ = lambda self: boxes.append((self.windowTitle(), self.text())) or 0
    sfm = sys.modules["sfmApp"]
    sfm.HasDocument = lambda: False
    sfm.GetShotAtCurrentTime = lambda: None

    def styled(level):
        label = QtGui.QLabel()
        ns["tool_set_status"](label, u"x", level)
        return label.styleSheet()

    def state(window):
        return {"status": window.status.text(), "style": window.status.styleSheet(),
                "coverage": window.coverage.text(), "body": window.body_summary.text(),
                "expr": window.expr_summary.text(), "combo": window.combo.count()}

    def refresh(window):
        del boxes[:]
        log_before = env.log() or u""
        window.populate()
        env.settle()
        return state(window), (env.log() or u"")[len(log_before):]

    # 1. Startup with no SFM document.
    env.click()
    env.settle()
    ns = env.module().__dict__
    window = env.slot()
    s1 = state(window)
    log1 = env.log() or u""
    check("1 no document at startup: no popup", not boxes, boxes)
    check("1 no document: neutral status and guidance",
          s1["status"] == NO_SESSION and s1["style"] == styled(u"neutral")
          and s1["coverage"] == s1["body"] == s1["expr"] == NO_SESSION, s1)
    check("1 no document: logged as an empty state, not an error",
          u"empty_reason=u'no-session'" in log1 and u"PROD_ACTION_ERROR" not in log1)

    # 2. Document open, playhead outside every shot.
    sfm.HasDocument = lambda: True
    s2, log2 = refresh(window)
    check("2 document without a current shot: no popup", not boxes, boxes)
    check("2 no shot: neutral status and guidance",
          s2["status"] == NO_SHOT and s2["style"] == styled(u"neutral")
          and s2["coverage"] == s2["body"] == s2["expr"] == NO_SHOT, s2)
    check("2 no shot: empty-reason logged", u"empty_reason=u'no-shot'" in log2 and u"PROD_ACTION_ERROR" not in log2)

    # 3. Current shot without supported models (real discovery on an empty shot).
    sfm.GetShotAtCurrentTime = lambda: Shot()
    s3, log3 = refresh(window)
    check("3 shot without supported models: no popup", not boxes, boxes)
    check("3 no models: neutral status and guidance; only the placeholder in the model list",
          s3["status"] == NO_MODELS and s3["style"] == styled(u"neutral")
          and s3["coverage"] == s3["body"] == s3["expr"] == NO_MODELS and s3["combo"] == 1, s3)
    check("3 no models: empty-reason logged", u"empty_reason=u'no-models'" in log3 and u"PROD_ACTION_ERROR" not in log3)

    # 4. Models found: the existing successful behavior.
    real_candidates = ns["g09a_candidates"]
    ns["g09a_candidates"] = lambda: [{"model": u"models/example/character.mdl", "checksum": 1,
                                      "animset_name": u"character1", "binding_count": 3}]
    s4, log4 = refresh(window)
    check("4 models found: existing status and guidance, model listed, no popup",
          not boxes and s4["status"] == u"1 model(s) found. Choose a character model."
          and s4["style"] == styled(u"neutral") and s4["coverage"] == u"Choose a character model."
          and s4["combo"] == 2, s4)
    check("4 models found: logged without an empty reason", u"PROD_MODELS count=1" in log4
          and u"empty_reason=None" in log4)

    # 5. Genuine failures keep the existing error popup, red status and traceback.
    def failing():
        raise RuntimeError("synthetic discovery failure")
    ns["g09a_candidates"] = failing
    s5, log5 = refresh(window)
    check("5a discovery failure: the existing error popup",
          len(boxes) == 1 and boxes[0] == REFRESH_ERROR, boxes)
    check("5a discovery failure: red status with the existing text",
          s5["status"] == REFRESH_ERROR[1] and s5["style"] == styled(u"error"), s5)
    check("5a discovery failure: action error and traceback logged",
          u"PROD_ACTION_ERROR label='Refresh Models'" in log5 and u"synthetic discovery failure" in log5
          and u"Traceback" in log5, log5[-400:])
    ns["g09a_candidates"] = real_candidates

    def has_document_fails():
        raise RuntimeError("synthetic HasDocument failure")
    sfm.HasDocument = has_document_fails
    s6, log6 = refresh(window)
    check("5b HasDocument failure is a genuine error: existing popup, red status, traceback",
          len(boxes) == 1 and boxes[0] == REFRESH_ERROR and s6["status"] == REFRESH_ERROR[1]
          and s6["style"] == styled(u"error") and u"synthetic HasDocument failure" in log6, (boxes, s6))

    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    window.close()
    env.settle()
    os._exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
