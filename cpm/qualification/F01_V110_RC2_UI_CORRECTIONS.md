# F-01 v1.1.0 RC2: the Owner's final UI corrections (2026-11-18)

**Authority:** "F-01 RC1 — Owner Results and Final UI Corrections". Presentation only. The RC1 smoke verdict is
recorded separately (`F01_V110_RC1_NATIVE_SMOKE_RESULTS.md`: PASS, restored) and is not changed by this revision.

**Status: RC2 locally verified (unsigned).** Not installed, not natively viewed, not signed, not released.

## 1. The three corrections (CPM `32183508…` → `7aa0fc4e159756f288a26819d9f8400f6f665bd797e5aff1c03ffac3a87eba47`, 1,479,697 B)

| # | Correction | Change |
|---|---|---|
| 1 | Save Pose size | `prompt_pose_scope`: the dialog's Full body size is recorded the first time Selected parts is chosen (before the picker appears); switching back to Full body hides the picker and restores exactly that size, so no empty space is left. Selected parts sizing (the eleven-row picker) is unchanged |
| 2 | Pose Info order | `prod_pose_info_view`: Name, Type, Saved, Updated (only when it differs, beside Saved), Includes, Not included, Model, Model path, Source shot, Source project. The Hip position row is removed. The Saved Values tree is unchanged |
| 3 | Helper sentence | `prod_scope_summary`: the Save New summary no longer adds "Helper bones that SFM moves automatically follow the pose and may look slightly different." `PROD_SCOPE_HELPER_NOTE` stays defined, but nothing shows it. The H1 helper admission and every protection are unchanged |

No record format, compatibility, admission, Save, Apply, Undo, transaction or recovery code changed. The diff touches
only those three functions plus one comment.

## 2. Tests

| Suite | Result |
|---|---|
| `test_cpm_app_f01_scoped_page` (2.7.5) | **18/18**; new D10: Full body → Selected parts (the dialog enlarged) → Full body gives back exactly the original size, twice. Teeth: without the restore, D10 fails (440 px → 1216 → 1216 → 1516) |
| `test_cpm_app_f01_scoped` (2.7.5, 3.10.6) | 487/487; UI.1, UI.1b, UI.4, UI.7 and DI01 updated to the new order and to no Hip row. DI01 still rejects any placement promise |
| `test_cpm_app_f01_pose_page` (2.7.5) | 123/123; U8 and V4 updated to the new order |
| `test_cpm_app_f01_helper` (both) | 78/78; the summary check now requires no helper sentence, and the helper admission checks are unchanged |
| Every other CPM suite (both interpreters) | identical to the RC1 baseline (the pre-existing rows in `F01_V110_RC1_INTEGRATION.md` section 3 are unchanged) |

Kits: the RC1S kit test `P.installed_build_is_the_rc1_cpm` now fails because it pins RC1's CPM `32183508…` to the
repository. That is expected, as with the other historical kits. Its evidence and verdict are unchanged.

## 3. Package (`release/v1.1.0-rc2/`)

| Item | Value |
|---|---|
| Spec | `SOFTWARE_SPEC.json` `9d15a387…` (33 files; RC1's spec with the new CPM identity and RC2 text) |
| Tool | `rc2_tool.py` `918c237c…`: RC1's `rc_tool.py` unchanged, with the RC2 spec and package name; `rc.template.json` `28e2c716…` |
| Unsigned inventory | `b547c6dd2c8c7046141480951c40f89579daf6b741aaf4fb3ad5cb2b964f2cf8` |
| Unsigned package (outside Git) | `E:\SFM_U0B_Scratch\f01-v110-rc2\package\SFM.Character.Tools.v1.1.0-rc2-UNSIGNED.zip` `46be7dbf375127050f433c73d442143497bec12bd7d28dc50f57765cccc76577` (1007 entries; an independent rebuild in `f01-v110-rc2-repro` is byte-identical) |
| Readiness | `rc2_tool.py verify`: **RC VERIFY PASS** (`RC_VERIFY.json` `7d9fac89…`) for package, updater, version, installer and rollback, as for RC1 |

## 4. Remaining before release (Owner authorization each)

1. **Optional:** a native look at the three corrections (Save dialog Full body ↔ Selected parts; Pose Info). This
   could reuse the RC1S kit with RC2's files. These are presentation-only changes with an automated size test.
2. Then the sequence in `F01_V110_RC1_SMOKE_PREPARATION.md` section 5, applied to RC2:
   - the v1.1.0 README;
   - signing;
   - the updater and Workshop installer checks on the signed package;
   - merge, tag and publication.
