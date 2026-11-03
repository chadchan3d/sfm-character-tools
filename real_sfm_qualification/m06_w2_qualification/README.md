# M-06 W2: native qualification instrumentation and deferred-path coverage

**Status: Astra's final W2 corrections (compressed data, supported Apply representations, Abort configuration handoff) accepted; the configuration-digest validation correction is implemented and qualified offline, awaiting Astra's review.** Nothing here has been run in SFM. There is no production change: the accepted W1 application `fd853661…` is byte-identical. Native qualification is **not** claimed. The corrections are traced in `W2_DESIGN_MAP.md` § "Astra-required corrections" and § "Astra's final W2 review".

## Contents

| Path | Purpose |
|---|---|
| `instruments/m06w2_core.py` | Strict read-only observation core, with four-state reads and identities (shared, exec-free loading) |
| `instruments/M06_Qualification_Observer.py` | Observer (format v2): one exclusively created observation per run. Staged twice, as `M06_Qualification_Observer.py` (`m06w2_config.json`) and `M06_Deferred_Observer.py` (`m06w2_deferred_config.json`) |
| `instruments/M06_Qualification_Abort_Injector.py` | Abort Injector v3: pinned to `fd853661`; records created graph elements and attachments; writes the watch list |
| `native/M06_Native_Probe.py` | Read-only prerequisite probe (v2): identity APIs, the selected instance's W1 token, clip topology, presence agreement and coverage, Undo forms |
| `native/M06_Deferred_Fixture_Preparation.py` | Deferred fixture preparation: requires the qualified mode-3 graph, changes one stored source on a verified disposable copy, and runs the `prepared` comparison in-session before any Save As |
| `tools/compare_obs.py` | Independent fail-closed comparator with declared invariants |
| `tools/compare_probes.py` | Probe acceptance, including selected-instance token invalidation on reload |
| `tools/scan_deferred_fixture.py` | Offline read-only binary-DMX scan of the M-05 fixture |
| `tools/stage_instruments.py` | Offline staging for a later native session (one Observer per configuration, plus `compare_obs.py`); never installs |
| `config/*.template.json` | Run configurations, filled from the offline fixture scans |
| `evidence/deferred_fixture_scan.json` | Scan of the accepted M-05 fixture (file unchanged by the read) |
| `tests/` | Offline fake DME, the suite, the mutation check, and `counterexamples.py` (Astra's counterexamples against any W2 tree) |
| `OBSERVER_SCHEMA.md`, `W2_DESIGN_MAP.md`, `procedures/NATIVE_PROCEDURES.md` | Contracts, traceability, native procedures and stop conditions |

## Running

- **Suite** (Python 2.7.5 and 3.10.6): `python -B tests/test_m06w2.py [RESULTS.json]`. Set `M06W2_M05_FIXTURE` to the M-05 fixture to include the real-fixture scan test.
- **Mutation check:** `python -B tests/mutate_w2.py RESULTS.json`.
- **Counterexamples:** `python -B tests/counterexamples.py W2_ROOT RESULTS.json SCAN_FIXTURE.dmx`, once for the corrected tree (first: it writes the output-mode-1 scan fixture) and once for the previous W2 tree.

## Native obligations (open until demonstrated natively)

1. **Unique IDs.** `str(GetId())` is a stable, distinct content rendering, and `IsUniqueIdValid`, `IsUniqueIdEqual`, `GetElementId` and `GetElement` behave as assumed (probes 1 and 2).
2. **Reload invalidation.** A same-session reopen of the same document invalidates the selected instance's W1 token (a readable component differs) even though persisted ids survive (probe 3).
3. **Clip topology.** Channels-clip topology and the channel attribute names (probe 4).
4. **Real `render()`** with duplicate same-model instances (procedure §5).
5. **Presence agreement.** `HasAttribute()`/`GetAttribute()` agree for optional channel attributes, and the Undo bindings' `False`/empty forms are as assumed (probe 6).
6. **Abort destruction.** `AbortUndoableOperation` makes the created graph elements, including the created channels' logs and layers, unresolvable through `GetElement(handle)`. The comparator requires this. If natively they stay resolvable but detached, the run stops for adjudication.
7. **Deferred fixture survival.** Coherent native evaluation of the selected Muscles flex, and survival of the prepared source/key disagreement across Save As and reopen (§3).
8. **The deferred native sequence** commit → pending → deferred verification → verified, under one operation id (§4).
9. **Observer v2 log and layer reads.** `IsEmpty()`, the channel's `log` attribute, `bookmarks`, `curveinfo`, layer `times`/`values`/`curvetypes`/`compressed` read natively as modelled. If one does not, the Observer reports the observation insufficient and the run stops for adjudication.
10. **EMPTY-origin write.** CPM's `ClearAndAddSampleAtTime(0)` natively leaves the layer's `curvetypes`, `compressed` block and `curveinfo` as they were. The comparator keeps them protected; a native difference is a mismatch and the run stops for adjudication.
11. **Configuration handoff.** The Observer and the Abort Injector natively load the same staged `m06w2_config.json`.
12. **Observation stability.** Exact equality of observations of a static scene across idle intervals. Native jitter makes the comparisons refuse (fail closed).
