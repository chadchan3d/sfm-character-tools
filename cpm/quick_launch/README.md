# CPM Quick Launch (optional component)

An optional **CPM** text button in SFM's Animation Set Editor toolbar. It opens Character Preset Manager through the
existing, unchanged R15 Scripts-menu launcher. Base CPM does not depend on it, and the Scripts-menu entry remains the
fallback.

**Design authority:** the Owner-approved *CPM Quick Launch Construction Blueprint* (Astra), with the supporting
adversarial audit and runtime addendum, from the designer handoff of 2026-10-18. Stages QL-1 to QL-3 are authorized
separately. This component is outside the Control Group Updater's L-series and its software inventory.

**Status:** QL-1 constructed and verified offline, including the corrections from Astra's adjudication of the QL-1
discretionary choices (recoverable recreation budget; waiting instead of suspending on incomplete or ambiguous
toolbars). QL-2 (real SFM) and QL-3 (optional packaging and installation) are not started.

## Files

| Responsibility | Repository | Installed, relative to `<SFM game>` |
|---|---|---|
| Autoinit bootstrap | `cpm/quick_launch/autoinit/ChadChan3D_CPM_ASE_Button.py` | `usermod/scripts/sfm/autoinit/ChadChan3D/ChadChan3D_CPM_ASE_Button.py` |
| Private implementation | `cpm/quick_launch/cpm_ase_quick_launch.py` | `usermod/scripts/ChadChan3D_CPM/cpm_ase_quick_launch.py` |
| Offline tests | `cpm/quick_launch/tests/test_cpm_ase_quick_launch.py` | not installed |

The bootstrap path must stay stable: Autoinit Manager records disablement by path.

## Architecture

```text
Autoinit (shared globals)
  -> bootstrap: one function, deleted in finally; leaves no names behind
  -> private module chadchan3d_cpm_ase_quick_launch (ABSENT -> LOADING -> READY, hash-identified, never reloaded)
  -> one controller per SFM process (QObject child of QApplication, retained by the module)
  -> one QToolButton "CPM" (object name chadchan3d_cpm_ase_button) parented to the native upper bar
  -> click: unchanged installed R15 launcher, compiled and run in a fresh dictionary
  -> CPM's existing load-once, reuse and refusal behavior
```

- **Bootstrap:** resolves paths from `sys.executable`, compiles the exact hashed bytes with `dont_inherit=True`, and
  makes no `sys.path` changes. A rerun reuses the ready module and asks the controller for one refresh. A foreign,
  loading or malformed module, or changed installed bytes, is refused until SFM restarts.
- **Controller states:**

  | State | Behavior |
  |---|---|
  | `WAITING` | No complete, uniquely supported toolbar yet; one 1-second discovery timer, quiet |
  | `ATTACHED` | Discovery stopped; event filters on the editor, the upper bar and its widgets drive one coalesced layout timer |
  | `SUSPENDED` | A positively unsupported toolbar or an unexpected error; no automatic retry. A rerun from Autoinit Manager rediscovers once after an unsupported toolbar; after an error, SFM must be restarted |
  | `STOPPING` / `STOPPED` | Reached on `aboutToQuit`; timers stopped, owned filters and connections removed, owned button and notice released |
- **Supported hierarchy:** exactly one `CQAnimationSetEditor` named `QAnimationSetEditor`. It must have exactly one
  `CQEditorUpperBarWidget` direct child with no layout, which in turn holds exactly one `CQTabbedToolButton` with
  tooltip `Add`.
- **Incomplete versus unsupported:**
  - **Waiting:** no editor yet; an editor without its upper bar or native Add yet; or ambiguity (several editors,
    upper bars or Add candidates). Nothing is injected, and attachment happens automatically once a complete, unique
    toolbar exists.
  - **Unsupported:** only an upper bar with a layout manager. It produces one console line pointing to the Scripts
    menu, and no dialog.
- **Losing the toolbar:**
  - **Destroyed:** the editor's and upper bar's `destroyed` signals invalidate the attachment immediately, without
    inspecting the dying objects, and return to `WAITING`. Leftover filters on surviving objects, and a dead button
    reference, are released on the next discovery tick.
  - **Structure lost or replaced without destruction:** for example, Add removed or a second candidate added. The
    controller detaches safely, removing its button from that bar, then waits or attaches to the replacement.
- **Placement:**
  - The vertical band comes from the native Add button.
  - Occupied space is every direct child widget that is explicitly visible (`isVisibleTo`), intersects the band and
    isn't a window. This includes unfamiliar controls; CPM's own button is excluded.
  - CPM takes the first free interval at or after the Add position, with 5 px clearance from every occupied span.
  - It is hidden when no complete interval fits and shown again when one does.
  - Geometry and visibility change only when they differ. A reentrancy guard ignores events caused by CPM's own
    placement.
  - No other control is moved, resized, hidden, reparented or deleted, and no layout is installed on the row.
- **Ownership:** by recorded object identity, never by name alone. Foreign widgets are never removed, renamed or
  reclaimed.
  - **Reserved name in use:** a foreign widget with the reserved name is left untouched and treated as occupied space,
    and CPM's button isn't added while it is present. Recovery is event-driven, with no extra polling. If that widget
    is removed, the button is added at once. If it is only renamed, which Qt reports to no one, the button is added at
    the next toolbar event or Autoinit refresh.
  - **Moved elsewhere:** a still-valid owned button moved elsewhere by another script remains owned. It isn't moved
    back or deleted, and no second button is created. If it is returned to the toolbar, it is placed again; if it is
    destroyed, that counts as a removal.
  - **Removed by someone else:** the owned button is recreated up to 3 times for an unchanged toolbar configuration.
    The budget rearms after a genuine change to the non-CPM toolbar children (a widget added or removed), on
    attachment to a new toolbar, or on an explicit Autoinit refresh. CPM's own creation, removal, geometry and
    visibility changes never rearm it, and neither do sibling geometry, visibility or stacking changes. When the
    budget runs out, one console line points to the Scripts menu and to rerunning the button from Autoinit Manager.
- **Launch:**
  - A synchronous guard ignores reentrant clicks.
  - An unreadable, uncompilable or raising launcher produces one console diagnostic and one reusable, controller-owned
    non-modal notice. The notice isn't shown over an active modal dialog. Its text is: "Character Preset Manager
    couldn't be opened. Try its Scripts-menu entry. If that also fails, repair the CPM installation."
  - R15 shows its own refusals.
  - Nothing CPM-related is imported or loaded before a click.

## User help

> If the toolbar is too narrow, widen the Animation Set Editor or open Character Preset Manager from Scripts.

> Turn off the CPM button in Autoinit Manager, then restart SFM.

## Offline verification (QL-1)

```text
<SFM game>/sdktools/python/2.7/win32/python.exe -E -B cpm/quick_launch/tests/test_cpm_ase_quick_launch.py --phase=run
py -3 cpm/quick_launch/tests/test_cpm_ase_quick_launch.py --phase=static
```

- **Production gate:** SFM's embedded Python 2.7.5 with real PySide 1.2 / Qt 4.8. Each scenario runs in its own child
  interpreter.
- **Off-screen hierarchy:** subclasses carrying the observed native class names model the editor.
- **Autoinit:** modelled as one shared host dictionary.
- **Clicks:** run the actual R15 launcher against a stub CPM implementation.
- **Python 3.10:** runs the static checks only.

Mocks do not qualify real SFM widgets, Autoinit itself or Extended ASE coexistence; those belong to QL-2.
