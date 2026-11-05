# -*- coding: utf-8 -*-
"""F-01 Pose Library M1, stage D: the Poses page in the real CPM window (real PySide 1.2 / Qt 4.8 under SFM's
Python 2.7.5, through the R15 harness test_cpm_app_r15_namespace_isolation.Env, with sfmApp faked at its boundary).

Checks: tab order (Poses after Clothing Fit; Review appended last), labels without ellipses, the tab style,
the window's unchanged minimum size, the page's widgets and its enablement with no character, a DPI-independent
estimate of the tab strip at the minimum width with "Review (999)" (native verification stays U-1: fonts and styles
differ inside SFM), and the UI consistency pass (names, list headers, the Poses note and actions, Pose Info, Help).

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


def g_qt(window):
    return window.render.im_func.func_globals["QtCore"]


HELP_EXPECTED = [
    u"Getting started",
    u"Choose the character you want to edit. Use Body Presets for body shape and Expressions for facial expressions. "
    u"In Clothing Fit, choose clothing or accessories to fit to that character. Use Poses to save and reuse "
    u"character poses.",
    u"The model list shows models in the shot under the playhead. To use a character from another shot, move the "
    u"playhead into that shot, click Refresh Model List, then choose the character.",
    u"Body Presets",
    u"Save body flexes and bone scaling together as one preset. Apply Preset copies those saved values to the "
    u"selected model.",
    u"Expressions",
    u"Save facial flexes as their own preset. Apply Preset copies those saved facial values to the selected model.",
    u"Clothing Fit",
    u"Match selected clothing and accessories to the selected model's body shape.",
    u"Poses",
    u"Save a character's pose at the playhead with Save New.",
    u"You must be in the Motion Editor to apply poses. Select a saved pose and click Apply Pose. The pose is applied "
    u"at the playhead without changing the character's position or facing.",
    u"Only supported characters and body parts can use saved poses. Use Pose Info to see what a pose includes.",
    u"Preset controls",
    u"Save New creates a new preset from the current values. Update Preset overwrites the selected preset with the "
    u"current values. Add Favorite marks presets for the Favorites only filter. Delete Preset moves the selected "
    u"preset to Trash.",
    u"Undo",
    u"Use SFM's normal Undo command (Ctrl+Z) to reverse applied Body Presets, Expressions, Poses, and Clothing Fit "
    u"changes.",
    u"Why does Review appear?",
    u"Review appears when the Manager cannot classify a flex. For each unrecognized flex, decide whether it belongs "
    u"in Body Presets or Expressions, or should be excluded from presets. Your choices are saved for this model. To "
    u"change one later, select it under Reviewed choices and click Clear Classification.",
    u"Where presets are saved",
    u"Each model has its own preset library. Use Model Info > Open Preset Folder to open it.",
    u"Why are so many flexes in Review?",
    u"The Manager uses the Animation Groups Master to identify Body and Expression controls. If many flexes appear "
    u"in Review, your Master may be missing or out of date. Update it before reviewing controls manually.",
]


def capture_dialog(QtGui, fn):
    """Run fn() with QDialog.exec_ replaced by a capture of the dialog's visible content (no event loop)."""
    seen = []
    real = QtGui.QDialog.exec_

    def fake(self):
        texts = [w.toPlainText() for w in self.findChildren(QtGui.QTextBrowser)]
        labels = [w.text() for w in self.findChildren(QtGui.QLabel)]
        buttons = [w.text() for w in self.findChildren(QtGui.QPushButton)]
        seen.append({"title": self.windowTitle(), "width": self.width(), "height": self.height(), "texts": texts,
                     "labels": labels, "buttons": buttons})
        return 0
    QtGui.QDialog.exec_ = fake
    try:
        fn()
    finally:
        QtGui.QDialog.exec_ = real
    return seen


def section_ui_pass(window, tabs, env, boxes, QtGui):
    """The approved UI consistency pass, in the real window."""
    g = window.render.im_func.func_globals
    check("U1 main window title", window.windowTitle() == u"Character Preset Manager", window.windowTitle())
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    check("U1 tab names", titles[:4] == [u"Body Presets", u"Expressions", u"Clothing Fit", u"Poses"] and
          titles[4].startswith(u"Review"), titles)
    check("U2 no introductory text above the Body Presets and Expressions lists",
          window.body_summary.isHidden() and window.expr_summary.isHidden()
          and window.body_summary.parent() is None and window.expr_summary.parent() is None)
    fit_labels = [w.text() for w in window.fit_page.findChildren(QtGui.QLabel)]
    check("U2 Clothing Fit keeps its instruction",
          fit_labels == [u"Match selected clothing to this model's body shape."], fit_labels)
    pose_labels = [w for w in window.pose_page.findChildren(QtGui.QLabel)]
    check("U3 Poses shows exactly the Motion Editor sentence above the list",
          [w.text() for w in pose_labels] == [u"You must be in the Motion Editor to apply poses."]
          and not pose_labels[0].isHidden(), [w.text() for w in pose_labels])
    # Poses actions: one row of three, built with the preset pages' own button helpers.
    lay = window.pose_page.layout()
    rows = [lay.itemAt(i).layout() for i in range(lay.count()) if lay.itemAt(i).layout() is not None]
    row = [rows[-1].itemAt(i).widget() for i in range(rows[-1].count())] if rows else []
    check("U4 Poses actions are one row: Apply Pose, Save New, Pose Info",
          [b.text() for b in row] == [u"Apply Pose", u"Save New", u"Pose Info"], [b.text() for b in row])
    pairs = ((window.apply_pose_button, window.apply_body), (window.save_pose_button, window.save_body),
             (window.info_pose_button, window.info_body))
    check("U4 the same button styles, heights and focus policy as Body Presets",
          all(a.styleSheet() == b.styleSheet() and a.minimumHeight() == b.minimumHeight()
              and a.focusPolicy() == b.focusPolicy() and a.font() == b.font() and not a.autoDefault()
              for a, b in pairs), [(a.text(), a.minimumHeight(), b.minimumHeight()) for a, b in pairs])
    check("U4 Body Presets and Expressions rows are unchanged",
          [b.text() for b in (window.apply_body, window.save_body, window.update_body, window.favorite_body,
                              window.info_body, window.delete_body)] ==
          [u"Apply Preset", u"Save New", u"Update Preset", u"Add Favorite", u"Preset Info", u"Delete Preset"])
    # Help.
    seen = capture_dialog(QtGui, window.open_help)
    h = seen[0] if seen else {}
    check("U5 Help title", h.get("title") == u"Character Preset Manager - Help", h.get("title"))
    text = (h.get("texts") or [u""])[0]
    paras = [p.strip() for p in text.split(u"\n") if p.strip()]
    check("U5 Help text is exactly the original with the approved Poses changes", paras == HELP_EXPECTED,
          [(i, a, b) for i, (a, b) in enumerate(zip(paras, HELP_EXPECTED)) if a != b][:3] or (len(paras),
                                                                                             len(HELP_EXPECTED)))
    check("U5 Help keeps the GitHub button and the license/author footer",
          u"Download / Update Master on GitHub" in h.get("buttons", []) and
          u"License: CC0 1.0 Universal \u00b7 Author: ChadChan3D" in h.get("labels", []), h.get("buttons"))
    avail = QtGui.QApplication.desktop().availableGeometry(window).height()
    print("Help size %sx%s, usable screen height %d" % (h.get("width"), h.get("height"), avail))
    check("U6 Help keeps its 820 px width; its height is at least 770 and within the usable screen height",
          h.get("width") == 820 and 770 <= h.get("height", 0) <= avail - 40, (h.get("width"), h.get("height"), avail))
    sizing = g["tool_help_preferred_height"]

    class Screen(object):
        def __init__(self, height):
            self.h = height

        def height(self):
            return self.h
    real_desktop = QtGui.QApplication.desktop
    try:
        QtGui.QApplication.desktop = staticmethod(lambda: type("D", (), {"availableGeometry": lambda self, w:
                                                                         Screen(600)})())
        dialog = QtGui.QDialog()
        lay2 = QtGui.QVBoxLayout(dialog)
        browser = QtGui.QTextBrowser(dialog)
        browser.setPlainText(u"\n".join(HELP_EXPECTED * 3))
        lay2.addWidget(browser)
        capped = sizing(dialog, browser, 820)
    finally:
        QtGui.QApplication.desktop = real_desktop
    check("U6 on a small screen Help is capped at the usable height (the text scrolls)", capped == 560, capped)
    # Pose Info: enabled only for a selected pose; read-only details in a dialog, nothing above the list.
    saved = dict((k, g[k]) for k in ("prod_pose_load_registry", "prod_pose_selected_library", "prod_pose_discover",
                                      "prod_pose_rig_class", "prod_pose_registry_select", "prod_pose_browse_eligible",
                                      "prod_resolve_instance", "prod_identity_from_row", "prod_context_token"))
    item = {u"name": u"Arms Up", u"preset_id": u"p1", u"revision": 1,
            u"record": {u"name": u"Arms Up", u"preset_id": u"p1", u"created_at": u"20261104-120000-000000",
                        u"pose": {u"regions": {u"left_arm": {}}, u"source": {
                            u"model_ref": u"models/test/krystal2020.mdl", u"shot_name": u"shot10",
                            u"rig_class": u"krystal-biped"}}}}
    g["prod_pose_load_registry"] = lambda: {}
    g["prod_pose_selected_library"] = lambda ident: {u"char_dir": u"unused", u"character_key": u"k"}
    g["prod_pose_discover"] = lambda char_dir, key, reg: {u"items": [item], u"unusable": []}
    g["prod_pose_rig_class"] = lambda reg, model, checksum: u"krystal-biped"
    g["prod_pose_registry_select"] = lambda reg, mode: {}
    g["prod_pose_browse_eligible"] = lambda sel, rec, cls: [u"left_arm"]
    ident = {"model": u"models/test/krystal2020.mdl", "checksum": 1234, "animset_name": u"Krystal"}
    g["prod_resolve_instance"] = lambda tok, ident=None: {"test_row": True}   # as P7: the guard's context check
    g["prod_identity_from_row"] = lambda row: dict(ident)
    g["prod_context_token"] = lambda *a, **k: {"test_context": True}   # the operation's pinned context (stubbed)
    try:
        window.identity = dict(ident)
        window.selection_token = {"kind": g["PROD_INSTANCE_TOKEN_KIND"], "test": True}
        window.refresh_pose_view()
        check("U7 a pose is listed with no message row", window.pose_list.count() == 1 and
              window.pose_list.item(0).text() == u"Arms Up")
        check("U7 no pose selected: Pose Info and Apply Pose disabled",
              not window.info_pose_button.isEnabled() and not window.apply_pose_button.isEnabled())
        window.pose_list.setCurrentRow(0)
        check("U7 pose selected: Pose Info and Apply Pose enabled",
              window.info_pose_button.isEnabled() and window.apply_pose_button.isEnabled())
        check("U7 the text above the list stays the Motion Editor note (no pose details)",
              window.pose_summary.text() == u"You must be in the Motion Editor to apply poses.")
        window.busy = True
        window.refresh_pose_buttons()
        check("U7 busy: Pose Info and Apply Pose disabled",
              not window.info_pose_button.isEnabled() and not window.apply_pose_button.isEnabled())
        window.busy = False
        window.refresh_pose_buttons()
        info = capture_dialog(QtGui, window.open_pose_info)
        d = info[0] if info else {"status": window.status.text()}
        check("U8 Pose Info opens a read-only dialog with the pose's details",
              d.get("title") == u"Pose Info" and u"Arms Up" in d.get("labels", []) and u"Left arm" in
              d.get("labels", []) and u"shot10" in d.get("labels", []) and
              any(u"Available: Left arm" in t for t in d.get("labels", [])) and d.get("buttons") == [u"Close"],
              d)
        check("U8 Pose Info ended its operation", not window.busy and window.operation is None)
        window.pose_list.setCurrentRow(-1)
        window.identity = None
        window.selection_token = None
        window.refresh_pose_view()
    finally:
        g.update(saved)


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
        rows = [window.pose_list.item(i).text() for i in range(window.pose_list.count())]
        check("P6 the empty-list message names the character, in the list, without a tab change",
              len(rows) == 1 and u"No poses saved for Krystal yet." in rows[0] and not calls, (rows, calls))
        check("P6 the message row is not selectable and selects no pose",
              window.pose_list.item(0).flags() == g["QtCore"].Qt.NoItemFlags and window.selected_pose() is None)
        check("P6 the text above the list stays the Motion Editor note",
              window.pose_summary.text() == g["PROD_POSE_EDITOR_NOTE_COPY"], window.pose_summary.text())
        check("P6 the selected character's pose list was read on selection", window.pose_items_key is not None)
        window.clear_model_selection()
        env.settle()
        check("P6 clearing the character disables Save New and Apply Pose at once",
              not window.save_pose_button.isEnabled() and not window.apply_pose_button.isEnabled())
        check("P6 clearing the character empties the list; the note above it is unchanged",
              window.pose_list.count() == 0 and window.pose_summary.text() == g["PROD_POSE_EDITOR_NOTE_COPY"],
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
    check("P2 uniform tab padding 6px 11px, no minimum tab width",
          u"padding: 6px 11px;" in sheet and sheet.count(u"padding:") == 1 and u"min-width" not in sheet, sheet)
    check("P2 selected-tab styling unchanged", u"QTabBar::tab:selected {\n            background: #454545;\n"
          u"            border-top: 2px solid #7c8f9c;\n            border-bottom: 1px solid #454545;" in sheet, sheet)
    buttons = [b.text() for b in window.pose_page.findChildren(QtGui.QPushButton)]
    check("P3 Poses page buttons", sorted(buttons) == [u"Apply Pose", u"Pose Info", u"Save New"], buttons)
    check("P3 no ellipses in any label", not [t for t in buttons + titles if u"..." in t or u"…" in t])
    check("P3 search field", window.pose_search.placeholderText() == u"Search poses")
    tabs.setCurrentWidget(window.pose_page)
    env.settle()
    check("P4 no character: Apply, Save and Pose Info disabled", not window.apply_pose_button.isEnabled()
          and not window.save_pose_button.isEnabled() and not window.info_pose_button.isEnabled())
    check("P4 no character: only the Motion Editor note above an empty list",
          window.pose_summary.text() == u"You must be in the Motion Editor to apply poses."
          and window.pose_list.count() == 0, (window.pose_summary.text(), window.pose_list.count()))
    check("P4 opening the page raised no dialog", not boxes, boxes)
    check("P5 minimum window size unchanged (540 px wide)", window.minimumWidth() == 540, window.minimumWidth())
    window.resize(540, window.height())
    env.settle()
    bar = tabs.tabBar()
    print("tab strip at this display's DPI (informational): %d px for %d tabs in a %d px pane" % (
        sum(bar.tabRect(i).width() for i in range(bar.count())), bar.count(), tabs.width()))
    # SFM's Qt 4 runs at 96 DPI logical; this machine's display may be scaled, so the estimate measures the labels
    # with the window's font at its 96-DPI pixel size, plus the style sheet's padding, borders and margin.
    font = QtGui.QFont(tabs.font())
    if font.pointSize() > 0:
        font.setPixelSize(int(round(font.pointSize() * 96.0 / 72.0)))
    fm = QtGui.QFontMetrics(font)
    labels = [tabs.tabText(i) for i in range(tabs.count()) if not tabs.tabText(i).startswith(u"Review")] + \
        [u"Review (999)"]
    total = sum(fm.width(t) + 2 * 11 + 2 + 1 for t in labels)
    avail = 540 - 2 * 11 - 2   # the Windows dialog layout margin at 96 DPI (11 px) and the pane border
    print("tab strip estimate at 96 DPI: %d px for %d tabs, %d px available" % (total, len(labels), avail))
    check("P5 DPI-independent estimate: five tabs with Review (999) fit the minimum width",
          len(labels) == 5 and total <= avail, (total, avail, labels))
    check("P5 tabs never elide or shrink their labels", bar.elideMode() == g_qt(window).Qt.ElideNone
          or bar.elideMode() == 0, bar.elideMode())
    section_ui_pass(window, tabs, env, boxes, QtGui)
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
