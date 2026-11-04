# -*- coding: utf-8 -*-
"""F-01 Pose Library M1, stage D: the Poses page in the real CPM window (real PySide 1.2 / Qt 4.8 under SFM's
Python 2.7.5, through the R15 harness test_cpm_app_r15_namespace_isolation.Env, with sfmApp faked at its boundary).

Checks: tab order (Poses after Clothing Fit; Review appended last), labels without ellipses, the compact tab style,
the window's unchanged minimum size, the page's widgets and its enablement with no character, and an offline
estimate of the tab strip at the minimum width with "Review (12)" (native verification stays U-1: fonts and styles
differ inside SFM).

Usage: <SFM python 2.7.5> -E -B test_cpm_app_f01_pose_page.py
"""
from __future__ import print_function

import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cpm_app_r15_namespace_isolation as r15  # noqa: E402

RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


def section_selection_refresh(window, tabs, env, boxes):
    """NQ-1 process A defect: selecting a character while Poses is open left Save New disabled until a tab change.
    The real window's model-selection publish (render) and clear paths run; only their scene-facing helpers are
    stubbed at the module boundary (provider, discovery, pose registry and library)."""
    g = window.render.im_func.func_globals
    saved = dict((k, g[k]) for k in ("prod_probe_semantic_provider", "prod_discover", "prod_load_library_meta",
                                      "prod_pose_load_registry", "prod_pose_selected_library", "prod_pose_discover",
                                      "prod_pose_rig_class", "prod_pose_registry_select"))
    g["prod_probe_semantic_provider"] = lambda ident, **kw: (None, {"status": u"unavailable", "reason": u"test"})
    g["prod_discover"] = lambda ident, kind: []
    g["prod_load_library_meta"] = lambda ident: saved["prod_load_library_meta"](ident)
    g["prod_pose_load_registry"] = lambda: {}
    g["prod_pose_selected_library"] = lambda ident: {u"char_dir": u"unused", u"character_key": u"k"}
    g["prod_pose_discover"] = lambda char_dir, key, reg: {u"items": [], u"unusable": []}
    g["prod_pose_rig_class"] = lambda reg, model, checksum: u"krystal-biped"
    g["prod_pose_registry_select"] = lambda reg, mode: {}
    calls = []
    counter = lambda index: calls.append(index)  # noqa: E731
    tabs.currentChanged.connect(counter)
    try:
        tabs.setCurrentWidget(window.pose_page)
        env.settle()
        del calls[:]
        check("P6 precondition: Poses open, no character, Save New disabled",
              window.identity is None and not window.save_pose_button.isEnabled())
        ident = {"model": u"models/test/krystal2020.mdl", "checksum": 1234, "animset_name": u"Krystal"}
        try:
            window.render(identity=ident, selection_token={"kind": u"test-token"})
            error = None
        except Exception as exc:
            error = exc
        env.settle()
        check("P6 the model-selection publish ran", error is None and window.identity is not None, error)
        check("P6 selecting a character while Poses is open enables Save New at once",
              window.save_pose_button.isEnabled())
        check("P6 the Poses summary names the character without a tab change",
              u"Krystal" in window.pose_summary.text() and not calls, (window.pose_summary.text(), calls))
        check("P6 the selected character's pose list was read on selection", window.pose_items_key is not None)
        window.clear_model_selection()
        env.settle()
        check("P6 clearing the character disables Save New and Apply Pose at once",
              not window.save_pose_button.isEnabled() and not window.apply_pose_button.isEnabled())
        check("P6 clearing the character empties the list and restores the guidance",
              window.pose_list.count() == 0 and window.pose_summary.text() == u"Choose a character model.",
              (window.pose_list.count(), window.pose_summary.text()))
        check("P6 no dialog raised", not boxes, boxes)
        check("P6 the Poses tab stayed open throughout (no tab change)",
              not calls and tabs.currentWidget() is window.pose_page, calls)
        # P7: the same selection through CPM's real busy-operation lifecycle (select_model -> guard ->
        # operation_begin -> render -> operation_end), as a user's click on the model list runs it natively.
        token = {"kind": g["PROD_INSTANCE_TOKEN_KIND"], "test": True}
        saved.update((k, g[k]) for k in ("prod_resolve_instance", "prod_identity_from_row"))
        g["prod_resolve_instance"] = lambda tok, ident=None: {"test_row": True}
        g["prod_identity_from_row"] = lambda row: dict(ident)
        window.candidates = [dict(ident, selection_token=token)]
        seen_busy = []
        original_render = window.render
        window.render = lambda *a, **k: (seen_busy.append(bool(window.busy)), original_render(*a, **k))[1]
        try:
            window.select_model(1)
        finally:
            del window.render
        env.settle()
        check("P7 the selection ran inside a busy CPM operation", seen_busy == [True], seen_busy)
        check("P7 after the operation ended: not busy, character selected",
              not window.busy and window.operation is None and window.identity is not None,
              (window.busy, window.operation, window.identity))
        check("P7 Save New is enabled at once after the real selection operation, without a tab change",
              window.save_pose_button.isEnabled() and not calls and tabs.currentWidget() is window.pose_page,
              (window.save_pose_button.isEnabled(), calls))
        window.clear_model_selection()
        env.settle()
    finally:
        g.update(saved)
        tabs.currentChanged.disconnect(counter)


def main():
    env = r15.Env("real", os.path.join(tempfile.gettempdir(), "cpm_pose_page_fixture"))
    QtGui = env.QtGui
    boxes = []
    QtGui.QMessageBox.exec_ = lambda self: boxes.append((self.windowTitle(), self.text())) or 0
    sfm = sys.modules["sfmApp"]
    sfm.HasDocument = lambda: False
    sfm.GetShotAtCurrentTime = lambda: None
    env.click()
    env.settle()
    window = env.slot()
    tabs = window.tabs
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    check("P1 tab order: Body Presets, Expressions, Clothing Fit, Poses", titles[:4] ==
          [u"Body Presets", u"Expressions", u"Clothing Fit", u"Poses"], titles)
    check("P1 Poses page is the fourth tab", tabs.indexOf(window.pose_page) == 3)
    window.review_items = [object()]
    window.review_pending_count = 12
    window.sync_review_tab()
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    check("P1 Review is appended after Poses", titles[-1] == u"Review (12)" and titles[3] == u"Poses", titles)
    sheet = tabs.styleSheet()
    check("P2 compact tab padding, no minimum tab width", u"padding: 6px 8px;" in sheet and u"min-width" not in sheet,
          sheet)
    buttons = [b.text() for b in window.pose_page.findChildren(QtGui.QPushButton)]
    check("P3 Poses page buttons", sorted(buttons) == [u"Apply Pose", u"Save New"], buttons)
    check("P3 no ellipses in any label", not [t for t in buttons + titles if u"..." in t or u"…" in t])
    check("P3 search field", window.pose_search.placeholderText() == u"Search poses")
    tabs.setCurrentWidget(window.pose_page)
    env.settle()
    check("P4 no character: Apply and Save disabled", not window.apply_pose_button.isEnabled()
          and not window.save_pose_button.isEnabled())
    check("P4 no character: summary guidance", window.pose_summary.text() == u"Choose a character model.",
          window.pose_summary.text())
    check("P4 opening the page raised no dialog", not boxes, boxes)
    check("P5 minimum window size unchanged (540 px wide)", window.minimumWidth() == 540, window.minimumWidth())
    window.resize(540, window.height())
    env.settle()
    bar = tabs.tabBar()
    total = sum(bar.tabRect(i).width() for i in range(bar.count()))
    print("tab strip estimate: %d px for %d tabs in a %d px pane" % (total, bar.count(), tabs.width()))
    check("P5 offline estimate: five tabs with Review (12) fit the minimum width", total <= tabs.width() - 4,
          (total, tabs.width()))
    section_selection_refresh(window, tabs, env, boxes)
    try:
        window.close()
    except Exception:
        pass
    passed = sum(1 for _, ok in RESULTS if ok)
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
