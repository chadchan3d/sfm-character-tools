# M-06 W2: native qualification procedures (PREPARED, NOT EXECUTED)

Nothing in this file has been run in SFM. Every step needs a separate Owner authorization for a native session. The candidate is the accepted W1 application, `fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d`. Offline fake behaviour is never a substitute for native evidence.

## 0. Boundaries for every native session

- Protected originals are never opened for editing and never saved:
  - the original session;
  - the M-06 multi-instance fixture (`4d7288a7…`);
  - the M-05 fixture (`fa9a0a46…`).
- Work only in **new disposable copies**.
- **Stop** on any of the following:
  - an Observer result of INSUFFICIENT;
  - a comparator verdict other than PASS;
  - a CPM message other than the one expected;
  - wrong-instance access;
  - an unexplained peer change;
  - unverified recovery;
  - a native API that behaves differently from these procedures.

  Preserve the evidence and do not retry or repair anything live.
- Run the Observer only while CPM is idle. It is read-only, never moves the playhead, and writes one exclusively created file.
- After SFM closes:
  - restore the recorded installation and preset-library baseline;
  - verify the protected inventories independently;
  - carry over attempt 3's `install.py`, `restore.py` and `integrity.py`, unchanged except for re-pinning to `fd853661`.

## 1. Staging (offline; can be done now)

1. Fill in the placeholders in `config/m06w2_config.template.json` and `config/m06w2_deferred_config.template.json`: the paths, and the protected-file hashes measured that day.
2. Run `python -I tools/stage_instruments.py <config> <new staging dir> <deferred config>`.
3. The tool:
   - refuses any leftover placeholder and any CPM pin other than `fd853661`;
   - substitutes `INSTRUMENT_DIR`;
   - stages **one Observer per configuration** (the configuration-selection mechanism):

     | Staged Observer | Reads | Fixture |
     |---|---|---|
     | `M06_Qualification_Observer.py` | `m06w2_config.json` | multi-instance fixture, shot12 (§2, §5) |
     | `M06_Deferred_Observer.py` | `m06w2_deferred_config.json` | deferred fixture, shot10 (§3, §4) |

     Each staged configuration records its own `config_name`. An Observer, or the preparation script, whose configuration names a different file refuses. Every observation records the `config_name` and `config_sha256` it used, and the comparator refuses to compare observations taken with different configurations;
   - stages `compare_obs.py` beside the preparation script, which runs it in-session (§3);
   - records the instruments' planned installed paths;
   - writes `STAGED_SHA256SUMS.txt`.

Installing the staged folder as **Scripts > M06 Qualification** is a native-session step.

## 2. Ordinary M-06 qualification

This uses the multi-instance fixture: target `krystal20202new`, same-model peer `krystal20201alt`, shot12. Every observation in this section is taken with **M06_Qualification_Observer**.

Each row is one observation point, followed by the declared comparison: `python -I tools/compare_obs.py <invariant> A B [spec]`.

| Step | Observation | Comparison |
|---|---|---|
| Fresh session; CPM closed | obs-A | Baseline. It must be **complete**. |
| Body Save | obs-B | `unchanged` A→B. Then `preset` A + the saved file: every bone, and full-precision effective values. |
| Update | obs-C | `unchanged` A→C |
| Apply of the baseline preset (no-op) | obs-D | `unchanged` A→D, including the required Undo fields |
| Changed Apply | obs-E | `apply` D→E, with a spec declaring, per changed flex side, the `effective` value (and `stored` when the source changes, which CPM's `write_side` always does for an EMPTY side); per bone, the physical `scale`, the scale `control_value` and `existing`/`created` graph; and the owned `undo_desc`. Only the declared sides' value fields may change. A declared EMPTY side may become exactly one key at time zero holding the declared value (CPM's `ClearAndAddSampleAtTime(0)` on the same layer). The opposite stereo side, log identities, defaults and metadata, compressed data, the graph's identities, expression, endpoints, memberships and the whole output log stay compared. The scale is verified as `lerp(control_value, lo, hi)` against the expression result and the physical bone; a mode-3 output must keep its empty log with `usedefaultvalue` False (the accepted M-05 graph). |
| Ctrl+Z | obs-F | `undo` D→F (spec: `redo_desc`) |
| Ctrl+Y | obs-G | `redo` E→G (spec: `undo_desc`) |
| Arm the Injector, then Apply a preset that creates a missing scale graph (mode-1 creation case) | `injector_*_fired.json`, then obs-H | `aborted` G→H, with the spec set to the **complete** fired record. The comparator re-derives the created controls, operators, channels, logs and layers from the record's baseline and in-transaction observations and requires them to reconcile exactly with the recorded list; the baseline must be obs-G's state. Every created element must be detached **and** no longer resolvable; authored state and the required Undo fields restored; no peer change recorded or observed. |
| Save As a disposable copy, quit, reopen | obs-I | `reopened` G→I (spec: `document_path` of the copy) |

The Injector refuses to arm when:

- its configuration does not name itself `m06w2_config.json` (it records that verified identity in its baseline and in-transaction observations; obs-G and obs-H must be taken with **M06_Qualification_Observer**, the same configuration);
- the installed CPM is not `fd853661`;
- the baseline observation is insufficient.

Equal counts or the absence of control names never establish removal. The comparator checks element identities and resolvability. A truncated or contradictory inventory is INSUFFICIENT EVIDENCE, never a smaller removal obligation.

## 3. Deferred-verification fixture preparation (M-05 fixture, shot10 / Krystal)

Offline evidence, available now: `evidence/deferred_fixture_scan.json`, produced by `tools/scan_deferred_fixture.py` from a read of the M-05 fixture. The file was unchanged before and after (`fa9a0a46…`).

- **Existing graph:** the qualified mode-3 graph `bip_head_scale` → `DmeExpressionOperator` → `bone 55 (bip_head)` `scale` is intact. Its physical scale is 1.1299999952.
- **Qualifying flexes:** four Body flexes have mode 3, one layer and one key at time zero: Breastsize, Muscles, slim and toraxwide.
- **Selected:** Muscles. Its stored value and key are both 0.35467979311943054. The proposed stored source is `0.6046798229217529`: distinct, finite, inside [0, 1] and float32-exact.

**Native steps (authorized session):**

1. Copy the M-05 fixture byte for byte to `m06w2_deferred_disposable.dmx`, and verify both hashes. The original is never opened.
2. Open the copy in SFM, set the playhead in shot10, and run **M06_Deferred_Fixture_Preparation**. It refuses, and changes nothing, unless all of these hold:
   - its configuration is the staged deferred configuration (`config_name` `m06w2_deferred_config.json`);
   - the document is that copy, and both hashes are verified;
   - a complete baseline observation exists, and it passes the comparator's own sufficiency check;
   - Muscles natively has mode 3, one layer, one key at time zero, a stored value equal to the key, **and coherent native evaluation**: the log value at the current time equals the key and the destination `flexWeight`;
   - the `bip_head` graph is the **qualified mode-3 graph**: exactly one graph on the bone, every input channel **and the output channel** mode 3, the output writing that bone's `scale`. A graph with output mode 1 refuses.

   After the Owner confirms, it sets **only** the control's `value`, inside one labelled Undo entry, and records the before and after observations.
3. In the same run, the script executes `compare_obs.py prepared` against the before and after observations, with `{"literal": "Muscles", "stored": 0.6046798229217529}`. It must PASS, which proves:
   - nothing else changed;
   - the representation is now `STATIC_PLAY_ONE_KEY_ZERO`;
   - the channel is the destination's sole writer and no channel writes the control;
   - the graph is the untouched qualified mode-3 graph.

   **Only on PASS** does the script write a `prep_*_verdict.json` and tell the Owner to Save As. On any other verdict it writes a stop record and shows **DO NOT SAVE**: close the disposable copy without saving and stop. Re-run the same comparison offline (`python -I tools/compare_obs.py prepared prep_before prep_after SPEC`) and confirm the same PASS.
4. **File > Save As** `m06w2_deferred_prepared.dmx`, then quit SFM. Restart, open the saved copy, set the playhead in shot10, and run **M06_Deferred_Observer** (never M06_Qualification_Observer, which reads the shot12 configuration).
5. Run `compare_obs.py reopened prep_after reopened '{"static_play": ["Muscles"]}'`. It must PASS: the source/key disagreement survived the reload, the admission conditions still hold, the existing graph is still input and output mode 3, and all other authored state is unchanged.

**Stop conditions.** Stop fixture preparation, and do not broaden the mutation, if any of these occur:

- the scan or the native preparation finds no qualifying flex, or no intact mode-3 graph (input **and** output mode 3);
- the in-session `prepared` comparison is not PASS (do not save);
- the evaluation is incoherent;
- reload removes the representation (`reopened` fails);
- any comparison is not PASS.

## 4. Deferred-verification qualification (after §3 passes)

Every observation in this section is taken with **M06_Deferred_Observer**. The test preset changes both the admitted Muscles flex and the physical value of the **existing** `bip_head` mode-3 scale. Make it with CPM's own Save from a deliberately prepared state, or from the attempt-3 `make_test_presets.py` method re-pinned to this fixture.

Observe this native sequence:

**native commit → verification-pending → deferred verification → verified terminal outcome**

| Evidence | Requirement |
|---|---|
| CPM log | The Apply logs `outcome='verification-pending'`, then exactly one deferred verification with outcome `verified`, under the **same operation id** (operation-identity continuity). There is no second Apply and no retry. |
| obs before → obs after | `apply` with Muscles `effective`, `bip_head` `{"scale": …, "control_value": …, "graph": "existing"}` and the owned `undo_desc`. The existing graph's element identities, topology, expression, endpoints, modes and log metadata are preserved (never replaced); the scale control source, the expression input and result, the output and the physical scale are each checked against the declared values. |
| Ctrl+Z / Ctrl+Y | `undo` restores **both** the flex and the scale in one Undo. `redo` re-applies both. |

A mode-1 graph creation does not satisfy this case, and neither does an offline call of the deferred function.

## 5. Native prerequisite probes (read-only)

| # | Probe | Acceptance (`tools/compare_probes.py`) |
|---|---|---|
| 1 | `str(GetId())` rendering | Stable across two reads and the registered wrapper; distinct between elements; content, not a pointer repr |
| 2 | `IsUniqueIdValid`, `IsUniqueIdEqual`, `GetElementId`, `GetElement` | Available; `bool` results; the registered and live ids agree; distinct elements compare unequal |
| 3 | Same-session reload: run the probe, **File > Open** the same document in the same SFM session, run it again | Both probes must be complete: every component of the **selected instance's** W1 token readable (document key, the current shot's `GetFileId()`, shot key, the configured target animation set's key, its game model's key, model and checksum). An unreadable component is a **FAIL** (never taken as invalidation). The token is invalidated when the file id or a document, shot, selected-animation-set or its game-model (type, handle, id) key differs, with the same model and checksum. Peers are not part of the token, so a peer-only change is a **FAIL**. All components identical is a **FAIL**, reported to Astra. |
| 4 | Channels-clip topology | `channelTrackGroup` › `animSetEditorChannels` › `DmeChannelsClip` children, with the selected instance's control channels in exactly one same-named clip |
| 5 | Real `render()` with two same-model instances (UI procedure) | In CPM on the multi-instance fixture: select `krystal20202new`, then `krystal20201alt`, then the first again. The log must show each selection's own scope and live signature. Save from each must capture only that instance, which the Observer `unchanged` checks on the other instance confirm. |
| 6 | `HasAttribute()` / `GetAttribute()` agreement for `channel`, `leftvaluechannel`, `rightvaluechannel`, `positionChannel`, `orientationChannel` | Every control is `has=True` with an attribute, or `has=False` with `AttributeError`/`None`. Anything else is a disagreement. Coverage must be complete and nonempty: every attribute recorded on every examined control, more than zero controls, no animation set with unreadable controls. |

The probe also records the Undo bindings' `False` and empty forms. These remain native uncertainties until the probe has been run and accepted.
