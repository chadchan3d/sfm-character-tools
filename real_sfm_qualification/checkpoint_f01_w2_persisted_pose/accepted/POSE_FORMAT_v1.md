# F01W2 left-arm pose format, version 1

A pose file is one standalone, self-contained JSON document. It holds the saved left-arm pose and the data
needed to check a destination before applying it. It does not depend on any sidecar file.

Qualification evidence is kept separately: the capture report and the hash binding in the run ledger belong
to the W2 qualification run, not to the format.

| Property | Value |
|---|---|
| Format identifier | `F01W2-left-arm-pose` |
| Version | integer `1` |
| Location in a W2 run | `<RUN_DIR>/poses/left_arm_pose.f01w2.json`, published once and never overwritten |
| Maximum size | 65,536 bytes |
| Parser and validator | `parse_pose()` in `harness/f01w2_core.py` |

## Encoding and parsing rules

**Bytes**
- Strict UTF-8, with no byte-order mark.
- Canonical writer output is ASCII JSON with keys sorted and one-space indentation, ending in a newline.
- Any byte sequence that satisfies the rules below is accepted; byte-exact canonical form is not required to
  read a file.

**JSON structure**
- Duplicate object keys are rejected at every level.
- The non-standard literals `NaN`, `Infinity` and `-Infinity` are rejected.
- Numbers that parse as non-finite, such as `1e400`, are rejected.
- Nothing in the file is executed or deserialized as code.

**Fields**
- Every object is closed: unknown fields are rejected, and every listed field is required.
- `diagnostics` is required as well, but it is diagnostic only (see below).

**Value types**
- **Numbers:** a JSON integer or float, never a boolean or a string, with `|x| <= 1e6`.
- **Integers:** a JSON integer with `|x| <= 1e6`; a float such as `1.0` is not accepted.
- **Strings:** 1 to 256 characters.

**Precision**
- Values keep the native observation's double precision, written as the shortest repr that reproduces the
  float.
- Nothing is rounded to float32 in the file. Rounding happens only when the authored key values are
  constructed at application.

## Conventions (the `conventions` object; every value is a fixed constant)

| Key | Value | Meaning |
|---|---|---|
| `units` | `sfm-native-units` | Positions are in SFM's native units |
| `quaternion_order` | `x,y,z,w` | Every quaternion is `[x, y, z, w]` |
| `transform_representation` | `rigid-position-unit-quaternion` | A transform is (position, unit quaternion), with no scale |
| `transform_composition` | `parent-times-child` | `compose(a, b) = a x b`, with child expressed in parent (W1's `compose`/`invert`) |
| `pose_frame` | `source-CollarL-world-at-capture` | Pose and skeletal values are expressed in the source `CollarL` evaluated world frame |
| `quaternion_unit_tolerance` | `0.0001` | Every quaternion must satisfy `abs(norm(q) - 1) <= 1e-4` |

**Quaternions**
- A quaternion's sign denotes the same rotation; it is not a unique orientation.
- Quaternions are never normalized silently. One outside the tolerance is rejected.
- W1 measured 1,133 native quaternions with a maximum unit-norm error of about 1.9e-7.

## Top-level fields

| Field | Type | Content |
|---|---|---|
| `format` | constant | `F01W2-left-arm-pose` |
| `version` | constant | `1` |
| `conventions` | object | See above |
| `model` | string | Normalized model path (lower case, `/`), for example `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` |
| `animation_set` | string | Animation set name (`Krystal`) |
| `compatibility` | object | Portable compatibility descriptor (below) |
| `pose` | object | `hand: {position: [3], orientation: [4]}` and `elbow: {position: [3]}`. Both are relative to the source `CollarL`. There is no elbow orientation. |
| `skeleton` | object | Independent skeletal reference (below) |
| `diagnostics` | object | `hand_target_residual` (number), `capture_shot` (string), `capture_movie_frame` (integer) |

## The pose

The pose is computed from:
- `Cs`, the source `CollarL` world transform;
- `Rs`, the source `rig_root` world transform;
- `Lh` and `Le`, the `Hand_l` and `Elbow_l` local transforms, which are their effective rig inputs.

| Quantity | Definition | Stored as |
|---|---|---|
| `Hs` | `Rs x Lh` | — |
| `Hc` | `inverse(Cs) x Hs` | `pose.hand.position`, `pose.hand.orientation` |
| `Es` | `Rs x (Le.position, identity)` | — |
| `Ec` | `inverse(Cs)` applied to `Es.position` | `pose.elbow.position` |

**Application**, against the destination's live `CollarL` world transform `Cd` and `rig_root` world
transform `Rd`:
- `Hd_local = inverse(Rd) x Cd x Hc`;
- `Ed_local = inverse(Rd)` applied to `(Cd` applied to `Ec)`.

## `skeleton`: the independent skeletal reference

`skeleton.bones` holds one entry for each of `bip_UpperArm_l`, `bip_lowerArm_l` and `bip_hand_l`, with these
fields:

| Field | Content |
|---|---|
| `local_orientation` | `[4]`: the evaluated local bone orientation; the primary oracle |
| `collar_position` | `[3]`: the evaluated world position in the source `CollarL` frame |
| `collar_orientation` | `[4]`: the evaluated world orientation in the source `CollarL` frame |

The secondary oracle is `Cd x (collar_position, collar_orientation)`.

`skeleton.upper_arm_origin` is `[3]`, the evaluated `bip_UpperArm_l` world origin in the source `CollarL`
frame. It is used by the shoulder guard.

These values are read from the evaluated bone DAGs. They are never reconstructed from the captured rig
inputs.

## `compatibility`: the portable descriptor

The descriptor is built only after the native identity checks pass. It contains names, roles and typed
values, never runtime handles. At application the descriptor is rebuilt from the destination, by the same
identity checks, and compared. The comparison is exact except for two fields:
- arm-bone local offsets, within 0.0001 units;
- constraint target weights, within 1e-6.

| Field | Content |
|---|---|
| `arm_chain` | 4 to 64 entries, sorted by name: `{name, index (integer), parent (string or null), local_position [3]}`. They cover `bip_collar_l` and every bone below it down to and including `bip_hand_l`, excluding the hand's descendants. Each name appears once, and the collar and the three arm bones are required. |
| `scale_state` | constant `unit`: the model, the arm-chain bones and the four rig handles had absent or unit scale |
| `handles` | for each of `rig_root`, `CollarL`, `Hand_l`, `Elbow_l`: `{parent: {type, name}}` |
| `constraints` | `ik`, `hand_orient`, `collar_point`, `collar_orient` (fields below) |
| `channels` | for each of `Hand_l_p`, `Hand_l_o`, `Elbow_l_p`, `Elbow_l_o`: the channel's role (fields below) |

**Each constraint** has these fields:

| Field | Content |
|---|---|
| `type` | `DmeRigIKConstraintOperator`, `DmeRigOrientConstraintOperator` or `DmeRigPointConstraintOperator` |
| `target_rig_handle` | `Hand_l` or `CollarL` |
| `target_weight` | number |
| `offsets` | `{oOffset: typed, vecOffset: typed}` |
| `solver` | a map with any of `startOffset`, `midOffset`, `poleVector`, `mode`, each typed |
| `joints` | IK only: `{startJoint, midJoint, endJoint}` bone names |
| `pole_target_rig_handle` | IK only: the constant `Elbow_l` |
| `slave_bone` | non-IK constraints only: the driven bone's name |

**Each channel role** has these fields: `control`, `control_attribute`, `from_attribute`, `from_index`,
`to_rig_handle`, `to_attribute`, `to_index`, `mode`, `log_type`, `layer_type`, `layer_count`, and
`curve_info` (the constant `none`).

**A typed field** is either `{"present": false}` (the attribute is absent) or `{"present": true, "value": v}`.
`v` may be:
- `null`, a boolean, a string or a bounded number;
- a list of at most 16 such scalars.

Element references are not portable. A capture refuses them instead of writing them.

## What a pose file never contains

- Element handles, runtime channel, log or layer identities, Python object references.
- Process identities, Undo descriptions or ownership, nonces.
- Session or other local paths, and W1 report data.

The tests check the golden file for each of these.

## Examples

- `tests/fixtures/golden_left_arm_pose.f01w2.json`: a complete, valid file captured from the synthetic
  fixture. Its SHA-256 is `2edf828c3a1bcc5078415338764277fc83e34df93beaedea10d4080a4f81579a`, and it is
  produced byte-identically under Python 2.7.5 and 3.10.6.
- `tests/fixtures/adversarial/`: byte-level invalid variants (a duplicate key, `NaN`, an overflowing number,
  a byte-order mark, invalid UTF-8, truncation). Structural variants are generated in
  `tests/test_f01w2.py`, in `TestPoseFormat`.
