# F-01 RC4: Save New responsiveness (implemented offline, not native-tested)

**Authority:** the Owner's RC3 finding ("Save New takes about five seconds before the dialog appears, with too little
feedback") and "F-01 RC4 — Astra Ruling and Implementation Authorization" section 7. Kept separate from the
cross-rig change.

## Measured cause (RC3 smoke log, ops 3 and 8)

About 3.4 s of read-only checking runs between the click and the Save dialog for a rigged character:
- the generic Full body inventory (needed for Selected parts), about 1.5 s;
- the structural rig probe, about 1.9 s.

Across both, the instance was read six times and the rig drafted three times. One draft was a pure duplicate:
`prod_body_rig_probe` resolved the profile inside `prod_body_current_time` and then again.

## Change

| Item | Change |
|---|---|
| Feedback | Save New (the interactive flow only) shows "Checking the character before saving." and a busy cursor before the checks. Both end before the dialog opens, and also on cancel or refusal. The label is repainted directly; the event loop is never run, so no re-entrant click is possible. Feedback never fails the action (`ProdWindow.pose_busy_begin` / `pose_busy_end`) |
| Duplicate draft | `prod_body_current_time` takes an already-resolved profile; the probe drafts once, and `prod_body_state` still re-reads and confirms the same description |

Nothing else changed:
- no check was removed, skipped or deferred, and no option or route changed;
- the modal-boundary revalidation and the full capture after the dialog are unchanged.

## Offline evidence

- `test_cpm_app_f01_structural_rig.py`: 314/314 on Python 2.7.5 and 3.10.6. It has 7 new E checks: feedback before the checks; feedback ended before the dialog, after a cancel and after a refusal; one draft plus one confirmation before the dialog; saving still works; no feedback for a named save.
- Harness method lists: the body, scoped and pose-integration suites. Canonical route: `F01_RC4_NEW_METHODS`.
- Full regression against the clean baseline `30a32bf`:
  - the only differences are the intended RC3 and RC4 checks;
  - plus the known environmental r15 item (the CRLF working copy of `cpm_compat_v1_projection.py`, documented at RC3).

**Expected effect:** immediate feedback, and roughly one draft less of waiting. The actual native time still needs to be
observed.
