# -*- coding: utf-8 -*-
"""F-01 SFP-1 (scoped poses, stage B): the Save dialog in the real CPM window (real PySide 1.2 / Qt 4.8 under SFM's
Python 2.7.5, through the R15 harness test_cpm_app_r15_namespace_isolation.Env, with sfmApp faked at its boundary).

The dialog (ProdWindow.prompt_pose_scope) is driven through its real widgets with QDialog.exec_ replaced only to avoid
a modal event loop: Full body is the default, the coverage line and the review list come from prod_scope_dialog_state,
Selected parts enables the grouped picker, checking a group checks its controls, Save and Cancel, the registry
(version 2) full-body route, and a refused full body that cannot be saved. The inventory is a fixed offline record;
scene reads are covered by test_cpm_app_f01_scoped.py.

Usage: <SFM python 2.7.5> -E -B test_cpm_app_f01_scoped_page.py
"""
from __future__ import print_function

import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cpm_app_r15_namespace_isolation as r15  # noqa: E402

RESULTS = []
SETTLE = [lambda: None]


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


def inventory(full=None, highlighted=(u"jaw",)):
    return {u"view": [{u"path": [u"Arms", u"LeftFingers"], u"bones": [u"finger1", u"finger2"],
                       u"unavailable": [{u"control": u"rig_hand_L", u"bone": None,
                                         u"reason": u"rig control (not supported in poses yet)"}]},
                      {u"path": [u"Face"], u"bones": [u"jaw"], u"unavailable": []},
                      {u"path": [u"RigArms", u"LeftArm"], u"bones": [],
                       u"unavailable": [{u"control": u"Hand_L", u"bone": u"hand", u"reason": u"driven by the rig"}]}],
            u"highlighted": list(highlighted),
            u"full_body": full or {u"status": u"available", u"code": None, u"message": None, u"review": []},
            u"signature": u"s", u"time": {}, u"root": u"pelvis", u"carried": [],
            u"classes": {u"finger1": u"direct-fk", u"finger2": u"direct-fk", u"jaw": u"direct-fk",
                         u"pelvis": u"direct-fk"},
            u"parents": {u"pelvis": None, u"hand": u"pelvis", u"finger1": u"hand", u"finger2": u"finger1",
                         u"head": u"pelvis", u"jaw": u"head"}}


def drive(window, QtGui, QtCore, inv, body_route, steps):
    """Open the real dialog; `steps(dialog, seen)` manipulates its widgets and returns True to Save, False to
    Cancel. Returns (result, seen)."""
    seen = {}
    real = QtGui.QDialog.exec_

    def fake(self):
        self.show()
        seen[u"title"] = self.windowTitle()
        seen[u"buttons"] = sorted(b.text() for b in self.findChildren(QtGui.QPushButton))
        seen[u"default"] = [b.text() for b in self.findChildren(QtGui.QPushButton) if b.isDefault()]
        save = [b for b in self.findChildren(QtGui.QPushButton) if b.text() == u"Save"][0]
        cancel = [b for b in self.findChildren(QtGui.QPushButton) if b.text() == u"Cancel"][0]
        go = steps(self, seen, save)
        (save if go else cancel).click()
        return self.result()
    QtGui.QDialog.exec_ = fake
    try:
        return window.prompt_pose_scope(inv, body_route), seen
    finally:
        QtGui.QDialog.exec_ = real
        SETTLE[0]()           # process the dialog's deferred deletion, as SFM's event loop would


def labels(dialog, QtGui):
    return [l.text() for l in dialog.findChildren(QtGui.QLabel)]


def summary_of(dialog, QtGui):
    texts = [t for t in labels(dialog, QtGui) if t and t not in (u"Name:",) and not t.startswith(u"Review these")]
    return texts[-1] if texts else u""


def main():
    env = r15.Env("real", os.path.join(tempfile.gettempdir(), "cpm_scoped_page_fixture"))
    QtGui = env.QtGui
    sfm = sys.modules["sfmApp"]
    sfm.HasDocument = lambda: False
    sfm.GetShotAtCurrentTime = lambda: None
    env.click()
    env.settle()
    window = env.slot()
    SETTLE[0] = env.settle
    QtCore = window.render.im_func.func_globals["QtCore"]

    def default(dialog, seen, save):
        tree = dialog.findChild(QtGui.QTreeWidget, "pose_scope_picker")
        radios = dict((r.text(), r) for r in dialog.findChildren(QtGui.QRadioButton))
        box = [g for g in dialog.findChildren(QtGui.QGroupBox) if g.title() == u"Review scope"][0]
        lists = [w for w in box.findChildren(QtGui.QListWidget)]
        seen[u"state"] = (radios[u"Full body"].isChecked(), not radios[u"Selected parts"].isChecked(),
                          tree.isHidden(), box.isVisible(), [lists[0].item(i).text()
                                                                    for i in range(lists[0].count())],
                          save.isEnabled(), summary_of(dialog, QtGui))
        seen[u"unavailable"] = [tree.topLevelItem(0).child(i).text(0) for i in range(tree.topLevelItem(0).childCount())
                                if not tree.topLevelItem(0).child(i).flags() & QtCore.Qt.ItemIsUserCheckable]
        groups = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        seen[u"groups"] = [(g.text(0), g.toolTip(0), bool(g.flags() & QtCore.Qt.ItemIsUserCheckable)) for g in groups]
        seen[u"unavailable_only"] = [groups[2].child(i).text(0) for i in range(groups[2].childCount())]
        return True
    got, seen = drive(window, QtGui, QtCore, inventory(), False, default)
    check("D1 the Save dialog: title Save Pose, Save and Cancel, Save is the default",
          seen[u"title"] == u"Save Pose" and seen[u"buttons"] == [u"Cancel", u"Save"] and seen[u"default"] == [u"Save"],
          seen)
    check("D1 Full body is the default; the inactive picker is hidden; the review lists the highlighted controls",
          seen[u"state"][:6] == (True, True, True, True, [u"jaw"], True), seen[u"state"])
    check("D1 coverage line comes from the ledger state",
          seen[u"state"][6] == u"Includes the listed facial bones. Facial expressions are not saved.",
          seen[u"state"][6])
    check("D1 group labels drop a repeated prefix only where unambiguous; the full path is the tooltip",
          seen[u"groups"][0][:2] == (u"LeftFingers", u"Arms > LeftFingers") and seen[u"groups"][1][0] == u"Face",
          seen[u"groups"])
    check("D1 an unavailable-only group has no checkbox, says so, and keeps its reasons",
          seen[u"groups"][2] == (u"LeftArm (unavailable)", u"None of these controls can be saved in a pose.", False)
          and seen[u"groups"][0][2] and seen[u"unavailable_only"] == [u"Hand_L: driven by the rig"], seen)
    check("D1 unavailable controls are shown with their reason, not selectable",
          seen[u"unavailable"] == [u"rig_hand_L: rig control (not supported in poses yet)"], seen[u"unavailable"])
    check("D1 Save returns the default full-body request with no exclusion",
          got == {u"name": u"Pose", u"kind": u"full_body",
                  u"request": {u"kind": u"full_body", u"bones": [], u"exclusions": []}}, got)

    def leave(dialog, seen, save):
        [c for c in dialog.findChildren(QtGui.QCheckBox) if c.text() == u"Leave these controls unchanged"][0].setChecked(
            True)
        seen[u"summary"] = summary_of(dialog, QtGui)
        return True
    got, seen = drive(window, QtGui, QtCore, inventory(), False, leave)
    check("D2 leaving the reviewed controls unchanged is an explicit, recorded user decision",
          seen[u"summary"] == u"The listed controls are left as they are on the character."
          and got[u"request"][u"exclusions"] == [{u"id": u"face", u"bones": [u"jaw"], u"reason": u"expression controls "
                                                  u"left unchanged by the artist", u"provenance": u"user_confirmed",
                                                  u"policy_revision": None, u"label": u"Face"}], (seen, got))

    def parts(dialog, seen, save):
        tree = dialog.findChild(QtGui.QTreeWidget, "pose_scope_picker")
        [r for r in dialog.findChildren(QtGui.QRadioButton) if r.text() == u"Selected parts"][0].setChecked(True)
        seen[u"empty"] = (not tree.isHidden(), save.isEnabled(), summary_of(dialog, QtGui))
        tree.topLevelItem(0).setCheckState(0, QtCore.Qt.Checked)
        seen[u"after"] = (save.isEnabled(), summary_of(dialog, QtGui),
                          [tree.topLevelItem(0).child(i).checkState(0) == QtCore.Qt.Checked for i in range(2)])
        box = [g for g in dialog.findChildren(QtGui.QGroupBox) if g.title() == u"Review scope"][0]
        seen[u"review_hidden"] = not box.isVisible()
        return True
    got, seen = drive(window, QtGui, QtCore, inventory(), False, parts)
    check("D3 Selected parts shows the picker; nothing selected cannot be saved",
          seen[u"empty"] == (True, False, u"Select at least one body control."), seen[u"empty"])
    check("D3 checking a group selects its controls; an ordinary finger selection needs no explanation",
          seen[u"after"] == (True, u"", [True, True]) and
          seen[u"review_hidden"], seen)
    check("D3 Save returns the explicit selected bones",
          got == {u"name": u"Pose", u"kind": u"selected_parts",
                  u"request": {u"kind": u"selected_parts", u"bones": [u"finger1", u"finger2"], u"exclusions": []}},
          got)
    got, seen = drive(window, QtGui, QtCore, inventory(), False, lambda d, s, save: False)
    check("D4 Cancel saves nothing", got is None, got)

    def route(dialog, seen, save):
        seen[u"summary"] = summary_of(dialog, QtGui)
        seen[u"save"] = save.isEnabled()
        return True
    got, seen = drive(window, QtGui, QtCore, inventory(highlighted=()), True, route)
    check("D5 a registry character's full body keeps its version 2 route",
          got == {u"name": u"Pose", u"kind": u"full_body", u"request": None} and seen[u"save"] and
          seen[u"summary"] == u"Facial expressions, gaze and the character's place in the scene are not saved.",
          (got, seen))
    refused = {u"status": u"refused", u"code": u"rig-driven", u"review": [],
               u"message": u"Full body can't be saved: parts of this character's body are driven by its rig. Choose "
                           u"Selected parts to save a smaller pose."}
    got, seen = drive(window, QtGui, QtCore, inventory(full=refused, highlighted=()), False, route)
    check("D6 an unsupported full body cannot be saved and points to Selected parts",
          got is None and not seen[u"save"] and u"Choose Selected parts" in seen[u"summary"], (got, seen))

    def refused_with_face(dialog, seen, save):
        box = [g for g in dialog.findChildren(QtGui.QGroupBox) if g.title() == u"Review scope"][0]
        leave_box = [c for c in dialog.findChildren(QtGui.QCheckBox) if c.text() == u"Leave these controls unchanged"]
        seen[u"review_visible"] = box.isVisible()
        seen[u"leave_visible"] = bool(leave_box) and leave_box[0].isVisible()
        seen[u"summary"] = summary_of(dialog, QtGui)
        seen[u"save"] = save.isEnabled()
        return True
    got, seen = drive(window, QtGui, QtCore, inventory(full=dict(refused, review=[u"jaw"])), False, refused_with_face)
    check("D7 a refusal the review can't resolve shows its reason only: no review checklist (PS-2 UI corrections)",
          got is None and not seen[u"review_visible"] and not seen[u"leave_visible"] and not seen[u"save"] and
          seen[u"summary"] == refused[u"message"], (got, seen))

    def picker_height(dialog, seen, save):
        tree = dialog.findChild(QtGui.QTreeWidget, "pose_scope_picker")
        [r for r in dialog.findChildren(QtGui.QRadioButton) if r.text() == u"Selected parts"][0].setChecked(True)
        SETTLE[0]()
        row = tree.sizeHintForRow(0)
        seen[u"rows"] = (tree.minimumHeight(), row, tree.topLevelItemCount(), tree.height())
        return False
    got, seen = drive(window, QtGui, QtCore, inventory(), False, picker_height)
    minimum, row, groups, shown = seen[u"rows"]
    print("D8 measured (minimum, row, groups, shown): %r" % (seen[u"rows"],))
    check("D8 the picker shows about eleven rows with only three groups (PS-2 UI corrections)",
          groups == 3 and row > 0 and minimum >= 11 * row and shown >= 11 * row, seen[u"rows"])

    def v2_only(dialog, seen, save):
        parts_radio = [r for r in dialog.findChildren(QtGui.QRadioButton) if r.text() == u"Selected parts"][0]
        seen[u"parts"] = (parts_radio.isEnabled(), parts_radio.toolTip())
        seen[u"summary"] = summary_of(dialog, QtGui)
        seen[u"save"] = save.isEnabled()
        return True
    unavailable = window.render.im_func.func_globals["prod_scope_selected_parts_unavailable"](u"generic refusal")
    got, seen = drive(window, QtGui, QtCore, unavailable, True, v2_only)
    check("D9 K1: without a generic inventory, Full body keeps the version 2 route and Selected parts says why "
          "it is unavailable",
          got == {u"name": u"Pose", u"kind": u"full_body", u"request": None} and seen[u"save"] and
          seen[u"parts"] == (False, u"generic refusal") and
          seen[u"summary"] == u"Facial expressions, gaze and the character's place in the scene are not saved.",
          (got, seen))
    try:
        window.close()
    except Exception:
        pass
    passed = sum(1 for _, ok in RESULTS if ok)
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
