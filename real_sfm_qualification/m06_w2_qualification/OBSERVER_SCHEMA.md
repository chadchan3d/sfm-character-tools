# M-06 W2 Observer v2: observation schema and required-field contract

Format: `M06W2-observation-v2` (core `m06w2-core-v2`). The core is `instruments/m06w2_core.py`, and one JSON file is written per run. The comparator, `tools/compare_obs.py`, is written independently of the core and checks this contract. It validates the nested evidence itself: the Observer's `complete` flag is necessary, never sufficient.

Changes from v1 (Astra's W2 corrections): the log and layer evidence below, the channel-log relationship, `IsEmpty()`, curve and bookmark metadata, raw and compressed key arrays, the configuration name, the accepted-W1 CPM identity, and the created logs and layers in the injector's inventory.

## Value states

Every native read is one of four states:

| State | Meaning |
|---|---|
| `{"s": "present", "v": value}` | The attribute exists and was read. Element values are identity records. |
| `{"s": "null"}` | The attribute exists and holds a null element reference. |
| `{"s": "absent"}` | The attribute verifiably does not exist: `GetAttribute` raised `AttributeError` or returned `None`, **and** `HasAttribute` returned exactly `False`. |
| `{"s": "unreadable", "e": reason}` | Anything else, including an accessor failure, a presence disagreement, a non-`bool` presence result, a non-finite number or an unrenderable value. |

Post-abort watch entries may additionally be `{"s": "gone"}`: `GetElement(handle)` returned `None`.

**An exception never becomes an apparently valid empty collection or a neutral value.** Every required unreadable read is listed in `insufficient`.

## Identity record

`ident(element)` is `{"type", "name", "handle", "id"}`. Each part is read natively:

- `GetTypeString()`
- `GetName()`
- `GetHandle()`, as an integer (`bool` is not accepted)
- `str(GetId())`

The `id` text must be a content rendering. Empty, `<…>` or `at 0x` renderings are unreadable.

## Record structure

| Key | Contents | Required |
|---|---|---|
| `format`, `core`, `label`, `python`, `config_name`, `config_sha256` | Instrument identity, and the configuration file the Observer was staged for (`m06w2_config.json` or `m06w2_deferred_config.json`) | yes |
| `declared` | `shot`, `target_animset`, `peers`, `body`, `nonbody`: the scope the comparator holds the record to (§ Completeness) | yes |
| `context_begin`, `context_end` | Document root identity, file id, document path, shot identity and head time. Read before and after; they must be identical. | yes |
| `integrity` | Each protected file `{expected, actual, match}`; instrument file hashes; `cpm`: the installed CPM hash. The configuration must pin the accepted W1 hash `fd853661…`, and the installed file must equal it; otherwise `cpm` is unreadable or mismatched and the observation is insufficient | yes |
| `channels_clips` | Every shot channels clip (track groups → tracks → children) with its channel identities: the channel-container membership | yes |
| `target` | Animation-set record (below) | yes |
| `peers` | Animation-set record for each declared peer: a distinct, same-model instance | yes |
| `unresolved_channels` | Channels whose endpoint or attribute is unreadable. They may write anything, so this must be empty. | yes |
| `undo` | `enabled`, `can_undo`, `can_redo` (exact `bool`); `undo_desc`, `redo_desc` (text); `item_count` (diagnostic, not required) | yes |
| `watch` | After an abort: whether each created element is still resolvable (`gone` or an identity) | yes (may be empty) |
| `insufficient` | Reasons the observation is insufficient | yes |
| `complete` | `true` only when `insufficient` is empty | yes |

### Animation-set record

| Key | Contents |
|---|---|
| `identity` | Animation set, game model, `modelName`, and checksum (`GetStudioHdr().checksum`, an integer) |
| `controls`, `operators` | The animation set's membership, as identities |
| `control_groups` | `[{"group": {id, name}, "control": {id, name}}]` over the whole `rootControlGroup` tree |
| `flex`, `nonbody` | One record per **declared** literal (exactly one control is required). It holds the `MONO` or `STEREO` shape and each side's record. |
| `transform_controls` | Each `DmeTransformControl`: `valuePosition`, `valueOrientation`, and the position and orientation channels with their channel views |
| `bones` | **Every** bone transform of the game model: index, name, transform identity, `scale` state and value, all writers, and `scale_writers` |
| `graphs` | One record per scale writer: output channel view, operator and its `expr`/`lo`/`hi`/`value`/`result`, and input channel views with the source control's `value`/`defaultValue` |

### Side record (one flex side)

Each side record holds:

- `stored`: the source value;
- `channel`: the channel identity;
- `mode`, `from`, `from_attribute`, `to`, `to_attribute`;
- `log`, each field required:
  - `log`: the identity `GetLog()` returned; `channel_log_attribute`: the channel's `log` attribute, which must be the same element;
  - `usedefaultvalue`, `defaultvalue`, `bookmarks`, `curveinfo` (element reference, or verified absent);
  - `is_empty`: `IsEmpty()`, which must return a `bool`;
  - `layer_count` and `layers`; each layer: identity, `key_count`, `keys` `[ticks, value]`, the raw `times` and `values` arrays (which must agree with the keys), `curvetypes`, `compressed` and `curveinfo`;
    - `compressed` is one of four distinguished states: **verified absence** (`absent`); **valid empty data** (`{length: 0, sha256: <SHA-256 of zero bytes>}`); **non-empty data** (`{length: n > 0, sha256: <64 hex>}`); or **unreadable**, which makes the observation insufficient. Any other record is malformed and is INSUFFICIENT EVIDENCE. Compressed data is protected state: no invariant treats it as an authored value, so any change to it is a mismatch;
  - `evaluated`: the native value at the channel's current time (finite), and `current_ticks_transient`, which is not compared;
- `clips`: the channels clips holding the channel;
- `destination_value`;
- `destination_writers` and `control_writers`, as channel identities;
- `representation`, which is one of:
  - `EMPTY`: no key **and** `IsEmpty()` is `True`. Its effective value is the stored source, which must agree (within CPM's 1e-5) with the evaluation and the destination;
  - `ONE_KEY_ZERO`: one key at time 0, equal to the stored value;
  - `STATIC_PLAY_ONE_KEY_ZERO`: mode 3, one layer, one key at time 0, with the key equal to the evaluated and destination values but different from the stored value, **and** CPM's supported metadata (`flex_static_play_admitted()`): no `curveinfo` on the log or layer, no per-key `curvetypes`, and an empty or absent `compressed` block. `EMPTY` and `ONE_KEY_ZERO` carry no compressed-data rule in production, so the W2 instruments impose none;
  - `OTHER`.

### Scale-writer rule (corrected)

A bone's `scale_writers` are only those channels whose `toElement` is that exact bone transform (same handle and id) **and** whose `toAttribute` is exactly `"scale"`. Position and orientation channels are listed in `writers` but are not scale writers. A channel with an unreadable endpoint or attribute is never silently excluded: it is listed in `unresolved_channels`, and the observation is insufficient.

## Completeness

The comparator returns INSUFFICIENT EVIDENCE, and never PASS, when any of these holds:

- a required top-level or nested field is missing (no defaults), including every log, layer and evaluation field above, on the target, the peers and every graph input and output;
- the nested evidence is inconsistent: a layer count or key count that does not match, raw arrays that disagree with the keys, a channel `log` attribute that is not the `GetLog()` element, a non-`bool` `is_empty`, a non-finite evaluation, or a claimed `representation` that the comparator does not re-derive from the evidence;
- a flex side's channel, or a graph channel, is in no channels clip; a graph's output does not write its bone's `scale`; a graph input has no source control;
- `integrity.cpm` is not the accepted W1 candidate (`actual == fd853661…` and `match` true);
- an observation's `config_sha256` is not a genuine SHA-256 text rendering: a string of exactly 64 hexadecimal characters. Null, empty, non-text, truncated, extended, padded or non-hexadecimal values are refused, even when every observation carries the same value;
- the two observations were taken with different configurations (`config_name` or `config_sha256`);
- for `aborted`: A, the injector's armed baseline, its in-transaction observation and B do not all record the ordinary configuration `m06w2_config.json` (a missing or different `config_name` anywhere);
- the format differs;
- `complete` is not true, or `insufficient` is not empty;
- `unresolved_channels` is not empty;
- the context differs between begin and end;
- the peer records are not exactly the declared peers;
- a target or peer `flex` or `nonbody` record set differs from the declared literals;
- a declared control is unavailable;
- a protected file is not verified unchanged;
- any state record anywhere is unreadable or unknown, **even when it is identical in both observations**;
- the identities are contradictory or belong to the wrong instance.
