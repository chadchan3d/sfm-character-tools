# -*- coding: ascii -*-
r"""
SFM Character Slider Preset Tool
0.2.0 RC6 - Generic Master-Driven Production Candidate
RUN TYPE: MAINMENU

First consolidated production candidate after G01-G11A.
Uses explicit generic model selection, reusable Master authority, generic Body/Expression
scopes and v3 storage, readable immutable v2 Nika/Krystal presets, exact
Krystal2020 Head Scale structural capability, and the qualified queued one-transaction-per-event-turn Match Clothing coordinator.

Dormant qualification helpers remain in-source for RC1 and may be removed during
release hardening after integrated acceptance.
"""

# CPM R15 allow-guard. This file is the private CPM implementation module
# (chadchan3d_cpm_app). Only the ChadChan3D Scripts-menu launcher may execute
# it, inside the launcher's loading context. Refuse every other execution
# (for example, running this file directly from a menu) before any import or
# application definition. Accident protection only; not a security boundary.
if not (
    __name__ == "chadchan3d_cpm_app"
    and globals().get("__chadchan3d_cpm_loader__") == "cpm-private-loader-v1"
    and globals().get("__chadchan3d_cpm_state__") == "loading"
):
    raise RuntimeError(
        "SFM Character Preset Manager: this file is the private implementation "
        "module. Launch it through the ChadChan3D > SFM_Character_Preset_Manager "
        "Scripts menu entry."
    )

import datetime
import os
import re
import traceback
import math
import sys
import base64

import sfmApp
import vs

from PySide import QtCore
from PySide import QtGui

try:
    unicode
except NameError:
    unicode = str

try:
    long
except NameError:
    long = int


OUTPUT_PATH = (
    "C:\\Users\\Public\\Documents\\"
    "SFM_CSP_G11A_ProductionWindowBodyMatch.log"
)

SHOT_NAME = u"shot5"
ANIMSET_NAME = u"nikasharkv21"
MODEL_PATH = u"models/annoad/nika/nikasharkv2.mdl"
MODEL_CHECKSUM = 865329843

MAX_GROUPS = 800
MAX_CONTROLS = 5000
EPSILON = 1.0e-5
APP_ATTR = "_sfm_character_slider_preset_tool_window"


def u(value):
    if value is None:
        return None
    if isinstance(value, unicode):
        return value
    try:
        return value.decode("utf-8")
    except Exception:
        try:
            return value.decode("latin-1")
        except Exception:
            return unicode(value)


def b(value):
    if isinstance(value, unicode):
        return value.encode("utf-8")
    return str(value)


def native_attr_name(value):
    try:
        if isinstance(value, unicode):
            return value.encode("ascii")
    except Exception:
        pass
    return value


def reset_log():
    """Best-effort diagnostic reset. Diagnostic I/O must never affect the tool."""
    fp = None

    try:
        fp = open(
            OUTPUT_PATH,
            "wb",
        )
        fp.write("")
        fp.flush()
        return True
    except Exception:
        return False
    finally:
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass


def log_line(text):
    """Best-effort diagnostics only; never changes product control flow."""
    fp = None

    try:
        fp = open(
            OUTPUT_PATH,
            "ab",
        )
        stamp = datetime.datetime.now().strftime(
            "%H:%M:%S.%f"
        )
        fp.write(
            ("[%s] %s\r\n" % (stamp, u(text))).encode(
                "utf-8",
                "backslashreplace",
            )
        )
        fp.flush()
        return True
    except Exception:
        return False
    finally:
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass


def ptr(obj):
    if obj is None:
        return None
    try:
        return long(obj.this)
    except Exception:
        try:
            return long(int(obj.this))
        except Exception:
            return None


def handle(obj):
    if obj is None:
        return None
    try:
        return int(obj.GetHandle())
    except Exception:
        return None


def name(obj):
    if obj is None:
        return None
    try:
        return u(obj.GetName())
    except Exception:
        return u"<UNNAMED>"


def typ(obj):
    if obj is None:
        return None
    try:
        return u(obj.GetTypeString())
    except Exception:
        try:
            return u(obj.__class__.__name__)
        except Exception:
            return None


def dme_id(obj):
    return (typ(obj), name(obj), handle(obj), ptr(obj))


def same_dme(a, b):
    return (
        a is not None
        and b is not None
        and handle(a) == handle(b)
        and ptr(a) == ptr(b)
    )


def get_attr(element, attr_name):
    if element is None:
        return None
    try:
        return element.GetAttribute(
            native_attr_name(attr_name)
        )
    except Exception:
        return None


def attr_value(element, attr_name):
    attr = get_attr(element, attr_name)

    if attr is not None:
        try:
            return attr.GetValue()
        except Exception:
            try:
                return attr.GetValueUntyped()
            except Exception:
                pass

    try:
        return getattr(
            element,
            native_attr_name(attr_name),
        )
    except Exception:
        return None


def arr(element, attr_name):
    value = attr_value(element, attr_name)

    if value is None:
        return []

    try:
        return list(value)
    except Exception:
        pass

    try:
        return [value[i] for i in range(len(value))]
    except Exception:
        return []


def as_float(value):
    try:
        number = float(value)
    except Exception:
        return None

    try:
        if math.isnan(number) or math.isinf(number):
            return None
    except Exception:
        return None

    return number


def close_enough(a, b):
    af = as_float(a)
    bf = as_float(b)

    return (
        af is not None
        and bf is not None
        and abs(af - bf) <= EPSILON
    )


def seconds(value):
    if value is None:
        return None

    try:
        return float(value.GetSeconds())
    except Exception:
        pass

    try:
        return float(value)
    except Exception:
        return None


def model_asset(game_model):
    value = attr_value(game_model, "modelName")

    if value is None:
        return None

    return (
        u(value)
        .strip()
        .replace("\\", "/")
        .lower()
    )


def get_game_model(animset):
    try:
        if not animset.HasAttribute("gameModel"):
            return None
        gm = animset.gameModel
    except Exception:
        return None

    if gm is None or ptr(gm) is None:
        return None

    return gm


def checksum(game_model):
    hdr = game_model.GetStudioHdr()

    if hdr is None:
        raise RuntimeError("GetStudioHdr failed.")

    return int(hdr.checksum)


def current_shot():
    # Production resolver: current-shot identity is never a fixed test fixture.
    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        raise RuntimeError(
            "No current shot."
        )

    return shot


def exact_animset(shot):
    matches = []

    for animset in list(shot.animationSets):
        if name(animset) != ANIMSET_NAME:
            continue

        gm = get_game_model(animset)

        if gm is None:
            continue

        if model_asset(gm) != MODEL_PATH:
            continue

        if checksum(gm) != MODEL_CHECKSUM:
            continue

        matches.append((animset, gm))

    if len(matches) != 1:
        raise RuntimeError(
            "Expected one exact %r instance; found %d."
            % (
                ANIMSET_NAME,
                len(matches),
            )
        )

    return matches[0]


def child_groups(group):
    return [
        item
        for item in arr(group, "children")
        if typ(item) == u"DmeControlGroup"
    ]


def root_group(animset):
    try:
        root = animset.GetRootControlGroup()
    except Exception:
        root = attr_value(
            animset,
            "rootControlGroup",
        )

    if root is None:
        raise RuntimeError(
            "Character has no root control group."
        )

    return root


def group_inventory(animset):
    root = root_group(animset)

    records = []
    stack = [(root, [name(root)])]
    seen = set()

    while stack:
        group, parts = stack.pop()

        key = (
            handle(group),
            ptr(group),
        )

        if key in seen:
            continue

        seen.add(key)

        if len(seen) > MAX_GROUPS:
            raise RuntimeError(
                "Control-group traversal exceeded safety cap."
            )

        clean = [
            part
            for part in parts
            if part is not None
        ]

        records.append(
            {
                "group": group,
                "path": u"/".join(clean),
                "parts": clean,
            }
        )

        for child in child_groups(group):
            stack.append(
                (
                    child,
                    clean + [name(child)],
                )
            )

    records.sort(
        key=lambda row: row["path"]
    )

    return records


def resolve_group_by_path(animset, wanted_path):
    matches = [
        row
        for row in group_inventory(animset)
        if row["path"] == wanted_path
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "Selected group path %r no longer resolves uniquely."
            % wanted_path
        )

    return matches[0]["group"]


def subtree_controls(group):
    result = []
    stack = [group]
    seen_groups = set()
    seen_controls = set()

    while stack:
        current = stack.pop()

        group_key = (
            handle(current),
            ptr(current),
        )

        if group_key in seen_groups:
            continue

        seen_groups.add(group_key)

        if len(seen_groups) > MAX_GROUPS:
            raise RuntimeError(
                "Group subtree exceeded safety cap."
            )

        for control in arr(current, "controls"):
            control_key = (
                handle(control),
                ptr(control),
            )

            if control_key in seen_controls:
                continue

            seen_controls.add(control_key)
            result.append(control)

            if len(seen_controls) > MAX_CONTROLS:
                raise RuntimeError(
                    "Control subtree exceeded safety cap."
                )

        for child in child_groups(current):
            stack.append(child)

    return result


def global_index(operator):
    try:
        return int(operator.GetGlobalIndex())
    except Exception:
        return None


def resolve_side(
    control,
    source_attr,
    channel_attr,
):
    source_attribute = get_attr(
        control,
        source_attr,
    )

    if source_attribute is None:
        return None

    channel = attr_value(
        control,
        channel_attr,
    )

    if (
        channel is None
        or typ(channel) != u"DmeChannel"
    ):
        return None

    destination = attr_value(
        channel,
        "toElement",
    )

    if (
        destination is None
        or typ(destination)
        != u"DmeGlobalFlexControllerOperator"
    ):
        return None

    gid = global_index(destination)

    if gid is None:
        return None

    try:
        log = channel.GetLog()
    except Exception:
        log = attr_value(channel, "log")

    if (
        log is None
        or typ(log) != u"DmeFloatLog"
    ):
        return None

    try:
        layer_count = int(
            log.GetNumLayers()
        )
    except Exception:
        try:
            layer_count = len(list(log.layers))
        except Exception:
            return None

    if layer_count != 1:
        return None

    try:
        layer = log.GetLayer(0)
    except Exception:
        try:
            layer = list(log.layers)[0]
        except Exception:
            return None

    if typ(layer) != u"DmeFloatLogLayer":
        return None

    return {
        "source_attr": source_attr,
        "source_attribute": source_attribute,
        "channel_attr": channel_attr,
        "channel": channel,
        "destination": destination,
        "global": gid,
        "log": log,
        "layer": layer,
    }


def flex_binding(control):
    if control is None or typ(control) != u"DmElement":
        return None

    if (
        get_attr(control, "leftValue") is not None
        and get_attr(control, "rightValue") is not None
    ):
        left = resolve_side(
            control,
            u"leftValue",
            "leftvaluechannel",
        )
        right = resolve_side(
            control,
            u"rightValue",
            "rightvaluechannel",
        )

        if left is None or right is None:
            return None

        if handle(left["channel"]) == handle(right["channel"]):
            return None

        if handle(left["log"]) == handle(right["log"]):
            return None

        return {
            "literal": name(control),
            "shape": "STEREO",
            "global_key": (
                "STEREO",
                left["global"],
                right["global"],
            ),
            "control": control,
            "sides": [
                ("left", left),
                ("right", right),
            ],
        }

    if get_attr(control, "value") is not None:
        mono = resolve_side(
            control,
            u"value",
            "channel",
        )

        if mono is None:
            return None

        return {
            "literal": name(control),
            "shape": "MONO",
            "global_key": (
                "MONO",
                mono["global"],
            ),
            "control": control,
            "sides": [
                ("mono", mono),
            ],
        }

    return None


def bindings_for_group(group):
    result = []

    for control in subtree_controls(group):
        binding = flex_binding(control)

        if binding is not None:
            result.append(binding)

    result.sort(
        key=lambda row: (
            row["literal"] or u"",
            row["shape"],
        )
    )

    # Global identity must be unique inside the chosen preset scope.
    index = {}

    for binding in result:
        index.setdefault(
            binding["global_key"],
            [],
        ).append(binding)

    duplicates = [
        (
            key,
            [row["literal"] for row in rows],
        )
        for key, rows in index.items()
        if len(rows) != 1
    ]

    if duplicates:
        raise RuntimeError(
            "Chosen group contains duplicate structural identities: %r"
            % duplicates
        )

    return result


def key_count(layer):
    try:
        return int(layer.GetKeyCount())
    except Exception:
        try:
            return min(
                len(layer.times),
                len(layer.values),
            )
        except Exception:
            return None


def side_snapshot(control, side):
    count = key_count(side["layer"])

    try:
        empty = bool(side["log"].IsEmpty())
    except Exception:
        empty = None

    try:
        evaluated = as_float(
            side["log"].GetValue(
                side["channel"].GetCurrentTime()
            )
        )
    except Exception:
        evaluated = None

    key_time = None
    key_value = None

    if count == 1:
        try:
            key_time = seconds(
                side["layer"].GetKeyTime(0)
            )
        except Exception:
            pass

        try:
            key_value = as_float(
                side["layer"].GetKeyValue(0)
            )
        except Exception:
            pass

    return {
        "source": as_float(
            attr_value(
                control,
                side["source_attr"],
            )
        ),
        "destination": as_float(
            attr_value(
                side["destination"],
                "flexWeight",
            )
        ),
        "evaluated": evaluated,
        "key_count": count,
        "is_empty": empty,
        "key0_time": key_time,
        "key0_value": key_value,
        "channel_id": dme_id(side["channel"]),
        "log_id": dme_id(side["log"]),
        "layer_id": dme_id(side["layer"]),
        "destination_id": dme_id(side["destination"]),
    }


def binding_snapshot(binding):
    result = {
        "literal": binding["literal"],
        "shape": binding["shape"],
        "global_key": binding["global_key"],
        "control_id": dme_id(binding["control"]),
        "sides": {},
    }

    for side_name, side in binding["sides"]:
        result["sides"][side_name] = side_snapshot(
            binding["control"],
            side,
        )

    return result


def state_kind(state):
    if (
        state["key_count"] == 0
        and state["is_empty"] is True
    ):
        return "EMPTY"

    if (
        state["key_count"] == 1
        and state["is_empty"] is False
        and close_enough(
            state["key0_time"],
            0.0,
        )
        and close_enough(
            state["key0_value"],
            state["source"],
        )
    ):
        return "ONE_KEY_ZERO"

    return "UNSUPPORTED"


def coherent(state):
    return (
        state_kind(state) != "UNSUPPORTED"
        and close_enough(
            state["source"],
            state["destination"],
        )
        and close_enough(
            state["source"],
            state["evaluated"],
        )
    )


def same_side_identity(a, bstate):
    return (
        a["channel_id"] == bstate["channel_id"]
        and a["log_id"] == bstate["log_id"]
        and a["layer_id"] == bstate["layer_id"]
        and a["destination_id"] == bstate["destination_id"]
    )


def matches_value(state, desired):
    return (
        coherent(state)
        and close_enough(state["source"], desired)
        and close_enough(state["destination"], desired)
        and close_enough(state["evaluated"], desired)
    )


def matches_baseline(state, baseline, origin):
    if not same_side_identity(state, baseline):
        return False

    if not (
        close_enough(state["source"], baseline["source"])
        and close_enough(
            state["destination"],
            baseline["destination"],
        )
        and close_enough(
            state["evaluated"],
            baseline["evaluated"],
        )
    ):
        return False

    if origin == "EMPTY":
        return (
            state["key_count"] == 0
            and state["is_empty"] is True
        )

    if origin == "ONE_KEY_ZERO":
        return (
            state["key_count"] == 1
            and state["is_empty"] is False
            and close_enough(
                state["key0_time"],
                baseline["key0_time"],
            )
            and close_enough(
                state["key0_value"],
                baseline["key0_value"],
            )
        )

    return False


def make_zero_time():
    zero = vs.tier1.DmeTime_t(0)

    if not close_enough(
        zero.GetSeconds(),
        0.0,
    ):
        raise RuntimeError(
            "Could not create local-zero time."
        )

    return zero


def write_side(
    binding,
    side,
    origin,
    desired,
):
    if origin == "EMPTY":
        side["source_attribute"].SetValue(
            float(desired)
        )
        side["layer"].ClearAndAddSampleAtTime(
            make_zero_time(),
            side["channel"],
        )
        side["channel"].Operate()
        return

    if origin == "ONE_KEY_ZERO":
        side["layer"].SetKeyValue(
            0,
            float(desired),
        )
        side["source_attribute"].SetValue(
            float(desired)
        )
        side["channel"].Operate()
        return

    raise RuntimeError(
        "Unsupported writer origin %r."
        % origin
    )


def restore_side(
    binding,
    side,
    baseline,
    origin,
):
    if origin == "EMPTY":
        side["layer"].ClearKeys()
        side["source_attribute"].SetValue(
            float(baseline["source"])
        )
        side["channel"].Operate()
        return

    if origin == "ONE_KEY_ZERO":
        side["layer"].SetKeyValue(
            0,
            float(baseline["key0_value"]),
        )
        side["source_attribute"].SetValue(
            float(baseline["source"])
        )
        side["channel"].Operate()
        return

    raise RuntimeError(
        "Unsupported Restore origin %r."
        % origin
    )


def dm():
    data_model = getattr(
        vs,
        "g_pDataModel",
        None,
    )

    if data_model is None:
        raise RuntimeError(
            "vs.g_pDataModel unavailable."
        )

    return data_model


def undo_state(label):
    data_model = dm()

    result = {}

    for key, method_name in (
        ("enabled", "IsUndoEnabled"),
        ("count", "GetUndoItemCount"),
        ("desc", "GetUndoDesc"),
    ):
        try:
            result[key] = getattr(
                data_model,
                method_name,
            )()
        except Exception:
            result[key] = None

    try:
        log_line(
            "%s=%r"
            % (
                label,
                result,
            )
        )
    except Exception:
        pass

    return result


def same_time_refresh(head_time, label):
    before = float(
        sfmApp.GetHeadTimeInSeconds()
    )

    sfmApp.SetHeadTimeInSeconds(
        float(head_time)
    )

    after_set = float(
        sfmApp.GetHeadTimeInSeconds()
    )

    sfmApp.ProcessEvents()

    after_process = float(
        sfmApp.GetHeadTimeInSeconds()
    )

    try:
        log_line(
            "%s_REFRESH requested=%r before=%r after_set=%r after_process=%r"
            % (
                label,
                head_time,
                before,
                after_set,
                after_process,
            )
        )
    except Exception:
        pass


def qt_parent():
    try:
        active = QtGui.QApplication.activeWindow()
    except Exception:
        active = None

    if (
        active is not None
        and isinstance(active, QtGui.QWidget)
    ):
        return active

    return None




# -------------------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------------------
# R35 - Master-derived head-shape eligibility evidence
# -------------------------------------------------------------------------------------------------

import hashlib

R35_MODEL_PATH = u"models/annoad/nika/nikasharkv2.mdl"
R35_MODEL_CHECKSUM = 865329843

R35_HEAD_LITERALS = (
    u"NikHeadShape1",
    u"NikHeadShape2",
)

R35_BODY_LITERAL = u"FBMfitness"



# -------------------------------------------------------------------------------------------------
# Production Integration P01
# Temporary Master-TXT provider seam + complete supported-vocabulary semantic contract
#
# IMPORTANT:
# - Read-only with respect to the SFM document.
# - Does NOT write character.json.
# - Does NOT claim the temporary TXT bridge is the final release provider.
# - The future sidecar provider must implement the same caller-facing contract.
# -------------------------------------------------------------------------------------------------

import hashlib
import json

P01_MODEL_PATH = u"models/annoad/nika/nikasharkv2.mdl"
P01_MODEL_CHECKSUM = 865329843

# Production semantic-provider contract.  The P01 names remain aliases so the
# already-qualified caller/test code can be migrated incrementally without
# changing semantic answers during G01.
SEMANTIC_PROVIDER_CONTRACT = u"sfm-character-semantic-provider-v1"
SEMANTIC_PROVIDER_KIND_MASTER_TXT = u"temporary_master_txt_bridge"
SEMANTIC_PROVIDER_KIND_MASTER_SIDECAR = u"compiled_master_sidecar_r1d"
SEMANTIC_PROVIDER_FOLD_POLICY = u"ascii-a-z-v1"
SEMANTIC_PROVIDER_MASTER_FILENAME = u"sfm_defaultanimationgroups.txt"

SEMANTIC_STATUS_RESOLVED = u"resolved"
SEMANTIC_STATUS_CONFLICT = u"conflict"
SEMANTIC_STATUS_ABSENT = u"absent"
SEMANTIC_STATUS_UNAVAILABLE = u"authority-unavailable"

SEMANTIC_MATCH_EXACT = u"exact"
SEMANTIC_MATCH_FOLDED = u"ascii-fold"
SEMANTIC_MATCH_NONE = u"none"

P01_PROVIDER_CONTRACT = SEMANTIC_PROVIDER_CONTRACT
P01_PROVIDER_KIND = SEMANTIC_PROVIDER_KIND_MASTER_TXT
P01_FOLD_POLICY = SEMANTIC_PROVIDER_FOLD_POLICY
P01_MASTER_FILENAME = SEMANTIC_PROVIDER_MASTER_FILENAME
P01_STATUS_RESOLVED = SEMANTIC_STATUS_RESOLVED
P01_STATUS_CONFLICT = SEMANTIC_STATUS_CONFLICT
P01_STATUS_ABSENT = SEMANTIC_STATUS_ABSENT
P01_STATUS_UNAVAILABLE = SEMANTIC_STATUS_UNAVAILABLE
P01_MATCH_EXACT = SEMANTIC_MATCH_EXACT
P01_MATCH_FOLDED = SEMANTIC_MATCH_FOLDED
P01_MATCH_NONE = SEMANTIC_MATCH_NONE


def p01_master_path():
    try:
        import filesystem
        mod_path = unicode(filesystem.valve.mod())
    except Exception as exc:
        raise RuntimeError(
            "SFM could not resolve the active mod directory: %r" % exc
        )

    if not mod_path:
        raise RuntimeError("SFM returned an empty active mod directory.")

    path = os.path.join(mod_path, "cfg", P01_MASTER_FILENAME)
    try:
        log_line(
            "P01_MASTER_PATH source='filesystem.valve.mod' mod_path=%r path=%r"
            % (mod_path, path)
        )
    except Exception:
        pass
    return path


_SEMANTIC_PROVIDER = None
_SEMANTIC_PROVIDER_OPEN_COUNT = 0
_SEMANTIC_PROVIDER_REUSE_COUNT = 0
_SEMANTIC_PROVIDER_INVALIDATION_COUNT = 0
_SEMANTIC_PROVIDER_PRODUCTION_PARSE_COUNT = 0
_SEMANTIC_PROVIDER_GENERATION = 0



class ProdHistoricalAuthorityDisabled(RuntimeError):
    """Historical semantic-provider acquisition was invoked; it is disabled (handoff
    section 22 item 6). Semantic authority comes only from the canonical CPM route."""


def get_semantic_provider():
    raise ProdHistoricalAuthorityDisabled(
        "Historical semantic-provider acquisition is disabled; use the canonical CPM authority route."
    )


def semantic_provider_runtime_stats():
    descriptor = None
    provider_stats = {
        "query_batch_count": 0,
        "query_literal_count": 0,
    }

    if _SEMANTIC_PROVIDER is not None:
        descriptor = _SEMANTIC_PROVIDER.generation_descriptor()
        provider_stats = _SEMANTIC_PROVIDER.runtime_stats()

    return {
        "open_count": _SEMANTIC_PROVIDER_OPEN_COUNT,
        "reuse_count": _SEMANTIC_PROVIDER_REUSE_COUNT,
        "invalidation_count": _SEMANTIC_PROVIDER_INVALIDATION_COUNT,
        "production_parse_count": _SEMANTIC_PROVIDER_PRODUCTION_PARSE_COUNT,
        "descriptor": descriptor,
        "query_batch_count": provider_stats["query_batch_count"],
        "query_literal_count": provider_stats["query_literal_count"],
        "provider_runtime": dict(
            provider_stats
        ),
    }


def p01_is_face_path(path):
    if not path:
        return False
    parts = [item for item in unicode(path).split(u"/") if item]
    return bool(parts and parts[0].lower() == u"face")


def p01_model_backed_animsets(shot):
    result = []
    for animset in list(shot.animationSets):
        gm = get_game_model(animset)
        if gm is None:
            continue
        asset = model_asset(gm)
        check = checksum(gm)
        if asset is None or check is None:
            continue
        result.append({
            "animset": animset,
            "gm": gm,
            "model": asset,
            "checksum": check,
            "animset_name": name(animset),
        })
    return result


def p01_current_nika():
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("No current shot.")

    matches = [
        row for row in p01_model_backed_animsets(shot)
        if row["model"] == P01_MODEL_PATH and row["checksum"] == P01_MODEL_CHECKSUM
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "P01 requires exactly one compatible Nika Shark in the current shot; found %d."
            % len(matches)
        )
    row = matches[0]
    row["shot"] = shot
    return row


def p01_all_supported_flex_bindings(animset):
    try:
        controls = list(animset.controls)
    except Exception:
        controls = arr(animset, "controls")

    if len(controls) > MAX_CONTROLS:
        raise RuntimeError("Animation-set control count exceeded the established safety cap.")

    bindings = []
    for control in controls:
        binding = flex_binding(control)
        if binding is not None:
            bindings.append(binding)

    bindings.sort(
        key=lambda row: (row["literal"] or u"", row["shape"], repr(row["global_key"]))
    )
    return bindings


def p01_scope_from_live_vocabulary(bindings, answers):
    by_literal = {}
    for binding in bindings:
        by_literal.setdefault(binding["literal"], []).append(binding)

    rows = []
    accepted = []
    counts = {
        "supported_bindings": len(bindings),
        "unique_literals": len(by_literal),
        "resolved_face": 0,
        "resolved_nonface": 0,
        "conflict": 0,
        "absent": 0,
        "binding_ambiguous": 0,
        "folded_resolved": 0,
    }

    for literal in sorted(by_literal.keys()):
        live_rows = by_literal[literal]
        answer = answers[literal]
        binding_ambiguous = len(live_rows) != 1
        face = False
        eligibility = u"unresolved"

        if binding_ambiguous:
            counts["binding_ambiguous"] += 1
            eligibility = u"binding-ambiguous"
        elif answer["status"] == P01_STATUS_CONFLICT:
            counts["conflict"] += 1
            eligibility = u"semantic-conflict"
        elif answer["status"] == P01_STATUS_ABSENT:
            counts["absent"] += 1
            eligibility = u"master-absent"
        elif answer["status"] == P01_STATUS_RESOLVED:
            face = p01_is_face_path(answer["resolved_path"])
            if answer["match_kind"] == P01_MATCH_FOLDED:
                counts["folded_resolved"] += 1
            if face:
                counts["resolved_face"] += 1
                eligibility = u"expression-eligible"
                accepted.append(literal)
            else:
                counts["resolved_nonface"] += 1
                eligibility = u"master-nonface"
        else:
            eligibility = u"authority-unavailable"

        rows.append({
            "literal": literal,
            "live_binding_count": len(live_rows),
            "live_shapes": sorted(set(item["shape"] for item in live_rows)),
            "semantic_status": answer["status"],
            "match_kind": answer["match_kind"],
            "resolved_path": answer["resolved_path"],
            "destinations": list(answer["destinations"]),
            "master_spellings": list(answer["spellings"]),
            "face_member": face,
            "eligibility": eligibility,
        })

    return {
        "rows": rows,
        "accepted_expression_literals": sorted(accepted),
        "counts": counts,
    }



# -------------------------------------------------------------------------------------------------
# Production Refactor G02
# Generic read-only semantic snapshot for arbitrary model-backed animation sets.
#
# This layer deliberately knows nothing about Nika/Krystal identity. It inventories the current
# model's supported FLEX vocabulary, asks the retained semantic provider, and partitions the result
# into Expression (Master Face), Body Preset (Master Body Morphs), other resolved domains, genuine
# Master misses, conflicts, authority failures, and live-binding ambiguity.
#
# G02 does NOT change Save/Apply routing yet. The qualified fixture paths remain the production
# mutation path until later gates prove generic execution equivalence.
# -------------------------------------------------------------------------------------------------

SEMANTIC_BODY_MORPHS_PATH = u"Body Morphs"


def semantic_is_body_morph_path(path):
    if not path:
        return False
    return unicode(path) == SEMANTIC_BODY_MORPHS_PATH


def semantic_snapshot_from_live_vocabulary(bindings, answers):
    by_literal = {}
    for binding in bindings:
        by_literal.setdefault(binding["literal"], []).append(binding)

    rows = []
    expression_literals = []
    body_literals = []
    counts = {
        "supported_bindings": len(bindings),
        "unique_literals": len(by_literal),
        "resolved_face": 0,
        "resolved_body_morphs": 0,
        "resolved_other": 0,
        "miss": 0,
        "conflict": 0,
        "authority_unavailable": 0,
        "binding_ambiguous": 0,
        "folded_resolved": 0,
        "expression_eligible": 0,
        "body_eligible": 0,
    }

    for literal in sorted(by_literal.keys()):
        live_rows = by_literal[literal]
        binding_ambiguous = len(live_rows) != 1
        if binding_ambiguous:
            counts["binding_ambiguous"] += 1

        answer = answers.get(literal)
        status = None if answer is None else answer.get("status")
        match_kind = None if answer is None else answer.get("match_kind")
        resolved_path = None if answer is None else answer.get("resolved_path")
        semantic_class = u"authority-unavailable"
        operation = u"unresolved"

        if status == P01_STATUS_RESOLVED:
            if match_kind == P01_MATCH_FOLDED:
                counts["folded_resolved"] += 1

            if p01_is_face_path(resolved_path):
                counts["resolved_face"] += 1
                semantic_class = u"face"
                if not binding_ambiguous:
                    operation = u"expression"
                    expression_literals.append(literal)
                    counts["expression_eligible"] += 1
            elif semantic_is_body_morph_path(resolved_path):
                counts["resolved_body_morphs"] += 1
                semantic_class = u"body-morphs"
                if not binding_ambiguous:
                    operation = u"body"
                    body_literals.append(literal)
                    counts["body_eligible"] += 1
            else:
                counts["resolved_other"] += 1
                semantic_class = u"other"
                operation = u"excluded-other"

        elif status == P01_STATUS_ABSENT:
            counts["miss"] += 1
            semantic_class = u"master-miss"
            operation = u"unresolved"

        elif status == P01_STATUS_CONFLICT:
            counts["conflict"] += 1
            semantic_class = u"master-conflict"
            operation = u"unresolved"

        else:
            counts["authority_unavailable"] += 1
            semantic_class = u"authority-unavailable"
            operation = u"unresolved"

        rows.append({
            "literal": literal,
            "live_binding_count": len(live_rows),
            "live_shapes": sorted(set(item["shape"] for item in live_rows)),
            "binding_ambiguous": binding_ambiguous,
            "semantic_status": status,
            "match_kind": match_kind,
            "resolved_path": resolved_path,
            "destinations": [] if answer is None else list(answer.get("destinations") or []),
            "master_spellings": [] if answer is None else list(answer.get("spellings") or []),
            "semantic_class": semantic_class,
            "operation": operation,
        })

    return {
        "rows": rows,
        "accepted_expression_literals": sorted(expression_literals),
        "accepted_body_literals": sorted(body_literals),
        "counts": counts,
    }


def semantic_snapshot_signature(snapshot):
    payload = []
    for row in snapshot["rows"]:
        payload.append((
            row["literal"],
            row["live_binding_count"],
            tuple(row["live_shapes"]),
            bool(row["binding_ambiguous"]),
            row["semantic_status"],
            row["match_kind"],
            row["resolved_path"],
            tuple(row["destinations"]),
            tuple(row["master_spellings"]),
            row["semantic_class"],
            row["operation"],
        ))
    encoded = repr(tuple(payload)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semantic_snapshot_for_model_row(row, provider=None):
    if row is None:
        raise RuntimeError("Generic semantic snapshot requires a model-backed animation-set row.")

    animset = row.get("animset")
    if animset is None:
        raise RuntimeError("Generic semantic snapshot row has no live animation set.")

    bindings = p01_all_supported_flex_bindings(animset)
    literals = sorted(set(item["literal"] for item in bindings))

    if provider is None:
        raise RuntimeError(
            "Semantic snapshot requires an explicitly supplied authority provider."
        )

    descriptor = provider.generation_descriptor()
    if not descriptor.get("valid"):
        raise RuntimeError("Semantic authority is not valid.")

    answers = provider.query_many(literals)
    semantic = semantic_snapshot_from_live_vocabulary(bindings, answers)
    signature = semantic_snapshot_signature(semantic)

    target = {
        "model": row.get("model"),
        "checksum": row.get("checksum"),
        "animset_name": row.get("animset_name"),
        "animset": animset,
        "gm": row.get("gm"),
    }

    return {
        "target": target,
        "bindings": bindings,
        "answers": answers,
        "semantic": semantic,
        "provider": provider,
        "provider_descriptor": descriptor,
        "signature": signature,
    }


def p01_row_by_literal(scope, literal):
    matches = [row for row in scope["rows"] if row["literal"] == literal]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one scope row for %r; found %d." % (literal, len(matches))
        )
    return matches[0]


def p01_write_report(record):
    path = (
        "C:\\Users\\Public\\Documents\\"
        "SFM_CharacterPreset_P01_MasterScopeContract_report.json"
    )
    fp = open(path, "wb")
    try:
        payload = json.dumps(
            record,
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        ) + "\n"
        fp.write(payload.encode("ascii"))
        fp.flush()
        try:
            os.fsync(fp.fileno())
        except Exception:
            pass
    finally:
        fp.close()
    return path



# -------------------------------------------------------------------------------------------------
# Production Integration P02
# Complete Master-derived Expression capture -> safe disk save -> disk reload -> Apply -> one Undo
#
# Temporary semantic provider: installed Master TXT bridge from P01.
# Future sidecar swaps behind the same semantic policy/provider seam.
# -------------------------------------------------------------------------------------------------

import ctypes

P02_SCHEMA_VERSION = 2
P02_PROFILE_ID = u"sfm-character-nika-shark-v1"
P02_PROFILE_REVISION = 2
P02_EXPRESSION_SCOPE_REVISION = 2
P02_EXPRESSION_POLICY_ID = u"master-face-flex-v1"
P02_PRESET_ID = u"p02-complete-expression-v1"
P02_PRESET_NAME = u"P02 Complete Facial State"

P02_LIBRARY_DIRNAME = u"SFM Character Preset Tool"
P02_CHARACTER_FOLDER = u"Nika Shark--nika-shark-v1"
P02_EXPRESSION_FILENAME = (
    u"P02 Complete Facial State--p02-complete-expression-v1.json"
)

P02_HEAD_LITERALS = (
    u"NikHeadShape1",
    u"NikHeadShape2",
)
P02_BODY_SENTINEL = u"FBMfitness"
P02_PREFERRED_STEREO = u"SmileClosed"


class P02GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


P02_FOLDERID_DOCUMENTS = P02GUID(
    0xFDD39AD0,
    0x238F,
    0x46AF,
    (ctypes.c_ubyte * 8)(
        0xAD, 0xB4, 0x6C, 0x85,
        0x48, 0x03, 0x69, 0xC7,
    ),
)


def p02_documents():
    out = ctypes.c_wchar_p()

    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(P02_FOLDERID_DOCUMENTS),
        0,
        None,
        ctypes.byref(out),
    )

    if result != 0 or not out.value:
        raise RuntimeError(
            "Windows could not resolve the current user's Documents folder."
        )

    try:
        path = unicode(out.value)
    finally:
        try:
            ctypes.windll.ole32.CoTaskMemFree(out)
        except Exception:
            pass

    if path.rstrip(u"\\/").lower() == u"c:\\users\\public\\documents":
        raise RuntimeError(
            "The preset library resolved to Public Documents."
        )

    return path


def p02_paths():
    root = os.path.join(
        p02_documents(),
        P02_LIBRARY_DIRNAME,
    )
    character_root = os.path.join(
        root,
        u"Characters",
        P02_CHARACTER_FOLDER,
    )
    expression_root = os.path.join(
        character_root,
        u"Expressions",
    )

    return {
        "root": root,
        "character_root": character_root,
        "profile": os.path.join(
            character_root,
            u"character.json",
        ),
        "expression": os.path.join(
            expression_root,
            P02_EXPRESSION_FILENAME,
        ),
    }


def p02_ensure_dir(path):
    if os.path.isdir(path):
        return

    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def p02_json_text(record):
    return (
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + u"\n"
    )


def p02_unique_temp(path):
    stamp = datetime.datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )
    return (
        path
        + u".tmp-p02-"
        + unicode(os.getpid())
        + u"-"
        + unicode(stamp)
    )


def p02_safe_write_json(path, record):
    p02_ensure_dir(
        os.path.dirname(path)
    )

    temp_path = p02_unique_temp(
        path
    )
    backup_path = path + u".bak"

    payload = p02_json_text(
        record
    ).encode(
        "utf-8"
    )

    fp = open(
        temp_path,
        "wb",
    )

    try:
        fp.write(
            payload
        )
        fp.flush()

        try:
            os.fsync(
                fp.fileno()
            )
        except Exception as exc:
            raise RuntimeError(
                "Could not synchronize temporary save file %r: %r"
                % (
                    temp_path,
                    exc,
                )
            )
    finally:
        fp.close()

    try:
        if os.path.exists(
            path
        ):
            result = ctypes.windll.kernel32.ReplaceFileW(
                ctypes.c_wchar_p(path),
                ctypes.c_wchar_p(temp_path),
                ctypes.c_wchar_p(backup_path),
                0,
                None,
                None,
            )

            if not result:
                code = ctypes.windll.kernel32.GetLastError()
                raise RuntimeError(
                    "Windows could not safely replace %r (error %d)."
                    % (
                        path,
                        code,
                    )
                )
        else:
            result = ctypes.windll.kernel32.MoveFileExW(
                ctypes.c_wchar_p(temp_path),
                ctypes.c_wchar_p(path),
                0x8,
            )

            if not result:
                code = ctypes.windll.kernel32.GetLastError()
                raise RuntimeError(
                    "Windows could not finish saving %r (error %d)."
                    % (
                        path,
                        code,
                    )
                )

    except Exception:
        log_line(
            "P02_STORAGE_FAILURE_STATE destination=%r temp_exists=%r "
            "backup_exists=%r destination_exists=%r"
            % (
                path,
                os.path.exists(
                    temp_path
                ),
                os.path.exists(
                    backup_path
                ),
                os.path.exists(
                    path
                ),
            )
        )
        raise

    return {
        "destination": path,
        "backup": backup_path,
        "backup_exists": os.path.exists(
            backup_path
        ),
        "temp_exists_after": os.path.exists(
            temp_path
        ),
        "bytes": len(
            payload
        ),
    }


def p02_read_json(path):
    fp = open(
        path,
        "rb",
    )

    try:
        raw = fp.read()
    finally:
        fp.close()

    return json.loads(
        raw.decode(
            "utf-8"
        )
    )


def p02_scope_row_signature(row):
    return {
        "literal": row[
            "literal"
        ],
        "live_shapes": list(
            row[
                "live_shapes"
            ]
        ),
        "semantic_status": row[
            "semantic_status"
        ],
        "match_kind": row[
            "match_kind"
        ],
        "resolved_path": row[
            "resolved_path"
        ],
        "destinations": list(
            row[
                "destinations"
            ]
        ),
        "master_spellings": list(
            row[
                "master_spellings"
            ]
        ),
        "face_member": bool(
            row[
                "face_member"
            ]
        ),
        "eligibility": row[
            "eligibility"
        ],
    }


def p02_scope_signature(rows):
    payload = json.dumps(
        [
            p02_scope_row_signature(
                row
            )
            for row in sorted(
                rows,
                key=lambda item: item[
                    "literal"
                ],
            )
        ],
        ensure_ascii=True,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )

    return hashlib.sha256(
        payload.encode(
            "ascii"
        )
    ).hexdigest()


def p02_current_nika():
    return p01_current_nika()


def p02_binding_map(bindings):
    by_literal = {}

    for binding in bindings:
        by_literal.setdefault(
            binding[
                "literal"
            ],
            [],
        ).append(
            binding
        )

    return by_literal


def p02_complete_scope():
    target = p02_current_nika()
    bindings = p01_all_supported_flex_bindings(
        target[
            "animset"
        ]
    )

    if not bindings:
        raise RuntimeError(
            "Nika has no supported live FLEX bindings."
        )

    literals = sorted(
        set(
            item[
                "literal"
            ]
            for item in bindings
        )
    )

    provider = get_semantic_provider()
    descriptor = provider.generation_descriptor()
    answers = provider.query_many(
        literals
    )
    scope = p01_scope_from_live_vocabulary(
        bindings,
        answers,
    )

    counts = scope[
        "counts"
    ]

    if counts[
        "absent"
    ] != 0:
        raise RuntimeError(
            "Complete Nika scope contains %d Master-absent supported FLEX literals."
            % counts[
                "absent"
            ]
        )

    if counts[
        "conflict"
    ] != 0:
        raise RuntimeError(
            "Complete Nika scope contains %d Master semantic conflicts."
            % counts[
                "conflict"
            ]
        )

    if counts[
        "binding_ambiguous"
    ] != 0:
        raise RuntimeError(
            "Complete Nika scope contains %d ambiguous live FLEX literals."
            % counts[
                "binding_ambiguous"
            ]
        )

    by_literal = p02_binding_map(
        bindings
    )

    accepted = {}

    for literal in scope[
        "accepted_expression_literals"
    ]:
        rows = by_literal.get(
            literal,
            [],
        )

        if len(rows) != 1:
            raise RuntimeError(
                "Expression literal %r did not resolve to exactly one supported live binding."
                % literal
            )

        accepted[
            literal
        ] = rows[0]

    if len(
        accepted
    ) != counts[
        "resolved_face"
    ]:
        raise RuntimeError(
            "Accepted Expression scope count does not match resolved Face count."
        )

    for literal in P02_HEAD_LITERALS:
        if literal not in accepted:
            raise RuntimeError(
                "Required head-shape sentinel %r is not in the Master-derived Face scope."
                % literal
            )

    body_row = p01_row_by_literal(
        scope,
        P02_BODY_SENTINEL,
    )

    if (
        body_row[
            "eligibility"
        ]
        != u"master-nonface"
        or body_row[
            "resolved_path"
        ]
        != u"Body Morphs"
    ):
        raise RuntimeError(
            "FBMfitness is not the expected Master non-Face sentinel: %r."
            % body_row
        )

    body_rows = by_literal.get(
        P02_BODY_SENTINEL,
        [],
    )

    if len(
        body_rows
    ) != 1:
        raise RuntimeError(
            "FBMfitness did not resolve to exactly one supported live binding."
        )

    scope_signature = p02_scope_signature(
        scope[
            "rows"
        ]
    )
    provider_stats = semantic_provider_runtime_stats()

    log_line(
        "SEMANTIC_SCOPE_RESOLVED signature=%s open_count=%d reuse_count=%d parse_count=%d query_batches=%d query_literals=%d"
        % (
            scope_signature,
            provider_stats["open_count"],
            provider_stats["reuse_count"],
            provider_stats["production_parse_count"],
            provider_stats["query_batch_count"],
            provider_stats["query_literal_count"],
        )
    )

    return {
        "target": target,
        "bindings": bindings,
        "by_literal": by_literal,
        "accepted": accepted,
        "body_binding": body_rows[
            0
        ],
        "body_row": body_row,
        "provider": provider,
        "provider_descriptor": descriptor,
        "scope": scope,
        "scope_signature": scope_signature,
    }


def p02_snapshot_supported(binding):
    snap = binding_snapshot(
        binding
    )

    for side_name, state in snap[
        "sides"
    ].items():
        if not coherent(
            state
        ):
            raise RuntimeError(
                "Unsupported static Expression state at %r/%s."
                % (
                    binding[
                        "literal"
                    ],
                    side_name,
                )
            )

    return snap


def p02_snapshot_matches_baseline(
    binding,
    baseline,
):
    observed = binding_snapshot(
        binding
    )

    if (
        observed[
            "literal"
        ]
        != baseline[
            "literal"
        ]
        or observed[
            "shape"
        ]
        != baseline[
            "shape"
        ]
        or observed[
            "global_key"
        ]
        != baseline[
            "global_key"
        ]
        or observed[
            "control_id"
        ]
        != baseline[
            "control_id"
        ]
    ):
        return False

    for side_name, side in binding[
        "sides"
    ]:
        old_state = baseline[
            "sides"
        ][
            side_name
        ]
        old_origin = state_kind(
            old_state
        )

        if not matches_baseline(
            observed[
                "sides"
            ][
                side_name
            ],
            old_state,
            old_origin,
        ):
            return False

    return True


def p02_saved_value_record(
    binding,
    snap,
):
    record = {
        "representation": binding[
            "shape"
        ],
    }

    if binding[
        "shape"
    ] == "MONO":
        record[
            "mono"
        ] = float(
            snap[
                "sides"
            ][
                "mono"
            ][
                "evaluated"
            ]
        )
        return record

    if binding[
        "shape"
    ] == "STEREO":
        record[
            "left"
        ] = float(
            snap[
                "sides"
            ][
                "left"
            ][
                "evaluated"
            ]
        )
        record[
            "right"
        ] = float(
            snap[
                "sides"
            ][
                "right"
            ][
                "evaluated"
            ]
        )
        return record

    raise RuntimeError(
        "Unsupported Expression representation %r."
        % binding[
            "shape"
        ]
    )


def p02_desired(
    record,
    side_name,
):
    if not isinstance(record, dict):
        raise RuntimeError(
            "Saved FLEX record is malformed."
        )

    representation = u(
        record.get(
            "representation"
        )
    )

    if representation == u"MONO":
        if side_name != "mono":
            raise RuntimeError(
                "MONO preset record requested for non-mono side."
            )

        desired = as_float(
            record.get(
                "mono"
            )
        )

        if desired is None:
            raise RuntimeError(
                "Saved FLEX value is not a finite number."
            )

        return desired

    if representation == u"STEREO":
        if side_name not in (
            "left",
            "right",
        ):
            raise RuntimeError(
                "STEREO preset record requested with invalid side."
            )

        desired = as_float(
            record.get(
                side_name
            )
        )

        if desired is None:
            raise RuntimeError(
                "Saved FLEX value is not a finite number."
            )

        return desired

    raise RuntimeError(
        "Unsupported saved Expression representation %r."
        % representation
    )


def p02_profile_and_preset(
    scope_state,
    snapshots,
):
    controls = {}
    values = {}
    semantic_rows = {}

    for row in scope_state[
        "scope"
    ][
        "rows"
    ]:
        literal = row[
            "literal"
        ]
        logical_id = (
            u"flex."
            + literal
        )

        semantic_rows[
            logical_id
        ] = p02_scope_row_signature(
            row
        )

        controls[
            logical_id
        ] = {
            "literal": literal,
            "representation": (
                row[
                    "live_shapes"
                ][0]
                if len(
                    row[
                        "live_shapes"
                    ]
                ) == 1
                else None
            ),
            "semantic_eligibility": row[
                "eligibility"
            ],
            "expression_capture": (
                row[
                    "eligibility"
                ]
                == u"expression-eligible"
            ),
            "expression_apply": (
                row[
                    "eligibility"
                ]
                == u"expression-eligible"
            ),
        }

    for literal in sorted(
        scope_state[
            "accepted"
        ].keys()
    ):
        binding = scope_state[
            "accepted"
        ][
            literal
        ]
        values[
            u"flex." + literal
        ] = p02_saved_value_record(
            binding,
            snapshots[
                literal
            ],
        )

    descriptor = scope_state[
        "provider_descriptor"
    ]
    accepted_ids = [
        u"flex." + literal
        for literal in sorted(
            scope_state[
                "accepted"
            ].keys()
        )
    ]

    profile = {
        "schema_version": P02_SCHEMA_VERSION,
        "profile_id": P02_PROFILE_ID,
        "revision": P02_PROFILE_REVISION,
        "display_name": "Nika Shark",
        "models": [
            {
                "path": P01_MODEL_PATH,
                "checksum": P01_MODEL_CHECKSUM,
                "status": "accepted",
            },
        ],
        "controls": controls,
        "expression_semantics": {
            "policy_id": P02_EXPRESSION_POLICY_ID,
            "scope_revision": P02_EXPRESSION_SCOPE_REVISION,
            "provider_contract": descriptor[
                "provider_contract"
            ],
            "adopted_source_sha256": descriptor[
                "source_sha256"
            ],
            "fold_policy": descriptor[
                "fold_policy"
            ],
            "provider_kind_at_adoption": descriptor[
                "provider_kind"
            ],
            "coverage": {
                "supported_live_flex_bindings": scope_state[
                    "scope"
                ][
                    "counts"
                ][
                    "supported_bindings"
                ],
                "unique_live_flex_literals": scope_state[
                    "scope"
                ][
                    "counts"
                ][
                    "unique_literals"
                ],
                "classification_row_count": len(
                    scope_state[
                        "scope"
                    ][
                        "rows"
                    ]
                ),
                "scope_signature_sha256": scope_state[
                    "scope_signature"
                ],
            },
            "classification_rows": semantic_rows,
            "accepted_expression_ids": accepted_ids,
            "local_overrides": [],
            "pending_semantic_review": False,
        },
    }

    preset = {
        "schema_version": P02_SCHEMA_VERSION,
        "preset_id": P02_PRESET_ID,
        "profile_id": P02_PROFILE_ID,
        "kind": "expression",
        "name": P02_PRESET_NAME,
        "capture_profile_revision": P02_PROFILE_REVISION,
        "capture_expression_scope_revision": (
            P02_EXPRESSION_SCOPE_REVISION
        ),
        "capture_master_source_sha256": descriptor[
            "source_sha256"
        ],
        "model_ref": {
            "path": P01_MODEL_PATH,
            "checksum": P01_MODEL_CHECKSUM,
        },
        "values": values,
    }

    return profile, preset


def p02_validate_disk(
    profile,
    preset,
):
    if profile.get(
        "schema_version"
    ) != P02_SCHEMA_VERSION:
        raise RuntimeError(
            "Saved Nika profile schema is unsupported."
        )

    if profile.get(
        "profile_id"
    ) != P02_PROFILE_ID:
        raise RuntimeError(
            "Saved Nika profile ID is unexpected."
        )

    semantics = profile.get(
        "expression_semantics"
    )

    if not isinstance(
        semantics,
        dict
    ):
        raise RuntimeError(
            "Saved Nika profile lacks Expression semantics."
        )

    if semantics.get(
        "policy_id"
    ) != P02_EXPRESSION_POLICY_ID:
        raise RuntimeError(
            "Saved Nika Expression policy is unexpected."
        )

    if semantics.get(
        "scope_revision"
    ) != P02_EXPRESSION_SCOPE_REVISION:
        raise RuntimeError(
            "Saved Nika Expression scope revision is unexpected."
        )

    if preset.get(
        "kind"
    ) != "expression":
        raise RuntimeError(
            "Saved P02 record is not an Expression preset."
        )

    if preset.get(
        "profile_id"
    ) != P02_PROFILE_ID:
        raise RuntimeError(
            "Saved P02 Expression belongs to another profile."
        )

    if preset.get(
        "capture_expression_scope_revision"
    ) != P02_EXPRESSION_SCOPE_REVISION:
        raise RuntimeError(
            "Saved P02 Expression scope revision is unexpected."
        )

    accepted_ids = semantics.get(
        "accepted_expression_ids"
    )
    values = preset.get(
        "values"
    )

    if not isinstance(
        accepted_ids,
        list
    ) or not isinstance(
        values,
        dict
    ):
        raise RuntimeError(
            "Saved P02 Expression scope/value records are malformed."
        )

    if set(
        accepted_ids
    ) != set(
        values.keys()
    ):
        raise RuntimeError(
            "Saved P02 Expression values do not exactly match the adopted accepted scope."
        )

    return True


def p02_compare_live_to_adopted(
    scope_state,
    profile,
):
    semantics = profile[
        "expression_semantics"
    ]
    adopted_rows = semantics[
        "classification_rows"
    ]
    live_rows = {}

    for row in scope_state[
        "scope"
    ][
        "rows"
    ]:
        live_rows[
            u"flex." + row[
                "literal"
            ]
        ] = p02_scope_row_signature(
            row
        )

    if set(
        live_rows.keys()
    ) != set(
        adopted_rows.keys()
    ):
        raise RuntimeError(
            "Current supported FLEX vocabulary does not match the adopted classified vocabulary."
        )

    changed = []

    for logical_id in sorted(
        live_rows.keys()
    ):
        if (
            live_rows[
                logical_id
            ]
            != adopted_rows[
                logical_id
            ]
        ):
            changed.append(
                logical_id
            )

    if changed:
        raise RuntimeError(
            "Current Master/live semantic result differs from the adopted scope for: %r"
            % changed
        )

    if (
        scope_state[
            "scope_signature"
        ]
        != semantics[
            "coverage"
        ][
            "scope_signature_sha256"
        ]
    ):
        raise RuntimeError(
            "Current semantic scope signature differs from the adopted scope."
        )

    return True


def p02_find_zero_mono_candidate(
    scope_state,
    snapshots,
):
    preferred = (
        u"A",
        u"E",
        u"I",
        u"O",
        u"U",
        u"MouthPucker",
        u"JawDrop",
    )

    ordered = list(
        preferred
    ) + [
        literal
        for literal in sorted(
            scope_state[
                "accepted"
            ].keys()
        )
        if literal not in preferred
    ]

    for literal in ordered:
        if literal in P02_HEAD_LITERALS:
            continue

        binding = scope_state[
            "accepted"
        ].get(
            literal
        )

        if (
            binding is None
            or binding[
                "shape"
            ] != "MONO"
        ):
            continue

        value = snapshots[
            literal
        ][
            "sides"
        ][
            "mono"
        ][
            "evaluated"
        ]

        if close_enough(
            value,
            0.0,
        ):
            return literal

    return None


def p02_find_stereo_candidate(
    scope_state,
):
    if (
        P02_PREFERRED_STEREO
        in scope_state[
            "accepted"
        ]
        and scope_state[
            "accepted"
        ][
            P02_PREFERRED_STEREO
        ][
            "shape"
        ] == "STEREO"
    ):
        return P02_PREFERRED_STEREO

    for literal in sorted(
        scope_state[
            "accepted"
        ].keys()
    ):
        if scope_state[
            "accepted"
        ][
            literal
        ][
            "shape"
        ] == "STEREO":
            return literal

    return None



# -------------------------------------------------------------------------------------------------
# Production Integration P03
# Integrated artist window acceptance
#
# Current semantic provider:
#   installed Master TXT bridge
#
# Future:
#   qualified Master sidecar swaps behind the same semantic provider seam.
#
# This checkpoint intentionally does not reopen primitive FLEX/Undo/Head-Scale
# research. It integrates the already-qualified behavior into one window.
# -------------------------------------------------------------------------------------------------

import shutil
import uuid


P03_BODY_POLICY_ID = u"master-body-morph-flex-v1"
P03_BODY_SCOPE_REVISION = 1
P03_ACCEPTANCE_BODY_ID = u"p03-acceptance-body-v1"
P03_ACCEPTANCE_BODY_NAME = u"P03 Acceptance Body"

P03_TRASH_DIRNAME = u"Trash"
P03_EXPORT_DIRNAME = u"Exports"
P03_LOGS_DIRNAME = u"Logs"

P03_BODY_FOLDER = u"Body Presets"
P03_EXPRESSION_FOLDER = u"Expressions"

P03_KIND_BODY = u"body"
P03_KIND_EXPRESSION = u"expression"

P03_MATCH_UNCHANGED = u"unchanged"
P03_MATCH_COMMITTED = u"committed"
P03_MATCH_FAILED_RESTORED = u"failed-restored"
P03_MATCH_FAILED_UNRECOVERED = u"failed-unrecovered"
P03_MATCH_COMMITTED_UNVERIFIED = u"committed-unverified"
P03_MATCH_UNATTEMPTED = u"unattempted"
P03_MATCH_FINAL_MISMATCH = u"final-mismatch"

P03_ACCEPTANCE_EXPORT_NAME = u"P03 Library Export.json"


def p03_now_stamp():
    return datetime.datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )


def p03_library_paths():
    base = p02_paths()

    return {
        "root": base["root"],
        "character_root": base["character_root"],
        "profile": base["profile"],
        "body_dir": os.path.join(
            base["character_root"],
            P03_BODY_FOLDER,
        ),
        "expression_dir": os.path.join(
            base["character_root"],
            P03_EXPRESSION_FOLDER,
        ),
        "trash": os.path.join(
            base["root"],
            P03_TRASH_DIRNAME,
        ),
        "exports": os.path.join(
            base["root"],
            P03_EXPORT_DIRNAME,
        ),
        "logs": os.path.join(
            base["root"],
            P03_LOGS_DIRNAME,
        ),
    }


def p03_profile():
    path = p03_library_paths()[
        "profile"
    ]

    if not os.path.isfile(path):
        raise RuntimeError(
            "Nika character profile has not been initialized."
        )

    profile = p02_read_json(
        path
    )

    if profile.get(
        "schema_version"
    ) != P02_SCHEMA_VERSION:
        raise RuntimeError(
            "Current Nika character profile schema is unsupported."
        )

    if profile.get(
        "profile_id"
    ) != P02_PROFILE_ID:
        raise RuntimeError(
            "Current Nika profile ID is unexpected."
        )

    return profile


def p03_json_candidates(folder):
    if not os.path.isdir(folder):
        return []

    result = []

    for filename in sorted(
        os.listdir(folder)
    ):
        lower = filename.lower()

        if not lower.endswith(
            ".json"
        ):
            continue

        if (
            ".tmp-" in lower
            or lower.endswith(
                ".bak"
            )
        ):
            continue

        path = os.path.join(
            folder,
            filename,
        )

        if os.path.isfile(
            path
        ):
            result.append(
                path
            )

    return result


def p03_validate_preset(
    record,
    expected_kind=None,
):
    if not isinstance(
        record,
        dict
    ):
        raise RuntimeError(
            "Preset is not a JSON object."
        )

    if record.get(
        "schema_version"
    ) != P02_SCHEMA_VERSION:
        raise RuntimeError(
            "Preset schema is unsupported."
        )

    if record.get(
        "profile_id"
    ) != P02_PROFILE_ID:
        raise RuntimeError(
            "Preset belongs to another Character profile."
        )

    kind = u(
        record.get(
            "kind"
        )
    )

    if kind not in (
        P03_KIND_BODY,
        P03_KIND_EXPRESSION,
    ):
        raise RuntimeError(
            "Preset kind is unsupported."
        )

    if (
        expected_kind is not None
        and kind != expected_kind
    ):
        raise RuntimeError(
            "Preset kind does not match the requested library."
        )

    preset_id = u(
        record.get(
            "preset_id"
        )
    )

    if not preset_id:
        raise RuntimeError(
            "Preset has no stable preset_id."
        )

    if not isinstance(
        record.get(
            "values"
        ),
        dict,
    ):
        raise RuntimeError(
            "Preset values are missing or malformed."
        )

    return True


def p03_discover_presets(kind):
    paths = p03_library_paths()

    if kind == P03_KIND_BODY:
        folder = paths[
            "body_dir"
        ]
    elif kind == P03_KIND_EXPRESSION:
        folder = paths[
            "expression_dir"
        ]
    else:
        raise RuntimeError(
            "Unsupported library kind."
        )

    result = []

    for path in p03_json_candidates(
        folder
    ):
        try:
            record = p02_read_json(
                path
            )
            p03_validate_preset(
                record,
                kind,
            )
        except Exception as exc:
            log_line(
                "P03_LIBRARY_SKIP path=%r error=%r"
                % (
                    path,
                    exc,
                )
            )
            continue

        result.append(
            {
                "path": path,
                "record": record,
            }
        )

    result.sort(
        key=lambda item: (
            u(
                item["record"].get(
                    "name"
                )
            ).lower(),
            u(
                item["record"].get(
                    "preset_id"
                )
            ),
        )
    )

    return result


def p03_unique_preset_path(
    kind,
    display_name,
    preset_id,
):
    paths = p03_library_paths()

    if kind == P03_KIND_BODY:
        folder = paths[
            "body_dir"
        ]
    else:
        folder = paths[
            "expression_dir"
        ]

    p02_ensure_dir(
        folder
    )

    safe_name = u(display_name)

    for ch in u'<>:"/\\|?*':
        safe_name = safe_name.replace(
            ch,
            u"_",
        )

    safe_name = safe_name.strip()

    if not safe_name:
        safe_name = u"Preset"

    suffix = u(
        preset_id
    )[:12]

    candidate = os.path.join(
        folder,
        safe_name
        + u"--"
        + suffix
        + u".json",
    )

    if not os.path.exists(
        candidate
    ):
        return candidate

    counter = 2

    while counter < 1000:
        candidate = os.path.join(
            folder,
            safe_name
            + u"--"
            + suffix
            + u"-"
            + unicode(counter)
            + u".json",
        )

        if not os.path.exists(
            candidate
        ):
            return candidate

        counter += 1

    raise RuntimeError(
        "Could not allocate a collision-free preset filename."
    )


def p03_body_scope(scope_state):
    rows = []
    accepted = {}

    by_literal = scope_state[
        "by_literal"
    ]

    for row in scope_state[
        "scope"
    ][
        "rows"
    ]:
        if (
            row[
                "semantic_status"
            ]
            != P01_STATUS_RESOLVED
            or row[
                "resolved_path"
            ]
            != u"Body Morphs"
        ):
            continue

        literal = row[
            "literal"
        ]
        bindings = by_literal.get(
            literal,
            [],
        )

        if len(bindings) != 1:
            raise RuntimeError(
                "Body Morph literal %r does not have exactly one supported live binding."
                % literal
            )

        rows.append(
            row
        )
        accepted[
            literal
        ] = bindings[
            0
        ]

    if not accepted:
        raise RuntimeError(
            "Master-derived Nika Body Morph scope is empty."
        )

    return {
        "rows": rows,
        "accepted": accepted,
        "signature": p02_scope_signature(
            rows
        ),
    }


def p03_profile_with_body_scope(
    profile,
    scope_state,
    body_scope,
):
    result = json.loads(
        json.dumps(
            profile
        )
    )

    controls = result.setdefault(
        "controls",
        {},
    )

    classification_rows = {}

    for row in body_scope[
        "rows"
    ]:
        literal = row[
            "literal"
        ]
        logical_id = (
            u"flex."
            + literal
        )

        classification_rows[
            logical_id
        ] = p02_scope_row_signature(
            row
        )

        entry = controls.setdefault(
            logical_id,
            {},
        )

        entry[
            "literal"
        ] = literal
        entry[
            "representation"
        ] = row[
            "live_shapes"
        ][0]
        entry[
            "body_capture"
        ] = True
        entry[
            "body_apply"
        ] = True

        # Preserve independent Expression permissions.
        if (
            "expression_capture"
            not in entry
        ):
            entry[
                "expression_capture"
            ] = False

        if (
            "expression_apply"
            not in entry
        ):
            entry[
                "expression_apply"
            ] = False

    descriptor = scope_state[
        "provider_descriptor"
    ]

    result[
        "body_semantics"
    ] = {
        "policy_id": P03_BODY_POLICY_ID,
        "scope_revision": P03_BODY_SCOPE_REVISION,
        "provider_contract": descriptor[
            "provider_contract"
        ],
        "adopted_source_sha256": descriptor[
            "source_sha256"
        ],
        "fold_policy": descriptor[
            "fold_policy"
        ],
        "provider_kind_at_adoption": descriptor[
            "provider_kind"
        ],
        "coverage": {
            "accepted_body_controls": len(
                body_scope[
                    "accepted"
                ]
            ),
            "scope_signature_sha256": body_scope[
                "signature"
            ],
        },
        "classification_rows": classification_rows,
        "accepted_body_ids": [
            u"flex." + literal
            for literal in sorted(
                body_scope[
                    "accepted"
                ].keys()
            )
        ],
        "local_overrides": [],
        "pending_semantic_review": False,
    }

    result.setdefault(
        "default_body_preset_id",
        None,
    )

    return result


def p03_capture_values(
    accepted,
):
    values = {}
    snapshots = {}

    for literal in sorted(
        accepted.keys()
    ):
        binding = accepted[
            literal
        ]
        snap = p02_snapshot_supported(
            binding
        )

        snapshots[
            literal
        ] = snap
        values[
            u"flex." + literal
        ] = p02_saved_value_record(
            binding,
            snap,
        )

    return values, snapshots


def p03_save_current_body():
    scope_state = p02_complete_scope()
    body_scope = p03_body_scope(
        scope_state
    )
    values, snapshots = p03_capture_values(
        body_scope[
            "accepted"
        ]
    )

    profile = p03_profile()
    merged_profile = p03_profile_with_body_scope(
        profile,
        scope_state,
        body_scope,
    )

    preset = {
        "schema_version": P02_SCHEMA_VERSION,
        "preset_id": P03_ACCEPTANCE_BODY_ID,
        "profile_id": P02_PROFILE_ID,
        "kind": P03_KIND_BODY,
        "name": P03_ACCEPTANCE_BODY_NAME,
        "capture_profile_revision": merged_profile.get(
            "revision",
            P02_PROFILE_REVISION,
        ),
        "capture_body_scope_revision": P03_BODY_SCOPE_REVISION,
        "capture_master_source_sha256": scope_state[
            "provider_descriptor"
        ][
            "source_sha256"
        ],
        "model_ref": {
            "path": P01_MODEL_PATH,
            "checksum": P01_MODEL_CHECKSUM,
        },
        "values": values,
    }

    paths = p03_library_paths()
    p02_ensure_dir(
        paths[
            "body_dir"
        ]
    )

    preset_path = os.path.join(
        paths[
            "body_dir"
        ],
        u"P03 Acceptance Body--p03-acceptance-body-v1.json",
    )

    p02_safe_write_json(
        paths[
            "profile"
        ],
        merged_profile,
    )
    p02_safe_write_json(
        preset_path,
        preset,
    )

    loaded_profile = p02_read_json(
        paths[
            "profile"
        ]
    )
    loaded_preset = p02_read_json(
        preset_path
    )

    p03_validate_preset(
        loaded_preset,
        P03_KIND_BODY,
    )

    if (
        loaded_profile.get(
            "expression_semantics"
        )
        != profile.get(
            "expression_semantics"
        )
    ):
        raise RuntimeError(
            "Adding Body scope changed the adopted Expression semantics."
        )

    if set(
        loaded_preset[
            "values"
        ].keys()
    ) != set(
        merged_profile[
            "body_semantics"
        ][
            "accepted_body_ids"
        ]
    ):
        raise RuntimeError(
            "Saved Body preset does not exactly match the adopted Body scope."
        )

    log_line(
        "P03_BODY_SAVE=PASS controls=%d path=%r expression_semantics_preserved=True"
        % (
            len(
                values
            ),
            preset_path,
        )
    )

    return {
        "path": preset_path,
        "record": loaded_preset,
        "capture_snapshots": snapshots,
    }


def p03_scope_for_kind(
    kind,
    profile,
):
    scope_state = p02_complete_scope()

    if kind == P03_KIND_EXPRESSION:
        p02_compare_live_to_adopted(
            scope_state,
            profile,
        )

        accepted = scope_state[
            "accepted"
        ]

        expected_ids = set(
            profile[
                "expression_semantics"
            ][
                "accepted_expression_ids"
            ]
        )

    elif kind == P03_KIND_BODY:
        body_scope = p03_body_scope(
            scope_state
        )
        semantics = profile.get(
            "body_semantics"
        )

        if not isinstance(
            semantics,
            dict,
        ):
            raise RuntimeError(
                "Character profile has no adopted Body scope."
            )

        if (
            semantics.get(
                "scope_signature_sha256"
            )
            is not None
        ):
            # Older/provisional layout compatibility.
            expected_sig = semantics[
                "scope_signature_sha256"
            ]
        else:
            expected_sig = semantics[
                "coverage"
            ][
                "scope_signature_sha256"
            ]

        if (
            body_scope[
                "signature"
            ]
            != expected_sig
        ):
            raise RuntimeError(
                "Current Master-derived Body scope differs from the adopted Body scope."
            )

        accepted = body_scope[
            "accepted"
        ]
        expected_ids = set(
            semantics[
                "accepted_body_ids"
            ]
        )

    else:
        raise RuntimeError(
            "Unsupported preset kind."
        )

    actual_ids = set(
        u"flex." + literal
        for literal in accepted.keys()
    )

    if actual_ids != expected_ids:
        raise RuntimeError(
            "Current required %s scope does not match the adopted profile."
            % kind
        )

    return scope_state, accepted


def p03_build_plan(
    accepted,
    preset,
):
    values = preset[
        "values"
    ]
    expected = set(
        u"flex." + literal
        for literal in accepted.keys()
    )

    if set(
        values.keys()
    ) != expected:
        raise RuntimeError(
            "Preset values do not exactly match the current required scope."
        )

    baselines = {}
    plan = []
    changed_sides = 0

    for literal in sorted(
        accepted.keys()
    ):
        binding = accepted[
            literal
        ]
        snap = p02_snapshot_supported(
            binding
        )
        baselines[
            literal
        ] = snap

        record = values[
            u"flex." + literal
        ]

        if record.get(
            "representation"
        ) != binding[
            "shape"
        ]:
            raise RuntimeError(
                "Representation mismatch for %r."
                % literal
            )

        for side_name, side in binding[
            "sides"
        ]:
            state = snap[
                "sides"
            ][
                side_name
            ]
            origin = state_kind(
                state
            )

            if origin == "UNSUPPORTED":
                raise RuntimeError(
                    "Current state is unsupported at %r/%s."
                    % (
                        literal,
                        side_name,
                    )
                )

            desired = p02_desired(
                record,
                side_name,
            )

            if desired is None:
                raise RuntimeError(
                    "Saved value is invalid at %r/%s."
                    % (
                        literal,
                        side_name,
                    )
                )

            needs_write = not matches_value(
                state,
                desired,
            )

            if needs_write:
                changed_sides += 1

            plan.append(
                {
                    "literal": literal,
                    "binding": binding,
                    "side_name": side_name,
                    "side": side,
                    "origin": origin,
                    "desired": desired,
                    "needs_write": needs_write,
                }
            )

    return {
        "plan": plan,
        "baselines": baselines,
        "changed_sides": changed_sides,
    }


def p03_verify_saved_values(
    accepted,
    preset,
):
    values = preset[
        "values"
    ]

    for literal in sorted(
        accepted.keys()
    ):
        binding = accepted[
            literal
        ]
        observed = binding_snapshot(
            binding
        )
        record = values[
            u"flex." + literal
        ]

        for side_name, side in binding[
            "sides"
        ]:
            desired = p02_desired(
                record,
                side_name,
            )

            if not matches_value(
                observed[
                    "sides"
                ][
                    side_name
                ],
                desired,
            ):
                return False

    return True


def p03_verify_baselines(
    accepted,
    baselines,
):
    for literal in sorted(
        accepted.keys()
    ):
        if not p02_snapshot_matches_baseline(
            accepted[
                literal
            ],
            baselines[
                literal
            ],
        ):
            return False

    return True


def p03_apply_preset(
    preset_path,
    kind,
):
    preset = p02_read_json(
        preset_path
    )
    p03_validate_preset(
        preset,
        kind,
    )

    profile = p03_profile()
    scope_state, accepted = p03_scope_for_kind(
        kind,
        profile,
    )

    built = p03_build_plan(
        accepted,
        preset,
    )

    undo_before = undo_state(
        "P03_%s_UNDO_BEFORE"
        % kind.upper()
    )

    if built[
        "changed_sides"
    ] == 0:
        undo_after = undo_state(
            "P03_%s_UNDO_AFTER_NOOP"
            % kind.upper()
        )

        if undo_after != undo_before:
            raise RuntimeError(
                "A true no-op changed native Undo state."
            )

        log_line(
            "P03_SHARED_EXECUTOR kind=%r outcome='no-op' changed_sides=0 undo_unchanged=True"
            % kind
        )

        return {
            "outcome": "no-op",
            "kind": kind,
            "preset": preset,
            "baselines": built[
                "baselines"
            ],
            "changed_sides": 0,
            "undo_before": undo_before,
            "undo_after": undo_after,
        }

    dm_obj = dm()
    scope_open = False

    undo_name = (
        u"Apply Body Preset"
        if kind == P03_KIND_BODY
        else u"Apply Expression"
    )

    try:
        dm_obj.StartUndo(
            b(
                undo_name
            ),
            b(
                u"Redo "
                + undo_name
            ),
        )
        scope_open = True

        for item in built[
            "plan"
        ]:
            if not item[
                "needs_write"
            ]:
                continue

            write_side(
                item[
                    "binding"
                ],
                item[
                    "side"
                ],
                item[
                    "origin"
                ],
                item[
                    "desired"
                ],
            )

        if not p03_verify_saved_values(
            accepted,
            preset,
        ):
            raise RuntimeError(
                "Authored preset verification failed before commit."
            )

        dm_obj.FinishUndo()
        scope_open = False

    except Exception:
        if scope_open:
            dm_obj.AbortUndoableOperation()

            # Verify exact supported baseline after owned abort.
            scope_after_abort, accepted_after_abort = p03_scope_for_kind(
                kind,
                profile,
            )

            if not p03_verify_baselines(
                accepted_after_abort,
                built[
                    "baselines"
                ],
            ):
                raise RuntimeError(
                    "Preset Apply failed and owned rollback could not be verified."
                )

        raise

    head_time = float(
        sfmApp.GetHeadTimeInSeconds()
    )

    same_time_refresh(
        head_time,
        "P03_%s_APPLY"
        % kind.upper(),
    )

    # Fresh resolution after the event-loop boundary.
    scope_after, accepted_after = p03_scope_for_kind(
        kind,
        profile,
    )

    if not p03_verify_saved_values(
        accepted_after,
        preset,
    ):
        log_line(
            "P03_SHARED_EXECUTOR kind=%r outcome='committed-unverified' changed_sides=%d"
            % (
                kind,
                built[
                    "changed_sides"
                ],
            )
        )
        raise RuntimeError(
            "Preset committed, but post-refresh verification failed. Use SFM Undo."
        )

    undo_after = undo_state(
        "P03_%s_UNDO_AFTER_COMMIT"
        % kind.upper()
    )

    result = {
        "outcome": "committed",
        "kind": kind,
        "preset": preset,
        "baselines": built[
            "baselines"
        ],
        "changed_sides": built[
            "changed_sides"
        ],
        "undo_before": undo_before,
        "undo_after": undo_after,
        "head_time": head_time,
    }

    log_line(
        "P03_SHARED_EXECUTOR kind=%r outcome='committed' changed_sides=%d"
        % (
            kind,
            built[
                "changed_sides"
            ],
        )
    )

    return result


def p03_verify_undo_result(
    apply_result,
):
    if apply_result.get(
        "outcome"
    ) != "committed":
        raise RuntimeError(
            "There is no committed Apply to verify."
        )

    kind = apply_result[
        "kind"
    ]
    profile = p03_profile()

    same_time_refresh(
        apply_result[
            "head_time"
        ],
        "P03_%s_UNDO_VERIFY"
        % kind.upper(),
    )

    scope_state, accepted = p03_scope_for_kind(
        kind,
        profile,
    )

    if not p03_verify_baselines(
        accepted,
        apply_result[
            "baselines"
        ],
    ):
        raise RuntimeError(
            "One native Undo did not restore the supported pre-Apply %s state."
            % kind
        )

    log_line(
        "P03_NATIVE_UNDO_VERIFY=PASS kind=%r restored_supported_baseline=True"
        % kind
    )

    return True


# -------------------------------------------------------------------------------------------------
# Library operations used by the integrated window and acceptance routine.
# -------------------------------------------------------------------------------------------------


def p03_find_preset_by_id(
    kind,
    preset_id,
):
    for item in p03_discover_presets(
        kind
    ):
        if u(
            item[
                "record"
            ].get(
                "preset_id"
            )
        ) == u(
            preset_id
        ):
            return item

    return None


def p03_duplicate_preset(
    source_path,
):
    record = p02_read_json(
        source_path
    )
    p03_validate_preset(
        record
    )

    duplicate = json.loads(
        json.dumps(
            record
        )
    )

    new_id = u"copy-" + unicode(
        uuid.uuid4().hex
    )
    duplicate[
        "preset_id"
    ] = new_id
    duplicate[
        "name"
    ] = u(
        record.get(
            "name"
        )
    ) + u" Copy"

    target = p03_unique_preset_path(
        u(
            duplicate[
                "kind"
            ]
        ),
        u(
            duplicate[
                "name"
            ]
        ),
        new_id,
    )

    p02_safe_write_json(
        target,
        duplicate,
    )

    return target, duplicate


def p03_rename_preset(
    path,
    new_name,
):
    record = p02_read_json(
        path
    )
    p03_validate_preset(
        record
    )

    record[
        "name"
    ] = u(
        new_name
    )

    # Physical filename intentionally remains stable.
    p02_safe_write_json(
        path,
        record,
    )

    return record


def p03_set_default_body(
    preset_id,
):
    profile = p03_profile()

    if preset_id is not None:
        item = p03_find_preset_by_id(
            P03_KIND_BODY,
            preset_id,
        )

        if item is None:
            raise RuntimeError(
                "Default Body preset does not exist."
            )

    previous = profile.get(
        "default_body_preset_id"
    )
    profile[
        "default_body_preset_id"
    ] = preset_id

    p02_safe_write_json(
        p03_library_paths()[
            "profile"
        ],
        profile,
    )

    return previous


def p03_move_to_trash(
    path,
):
    record = p02_read_json(
        path
    )
    p03_validate_preset(
        record
    )

    paths = p03_library_paths()
    p02_ensure_dir(
        paths[
            "trash"
        ]
    )

    basename = os.path.basename(
        path
    )
    target = os.path.join(
        paths[
            "trash"
        ],
        p03_now_stamp()
        + u"--"
        + basename,
    )

    result = ctypes.windll.kernel32.MoveFileExW(
        ctypes.c_wchar_p(path),
        ctypes.c_wchar_p(target),
        0,
    )

    if not result:
        code = ctypes.windll.kernel32.GetLastError()
        raise RuntimeError(
            "Could not move preset to Trash (Windows error %d)."
            % code
        )

    if (
        record[
            "kind"
        ] == P03_KIND_BODY
    ):
        profile = p03_profile()

        if profile.get(
            "default_body_preset_id"
        ) == record[
            "preset_id"
        ]:
            profile[
                "default_body_preset_id"
            ] = None
            p02_safe_write_json(
                paths[
                    "profile"
                ],
                profile,
            )

    return target, record


def p03_export_preset(
    source_path,
    target_path,
):
    record = p02_read_json(
        source_path
    )
    p03_validate_preset(
        record
    )

    p02_ensure_dir(
        os.path.dirname(
            target_path
        )
    )

    if os.path.exists(
        target_path
    ):
        os.remove(
            target_path
        )

    shutil.copy2(
        source_path,
        target_path,
    )

    exported = p02_read_json(
        target_path
    )

    if exported != record:
        raise RuntimeError(
            "Exported preset did not validate against the source."
        )

    return target_path


def p03_import_as_copy(
    source_path,
):
    record = p02_read_json(
        source_path
    )
    p03_validate_preset(
        record
    )

    imported = json.loads(
        json.dumps(
            record
        )
    )

    imported[
        "preset_id"
    ] = (
        u"import-"
        + unicode(
            uuid.uuid4().hex
        )
    )
    imported[
        "name"
    ] = (
        u(
            record.get(
                "name"
            )
        )
        + u" Imported"
    )

    target = p03_unique_preset_path(
        u(
            imported[
                "kind"
            ]
        ),
        u(
            imported[
                "name"
            ]
        ),
        u(
            imported[
                "preset_id"
            ]
        ),
    )

    p02_safe_write_json(
        target,
        imported,
    )

    return target, imported


# -------------------------------------------------------------------------------------------------
# Body Match production executor.
# -------------------------------------------------------------------------------------------------


def p03_safe_call(
    obj,
    method_name,
    *args
):
    try:
        return getattr(
            obj,
            method_name,
        )(
            *args
        )
    except Exception:
        return None


def p03_native_index(
    game_model,
):
    hdr = game_model.GetStudioHdr()

    if hdr is None:
        raise RuntimeError(
            "GetStudioHdr failed."
        )

    try:
        count = int(
            hdr.numflexcontrollers()
        )
    except Exception:
        count = int(
            hdr.numflexcontrollers
        )

    if count < 0 or count > 4096:
        raise RuntimeError(
            "Native controller count exceeded safety cap."
        )

    result = {}

    for index in range(
        count
    ):
        controller = p03_safe_call(
            hdr,
            "pFlexcontroller",
            index,
        )

        if controller is None:
            continue

        try:
            gid = int(
                controller.localToGlobal
            )
        except Exception:
            continue

        result.setdefault(
            gid,
            [],
        ).append(
            {
                "name": u(
                    p03_safe_call(
                        controller,
                        "pszName",
                    )
                ),
                "type": u(
                    p03_safe_call(
                        controller,
                        "pszType",
                    )
                ),
                "min": float(
                    controller.min
                ),
                "max": float(
                    controller.max
                ),
            }
        )

    return result


def p03_unique_native(
    native,
    gid,
):
    rows = native.get(
        gid,
        [],
    )

    if len(rows) != 1:
        return None

    return rows[
        0
    ]


def p03_native_pair_compatible(
    source_native,
    target_native,
    source_binding,
    target_binding,
):
    if source_binding[
        "shape"
    ] != target_binding[
        "shape"
    ]:
        return False

    if len(
        source_binding[
            "sides"
        ]
    ) != len(
        target_binding[
            "sides"
        ]
    ):
        return False

    for (
        source_side_name,
        source_side,
    ), (
        target_side_name,
        target_side,
    ) in zip(
        source_binding[
            "sides"
        ],
        target_binding[
            "sides"
        ],
    ):
        if source_side_name != target_side_name:
            return False

        source_record = p03_unique_native(
            source_native,
            source_side[
                "global"
            ],
        )
        target_record = p03_unique_native(
            target_native,
            target_side[
                "global"
            ],
        )

        if (
            source_record is None
            or target_record is None
        ):
            return False

        if not (
            close_enough(
                source_record[
                    "min"
                ],
                target_record[
                    "min"
                ],
            )
            and close_enough(
                source_record[
                    "max"
                ],
                target_record[
                    "max"
                ],
            )
            and u(
                source_record[
                    "name"
                ]
            ).lower()
            == u(
                target_record[
                    "name"
                ]
            ).lower()
            and u(
                source_record[
                    "type"
                ]
            ).lower()
            == u(
                target_record[
                    "type"
                ]
            ).lower()
        ):
            return False

    return True


def p03_build_mapping(
    source_list,
    source_native,
    target_list,
    target_native,
):
    source_index = {}
    target_index = {}

    for binding in source_list:
        source_index.setdefault(
            binding[
                "global_key"
            ],
            [],
        ).append(
            binding
        )

    for binding in target_list:
        target_index.setdefault(
            binding[
                "global_key"
            ],
            [],
        ).append(
            binding
        )

    mappings = []
    ambiguous = []
    incompatible = []

    for global_key in sorted(
        source_index.keys(),
        key=lambda value: repr(
            value
        ),
    ):
        sources = source_index.get(
            global_key,
            [],
        )
        targets = target_index.get(
            global_key,
            [],
        )

        if len(
            sources
        ) != 1:
            ambiguous.append(
                (
                    global_key,
                    "SOURCE_DUPLICATE",
                )
            )
            continue

        if len(
            targets
        ) == 0:
            continue

        if len(
            targets
        ) != 1:
            ambiguous.append(
                (
                    global_key,
                    "TARGET_DUPLICATE",
                )
            )
            continue

        source_binding = sources[
            0
        ]
        target_binding = targets[
            0
        ]

        if not p03_native_pair_compatible(
            source_native,
            target_native,
            source_binding,
            target_binding,
        ):
            incompatible.append(
                (
                    global_key,
                    source_binding[
                        "literal"
                    ],
                    target_binding[
                        "literal"
                    ],
                )
            )
            continue

        mappings.append(
            {
                "source": source_binding,
                "target": target_binding,
            }
        )

    return {
        "mappings": mappings,
        "ambiguous": ambiguous,
        "incompatible": incompatible,
    }


def p03_model_animsets():
    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        raise RuntimeError(
            "No current shot."
        )

    result = []

    for animset in list(
        shot.animationSets
    ):
        gm = get_game_model(
            animset
        )

        if gm is None:
            continue

        try:
            check = checksum(
                gm
            )
            asset = model_asset(
                gm
            )
        except Exception:
            continue

        result.append(
            {
                "shot": shot,
                "animset": animset,
                "gm": gm,
                "name": name(
                    animset
                ),
                "model": asset,
                "checksum": check,
            }
        )

    return result


def p03_resolve_target(
    wanted_name,
    wanted_model,
    wanted_checksum,
):
    matches = []

    for row in p03_model_animsets():
        if (
            row[
                "name"
            ] == wanted_name
            and row[
                "model"
            ] == wanted_model
            and row[
                "checksum"
            ] == wanted_checksum
        ):
            matches.append(
                row
            )

    if len(
        matches
    ) != 1:
        raise RuntimeError(
            "Could not freshly resolve clothing target %r; found %d."
            % (
                wanted_name,
                len(
                    matches
                ),
            )
        )

    return matches[
        0
    ]


def p03_target_bindings(
    animset,
):
    return p01_all_supported_flex_bindings(
        animset
    )


def p03_clothing_candidates():
    scope_state = p02_complete_scope()
    body_scope = p03_body_scope(
        scope_state
    )

    source = scope_state[
        "target"
    ]
    source_list = [
        body_scope[
            "accepted"
        ][literal]
        for literal in sorted(
            body_scope[
                "accepted"
            ].keys()
        )
    ]
    source_native = p03_native_index(
        source[
            "gm"
        ]
    )

    candidates = []

    for row in p03_model_animsets():
        if same_dme(
            row[
                "animset"
            ],
            source[
                "animset"
            ],
        ):
            continue

        target_list = p03_target_bindings(
            row[
                "animset"
            ]
        )

        if not target_list:
            continue

        target_native = p03_native_index(
            row[
                "gm"
            ]
        )

        mapping = p03_build_mapping(
            source_list,
            source_native,
            target_list,
            target_native,
        )

        if not mapping[
            "mappings"
        ]:
            continue

        candidates.append(
            {
                "name": row[
                    "name"
                ],
                "model": row[
                    "model"
                ],
                "checksum": row[
                    "checksum"
                ],
                "mapping_count": len(
                    mapping[
                        "mappings"
                    ]
                ),
                "ambiguous_count": len(
                    mapping[
                        "ambiguous"
                    ]
                ),
                "incompatible_count": len(
                    mapping[
                        "incompatible"
                    ]
                ),
            }
        )

    candidates.sort(
        key=lambda item: (
            item[
                "name"
            ],
            item[
                "model"
            ],
        )
    )

    return candidates



def p03_unmapped_relevant_controls(
    source_scope,
    target_list,
    mapping,
):
    matched_keys = set(
        pair[
            "target"
        ][
            "global_key"
        ]
        for pair in mapping[
            "mappings"
        ]
    )

    pending = []

    for binding in target_list:
        if binding[
            "global_key"
        ] in matched_keys:
            continue

        pending.append(
            binding[
                "literal"
            ]
        )

    if not pending:
        return []

    answers = source_scope[
        "provider"
    ].query_many(
        sorted(
            set(
                pending
            )
        )
    )

    rows = []

    for binding in target_list:
        if binding[
            "global_key"
        ] in matched_keys:
            continue

        answer = answers.get(
            binding[
                "literal"
            ]
        )

        if not answer:
            continue

        if answer.get(
            "status"
        ) != P01_STATUS_RESOLVED:
            continue

        path = answer.get(
            "resolved_path"
        )

        if path not in (
            u"Body Morphs",
            u"Clothing",
        ):
            continue

        rows.append(
            {
                "literal": binding[
                    "literal"
                ],
                "shape": binding[
                    "shape"
                ],
                "master_path": path,
            }
        )

    rows.sort(
        key=lambda row: (
            row[
                "master_path"
            ],
            row[
                "literal"
            ],
        )
    )

    return rows


def p03_target_plan(
    source_scope,
    source_snapshots,
    target_row,
):
    target = p03_resolve_target(
        target_row[
            "name"
        ],
        target_row[
            "model"
        ],
        target_row[
            "checksum"
        ],
    )

    source = source_scope[
        "target"
    ]
    body_scope = p03_body_scope(
        source_scope
    )

    source_list = [
        body_scope[
            "accepted"
        ][literal]
        for literal in sorted(
            body_scope[
                "accepted"
            ].keys()
        )
    ]

    source_native = p03_native_index(
        source[
            "gm"
        ]
    )
    target_list = p03_target_bindings(
        target[
            "animset"
        ]
    )
    target_native = p03_native_index(
        target[
            "gm"
        ]
    )

    mapping = p03_build_mapping(
        source_list,
        source_native,
        target_list,
        target_native,
    )

    unmapped_relevant = p03_unmapped_relevant_controls(
        source_scope,
        target_list,
        mapping,
    )

    if mapping[
        "ambiguous"
    ]:
        raise RuntimeError(
            "Body Match target %r has ambiguous established mappings."
            % target[
                "name"
            ]
        )

    entries = []
    changed_sides = 0

    for pair in mapping[
        "mappings"
    ]:
        source_binding = pair[
            "source"
        ]
        target_binding = pair[
            "target"
        ]

        source_snap = source_snapshots[
            source_binding[
                "literal"
            ]
        ]
        target_snap = p02_snapshot_supported(
            target_binding
        )

        side_entries = []

        for (
            source_side_name,
            source_side,
        ), (
            target_side_name,
            target_side,
        ) in zip(
            source_binding[
                "sides"
            ],
            target_binding[
                "sides"
            ],
        ):
            desired = source_snap[
                "sides"
            ][
                source_side_name
            ][
                "evaluated"
            ]
            state = target_snap[
                "sides"
            ][
                target_side_name
            ]
            origin = state_kind(
                state
            )

            if origin == "UNSUPPORTED":
                raise RuntimeError(
                    "Target %r has unsupported state at %r/%s."
                    % (
                        target[
                            "name"
                        ],
                        target_binding[
                            "literal"
                        ],
                        target_side_name,
                    )
                )

            needs_write = not matches_value(
                state,
                desired,
            )

            if needs_write:
                changed_sides += 1

            side_entries.append(
                {
                    "side_name": target_side_name,
                    "side": target_side,
                    "origin": origin,
                    "baseline": state,
                    "desired": desired,
                    "needs_write": needs_write,
                }
            )

        entries.append(
            {
                "target_binding": target_binding,
                "target_baseline": target_snap,
                "sides": side_entries,
            }
        )

    return {
        "identity": {
            "name": target[
                "name"
            ],
            "model": target[
                "model"
            ],
            "checksum": target[
                "checksum"
            ],
        },
        "mapping": mapping,
        "entries": entries,
        "changed_sides": changed_sides,
        "unmapped_relevant": unmapped_relevant,
    }


def p03_target_matches_plan(
    target_plan,
):
    target = p03_resolve_target(
        target_plan[
            "identity"
        ][
            "name"
        ],
        target_plan[
            "identity"
        ][
            "model"
        ],
        target_plan[
            "identity"
        ][
            "checksum"
        ],
    )

    current_bindings = p03_target_bindings(
        target[
            "animset"
        ]
    )
    by_key = {}

    for binding in current_bindings:
        by_key.setdefault(
            binding[
                "global_key"
            ],
            [],
        ).append(
            binding
        )

    for entry in target_plan[
        "entries"
    ]:
        old_binding = entry[
            "target_binding"
        ]
        matches = by_key.get(
            old_binding[
                "global_key"
            ],
            [],
        )

        if len(
            matches
        ) != 1:
            return False

        observed = binding_snapshot(
            matches[
                0
            ]
        )

        for side_entry in entry[
            "sides"
        ]:
            if not matches_value(
                observed[
                    "sides"
                ][
                    side_entry[
                        "side_name"
                    ]
                ],
                side_entry[
                    "desired"
                ],
            ):
                return False

    return True


def p03_target_matches_baseline(
    target_plan,
):
    target = p03_resolve_target(
        target_plan[
            "identity"
        ][
            "name"
        ],
        target_plan[
            "identity"
        ][
            "model"
        ],
        target_plan[
            "identity"
        ][
            "checksum"
        ],
    )

    current_bindings = p03_target_bindings(
        target[
            "animset"
        ]
    )
    by_key = {}

    for binding in current_bindings:
        by_key.setdefault(
            binding[
                "global_key"
            ],
            [],
        ).append(
            binding
        )

    for entry in target_plan[
        "entries"
    ]:
        old_binding = entry[
            "target_binding"
        ]
        matches = by_key.get(
            old_binding[
                "global_key"
            ],
            [],
        )

        if len(
            matches
        ) != 1:
            return False

        current = matches[
            0
        ]
        observed = binding_snapshot(
            current
        )

        baseline = entry[
            "target_baseline"
        ]

        if (
            observed[
                "literal"
            ] != baseline[
                "literal"
            ]
            or observed[
                "shape"
            ] != baseline[
                "shape"
            ]
            or observed[
                "control_id"
            ] != baseline[
                "control_id"
            ]
        ):
            return False

        for side_entry in entry[
            "sides"
        ]:
            if not matches_baseline(
                observed[
                    "sides"
                ][
                    side_entry[
                        "side_name"
                    ]
                ],
                side_entry[
                    "baseline"
                ],
                side_entry[
                    "origin"
                ],
            ):
                return False

    return True


def p03_apply_body_match(
    selected_targets,
):
    if not selected_targets:
        raise RuntimeError(
            "Select at least one clothing item."
        )

    source_scope = p02_complete_scope()
    body_scope = p03_body_scope(
        source_scope
    )
    source_values, source_snapshots = p03_capture_values(
        body_scope[
            "accepted"
        ]
    )

    plans = []

    for target_row in selected_targets:
        plan = p03_target_plan(
            source_scope,
            source_snapshots,
            target_row,
        )
        plans.append(
            plan
        )

        log_line(
            "P03_BODY_MATCH_PLAN target=%r mappings=%d changed_sides=%d "
            "incompatible=%d unmapped_relevant=%r"
            % (
                plan[
                    "identity"
                ][
                    "name"
                ],
                len(
                    plan[
                        "mapping"
                    ][
                        "mappings"
                    ]
                ),
                plan[
                    "changed_sides"
                ],
                len(
                    plan[
                        "mapping"
                    ][
                        "incompatible"
                    ]
                ),
                plan[
                    "unmapped_relevant"
                ],
            )
        )

    outcomes = []

    for index, target_plan in enumerate(
        plans
    ):
        identity = target_plan[
            "identity"
        ]

        if target_plan[
            "changed_sides"
        ] == 0:
            outcomes.append(
                {
                    "target": identity[
                        "name"
                    ],
                    "status": P03_MATCH_UNCHANGED,
                    "changed_sides": 0,
                }
            )
            continue

        dm_obj = dm()
        scope_open = False

        try:
            dm_obj.StartUndo(
                b(
                    u"Match Clothing: "
                    + u(
                        identity[
                            "name"
                        ]
                    )
                ),
                b(
                    u"Redo Match Clothing: "
                    + u(
                        identity[
                            "name"
                        ]
                    )
                ),
            )
            scope_open = True

            for entry in target_plan[
                "entries"
            ]:
                binding = entry[
                    "target_binding"
                ]

                for side_entry in entry[
                    "sides"
                ]:
                    if not side_entry[
                        "needs_write"
                    ]:
                        continue

                    write_side(
                        binding,
                        side_entry[
                            "side"
                        ],
                        side_entry[
                            "origin"
                        ],
                        side_entry[
                            "desired"
                        ],
                    )

            # Verify authored values while transaction ownership is still clear.
            for entry in target_plan[
                "entries"
            ]:
                observed = binding_snapshot(
                    entry[
                        "target_binding"
                    ]
                )

                for side_entry in entry[
                    "sides"
                ]:
                    if not matches_value(
                        observed[
                            "sides"
                        ][
                            side_entry[
                                "side_name"
                            ]
                        ],
                        side_entry[
                            "desired"
                        ],
                    ):
                        raise RuntimeError(
                            "Authored Body Match verification failed."
                        )

            dm_obj.FinishUndo()
            scope_open = False

        except Exception as exc:
            restored = False

            if scope_open:
                try:
                    dm_obj.AbortUndoableOperation()
                    restored = p03_target_matches_baseline(
                        target_plan
                    )
                except Exception:
                    restored = False

            outcomes.append(
                {
                    "target": identity[
                        "name"
                    ],
                    "status": (
                        P03_MATCH_FAILED_RESTORED
                        if restored
                        else P03_MATCH_FAILED_UNRECOVERED
                    ),
                    "error": repr(
                        exc
                    ),
                }
            )

            for remaining in plans[
                index + 1:
            ]:
                outcomes.append(
                    {
                        "target": remaining[
                            "identity"
                        ][
                            "name"
                        ],
                        "status": P03_MATCH_UNATTEMPTED,
                    }
                )

            break

        same_time_refresh(
            float(
                sfmApp.GetHeadTimeInSeconds()
            ),
            "P03_BODY_MATCH_%d"
            % index,
        )

        verified = False

        try:
            verified = p03_target_matches_plan(
                target_plan
            )
        except Exception:
            verified = False

        outcomes.append(
            {
                "target": identity[
                    "name"
                ],
                "status": (
                    P03_MATCH_COMMITTED
                    if verified
                    else P03_MATCH_COMMITTED_UNVERIFIED
                ),
                "changed_sides": target_plan[
                    "changed_sides"
                ],
            }
        )

        if not verified:
            for remaining in plans[
                index + 1:
            ]:
                outcomes.append(
                    {
                        "target": remaining[
                            "identity"
                        ][
                            "name"
                        ],
                        "status": P03_MATCH_UNATTEMPTED,
                    }
                )
            break

    # Fresh source resolution and exact supported-state verification.
    source_after = p02_complete_scope()
    body_after = p03_body_scope(
        source_after
    )

    if not p03_verify_baselines(
        body_after[
            "accepted"
        ],
        source_snapshots,
    ):
        raise RuntimeError(
            "Body Match changed the Source body state."
        )

    # The per-target checks above prove each garment immediately after its
    # own transaction. One final evaluation boundary and fresh re-resolution
    # now proves that earlier garments still match after later garment writes.
    same_time_refresh(
        float(
            sfmApp.GetHeadTimeInSeconds()
        ),
        "P03_BODY_MATCH_FINAL_BATCH",
    )

    outcome_by_target = {}

    for row in outcomes:
        outcome_by_target[
            row[
                "target"
            ]
        ] = row

    final_rows = []
    all_final_verified = True

    for plan in plans:
        target_name = plan[
            "identity"
        ][
            "name"
        ]
        outcome = outcome_by_target.get(
            target_name
        )

        if outcome is None:
            continue

        if outcome[
            "status"
        ] not in (
            P03_MATCH_COMMITTED,
            P03_MATCH_UNCHANGED,
        ):
            continue

        try:
            verified = p03_target_matches_plan(
                plan
            )
        except Exception:
            verified = False

        outcome[
            "final_verified"
        ] = bool(
            verified
        )

        final_rows.append(
            {
                "target": target_name,
                "status_before_final_check": outcome[
                    "status"
                ],
                "final_verified": bool(
                    verified
                ),
                "unmapped_relevant": plan[
                    "unmapped_relevant"
                ],
            }
        )

        if not verified:
            all_final_verified = False

            if outcome[
                "status"
            ] == P03_MATCH_COMMITTED:
                outcome[
                    "status"
                ] = P03_MATCH_COMMITTED_UNVERIFIED
            else:
                outcome[
                    "status"
                ] = P03_MATCH_FINAL_MISMATCH

            outcome[
                "verification"
            ] = "final-batch"

    log_line(
        "P03_BODY_MATCH_FINAL_VERIFY all_final_verified=%r rows=%r"
        % (
            all_final_verified,
            final_rows,
        )
    )

    log_line(
        "P03_BODY_MATCH_OUTCOMES=%r source_unchanged=True"
        % outcomes
    )

    return outcomes



# -------------------------------------------------------------------------------------------------
# SFM Character Slider Preset Tool
# Production candidate 0.1
#
# Current qualified integrated profile:
#   Nika Shark
#
# Current semantic provider:
#   installed SFM Animation Groups Master TXT bridge
#
# Planned provider replacement:
#   qualified packed Master sidecar, through the same semantic contract.
#
# This production candidate intentionally contains no acceptance-test controls,
# injected failures, visual PASS checkboxes, or test-only countdowns.
# -------------------------------------------------------------------------------------------------

TOOL_VERSION = u"0.1.9-g02-generic-snapshot"
TOOL_NAME = u"SFM Character Preset Manager"


def tool_dialog_path(result):
    # PySide variants may return a string or a (string, filter) tuple.
    if isinstance(result, tuple):
        if not result:
            return u""
        return u(result[0])
    return u(result)


def tool_prompt_name(parent, title, label, initial=u""):
    result = QtGui.QInputDialog.getText(
        parent,
        title,
        label,
        QtGui.QLineEdit.Normal,
        initial,
    )

    if isinstance(result, tuple):
        value, ok = result
    else:
        value = result
        ok = bool(value)

    if not ok:
        return None

    value = u(value).strip()

    if not value:
        raise RuntimeError(
            "Preset name cannot be empty."
        )

    return value



def tool_build_initial_profile(
    scope_state,
):
    controls = {}
    semantic_rows = {}

    for row in scope_state[
        "scope"
    ][
        "rows"
    ]:
        literal = row[
            "literal"
        ]
        logical_id = (
            u"flex."
            + literal
        )

        semantic_rows[
            logical_id
        ] = p02_scope_row_signature(
            row
        )

        controls[
            logical_id
        ] = {
            "literal": literal,
            "representation": (
                row[
                    "live_shapes"
                ][0]
                if len(
                    row[
                        "live_shapes"
                    ]
                ) == 1
                else None
            ),
            "semantic_eligibility": row[
                "eligibility"
            ],
            "expression_capture": (
                row[
                    "eligibility"
                ]
                == u"expression-eligible"
            ),
            "expression_apply": (
                row[
                    "eligibility"
                ]
                == u"expression-eligible"
            ),
            "body_capture": False,
            "body_apply": False,
        }

    descriptor = scope_state[
        "provider_descriptor"
    ]

    profile = {
        "schema_version": P02_SCHEMA_VERSION,
        "profile_id": P02_PROFILE_ID,
        "revision": P02_PROFILE_REVISION,
        "display_name": "Nika Shark",
        "models": [
            {
                "path": P01_MODEL_PATH,
                "checksum": P01_MODEL_CHECKSUM,
                "status": "accepted",
            },
        ],
        "controls": controls,
        "expression_semantics": {
            "policy_id": P02_EXPRESSION_POLICY_ID,
            "scope_revision": P02_EXPRESSION_SCOPE_REVISION,
            "provider_contract": descriptor[
                "provider_contract"
            ],
            "adopted_source_sha256": descriptor[
                "source_sha256"
            ],
            "fold_policy": descriptor[
                "fold_policy"
            ],
            "provider_kind_at_adoption": descriptor[
                "provider_kind"
            ],
            "coverage": {
                "supported_live_flex_bindings": scope_state[
                    "scope"
                ][
                    "counts"
                ][
                    "supported_bindings"
                ],
                "unique_live_flex_literals": scope_state[
                    "scope"
                ][
                    "counts"
                ][
                    "unique_literals"
                ],
                "classification_row_count": len(
                    scope_state[
                        "scope"
                    ][
                        "rows"
                    ]
                ),
                "scope_signature_sha256": scope_state[
                    "scope_signature"
                ],
            },
            "classification_rows": semantic_rows,
            "accepted_expression_ids": [
                u"flex." + literal
                for literal in sorted(
                    scope_state[
                        "accepted"
                    ].keys()
                )
            ],
            "local_overrides": [],
            "pending_semantic_review": False,
        },
        "default_body_preset_id": None,
    }

    body_scope = p03_body_scope(
        scope_state
    )

    return p03_profile_with_body_scope(
        profile,
        scope_state,
        body_scope,
    )


def tool_body_scope_matches_adopted(
    profile,
    body_scope,
):
    semantics = profile.get(
        "body_semantics"
    )

    if not isinstance(
        semantics,
        dict,
    ):
        return False

    coverage = semantics.get(
        "coverage"
    )

    if not isinstance(
        coverage,
        dict,
    ):
        return False

    expected = coverage.get(
        "scope_signature_sha256"
    )

    if not expected:
        return False

    return (
        u(expected)
        == u(
            body_scope[
                "signature"
            ]
        )
    )


def tool_ensure_profile(
    scope_state=None,
):
    if scope_state is None:
        scope_state = p02_complete_scope()

    path = p03_library_paths()[
        "profile"
    ]

    if not os.path.isfile(
        path
    ):
        profile = tool_build_initial_profile(
            scope_state
        )

        p02_safe_write_json(
            path,
            profile,
        )

        loaded = p03_profile()

        if loaded != profile:
            raise RuntimeError(
                "New character profile did not read back exactly."
            )

        log_line(
            "TOOL_PROFILE_BOOTSTRAP=PASS profile=%r "
            "expression_controls=%d body_controls=%d"
            % (
                path,
                len(
                    profile[
                        "expression_semantics"
                    ][
                        "accepted_expression_ids"
                    ]
                ),
                len(
                    profile[
                        "body_semantics"
                    ][
                        "accepted_body_ids"
                    ]
                ),
            )
        )

        return loaded

    profile = p03_profile()

    # Existing adopted semantic scope is stable authority. Do not silently
    # refresh it when the current Master changes in a relevant way.
    p02_compare_live_to_adopted(
        scope_state,
        profile,
    )

    body_scope = p03_body_scope(
        scope_state
    )

    if not isinstance(
        profile.get(
            "body_semantics"
        ),
        dict,
    ):
        profile = p03_profile_with_body_scope(
            profile,
            scope_state,
            body_scope,
        )

        p02_safe_write_json(
            path,
            profile,
        )

        profile = p03_profile()

        log_line(
            "TOOL_PROFILE_BODY_SCOPE_ADDED=PASS body_controls=%d"
            % len(
                body_scope[
                    "accepted"
                ]
            )
        )

    elif not tool_body_scope_matches_adopted(
        profile,
        body_scope,
    ):
        raise RuntimeError(
            "The current Master-derived Body scope differs from this character's "
            "adopted scope. Review the semantic update before capturing or applying "
            "a new Body Preset."
        )

    return profile


def tool_save_expression_named(display_name):
    scope_state = p02_complete_scope()
    profile = tool_ensure_profile(
        scope_state
    )

    head_time = float(
        sfmApp.GetHeadTimeInSeconds()
    )
    same_time_refresh(
        head_time,
        "TOOL_EXPRESSION_CAPTURE",
    )

    # Resolve again after the evaluation boundary.
    scope_state = p02_complete_scope()

    p02_compare_live_to_adopted(
        scope_state,
        profile,
    )

    values, snapshots = p03_capture_values(
        scope_state[
            "accepted"
        ]
    )

    semantics = profile[
        "expression_semantics"
    ]
    accepted_ids = set(
        semantics[
            "accepted_expression_ids"
        ]
    )

    if set(
        values.keys()
    ) != accepted_ids:
        raise RuntimeError(
            "Current complete Expression scope does not match the adopted profile."
        )

    preset_id = (
        u"expression-"
        + unicode(
            uuid.uuid4().hex
        )
    )

    record = {
        "schema_version": P02_SCHEMA_VERSION,
        "preset_id": preset_id,
        "profile_id": P02_PROFILE_ID,
        "kind": P03_KIND_EXPRESSION,
        "name": u(display_name),
        "capture_profile_revision": profile.get(
            "revision",
            P02_PROFILE_REVISION,
        ),
        "capture_expression_scope_revision": semantics[
            "scope_revision"
        ],
        "capture_master_source_sha256": semantics[
            "adopted_source_sha256"
        ],
        "model_ref": {
            "path": P01_MODEL_PATH,
            "checksum": P01_MODEL_CHECKSUM,
        },
        "values": values,
    }

    path = p03_unique_preset_path(
        P03_KIND_EXPRESSION,
        u(display_name),
        preset_id,
    )

    p02_safe_write_json(
        path,
        record,
    )

    loaded = p02_read_json(
        path
    )
    p03_validate_preset(
        loaded,
        P03_KIND_EXPRESSION,
    )

    if loaded != record:
        raise RuntimeError(
            "Saved Expression did not read back exactly."
        )

    log_line(
        "TOOL_SAVE_EXPRESSION=PASS name=%r controls=%d path=%r"
        % (
            display_name,
            len(
                values
            ),
            path,
        )
    )

    return path


def tool_save_body_named(display_name):
    scope_state = p02_complete_scope()
    profile = tool_ensure_profile(
        scope_state
    )
    body_scope = p03_body_scope(
        scope_state
    )

    if not tool_body_scope_matches_adopted(
        profile,
        body_scope,
    ):
        raise RuntimeError(
            "The current Body semantic scope differs from the adopted profile. "
            "Nothing was saved."
        )

    values, snapshots = p03_capture_values(
        body_scope[
            "accepted"
        ]
    )

    profile = p03_profile()
    merged_profile = p03_profile_with_body_scope(
        profile,
        scope_state,
        body_scope,
    )

    preset_id = (
        u"body-"
        + unicode(
            uuid.uuid4().hex
        )
    )

    record = {
        "schema_version": P02_SCHEMA_VERSION,
        "preset_id": preset_id,
        "profile_id": P02_PROFILE_ID,
        "kind": P03_KIND_BODY,
        "name": u(display_name),
        "capture_profile_revision": merged_profile.get(
            "revision",
            P02_PROFILE_REVISION,
        ),
        "capture_body_scope_revision": P03_BODY_SCOPE_REVISION,
        "capture_master_source_sha256": scope_state[
            "provider_descriptor"
        ][
            "source_sha256"
        ],
        "model_ref": {
            "path": P01_MODEL_PATH,
            "checksum": P01_MODEL_CHECKSUM,
        },
        "values": values,
    }

    paths = p03_library_paths()

    path = p03_unique_preset_path(
        P03_KIND_BODY,
        u(display_name),
        preset_id,
    )

    p02_safe_write_json(
        path,
        record,
    )

    loaded_profile = p02_read_json(
        paths[
            "profile"
        ]
    )
    loaded = p02_read_json(
        path
    )

    p03_validate_preset(
        loaded,
        P03_KIND_BODY,
    )

    if (
        loaded_profile.get(
            "expression_semantics"
        )
        != profile.get(
            "expression_semantics"
        )
    ):
        raise RuntimeError(
            "Saving Body state changed the adopted Expression semantics."
        )

    if loaded != record:
        raise RuntimeError(
            "Saved Body Preset did not read back exactly."
        )

    log_line(
        "TOOL_SAVE_BODY=PASS name=%r controls=%d path=%r"
        % (
            display_name,
            len(
                values
            ),
            path,
        )
    )

    return path


def tool_find_list_item_by_path(widget, wanted_path):
    wanted = u(wanted_path)

    for index in range(
        widget.count()
    ):
        item = widget.item(
            index
        )
        path = u(
            item.data(
                QtCore.Qt.UserRole
            )
        )

        if path == wanted:
            return index

    return -1


def tool_item_path(widget):
    item = widget.currentItem()

    if item is None:
        raise RuntimeError(
            "Select a preset first."
        )

    return u(
        item.data(
            QtCore.Qt.UserRole
        )
    )


def tool_export_selected(parent, source_path):
    record = p02_read_json(
        source_path
    )
    p03_validate_preset(
        record
    )

    suggested = (
        u(record.get("name"))
        + u".json"
    )

    result = QtGui.QFileDialog.getSaveFileName(
        parent,
        "Export Preset",
        suggested,
        "JSON files (*.json);;All files (*)",
    )
    target = tool_dialog_path(
        result
    )

    if not target:
        return None

    if not target.lower().endswith(
        u".json"
    ):
        target += u".json"

    p03_export_preset(
        source_path,
        target,
    )

    log_line(
        "TOOL_EXPORT_PRESET=PASS source=%r target=%r"
        % (
            source_path,
            target,
        )
    )

    return target


def tool_import_preset(parent):
    result = QtGui.QFileDialog.getOpenFileName(
        parent,
        "Import Preset",
        u"",
        "JSON files (*.json);;All files (*)",
    )
    source = tool_dialog_path(
        result
    )

    if not source:
        return None

    target, record = p03_import_as_copy(
        source
    )

    log_line(
        "TOOL_IMPORT_PRESET=PASS source=%r target=%r kind=%r"
        % (
            source,
            target,
            record[
                "kind"
            ],
        )
    )

    return target, record


class MatchClothingDialog(QtGui.QDialog):

    def __init__(
        self,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )

        self.setWindowTitle(
            "Match Clothing"
        )
        self.setModal(
            True
        )
        self.resize(
            620,
            460,
        )

        layout = QtGui.QVBoxLayout(
            self
        )

        note = QtGui.QLabel(
            "Match the current character body to selected compatible clothing. "
            "Each changed garment creates its own native SFM Undo item."
        )
        note.setWordWrap(
            True
        )
        layout.addWidget(
            note
        )

        self.list = QtGui.QListWidget()
        layout.addWidget(
            self.list,
            1,
        )

        self.result = QtGui.QLabel(
            ""
        )
        self.result.setWordWrap(
            True
        )
        layout.addWidget(
            self.result
        )

        buttons = QtGui.QDialogButtonBox()
        self.match_button = buttons.addButton(
            "Match Selected",
            QtGui.QDialogButtonBox.AcceptRole,
        )
        close_button = buttons.addButton(
            QtGui.QDialogButtonBox.Close,
        )

        self.match_button.clicked.connect(
            self.run_match
        )
        close_button.clicked.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        self.populate()

    def populate(self):
        self.list.clear()

        candidates = p03_clothing_candidates()

        for row in candidates:
            item = QtGui.QListWidgetItem(
                u"%s  (%d mapped body controls)"
                % (
                    u(
                        row[
                            "name"
                        ]
                    ),
                    row[
                        "mapping_count"
                    ],
                )
            )
            item.setFlags(
                item.flags()
                | QtCore.Qt.ItemIsUserCheckable
            )
            item.setCheckState(
                QtCore.Qt.Checked
            )
            item.setData(
                QtCore.Qt.UserRole,
                row,
            )
            self.list.addItem(
                item
            )

        if not candidates:
            self.result.setText(
                "No compatible clothing targets were found in the current shot."
            )
            self.match_button.setEnabled(
                False
            )

    def run_match(self):
        selected = []

        for index in range(
            self.list.count()
        ):
            item = self.list.item(
                index
            )

            if item.checkState() != QtCore.Qt.Checked:
                continue

            selected.append(
                item.data(
                    QtCore.Qt.UserRole
                )
            )

        try:
            outcomes = p03_apply_body_match(
                selected
            )
        except Exception as exc:
            QtGui.QMessageBox.warning(
                self,
                "Match Clothing could not finish",
                u(exc),
            )
            return

        lines = []

        for row in outcomes:
            lines.append(
                u"%s: %s"
                % (
                    row[
                        "target"
                    ],
                    row[
                        "status"
                    ],
                )
            )

        all_verified = True

        for row in outcomes:
            if row[
                "status"
            ] in (
                P03_MATCH_COMMITTED_UNVERIFIED,
                P03_MATCH_FINAL_MISMATCH,
                P03_MATCH_FAILED_UNRECOVERED,
            ):
                all_verified = False

        lines.append(
            u""
        )

        if all_verified:
            lines.append(
                u"Matched control values were verified again after the full clothing batch."
            )
        else:
            lines.append(
                u"One or more clothing items could not be verified after the full batch."
            )

        self.result.setText(
            u"\n".join(
                lines
            )
        )

        log_line(
            "TOOL_MATCH_CLOTHING_COMPLETE outcomes=%r"
            % outcomes
        )




# Qualified R27 compatibility helpers required by the Krystal production adapter.

def authored_side_matches(state, desired):
    """
    Pre-refresh verification only.

    R15C4 incorrectly required destination/evaluated parity before the
    transaction had been finished and the qualified same-time refresh had run.
    Here we verify only the authored static state: source + one local-zero key.
    Full destination/evaluated verification remains mandatory after refresh.
    """
    return (
        close_enough(state["source"], desired)
        and state["key_count"] == 1
        and state["is_empty"] is False
        and close_enough(state["key0_time"], 0.0)
        and close_enough(state["key0_value"], desired)
    )

def model_backed_animsets(shot):
    records = []
    for animset in list(shot.animationSets):
        gm = get_game_model(animset)
        if gm is None:
            continue
        asset = model_asset(gm)
        check = checksum(gm)
        if asset is None or check is None:
            continue
        records.append({
            "animset": animset,
            "gm": gm,
            "animset_name": name(animset),
            "model": asset,
            "checksum": check,
            "animset_id": dme_id(animset),
        })
    records.sort(key=lambda row: (row["animset_name"] or u"", row["model"] or u""))
    return records

def all_flex_bindings(animset):
    result = []
    try:
        controls = list(animset.controls)
    except Exception:
        controls = arr(animset, "controls")
    if len(controls) > MAX_CONTROLS:
        raise RuntimeError("Animation-set control count exceeded safety cap.")
    for control in controls:
        binding = flex_binding(control)
        if binding is not None:
            result.append(binding)
    result.sort(key=lambda row: (row["literal"] or u"", row["shape"]))
    return result

def binding_key_without_runtime_id(binding):
    return (binding["literal"], binding["shape"])

KRYSTAL_MODEL = u"models/fursonas/starfox/krystal/bodies/krystal2020.mdl"
KRYSTAL_CHECKSUM = -1441261258
BODY_GROUP_NAME = u"Body Morphs"
SCALE_LITERAL = u"bip_head_scale"

MIN_FLEX_CHANGES = 1


def unique_krystal(shot):
    matches = [
        row for row in model_backed_animsets(shot)
        if (
            row["model"] == KRYSTAL_MODEL
            and row["checksum"] == KRYSTAL_CHECKSUM
        )
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "This test needs exactly one Krystal body model in the current shot; found %d."
            % len(matches)
        )
    return matches[0]


def unique_body_group(animset):
    matches = [
        row for row in group_inventory(animset)
        if (
            row["parts"]
            and row["parts"][-1] == BODY_GROUP_NAME
        )
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Krystal's Body Morphs group did not resolve uniquely; found %d."
            % len(matches)
        )
    return matches[0]


def unique_control_by_name(animset, shot, literal):
    """
    Resolve an exact named control from every live surface that SFM may update
    when Add Scale creates a control during the current session.

    R15C originally searched only animset.controls. The failed target run showed
    that this surface can remain incomplete after a live Add Scale operation.
    We therefore collect exact candidates from:
      - animset.controls
      - the current root-control-group tree
      - channel-clip fromElement references

    The result is still accepted only when ONE exact DME object remains, and the
    full qualified scale graph is validated immediately afterward.
    """

    surfaces = []
    candidates = {}

    def add_candidate(control, surface):
        if control is None:
            return
        if name(control) != literal:
            return

        key = (handle(control), ptr(control))

        if key not in candidates:
            candidates[key] = {
                "control": control,
                "surfaces": [],
            }

        if surface not in candidates[key]["surfaces"]:
            candidates[key]["surfaces"].append(surface)

    # 1. Animation-set controls array.
    try:
        direct_controls = list(animset.controls)
    except Exception:
        direct_controls = arr(animset, "controls")

    direct_hits = 0

    for control in direct_controls:
        if name(control) == literal:
            direct_hits += 1
            add_candidate(control, "animset.controls")

    surfaces.append(("animset.controls", direct_hits))

    # 2. Current root-control-group tree.
    group_hits = 0

    try:
        root = root_group(animset)

        for control in subtree_controls(root):
            if name(control) == literal:
                group_hits += 1
                add_candidate(control, "rootControlGroup")
    except Exception as exc:
        log_line(
            "SCALE_CONTROL_GROUP_TREE_ENUMERATION_ERROR=%r"
            % exc
        )

    surfaces.append(("rootControlGroup", group_hits))

    # 3. Current animation-set channel clip.  Newly-created Add Scale controls
    # may already own channels even when another collection is stale.
    channel_hits = 0

    try:
        clip = get_channels_clip(animset, shot)

        try:
            channels = list(clip.channels)
        except Exception:
            channels = arr(clip, "channels")

        for channel in channels:
            if typ(channel) != u"DmeChannel":
                continue

            control = attr_value(channel, "fromElement")

            if name(control) == literal:
                channel_hits += 1
                add_candidate(control, "channelClip.fromElement")

    except Exception as exc:
        log_line(
            "SCALE_CONTROL_CHANNEL_CLIP_ENUMERATION_ERROR=%r"
            % exc
        )

    surfaces.append(("channelClip.fromElement", channel_hits))

    rows = list(candidates.values())

    log_line(
        "SCALE_CONTROL_DISCOVERY literal=%r surfaces=%r unique_candidates=%d candidate_details=%r"
        % (
            literal,
            surfaces,
            len(rows),
            [
                (
                    dme_id(row["control"]),
                    row["surfaces"],
                )
                for row in rows
            ],
        )
    )

    if len(rows) != 1:
        raise RuntimeError(
            "Krystal's head-size control could not be identified safely. "
            "Nothing was changed."
        )

    return rows[0]["control"]


def get_log(channel):
    try:
        return channel.GetLog()
    except Exception:
        return attr_value(channel, "log")


def layer_count(log):
    try:
        return int(log.GetNumLayers())
    except Exception:
        pass
    try:
        return len(list(log.layers))
    except Exception:
        return None


def get_layer(log, index):
    try:
        return log.GetLayer(index)
    except Exception:
        pass
    try:
        return list(log.layers)[index]
    except Exception:
        return None


def get_channels_clip(animset, shot):
    group = shot.FindTrackGroup("channelTrackGroup")
    if group is None:
        raise RuntimeError("Krystal's channel track group is unavailable.")

    track = group.FindTrack("animSetEditorChannels")
    if track is None:
        raise RuntimeError("Krystal's animation-set channels track is unavailable.")

    clip = track.FindNamedClip(animset.GetName())
    if clip is None:
        raise RuntimeError("Krystal's animation-set channels clip is unavailable.")

    return clip


def resolve_qualified_head_scale(animset, shot, gm):
    """
    Resolve the already-qualified existing scale topology structurally.

    We intentionally do NOT require a particular expression/output-channel name.
    Authority comes from the previously qualified graph shape:
      bip_head_scale.value
        -> DmeChannel
        -> DmeExpressionOperator.value, lerp(value,lo,hi)
        -> unique pass-mode channel from expression.result
        -> DmeTransform.scale
    with a ONE_KEY_ZERO input and empty pass-through output log.
    """

    control = unique_control_by_name(animset, shot, SCALE_LITERAL)
    source_attr = get_attr(control, "value")
    if source_attr is None:
        raise RuntimeError("bip_head_scale has no value attribute.")

    channel = attr_value(control, "channel")
    if channel is None or typ(channel) != u"DmeChannel":
        raise RuntimeError("bip_head_scale input channel is not DmeChannel.")

    if not same_dme(attr_value(channel, "fromElement"), control):
        raise RuntimeError("bip_head_scale input source does not point back to the control.")

    if u(attr_value(channel, "fromAttribute")) != u"value":
        raise RuntimeError("bip_head_scale input does not source the value attribute.")

    expression = attr_value(channel, "toElement")
    if expression is None or typ(expression) != u"DmeExpressionOperator":
        raise RuntimeError("bip_head_scale does not feed a DmeExpressionOperator.")

    if u(attr_value(channel, "toAttribute")) != u"value":
        raise RuntimeError("bip_head_scale input does not feed expression.value.")

    expr = u(attr_value(expression, "expr"))
    normalized_expr = None if expr is None else expr.replace(" ", "").lower()
    if normalized_expr != u"lerp(value,lo,hi)":
        raise RuntimeError(
            "bip_head_scale expression is outside the qualified lerp(value,lo,hi) contract."
        )

    lo = as_float(attr_value(expression, "lo"))
    hi = as_float(attr_value(expression, "hi"))
    if lo is None or hi is None or close_enough(lo, hi):
        raise RuntimeError("bip_head_scale expression range is unreadable or degenerate.")

    input_log = get_log(channel)
    if input_log is None or typ(input_log) != u"DmeFloatLog":
        raise RuntimeError("bip_head_scale input log is not DmeFloatLog.")

    if layer_count(input_log) != 1:
        raise RuntimeError("bip_head_scale requires exactly one input log layer.")

    input_layer = get_layer(input_log, 0)
    if input_layer is None or typ(input_layer) != u"DmeFloatLogLayer":
        raise RuntimeError("bip_head_scale input layer is not DmeFloatLogLayer.")

    input_count = key_count(input_layer)

    try:
        input_empty = bool(input_log.IsEmpty())
    except Exception:
        input_empty = None

    key_time = None
    key_value = None

    if input_count == 0:
        if input_empty is not True:
            raise RuntimeError(
                "Krystal's head-size control is in an unsupported animation state. "
                "Nothing was changed."
            )
        input_origin = "EMPTY"

    elif input_count == 1:
        try:
            key_time = seconds(input_layer.GetKeyTime(0))
            key_value = float(input_layer.GetKeyValue(0))
        except Exception:
            raise RuntimeError(
                "Krystal's head-size control key could not be read safely. "
                "Nothing was changed."
            )

        if not close_enough(key_time, 0.0):
            raise RuntimeError(
                "Krystal's head-size control is animated in a way this test does not support. "
                "Nothing was changed."
            )

        input_origin = "ONE_KEY_ZERO"

    else:
        raise RuntimeError(
            "Krystal's head-size control is animated in a way this test does not support. "
            "Nothing was changed."
        )

    log_line(
        "SCALE_INPUT_STATE origin=%r key_count=%r is_empty=%r key_time=%r key_value=%r"
        % (
            input_origin,
            input_count,
            input_empty,
            key_time,
            key_value,
        )
    )

    clip = get_channels_clip(animset, shot)
    try:
        clip_channels = list(clip.channels)
    except Exception:
        clip_channels = arr(clip, "channels")

    output_matches = []

    for candidate in clip_channels:
        if typ(candidate) != u"DmeChannel":
            continue
        if not same_dme(attr_value(candidate, "fromElement"), expression):
            continue
        if u(attr_value(candidate, "fromAttribute")) != u"result":
            continue

        destination = attr_value(candidate, "toElement")
        if destination is None or typ(destination) != u"DmeTransform":
            continue
        if u(attr_value(candidate, "toAttribute")) != u"scale":
            continue

        output_matches.append((candidate, destination))

    if len(output_matches) != 1:
        raise RuntimeError(
            "Expected one qualified bip_head_scale output-to-transform route; found %d."
            % len(output_matches)
        )

    output, body_transform = output_matches[0]

    if get_attr(body_transform, "scale") is None:
        raise RuntimeError("Qualified head-scale destination lacks transform.scale.")

    try:
        mode = int(output.GetMode())
    except Exception:
        mode = None

    if mode != 1:
        raise RuntimeError("Qualified head-scale output is not pass mode 1.")

    output_log = get_log(output)
    if output_log is None or typ(output_log) != u"DmeFloatLog":
        raise RuntimeError("Qualified head-scale output log is not DmeFloatLog.")

    if layer_count(output_log) != 1:
        raise RuntimeError("Qualified head-scale output requires exactly one log layer.")

    output_layer = get_layer(output_log, 0)
    if output_layer is None or typ(output_layer) != u"DmeFloatLogLayer":
        raise RuntimeError("Qualified head-scale output layer is not DmeFloatLogLayer.")

    if key_count(output_layer) != 0:
        raise RuntimeError("Qualified head-scale pass-through output log must have zero keys.")

    return {
        "shot": shot,
        "animset": animset,
        "gm": gm,
        "control": control,
        "source_attr": source_attr,
        "channel": channel,
        "input_log": input_log,
        "input_layer": input_layer,
        "expression": expression,
        "output": output,
        "output_log": output_log,
        "output_layer": output_layer,
        "body_transform": body_transform,
        "lo": lo,
        "hi": hi,
        "capture_key_value": key_value,
    }


def scale_expected(binding, control_value):
    return binding["lo"] + float(control_value) * (
        binding["hi"] - binding["lo"]
    )


def scale_snapshot(binding):
    count = key_count(binding["input_layer"])

    try:
        empty = bool(binding["input_log"].IsEmpty())
    except Exception:
        empty = None

    key_time = None
    key_value = None

    if count == 1:
        try:
            key_time = seconds(binding["input_layer"].GetKeyTime(0))
            key_value = float(binding["input_layer"].GetKeyValue(0))
        except Exception:
            key_time = None
            key_value = None

    return {
        "source": as_float(attr_value(binding["control"], "value")),
        "expr_input": as_float(attr_value(binding["expression"], "value")),
        "expr_result": as_float(attr_value(binding["expression"], "result")),
        "key_count": count,
        "is_empty": empty,
        "key_time": key_time,
        "key_value": key_value,
        "bone_scale": as_float(attr_value(binding["body_transform"], "scale")),
        "control_id": dme_id(binding["control"]),
        "channel_id": dme_id(binding["channel"]),
        "input_log_id": dme_id(binding["input_log"]),
        "input_layer_id": dme_id(binding["input_layer"]),
        "expression_id": dme_id(binding["expression"]),
        "output_id": dme_id(binding["output"]),
        "body_transform_id": dme_id(binding["body_transform"]),
    }


def scale_state_kind(state):
    if (
        state["key_count"] == 0
        and state["is_empty"] is True
    ):
        return "EMPTY"

    if (
        state["key_count"] == 1
        and state["is_empty"] is False
        and close_enough(state["key_time"], 0.0)
        and close_enough(state["key_value"], state["source"])
    ):
        return "ONE_KEY_ZERO"

    return "UNSUPPORTED"


def scale_authored_matches(state, value):
    origin = scale_state_kind(state)

    if origin == "EMPTY":
        return (
            close_enough(state["source"], value)
            and close_enough(state["expr_input"], value)
        )

    if origin == "ONE_KEY_ZERO":
        return (
            close_enough(state["source"], value)
            and close_enough(state["expr_input"], value)
            and close_enough(state["key_time"], 0.0)
            and close_enough(state["key_value"], value)
        )

    return False


def scale_evaluated_matches(binding, state, value):
    expected = scale_expected(binding, value)
    return (
        scale_authored_matches(state, value)
        and close_enough(state["expr_result"], expected)
        and close_enough(state["bone_scale"], expected)
    )


def scale_baseline_matches(binding, state, baseline):
    origin = scale_state_kind(baseline)

    if origin == "EMPTY":
        return (
            scale_state_kind(state) == "EMPTY"
            and state["control_id"] == baseline["control_id"]
            and state["channel_id"] == baseline["channel_id"]
            and state["input_log_id"] == baseline["input_log_id"]
            and state["input_layer_id"] == baseline["input_layer_id"]
            and state["expression_id"] == baseline["expression_id"]
            and state["output_id"] == baseline["output_id"]
            and state["body_transform_id"] == baseline["body_transform_id"]
            and scale_evaluated_matches(
                binding,
                state,
                baseline["source"],
            )
        )

    if origin == "ONE_KEY_ZERO":
        return (
            scale_state_kind(state) == "ONE_KEY_ZERO"
            and state["control_id"] == baseline["control_id"]
            and state["channel_id"] == baseline["channel_id"]
            and state["input_log_id"] == baseline["input_log_id"]
            and state["input_layer_id"] == baseline["input_layer_id"]
            and state["expression_id"] == baseline["expression_id"]
            and state["output_id"] == baseline["output_id"]
            and state["body_transform_id"] == baseline["body_transform_id"]
            and scale_evaluated_matches(
                binding,
                state,
                baseline["source"],
            )
            and close_enough(state["key_time"], baseline["key_time"])
            and close_enough(state["key_value"], baseline["key_value"])
        )

    return False


def write_head_scale(binding, desired, origin=None):
    if origin is None:
        origin = scale_state_kind(scale_snapshot(binding))

    if origin == "EMPTY":
        binding["source_attr"].SetValue(float(desired))
        binding["input_layer"].ClearAndAddSampleAtTime(
            make_zero_time(),
            binding["channel"],
        )
        binding["channel"].Operate()
        return

    if origin == "ONE_KEY_ZERO":
        binding["input_layer"].SetKeyValue(0, float(desired))
        binding["source_attr"].SetValue(float(desired))
        binding["channel"].Operate()
        return

    raise RuntimeError(
        "Krystal's head-size control is in an unsupported animation state. "
        "Nothing was changed."
    )


def restore_head_scale(binding, baseline):
    origin = scale_state_kind(baseline)

    if origin == "EMPTY":
        binding["input_layer"].ClearKeys()
        binding["source_attr"].SetValue(float(baseline["source"]))
        binding["channel"].Operate()
        return

    if origin == "ONE_KEY_ZERO":
        binding["input_layer"].SetKeyValue(
            0,
            float(baseline["key_value"]),
        )
        binding["source_attr"].SetValue(float(baseline["source"]))
        binding["channel"].Operate()
        return

    raise RuntimeError(
        "The saved pre-Apply head-size state cannot be restored safely."
    )


def body_flex_bindings(animset):
    group = unique_body_group(animset)
    bindings = bindings_for_group(group["group"])

    if not bindings:
        raise RuntimeError("Krystal's Body Morphs group contains no supported flex controls.")

    return bindings


def plain_body_preset(krystal, flex_bindings, scale_binding):
    entries = []
    nonzero_flex_sides = 0

    for binding in flex_bindings:
        snap = binding_snapshot(binding)
        values = {}

        for side_name, state in snap["sides"].items():
            if not coherent(state):
                raise RuntimeError(
                    "Body slider %r/%s is outside the qualified static state."
                    % (binding["literal"], side_name)
                )

            values[side_name] = state["evaluated"]

            if not close_enough(state["evaluated"], 0.0):
                nonzero_flex_sides += 1

        entries.append({
            "literal": binding["literal"],
            "shape": binding["shape"],
            "values": values,
        })

        log_line(
            "CAPTURE_FLEX literal=%r shape=%r runtime_global_diagnostic=%r values=%r"
            % (
                binding["literal"],
                binding["shape"],
                binding["global_key"],
                values,
            )
        )

    scale_state = scale_snapshot(scale_binding)

    if not scale_evaluated_matches(
        scale_binding,
        scale_state,
        scale_state["source"],
    ):
        raise RuntimeError(
            "bip_head_scale is not fully coherent/evaluated at Capture."
        )

    scale_entry = {
        "kind": "qualified_existing_head_scale",
        "literal": SCALE_LITERAL,
        "value": scale_state["source"],
        "lo": scale_binding["lo"],
        "hi": scale_binding["hi"],
        "contract": "lerp_value_lo_hi_to_transform_scale_v1",
    }

    preset = {
        "schema_probe": 2,
        "preset_kind": "body",
        "model_path": krystal["model"],
        "model_checksum": krystal["checksum"],
        "flexes": entries,
        "scales": [scale_entry],
    }

    encoded = json.dumps(
        preset,
        sort_keys=True,
        separators=(",", ":"),
    )

    log_line(
        "CAPTURE_SCALE literal=%r value=%r lo=%r hi=%r downstream_scale=%r"
        % (
            SCALE_LITERAL,
            scale_state["source"],
            scale_binding["lo"],
            scale_binding["hi"],
            scale_state["bone_scale"],
        )
    )

    return preset, encoded, nonzero_flex_sides


def resolve_preset_on_target(target, shot, preset):
    flex_index = {}

    for binding in all_flex_bindings(target["animset"]):
        key = binding_key_without_runtime_id(binding)
        flex_index.setdefault(key, []).append(binding)

    resolved_flex = []

    for entry in preset["flexes"]:
        key = (entry["literal"], entry["shape"])
        candidates = flex_index.get(key, [])

        if len(candidates) != 1:
            raise RuntimeError(
                "Target body slider %r [%s] resolved %d times."
                % (
                    entry["literal"],
                    entry["shape"],
                    len(candidates),
                )
            )

        resolved_flex.append((entry, candidates[0]))

    scale_entry = preset["scales"][0]
    scale_binding = resolve_qualified_head_scale(
        target["animset"],
        shot,
        target["gm"],
    )

    if not close_enough(scale_binding["lo"], scale_entry["lo"]):
        raise RuntimeError("Target head-scale lower bound differs from captured capability.")

    if not close_enough(scale_binding["hi"], scale_entry["hi"]):
        raise RuntimeError("Target head-scale upper bound differs from captured capability.")

    return resolved_flex, scale_entry, scale_binding



# -------------------------------------------------------------------------------------------------
# R27 - exact R23/R25 scale builder + complete Body Preset apply
# -------------------------------------------------------------------------------------------------

R27_EXPR_NAME = u"bip_head_scale_rescale"
R27_OUTPUT_CHANNEL_NAME = u"scaled_bip_head_scale_channel"
R27_EXPR_TEXT = u"lerp(value, lo, hi)"
R27_NEUTRAL_VALUE = 0.1
R27_LO = 0.0
R27_HI = 10.0


def r26_animset_controls(animset):
    try:
        return list(animset.controls)
    except Exception:
        return arr(animset, "controls")


def r26_animset_operators(animset):
    try:
        return list(animset.operators)
    except Exception:
        return arr(animset, "operators")


def r26_clip_channels(clip):
    try:
        return list(clip.channels)
    except Exception:
        return arr(clip, "channels")


def r26_unique_head_control(animset):
    candidates = {}

    for control in r26_animset_controls(animset):
        if name(control) == u"bip_head":
            candidates[(handle(control), ptr(control))] = control

    found = None
    try:
        found = animset.FindControl(b(u"bip_head"))
    except Exception:
        try:
            found = animset.FindControl(u"bip_head")
        except Exception:
            found = None

    if found is not None and name(found) == u"bip_head":
        candidates[(handle(found), ptr(found))] = found

    rows = list(candidates.values())

    log_line(
        "R27_HEAD_DISCOVERY unique_candidates=%d details=%r"
        % (
            len(rows),
            [dme_id(row) for row in rows],
        )
    )

    if len(rows) != 1:
        raise RuntimeError(
            "Krystal's head transform could not be identified safely."
        )

    control = rows[0]

    if typ(control) != u"DmeTransformControl":
        raise RuntimeError(
            "Krystal's head control is not a transform control."
        )

    try:
        casted = vs.CastElementAsDmeTransformControl(control)
    except Exception:
        casted = control

    if casted is None or typ(casted) != u"DmeTransformControl":
        raise RuntimeError(
            "Krystal's head transform control could not be resolved."
        )

    return casted


def r26_unique_head_group(animset, head_control):
    matches = []

    for row in group_inventory(animset):
        if any(
            same_dme(member, head_control)
            for member in arr(row["group"], "controls")
        ):
            matches.append(row)

    if len(matches) != 1:
        raise RuntimeError(
            "Krystal's head control group could not be identified uniquely."
        )

    return matches[0]


def r26_scale_control_candidates(animset, shot):
    candidates = {}

    def add(control):
        if control is None or name(control) != SCALE_LITERAL:
            return
        candidates[(handle(control), ptr(control))] = control

    for control in r26_animset_controls(animset):
        add(control)

    for control in subtree_controls(root_group(animset)):
        add(control)

    clip = get_channels_clip(animset, shot)

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue
        add(attr_value(channel, "fromElement"))

    found = None
    try:
        found = animset.FindControl(b(SCALE_LITERAL))
    except Exception:
        try:
            found = animset.FindControl(SCALE_LITERAL)
        except Exception:
            found = None

    add(found)

    return list(candidates.values())


def r26_named_operator_count(animset, literal):
    return len([
        operator
        for operator in r26_animset_operators(animset)
        if name(operator) == literal
    ])


def r26_named_channel_count(clip, literal):
    return len([
        channel
        for channel in r26_clip_channels(clip)
        if name(channel) == literal
    ])


def r26_absence_fixture(target, shot):
    animset = target["animset"]
    head_control = r26_unique_head_control(animset)

    try:
        body_transform = head_control.GetTransform()
    except Exception as exc:
        raise RuntimeError(
            "Krystal's head transform could not be resolved: %r" % exc
        )

    if body_transform is None or typ(body_transform) != u"DmeTransform":
        raise RuntimeError(
            "Krystal's head does not resolve to a body transform."
        )

    head_group = r26_unique_head_group(
        animset,
        head_control,
    )

    clip = get_channels_clip(animset, shot)

    scale_candidates = r26_scale_control_candidates(
        animset,
        shot,
    )

    direct_group_scale = [
        control
        for control in arr(head_group["group"], "controls")
        if name(control) == SCALE_LITERAL
    ]

    state = {
        "shot_id": dme_id(shot),
        "animset_id": dme_id(animset),
        "body_transform_id": dme_id(body_transform),
        "head_group_id": dme_id(head_group["group"]),
        "head_group_path": head_group["path"],
        "body_has_scale": (
            get_attr(body_transform, "scale") is not None
        ),
        "scale_control_count": len(scale_candidates),
        "expression_count": r26_named_operator_count(
            animset,
            R27_EXPR_NAME,
        ),
        "input_channel_name_count": r26_named_channel_count(
            clip,
            SCALE_LITERAL,
        ),
        "output_channel_name_count": r26_named_channel_count(
            clip,
            R27_OUTPUT_CHANNEL_NAME,
        ),
        "head_group_scale_count": len(direct_group_scale),
        "animset_control_count": len(
            r26_animset_controls(animset)
        ),
        "animset_operator_count": len(
            r26_animset_operators(animset)
        ),
        "channel_count": len(
            r26_clip_channels(clip)
        ),
        "head_group_control_count": len(
            arr(head_group["group"], "controls")
        ),
    }

    log_line(
        "R27_SCALE_ABSENCE_STATE=%r"
        % state
    )

    clean = (
        state["body_has_scale"] is False
        and state["scale_control_count"] == 0
        and state["expression_count"] == 0
        and state["input_channel_name_count"] == 0
        and state["output_channel_name_count"] == 0
        and state["head_group_scale_count"] == 0
    )

    if not clean:
        raise RuntimeError(
            "This target already has a complete or partial head-size capability. "
            "Use a clean target shot for this test."
        )

    return {
        "target": target,
        "shot": shot,
        "animset": animset,
        "head_control": head_control,
        "body_transform": body_transform,
        "head_group": head_group,
        "clip": clip,
        "state": state,
    }


def r26_absence_counts_match(current, baseline):
    return (
        current["animset_control_count"]
        == baseline["animset_control_count"]
        and current["animset_operator_count"]
        == baseline["animset_operator_count"]
        and current["channel_count"]
        == baseline["channel_count"]
        and current["head_group_control_count"]
        == baseline["head_group_control_count"]
    )


def r26_add_float_attr(element, attr_name, value):
    if get_attr(element, attr_name) is not None:
        raise RuntimeError(
            "Unexpected pre-existing %s attribute."
            % attr_name
        )

    attr = element.AddAttributeAsFloat(
        b(attr_name)
    )

    if attr is None:
        raise RuntimeError(
            "Could not add %s."
            % attr_name
        )

    attr.SetValue(float(value))

    if not close_enough(
        attr_value(element, attr_name),
        value,
    ):
        raise RuntimeError(
            "%s did not retain its initialized value."
            % attr_name
        )

    return attr



def r26_exact_named_control_surfaces(animset, shot, literal):
    """R23-style exact live-control discovery across all qualified surfaces."""
    candidates = {}
    surfaces = []

    def add(control, surface):
        if control is None or name(control) != literal:
            return

        key = (handle(control), ptr(control))

        if key not in candidates:
            candidates[key] = {
                "control": control,
                "surfaces": [],
            }

        if surface not in candidates[key]["surfaces"]:
            candidates[key]["surfaces"].append(surface)

    direct_hits = 0
    for control in r26_animset_controls(animset):
        if name(control) == literal:
            direct_hits += 1
            add(control, "animset.controls")
    surfaces.append(("animset.controls", direct_hits))

    group_hits = 0
    for control in subtree_controls(root_group(animset)):
        if name(control) == literal:
            group_hits += 1
            add(control, "rootControlGroup")
    surfaces.append(("rootControlGroup", group_hits))

    channel_hits = 0
    clip = get_channels_clip(animset, shot)
    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue
        source = attr_value(channel, "fromElement")
        if name(source) == literal:
            channel_hits += 1
            add(source, "channelClip.fromElement")
    surfaces.append(("channelClip.fromElement", channel_hits))

    found = None
    try:
        found = animset.FindControl(b(literal))
    except Exception:
        try:
            found = animset.FindControl(literal)
        except Exception:
            found = None

    if found is not None and name(found) == literal:
        add(found, "animset.FindControl")

    return {
        "surfaces": surfaces,
        "candidates": list(candidates.values()),
        "find_control": found,
    }


def r26_named_operator_hits(animset, literal):
    return [
        operator
        for operator in r26_animset_operators(animset)
        if name(operator) == literal
    ]


def r26_add_float_attr_exact(element, attr_name, value):
    # Kept intentionally equivalent to R23's qualified helper.
    if get_attr(element, attr_name) is not None:
        raise RuntimeError(
            "Unexpected pre-existing %s attribute during capability construction."
            % attr_name
        )

    attr = element.AddAttributeAsFloat(b(attr_name))

    if attr is None:
        raise RuntimeError(
            "Could not add float attribute %s." % attr_name
        )

    attr.SetValue(float(value))

    observed = as_float(attr_value(element, attr_name))

    if not close_enough(observed, value):
        raise RuntimeError(
            "Float attribute %s did not retain its initialized value."
            % attr_name
        )

    return attr


def r26_create_input_control_channel_exact(animset, shot, clip):
    # This follows R23's qualified construction order exactly.
    control = animset.FindOrAddControl(
        b(SCALE_LITERAL),
        False,
        True,
    )

    if control is None or name(control) != SCALE_LITERAL:
        raise RuntimeError("SFM did not create bip_head_scale.")

    r26_add_float_attr_exact(
        control,
        "value",
        R27_NEUTRAL_VALUE,
    )
    r26_add_float_attr_exact(
        control,
        "defaultValue",
        R27_NEUTRAL_VALUE,
    )

    channel = vs.CreateElement(
        "DmeChannel",
        b(SCALE_LITERAL),
        shot.GetFileId(),
    )

    if channel is None or typ(channel) != u"DmeChannel":
        raise RuntimeError("Could not create the head-scale input DmeChannel.")

    input_log = vs.CreateElement(
        "DmeFloatLog",
        "float log",
        shot.GetFileId(),
    )

    if input_log is None or typ(input_log) != u"DmeFloatLog":
        raise RuntimeError("Could not create the head-scale DmeFloatLog.")

    channel.SetLog(input_log)

    # Qualified R23 representation: create ONE_KEY_ZERO directly.
    input_log.SetKey(
        make_zero_time(),
        float(R27_NEUTRAL_VALUE),
    )

    try:
        clip.channels.AddToTail(channel)
    except Exception as exc:
        raise RuntimeError(
            "Could not register the input channel in the channels clip: %r."
            % exc
        )

    control.SetValue(
        "channel",
        channel,
    )

    channel.SetInput(
        control,
        "value",
    )

    try:
        mode_before = int(channel.GetMode())
    except Exception:
        mode_before = None

    log_line(
        "R27_R23_INPUT_CHANNEL_MODE_BEFORE_SET=%r"
        % mode_before
    )

    channel.SetMode(3)

    try:
        mode_after = int(channel.GetMode())
    except Exception:
        mode_after = None

    log_line(
        "R27_R23_INPUT_CHANNEL_MODE_AFTER_SET=%r"
        % mode_after
    )

    if mode_after != 3:
        raise RuntimeError(
            "The created head-scale input channel could not be set to native mode 3."
        )

    return control, channel, input_log


def r26_create_expression_exact(animset):
    expression = vs.CreateElement(
        "DmeExpressionOperator",
        b(R27_EXPR_NAME),
        animset.GetFileId(),
    )

    if expression is None or typ(expression) != u"DmeExpressionOperator":
        raise RuntimeError("Could not create the scale expression operator.")

    expression.expr = b(R27_EXPR_TEXT)
    expression.SetValue("value", float(R27_NEUTRAL_VALUE))
    expression.SetValue("lo", float(R27_LO))
    expression.SetValue("hi", float(R27_HI))

    animset.AddOperator(expression)

    if get_attr(expression, "result") is None:
        raise RuntimeError(
            "The DmeExpressionOperator does not expose the expected result attribute."
        )

    return expression


def r26_resolve_created_graph_exact(
    animset,
    shot,
    expected_body_transform,
    expected_group,
):
    """Exact R23-style structural validation of the newly-created graph."""
    surfaces = r26_exact_named_control_surfaces(
        animset,
        shot,
        SCALE_LITERAL,
    )

    rows = surfaces["candidates"]

    if len(rows) != 1:
        raise RuntimeError(
            "Created bip_head_scale does not resolve as one unique live control."
        )

    control = rows[0]["control"]

    if typ(control) != u"DmElement":
        raise RuntimeError("Created bip_head_scale is not DmElement.")

    value_attr = get_attr(control, "value")
    default_attr = get_attr(control, "defaultValue")

    if value_attr is None or default_attr is None:
        raise RuntimeError(
            "Created bip_head_scale lacks value/defaultValue."
        )

    if not close_enough(
        attr_value(control, "defaultValue"),
        R27_NEUTRAL_VALUE,
    ):
        raise RuntimeError(
            "Created bip_head_scale defaultValue is not neutral 0.1."
        )

    input_channel = attr_value(control, "channel")

    if input_channel is None or typ(input_channel) != u"DmeChannel":
        raise RuntimeError("Created scale control has no DmeChannel.")

    if name(input_channel) != SCALE_LITERAL:
        raise RuntimeError("Created input channel name differs from native pattern.")

    if not same_dme(attr_value(input_channel, "fromElement"), control):
        raise RuntimeError("Created input channel source is not the scale control.")

    if u(attr_value(input_channel, "fromAttribute")) != u"value":
        raise RuntimeError("Created input channel does not source control.value.")

    try:
        input_mode = int(input_channel.GetMode())
    except Exception:
        input_mode = None

    if input_mode != 3:
        raise RuntimeError("Created input channel is not native-style mode 3.")

    expression = attr_value(input_channel, "toElement")

    if (
        expression is None
        or typ(expression) != u"DmeExpressionOperator"
        or name(expression) != R27_EXPR_NAME
    ):
        raise RuntimeError(
            "Created input channel does not target bip_head_scale_rescale."
        )

    if u(attr_value(input_channel, "toAttribute")) != u"value":
        raise RuntimeError("Created input channel does not target expression.value.")

    operator_hits = r26_named_operator_hits(
        animset,
        R27_EXPR_NAME,
    )

    if (
        len(operator_hits) != 1
        or not same_dme(operator_hits[0], expression)
    ):
        raise RuntimeError(
            "Created scale expression is not uniquely registered in animset.operators."
        )

    expr_text = u(attr_value(expression, "expr"))
    normalized_expr = None

    if expr_text is not None:
        normalized_expr = expr_text.replace(" ", "").lower()

    if normalized_expr != u"lerp(value,lo,hi)":
        raise RuntimeError(
            "Created scale expression does not match lerp(value,lo,hi)."
        )

    lo = as_float(attr_value(expression, "lo"))
    hi = as_float(attr_value(expression, "hi"))

    if (
        not close_enough(lo, R27_LO)
        or not close_enough(hi, R27_HI)
    ):
        raise RuntimeError("Created expression range is not 0..10.")

    input_log = get_log(input_channel)

    if input_log is None or typ(input_log) != u"DmeFloatLog":
        raise RuntimeError("Created input channel has no DmeFloatLog.")

    if layer_count(input_log) != 1:
        raise RuntimeError("Created input log does not have exactly one layer.")

    input_layer = get_layer(input_log, 0)

    if input_layer is None or typ(input_layer) != u"DmeFloatLogLayer":
        raise RuntimeError("Created input layer is not DmeFloatLogLayer.")

    if key_count(input_layer) != 1:
        raise RuntimeError("Created input log does not have exactly one key.")

    try:
        input_empty = bool(input_log.IsEmpty())
    except Exception:
        input_empty = None

    key_time = seconds(input_layer.GetKeyTime(0))
    key_value = as_float(input_layer.GetKeyValue(0))

    if (
        input_empty is not False
        or not close_enough(key_time, 0.0)
        or key_value is None
    ):
        raise RuntimeError("Created input log is not qualified ONE_KEY_ZERO.")

    clip = get_channels_clip(animset, shot)
    channels = r26_clip_channels(clip)

    input_hits = [
        channel
        for channel in channels
        if same_dme(channel, input_channel)
    ]

    if len(input_hits) != 1:
        raise RuntimeError(
            "Created input channel is not uniquely registered in the channels clip."
        )

    output_hits = [
        channel
        for channel in channels
        if name(channel) == R27_OUTPUT_CHANNEL_NAME
    ]

    if len(output_hits) != 1:
        raise RuntimeError(
            "Created output pass-through channel does not resolve uniquely."
        )

    output = output_hits[0]

    if not same_dme(attr_value(output, "fromElement"), expression):
        raise RuntimeError("Created output source is not the scale expression.")

    if u(attr_value(output, "fromAttribute")) != u"result":
        raise RuntimeError("Created output does not source expression.result.")

    body_transform = attr_value(output, "toElement")

    if (
        body_transform is None
        or typ(body_transform) != u"DmeTransform"
        or not same_dme(body_transform, expected_body_transform)
    ):
        raise RuntimeError(
            "Created output does not target the exact bip_head body transform."
        )

    if u(attr_value(output, "toAttribute")) != u"scale":
        raise RuntimeError("Created output does not target transform.scale.")

    if get_attr(body_transform, "scale") is None:
        raise RuntimeError("Created body transform lacks scale.")

    try:
        output_mode = int(output.GetMode())
    except Exception:
        output_mode = None

    if output_mode != 1:
        raise RuntimeError("Created output channel is not pass mode 1.")

    output_log = get_log(output)

    if output_log is None or typ(output_log) != u"DmeFloatLog":
        raise RuntimeError("Created output channel has no DmeFloatLog.")

    if layer_count(output_log) != 1:
        raise RuntimeError("Created output log does not have exactly one layer.")

    output_layer = get_layer(output_log, 0)

    if output_layer is None or typ(output_layer) != u"DmeFloatLogLayer":
        raise RuntimeError("Created output layer is not DmeFloatLogLayer.")

    if key_count(output_layer) != 0:
        raise RuntimeError("Created pass-through output log must remain empty.")

    direct_group_hits = [
        member
        for member in arr(expected_group["group"], "controls")
        if same_dme(member, control)
    ]

    if len(direct_group_hits) != 1:
        raise RuntimeError(
            "Created scale control is not registered exactly once in bip_head's group."
        )

    membership_rows = []
    for group_row in group_inventory(animset):
        if any(
            same_dme(member, control)
            for member in arr(group_row["group"], "controls")
        ):
            membership_rows.append(group_row)

    if (
        len(membership_rows) != 1
        or not same_dme(
            membership_rows[0]["group"],
            expected_group["group"],
        )
    ):
        raise RuntimeError(
            "Created scale control does not have one unambiguous control-group membership."
        )

    log_line(
        "R27_R23_CREATED_CONTROL_GROUP_MEMBERSHIP count=%d paths=%r"
        % (
            len(membership_rows),
            [row["path"] for row in membership_rows],
        )
    )

    return {
        "control": control,
        "source_attr": value_attr,
        "channel": input_channel,
        "input_log": input_log,
        "input_layer": input_layer,
        "expression": expression,
        "output": output,
        "output_log": output_log,
        "output_layer": output_layer,
        "body_transform": body_transform,
        "lo": lo,
        "hi": hi,
        "group": expected_group["group"],
        "group_path": expected_group["path"],
        "input_mode": input_mode,
        "output_mode": output_mode,
    }


def r26_r23_graph_snapshot(binding):
    input_layer = binding["input_layer"]
    input_log = binding["input_log"]

    try:
        empty = bool(input_log.IsEmpty())
    except Exception:
        empty = None

    count = key_count(input_layer)
    key_time = None
    key_value = None

    if count == 1:
        key_time = seconds(input_layer.GetKeyTime(0))
        key_value = as_float(input_layer.GetKeyValue(0))

    return {
        "source": as_float(attr_value(binding["control"], "value")),
        "default": as_float(attr_value(binding["control"], "defaultValue")),
        "expr_input": as_float(attr_value(binding["expression"], "value")),
        "expr_result": as_float(attr_value(binding["expression"], "result")),
        "body_scale": as_float(attr_value(binding["body_transform"], "scale")),
        "key_count": count,
        "is_empty": empty,
        "key_time": key_time,
        "key_value": key_value,
        "input_mode": binding["input_mode"],
        "output_mode": binding["output_mode"],
        "output_key_count": key_count(binding["output_layer"]),
        "control_id": dme_id(binding["control"]),
        "input_channel_id": dme_id(binding["channel"]),
        "input_log_id": dme_id(binding["input_log"]),
        "input_layer_id": dme_id(binding["input_layer"]),
        "expression_id": dme_id(binding["expression"]),
        "output_id": dme_id(binding["output"]),
        "output_log_id": dme_id(binding["output_log"]),
        "output_layer_id": dme_id(binding["output_layer"]),
        "body_transform_id": dme_id(binding["body_transform"]),
        "group_id": dme_id(binding["group"]),
        "group_path": binding["group_path"],
    }


def r26_r23_authored_matches(snapshot, value):
    return (
        close_enough(snapshot["source"], value)
        and close_enough(snapshot["default"], R27_NEUTRAL_VALUE)
        and close_enough(snapshot["expr_input"], value)
        and snapshot["key_count"] == 1
        and snapshot["is_empty"] is False
        and close_enough(snapshot["key_time"], 0.0)
        and close_enough(snapshot["key_value"], value)
        and snapshot["input_mode"] == 3
        and snapshot["output_mode"] == 1
        and snapshot["output_key_count"] == 0
    )


def r26_create_head_scale_capability(
    fixture,
    desired_value,
    expected_lo,
    expected_hi,
):
    """
    R27 deliberately uses the R23-qualified builder pattern as exercised again
    by R25 after a real source-to-target shot switch.  The only variable added
    by R27 is coexistence with the already-qualified Body Morph writes inside
    the same named transaction.
    """
    if (
        not close_enough(expected_lo, R27_LO)
        or not close_enough(expected_hi, R27_HI)
    ):
        raise RuntimeError(
            "The saved head-size capability uses a range this adapter has not qualified."
        )

    shot = fixture["shot"]
    animset = fixture["animset"]
    body_transform = fixture["body_transform"]
    head_group = fixture["head_group"]
    clip = fixture["clip"]

    # Exact R23 construction order starts by creating transform.scale.
    scale_attr = body_transform.AddAttributeAsFloat("scale")

    if scale_attr is None:
        raise RuntimeError("Could not add body transform scale capability.")

    scale_attr.SetValue(float(1.0))

    direct_scale_value = as_float(attr_value(body_transform, "scale"))
    log_line(
        "R27_R23_SCALE_ATTR_INIT element_value=%r"
        % direct_scale_value
    )

    if not close_enough(direct_scale_value, 1.0):
        raise RuntimeError(
            "New body transform scale attribute did not initialize to 1.0."
        )

    control, input_channel, input_log = r26_create_input_control_channel_exact(
        animset,
        shot,
        clip,
    )

    expression = r26_create_expression_exact(animset)

    input_channel.SetOutput(
        expression,
        "value",
    )

    output = clip.CreatePassThruConnection(
        b(R27_OUTPUT_CHANNEL_NAME),
        expression,
        "result",
        body_transform,
        "scale",
    )

    if output is None or typ(output) != u"DmeChannel":
        raise RuntimeError(
            "CreatePassThruConnection did not create the scale output channel."
        )

    head_group["group"].AddControl(control)

    binding = r26_resolve_created_graph_exact(
        animset,
        shot,
        body_transform,
        head_group,
    )

    neutral = r26_r23_graph_snapshot(binding)
    log_line(
        "R27_R23_CREATED_NEUTRAL_GRAPH=%r"
        % neutral
    )

    if not r26_r23_authored_matches(
        neutral,
        R27_NEUTRAL_VALUE,
    ):
        raise RuntimeError(
            "The newly-created scale graph does not match the native-style neutral authored state."
        )

    # R23/R25-qualified ONE_KEY_ZERO value replacement.
    binding["input_layer"].SetKeyValue(
        0,
        float(desired_value),
    )
    binding["source_attr"].SetValue(
        float(desired_value)
    )
    binding["channel"].Operate()

    authored = r26_r23_graph_snapshot(binding)
    log_line(
        "R27_R23_CREATED_SAVED_VALUE_AUTHORED=%r"
        % authored
    )

    if not r26_r23_authored_matches(
        authored,
        desired_value,
    ):
        raise RuntimeError(
            "The newly-created scale graph could not retain the saved head-size value."
        )

    return binding


def r26_resolve_flexes(target, preset):
    flex_index = {}

    for binding in all_flex_bindings(
        target["animset"]
    ):
        key = binding_key_without_runtime_id(
            binding
        )
        flex_index.setdefault(
            key,
            [],
        ).append(
            binding
        )

    resolved = []

    for entry in preset["flexes"]:
        key = (
            entry["literal"],
            entry["shape"],
        )

        candidates = flex_index.get(
            key,
            [],
        )

        if len(candidates) != 1:
            raise RuntimeError(
                "A saved body slider could not be matched safely on this Krystal."
            )

        resolved.append(
            (
                entry,
                candidates[0],
            )
        )

    return resolved


def r26_build_flex_plan(target, preset):
    resolved = r26_resolve_flexes(
        target,
        preset,
    )

    plan = []
    changed = 0

    for entry, binding in resolved:
        snap = binding_snapshot(
            binding
        )
        side_lookup = dict(
            binding["sides"]
        )

        for side_name, desired in entry["values"].items():
            if side_name not in snap["sides"]:
                raise RuntimeError(
                    "A saved body-slider side is unavailable on this Krystal."
                )

            state = snap["sides"][
                side_name
            ]
            origin = state_kind(
                state
            )

            if (
                origin == "UNSUPPORTED"
                or not coherent(state)
            ):
                raise RuntimeError(
                    "A target body slider is outside the qualified static state."
                )

            needs_write = not matches_value(
                state,
                desired,
            )

            if needs_write:
                changed += 1

            plan.append({
                "literal": entry["literal"],
                "shape": entry["shape"],
                "side_name": side_name,
                "binding": binding,
                "side": side_lookup[
                    side_name
                ],
                "baseline": state,
                "origin": origin,
                "desired": desired,
                "needs_write": needs_write,
            })

    return plan, changed


def r26_verify_full_preset(target, shot, preset):
    resolved = r26_resolve_flexes(
        target,
        preset,
    )

    for entry, binding in resolved:
        observed = binding_snapshot(
            binding
        )

        for side_name, desired in entry["values"].items():
            if not matches_value(
                observed["sides"][side_name],
                desired,
            ):
                raise RuntimeError(
                    "The saved body did not fully evaluate after refresh."
                )

    scale_entry = preset["scales"][0]

    scale_binding = resolve_qualified_head_scale(
        target["animset"],
        shot,
        target["gm"],
    )

    if (
        not close_enough(
            scale_binding["lo"],
            scale_entry["lo"],
        )
        or not close_enough(
            scale_binding["hi"],
            scale_entry["hi"],
        )
    ):
        raise RuntimeError(
            "The created head-size capability differs from the saved capability."
        )

    scale_state = scale_snapshot(
        scale_binding
    )

    if not scale_evaluated_matches(
        scale_binding,
        scale_state,
        scale_entry["value"],
    ):
        raise RuntimeError(
            "The saved head size did not fully evaluate after refresh."
        )

    return scale_binding, scale_state



# -------------------------------------------------------------------------------------------------
# P04 - Production Scale Adapter Integration
#
# Purpose:
#   Integrate the already-qualified Krystal2020 Body Morph + Head Scale path
#   into the production Body Preset persistence/execution contract.
#
# This is NOT new scale-mechanics research.
# -------------------------------------------------------------------------------------------------

import ctypes
import uuid



P04_SCHEMA_VERSION = 2
P04_PROFILE_ID = u"sfm-character-krystal2020-v1"
P04_PROFILE_REVISION = 3
P04_PRESET_ID = u"p04-production-scale-body-v1"
P04_PRESET_NAME = u"P04 Production Scale Body"
P04_CHARACTER_FOLDER = u"Krystal 2020--krystal2020-v1"
P04_LIBRARY_DIRNAME = u"SFM Character Preset Tool"
P04_BODY_FOLDER = u"Body Presets"

P04_SCALE_LOGICAL_ID = u"body.scale.head"
P04_SCALE_CONTRACT_ID = u"head_scale_lerp_v1"
P04_SCALE_BUILDER_ID = u"native_style_head_scale_v1"

P04_RESULT_PASS = (
    "P04_RESULT=PASS_PRODUCTION_BODY_SCALE_ADAPTER_SAVE_APPLY_REPEAT_NOOP_ONE_UNDO"
)


class P04GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


P04_FOLDERID_DOCUMENTS = P04GUID(
    0xFDD39AD0,
    0x238F,
    0x46AF,
    (ctypes.c_ubyte * 8)(
        0xAD, 0xB4, 0x6C, 0x85,
        0x48, 0x03, 0x69, 0xC7,
    ),
)


def p04_documents():
    out = ctypes.c_wchar_p()

    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(P04_FOLDERID_DOCUMENTS),
        0,
        None,
        ctypes.byref(out),
    )

    if result != 0 or not out.value:
        raise RuntimeError(
            "Windows could not resolve the current user's Documents folder."
        )

    try:
        path = unicode(out.value)
    finally:
        try:
            ctypes.windll.ole32.CoTaskMemFree(out)
        except Exception:
            pass

    if path.rstrip(u"\\/").lower() == u"c:\\users\\public\\documents":
        raise RuntimeError(
            "The preset library resolved to Public Documents."
        )

    return path


def p04_paths():
    character_root = os.path.join(
        p04_documents(),
        P04_LIBRARY_DIRNAME,
        u"Characters",
        P04_CHARACTER_FOLDER,
    )
    body_dir = os.path.join(
        character_root,
        P04_BODY_FOLDER,
    )

    return {
        "character_root": character_root,
        "body_dir": body_dir,
        "profile": os.path.join(
            character_root,
            u"character.json",
        ),
        "preset": os.path.join(
            body_dir,
            u"P04 Production Scale Body--p04-production-scale-body-v1.json",
        ),
    }


def p04_ensure_dir(path):
    if os.path.isdir(path):
        return

    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def p04_json_text(record):
    return (
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + u"\n"
    )


def p04_unique_temp(path):
    stamp = datetime.datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )
    return (
        path
        + u".tmp-p04-"
        + unicode(os.getpid())
        + u"-"
        + unicode(stamp)
        + u"-"
        + unicode(uuid.uuid4().hex[:8])
    )


def p04_safe_write_json(path, record):
    p04_ensure_dir(
        os.path.dirname(path)
    )

    temp_path = p04_unique_temp(
        path
    )
    backup_path = path + u".bak"
    payload = p04_json_text(
        record
    ).encode(
        "utf-8"
    )

    fp = open(
        temp_path,
        "wb",
    )

    try:
        fp.write(
            payload
        )
        fp.flush()
        os.fsync(
            fp.fileno()
        )
    finally:
        fp.close()

    try:
        if os.path.exists(
            path
        ):
            result = ctypes.windll.kernel32.ReplaceFileW(
                ctypes.c_wchar_p(path),
                ctypes.c_wchar_p(temp_path),
                ctypes.c_wchar_p(backup_path),
                0,
                None,
                None,
            )

            if not result:
                code = ctypes.windll.kernel32.GetLastError()
                raise RuntimeError(
                    "Windows could not safely replace %r (error %d)."
                    % (
                        path,
                        code,
                    )
                )

        else:
            result = ctypes.windll.kernel32.MoveFileExW(
                ctypes.c_wchar_p(temp_path),
                ctypes.c_wchar_p(path),
                0x8,
            )

            if not result:
                code = ctypes.windll.kernel32.GetLastError()
                raise RuntimeError(
                    "Windows could not finish saving %r (error %d)."
                    % (
                        path,
                        code,
                    )
                )

    except Exception:
        log_line(
            "P04_STORAGE_FAILURE path=%r temp_exists=%r backup_exists=%r destination_exists=%r"
            % (
                path,
                os.path.exists(
                    temp_path
                ),
                os.path.exists(
                    backup_path
                ),
                os.path.exists(
                    path
                ),
            )
        )
        raise

    return {
        "destination": path,
        "backup_exists": os.path.exists(
            backup_path
        ),
        "temp_exists_after": os.path.exists(
            temp_path
        ),
        "bytes": len(
            payload
        ),
    }


def p04_read_json(path):
    fp = open(
        path,
        "rb",
    )

    try:
        raw = fp.read()
    finally:
        fp.close()

    return json.loads(
        raw.decode(
            "utf-8"
        )
    )


def p04_flex_id(literal):
    return u"body.flex." + u(literal)


def p04_physical_multiplier(
    native_value,
    lo,
    hi,
):
    return (
        float(lo)
        + (
            float(native_value)
            * (
                float(hi)
                - float(lo)
            )
        )
    )


def p04_native_scalar(
    multiplier,
    lo,
    hi,
):
    denominator = (
        float(hi)
        - float(lo)
    )

    if close_enough(
        denominator,
        0.0,
    ):
        raise RuntimeError(
            "Head Scale contract has a degenerate numeric range."
        )

    return (
        float(multiplier)
        - float(lo)
    ) / denominator


def p04_build_records(
    krystal,
    probe_preset,
):
    controls = {}
    values = {}

    for entry in probe_preset[
        "flexes"
    ]:
        logical_id = p04_flex_id(
            entry[
                "literal"
            ]
        )

        controls[
            logical_id
        ] = {
            "literal": entry[
                "literal"
            ],
            "semantic_category": "body_morph",
            "representation": entry[
                "shape"
            ],
            "completeness": "required",
            "permissions": {
                "body_capture": True,
                "body_apply": True,
            },
        }

        value_record = {
            "representation": entry[
                "shape"
            ],
        }

        if entry[
            "shape"
        ] == "MONO":
            if sorted(
                entry[
                    "values"
                ].keys()
            ) != [
                "mono",
            ]:
                raise RuntimeError(
                    "MONO Body Morph %r did not contain exactly one mono value."
                    % entry[
                        "literal"
                    ]
                )

            value_record[
                "mono"
            ] = float(
                entry[
                    "values"
                ][
                    "mono"
                ]
            )

        elif entry[
            "shape"
        ] == "STEREO":
            if sorted(
                entry[
                    "values"
                ].keys()
            ) != [
                "left",
                "right",
            ]:
                raise RuntimeError(
                    "STEREO Body Morph %r did not contain exactly left/right values."
                    % entry[
                        "literal"
                    ]
                )

            value_record[
                "left"
            ] = float(
                entry[
                    "values"
                ][
                    "left"
                ]
            )
            value_record[
                "right"
            ] = float(
                entry[
                    "values"
                ][
                    "right"
                ]
            )

        else:
            raise RuntimeError(
                "Unsupported Body Morph representation %r."
                % entry[
                    "shape"
                ]
            )

        values[
            logical_id
        ] = value_record

    scale_entry = probe_preset[
        "scales"
    ][0]

    multiplier = p04_physical_multiplier(
        scale_entry[
            "value"
        ],
        scale_entry[
            "lo"
        ],
        scale_entry[
            "hi"
        ],
    )

    controls[
        P04_SCALE_LOGICAL_ID
    ] = {
        "literal": SCALE_LITERAL,
        "semantic_category": "body_proportion",
        "representation": "scale_multiplier",
        "completeness": "required",
        "permissions": {
            "body_capture": True,
            "body_apply": True,
        },
        "contract_id": P04_SCALE_CONTRACT_ID,
    }

    values[
        P04_SCALE_LOGICAL_ID
    ] = {
        "representation": "scale_multiplier",
        "value": float(
            multiplier
        ),
    }

    profile = {
        "schema_version": P04_SCHEMA_VERSION,
        "profile_id": P04_PROFILE_ID,
        "revision": P04_PROFILE_REVISION,
        "display_name": "Krystal 2020",
        "default_body_preset_id": P04_PRESET_ID,
        "models": [
            {
                "path": krystal[
                    "model"
                ],
                "checksum": int(
                    krystal[
                        "checksum"
                    ]
                ),
                "status": "accepted",
            },
        ],
        "controls": controls,
        "scale_contracts": {
            P04_SCALE_CONTRACT_ID: {
                "target_bone": "bip_head",
                "input_literal": SCALE_LITERAL,
                "portable_value": "scale_multiplier",
                "native_value": "normalized_scalar",
                "lo": float(
                    scale_entry[
                        "lo"
                    ]
                ),
                "hi": float(
                    scale_entry[
                        "hi"
                    ]
                ),
                "builder": P04_SCALE_BUILDER_ID,
            },
        },
        "semantic_provenance": {
            "body_scope": (
                "qualified Body Morphs group + qualified Krystal2020 bip_head Head Scale"
            ),
        },
    }

    preset = {
        "schema_version": P04_SCHEMA_VERSION,
        "preset_id": P04_PRESET_ID,
        "profile_id": P04_PROFILE_ID,
        "kind": "body",
        "name": P04_PRESET_NAME,
        "capture_profile_revision": P04_PROFILE_REVISION,
        "model_ref": {
            "path": krystal[
                "model"
            ],
            "checksum": int(
                krystal[
                    "checksum"
                ]
            ),
        },
        "values": values,
    }

    return profile, preset, multiplier


def p04_validate_disk(
    profile,
    preset,
):
    if profile.get(
        "schema_version"
    ) != P04_SCHEMA_VERSION:
        raise RuntimeError(
            "Krystal profile schema is unsupported."
        )

    if profile.get(
        "profile_id"
    ) != P04_PROFILE_ID:
        raise RuntimeError(
            "Krystal profile ID is unexpected."
        )

    if preset.get(
        "schema_version"
    ) != P04_SCHEMA_VERSION:
        raise RuntimeError(
            "Body Preset schema is unsupported."
        )

    if preset.get(
        "profile_id"
    ) != P04_PROFILE_ID:
        raise RuntimeError(
            "Body Preset belongs to another profile."
        )

    if preset.get(
        "kind"
    ) != "body":
        raise RuntimeError(
            "Saved Krystal preset is not a Body Preset."
        )

    scale_contracts = profile.get(
        "scale_contracts"
    )

    if not isinstance(
        scale_contracts,
        dict,
    ):
        raise RuntimeError(
            "Krystal profile has no scale contract."
        )

    contract = scale_contracts.get(
        P04_SCALE_CONTRACT_ID
    )

    if not isinstance(
        contract,
        dict,
    ):
        raise RuntimeError(
            "Krystal profile is missing the qualified Head Scale contract."
        )

    if (
        contract.get(
            "target_bone"
        )
        != "bip_head"
        or contract.get(
            "input_literal"
        )
        != SCALE_LITERAL
        or contract.get(
            "portable_value"
        )
        != "scale_multiplier"
        or contract.get(
            "builder"
        )
        != P04_SCALE_BUILDER_ID
    ):
        raise RuntimeError(
            "Krystal Head Scale contract differs from the qualified production contract."
        )

    values = preset.get(
        "values"
    )

    if not isinstance(
        values,
        dict,
    ):
        raise RuntimeError(
            "Krystal Body Preset values are malformed."
        )

    scale_value = values.get(
        P04_SCALE_LOGICAL_ID
    )

    if not isinstance(
        scale_value,
        dict,
    ):
        raise RuntimeError(
            "Krystal Body Preset is missing required Head Scale."
        )

    if scale_value.get(
        "representation"
    ) != "scale_multiplier":
        raise RuntimeError(
            "Saved Head Scale is not explicitly typed as scale_multiplier."
        )

    return True


def p04_disk_to_probe(
    profile,
    preset,
):
    p04_validate_disk(
        profile,
        preset,
    )

    contract = profile[
        "scale_contracts"
    ][
        P04_SCALE_CONTRACT_ID
    ]

    lo = float(
        contract[
            "lo"
        ]
    )
    hi = float(
        contract[
            "hi"
        ]
    )

    flexes = []

    for logical_id, value_record in sorted(
        preset[
            "values"
        ].items()
    ):
        if logical_id == P04_SCALE_LOGICAL_ID:
            continue

        control_record = profile[
            "controls"
        ].get(
            logical_id
        )

        if not isinstance(
            control_record,
            dict,
        ):
            raise RuntimeError(
                "Saved Body Morph %r has no profile control record."
                % logical_id
            )

        if control_record.get(
            "semantic_category"
        ) != "body_morph":
            raise RuntimeError(
                "Saved non-scale Body value %r is not a Body Morph."
                % logical_id
            )

        shape = value_record.get(
            "representation"
        )

        values = {}

        if shape == "MONO":
            values[
                "mono"
            ] = float(
                value_record[
                    "mono"
                ]
            )

        elif shape == "STEREO":
            values[
                "left"
            ] = float(
                value_record[
                    "left"
                ]
            )
            values[
                "right"
            ] = float(
                value_record[
                    "right"
                ]
            )

        else:
            raise RuntimeError(
                "Saved Body Morph %r has unsupported representation."
                % logical_id
            )

        flexes.append(
            {
                "literal": control_record[
                    "literal"
                ],
                "shape": shape,
                "values": values,
            }
        )

    scale_record = preset[
        "values"
    ][
        P04_SCALE_LOGICAL_ID
    ]

    multiplier = float(
        scale_record[
            "value"
        ]
    )

    native_value = p04_native_scalar(
        multiplier,
        lo,
        hi,
    )

    return {
        "schema_probe": 2,
        "preset_kind": "body",
        "model_path": preset[
            "model_ref"
        ][
            "path"
        ],
        "model_checksum": int(
            preset[
                "model_ref"
            ][
                "checksum"
            ]
        ),
        "flexes": flexes,
        "scales": [
            {
                "kind": "qualified_head_scale",
                "literal": SCALE_LITERAL,
                "value": native_value,
                "lo": lo,
                "hi": hi,
                "contract": "lerp_value_lo_hi_to_transform_scale_v1",
                "physical_multiplier": multiplier,
            },
        ],
    }


def p04_scale_topology_probe(
    target,
    shot,
):
    animset = target[
        "animset"
    ]

    head_control = r26_unique_head_control(
        animset
    )

    try:
        body_transform = head_control.GetTransform()
    except Exception as exc:
        raise RuntimeError(
            "Krystal's bip_head transform could not be resolved: %r."
            % exc
        )

    if (
        body_transform is None
        or typ(
            body_transform
        ) != u"DmeTransform"
    ):
        raise RuntimeError(
            "Krystal's bip_head does not resolve to the qualified body transform."
        )

    head_group = r26_unique_head_group(
        animset,
        head_control,
    )
    clip = get_channels_clip(
        animset,
        shot,
    )

    scale_candidates = r26_scale_control_candidates(
        animset,
        shot,
    )

    direct_group_scale = [
        control
        for control in arr(
            head_group[
                "group"
            ],
            "controls",
        )
        if name(
            control
        ) == SCALE_LITERAL
    ]

    signals = {
        "body_has_scale": (
            get_attr(
                body_transform,
                "scale",
            )
            is not None
        ),
        "scale_control_count": len(
            scale_candidates
        ),
        "expression_count": r26_named_operator_count(
            animset,
            R27_EXPR_NAME,
        ),
        "input_channel_name_count": r26_named_channel_count(
            clip,
            SCALE_LITERAL,
        ),
        "output_channel_name_count": r26_named_channel_count(
            clip,
            R27_OUTPUT_CHANNEL_NAME,
        ),
        "head_group_scale_count": len(
            direct_group_scale
        ),
    }

    clean_absent = (
        signals[
            "body_has_scale"
        ] is False
        and signals[
            "scale_control_count"
        ] == 0
        and signals[
            "expression_count"
        ] == 0
        and signals[
            "input_channel_name_count"
        ] == 0
        and signals[
            "output_channel_name_count"
        ] == 0
        and signals[
            "head_group_scale_count"
        ] == 0
    )

    if clean_absent:
        return {
            "kind": "absent",
            "fixture": r26_absence_fixture(
                target,
                shot,
            ),
            "binding": None,
            "baseline": None,
            "signals": signals,
        }

    try:
        binding = resolve_qualified_head_scale(
            animset,
            shot,
            target[
                "gm"
            ],
        )
    except Exception as exc:
        raise RuntimeError(
            "Krystal has partial, conflicting, or unsupported Head Scale topology. "
            "Nothing was changed. Detail: %r"
            % exc
        )

    state = scale_snapshot(
        binding
    )
    origin = scale_state_kind(
        state
    )

    if origin == "UNSUPPORTED":
        raise RuntimeError(
            "Krystal's existing Head Scale is animated or otherwise outside the qualified static contract."
        )

    if not scale_evaluated_matches(
        binding,
        state,
        state[
            "source"
        ],
    ):
        raise RuntimeError(
            "Krystal's existing Head Scale is not fully coherent/evaluated."
        )

    return {
        "kind": "existing",
        "fixture": None,
        "binding": binding,
        "baseline": state,
        "origin": origin,
        "signals": signals,
    }


def p04_flex_baselines_match(
    target,
    plan,
):
    flex_index = {}

    for binding in all_flex_bindings(
        target[
            "animset"
        ]
    ):
        key = binding_key_without_runtime_id(
            binding
        )
        flex_index.setdefault(
            key,
            [],
        ).append(
            binding
        )

    for item in plan:
        key = (
            item[
                "literal"
            ],
            item[
                "shape"
            ],
        )

        candidates = flex_index.get(
            key,
            [],
        )

        if len(
            candidates
        ) != 1:
            return False

        binding = candidates[
            0
        ]
        side_lookup = dict(
            binding[
                "sides"
            ]
        )

        side = side_lookup.get(
            item[
                "side_name"
            ]
        )

        if side is None:
            return False

        observed = side_snapshot(
            binding[
                "control"
            ],
            side,
        )

        if not matches_baseline(
            observed,
            item[
                "baseline"
            ],
            item[
                "origin"
            ],
        ):
            return False

    return True


def p04_verify_preapply_scale_baseline(
    target,
    shot,
    scale_preflight,
):
    if scale_preflight[
        "kind"
    ] == "absent":
        now = r26_absence_fixture(
            target,
            shot,
        )

        return r26_absence_counts_match(
            now[
                "state"
            ],
            scale_preflight[
                "fixture"
            ][
                "state"
            ],
        )

    binding = resolve_qualified_head_scale(
        target[
            "animset"
        ],
        shot,
        target[
            "gm"
        ],
    )

    return scale_baseline_matches(
        binding,
        scale_snapshot(
            binding
        ),
        scale_preflight[
            "baseline"
        ],
    )


def p04_apply_once(
    target,
    shot,
    probe_preset,
):
    if (
        target[
            "model"
        ]
        != probe_preset[
            "model_path"
        ]
        or int(
            target[
                "checksum"
            ]
        )
        != int(
            probe_preset[
                "model_checksum"
            ]
        )
    ):
        raise RuntimeError(
            "This Krystal model revision differs from the saved Body Preset."
        )

    # CRITICAL R27/R29 invariant:
    # no same-time refresh is permitted here before missing Head Scale creation.
    log_line(
        "P04_TARGET_PRECREATE_REFRESH_SKIPPED=True "
        "reason='R27_R29_QUALIFIED_CONSTRUCTION_BOUNDARY'"
    )

    scale_preflight = p04_scale_topology_probe(
        target,
        shot,
    )

    plan, flex_changed = r26_build_flex_plan(
        target,
        probe_preset,
    )

    scale_entry = probe_preset[
        "scales"
    ][0]

    scale_needs_write = True

    if scale_preflight[
        "kind"
    ] == "existing":
        current = scale_snapshot(
            scale_preflight[
                "binding"
            ]
        )

        scale_needs_write = not scale_evaluated_matches(
            scale_preflight[
                "binding"
            ],
            current,
            scale_entry[
                "value"
            ],
        )

    total_changed = (
        flex_changed
        + (
            1
            if (
                scale_preflight[
                    "kind"
                ] == "absent"
                or scale_needs_write
            )
            else 0
        )
    )

    undo_before = undo_state(
        "P04_UNDO_BEFORE_APPLY"
    )

    if total_changed == 0:
        undo_after = undo_state(
            "P04_UNDO_AFTER_NOOP"
        )

        if undo_after != undo_before:
            raise RuntimeError(
                "A true repeat Body Preset no-op changed native Undo state."
            )

        log_line(
            "P04_APPLY_ONCE outcome='no-op' flex_changed=0 scale_changed=False undo_unchanged=True"
        )

        return {
            "outcome": "no-op",
            "undo_before": undo_before,
            "undo_after": undo_after,
        }

    data_model = dm()
    scope_open = False

    try:
        data_model.StartUndo(
            b(
                u"Apply Body Preset - Krystal"
            ),
            b(
                u"Redo Apply Body Preset - Krystal"
            ),
        )
        scope_open = True

        if scale_preflight[
            "kind"
        ] == "absent":
            scale_binding = r26_create_head_scale_capability(
                scale_preflight[
                    "fixture"
                ],
                scale_entry[
                    "value"
                ],
                scale_entry[
                    "lo"
                ],
                scale_entry[
                    "hi"
                ],
            )

        else:
            scale_binding = scale_preflight[
                "binding"
            ]

            if scale_needs_write:
                write_head_scale(
                    scale_binding,
                    scale_entry[
                        "value"
                    ],
                    scale_preflight[
                        "origin"
                    ],
                )

        for item in plan:
            if not item[
                "needs_write"
            ]:
                continue

            write_side(
                item[
                    "binding"
                ],
                item[
                    "side"
                ],
                item[
                    "origin"
                ],
                item[
                    "desired"
                ],
            )

        for item in plan:
            if not item[
                "needs_write"
            ]:
                continue

            observed = side_snapshot(
                item[
                    "binding"
                ][
                    "control"
                ],
                item[
                    "side"
                ],
            )

            if not authored_side_matches(
                observed,
                item[
                    "desired"
                ],
            ):
                raise RuntimeError(
                    "A changed Body Morph could not be authored safely."
                )

        scale_immediate = scale_snapshot(
            scale_binding
        )

        if not scale_authored_matches(
            scale_immediate,
            scale_entry[
                "value"
            ],
        ):
            raise RuntimeError(
                "The Head Scale writer did not retain the saved value."
            )

        data_model.FinishUndo()
        scope_open = False

    except Exception:
        if scope_open:
            data_model.AbortUndoableOperation()
            scope_open = False

        # Verify rollback using the pre-Apply representation.
        same_time_refresh(
            float(
                sfmApp.GetHeadTimeInSeconds()
            ),
            "P04_ABORT",
        )

        rollback_shot = current_shot()
        rollback_target = unique_krystal(
            rollback_shot
        )

        scale_ok = p04_verify_preapply_scale_baseline(
            rollback_target,
            rollback_shot,
            scale_preflight,
        )
        flex_ok = p04_flex_baselines_match(
            rollback_target,
            plan,
        )

        log_line(
            "P04_ABORT_ROLLBACK_VERIFY scale_ok=%r flex_ok=%r"
            % (
                scale_ok,
                flex_ok,
            )
        )

        raise

    undo_after = undo_state(
        "P04_UNDO_AFTER_COMMIT"
    )

    head_time = float(
        sfmApp.GetHeadTimeInSeconds()
    )

    same_time_refresh(
        head_time,
        "P04_APPLY",
    )

    shot_after = current_shot()
    target_after = unique_krystal(
        shot_after
    )

    try:
        scale_after, scale_state_after = r26_verify_full_preset(
            target_after,
            shot_after,
            probe_preset,
        )
    except Exception as exc:
        log_line(
            "P04_APPLY_ONCE outcome='committed-unverified' flex_changed=%d "
            "scale_preflight=%r error=%r"
            % (
                flex_changed,
                scale_preflight[
                    "kind"
                ],
                exc,
            )
        )

        return {
            "outcome": "committed-unverified",
            "plan": plan,
            "scale_preflight": scale_preflight,
            "head_time": head_time,
            "undo_before": undo_before,
            "undo_after": undo_after,
            "target_shot_id": dme_id(
                shot_after
            ),
            "target_animset_name": target_after[
                "animset_name"
            ],
            "error": repr(
                exc
            ),
        }

    log_line(
        "P04_APPLY_ONCE outcome='committed' flex_changed=%d "
        "scale_preflight=%r native_scale=%r physical_multiplier=%r"
        % (
            flex_changed,
            scale_preflight[
                "kind"
            ],
            scale_state_after[
                "source"
            ],
            scale_state_after[
                "bone_scale"
            ],
        )
    )

    return {
        "outcome": "committed",
        "plan": plan,
        "scale_preflight": scale_preflight,
        "head_time": head_time,
        "undo_before": undo_before,
        "undo_after": undo_after,
        "target_shot_id": dme_id(
            shot_after
        ),
        "target_animset_name": target_after[
            "animset_name"
        ],
    }




# -------------------------------------------------------------------------------------------------
# Unified production profile dispatch
# -------------------------------------------------------------------------------------------------


PROD_WINDOW_ICON_NAME = u"SFMCPMIconWoman.png"
PROD_WINDOW_ICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAOiElEQVR42u1bCXgUVRKuej2TOyFyhTMEhXCIIRxZAuKCCOqKLIrr"
    "J4fy4e3C8rG6qCt+oq4uonjiBaugn6uyqNwIEkQBBQUEOTYkyGEAAyFAArkmmUy/2nrdPcmcCSaEDPvZ+Trd08d7VfWq6v1Vrxrg"
    "t63xNsTGp8F2oTqy2+2g667eRDACgH7Hx85A0NSSwxkCOIiIW3hfREQ7eb8wg3AhOhGIqQT0KvN0leqz2SUAXToiNG/K3TOfp5n9"
    "n34mOFUAim2WAa4WAifpusz5P1BzvI0PZeFhICeOQ7ltsZDOLE26sjWpZ5tHF/+uzLLJrYtscvzNQgoBkkWTx0LoflFrAI98uiRa"
    "3741hi2bIyAl2exR6bwx1B5UWENv/FyylmDsgzpUVkKmpok+Ll06G4pGraEajoqKYgYqP+ORT/zq3xpc0YUZFIEdH3o4RGX53S5D"
    "kBJg/VZqyb8P8aWdDTZIDdWww+HowsSnjRkhoEdyEKbdKoi+KkkwebwAFp46v+3inAWIeqnD4HQkHl2DL5eOsGMvwJZdBAdyCArO"
    "gnGvueUUr+qLPPpkaEN8LEFX1oTdWZR6sU6DdreKnSpEePV9Ce8vlnA835zebGx8sTGmYIpLgKdI86UeyQgP3ytg9HBkH2JcCr9Y"
    "vX9PPuh9egjZtAkann1If5RvPiXkrpWaLNvNnn+vuZfy+bZFmj5zqiaTk1CyBshhVwo9zG7MBhsuOuZtdi2SBfAMn1YqZoZfjQbT"
    "Lmv6q2mvyLTJWY8KabeB0gmd39+sCdFgZnDep0Ge+joyilvKhPe4jdX4obsQe3V3u3iqAQOTFzk7s4CWfUkwd4GE/AIlSJwWGRn+"
    "cllZeegKgIFLkpS0sUkstPtgloDhg9CnB6q9S7Qes07ZUcI9j0tgYbDDxKdZuP8ISRxg07QIKWVGdCQkr56nwZB0ixO0jl68Y61D"
    "gtYcGcku8JbrBOw9QJh1kAaxhvEcAvtCDgfoUj7GhKXOni4gPdUn3CNTE9BriMlDK8hPSZS1GDufazaC+TM1uCwRkTXgTUaH0SGl"
    "AeykWjHkXTh0ANpf/LsF9zwHGckD9pCPFqCnRnjrCVZfCWNQ1KENwsJVFMtXTvK+JWQ0QJK8X2nr01M8nB1Z/FAguw9sAu98Arh6"
    "YxD/yPuIIQomGxfujgsPDw0TiGaj521MSjeEfinoTbUv726dDhDqH81DmPaiDhu2VpuGb0pAacRYhtZ8/fJSV2VSSAjA4ahozQR1"
    "uvHqAMxXjR75BwAepl9RgUb0V1gEsHYTVfuNAIIaNsDSOkn9QkIA7JS6KJb69vC1e/TefVTf7eU55IU7Htbh+50El7Zn7J9N8GNW"
    "cEtRUNlmeq7OIeIDSKW1oE0rLxjsb8Beu/n/bDHCzZMIlmQQTJkg4JPXNAP///NNChAhmlsEm36LZoYKNQsRAaA0EaDJGfpofJAA"
    "GLbsBki/VYeMbyRNnyxg1iMIvbrznH+9gGXrJCxfBwFNwC0EZQUhIQAe7OPqwHAVLdflE+dXM63+H88HmPQ0waAxOpWUAi15W8AT"
    "E9HMEvHfK9MQEniE731chwNHq3XI07sUlxqtnQgNDUDcw7Q7Nm+vnt/J/efhCP+7nxn/B8f41+nw/iIJD4xF3L0CGS7zC1jNYkJz"
    "gIWvCVCQ/8Z7JeT6sHksH7CgUKFiyAwNDQCI4kP5yUL0U/czbOMvvEOQdouEXn/U4dNVEu4fIyDrCwGvThNwSRNPZ0FV8O/KPgCf"
    "zhZw7ATB4HESMvd7xRsUHWU8PjwkgiEeiuejI+nhfWs1Hj2EAzlAnRIJc3IRhk7Q6WwR4Y3XCLiJQcx1v0e3/fpOJVamFKriB/Vz"
    "yy6AURN1JSjY87lmIEqVXHp0lk4vvUsVmk1r73LppxtNA8LD7KzvNE45rgSeCxasIMjNN7wA3TFVV44Rdyy3wXvPIYwcFoR5z4yo"
    "BypWMumXAjBhlIDDuQROl1tJCO4YaZAdoevy+kZNibl0vTnT1Lp/b3ZMZYDPviVh1woNM74lI++3YYEG7VvRrwuHfe6ndmMHUwFw"
    "6AjbWiRCeTkZcDgqCqjMYWCQRvUBKmtDUkf4z+eMTJIUSCFY8RUT2Qmpf0/wR4dVUID8XbyPHNStls3NE5VXVInSp99QzlVFhcZD"
    "eqNqgM2mFUhd7lu+jrrGsGNSYbBy6D//ApDUzjcZgtUQGM/B/ZA3qFQhV1wM4qYdkpauA3Q4jCa2NKoGVFRUKupmrNmogIskhsOk"
    "IDxDVSo4EwTMI9Q88j73jhwzj20SFNSS0KYFwPipyiHAtjCbtrbRp0FNEx+xEF5xMU2p3UGpJuUXEDKmp1IH1sAseYTNwd2Eig7V"
    "pcz9unGjcwcApxOOoRAjKypdeqMLwGXQQMVqxbcZT1cZ3wL+sIdcZQ7ABStrmGzR0+UH9oEqVliSIdV9xyvzzQc7tjce0Hg2CBEk"
    "aG4xsTEmTyu/NrhZy4zsnvG2hJIy9M751IZCPITxwjuShcCBscAZ3/0oyeHUKCrKTEMkKMgYOgLAE6c4FtB1UilstXF8gI8cOUb0"
    "4AzpH9pjkBjJQ1KbdwC9PF8qqS5jS8nQdcDiEol5+cZCW15e3snQEQCTtKa4BEhFeO3NsLgzq2gGX5/z3mcSZs6tBjtGeoCCp72U"
    "BLIOIv1pso7sV/IE4iR+pVuTOICm8QhfbJTqqZUQSlt8fLyCxAuHDRTym4+FWtqq1ARebrdrYXy+khnQ/3aPppfvtZkrQPuCrQzZ"
    "5PqPbLJFU2NJrIBxf9+ICE0FPps4hpDznjPaLmTH2xZCbbPZRDwTt23S7ZocOdQgdJWFFcKYmZ8VaOrfG+X2ZbaqqhBP5s/s0ORj"
    "DwipSonUszzyo6xYY1RcDOjzntNkbDQWs1CGQqhuYWEilhlf3LolMjaEovAwm9vMD7RshrJzkln+csMgIec+I+TXH2pyxVybnHq3"
    "kOo+xwqyXyq6BXCDZTIvNbsEdbsNj9k00RdCfbPqetSiZoahAZoWo8LloQNRluwS8q2nNNmzG0qGNUpIStVlfBzI+0YLmb1GyMVv"
    "aSrTwxqEUy0NuNlsD19rEM093w2yx+7KTC1lVz1RQRhdyjuVclzVByEyAuG+0cC7BidOER5mlKcgdOckALtmqkpcNEGYXSVLaSyb"
    "z2xNwyVOpz6F76bDxbSxo2ptLZFXtG4B8vjmAE4vwHK5qhybPF5YWgAbWaMGR0SENVgpT70SIjGxUaLcUZEgpUzkkW/PlxiokkpX"
    "q4LIVBUWDOyLwPYOyR1rAv3ogy4BnnqdYPYHkkNe424+/9vKZ9l8+zDvuSycXCHE0ajI8Pyi4jK6YALgkU2UkiYw8cOY/p7cc7R7"
    "fmdvjUltEbpcitTncsJrr0S4oos7KqSAeWIKEgio9grPAqjcglozyD4EkJMLlJtHRr7Qo9SgiA87+GyVJsR8l64XNogAwsPt6HS6"
    "HmGA8yR3GpGWgnB1P4Se3YCSOwB24Jk5Pg69FjSrUl3nnAzxDxc8E6vqdVU+d/oMC+MXgp9ymPNMgDUspOyDRjb6NJvd/ZJo8XkX"
    "ADf8MjP/1wG9Ed6YjpDSxVryRQgc33oUPpJn7g/Au0KEfCIhpF9BXrVQ124C+POTUglGTaF3shA+PG8CUOWuzPzHNwxC/Ox1YSxV"
    "+wV2Xokf8k+CVDGL/r3WVhhdQ1l5VdWpqq09iTBonA4HDpODnWcam+reeguAbT5G1+VPbROw1a7lAuKb1Gly9PB37ooRL1sJLJhz"
    "Mh1LEa1mtnI8MnCMrkxlXXh42LDycmf9giGW4j18aDX9L1jFPHoNCgWOZX2THr6LpL6loliL4ALMHujRljuWSksBGD1cqOTxEKez"
    "Mq1e0WCY0nWiu5vFA9w+sppCwmC+HKuZ9hr1WlJfGMQcKJj6m/2Qr8+xTieNM0XLTd1ZLwG4XJWduN3uI65x1+3WOH2DX3IfakmA"
    "om+iwEfda/ykBP3ocTelZqjENoYw/xBlZVDqJACWoCpHwCHp/v2Sl8ZjANrQn0EKEP8jBGk8QLKAzm2GUN0OSjOWqxOdFRUJ9fEB"
    "PdQ/o9CRfOzf+q3S00u/xBpUHANojHetQE0K5JdWt15/e4G01qEDN5HS1RwFRqnJdRcAUTtNqBy/r51Wn019niDvlKQaNdVv2sNq"
    "DalRJuSPhKw2N/0AMP9TGVTuHdtVnbepjwbExsYARYShl49yk3TwCOA8JkKVr/2qSbZKKAFsAs9tBmzXCmDGHDKqzBH8q3FU+sxq"
    "IbruAkDMOlsMMPkZCUWl/pR8sprApQNFR9YhFiHwd3iBnB4FUCMyq0TUoul3O6vrsEwRImzYhjDlWUM7XPzWrjoLgNHUE9zxB3M+"
    "ltT1Wh1m/ovDskKsyulv2m6SXlBUhy8AMcjCSJUy1FBYzZdOmtlnYxFWPVFWYa5PDmYkOHS8C/bso5MMiW9lSLy9XkiQY3FgQDFU"
    "FSkzTekqWTGkv4DhgxFeeFfS0WOE6vMWVdpyjrDd/7dn0OQ5vQSRq1L7HsMl7M8hGtBHYOsWKmqUxocXChHze3MYwb7uctUeGZ7z"
    "yMXGRkJpaXkaC2I803cTk9jWTSmrIz50l4D0XhwkJSO0SVCqRYEdJ0INcz/5Ywi+VO5EOvQLYOZ+gh8Z3a//XjLkJU8DyWGmv+Lj"
    "EptNW+usdFU2aEIkkr1ihbOyKw/cQKYhncnopQAT37KrQYuJAkxkx6gcVasWCOqboPg4vs7uSBWWqroKtYCqILwKb1UCpNxJUMJ+"
    "pqiE4HShoeJ0/CTh0eNgfGajnrEM5hR3kckM7+DzrRyofRcZrh0tdVTWhZXz972A3a6pig0llK5M56VMajs1BXEHCoiomr5Y/h2l"
    "6p7JzEWix6To4muKg1IWYDG/e5rvngKVCQI4xo8e4esHNSGyIyLCjxeXlJ2372ov6OfLkeF2ZG6RGVHOVwOj1AEl26q02WxUUlpO"
    "8Nt2Ybf/AbvfU5e+h5MGAAAAAElFTkSuQmCC"
)
_PROD_WINDOW_ICON_CACHE = None
_PROD_WINDOW_ICON_LOOKUP_DONE = False


def tool_window_icon():
    """Return the embedded project icon; no external asset path is required."""
    global _PROD_WINDOW_ICON_CACHE
    global _PROD_WINDOW_ICON_LOOKUP_DONE

    if _PROD_WINDOW_ICON_LOOKUP_DONE:
        return _PROD_WINDOW_ICON_CACHE

    _PROD_WINDOW_ICON_LOOKUP_DONE = True

    try:
        raw = base64.b64decode(
            PROD_WINDOW_ICON_PNG_BASE64
        )
        pixmap = QtGui.QPixmap()

        if not pixmap.loadFromData(
            raw,
            "PNG",
        ):
            log_line(
                "PROD_WINDOW_ICON status='embedded-load-failed'"
            )
            return None

        icon = QtGui.QIcon(
            pixmap
        )

        if icon.isNull():
            log_line(
                "PROD_WINDOW_ICON status='embedded-null'"
            )
            return None

        _PROD_WINDOW_ICON_CACHE = icon
        return _PROD_WINDOW_ICON_CACHE

    except Exception as exc:
        try:
            log_line(
                "PROD_WINDOW_ICON status='embedded-exception' error=%r"
                % exc
            )
        except Exception:
            pass
        return None



def tool_apply_window_icon(
    window,
):
    if window is None:
        return False

    try:
        icon = tool_window_icon()

        if icon is None:
            return False

        window.setWindowIcon(
            icon
        )
        return True

    except Exception as exc:
        try:
            log_line(
                "PROD_WINDOW_ICON status='apply-failed' error=%r"
                % exc
            )
        except Exception:
            pass
        return False



def tool_apply_visual_theme(
    window,
):
    tool_apply_window_icon(
        window
    )

    # Keep the dark SFM-aligned look and remove the bright tab-pane border
    # that makes text difficult to read.
    window.setStyleSheet(
        """
        QTabWidget::pane {
            border: 0px;
            background: #3a3a3a;
            margin-top: 0px;
        }
        QTabBar::tab {
            background: #3a3a3a;
            color: #d8d8d8;
            border: 1px solid #4a4a4a;
            border-bottom: 0px;
            padding: 4px 10px;
        }
        QTabBar::tab:selected {
            background: #3a3a3a;
        }
        QListWidget, QTextEdit {
            background: #2b2b2b;
            color: #d8d8d8;
            border: 1px solid #4a4a4a;
        }
        QLabel {
            background: transparent;
        }
        """
    )


def tool_remove_context_help(dialog):
    try:
        dialog.setWindowFlags(
            dialog.windowFlags()
            & ~QtCore.Qt.WindowContextHelpButtonHint
        )
    except Exception:
        pass


def tool_apply_dialog_font(
    dialog,
    point_delta=3,
):
    tool_remove_context_help(dialog)

    base = QtGui.QApplication.font()
    font = QtGui.QFont(base)

    if font.pointSize() > 0:
        font.setPointSize(
            font.pointSize()
            + point_delta
        )
    elif font.pixelSize() > 0:
        font.setPixelSize(
            font.pixelSize()
            + 4
        )

    dialog.setFont(font)

    for widget in dialog.findChildren(
        QtGui.QWidget
    ):
        widget.setFont(font)


def tool_apply_preset_list_style(
    widget,
):
    # Preset lists are single-column. Alternating bands compete with
    # the much more important selected-preset state, so keep one
    # uniform background and make selection unmistakable.
    widget.setAlternatingRowColors(
        False
    )
    widget.setStyleSheet(
        """
        QListWidget::item:selected {
            background-color: #2f76b5;
            color: #ffffff;
        }
        """
    )


def tool_apply_tab_style(
    tabs,
):
    tabs.setStyleSheet(
        """
        QTabWidget::pane {
            border: 1px solid #4a4a4a;
            top: -1px;
        }
        QTabBar::tab {
            background: #333333;
            border: 1px solid #4a4a4a;
            border-bottom: none;
            padding: 6px 14px;
            margin-right: 1px;
            min-width: 96px;
        }
        QTabBar::tab:selected {
            background: #454545;
            border-top: 2px solid #7c8f9c;
            border-bottom: 1px solid #454545;
        }
        """
    )


def tool_apply_main_action_button(
    button,
):
    # Main-window actions share one restrained neutral treatment.
    button.setAutoDefault(False)
    button.setDefault(False)
    button.setMinimumHeight(30)
    button.setStyleSheet(
        """
        QPushButton {
            background-color: #494949;
            border: 1px solid #5b5b5b;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #535353;
            border: 1px solid #666666;
        }
        QPushButton:pressed {
            background-color: #414141;
        }
        QPushButton:disabled {
            background-color: #393939;
            color: #858585;
            border: 1px solid #484848;
        }
        """
    )


def tool_apply_secondary_action_button(
    button,
):
    # Layout, rather than a second color family, carries hierarchy.
    tool_apply_main_action_button(
        button
    )


# Action colors mean the same thing everywhere in CPM: blue is the primary
# action, gold is Favorite, red is destructive. Every other action stays
# neutral. Layout establishes hierarchy; color only reinforces meaning, so
# semantic buttons keep the neutral fill and carry the role in the border.
# Disabled semantic buttons use the neutral disabled treatment so they never
# look available.
PROD_ACTION_BUTTON_PALETTES = {
    u"primary": {
        "background": "#494949",
        "border": "#4f7594",
        "color": "#d8d8d8",
        "hover": "#515151",
        "hover_border": "#5b88ad",
        "pressed": "#3e4247",
    },
    u"favorite": {
        "background": "#494949",
        "border": "#806d43",
        "color": "#d8d8d8",
        "hover": "#515151",
        "hover_border": "#947d4b",
        "pressed": "#45423c",
    },
    u"destructive": {
        "background": "#494949",
        "border": "#7a4d4d",
        "color": "#d8d8d8",
        "hover": "#515151",
        "hover_border": "#8d5959",
        "pressed": "#463e3e",
    },
}


def tool_apply_semantic_action_button(
    button,
    role,
):
    # Shares the neutral main-action sizing; unknown roles stay neutral.
    tool_apply_main_action_button(
        button
    )

    palette = PROD_ACTION_BUTTON_PALETTES.get(
        role
    )

    if palette is None:
        return

    button.setStyleSheet(
        """
        QPushButton {
            background-color: %(background)s;
            color: %(color)s;
            border: 1px solid %(border)s;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: %(hover)s;
            border: 1px solid %(hover_border)s;
        }
        QPushButton:pressed {
            background-color: %(pressed)s;
        }
        QPushButton:disabled {
            background-color: #393939;
            color: #858585;
            border: 1px solid #484848;
        }
        """
        % palette
    )


def tool_favorite_star_icon(
):
    # Favorite color belongs to the saved item being marked, not the action.
    size = 14
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    try:
        painter.setRenderHint(
            QtGui.QPainter.Antialiasing,
            True,
        )
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(
            QtGui.QColor(
                "#d6ad4b"
            )
        )

        points = []
        center = (size - 1) / 2.0
        outer = size * 0.43
        inner = outer * 0.45

        for index in range(10):
            radius = outer if (index % 2) == 0 else inner
            angle = (
                -math.pi / 2.0
                + index * math.pi / 5.0
            )
            points.append(
                QtCore.QPointF(
                    center + radius * math.cos(angle),
                    center + radius * math.sin(angle),
                )
            )

        painter.drawPolygon(
            QtGui.QPolygonF(points)
        )
    finally:
        painter.end()

    return QtGui.QIcon(
        pixmap
    )


def tool_apply_primary_button(
    button,
):
    # Reserved for single-terminal-action helper dialogs such as
    # Match Clothing. Main-window preset actions stay native gray.
    button.setAutoDefault(False)
    button.setDefault(False)
    button.setStyleSheet(
        """
        QPushButton {
            background-color: #2f76b5;
            color: #ffffff;
            border: 1px solid #4b8fc7;
            padding: 4px 10px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #377fbd;
        }
        QPushButton:pressed {
            background-color: #28679d;
        }
        QPushButton:disabled {
            background-color: #4a4a4a;
            color: #8d8d8d;
            border: 1px solid #555555;
            font-weight: normal;
        }
        """
    )


def tool_set_status(
    label,
    text,
    level=u"neutral",
):
    label.setText(
        u(text)
    )

    styles = {
        u"neutral": (
            "QLabel {"
            " background: #343434;"
            " color: #d8d8d8;"
            " border: 1px solid #4a4a4a;"
            " padding: 4px 6px;"
            "}"
        ),
        u"success": (
            "QLabel {"
            " background: #314338;"
            " color: #e0eee4;"
            " border: 1px solid #526d5a;"
            " padding: 4px 6px;"
            "}"
        ),
        u"warning": (
            "QLabel {"
            " background: #4a4130;"
            " color: #f0e6c8;"
            " border: 1px solid #746542;"
            " padding: 4px 6px;"
            "}"
        ),
        u"error": (
            "QLabel {"
            " background: #4b3232;"
            " color: #f0dddd;"
            " border: 1px solid #754a4a;"
            " padding: 4px 6px;"
            "}"
        ),
    }

    label.setStyleSheet(
        styles.get(
            u(level),
            styles[u"neutral"],
        )
    )



def tool_keep_modal_dialog_in_front(
    dialog,
):
    """
    Keep SFM modal prompts visible over the host while they are active.

    This does not make them modeless and does not permit background editing.
    """
    tool_apply_window_icon(
        dialog
    )

    try:
        dialog.setWindowFlags(
            dialog.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )
    except Exception:
        pass

    return dialog


def tool_warning_message(
    parent,
    title,
    message,
):
    box = QtGui.QMessageBox(
        parent
    )
    tool_keep_modal_dialog_in_front(
        box
    )

    try:
        box.setIcon(
            QtGui.QMessageBox.Warning
        )
        box.setWindowTitle(
            u(title)
        )
        box.setText(
            u(message)
        )
        box.addButton(
            QtGui.QMessageBox.Ok
        )
        tool_apply_dialog_font(
            box
        )
        box.exec_()

    finally:
        box.deleteLater()


def tool_model_relative_path(
    model_path,
):
    value = u(
        model_path
        or u""
    ).replace(
        u"\\",
        u"/",
    )

    if value.lower().startswith(
        u"models/"
    ):
        value = value[
            len(
                u"models/"
            ):
        ]

    return value


def tool_format_number(
    value,
):
    text_value = (
        "%.3f"
        % float(
            value
        )
    ).rstrip(
        "0"
    ).rstrip(
        "."
    )

    if text_value == "-0":
        text_value = "0"

    return text_value


def tool_format_saved_stamp(
    value,
):
    raw = u(
        value
        or u""
    )

    match = re.match(
        r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})",
        raw,
    )

    if match is None:
        return raw or u"Unknown"

    return u"%s-%s-%s %s:%s:%s" % (
        match.group(1),
        match.group(2),
        match.group(3),
        match.group(4),
        match.group(5),
        match.group(6),
    )


def tool_make_value_tree(
    parent,
    first_header,
):
    tree = QtGui.QTreeWidget(parent)
    tree.setColumnCount(2)
    tree.setHeaderLabels(
        [
            u(first_header),
            "Value",
        ]
    )
    tree.setRootIsDecorated(True)
    tree.setAlternatingRowColors(False)
    tree.header().setStretchLastSection(False)
    tree.header().setResizeMode(
        0,
        QtGui.QHeaderView.Stretch,
    )
    tree.header().setResizeMode(
        1,
        QtGui.QHeaderView.ResizeToContents,
    )
    return tree


def tool_add_banded_value_rows(root, rows):
    band = QtGui.QBrush(
        QtGui.QColor("#393939")
    )

    for index, row in enumerate(rows):
        item = QtGui.QTreeWidgetItem(
            [
                u(row[0]),
                u(row[1]),
            ]
        )

        if index % 2 == 1:
            item.setBackground(0, band)
            item.setBackground(1, band)

        root.addChild(item)


def tool_sfm_search_roots():
    try:
        import filesystem
        mod_value = u(filesystem.valve.mod())
    except Exception:
        return []

    if not mod_value:
        return []

    mod_path = os.path.abspath(mod_value)
    game_root = os.path.dirname(mod_path)
    roots = [mod_path]
    gameinfo = os.path.join(mod_path, "gameinfo.txt")

    if os.path.isfile(gameinfo):
        try:
            fp = open(gameinfo, "rb")
            try:
                raw = fp.read()
            finally:
                fp.close()

            try:
                content = raw.decode("utf-8")
            except Exception:
                content = raw.decode("latin-1")

            in_paths = False
            opened = False
            depth = 0

            for raw_line in content.splitlines():
                line = raw_line.split(u"//", 1)[0].strip()

                if not line:
                    continue

                if not in_paths:
                    if re.match(r'^"?SearchPaths"?\b', line, re.I):
                        in_paths = True
                    continue

                opens = line.count(u"{")
                closes = line.count(u"}")

                if opens:
                    opened = True
                    depth += opens

                if opened and depth > 0:
                    match = re.match(
                        r'^"?Game"?\s+(.+?)\s*$',
                        line,
                        re.I,
                    )

                    if match is not None:
                        value = match.group(1).strip().strip(u'"')
                        token = u"|gameinfo_path|"

                        if value.lower().startswith(token):
                            suffix = value[len(token):].lstrip(u"\\/")
                            root = (
                                os.path.join(mod_path, suffix)
                                if suffix
                                else mod_path
                            )
                        elif u"|" in value:
                            root = None
                        elif os.path.isabs(value):
                            root = value
                        else:
                            root = os.path.join(game_root, value)

                        if root:
                            roots.append(os.path.abspath(root))

                if closes:
                    depth -= closes
                    if opened and depth <= 0:
                        break
        except Exception:
            pass

    result = []
    seen = set()

    for root in roots:
        normalized = os.path.normcase(
            os.path.normpath(root)
        )
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(root)

    return result


def tool_resolve_model_file(model_path):
    relative = u(model_path or u"").replace(
        u"/",
        os.sep,
    ).replace(
        u"\\",
        os.sep,
    )

    for root in tool_sfm_search_roots():
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return None


def tool_open_folder(parent, folder, label):
    path = u(folder or u"")

    if not path or not os.path.isdir(path):
        tool_warning_message(
            parent,
            label,
            "This folder could not be found.",
        )
        return False

    try:
        os.startfile(path)
        return True
    except Exception:
        tool_warning_message(
            parent,
            label,
            "Windows Explorer could not open this folder.",
        )
        return False






CHARACTER_NIKA = u"nika"
CHARACTER_KRYSTAL = u"krystal2020"

KRYSTAL_PROFILE_ID = P04_PROFILE_ID
KRYSTAL_CHARACTER_FOLDER = P04_CHARACTER_FOLDER


def tool_detect_supported_character():
    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        raise RuntimeError(
            "No current shot."
        )

    matches = []

    for row in p01_model_backed_animsets(
        shot
    ):
        if (
            row[
                "model"
            ] == P01_MODEL_PATH
            and row[
                "checksum"
            ] == P01_MODEL_CHECKSUM
        ):
            matches.append(
                {
                    "kind": CHARACTER_NIKA,
                    "display_name": u"Nika Shark",
                    "profile_id": P02_PROFILE_ID,
                    "character_folder": P02_CHARACTER_FOLDER,
                    "shot": shot,
                    "row": row,
                }
            )

        elif (
            row[
                "model"
            ] == KRYSTAL_MODEL
            and row[
                "checksum"
            ] == KRYSTAL_CHECKSUM
        ):
            matches.append(
                {
                    "kind": CHARACTER_KRYSTAL,
                    "display_name": u"Krystal 2020",
                    "profile_id": KRYSTAL_PROFILE_ID,
                    "character_folder": KRYSTAL_CHARACTER_FOLDER,
                    "shot": shot,
                    "row": row,
                }
            )

    if len(
        matches
    ) != 1:
        raise RuntimeError(
            "The current shot must contain exactly one supported character "
            "(Nika Shark or Krystal 2020); found %d."
            % len(
                matches
            )
        )

    return matches[
        0
    ]


def tool_paths_for_context(
    context,
):
    root = os.path.join(
        p02_documents(),
        P02_LIBRARY_DIRNAME,
    )
    character_root = os.path.join(
        root,
        u"Characters",
        context[
            "character_folder"
        ],
    )

    return {
        "root": root,
        "character_root": character_root,
        "profile": os.path.join(
            character_root,
            u"character.json",
        ),
        "body_dir": os.path.join(
            character_root,
            P03_BODY_FOLDER,
        ),
        "expression_dir": os.path.join(
            character_root,
            P03_EXPRESSION_FOLDER,
        ),
        "trash": os.path.join(
            root,
            P03_TRASH_DIRNAME,
        ),
        "exports": os.path.join(
            root,
            P03_EXPORT_DIRNAME,
        ),
    }


def tool_validate_preset_for_context(
    context,
    record,
    expected_kind=None,
):
    if not isinstance(
        record,
        dict,
    ):
        raise RuntimeError(
            "Preset is not a JSON object."
        )

    if record.get(
        "schema_version"
    ) != P02_SCHEMA_VERSION:
        raise RuntimeError(
            "Preset schema is unsupported."
        )

    if record.get(
        "profile_id"
    ) != context[
        "profile_id"
    ]:
        raise RuntimeError(
            "Preset belongs to another Character profile."
        )

    kind = u(
        record.get(
            "kind"
        )
    )

    if kind not in (
        P03_KIND_BODY,
        P03_KIND_EXPRESSION,
    ):
        raise RuntimeError(
            "Preset kind is unsupported."
        )

    if (
        expected_kind is not None
        and kind != expected_kind
    ):
        raise RuntimeError(
            "Preset kind does not match the requested library."
        )

    if (
        context[
            "kind"
        ] == CHARACTER_KRYSTAL
        and kind != P03_KIND_BODY
    ):
        raise RuntimeError(
            "Krystal Expressions are not yet a qualified production capability."
        )

    preset_id = u(
        record.get(
            "preset_id"
        )
    )

    if not preset_id:
        raise RuntimeError(
            "Preset has no stable preset_id."
        )

    if not isinstance(
        record.get(
            "values"
        ),
        dict,
    ):
        raise RuntimeError(
            "Preset values are missing or malformed."
        )

    return True


def tool_profile_for_context(
    context,
    required=True,
):
    path = tool_paths_for_context(
        context
    )[
        "profile"
    ]

    if not os.path.isfile(
        path
    ):
        if required:
            raise RuntimeError(
                "%s profile has not been initialized."
                % context[
                    "display_name"
                ]
            )
        return None

    profile = p02_read_json(
        path
    )

    if profile.get(
        "schema_version"
    ) != P02_SCHEMA_VERSION:
        raise RuntimeError(
            "Character profile schema is unsupported."
        )

    if profile.get(
        "profile_id"
    ) != context[
        "profile_id"
    ]:
        raise RuntimeError(
            "Character profile identity does not match the current character."
        )

    return profile


def tool_discover_presets_for_context(
    context,
    kind,
):
    if (
        context[
            "kind"
        ] == CHARACTER_KRYSTAL
        and kind == P03_KIND_EXPRESSION
    ):
        return []

    paths = tool_paths_for_context(
        context
    )

    folder = (
        paths[
            "body_dir"
        ]
        if kind == P03_KIND_BODY
        else paths[
            "expression_dir"
        ]
    )

    profile = tool_profile_for_context(
        context,
        required=False,
    )

    result = []

    for path in p03_json_candidates(
        folder
    ):
        try:
            record = p02_read_json(
                path
            )
            tool_validate_preset_for_context(
                context,
                record,
                kind,
            )

            if (
                context[
                    "kind"
                ] == CHARACTER_KRYSTAL
            ):
                if profile is None:
                    raise RuntimeError(
                        "Krystal profile is unavailable."
                    )

                p04_validate_disk(
                    profile,
                    record,
                )

        except Exception as exc:
            log_line(
                "TOOL_LIBRARY_SKIP character=%r path=%r error=%r"
                % (
                    context[
                        "kind"
                    ],
                    path,
                    exc,
                )
            )
            continue

        result.append(
            {
                "path": path,
                "record": record,
            }
        )

    result.sort(
        key=lambda item: (
            u(
                item[
                    "record"
                ].get(
                    "name"
                )
            ).lower(),
            u(
                item[
                    "record"
                ].get(
                    "preset_id"
                )
            ),
        )
    )

    return result


def tool_unique_path_for_context(
    context,
    kind,
    display_name,
    preset_id,
):
    paths = tool_paths_for_context(
        context
    )

    folder = (
        paths[
            "body_dir"
        ]
        if kind == P03_KIND_BODY
        else paths[
            "expression_dir"
        ]
    )

    p02_ensure_dir(
        folder
    )

    safe_name = u(
        display_name
    )

    for ch in u'<>:"/\\|?*':
        safe_name = safe_name.replace(
            ch,
            u"_",
        )

    safe_name = safe_name.strip()

    if not safe_name:
        safe_name = u"Preset"

    suffix = u(
        preset_id
    )[:12]

    candidate = os.path.join(
        folder,
        safe_name
        + u"--"
        + suffix
        + u".json",
    )

    if not os.path.exists(
        candidate
    ):
        return candidate

    counter = 2

    while counter < 1000:
        candidate = os.path.join(
            folder,
            safe_name
            + u"--"
            + suffix
            + u"-"
            + unicode(
                counter
            )
            + u".json",
        )

        if not os.path.exists(
            candidate
        ):
            return candidate

        counter += 1

    raise RuntimeError(
        "Could not allocate a collision-free preset filename."
    )


def tool_find_preset_for_context(
    context,
    kind,
    preset_id,
):
    for item in tool_discover_presets_for_context(
        context,
        kind,
    ):
        if u(
            item[
                "record"
            ].get(
                "preset_id"
            )
        ) == u(
            preset_id
        ):
            return item

    return None


def tool_duplicate_for_context(
    context,
    source_path,
):
    record = p02_read_json(
        source_path
    )
    tool_validate_preset_for_context(
        context,
        record,
    )

    duplicate = json.loads(
        json.dumps(
            record
        )
    )

    new_id = (
        u"copy-"
        + unicode(
            uuid.uuid4().hex
        )
    )

    duplicate[
        "preset_id"
    ] = new_id
    duplicate[
        "name"
    ] = (
        u(
            record.get(
                "name"
            )
        )
        + u" Copy"
    )

    target = tool_unique_path_for_context(
        context,
        u(
            duplicate[
                "kind"
            ]
        ),
        u(
            duplicate[
                "name"
            ]
        ),
        new_id,
    )

    p02_safe_write_json(
        target,
        duplicate,
    )

    return target, duplicate


def tool_rename_for_context(
    context,
    path,
    new_name,
):
    record = p02_read_json(
        path
    )
    tool_validate_preset_for_context(
        context,
        record,
    )

    record[
        "name"
    ] = u(
        new_name
    )

    p02_safe_write_json(
        path,
        record,
    )

    return record


def tool_set_default_body_for_context(
    context,
    preset_id,
):
    profile = tool_profile_for_context(
        context,
        required=True,
    )

    if preset_id is not None:
        item = tool_find_preset_for_context(
            context,
            P03_KIND_BODY,
            preset_id,
        )

        if item is None:
            raise RuntimeError(
                "Default Body Preset does not exist."
            )

    previous = profile.get(
        "default_body_preset_id"
    )

    profile[
        "default_body_preset_id"
    ] = preset_id

    p02_safe_write_json(
        tool_paths_for_context(
            context
        )[
            "profile"
        ],
        profile,
    )

    return previous


def tool_move_to_trash_for_context(
    context,
    path,
):
    record = p02_read_json(
        path
    )
    tool_validate_preset_for_context(
        context,
        record,
    )

    paths = tool_paths_for_context(
        context
    )

    p02_ensure_dir(
        paths[
            "trash"
        ]
    )

    basename = os.path.basename(
        path
    )

    target = os.path.join(
        paths[
            "trash"
        ],
        p03_now_stamp()
        + u"--"
        + basename,
    )

    result = ctypes.windll.kernel32.MoveFileExW(
        ctypes.c_wchar_p(
            path
        ),
        ctypes.c_wchar_p(
            target
        ),
        0,
    )

    if not result:
        code = ctypes.windll.kernel32.GetLastError()
        raise RuntimeError(
            "Could not move preset to Trash (Windows error %d)."
            % code
        )

    if record[
        "kind"
    ] == P03_KIND_BODY:
        profile = tool_profile_for_context(
            context,
            required=False,
        )

        if (
            profile is not None
            and profile.get(
                "default_body_preset_id"
            )
            == record[
                "preset_id"
            ]
        ):
            profile[
                "default_body_preset_id"
            ] = None

            p02_safe_write_json(
                paths[
                    "profile"
                ],
                profile,
            )

    return target, record


def tool_export_for_context(
    context,
    source_path,
    target_path,
):
    record = p02_read_json(
        source_path
    )
    tool_validate_preset_for_context(
        context,
        record,
    )

    p02_ensure_dir(
        os.path.dirname(
            target_path
        )
    )

    if os.path.exists(
        target_path
    ):
        os.remove(
            target_path
        )

    shutil.copy2(
        source_path,
        target_path,
    )

    exported = p02_read_json(
        target_path
    )

    if exported != record:
        raise RuntimeError(
            "Exported preset did not validate against the source."
        )

    return target_path


def tool_import_for_context(
    parent,
    context,
):
    result = QtGui.QFileDialog.getOpenFileName(
        parent,
        "Import Preset",
        u"",
        "JSON files (*.json);;All files (*)",
    )

    source = tool_dialog_path(
        result
    )

    if not source:
        return None

    record = p02_read_json(
        source
    )
    tool_validate_preset_for_context(
        context,
        record,
    )

    if (
        context[
            "kind"
        ] == CHARACTER_KRYSTAL
    ):
        profile = tool_profile_for_context(
            context,
            required=True,
        )
        p04_validate_disk(
            profile,
            record,
        )

    imported = json.loads(
        json.dumps(
            record
        )
    )

    imported[
        "preset_id"
    ] = (
        u"import-"
        + unicode(
            uuid.uuid4().hex
        )
    )
    imported[
        "name"
    ] = (
        u(
            record.get(
                "name"
            )
        )
        + u" Imported"
    )

    target = tool_unique_path_for_context(
        context,
        u(
            imported[
                "kind"
            ]
        ),
        u(
            imported[
                "name"
            ]
        ),
        u(
            imported[
                "preset_id"
            ]
        ),
    )

    p02_safe_write_json(
        target,
        imported,
    )

    return target, imported


def tool_krystal_profile_semantics_equal(
    existing,
    generated,
):
    for key in (
        "models",
        "controls",
        "scale_contracts",
        "semantic_provenance",
    ):
        if existing.get(
            key
        ) != generated.get(
            key
        ):
            return False

    return True


def tool_save_krystal_body_named(
    display_name,
):
    shot = current_shot()
    krystal = unique_krystal(
        shot
    )

    head_time = float(
        sfmApp.GetHeadTimeInSeconds()
    )

    same_time_refresh(
        head_time,
        "TOOL_KRYSTAL_CAPTURE",
    )

    shot = current_shot()
    krystal = unique_krystal(
        shot
    )

    flex_bindings = body_flex_bindings(
        krystal[
            "animset"
        ]
    )

    try:
        scale_binding = resolve_qualified_head_scale(
            krystal[
                "animset"
            ],
            shot,
            krystal[
                "gm"
            ],
        )
    except Exception as exc:
        raise RuntimeError(
            "A complete Krystal Body Preset requires the qualified Head Scale "
            "capability on the source character. Nothing was saved. Detail: %r"
            % exc
        )

    probe, encoded, nonzero = plain_body_preset(
        krystal,
        flex_bindings,
        scale_binding,
    )

    generated_profile, generated_preset, multiplier = p04_build_records(
        krystal,
        probe,
    )

    context = tool_detect_supported_character()

    if context[
        "kind"
    ] != CHARACTER_KRYSTAL:
        raise RuntimeError(
            "The current character changed during Save."
        )

    paths = tool_paths_for_context(
        context
    )

    existing_profile = tool_profile_for_context(
        context,
        required=False,
    )

    if existing_profile is not None:
        if not tool_krystal_profile_semantics_equal(
            existing_profile,
            generated_profile,
        ):
            raise RuntimeError(
                "The existing Krystal profile differs from the qualified Head Scale/"
                "Body Morph contract. Review it before saving another preset."
            )

        generated_profile[
            "default_body_preset_id"
        ] = existing_profile.get(
            "default_body_preset_id"
        )

    preset_id = (
        u"body-"
        + unicode(
            uuid.uuid4().hex
        )
    )

    generated_preset[
        "preset_id"
    ] = preset_id
    generated_preset[
        "name"
    ] = u(
        display_name
    )

    if existing_profile is None:
        p02_safe_write_json(
            paths[
                "profile"
            ],
            generated_profile,
        )

    target = tool_unique_path_for_context(
        context,
        P03_KIND_BODY,
        u(
            display_name
        ),
        preset_id,
    )

    p02_safe_write_json(
        target,
        generated_preset,
    )

    disk_profile = tool_profile_for_context(
        context,
        required=True,
    )
    disk_preset = p02_read_json(
        target
    )

    p04_validate_disk(
        disk_profile,
        disk_preset,
    )

    log_line(
        "TOOL_SAVE_KRYSTAL_BODY=PASS name=%r body_morphs=%d "
        "head_scale_multiplier=%r path=%r"
        % (
            display_name,
            len(
                probe[
                    "flexes"
                ]
            ),
            multiplier,
            target,
        )
    )

    return target


def tool_apply_krystal_body(
    path,
):
    context = tool_detect_supported_character()

    if context[
        "kind"
    ] != CHARACTER_KRYSTAL:
        raise RuntimeError(
            "The selected Krystal Body Preset cannot be applied to this character."
        )

    profile = tool_profile_for_context(
        context,
        required=True,
    )
    preset = p02_read_json(
        path
    )

    tool_validate_preset_for_context(
        context,
        preset,
        P03_KIND_BODY,
    )

    p04_validate_disk(
        profile,
        preset,
    )

    probe = p04_disk_to_probe(
        profile,
        preset,
    )

    shot = current_shot()
    target = unique_krystal(
        shot
    )

    result = p04_apply_once(
        target,
        shot,
        probe,
    )

    log_line(
        "TOOL_APPLY_KRYSTAL_BODY outcome=%r preset=%r"
        % (
            result[
                "outcome"
            ],
            preset.get(
                "name"
            ),
        )
    )

    return result


def tool_export_selected_for_context(
    parent,
    context,
    source_path,
):
    record = p02_read_json(
        source_path
    )
    tool_validate_preset_for_context(
        context,
        record,
    )

    suggested = (
        u(
            record.get(
                "name"
            )
        )
        + u".json"
    )

    result = QtGui.QFileDialog.getSaveFileName(
        parent,
        "Export Preset",
        suggested,
        "JSON files (*.json);;All files (*)",
    )

    target = tool_dialog_path(
        result
    )

    if not target:
        return None

    if not target.lower().endswith(
        u".json"
    ):
        target += u".json"

    return tool_export_for_context(
        context,
        source_path,
        target,
    )


class UnifiedDetailsDialog(QtGui.QDialog):

    def __init__(
        self,
        context,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )

        self.context = context

        self.setWindowTitle(
            "Character Preset Details"
        )
        self.setModal(
            True
        )
        self.resize(
            700,
            500,
        )

        layout = QtGui.QVBoxLayout(
            self
        )

        self.text = QtGui.QTextEdit()
        self.text.setReadOnly(
            True
        )
        layout.addWidget(
            self.text,
            1,
        )

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Close
        )
        buttons.rejected.connect(
            self.reject
        )
        layout.addWidget(
            buttons
        )

        self.refresh()

    def refresh(self):
        try:
            context = tool_detect_supported_character()

            if context[
                "kind"
            ] == CHARACTER_NIKA:
                scope = p02_complete_scope()
                profile = tool_ensure_profile(
                    scope
                )
                body = p03_body_scope(
                    scope
                )

                descriptor = scope[
                    "provider_descriptor"
                ]
                counts = scope[
                    "scope"
                ][
                    "counts"
                ]

                lines = [
                    u"Tool: %s %s"
                    % (
                        TOOL_NAME,
                        TOOL_VERSION,
                    ),
                    u"",
                    u"Character: Nika Shark",
                    u"Model: %s"
                    % P01_MODEL_PATH,
                    u"Checksum: %s"
                    % P01_MODEL_CHECKSUM,
                    u"",
                    u"Expression controls: %d"
                    % counts[
                        "resolved_face"
                    ],
                    u"Body Morph controls: %d"
                    % len(
                        body[
                            "accepted"
                        ]
                    ),
                    u"",
                    u"Semantic provider: %s"
                    % descriptor[
                        "provider_kind"
                    ],
                    u"Master SHA-256: %s"
                    % descriptor[
                        "source_sha256"
                    ],
                    u"",
                    u"Default Body Preset ID: %s"
                    % (
                        profile.get(
                            "default_body_preset_id"
                        )
                        or u"(none)"
                    ),
                ]

            else:
                profile = tool_profile_for_context(
                    context,
                    required=False,
                )
                shot = current_shot()
                target = unique_krystal(
                    shot
                )
                scale_probe = p04_scale_topology_probe(
                    target,
                    shot,
                )

                lines = [
                    u"Tool: %s %s"
                    % (
                        TOOL_NAME,
                        TOOL_VERSION,
                    ),
                    u"",
                    u"Character: Krystal 2020",
                    u"Model: %s"
                    % KRYSTAL_MODEL,
                    u"Checksum: %s"
                    % KRYSTAL_CHECKSUM,
                    u"",
                    u"Body Morph controls: %d"
                    % len(
                        body_flex_bindings(
                            target[
                                "animset"
                            ]
                        )
                    ),
                    u"Head Scale capability: %s"
                    % scale_probe[
                        "kind"
                    ],
                    u"Head Scale policy: required Body Preset component",
                    u"Portable scale value: physical scale_multiplier",
                    u"",
                    u"Expressions: not yet qualified for this profile",
                    u"Match Clothing: not yet qualified for this profile",
                    u"",
                    u"Default Body Preset ID: %s"
                    % (
                        (
                            profile.get(
                                "default_body_preset_id"
                            )
                            if profile is not None
                            else None
                        )
                        or u"(none)"
                    ),
                ]

            self.text.setPlainText(
                u"\n".join(
                    lines
                )
            )

        except Exception as exc:
            self.text.setPlainText(
                u"Details could not be resolved:\n\n%s"
                % u(
                    exc
                )
            )


class CharacterPresetWindow(QtGui.QDialog):

    def __init__(
        self,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )

        self.setWindowTitle(
            TOOL_NAME
        )
        self.setModal(
            False
        )
        self.resize(
            760,
            530,
        )

        self.busy = False
        self.current_context = None

        outer = QtGui.QVBoxLayout(
            self
        )

        header = QtGui.QHBoxLayout()

        self.character_label = QtGui.QLabel(
            "<b>Character:</b> resolving..."
        )
        header.addWidget(
            self.character_label
        )
        header.addStretch(
            1
        )

        self.refresh_button = QtGui.QPushButton(
            "Refresh"
        )
        self.refresh_button.clicked.connect(
            self.refresh_all
        )
        header.addWidget(
            self.refresh_button
        )

        outer.addLayout(
            header
        )

        self.status = QtGui.QLabel(
            ""
        )
        self.status.setWordWrap(
            True
        )
        outer.addWidget(
            self.status
        )

        self.tabs = QtGui.QTabWidget()
        outer.addWidget(
            self.tabs,
            1,
        )

        self._build_body_tab()
        self._build_expression_tab()
        self.tabs.setDocumentMode(
            True
        )
        tool_apply_visual_theme(
            self
        )

        footer = QtGui.QHBoxLayout()

        self.match_button = QtGui.QPushButton(
            "Match Clothing..."
        )
        self.match_button.clicked.connect(
            self.open_match
        )
        footer.addWidget(
            self.match_button
        )

        footer.addStretch(
            1
        )

        self.details_button = QtGui.QPushButton(
            "Details..."
        )
        self.details_button.clicked.connect(
            self.open_details
        )
        footer.addWidget(
            self.details_button
        )

        outer.addLayout(
            footer
        )

        self.refresh_all()

    def _build_body_tab(self):
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(
            widget
        )

        self.body_list = QtGui.QListWidget()
        layout.addWidget(
            self.body_list,
            1,
        )

        row1 = QtGui.QHBoxLayout()

        self.save_body_button = QtGui.QPushButton(
            "Save Current Body..."
        )
        self.save_body_button.clicked.connect(
            self.save_body
        )
        row1.addWidget(
            self.save_body_button
        )

        self.apply_body_button = QtGui.QPushButton(
            "Apply"
        )
        self.apply_body_button.clicked.connect(
            self.apply_body
        )
        row1.addWidget(
            self.apply_body_button
        )

        self.default_body_button = QtGui.QPushButton(
            "Set Default"
        )
        self.default_body_button.clicked.connect(
            self.set_default_body
        )
        row1.addWidget(
            self.default_body_button
        )

        layout.addLayout(
            row1
        )

        row2 = QtGui.QHBoxLayout()

        for label, handler in (
            (
                "Duplicate",
                self.duplicate_body,
            ),
            (
                "Rename...",
                self.rename_body,
            ),
            (
                "Delete",
                self.delete_body,
            ),
            (
                "Export...",
                self.export_body,
            ),
            (
                "Import...",
                self.import_any,
            ),
        ):
            button = QtGui.QPushButton(
                label
            )
            button.clicked.connect(
                handler
            )
            row2.addWidget(
                button
            )

        layout.addLayout(
            row2
        )

        self.tabs.addTab(
            widget,
            "Body Presets",
        )

    def _build_expression_tab(self):
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(
            widget
        )

        note = QtGui.QLabel(
            "Saves facial controls, including face shape."
        )
        note.setWordWrap(
            True
        )
        layout.addWidget(
            note
        )

        self.expression_list = QtGui.QListWidget()
        layout.addWidget(
            self.expression_list,
            1,
        )

        row1 = QtGui.QHBoxLayout()

        self.save_expression_button = QtGui.QPushButton(
            "Save Current Expression..."
        )
        self.save_expression_button.clicked.connect(
            self.save_expression
        )
        row1.addWidget(
            self.save_expression_button
        )

        self.apply_expression_button = QtGui.QPushButton(
            "Apply"
        )
        self.apply_expression_button.clicked.connect(
            self.apply_expression
        )
        row1.addWidget(
            self.apply_expression_button
        )

        layout.addLayout(
            row1
        )

        row2 = QtGui.QHBoxLayout()

        for label, handler in (
            (
                "Duplicate",
                self.duplicate_expression,
            ),
            (
                "Rename...",
                self.rename_expression,
            ),
            (
                "Delete",
                self.delete_expression,
            ),
            (
                "Export...",
                self.export_expression,
            ),
            (
                "Import...",
                self.import_any,
            ),
        ):
            button = QtGui.QPushButton(
                label
            )
            button.clicked.connect(
                handler
            )
            row2.addWidget(
                button
            )

        layout.addLayout(
            row2
        )

        self.tabs.addTab(
            widget,
            "Expressions",
        )

    def guarded(
        self,
        label,
        func,
    ):
        if self.busy:
            return None

        self.busy = True

        try:
            return func()

        except Exception as exc:
            log_line(
                "TOOL_ACTION_ERROR label=%r error=%r"
                % (
                    label,
                    exc,
                )
            )
            log_line(
                traceback.format_exc()
            )

            self.status.setText(
                "%s could not complete."
                % label
            )

            try:
                QtGui.QMessageBox.warning(
                    self,
                    "%s could not complete"
                    % label,
                    u(
                        exc
                    ),
                )
            except Exception:
                pass

            return None

        finally:
            self.busy = False

    def require_current_context(self):
        context = tool_detect_supported_character()

        if (
            self.current_context is not None
            and context[
                "kind"
            ] != self.current_context[
                "kind"
            ]
        ):
            self.current_context = context
            self.refresh_body_list()
            self.refresh_expression_list()
            self.update_capabilities()

            raise RuntimeError(
                "The current character changed. The library was refreshed; select a preset again."
            )

        self.current_context = context
        return context

    def update_capabilities(self):
        if self.current_context is None:
            return

        is_nika = (
            self.current_context[
                "kind"
            ]
            == CHARACTER_NIKA
        )

        self.tabs.setTabEnabled(
            1,
            is_nika,
        )
        self.match_button.setEnabled(
            is_nika,
        )

        if not is_nika:
            self.expression_list.clear()

    def refresh_all(self):
        def work():
            context = tool_detect_supported_character()
            self.current_context = context

            if context[
                "kind"
            ] == CHARACTER_NIKA:
                scope = p02_complete_scope()
                tool_ensure_profile(
                    scope
                )

            self.character_label.setText(
                u"<b>Character:</b> %s"
                % context[
                    "display_name"
                ]
            )

            self.update_capabilities()
            self.refresh_body_list()
            self.refresh_expression_list()

            self.status.setText(
                u"Ready - %s"
                % u(
                    context[
                        "row"
                    ][
                        "animset_name"
                    ]
                )
            )

            log_line(
                "TOOL_REFRESH=PASS character=%r shot=%r animset=%r"
                % (
                    context[
                        "kind"
                    ],
                    name(
                        context[
                            "shot"
                        ]
                    ),
                    context[
                        "row"
                    ][
                        "animset_name"
                    ],
                )
            )

        return self.guarded(
            "Refresh",
            work,
        )

    def refresh_body_list(self):
        self.body_list.clear()

        if self.current_context is None:
            return

        profile = tool_profile_for_context(
            self.current_context,
            required=False,
        )

        default_id = (
            profile.get(
                "default_body_preset_id"
            )
            if profile is not None
            else None
        )

        for item in tool_discover_presets_for_context(
            self.current_context,
            P03_KIND_BODY,
        ):
            record = item[
                "record"
            ]

            title = u(
                record.get(
                    "name"
                )
            )

            if (
                default_id
                and record[
                    "preset_id"
                ] == default_id
            ):
                title += u" [Default]"

            widget_item = QtGui.QListWidgetItem(
                title
            )
            widget_item.setData(
                QtCore.Qt.UserRole,
                item[
                    "path"
                ],
            )
            self.body_list.addItem(
                widget_item
            )

    def refresh_expression_list(self):
        self.expression_list.clear()

        if (
            self.current_context is None
            or self.current_context[
                "kind"
            ] != CHARACTER_NIKA
        ):
            return

        for item in tool_discover_presets_for_context(
            self.current_context,
            P03_KIND_EXPRESSION,
        ):
            widget_item = QtGui.QListWidgetItem(
                u(
                    item[
                        "record"
                    ].get(
                        "name"
                    )
                )
            )
            widget_item.setData(
                QtCore.Qt.UserRole,
                item[
                    "path"
                ],
            )
            self.expression_list.addItem(
                widget_item
            )

    def selected_path(
        self,
        widget,
    ):
        return tool_item_path(
            widget
        )

    def save_body(self):
        def work():
            context = self.require_current_context()

            name_value = tool_prompt_name(
                self,
                "Save Current Body",
                "Preset name:",
                u"Body",
            )

            if name_value is None:
                return

            if context[
                "kind"
            ] == CHARACTER_NIKA:
                path = tool_save_body_named(
                    name_value
                )
            else:
                path = tool_save_krystal_body_named(
                    name_value
                )

            self.refresh_body_list()

            index = tool_find_list_item_by_path(
                self.body_list,
                path,
            )

            if index >= 0:
                self.body_list.setCurrentRow(
                    index
                )

            self.status.setText(
                "Body Preset saved."
            )

        return self.guarded(
            "Save Current Body",
            work,
        )

    def apply_body(self):
        def work():
            context = self.require_current_context()

            path = self.selected_path(
                self.body_list
            )

            if context[
                "kind"
            ] == CHARACTER_NIKA:
                result = p03_apply_preset(
                    path,
                    P03_KIND_BODY,
                )
            else:
                result = tool_apply_krystal_body(
                    path
                )

            outcome = result[
                "outcome"
            ]

            if outcome == "no-op":
                self.status.setText(
                    "Body already matches this preset; nothing changed."
                )

            elif outcome == "committed-unverified":
                self.status.setText(
                    "Body Preset was committed, but verification failed. Use SFM Undo."
                )
                QtGui.QMessageBox.warning(
                    self,
                    "Body Preset committed but could not be verified",
                    "The change was committed. Use SFM Undo if the result is not correct.",
                )

            else:
                self.status.setText(
                    "Body Preset applied."
                )

        return self.guarded(
            "Apply Body Preset",
            work,
        )

    def save_expression(self):
        def work():
            context = self.require_current_context()

            if context[
                "kind"
            ] != CHARACTER_NIKA:
                raise RuntimeError(
                    "Expressions are not yet a qualified production capability for Krystal 2020."
                )

            name_value = tool_prompt_name(
                self,
                "Save Current Expression",
                "Preset name:",
                u"Expression",
            )

            if name_value is None:
                return

            path = tool_save_expression_named(
                name_value
            )

            self.refresh_expression_list()

            index = tool_find_list_item_by_path(
                self.expression_list,
                path,
            )

            if index >= 0:
                self.expression_list.setCurrentRow(
                    index
                )

            self.status.setText(
                "Expression saved."
            )

        return self.guarded(
            "Save Current Expression",
            work,
        )

    def apply_expression(self):
        def work():
            context = self.require_current_context()

            if context[
                "kind"
            ] != CHARACTER_NIKA:
                raise RuntimeError(
                    "Expressions are not yet a qualified production capability for Krystal 2020."
                )

            path = self.selected_path(
                self.expression_list
            )

            result = p03_apply_preset(
                path,
                P03_KIND_EXPRESSION,
            )

            if result[
                "outcome"
            ] == "no-op":
                self.status.setText(
                    "Expression already matches this preset; nothing changed."
                )
            else:
                self.status.setText(
                    "Expression applied."
                )

        return self.guarded(
            "Apply Expression",
            work,
        )

    def duplicate_selected(
        self,
        widget,
    ):
        context = self.require_current_context()

        path = self.selected_path(
            widget
        )

        new_path, record = tool_duplicate_for_context(
            context,
            path,
        )

        return new_path

    def duplicate_body(self):
        def work():
            path = self.duplicate_selected(
                self.body_list
            )
            self.refresh_body_list()

            index = tool_find_list_item_by_path(
                self.body_list,
                path,
            )

            if index >= 0:
                self.body_list.setCurrentRow(
                    index
                )

            self.status.setText(
                "Body Preset duplicated."
            )

        return self.guarded(
            "Duplicate Body Preset",
            work,
        )

    def duplicate_expression(self):
        def work():
            path = self.duplicate_selected(
                self.expression_list
            )
            self.refresh_expression_list()

            index = tool_find_list_item_by_path(
                self.expression_list,
                path,
            )

            if index >= 0:
                self.expression_list.setCurrentRow(
                    index
                )

            self.status.setText(
                "Expression duplicated."
            )

        return self.guarded(
            "Duplicate Expression",
            work,
        )

    def rename_selected(
        self,
        widget,
        refresh_func,
    ):
        context = self.require_current_context()
        path = self.selected_path(
            widget
        )

        record = p02_read_json(
            path
        )
        tool_validate_preset_for_context(
            context,
            record,
        )

        name_value = tool_prompt_name(
            self,
            "Rename Preset",
            "Name:",
            u(
                record.get(
                    "name"
                )
            ),
        )

        if name_value is None:
            return None

        tool_rename_for_context(
            context,
            path,
            name_value,
        )

        refresh_func()
        return path

    def rename_body(self):
        def work():
            if self.rename_selected(
                self.body_list,
                self.refresh_body_list,
            ):
                self.status.setText(
                    "Body Preset renamed."
                )

        return self.guarded(
            "Rename Body Preset",
            work,
        )

    def rename_expression(self):
        def work():
            if self.rename_selected(
                self.expression_list,
                self.refresh_expression_list,
            ):
                self.status.setText(
                    "Expression renamed."
                )

        return self.guarded(
            "Rename Expression",
            work,
        )

    def delete_selected(
        self,
        widget,
        refresh_func,
    ):
        context = self.require_current_context()
        path = self.selected_path(
            widget
        )

        record = p02_read_json(
            path
        )
        tool_validate_preset_for_context(
            context,
            record,
        )

        answer = QtGui.QMessageBox.question(
            self,
            "Delete Preset",
            u"Move '%s' to Trash?"
            % u(
                record.get(
                    "name"
                )
            ),
            QtGui.QMessageBox.Yes
            | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No,
        )

        if answer != QtGui.QMessageBox.Yes:
            return False

        tool_move_to_trash_for_context(
            context,
            path,
        )

        refresh_func()
        return True

    def delete_body(self):
        def work():
            if self.delete_selected(
                self.body_list,
                self.refresh_body_list,
            ):
                self.status.setText(
                    "Body Preset moved to Trash."
                )

        return self.guarded(
            "Delete Body Preset",
            work,
        )

    def delete_expression(self):
        def work():
            if self.delete_selected(
                self.expression_list,
                self.refresh_expression_list,
            ):
                self.status.setText(
                    "Expression moved to Trash."
                )

        return self.guarded(
            "Delete Expression",
            work,
        )

    def set_default_body(self):
        def work():
            context = self.require_current_context()
            path = self.selected_path(
                self.body_list
            )

            record = p02_read_json(
                path
            )
            tool_validate_preset_for_context(
                context,
                record,
                P03_KIND_BODY,
            )

            tool_set_default_body_for_context(
                context,
                record[
                    "preset_id"
                ],
            )

            self.refresh_body_list()
            self.status.setText(
                "Default Body Preset updated."
            )

        return self.guarded(
            "Set Default Body Preset",
            work,
        )

    def export_selected(
        self,
        widget,
    ):
        context = self.require_current_context()
        path = self.selected_path(
            widget
        )

        return tool_export_selected_for_context(
            self,
            context,
            path,
        )

    def export_body(self):
        def work():
            if self.export_selected(
                self.body_list
            ):
                self.status.setText(
                    "Body Preset exported."
                )

        return self.guarded(
            "Export Body Preset",
            work,
        )

    def export_expression(self):
        def work():
            if self.export_selected(
                self.expression_list
            ):
                self.status.setText(
                    "Expression exported."
                )

        return self.guarded(
            "Export Expression",
            work,
        )

    def import_any(self):
        def work():
            context = self.require_current_context()

            imported = tool_import_for_context(
                self,
                context,
            )

            if imported is None:
                return

            path, record = imported

            self.refresh_body_list()
            self.refresh_expression_list()

            if record[
                "kind"
            ] == P03_KIND_BODY:
                index = tool_find_list_item_by_path(
                    self.body_list,
                    path,
                )

                if index >= 0:
                    self.body_list.setCurrentRow(
                        index
                    )

                self.tabs.setCurrentIndex(
                    0
                )

            else:
                index = tool_find_list_item_by_path(
                    self.expression_list,
                    path,
                )

                if index >= 0:
                    self.expression_list.setCurrentRow(
                        index
                    )

                self.tabs.setCurrentIndex(
                    1
                )

            self.status.setText(
                "Preset imported as a new copy."
            )

        return self.guarded(
            "Import Preset",
            work,
        )

    def open_match(self):
        def work():
            context = self.require_current_context()

            if context[
                "kind"
            ] != CHARACTER_NIKA:
                raise RuntimeError(
                    "Match Clothing is not yet a qualified production capability for Krystal 2020."
                )

            dialog = MatchClothingDialog(
                self
            )
            dialog.exec_()

            self.status.setText(
                "Match Clothing closed."
            )

        return self.guarded(
            "Match Clothing",
            work,
        )

    def open_details(self):
        context = self.require_current_context()

        dialog = UnifiedDetailsDialog(
            context,
            self,
        )
        dialog.exec_()

    def closeEvent(
        self,
        event,
    ):
        try:
            app = QtGui.QApplication.instance()

            if (
                app is not None
                and getattr(
                    app,
                    APP_ATTR,
                    None,
                ) is self
            ):
                setattr(
                    app,
                    APP_ATTR,
                    None,
                )
        except Exception:
            pass

        QtGui.QDialog.closeEvent(
            self,
            event,
        )


def StartCharacterSliderPresetTool():
    app = QtGui.QApplication.instance()

    if app is None:
        return

    existing = getattr(
        app,
        APP_ATTR,
        None,
    )

    if existing is not None:
        try:
            existing.show()
            existing.raise_()
            existing.activateWindow()

            log_line(
                "TOOL_REOPEN_EXISTING_WINDOW=PASS"
            )
            return
        except Exception:
            pass

    reset_log()

    log_line(
        "=" * 120
    )
    log_line(
        "%s %s"
        % (
            TOOL_NAME,
            TOOL_VERSION,
        )
    )
    log_line(
        "captured_at=%s"
        % datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )
    )
    log_line(
        "SUPPORTED_PROFILES='Nika Shark; Krystal 2020'"
    )
    log_line(
        "NIKA_CAPABILITIES='Body Presets; Expressions; Match Clothing'"
    )
    log_line(
        "KRYSTAL_CAPABILITIES='Body Presets + required Head Scale'"
    )
    log_line(
        "SEMANTIC_PROVIDER='reused Master TXT provider generation where applicable'"
    )
    log_line(
        "SIDECAR_STATUS='planned provider replacement; not required for current candidate'"
    )

    try:
        window = CharacterPresetWindow(
            qt_parent()
        )

        setattr(
            app,
            APP_ATTR,
            window,
        )

        window.show()
        window.raise_()
        window.activateWindow()

        log_line(
            "TOOL_WINDOW_SHOWN=True"
        )
        log_line(
            "MAINMENU_CALLBACK_RETURNING=True"
        )
        log_line(
            "=" * 120
        )

    except Exception as exc:
        log_line(
            "TOOL_OPEN_FAIL=%r"
            % exc
        )
        log_line(
            traceback.format_exc()
        )

        try:
            QtGui.QMessageBox.warning(
                qt_parent(),
                "Character Preset Manager could not open",
                u(
                    exc
                ),
            )
        except Exception:
            pass




G09A_APP_ATTR = "_sfm_csp_g09a_generic_window_route"
G09A_SCHEMA_VERSION = 3
G09A_ID_POLICY = u"normalized-model-path-sha256-v1"


def g09a_normalize_model_path(path):
    value = u(path).replace(u"\\", u"/").strip().lower()
    while u"//" in value:
        value = value.replace(u"//", u"/")
    return value


def g09a_library_key(model_path):
    normalized = g09a_normalize_model_path(model_path)
    return u"modelpath-sha256-v1:" + u(
        hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    )


def g09a_safe_label(model_path):
    normalized = g09a_normalize_model_path(model_path)
    basename = normalized.rsplit(u"/", 1)[-1]
    if basename.lower().endswith(u".mdl"):
        basename = basename[:-4]

    for ch in u'<>:"/\\|?*':
        basename = basename.replace(ch, u"_")

    basename = basename.strip(u" .") or u"Model"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return basename[:80] + u"--" + u(digest)


def g09a_candidates():
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("No current shot.")

    result = []

    for row in p01_model_backed_animsets(shot):
        bindings = p01_all_supported_flex_bindings(row["animset"])
        if not bindings:
            continue

        result.append({
            "model": row.get("model"),
            "checksum": row.get("checksum"),
            "animset_name": row.get("animset_name"),
            "binding_count": len(bindings),
        })

    return sorted(
        result,
        key=lambda item: (
            (item.get("animset_name") or u"").lower(),
            (item.get("model") or u"").lower(),
            item.get("checksum") or 0,
        ),
    )


PROD_EMPTY_STATE_GUIDANCE = {
    u"no-session": u"Open an SFM session to use Character Preset Manager.",
    u"no-shot": u"Move the playhead into a shot to choose a character model.",
    u"no-models": u"Add a character model in the Animation Set Editor to get started.",
}


def prod_model_candidates():
    """(candidates, empty_reason) for the production window's model list.
    Ordinary empty states are returned rather than raised: no-session (no SFM
    document), no-shot (playhead outside every shot) and no-models (no
    supported character model in the current shot). Genuine failures still
    raise to the caller."""
    if not sfmApp.HasDocument():
        return [], u"no-session"
    if sfmApp.GetShotAtCurrentTime() is None:
        return [], u"no-shot"
    candidates = g09a_candidates()
    return candidates, (None if candidates else u"no-models")


def g09a_resolve(identity):
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("No current shot.")

    matches = []
    for row in p01_model_backed_animsets(shot):
        if (
            row.get("model") == identity.get("model")
            and row.get("checksum") == identity.get("checksum")
            and row.get("animset_name") == identity.get("animset_name")
        ):
            matches.append(row)

    if len(matches) != 1:
        raise RuntimeError(
            "Selected model could not be freshly re-resolved; found %d exact matches."
            % len(matches)
        )

    return matches[0]


def g09a_context(identity, row, snapshot):
    root = os.path.join(
        p02_documents(),
        P02_LIBRARY_DIRNAME,
    )
    folder = g09a_safe_label(identity["model"])
    character_root = os.path.join(
        root,
        u"Characters",
        folder,
    )

    misses = sorted(
        item["literal"]
        for item in snapshot["semantic"]["rows"]
        if item.get("semantic_class") == u"master-miss"
    )

    return {
        "identity": dict(identity),
        "library_key": g09a_library_key(identity["model"]),
        "character_folder": folder,
        "character_root": character_root,
        "body_dir": os.path.join(character_root, P03_BODY_FOLDER),
        "expression_dir": os.path.join(character_root, P03_EXPRESSION_FOLDER),
        "snapshot_signature": snapshot["signature"],
        "counts": dict(snapshot["semantic"]["counts"]),
        "misses": misses,
    }


def g09a_v3_preset_count(folder, expected_kind, library_key):
    count = 0

    for path in p03_json_candidates(folder):
        try:
            record = p02_read_json(path)
        except Exception:
            continue

        if record.get("schema_version") != G09A_SCHEMA_VERSION:
            continue
        if record.get("record_kind") != u"preset":
            continue
        if u(record.get("kind")) != expected_kind:
            continue
        if record.get("character_key") != library_key:
            continue
        if not isinstance(record.get("values"), dict):
            continue

        count += 1

    return count


class G09AGenericWindowRoute(QtGui.QDialog):

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle("SFM Character Slider Preset Tool - G09A")
        self.resize(780, 500)

        self.candidates = []
        self.pinned_identity = None
        self.current_context = None

        outer = QtGui.QVBoxLayout(self)

        header = QtGui.QHBoxLayout()
        header.addWidget(QtGui.QLabel("<b>Model:</b>"))

        self.model_combo = QtGui.QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_selection_changed)
        header.addWidget(self.model_combo, 1)

        self.refresh_button = QtGui.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.populate_models)
        header.addWidget(self.refresh_button)

        outer.addLayout(header)

        self.coverage = QtGui.QLabel("Choose a model.")
        self.coverage.setWordWrap(True)
        outer.addWidget(self.coverage)

        self.tabs = QtGui.QTabWidget()

        body_page = QtGui.QWidget()
        body_layout = QtGui.QVBoxLayout(body_page)
        self.body_summary = QtGui.QLabel("")
        self.body_summary.setWordWrap(True)
        body_layout.addWidget(self.body_summary)
        self.body_list = QtGui.QListWidget()
        body_layout.addWidget(self.body_list, 1)
        self.tabs.addTab(body_page, "Body Presets")

        expr_page = QtGui.QWidget()
        expr_layout = QtGui.QVBoxLayout(expr_page)
        self.expression_summary = QtGui.QLabel("")
        self.expression_summary.setWordWrap(True)
        expr_layout.addWidget(self.expression_summary)
        self.expression_list = QtGui.QListWidget()
        expr_layout.addWidget(self.expression_list, 1)
        self.tabs.addTab(expr_page, "Expressions")

        unresolved_page = QtGui.QWidget()
        unresolved_layout = QtGui.QVBoxLayout(unresolved_page)
        unresolved_layout.addWidget(
            QtGui.QLabel(
                "Unresolved sliders remain available for review; they are not silently classified."
            )
        )
        self.unresolved_list = QtGui.QListWidget()
        unresolved_layout.addWidget(self.unresolved_list, 1)
        self.tabs.addTab(unresolved_page, "Needs Review")

        outer.addWidget(self.tabs, 1)

        footer = QtGui.QHBoxLayout()

        self.validate_button = QtGui.QPushButton("Validate Current Route")
        self.validate_button.setEnabled(False)
        self.validate_button.clicked.connect(self.validate_route)
        footer.addWidget(self.validate_button)

        footer.addStretch(1)

        close_button = QtGui.QPushButton("Close")
        close_button.clicked.connect(self.close)
        footer.addWidget(close_button)

        outer.addLayout(footer)

        self.status = QtGui.QLabel("")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        tool_apply_visual_theme(self)

        self.populate_models()

    def populate_models(self):
        try:
            self.candidates = g09a_candidates()
        except Exception as exc:
            log_line("G09A_MODEL_ENUM_FAIL error=%r" % exc)
            self.status.setText("Models could not be listed.")
            return

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItem("Choose a model...")

        for item in self.candidates:
            self.model_combo.addItem(
                u"%s - %s"
                % (
                    u(item["animset_name"]),
                    u(item["model"]),
                )
            )

        self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)

        self.pinned_identity = None
        self.current_context = None
        self.validate_button.setEnabled(False)
        self.body_list.clear()
        self.expression_list.clear()
        self.unresolved_list.clear()
        self.body_summary.setText("")
        self.expression_summary.setText("")
        self.coverage.setText("Choose a model.")
        self.status.setText(
            "%d FLEX-bearing model(s) found. No model is selected."
            % len(self.candidates)
        )

        log_line(
            "G09A_MODELS count=%d initial_index=%d candidates=%r"
            % (
                len(self.candidates),
                self.model_combo.currentIndex(),
                [
                    (
                        item["model"],
                        item["checksum"],
                        item["animset_name"],
                        item["binding_count"],
                    )
                    for item in self.candidates
                ],
            )
        )

    def on_selection_changed(self, index):
        if index <= 0 or index > len(self.candidates):
            self.pinned_identity = None
            self.current_context = None
            self.validate_button.setEnabled(False)
            return

        item = self.candidates[index - 1]
        self.pinned_identity = {
            "model": item["model"],
            "checksum": item["checksum"],
            "animset_name": item["animset_name"],
        }

        log_line(
            "G09A_USER_SELECTION index=%d model=%r checksum=%r animset=%r"
            % (
                index,
                item["model"],
                item["checksum"],
                item["animset_name"],
            )
        )

        self.resolve_and_render()
        self.validate_button.setEnabled(True)

    def resolve_and_render(self):
        identity = self.pinned_identity
        if identity is None:
            return

        row = g09a_resolve(identity)
        snapshot = semantic_snapshot_for_model_row(
            row,
            get_semantic_provider(),
        )
        context = g09a_context(identity, row, snapshot)
        self.current_context = context

        counts = context["counts"]
        body_count = g09a_v3_preset_count(
            context["body_dir"],
            P03_KIND_BODY,
            context["library_key"],
        )
        expression_count = g09a_v3_preset_count(
            context["expression_dir"],
            P03_KIND_EXPRESSION,
            context["library_key"],
        )

        self.body_list.clear()
        self.expression_list.clear()
        self.unresolved_list.clear()

        self.body_list.addItem(
            "%d compatible v3 Body Preset(s) in this model library."
            % body_count
        )
        self.expression_list.addItem(
            "%d compatible v3 Expression(s) in this model library."
            % expression_count
        )

        for literal in context["misses"]:
            self.unresolved_list.addItem(literal)

        self.body_summary.setText(
            "Master-resolved Body controls: %d"
            % counts["body_eligible"]
        )
        self.expression_summary.setText(
            "Master-resolved Expression controls: %d"
            % counts["expression_eligible"]
        )

        self.coverage.setText(
            u"Expression: %d   Body: %d   Other: %d   Needs review: %d"
            % (
                counts["expression_eligible"],
                counts["body_eligible"],
                counts["resolved_other"],
                len(context["misses"]),
            )
        )

        self.status.setText(
            u"Ready - %s"
            % identity["animset_name"]
        )

        log_line(
            "G09A_ROUTE_RENDER model=%r animset=%r library_key=%r folder=%r "
            "face=%d body=%d other=%d miss=%d conflict=%d "
            "body_presets_v3=%d expressions_v3=%d"
            % (
                identity["model"],
                identity["animset_name"],
                context["library_key"],
                context["character_folder"],
                counts["expression_eligible"],
                counts["body_eligible"],
                counts["resolved_other"],
                len(context["misses"]),
                counts["conflict"],
                body_count,
                expression_count,
            )
        )

    def validate_route(self):
        if self.pinned_identity is None or self.current_context is None:
            self.status.setText("Choose a model first.")
            return

        try:
            pinned = dict(self.pinned_identity)
            prior = dict(self.current_context)

            row = g09a_resolve(pinned)
            snapshot = semantic_snapshot_for_model_row(
                row,
                get_semantic_provider(),
            )
            fresh = g09a_context(
                pinned,
                row,
                snapshot,
            )

            if fresh["identity"] != prior["identity"]:
                raise RuntimeError("Fresh target identity changed.")
            if fresh["library_key"] != prior["library_key"]:
                raise RuntimeError("Fresh library identity changed.")
            if fresh["character_folder"] != prior["character_folder"]:
                raise RuntimeError("Fresh library folder changed.")
            if fresh["snapshot_signature"] != prior["snapshot_signature"]:
                raise RuntimeError("Fresh semantic snapshot changed.")
            if fresh["counts"] != prior["counts"]:
                raise RuntimeError("Fresh semantic counts changed.")
            if fresh["misses"] != prior["misses"]:
                raise RuntimeError("Fresh unresolved set changed.")

            if self.model_combo.currentIndex() <= 0:
                raise RuntimeError("Model chooser lost its explicit selection.")

            stats = semantic_provider_runtime_stats()

            log_line(
                "G09A_RESULT=PASS model=%r animset=%r "
                "explicit_selection=True fresh_reacquire=True "
                "library_identity_stable=True semantic_snapshot_stable=True "
                "needs_review=%d provider_stats=%r"
                % (
                    pinned["model"],
                    pinned["animset_name"],
                    len(fresh["misses"]),
                    stats,
                )
            )

            self.status.setText(
                "PASS. Generic production-window route is stable for the selected model."
            )
            self.validate_button.setEnabled(False)

        except Exception as exc:
            log_line("G09A_RESULT=FAIL error=%r" % exc)
            log_line(traceback.format_exc())
            self.status.setText("Route validation failed. Send the G09A log for review.")


def RunG09AGenericWindowRoute():
    reset_log()
    log_line("=" * 120)
    log_line("G09A_GENERIC_PRODUCTION_WINDOW_ROUTE START")
    log_line("mutation_policy=READ_ONLY_NO_LIBRARY_WRITE_NO_DME_MUTATION")

    app = QtGui.QApplication.instance()
    if app is None:
        log_line("G09A_RESULT=FAIL error='No QApplication instance.'")
        return

    existing = getattr(app, G09A_APP_ATTR, None)
    if existing is not None:
        try:
            existing.close()
        except Exception:
            pass

    try:
        window = G09AGenericWindowRoute(qt_parent())
        setattr(app, G09A_APP_ATTR, window)
        window.show()
        window.raise_()
        window.activateWindow()

        log_line(
            "G09A_WINDOW_SHOWN=True initial_index=%d validate_enabled=%r"
            % (
                window.model_combo.currentIndex(),
                window.validate_button.isEnabled(),
            )
        )
        log_line("=" * 120)

    except Exception as exc:
        log_line("G09A_RESULT=FAIL error=%r" % exc)
        log_line(traceback.format_exc())



G11A_APP_ATTR = "_sfm_csp_g11a_production_window_body_match"
G11A_PANTS_CHECKSUM = 72805840
G11A_TOP_CHECKSUM = 1543245283


def g11a_source(
    identity,
    provider=None,
):
    row = g09a_resolve(identity)
    if provider is None:
        provider = get_semantic_provider()
    snapshot = semantic_snapshot_for_model_row(
        row,
        provider,
    )

    by_literal = {}
    for binding in snapshot["bindings"]:
        by_literal.setdefault(
            binding["literal"],
            [],
        ).append(binding)

    accepted = {}
    source_list = []

    for literal in snapshot["semantic"]["accepted_body_literals"]:
        rows = by_literal.get(literal, [])

        if len(rows) != 1:
            raise RuntimeError(
                "Generic Body literal %r has %d live bindings."
                % (literal, len(rows))
            )

        accepted[literal] = rows[0]
        source_list.append(rows[0])

    source_list.sort(
        key=lambda item: (
            item["literal"],
            item["shape"],
            repr(item["global_key"]),
        )
    )

    if not source_list:
        raise RuntimeError(
            "The selected model has no Master-resolved Body Morph controls."
        )

    values, snapshots = p03_capture_values(
        accepted
    )

    return {
        "identity": dict(identity),
        "row": row,
        "provider": provider,
        "snapshot": snapshot,
        "accepted": accepted,
        "source_list": source_list,
        "source_native": p03_native_index(
            row["gm"]
        ),
        "source_snapshots": snapshots,
    }


def g11a_verify_source_against(source_snapshot):
    fresh = g11a_source(
        source_snapshot["identity"]
    )

    return p03_verify_baselines(
        fresh["accepted"],
        source_snapshot["source_snapshots"],
    )


def g11a_target_rows():
    return p03_model_animsets()


def g11a_target_identity(row):
    return {
        "name": row["name"],
        "model": row["model"],
        "checksum": row["checksum"],
    }


def g11a_resolve_target(identity):
    matches = []

    for row in g11a_target_rows():
        if (
            row["name"] == identity["name"]
            and row["model"] == identity["model"]
            and row["checksum"] == identity["checksum"]
        ):
            matches.append(row)

    if len(matches) != 1:
        raise RuntimeError(
            "Body Match target %r could not be freshly re-resolved; found %d exact matches."
            % (
                identity["name"],
                len(matches),
            )
        )

    return matches[0]


def g11a_index_by_key(bindings):
    result = {}

    for binding in bindings:
        result.setdefault(
            binding["global_key"],
            [],
        ).append(binding)

    return result


def g11a_safe_plan(source, target_row):
    target_list = p03_target_bindings(
        target_row["animset"]
    )

    if not target_list:
        raise RuntimeError(
            "Target %r has no supported FLEX controls."
            % target_row["name"]
        )

    target_native = p03_native_index(
        target_row["gm"]
    )

    mapping = p03_build_mapping(
        source["source_list"],
        source["source_native"],
        target_list,
        target_native,
    )

    if not mapping["mappings"]:
        raise RuntimeError(
            "Target %r has no established compatible Body mappings."
            % target_row["name"]
        )

    if mapping["incompatible"]:
        raise RuntimeError(
            "Target %r has incompatible established mappings: %r."
            % (
                target_row["name"],
                mapping["incompatible"],
            )
        )

    for key, reason in mapping["ambiguous"]:
        if reason != "SOURCE_DUPLICATE":
            raise RuntimeError(
                "Target %r has unqualified ambiguity %r at %r."
                % (
                    target_row["name"],
                    reason,
                    key,
                )
            )

    ambiguous_keys = set(
        key for key, reason in mapping["ambiguous"]
    )
    mapped_keys = set(
        pair["source"]["global_key"]
        for pair in mapping["mappings"]
    )

    overlap = ambiguous_keys.intersection(
        mapped_keys
    )

    if overlap:
        raise RuntimeError(
            "Ambiguous keys leaked into the writable mapping set: %r."
            % sorted(
                repr(key)
                for key in overlap
            )
        )

    source_by_key = g11a_index_by_key(
        source["source_list"]
    )
    target_by_key = g11a_index_by_key(
        target_list
    )

    entries = []
    changed_sides = 0

    for pair in mapping["mappings"]:
        source_binding = pair["source"]
        target_binding = pair["target"]
        key = source_binding["global_key"]

        if len(source_by_key.get(key, [])) != 1:
            raise RuntimeError(
                "Writable source key %r is not unique."
                % (key,)
            )

        if len(target_by_key.get(key, [])) != 1:
            raise RuntimeError(
                "Writable target key %r is not unique."
                % (key,)
            )

        if not p03_native_pair_compatible(
            source["source_native"],
            target_native,
            source_binding,
            target_binding,
        ):
            raise RuntimeError(
                "Writable pair %r failed native compatibility."
                % (key,)
            )

        source_snap = source["source_snapshots"][
            source_binding["literal"]
        ]
        target_snap = p02_snapshot_supported(
            target_binding
        )

        side_entries = []

        for (
            source_side_name,
            source_side,
        ), (
            target_side_name,
            target_side,
        ) in zip(
            source_binding["sides"],
            target_binding["sides"],
        ):
            desired = source_snap["sides"][
                source_side_name
            ]["evaluated"]

            state = target_snap["sides"][
                target_side_name
            ]
            origin = state_kind(
                state
            )

            if origin == "UNSUPPORTED":
                raise RuntimeError(
                    "Target %r has unsupported state at %r/%s."
                    % (
                        target_row["name"],
                        target_binding["literal"],
                        target_side_name,
                    )
                )

            needs_write = not matches_value(
                state,
                desired,
            )

            if needs_write:
                changed_sides += 1

            side_entries.append({
                "side_name": target_side_name,
                "side": target_side,
                "origin": origin,
                "baseline": state,
                "desired": desired,
                "needs_write": needs_write,
            })

        entries.append({
            "target_binding": target_binding,
            "source_binding": source_binding,
            "target_baseline": target_snap,
            "sides": side_entries,
        })

    warnings = p03_unmapped_relevant_controls(
        {
            "provider": source["provider"],
        },
        target_list,
        mapping,
    )

    return {
        "identity": g11a_target_identity(
            target_row
        ),
        "mapping": mapping,
        "entries": entries,
        "changed_sides": changed_sides,
        "warnings": warnings,
    }


def g11a_candidates(source):
    result = []

    for row in g11a_target_rows():
        if same_dme(
            source["row"]["animset"],
            row["animset"],
        ):
            continue

        try:
            plan = g11a_safe_plan(
                source,
                row,
            )
        except Exception:
            continue

        result.append({
            "identity": dict(
                plan["identity"]
            ),
            "mapping_count": len(
                plan["mapping"]["mappings"]
            ),
            "source_duplicate_count": len(
                plan["mapping"]["ambiguous"]
            ),
            "warning_count": len(
                plan["warnings"]
            ),
        })

    result.sort(
        key=lambda item: (
            item["identity"]["name"],
            item["identity"]["model"],
        )
    )

    return result


def g11a_snapshot_target(plan):
    target = g11a_resolve_target(
        plan["identity"]
    )

    current = p03_target_bindings(
        target["animset"]
    )
    by_key = g11a_index_by_key(
        current
    )
    result = {}

    for entry in plan["entries"]:
        key = entry["target_binding"]["global_key"]
        matches = by_key.get(
            key,
            [],
        )

        if len(matches) != 1:
            raise RuntimeError(
                "Target snapshot key %r is not unique."
                % (key,)
            )

        result[
            repr(key)
        ] = binding_snapshot(
            matches[0]
        )

    return result


def g11a_verify_target_snapshot(
    plan,
    baseline,
):
    target = g11a_resolve_target(
        plan["identity"]
    )

    current = p03_target_bindings(
        target["animset"]
    )
    by_key = g11a_index_by_key(
        current
    )

    for entry in plan["entries"]:
        key = entry["target_binding"]["global_key"]
        matches = by_key.get(
            key,
            [],
        )

        if len(matches) != 1:
            return False

        observed = binding_snapshot(
            matches[0]
        )
        expected = baseline.get(
            repr(key)
        )

        if expected is None:
            return False

        if (
            observed["literal"] != expected["literal"]
            or observed["shape"] != expected["shape"]
            or observed["control_id"] != expected["control_id"]
        ):
            return False

        for side_name, side in matches[0]["sides"]:
            origin = state_kind(
                expected["sides"][
                    side_name
                ]
            )

            if not matches_baseline(
                observed["sides"][
                    side_name
                ],
                expected["sides"][
                    side_name
                ],
                origin,
            ):
                return False

    return True


def g11a_apply_one(plan):
    if plan["changed_sides"] == 0:
        return "NO_CHANGE"

    label = (
        u"G11A Match Clothing: "
        + u(
            plan["identity"]["name"]
        )
    )

    dm_obj = dm()
    scope_open = False

    try:
        dm_obj.StartUndo(
            b(label),
            b(u"Redo " + label),
        )
        scope_open = True

        for entry in plan["entries"]:
            binding = entry["target_binding"]

            for side_entry in entry["sides"]:
                if not side_entry["needs_write"]:
                    continue

                write_side(
                    binding,
                    side_entry["side"],
                    side_entry["origin"],
                    side_entry["desired"],
                )

        for entry in plan["entries"]:
            observed = binding_snapshot(
                entry["target_binding"]
            )

            for side_entry in entry["sides"]:
                if not matches_value(
                    observed["sides"][
                        side_entry["side_name"]
                    ],
                    side_entry["desired"],
                ):
                    raise RuntimeError(
                        "Authored Body Match verification failed for %r."
                        % plan["identity"]["name"]
                    )

        dm_obj.FinishUndo()
        scope_open = False

    except Exception:
        if scope_open:
            dm_obj.AbortUndoableOperation()
        raise

    same_time_refresh(
        float(
            sfmApp.GetHeadTimeInSeconds()
        ),
        label,
    )

    return "CHANGED"


def g11a_common_fixture_probe(
    source,
    plans,
):
    if not plans:
        raise RuntimeError(
            "No target plans were supplied for the qualification source delta."
        )

    common = None
    pair_by_plan = []

    for plan in plans:
        pairs = dict(
            (
                pair["source"]["global_key"],
                pair,
            )
            for pair in plan["mapping"]["mappings"]
        )
        pair_by_plan.append(
            pairs
        )

        keys = set(
            pairs.keys()
        )

        if common is None:
            common = keys
        else:
            common = common.intersection(
                keys
            )

    common = sorted(
        common or [],
        key=lambda value: repr(value),
    )

    if not common:
        raise RuntimeError(
            "The qualification targets have no common safe Body mapping."
        )

    for key in common:
        source_binding = pair_by_plan[0][
            key
        ]["source"]
        source_snap = source["source_snapshots"][
            source_binding["literal"]
        ]

        target_snaps = []

        for pairs in pair_by_plan:
            target_binding = pairs[
                key
            ]["target"]
            target_snaps.append(
                p02_snapshot_supported(
                    target_binding
                )
            )

        for side_name, side in source_binding["sides"]:
            source_state = source_snap["sides"][
                side_name
            ]
            origin = state_kind(
                source_state
            )

            if origin == "UNSUPPORTED":
                continue

            current = as_float(
                source_state.get(
                    "evaluated"
                )
            )

            if current is None:
                continue

            target_values = []

            valid = True

            for snap in target_snaps:
                if side_name not in snap["sides"]:
                    valid = False
                    break

                value = as_float(
                    snap["sides"][
                        side_name
                    ].get(
                        "evaluated"
                    )
                )

                if value is None:
                    valid = False
                    break

                target_values.append(
                    value
                )

            if not valid:
                continue

            for desired in (
                current + 0.125,
                current - 0.125,
                current + 0.25,
                current - 0.25,
            ):
                if close_enough(
                    desired,
                    current,
                ):
                    continue

                if any(
                    close_enough(
                        desired,
                        value,
                    )
                    for value in target_values
                ):
                    continue

                return {
                    "binding": source_binding,
                    "side_name": side_name,
                    "side": side,
                    "origin": origin,
                    "before": current,
                    "desired": float(
                        desired
                    ),
                    "literal": source_binding[
                        "literal"
                    ],
                    "global_key": key,
                }

    raise RuntimeError(
        "No common mapped source side can create a visible delta in both qualification garments."
    )


def g11a_change_source(
    source,
    probe,
):
    label = u"G11A Qualification Source Delta"

    dm_obj = dm()
    scope_open = False

    try:
        dm_obj.StartUndo(
            b(label),
            b(u"Redo " + label),
        )
        scope_open = True

        write_side(
            probe["binding"],
            probe["side"],
            probe["origin"],
            probe["desired"],
        )

        observed = binding_snapshot(
            probe["binding"]
        )

        if not matches_value(
            observed["sides"][
                probe["side_name"]
            ],
            probe["desired"],
        ):
            raise RuntimeError(
                "Qualification source delta failed verification."
            )

        dm_obj.FinishUndo()
        scope_open = False

    except Exception:
        if scope_open:
            dm_obj.AbortUndoableOperation()
        raise

    same_time_refresh(
        float(
            sfmApp.GetHeadTimeInSeconds()
        ),
        label,
    )


class G11AMatchClothingDialog(QtGui.QDialog):

    def __init__(
        self,
        owner,
        source_identity,
        expected_source,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )

        self.owner = owner
        self.source_identity = dict(
            source_identity
        )
        self.expected_source = expected_source

        self.candidates = []
        self.batch_active = False
        self.batch_generation = 0
        self.selected_identities = []
        self.selected_original_plans = {}
        self.selected_original_snapshots = {}
        self.committed_order = []
        self.outcomes = []

        self.setWindowTitle(
            "Match Clothing"
        )
        self.resize(
            700,
            520,
        )

        layout = QtGui.QVBoxLayout(
            self
        )

        note = QtGui.QLabel(
            "Select clothing to match to the model chosen in the main window. "
            "Each changed garment creates its own native SFM Undo item."
        )
        note.setWordWrap(
            True
        )
        layout.addWidget(
            note
        )

        self.list = QtGui.QListWidget()
        layout.addWidget(
            self.list,
            1,
        )

        self.result = QtGui.QLabel(
            ""
        )
        self.result.setWordWrap(
            True
        )
        layout.addWidget(
            self.result
        )

        buttons = QtGui.QDialogButtonBox()

        self.match_button = buttons.addButton(
            "Match Selected",
            QtGui.QDialogButtonBox.AcceptRole,
        )

        close_button = buttons.addButton(
            QtGui.QDialogButtonBox.Close,
        )

        self.match_button.clicked.connect(
            self.start_batch
        )
        close_button.clicked.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        tool_apply_visual_theme(
            self
        )

        self.populate()

    def closeEvent(
        self,
        event,
    ):
        self.batch_active = False
        self.batch_generation += 1
        QtGui.QDialog.closeEvent(
            self,
            event,
        )

    def populate(self):
        source = g11a_source(
            self.source_identity
        )

        self.candidates = g11a_candidates(
            source
        )

        self.list.clear()

        for candidate in self.candidates:
            ident = candidate[
                "identity"
            ]

            item = QtGui.QListWidgetItem(
                u"%s  (%d mapped; %d review)"
                % (
                    u(
                        ident["name"]
                    ),
                    candidate[
                        "mapping_count"
                    ],
                    candidate[
                        "warning_count"
                    ],
                )
            )

            item.setFlags(
                item.flags()
                | QtCore.Qt.ItemIsUserCheckable
            )
            item.setCheckState(
                QtCore.Qt.Unchecked
            )
            item.setData(
                QtCore.Qt.UserRole,
                candidate,
            )

            self.list.addItem(
                item
            )

        self.result.setText(
            "%d compatible target(s) found. Check exactly two for this qualification."
            % len(
                self.candidates
            )
        )

        self.match_button.setEnabled(
            bool(
                self.candidates
            )
        )

        log_line(
            "G11A_MATCH_DIALOG candidates=%r"
            % [
                (
                    item["identity"]["model"],
                    item["identity"]["checksum"],
                    item["identity"]["name"],
                    item["mapping_count"],
                    item["source_duplicate_count"],
                    item["warning_count"],
                )
                for item in self.candidates
            ]
        )

    def checked_candidates(self):
        result = []

        for index in range(
            self.list.count()
        ):
            item = self.list.item(
                index
            )

            if item.checkState() != QtCore.Qt.Checked:
                continue

            result.append(
                item.data(
                    QtCore.Qt.UserRole
                )
            )

        return result

    def start_batch(self):
        if self.batch_active:
            return

        selected = self.checked_candidates()

        if len(selected) != 2:
            self.result.setText(
                "For G11A, select exactly two targets: Nika sports pants and Nika sports top."
            )
            return

        checksums = set(
            item["identity"]["checksum"]
            for item in selected
        )

        expected = set([
            G11A_PANTS_CHECKSUM,
            G11A_TOP_CHECKSUM,
        ])

        if checksums != expected:
            self.result.setText(
                "For G11A, select exactly Nika sports pants and Nika sports top."
            )
            return

        try:
            source = g11a_source(
                self.source_identity
            )

            if not g11a_verify_source_against(
                self.expected_source
            ):
                raise RuntimeError(
                    "The selected source model changed before Body Match began."
                )

            self.selected_identities = [
                dict(
                    item["identity"]
                )
                for item in selected
            ]
            self.selected_original_plans = {}
            self.selected_original_snapshots = {}

            for identity in self.selected_identities:
                plan = g11a_safe_plan(
                    source,
                    g11a_resolve_target(
                        identity
                    ),
                )

                self.selected_original_plans[
                    identity["checksum"]
                ] = plan
                self.selected_original_snapshots[
                    identity["checksum"]
                ] = g11a_snapshot_target(
                    plan
                )

            self.batch_active = True
            self.batch_generation += 1
            generation = self.batch_generation
            self.committed_order = []
            self.outcomes = []

            self.match_button.setEnabled(
                False
            )
            self.list.setEnabled(
                False
            )
            self.result.setText(
                "Matching selected clothing..."
            )

            log_line(
                "G11A_COORDINATOR_START generation=%d "
                "source_model=%r source_animset=%r "
                "selected=%r user_click_mutation_transactions=0"
                % (
                    generation,
                    self.source_identity[
                        "model"
                    ],
                    self.source_identity[
                        "animset_name"
                    ],
                    self.selected_identities,
                )
            )

            QtCore.QTimer.singleShot(
                0,
                lambda: self.run_stage(
                    generation,
                    0,
                ),
            )

        except Exception as exc:
            log_line(
                "G11A_COORDINATOR_START_FAIL error=%r"
                % exc
            )
            log_line(
                traceback.format_exc()
            )
            self.result.setText(
                "Body Match could not start. Send the G11A log for review."
            )

    def stage_valid(
        self,
        generation,
    ):
        return (
            self.batch_active
            and generation == self.batch_generation
            and self.isVisible()
        )

    def fail_batch(
        self,
        stage_index,
        exc,
    ):
        self.batch_active = False

        log_line(
            "G11A_COORDINATOR_FAIL stage_index=%d error=%r"
            % (
                stage_index,
                exc,
            )
        )
        log_line(
            traceback.format_exc()
        )

        self.result.setText(
            "Body Match failed. Send the G11A log for review."
        )

    def run_stage(
        self,
        generation,
        stage_index,
    ):
        if not self.stage_valid(
            generation
        ):
            return

        if stage_index >= len(
            self.selected_identities
        ):
            self.finish_batch(
                generation
            )
            return

        identity = self.selected_identities[
            stage_index
        ]

        try:
            log_line(
                "G11A_STAGE_ENTER generation=%d stage_index=%d target=%r queued_callback=True"
                % (
                    generation,
                    stage_index,
                    identity,
                )
            )

            source = g11a_source(
                self.source_identity
            )

            if not g11a_verify_source_against(
                self.expected_source
            ):
                raise RuntimeError(
                    "The selected source changed during queued Body Match."
                )

            plan = g11a_safe_plan(
                source,
                g11a_resolve_target(
                    identity
                ),
            )

            outcome = g11a_apply_one(
                plan
            )

            if outcome == "CHANGED":
                self.committed_order.append(
                    dict(
                        identity
                    )
                )

            fresh_source = g11a_source(
                self.source_identity
            )

            if not g11a_verify_source_against(
                self.expected_source
            ):
                raise RuntimeError(
                    "Matching target %r changed the selected source."
                    % identity["name"]
                )

            fresh_plan = g11a_safe_plan(
                fresh_source,
                g11a_resolve_target(
                    identity
                ),
            )

            if fresh_plan["changed_sides"] != 0:
                raise RuntimeError(
                    "Target %r does not match after its queued stage."
                    % identity["name"]
                )

            self.outcomes.append({
                "identity": dict(
                    identity
                ),
                "outcome": outcome,
                "mapping_count": len(
                    plan["mapping"]["mappings"]
                ),
                "warning_count": len(
                    plan["warnings"]
                ),
            })

            log_line(
                "G11A_STAGE_PASS generation=%d stage_index=%d "
                "target=%r outcome=%r mappings=%d warnings=%d "
                "mutation_transactions_in_callback=%d"
                % (
                    generation,
                    stage_index,
                    identity,
                    outcome,
                    len(
                        plan["mapping"]["mappings"]
                    ),
                    len(
                        plan["warnings"]
                    ),
                    (
                        1
                        if outcome == "CHANGED"
                        else 0
                    ),
                )
            )

            QtCore.QTimer.singleShot(
                0,
                lambda: self.run_stage(
                    generation,
                    stage_index + 1,
                ),
            )

        except Exception as exc:
            self.fail_batch(
                stage_index,
                exc,
            )

    def finish_batch(
        self,
        generation,
    ):
        if not self.stage_valid(
            generation
        ):
            return

        try:
            source = g11a_source(
                self.source_identity
            )

            if not g11a_verify_source_against(
                self.expected_source
            ):
                raise RuntimeError(
                    "The selected source changed during final Body Match verification."
                )

            for identity in self.selected_identities:
                plan = g11a_safe_plan(
                    source,
                    g11a_resolve_target(
                        identity
                    ),
                )

                if plan["changed_sides"] != 0:
                    raise RuntimeError(
                        "Target %r failed final batch verification."
                        % identity["name"]
                    )

            if len(
                self.committed_order
            ) != 2:
                raise RuntimeError(
                    "G11A requires both qualification garments to create one native Undo transaction."
                )

            self.batch_active = False

            log_line(
                "G11A_COORDINATOR=PASS generation=%d "
                "single_user_match_action=True "
                "source_from_generic_window=True "
                "selected_source_identity=%r "
                "queued_zero_delay_event_turns=True "
                "one_mutation_transaction_per_callback=True "
                "committed_order=%r outcomes=%r"
                % (
                    generation,
                    self.source_identity,
                    self.committed_order,
                    self.outcomes,
                )
            )

            self.result.setText(
                "Both garments matched."
            )

            self.owner.on_body_match_complete(
                self,
            )

        except Exception as exc:
            self.fail_batch(
                len(
                    self.selected_identities
                ),
                exc,
            )


class G11AProductionWindow(QtGui.QDialog):

    def __init__(
        self,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )

        self.setWindowTitle(
            "SFM Character Slider Preset Tool - G11A"
        )
        self.resize(
            820,
            580,
        )

        self.candidates = []
        self.identity = None
        self.current_context = None

        self.original_source = None
        self.disturbed_source = None

        self.body_match_dialog = None
        self.committed_order = []
        self.target_plans = {}
        self.target_snapshots = {}

        self.top_undo_verified = False
        self.pants_undo_verified = False

        outer = QtGui.QVBoxLayout(
            self
        )

        header = QtGui.QHBoxLayout()
        header.addWidget(
            QtGui.QLabel(
                "<b>Model:</b>"
            )
        )

        self.model_combo = QtGui.QComboBox()
        self.model_combo.currentIndexChanged.connect(
            self.on_selection_changed
        )
        header.addWidget(
            self.model_combo,
            1,
        )

        self.refresh_button = QtGui.QPushButton(
            "Refresh Models"
        )
        self.refresh_button.clicked.connect(
            self.populate_models
        )
        header.addWidget(
            self.refresh_button
        )

        outer.addLayout(
            header
        )

        self.coverage = QtGui.QLabel(
            "Choose a model."
        )
        self.coverage.setWordWrap(
            True
        )
        outer.addWidget(
            self.coverage
        )

        self.tabs = QtGui.QTabWidget()

        body_page = QtGui.QWidget()
        body_layout = QtGui.QVBoxLayout(
            body_page
        )
        self.body_summary = QtGui.QLabel(
            ""
        )
        body_layout.addWidget(
            self.body_summary
        )
        self.tabs.addTab(
            body_page,
            "Body Presets",
        )

        expression_page = QtGui.QWidget()
        expression_layout = QtGui.QVBoxLayout(
            expression_page
        )
        self.expression_summary = QtGui.QLabel(
            ""
        )
        expression_layout.addWidget(
            self.expression_summary
        )
        self.tabs.addTab(
            expression_page,
            "Expressions",
        )

        review_page = QtGui.QWidget()
        review_layout = QtGui.QVBoxLayout(
            review_page
        )
        self.review_list = QtGui.QListWidget()
        review_layout.addWidget(
            self.review_list
        )
        self.tabs.addTab(
            review_page,
            "Needs Review",
        )

        outer.addWidget(
            self.tabs,
            1,
        )

        test_note = QtGui.QLabel(
            "Qualification setup: after selecting Nika, create one source Body delta. "
            "Then open Match Clothing, check only sports pants and sports top, and click Match Selected once."
        )
        test_note.setWordWrap(
            True
        )
        outer.addWidget(
            test_note
        )

        row1 = QtGui.QHBoxLayout()

        self.delta_button = QtGui.QPushButton(
            "1. Create Qualification Source Delta"
        )
        self.delta_button.setEnabled(
            False
        )
        self.delta_button.clicked.connect(
            self.create_source_delta
        )
        row1.addWidget(
            self.delta_button
        )

        self.match_button = QtGui.QPushButton(
            "2. Match Clothing..."
        )
        self.match_button.setEnabled(
            False
        )
        self.match_button.clicked.connect(
            self.open_match
        )
        row1.addWidget(
            self.match_button
        )

        outer.addLayout(
            row1
        )

        row2 = QtGui.QHBoxLayout()

        self.verify_top_button = QtGui.QPushButton(
            "3. Verify Top Match Undo"
        )
        self.verify_top_button.setEnabled(
            False
        )
        self.verify_top_button.clicked.connect(
            self.verify_top_undo
        )
        row2.addWidget(
            self.verify_top_button
        )

        self.verify_pants_button = QtGui.QPushButton(
            "4. Verify Pants Match Undo"
        )
        self.verify_pants_button.setEnabled(
            False
        )
        self.verify_pants_button.clicked.connect(
            self.verify_pants_undo
        )
        row2.addWidget(
            self.verify_pants_button
        )

        self.verify_final_button = QtGui.QPushButton(
            "5. Verify Final Cleanup"
        )
        self.verify_final_button.setEnabled(
            False
        )
        self.verify_final_button.clicked.connect(
            self.verify_final
        )
        row2.addWidget(
            self.verify_final_button
        )

        outer.addLayout(
            row2
        )

        self.status = QtGui.QLabel(
            ""
        )
        self.status.setWordWrap(
            True
        )
        outer.addWidget(
            self.status
        )

        tool_apply_visual_theme(
            self
        )

        self.populate_models()

    def populate_models(self):
        self.candidates = g09a_candidates()

        self.model_combo.blockSignals(
            True
        )
        self.model_combo.clear()
        self.model_combo.addItem(
            "Choose a model..."
        )

        for item in self.candidates:
            self.model_combo.addItem(
                u"%s - %s"
                % (
                    u(
                        item["animset_name"]
                    ),
                    u(
                        item["model"]
                    ),
                )
            )

        self.model_combo.setCurrentIndex(
            0
        )
        self.model_combo.blockSignals(
            False
        )

        self.identity = None
        self.current_context = None

        self.delta_button.setEnabled(
            False
        )
        self.match_button.setEnabled(
            False
        )
        self.verify_top_button.setEnabled(
            False
        )
        self.verify_pants_button.setEnabled(
            False
        )
        self.verify_final_button.setEnabled(
            False
        )

        self.coverage.setText(
            "Choose a model."
        )
        self.body_summary.setText(
            ""
        )
        self.expression_summary.setText(
            ""
        )
        self.review_list.clear()

        self.status.setText(
            "%d FLEX-bearing model(s) found."
            % len(
                self.candidates
            )
        )

        log_line(
            "G11A_MODELS count=%d initial_index=%d candidates=%r"
            % (
                len(
                    self.candidates
                ),
                self.model_combo.currentIndex(),
                [
                    (
                        item["model"],
                        item["checksum"],
                        item["animset_name"],
                        item["binding_count"],
                    )
                    for item in self.candidates
                ],
            )
        )

    def on_selection_changed(
        self,
        index,
    ):
        self.delta_button.setEnabled(
            False
        )
        self.match_button.setEnabled(
            False
        )
        self.review_list.clear()

        if (
            index <= 0
            or index > len(
                self.candidates
            )
        ):
            self.identity = None
            self.current_context = None
            self.coverage.setText(
                "Choose a model."
            )
            return

        item = self.candidates[
            index - 1
        ]

        identity = {
            "model": item["model"],
            "checksum": item["checksum"],
            "animset_name": item["animset_name"],
        }

        row = g09a_resolve(
            identity
        )
        snapshot = semantic_snapshot_for_model_row(
            row,
            get_semantic_provider(),
        )
        context = g09a_context(
            identity,
            row,
            snapshot,
        )

        self.identity = identity
        self.current_context = context

        counts = context[
            "counts"
        ]

        self.body_summary.setText(
            "Master-resolved Body controls: %d"
            % counts[
                "body_eligible"
            ]
        )
        self.expression_summary.setText(
            "Master-resolved Expression controls: %d"
            % counts[
                "expression_eligible"
            ]
        )

        for literal in context[
            "misses"
        ]:
            self.review_list.addItem(
                literal
            )

        self.coverage.setText(
            u"Expression: %d   Body: %d   Other: %d   Needs review: %d"
            % (
                counts[
                    "expression_eligible"
                ],
                counts[
                    "body_eligible"
                ],
                counts[
                    "resolved_other"
                ],
                len(
                    context[
                        "misses"
                    ]
                ),
            )
        )

        self.delta_button.setEnabled(
            counts[
                "body_eligible"
            ] > 0
        )

        self.status.setText(
            u"Ready - %s"
            % identity[
                "animset_name"
            ]
        )

        log_line(
            "G11A_SELECTION model=%r checksum=%r animset=%r "
            "library_key=%r face=%d body=%d other=%d miss=%d"
            % (
                identity[
                    "model"
                ],
                identity[
                    "checksum"
                ],
                identity[
                    "animset_name"
                ],
                context[
                    "library_key"
                ],
                counts[
                    "expression_eligible"
                ],
                counts[
                    "body_eligible"
                ],
                counts[
                    "resolved_other"
                ],
                len(
                    context[
                        "misses"
                    ]
                ),
            )
        )

    def create_source_delta(self):
        if self.identity is None:
            return

        try:
            # G11A uses the known two-garment fixture only to create deterministic
            # qualification input. Body Match itself remains selected-source generic.
            pants_rows = [
                row for row in g11a_target_rows()
                if row[
                    "checksum"
                ] == G11A_PANTS_CHECKSUM
            ]
            top_rows = [
                row for row in g11a_target_rows()
                if row[
                    "checksum"
                ] == G11A_TOP_CHECKSUM
            ]

            if (
                len(
                    pants_rows
                ) != 1
                or len(
                    top_rows
                ) != 1
            ):
                raise RuntimeError(
                    "G11A qualification requires exactly one Nika sports pants and one Nika sports top in the shot."
                )

            source = g11a_source(
                self.identity
            )

            pants_plan = g11a_safe_plan(
                source,
                pants_rows[0],
            )
            top_plan = g11a_safe_plan(
                source,
                top_rows[0],
            )

            probe = g11a_common_fixture_probe(
                source,
                [
                    pants_plan,
                    top_plan,
                ],
            )

            self.original_source = source

            g11a_change_source(
                source,
                probe,
            )

            disturbed_source = g11a_source(
                self.identity
            )

            pants_fresh = g11a_safe_plan(
                disturbed_source,
                pants_rows[0],
            )
            top_fresh = g11a_safe_plan(
                disturbed_source,
                top_rows[0],
            )

            if (
                pants_fresh[
                    "changed_sides"
                ] < 1
                or top_fresh[
                    "changed_sides"
                ] < 1
            ):
                raise RuntimeError(
                    "Qualification source delta did not create Body Match changes for both known garments."
                )

            self.disturbed_source = disturbed_source

            self.model_combo.setEnabled(
                False
            )
            self.refresh_button.setEnabled(
                False
            )
            self.delta_button.setEnabled(
                False
            )
            self.match_button.setEnabled(
                True
            )

            log_line(
                "G11A_SOURCE_DELTA=PASS "
                "selected_source_model=%r selected_source_animset=%r "
                "literal=%r side=%r key=%r before=%r desired=%r "
                "pants_changed_sides=%d top_changed_sides=%d "
                "source_from_generic_window=True"
                % (
                    self.identity[
                        "model"
                    ],
                    self.identity[
                        "animset_name"
                    ],
                    probe[
                        "literal"
                    ],
                    probe[
                        "side_name"
                    ],
                    probe[
                        "global_key"
                    ],
                    probe[
                        "before"
                    ],
                    probe[
                        "desired"
                    ],
                    pants_fresh[
                        "changed_sides"
                    ],
                    top_fresh[
                        "changed_sides"
                    ],
                )
            )

            self.status.setText(
                "Qualification source delta PASS. Open Match Clothing."
            )

        except Exception as exc:
            log_line(
                "G11A_SOURCE_DELTA=FAIL error=%r"
                % exc
            )
            log_line(
                traceback.format_exc()
            )
            self.status.setText(
                "Qualification setup failed. Send the G11A log for review."
            )

    def open_match(self):
        if (
            self.identity is None
            or self.disturbed_source is None
        ):
            return

        dialog = G11AMatchClothingDialog(
            self,
            self.identity,
            self.disturbed_source,
            self,
        )

        self.body_match_dialog = dialog

        log_line(
            "G11A_MATCH_DIALOG_OPEN source_identity=%r"
            % self.identity
        )

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def on_body_match_complete(
        self,
        dialog,
    ):
        self.committed_order = [
            dict(
                identity
            )
            for identity in dialog.committed_order
        ]
        self.target_plans = dict(
            dialog.selected_original_plans
        )
        self.target_snapshots = dict(
            dialog.selected_original_snapshots
        )

        self.match_button.setEnabled(
            False
        )
        self.verify_top_button.setEnabled(
            True
        )

        self.status.setText(
            "Body Match PASS. Press Ctrl+Z once, then Verify Top Match Undo."
        )

        log_line(
            "G11A_WINDOW_BODY_MATCH_COMPLETE "
            "source_identity=%r committed_order=%r"
            % (
                self.identity,
                self.committed_order,
            )
        )

    def verify_top_undo(self):
        if len(
            self.committed_order
        ) != 2:
            return

        try:
            last_identity = self.committed_order[
                -1
            ]
            first_identity = self.committed_order[
                0
            ]

            same_time_refresh(
                float(
                    sfmApp.GetHeadTimeInSeconds()
                ),
                "G11A_UNDO_LAST_MATCH",
            )

            last_checksum = last_identity[
                "checksum"
            ]

            if not g11a_verify_target_snapshot(
                self.target_plans[
                    last_checksum
                ],
                self.target_snapshots[
                    last_checksum
                ],
            ):
                raise RuntimeError(
                    "Undo did not restore the last matched target."
                )

            source = g11a_source(
                self.identity
            )
            first_plan = g11a_safe_plan(
                source,
                g11a_resolve_target(
                    first_identity
                ),
            )

            if first_plan[
                "changed_sides"
            ] != 0:
                raise RuntimeError(
                    "Undoing the last target changed the earlier matched target."
                )

            if not g11a_verify_source_against(
                self.disturbed_source
            ):
                raise RuntimeError(
                    "The selected source changed after the first Match Undo."
                )

            self.top_undo_verified = True

            self.verify_top_button.setEnabled(
                False
            )
            self.verify_pants_button.setEnabled(
                True
            )

            log_line(
                "G11A_UNDO_LAST_MATCH=PASS "
                "last_target=%r earlier_target_still_matched=True "
                "source_delta_preserved=True undo_state=%r"
                % (
                    last_identity,
                    undo_state(
                        "G11A_UNDO_LAST_STATE"
                    ),
                )
            )

            self.status.setText(
                "Last Match Undo PASS. Press Ctrl+Z once, then Verify Pants Match Undo."
            )

        except Exception as exc:
            log_line(
                "G11A_UNDO_LAST_MATCH=FAIL error=%r"
                % exc
            )
            log_line(
                traceback.format_exc()
            )
            self.status.setText(
                "Undo verification failed. Send the G11A log for review."
            )

    def verify_pants_undo(self):
        if not self.top_undo_verified:
            return

        try:
            same_time_refresh(
                float(
                    sfmApp.GetHeadTimeInSeconds()
                ),
                "G11A_UNDO_FIRST_MATCH",
            )

            for identity in self.committed_order:
                checksum = identity[
                    "checksum"
                ]

                if not g11a_verify_target_snapshot(
                    self.target_plans[
                        checksum
                    ],
                    self.target_snapshots[
                        checksum
                    ],
                ):
                    raise RuntimeError(
                        "Undo did not restore target %r."
                        % identity[
                            "name"
                        ]
                    )

            if not g11a_verify_source_against(
                self.disturbed_source
            ):
                raise RuntimeError(
                    "The selected source changed after the second Match Undo."
                )

            self.pants_undo_verified = True

            self.verify_pants_button.setEnabled(
                False
            )
            self.verify_final_button.setEnabled(
                True
            )

            log_line(
                "G11A_UNDO_FIRST_MATCH=PASS "
                "both_targets_original=True "
                "source_delta_preserved=True undo_state=%r"
                % undo_state(
                    "G11A_UNDO_FIRST_STATE"
                )
            )

            self.status.setText(
                "Both Match Undos PASS. Press Ctrl+Z once, then Verify Final Cleanup."
            )

        except Exception as exc:
            log_line(
                "G11A_UNDO_FIRST_MATCH=FAIL error=%r"
                % exc
            )
            log_line(
                traceback.format_exc()
            )
            self.status.setText(
                "Undo verification failed. Send the G11A log for review."
            )

    def verify_final(self):
        if not self.pants_undo_verified:
            return

        try:
            same_time_refresh(
                float(
                    sfmApp.GetHeadTimeInSeconds()
                ),
                "G11A_FINAL_CLEANUP",
            )

            if not g11a_verify_source_against(
                self.original_source
            ):
                raise RuntimeError(
                    "Final Undo did not restore the selected source model exactly."
                )

            for identity in self.committed_order:
                checksum = identity[
                    "checksum"
                ]

                if not g11a_verify_target_snapshot(
                    self.target_plans[
                        checksum
                    ],
                    self.target_snapshots[
                        checksum
                    ],
                ):
                    raise RuntimeError(
                        "Target %r changed during final source cleanup."
                        % identity[
                            "name"
                        ]
                    )

            # Re-resolve the same generic production-window identity after all
            # mutation and Undo work.
            row = g09a_resolve(
                self.identity
            )
            snapshot = semantic_snapshot_for_model_row(
                row,
                get_semantic_provider(),
            )
            final_context = g09a_context(
                self.identity,
                row,
                snapshot,
            )

            if final_context[
                "identity"
            ] != self.current_context[
                "identity"
            ]:
                raise RuntimeError(
                    "Generic production-window identity changed."
                )

            if final_context[
                "library_key"
            ] != self.current_context[
                "library_key"
            ]:
                raise RuntimeError(
                    "Generic production-window library identity changed."
                )

            stats = semantic_provider_runtime_stats()

            log_line(
                "G11A_RESULT=PASS "
                "source_selected_in_generic_production_window=True "
                "source_identity=%r "
                "production_window_identity_stable=True "
                "generic_master_body_scope=True "
                "match_dialog_candidates_from_selected_source=True "
                "single_user_match_action=True "
                "queued_zero_delay_event_turns=True "
                "one_mutation_transaction_per_callback=True "
                "source_duplicate_keys_excluded=True "
                "one_native_undo_per_changed_garment=True "
                "undo_isolation=True "
                "source_setup_undo_restored_original=True "
                "all_targets_original_after_cleanup=True "
                "provider_stats=%r"
                % (
                    self.identity,
                    stats,
                )
            )

            self.verify_final_button.setEnabled(
                False
            )
            self.status.setText(
                "PASS. Generic production-window Body Match integration is qualified."
            )

        except Exception as exc:
            log_line(
                "G11A_RESULT=FAIL error=%r"
                % exc
            )
            log_line(
                traceback.format_exc()
            )
            self.status.setText(
                "Final cleanup failed. Send the G11A log for review."
            )


def RunG11AProductionWindowBodyMatch():
    reset_log()
    log_line(
        "=" * 120
    )
    log_line(
        "G11A_PRODUCTION_WINDOW_BODY_MATCH START"
    )
    log_line(
        "mutation_policy=GENERIC_WINDOW_SOURCE_PLUS_QUEUED_ONE_UNDO_PER_GARMENT"
    )

    app = QtGui.QApplication.instance()

    if app is None:
        log_line(
            "G11A_RESULT=FAIL error='No QApplication instance.'"
        )
        return

    existing = getattr(
        app,
        G11A_APP_ATTR,
        None,
    )

    if existing is not None:
        try:
            existing.close()
        except Exception:
            pass

    try:
        window = G11AProductionWindow(
            qt_parent()
        )
        setattr(
            app,
            G11A_APP_ATTR,
            window,
        )
        window.show()
        window.raise_()
        window.activateWindow()

        log_line(
            "G11A_WINDOW_SHOWN=True initial_index=%d"
            % window.model_combo.currentIndex()
        )
        log_line(
            "=" * 120
        )

    except Exception as exc:
        log_line(
            "G11A_RESULT=FAIL error=%r"
            % exc
        )
        log_line(
            traceback.format_exc()
        )




# =================================================================================================
# 0.2.0 RC1 consolidated production layer
# =================================================================================================
PROD_VERSION = u"0.2.0-rc7-g18an-save-new-copy"
PROD_SCHEMA_VERSION = 3
PROD_LIBRARY_DIRNAME = u"SFM Character Preset Manager"
PROD_LEGACY_LIBRARY_DIRNAME = u"SFM Character Preset Tool"
PROD_LIBRARY_META_FILENAME = u"library.json"
PROD_LIBRARY_META_SCHEMA = 1
PROD_SEMANTIC_POLICY = u"master-category-operation-scope-v1"
PROD_APP_ATTR = "_sfm_character_slider_preset_tool_window"
PROD_OUTPUT_PATH = "C:\\Users\\Public\\Documents\\SFM_CSP_G18AN_SaveNewCopy.log"
PROD_RUN_ID = u"%s-pid%d" % (
    datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
    int(os.getpid()),
)
PROD_PID = int(os.getpid())
PROD_MASTER_GITHUB_URL = u"https://github.com/chadchan3d/sfm-animation-groups-master"

PROD_MASTER_REVIEW_WARNING_THRESHOLD = 20
PROD_MASTER_PROVIDER_WARNING_COPY = (
    u"Animation Groups Master sidecar is missing or out of date. "
    u"Rebuild the sidecar to use Body Presets, Expressions, and Clothing Fit."
)
PROD_MASTER_REVIEW_WARNING_COPY = (
    u"Many controls are unrecognized. Check that your Animation Groups Master "
    u"is current before reviewing them manually."
)


# ---------------------------------------------------------------------------
# CPM convergence Step 2b: canonical authority route.
#
# Production semantic authority comes only from the canonical shared broker
# through the CPM-owned authority adapter (cpm_authority_adapter, above the
# cpm_compat_v1 projection). The historical G18AN provider, discovery, fallback
# and parity machinery was removed in handoff section 22 item 6;
# get_semantic_provider remains only as an unconditional refusal
# (ProdHistoricalAuthorityDisabled) and is not reachable from this production
# route. Late helpers not yet migrated to a
# CPM Operation Authority Context (Step 3/4) fail closed via
# ProdCpmUnmigratedProvider instead of reaching any provider.
# ---------------------------------------------------------------------------

PROD_CPM_MAINMENU_RELATIVE_PARTS = ("usermod", "scripts", "sfm", "mainmenu", "ChadChan3D")
PROD_CPM_ADAPTER_MODULES = ("cpm_authority_adapter", "cpm_compat_v1_projection")


class ProdCpmAuthorityBootstrapError(RuntimeError):
    pass


class ProdCpmAuthorityNotMigrated(RuntimeError):
    pass


def prod_cpm_mainmenu_dir():
    """Same sys.executable-derived MAINMENU formula as the qualified
    Normalizer and the CPM adapter (duplicated intentionally: it must run
    before either can be imported; handoff section 16)."""
    game_root = os.path.dirname(os.path.abspath(sys.executable))
    return os.path.join(game_root, *PROD_CPM_MAINMENU_RELATIVE_PARTS)


def prod_cpm_import_adapter():
    """Import the CPM authority adapter from the canonical MAINMENU directory
    and refuse any same-named module loaded from anywhere else."""
    mainmenu_dir = prod_cpm_mainmenu_dir()
    if mainmenu_dir not in sys.path:
        sys.path.insert(0, mainmenu_dir)
    import cpm_authority_adapter as adapter_module
    expected = os.path.normcase(os.path.normpath(mainmenu_dir))
    for name in PROD_CPM_ADAPTER_MODULES:
        module = sys.modules.get(name)
        origin = os.path.dirname(os.path.abspath(getattr(module, "__file__", "") or ""))
        if module is None or os.path.normcase(os.path.normpath(origin)) != expected:
            raise ProdCpmAuthorityBootstrapError(
                "CPM authority module %r was not loaded from the canonical MAINMENU directory." % name
            )
    if adapter_module.locate_mainmenu_dir() != mainmenu_dir:
        raise ProdCpmAuthorityBootstrapError(
            "CPM authority adapter MAINMENU formula diverged from the application's."
        )
    return adapter_module


def prod_cpm_is_main_thread():
    app = QtCore.QCoreApplication.instance()
    return bool(
        app is not None
        and QtCore.QThread.currentThread() is app.thread()
    )


def prod_cpm_open_adapter():
    """A fresh canonical authority adapter for one bounded use. It holds no
    lease, view or provider; its generation is pinned on first descriptor
    or query. Raises on any bootstrap/identity failure."""
    adapter_module = prod_cpm_import_adapter()
    return adapter_module.open_canonical_authority(
        p01_master_path(),
        is_main_thread_fn=prod_cpm_is_main_thread,
    )


def prod_cpm_scope_generation_stale(scope):
    """True if the scope's authority generation is not the current one (or
    the current one cannot be established)."""
    try:
        current = prod_cpm_open_adapter().generation_descriptor()
    except Exception as exc:
        try:
            log_line("PROD_CPM_GENERATION_CHECK_FAILED error=%r" % (exc,))
        except Exception:
            pass
        return True
    authority = (scope or {}).get("authority") or {}
    return u(authority.get("provider_sha256")) != u(current.get("source_sha256"))


def prod_cpm_unmigrated_authority(helper):
    try:
        log_line("PROD_CPM_UNMIGRATED_AUTHORITY_REFUSED helper=%r" % (helper,))
    except Exception:
        pass
    raise ProdCpmAuthorityNotMigrated(
        "Semantic authority for %s is not available until its operation "
        "authority context is migrated." % helper
    )


class ProdCpmUnmigratedProvider(object):
    """Fail-closed stand-in for late helpers that still expect a provider
    (R6). Never falls back to the historical provider."""

    def __init__(self, helper):
        self.helper = helper

    def generation_descriptor(self):
        prod_cpm_unmigrated_authority(self.helper)

    def query_many(self, literals):
        prod_cpm_unmigrated_authority(self.helper)


def prod_cpm_health(status, reason, message=None, descriptor=None):
    return {
        "status": status,
        "reason": reason,
        "message": message,
        "descriptor": descriptor,
    }


# ---------------------------------------------------------------------------
# CPM convergence Step 3: CPM Operation Authority Context (handoff section 14).
#
# A semantic-dependent operation proves its scope's generation current once,
# at its post-prompt entry, and captures the result as detached plain data.
# Late helpers (persistence, postcommit readback, abort verification) consume
# that context; they never reopen or re-authorize semantic authority, and never
# reinterpret membership under a newer generation.
# ---------------------------------------------------------------------------

PROD_CPM_OPERATION_CONTEXT_SCHEMA = u"cpm-operation-authority-context-v1"
PROD_CPM_STALE_SCOPE_MESSAGE = "The selected model's semantic scope is stale. Reselect the model."


class ProdCpmOperationAuthorityError(RuntimeError):
    pass


def prod_cpm_pure_scalar_types():
    try:
        return (type(None), bool, int, long, float, unicode, str)  # noqa: F821 -- Python 2
    except NameError:
        return (type(None), bool, int, float, str, bytes)


PROD_CPM_PURE_SCALARS = prod_cpm_pure_scalar_types()


def prod_cpm_detached(value):
    """Deep copy of plain data; refuses anything else (views, leases,
    providers, adapters, iterators, closures, DME/Qt objects)."""
    if isinstance(value, dict):
        return dict(
            (prod_cpm_detached(k), prod_cpm_detached(v))
            for k, v in value.items()
        )
    if isinstance(value, list):
        return [prod_cpm_detached(v) for v in value]
    if isinstance(value, tuple):
        return tuple(prod_cpm_detached(v) for v in value)
    if isinstance(value, PROD_CPM_PURE_SCALARS):
        return value
    raise ProdCpmOperationAuthorityError(
        "Operation authority context refused a non-plain value of type %r."
        % type(value).__name__
    )


def prod_cpm_context_matches_identity(context, identity):
    try:
        ctx_identity = context["identity"]
        return (
            prod_norm(ctx_identity.get("model")) == prod_norm(identity.get("model"))
            and int(ctx_identity.get("checksum")) == int(identity.get("checksum"))
            and u(ctx_identity.get("animset_name")) == u(identity.get("animset_name"))
        )
    except Exception:
        return False


def prod_cpm_reclassify_outcome(literal, new_scope):
    """Separate the durable Reclassify edit from the classification the
    rebuilt current-authority scope now gives the literal."""
    row = None
    for item in (new_scope.get("semantic") or {}).get("rows") or []:
        if u(item.get("literal")) == u(literal):
            row = item
            break
    return {
        "durable_edit": True,
        "returned_to_review": literal in (new_scope.get("unresolved") or []),
        "current_semantic_class": None if row is None else row.get("semantic_class"),
        "current_semantic_status": None if row is None else row.get("semantic_status"),
    }


def prod_cpm_authorize_operation(identity, scope, kind, label):
    """Fresh post-prompt authorization for one semantic-dependent operation.
    Proves the scope's generation current through the canonical
    expected-generation route (same requested vocabulary as the scope), then
    returns the detached Operation Authority Context. A changed generation
    raises the existing stale-scope error before any write or mutation."""
    if not isinstance(scope, dict) or not isinstance(scope.get("authority"), dict):
        raise RuntimeError(PROD_CPM_STALE_SCOPE_MESSAGE)
    expected = u(scope["authority"].get("provider_sha256"))
    literals = sorted(
        set(
            u(row.get("literal"))
            for row in ((scope.get("semantic") or {}).get("rows") or [])
        )
    )
    adapter_module = prod_cpm_import_adapter()
    adapter = prod_cpm_open_adapter()
    failure = None
    provenance = None
    try:
        provenance = adapter.verify_current_generation(expected, literals)
    except adapter_module.CpmGenerationMismatch as exc:
        failure = (RuntimeError, PROD_CPM_STALE_SCOPE_MESSAGE, u(exc.reason))
    except adapter_module.CpmAuthorityUnavailable as exc:
        failure = (
            ProdCpmOperationAuthorityError,
            "Semantic authority is unavailable for this action (%s)." % exc.reason,
            u(exc.reason),
        )
    adapter = None
    if failure is not None:
        try:
            log_line(
                "PROD_CPM_OPERATION_AUTHORIZATION_REFUSED operation=%r reason=%r"
                % (label, failure[2])
            )
        except Exception:
            pass
        raise failure[0](failure[1])

    capture = prod_cpm_detached(provenance["provider_capture"])
    if u(capture.get("source_sha256")) != expected:
        raise RuntimeError(PROD_CPM_STALE_SCOPE_MESSAGE)
    membership = None
    if kind is not None:
        key = u"body" if kind == P03_KIND_BODY else u"expression"
        membership = {
            "kind": u(kind),
            "descriptors": prod_cpm_detached(scope[key]),
        }
    context = prod_cpm_detached({
        "schema": PROD_CPM_OPERATION_CONTEXT_SCHEMA,
        "operation": u(label),
        "identity": {
            "model": u(identity.get("model")),
            "checksum": int(identity.get("checksum")),
            "animset_name": u(identity.get("animset_name")),
        },
        "master_sha256": expected,
        "compatibility_identity": [u(item) for item in provenance["compatibility_identity"]],
        "provider_capture": capture,
        "runtime": {
            "api_version": u(adapter_module.EXPECTED_API_VERSION),
            "build_id": u(adapter_module.EXPECTED_BUILD_ID),
        },
        "consumer_kind": u(provenance["compatibility_identity"][2]),
        "projection_contract": u(capture.get("projection_contract")),
        "semantic_policy_revision": u(PROD_SEMANTIC_POLICY),
        "scope_authority": scope["authority"],
        "live_signature": scope.get("live_signature") or {},
        "membership": membership,
        "persistence": {
            "last_validated_provider": prod_provider_capture(capture),
            "semantic_policy": u(PROD_SEMANTIC_POLICY),
        },
    })
    provenance = None
    try:
        log_line(
            "PROD_CPM_OPERATION_AUTHORIZED operation=%r sha256=%s kind=%r membership=%r"
            % (
                label,
                expected,
                kind,
                None if membership is None else len(membership["descriptors"]),
            )
        )
    except Exception:
        pass
    return context



# ---------------------------------------------------------------------------
# CPM convergence Step 4: Clothing Fit per-target authority (handoff section 15).
#
# One user Fit owns one semantic generation, Gfit (the Master SHA; distinct
# from the integer fit_generation callback-cancellation counter). Each target
# stage proves Gfit with expected_generation over source + target vocabulary
# and holds that one stage lease through planning, native mutation and
# post-stage verification; it is released before the next target is queued.
# ---------------------------------------------------------------------------


class ProdCpmFitStop(RuntimeError):
    """Stops the current Fit without recording the current target as failed.
    ``unattempted_from`` is the first selected index left unattempted."""

    def __init__(self, message, unattempted_from):
        RuntimeError.__init__(self, message)
        self.unattempted_from = unattempted_from


def prod_cpm_fit_stage_vocabulary(fit_context, target_row):
    """Source requirements (the authorized Body membership) plus every
    target FLEX literal, which covers any unmatched subset queried by the
    existing warning logic during planning and post-stage verification."""
    source = set(
        ((fit_context.get("membership") or {}).get("descriptors") or {}).keys()
    )
    target = set(
        u(binding.get("literal"))
        for binding in p03_target_bindings(target_row["animset"])
    )
    return sorted(source | target)


def prod_cpm_open_fit_stage(fit_context, target_row, index):
    """Per-target Gfit proof. Returns a held stage authority, or raises
    ProdCpmFitStop (generation changed: the target does not begin) or
    ProdCpmOperationAuthorityError (authority unavailable)."""
    literals = prod_cpm_fit_stage_vocabulary(fit_context, target_row)
    adapter_module = prod_cpm_import_adapter()
    adapter = prod_cpm_open_adapter()
    failure = None
    stage = None
    try:
        stage = adapter.open_stage(fit_context["master_sha256"], literals)
    except adapter_module.CpmGenerationMismatch as exc:
        failure = (u"generation-mismatch", u(exc.reason))
    except adapter_module.CpmAuthorityUnavailable as exc:
        failure = (u"unavailable", u(exc.reason))
    adapter = None
    if failure is not None:
        try:
            log_line(
                "PROD_CPM_FIT_STAGE_REFUSED index=%d gfit=%s kind=%r reason=%r"
                % (index, fit_context["master_sha256"], failure[0], failure[1])
            )
        except Exception:
            pass
        if failure[0] == u"generation-mismatch":
            raise ProdCpmFitStop(
                PROD_CPM_STALE_SCOPE_MESSAGE,
                index,
            )
        raise ProdCpmOperationAuthorityError(
            "Semantic authority is unavailable for this Clothing Fit target (%s)." % failure[1]
        )
    try:
        log_line(
            "PROD_CPM_FIT_STAGE_OPEN index=%d gfit=%s literals=%d"
            % (index, stage.generation, len(literals))
        )
    except Exception:
        pass
    return stage


def prod_cpm_release_fit_stage(stage, index):
    """Release one stage lease; a release failure was already handed to the
    broker's durable registry, and stops the Fit before the next target."""
    if stage is None:
        return None
    failure = stage.release()
    try:
        log_line(
            "PROD_CPM_FIT_STAGE_RELEASED index=%d ok=%r"
            % (index, failure is None)
        )
    except Exception:
        pass
    if failure is not None:
        raise ProdCpmFitStop(
            "The Clothing Fit authority stage could not be released.",
            index + 1,
        )
    return None

def prod_probe_semantic_provider(identity):
    """Migrated authority health (R3): healthy only after canonical
    bootstrap, admission, authorization, cpm_compat_v1 contract, complete
    requested coverage and exact interpretation succeed for the selected
    model's live vocabulary. No whole-Master count thresholds. Returns
    (adapter or None, health)."""
    try:
        adapter = prod_cpm_open_adapter()
    except Exception as exc:
        health = prod_cpm_health(
            u"unavailable",
            u"cpm-authority-bootstrap-failed",
            u(exc),
        )
        try:
            log_line(
                "PROD_PROVIDER_HEALTH status=%r reason=%r error=%r"
                % (health["status"], health["reason"], health["message"])
            )
        except Exception:
            pass
        return None, health

    row = prod_resolve(
        identity
    )
    literals = sorted(
        set(
            item["literal"]
            for item in p01_all_supported_flex_bindings(row["animset"])
        )
    )
    assessed = adapter.assess_health(
        literals
    )
    if assessed.get("status") != u"healthy":
        health = prod_cpm_health(
            u"unavailable",
            u(assessed.get("reason")),
            u(assessed.get("message")),
        )
        try:
            log_line(
                "PROD_PROVIDER_HEALTH status=%r reason=%r error=%r"
                % (health["status"], health["reason"], health["message"])
            )
        except Exception:
            pass
        return None, health

    descriptor = dict(assessed.get("descriptor") or {})
    health = prod_cpm_health(
        u"healthy",
        u(assessed.get("reason")),
        None,
        descriptor,
    )
    advisory = assessed.get("advisory") or {}
    try:
        log_line(
            "PROD_PROVIDER_HEALTH status=%r reason=%r kind=%r sha256=%r "
            "requested_literals=%r master_unknown_literals=%r"
            % (
                health["status"],
                health["reason"],
                descriptor.get("provider_kind"),
                descriptor.get("source_sha256"),
                advisory.get("requested_literal_count"),
                advisory.get("master_unknown_literal_count"),
            )
        )
    except Exception:
        pass
    return adapter, health


def prod_norm(path):
    return g09a_normalize_model_path(path)


def prod_key(path):
    return g09a_library_key(path)


def prod_label(path):
    return g09a_safe_label(path)


def prod_identity_from_row(
    row,
):
    return {
        "model": row.get(
            "model"
        ),
        "checksum": row.get(
            "checksum"
        ),
        "animset_name": row.get(
            "animset_name"
        ),
    }


def prod_resolve_from_rows(
    identity,
    rows,
):
    """
    Resolve the selected model without treating Animation Set name as durable
    identity.

    Model path + checksum are the durable model/library identity.
    Animation Set names are user-editable SFM display metadata.

    If several otherwise-identical model instances exist, the current
    Animation Set name may disambiguate them. Remaining ambiguity fails closed.
    """
    durable = [
        row
        for row in rows
        if (
            row.get(
                "model"
            )
            == identity.get(
                "model"
            )
            and row.get(
                "checksum"
            )
            == identity.get(
                "checksum"
            )
        )
    ]

    if len(
        durable
    ) == 1:
        return durable[0]

    if not durable:
        raise RuntimeError(
            "Selected model could not be freshly re-resolved; "
            "found 0 model-path/checksum matches."
        )

    requested_name = identity.get(
        "animset_name"
    )
    named = [
        row
        for row in durable
        if row.get(
            "animset_name"
        )
        == requested_name
    ]

    if len(
        named
    ) == 1:
        return named[0]

    if len(
        named
    ) > 1:
        raise RuntimeError(
            "Selected model is ambiguous; found %d live instances with the "
            "same model, checksum, and Animation Set name."
            % len(
                named
            )
        )

    raise RuntimeError(
        "Selected model is ambiguous after its Animation Set name changed; "
        "found %d live instances with the same model and checksum. "
        "Refresh Model List and reselect the intended instance."
        % len(
            durable
        )
    )


def prod_resolve(
    identity,
):
    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        raise RuntimeError(
            "No current shot."
        )

    row = prod_resolve_from_rows(
        identity,
        p01_model_backed_animsets(
            shot
        ),
    )

    old_name = u(
        identity.get(
            "animset_name"
        )
        or u""
    )
    new_name = u(
        row.get(
            "animset_name"
        )
        or u""
    )

    if old_name != new_name:
        try:
            log_line(
                "G18AN_ANIMSET_RENAME_RESOLVED model=%r checksum=%r old=%r new=%r"
                % (
                    identity.get(
                        "model"
                    ),
                    identity.get(
                        "checksum"
                    ),
                    old_name,
                    new_name,
                )
            )
        except Exception:
            pass

    return row


class PROD_PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


_PROD_PRIVATE_WINDLL = {}


def prod_private_windll(name):
    """CPM-private Windows DLL handle for diagnostics (R14). Function objects
    reached through ctypes.windll.<dll> are shared by every consumer in the
    SFM process, so argtypes/restype set on them leak into, e.g., the
    production Normalizer's own telemetry. A private handle keeps CPM's
    prototypes local."""
    dll = _PROD_PRIVATE_WINDLL.get(name)
    if dll is None:
        dll = ctypes.WinDLL(name)
        _PROD_PRIVATE_WINDLL[name] = dll
    return dll


def prod_resource_snapshot(label):
    """Best-effort diagnostics only. Never changes scene state or forces GC."""
    ws_mb = None
    private_mb = None
    pagefile_mb = None
    handles = None
    gdi = None
    user = None
    top_widgets = None
    dialogs = None

    try:
        # R14: private handles, never the process-shared ctypes.windll ones.
        kernel32 = prod_private_windll("kernel32")
        psapi = prod_private_windll("psapi")
        user32 = prod_private_windll("user32")

        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p

        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(
                PROD_PROCESS_MEMORY_COUNTERS_EX
            ),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int

        kernel32.GetProcessHandleCount.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        kernel32.GetProcessHandleCount.restype = ctypes.c_int

        user32.GetGuiResources.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
        ]
        user32.GetGuiResources.restype = ctypes.c_ulong

        process = kernel32.GetCurrentProcess()

        counters = PROD_PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)

        if psapi.GetProcessMemoryInfo(
            process,
            ctypes.byref(counters),
            counters.cb,
        ):
            divisor = 1024.0 * 1024.0
            ws_mb = float(counters.WorkingSetSize) / divisor
            private_mb = float(counters.PrivateUsage) / divisor
            pagefile_mb = float(counters.PagefileUsage) / divisor

        handle_count = ctypes.c_ulong(0)
        if kernel32.GetProcessHandleCount(
            process,
            ctypes.byref(handle_count),
        ):
            handles = int(handle_count.value)

        try:
            gdi = int(
                user32.GetGuiResources(
                    process,
                    0,
                )
            )
            user = int(
                user32.GetGuiResources(
                    process,
                    1,
                )
            )
        except Exception:
            pass

    except Exception as exc:
        try:
            log_line(
                "PROD_RESOURCE_NATIVE_UNAVAILABLE label=%r error=%r"
                % (
                    u(label),
                    exc,
                )
            )
        except Exception:
            pass

    try:
        app = QtGui.QApplication.instance()
        if app is not None:
            widgets = list(
                app.topLevelWidgets()
            )
            top_widgets = len(
                widgets
            )
            dialogs = sum(
                1
                for widget in widgets
                if isinstance(
                    widget,
                    QtGui.QDialog,
                )
            )
    except Exception:
        pass

    try:
        log_line(
            "PROD_RESOURCE label=%r working_set_mb=%r private_commit_mb=%r "
            "pagefile_commit_mb=%r handles=%r gdi=%r user=%r top_widgets=%r dialogs=%r"
            % (
                u(label),
                ws_mb,
                private_mb,
                pagefile_mb,
                handles,
                gdi,
                user,
                top_widgets,
                dialogs,
            )
        )
    except Exception:
        pass



def prod_json_digest(record):
    payload = json.dumps(
        record,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        payload.encode("ascii")
    ).hexdigest()


def prod_binding_descriptor(binding):
    return {
        "literal": u(binding.get("literal")),
        "shape": u(binding.get("shape")),
        "global_key": tuple(
            binding.get("global_key")
            or ()
        ),
    }


def prod_live_binding_signatures(bindings):
    vocabulary = sorted(
        set(
            u(binding.get("literal"))
            for binding in bindings
        )
    )
    representation = sorted(
        (
            u(binding.get("literal")),
            u(binding.get("shape")),
            repr(
                tuple(
                    binding.get("global_key")
                    or ()
                )
            ),
        )
        for binding in bindings
    )

    vocabulary_sha = hashlib.sha256(
        repr(
            tuple(vocabulary)
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    representation_sha = hashlib.sha256(
        repr(
            tuple(representation)
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return {
        "vocabulary_sha256": vocabulary_sha,
        "representation_sha256": representation_sha,
    }


def prod_override_revision(profile):
    if not isinstance(
        profile,
        dict,
    ):
        overrides = {}
        revision = 0
    else:
        overrides = profile.get(
            "semantic_overrides"
        ) or {}
        try:
            revision = int(
                profile.get(
                    "semantic_override_revision"
                )
                or 0
            )
        except Exception:
            revision = 0

    payload = json.dumps(
        overrides,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(
        payload.encode(
            "ascii"
        )
    ).hexdigest()

    return u"%d:%s" % (
        revision,
        digest,
    )


def prod_current_provider_descriptor():
    # CPM Step 2b: fresh canonical observation of the current generation.
    return prod_cpm_open_adapter().generation_descriptor()


def prod_pure_semantic_row(row):
    return {
        "literal": u(
            row.get(
                "literal"
            )
        ),
        "live_binding_count": int(
            row.get(
                "live_binding_count"
            )
            or 0
        ),
        "live_shapes": list(
            row.get(
                "live_shapes"
            )
            or []
        ),
        "binding_ambiguous": bool(
            row.get(
                "binding_ambiguous"
            )
        ),
        "semantic_status": row.get(
            "semantic_status"
        ),
        "match_kind": row.get(
            "match_kind"
        ),
        "resolved_path": row.get(
            "resolved_path"
        ),
        "destinations": list(
            row.get(
                "destinations"
            )
            or []
        ),
        "master_spellings": list(
            row.get(
                "master_spellings"
            )
            or []
        ),
        "semantic_class": row.get(
            "semantic_class"
        ),
        "operation": row.get(
            "operation"
        ),
    }


def prod_scope_pure_assert(scope):
    forbidden_type_names = set(
        (
            u"DmeChannel",
            u"DmeFloatLog",
            u"DmeFloatLogLayer",
            u"DmeGlobalFlexControllerOperator",
            u"DmeTransform",
            u"DmeTransformControl",
        )
    )

    stack = [
        scope
    ]
    seen = set()

    while stack:
        value = stack.pop()
        marker = id(
            value
        )

        if marker in seen:
            continue

        seen.add(
            marker
        )

        if isinstance(
            value,
            dict,
        ):
            stack.extend(
                value.keys()
            )
            stack.extend(
                value.values()
            )
            continue

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            stack.extend(
                value
            )
            continue

        if isinstance(
            value,
            QtCore.QObject,
        ):
            raise RuntimeError(
                "Persistent semantic scope retained a Qt object."
            )

        try:
            value_type = typ(
                value
            )
        except Exception:
            value_type = None

        if (
            value_type in forbidden_type_names
            or (
                value_type is not None
                and (
                    u(value_type).startswith(
                        u"Dme"
                    )
                    or u(value_type)
                    == u"DmElement"
                )
            )
        ):
            raise RuntimeError(
                "Persistent semantic scope retained live DME state %r."
                % value_type
            )

    return True


def prod_context_token(identity):
    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        raise RuntimeError(
            "No current shot."
        )

    row = prod_resolve(
        identity
    )

    try:
        file_id = int(
            shot.GetFileId()
        )
    except Exception:
        file_id = u(
            shot.GetFileId()
        )

    return {
        "document_file_id": file_id,
        "shot_id": dme_id(
            shot
        ),
        "animset_id": dme_id(
            row[
                "animset"
            ]
        ),
        "model_instance_id": dme_id(
            row[
                "gm"
            ]
        ),
        "library_identity": dict(
            identity
        ),
    }


def prod_context_token_matches(token):
    if not isinstance(
        token,
        dict,
    ):
        return False

    identity = token.get(
        "library_identity"
    )

    if not isinstance(
        identity,
        dict,
    ):
        return False

    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        return False

    try:
        current_file_id = int(
            shot.GetFileId()
        )
    except Exception:
        try:
            current_file_id = u(
                shot.GetFileId()
            )
        except Exception:
            return False

    if (
        current_file_id
        != token.get(
            "document_file_id"
        )
        or dme_id(
            shot
        )
        != token.get(
            "shot_id"
        )
    ):
        return False

    try:
        row = prod_resolve(
            identity
        )
    except Exception:
        return False

    return (
        dme_id(
            row[
                "animset"
            ]
        )
        == token.get(
            "animset_id"
        )
        and dme_id(
            row[
                "gm"
            ]
        )
        == token.get(
            "model_instance_id"
        )
    )


def prod_validate_context_token(token):
    if not prod_context_token_matches(
        token
    ):
        raise RuntimeError(
            "The active shot or model instance changed. Reselect the model before continuing."
        )

    return True


def prod_selected_record_revision(item):
    if not isinstance(
        item,
        dict,
    ):
        return None

    record = item.get(
        "record"
    )

    if not isinstance(
        record,
        dict,
    ):
        return None

    return item.get(
        "revision"
    ) or prod_json_digest(
        record
    )


def prod_reread_selected_record(
    identity,
    item,
    kind,
):
    if (
        not isinstance(
            item,
            dict,
        )
        or item.get(
            "source"
        )
        != u"v3"
    ):
        raise RuntimeError(
            "Only current-library presets support revision checks."
        )

    path = item.get(
        "path"
    )

    if (
        not path
        or not os.path.isfile(
            path
        )
    ):
        raise RuntimeError(
            "Preset file no longer exists."
        )

    record = p02_read_json(
        path
    )
    prod_validate_preset(
        identity,
        record,
        kind,
    )

    cached = item.get(
        "record"
    ) or {}

    if (
        u(record.get("preset_id"))
        != u(cached.get("preset_id"))
        or u(record.get("kind"))
        != u(cached.get("kind"))
        or prod_json_digest(
            record
        )
        != prod_selected_record_revision(
            item
        )
    ):
        raise RuntimeError(
            "The selected preset changed on disk. Refresh Presets and select it again."
        )

    return record


def prod_outcome(
    phase,
    native_committed=False,
    durable_persisted=False,
    verified=None,
    ui_published=None,
    target_identity=None,
    path=None,
    error=None,
    recovery=None,
):
    normalized_phase = u(
        phase
    )

    legacy_outcome = normalized_phase
    if normalized_phase == u"committed-verified":
        legacy_outcome = u"committed"
    elif normalized_phase == u"aborted-precommit":
        legacy_outcome = u"aborted"

    return {
        "phase": normalized_phase,
        "outcome": legacy_outcome,
        "native_committed": bool(
            native_committed
        ),
        "durable_persisted": bool(
            durable_persisted
        ),
        "verified": verified,
        "ui_published": ui_published,
        "target_identity": (
            None
            if target_identity is None
            else dict(
                target_identity
            )
        ),
        "path": path,
        "error": (
            None
            if error is None
            else u(
                error
            )
        ),
        "recovery": recovery,
    }



def prod_scope_matches_identity(
    scope,
    identity,
    authority_context=None,
):
    if not isinstance(
        scope,
        dict,
    ):
        return False

    current = scope.get(
        "identity"
    )

    if not isinstance(
        current,
        dict,
    ):
        return False

    try:
        same_identity = (
            prod_norm(
                current.get(
                    "model"
                )
            )
            == prod_norm(
                identity.get(
                    "model"
                )
            )
            and int(
                current.get(
                    "checksum"
                )
            )
            == int(
                identity.get(
                    "checksum"
                )
            )
            and u(
                current.get(
                    "animset_name"
                )
            )
            == u(
                identity.get(
                    "animset_name"
                )
            )
        )

        if not same_identity:
            return False

        authority = scope.get(
            "authority"
        ) or {}
        if authority_context is not None:
            # CPM Step 3: verify against the operation's pinned authority;
            # never reopen or re-authorize it.
            if not prod_cpm_context_matches_identity(
                authority_context,
                identity,
            ):
                return False
            provider = {
                "provider_generation": authority_context[
                    "provider_capture"
                ].get("provider_generation"),
                "source_sha256": authority_context.get(
                    "master_sha256"
                ),
            }
        else:
            provider = prod_current_provider_descriptor()

        if (
            int(
                authority.get(
                    "provider_generation"
                )
                or 0
            )
            != int(
                provider.get(
                    "provider_generation"
                )
                or 0
            )
            or u(
                authority.get(
                    "provider_sha256"
                )
            )
            != u(
                provider.get(
                    "source_sha256"
                )
            )
            or u(
                authority.get(
                    "semantic_policy_revision"
                )
            )
            != u(
                PROD_SEMANTIC_POLICY
            )
        ):
            return False

        profile = prod_load_character(
            identity
        )

        if u(
            authority.get(
                "override_revision"
            )
        ) != u(
            prod_override_revision(
                profile
            )
        ):
            return False

        return True

    except Exception:
        return False


def prod_live_bindings_for_cached_scope(
    identity,
    scope,
    kind,
    authority_context=None,
):
    """Fresh live FLEX bindings using pure cached semantic membership. With an
    Operation Authority Context, the check is pinned to that operation's
    authorized generation and membership (CPM Step 3)."""
    if not prod_scope_matches_identity(
        scope,
        identity,
        authority_context=authority_context,
    ):
        raise RuntimeError(
            "The selected model's semantic scope is stale. Reselect the model."
        )

    if kind == P03_KIND_BODY:
        expected_names = set(
            scope[
                "body"
            ].keys()
        )
    elif kind == P03_KIND_EXPRESSION:
        expected_names = set(
            scope[
                "expression"
            ].keys()
        )
    else:
        raise RuntimeError(
            "Unsupported preset kind."
        )

    row = prod_resolve(
        identity
    )
    bindings = p01_all_supported_flex_bindings(
        row[
            "animset"
        ]
    )
    signatures = prod_live_binding_signatures(
        bindings
    )

    expected_signature = scope.get(
        "live_signature"
    ) or {}

    if (
        signatures.get(
            "vocabulary_sha256"
        )
        != expected_signature.get(
            "vocabulary_sha256"
        )
        or signatures.get(
            "representation_sha256"
        )
        != expected_signature.get(
            "representation_sha256"
        )
    ):
        raise RuntimeError(
            "The selected model's live flex vocabulary changed. Reselect the model."
        )

    by_literal = {}

    for binding in bindings:
        by_literal.setdefault(
            binding[
                "literal"
            ],
            [],
        ).append(
            binding
        )

    accepted = {}

    descriptor_map = scope[
        "body"
        if kind == P03_KIND_BODY
        else "expression"
    ]
    if authority_context is not None:
        membership = authority_context.get("membership") or {}
        if (
            u(membership.get("kind")) != u(kind)
            or set((membership.get("descriptors") or {}).keys()) != expected_names
        ):
            raise RuntimeError(
                PROD_CPM_STALE_SCOPE_MESSAGE
            )
        descriptor_map = membership["descriptors"]

    for literal in sorted(
        expected_names
    ):
        rows = by_literal.get(
            literal,
            [],
        )

        if len(
            rows
        ) != 1:
            raise RuntimeError(
                "Current live binding for %r is no longer unique."
                % literal
            )

        observed_descriptor = prod_binding_descriptor(
            rows[
                0
            ]
        )
        expected_descriptor = descriptor_map.get(
            literal
        )

        if (
            not isinstance(
                expected_descriptor,
                dict,
            )
            or observed_descriptor
            != expected_descriptor
        ):
            raise RuntimeError(
                "Current representation for %r changed. Reselect the model."
                % literal
            )

        accepted[
            literal
        ] = rows[
            0
        ]

    return {
        "row": row,
        "accepted": accepted,
        "provider": ProdCpmUnmigratedProvider(
            "prod_live_bindings_for_cached_scope"
        ),
        "live_signature": signatures,
    }


def prod_assert_unique_preset_name_items(
    items,
    kind,
    name_value,
):
    requested = prod_preset_name_key(
        name_value
    )

    if not requested:
        raise RuntimeError(
            "Enter a preset name."
        )

    for item in list(
        items
        or []
    ):
        record = item.get(
            "record"
        ) or {}
        existing = u(
            record.get("name")
            or record.get("preset_id")
            or u""
        )

        if prod_preset_name_key(
            existing
        ) == requested:
            label = (
                "Body Preset"
                if kind == P03_KIND_BODY
                else "Expression"
            )
            raise RuntimeError(
                "A %s named '%s' already exists. Choose a different name."
                % (
                    label,
                    u(name_value).strip(),
                )
            )

    return True


def prod_library_root():
    return os.path.join(p02_documents(), PROD_LIBRARY_DIRNAME)


def prod_legacy_library_root():
    return os.path.join(p02_documents(), PROD_LEGACY_LIBRARY_DIRNAME)


def prod_prepare_library_root():
    old_root = prod_legacy_library_root()
    new_root = prod_library_root()

    if os.path.isdir(old_root) and not os.path.exists(new_root):
        os.rename(old_root, new_root)
        if os.path.exists(old_root) or not os.path.isdir(new_root):
            raise RuntimeError("Preset library folder rename could not be verified.")
        try:
            log_line("PROD_LIBRARY_ROOT_MIGRATION=PASS old=%r new=%r" % (old_root, new_root))
        except Exception:
            pass
    elif os.path.isdir(old_root) and os.path.isdir(new_root):
        try:
            log_line("PROD_LIBRARY_ROOT_MIGRATION=SKIP reason='both-exist' old=%r new=%r" % (old_root, new_root))
        except Exception:
            pass

    p02_ensure_dir(new_root)
    return new_root


def prod_paths(identity):
    root = prod_library_root()
    char = os.path.join(root, u"Characters", prod_label(identity["model"]))
    return {
        "root": root,
        "char": char,
        "profile": os.path.join(char, u"character.json"),
        "library_meta": os.path.join(char, PROD_LIBRARY_META_FILENAME),
        "body": os.path.join(char, P03_BODY_FOLDER),
        "expression": os.path.join(char, P03_EXPRESSION_FOLDER),
    }


def prod_favorite_key(record):
    return u"%s:%s" % (u(record.get("kind") or u""), u(record.get("preset_id") or u""))


def prod_load_library_meta(identity):
    path = prod_paths(identity)["library_meta"]
    if not os.path.isfile(path):
        return {"schema_version": PROD_LIBRARY_META_SCHEMA, "record_kind": u"library-metadata", "favorites": []}
    record = p02_read_json(path)
    if not isinstance(record, dict) or record.get("schema_version") != PROD_LIBRARY_META_SCHEMA or record.get("record_kind") != u"library-metadata":
        raise RuntimeError("Preset library metadata is unsupported.")
    favorites = record.get("favorites")
    if not isinstance(favorites, list):
        raise RuntimeError("Preset library Favorites data is malformed.")
    record["favorites"] = sorted(set(u(value) for value in favorites if u(value)))
    return record


def prod_save_library_meta(
    identity,
    record,
    phase_callback=None,
):
    path = prod_paths(
        identity
    )[
        "library_meta"
    ]
    p02_ensure_dir(
        os.path.dirname(
            path
        )
    )
    p02_safe_write_json(
        path,
        record,
    )

    if phase_callback is not None:
        phase_callback(
            "durable-commit",
            {
                "path": path,
                "kind": u"library-metadata",
            },
        )

    loaded = p02_read_json(
        path
    )

    if loaded != record:
        raise RuntimeError(
            "Preset library metadata did not read back exactly."
        )

    if phase_callback is not None:
        phase_callback(
            "durable-verified",
            {
                "path": path,
                "kind": u"library-metadata",
            },
        )

    return loaded


def prod_is_favorite(identity, record):
    key = prod_favorite_key(record)
    if not key or key == u":":
        return False
    return key in set(prod_load_library_meta(identity).get("favorites") or [])


def prod_set_favorite(
    identity,
    record,
    enabled,
    phase_callback=None,
):
    key = prod_favorite_key(
        record
    )

    if (
        not key
        or key
        == u":"
    ):
        raise RuntimeError(
            "Preset identity is missing."
        )

    meta = prod_load_library_meta(
        identity
    )
    favorites = set(
        u(
            value
        )
        for value in (
            meta.get(
                "favorites"
            )
            or []
        )
    )

    if enabled:
        favorites.add(
            key
        )
    else:
        favorites.discard(
            key
        )

    meta[
        "favorites"
    ] = sorted(
        favorites
    )

    loaded = prod_save_library_meta(
        identity,
        meta,
        phase_callback=phase_callback,
    )

    try:
        log_line(
            "PROD_FAVORITE_SET model=%r preset=%r enabled=%r"
            % (
                identity[
                    "model"
                ],
                key,
                bool(
                    enabled
                ),
            )
        )
    except Exception:
        pass

    return {
        "enabled": bool(
            enabled
        ),
        "meta": loaded,
    }


def prod_effective_recent_stamp(record):
    return u(record.get("modified_at") or record.get("created_at") or u"")


def prod_item_display_name(item):
    return u(item["record"].get("name") or item["record"].get("preset_id") or u"Preset")


def prod_item_matches_search(item, query):
    needle = u(query or u"").strip().lower()
    if not needle:
        return True
    record = item["record"]
    haystack = u" ".join([prod_item_display_name(item), u(record.get("preset_id") or u"")]).lower()
    return needle in haystack


def prod_sort_items(items, sort_mode):
    rows = list(items)
    if u(sort_mode) == u"Recent":
        rows.sort(key=lambda item: (prod_effective_recent_stamp(item["record"]), prod_item_display_name(item).lower()), reverse=True)
    else:
        rows.sort(key=lambda item: (prod_item_display_name(item).lower(), 0 if item.get("source") == u"v3" else 1, u(item["record"].get("preset_id") or u"")))
    return rows


def prod_provider_capture(provider_or_descriptor):
    if isinstance(provider_or_descriptor, dict):
        d = dict(provider_or_descriptor)
    else:
        d = provider_or_descriptor.generation_descriptor()

    return {
        "provider_contract": d.get("provider_contract"),
        "source_sha256": d.get("source_sha256"),
        "fold_policy": d.get("fold_policy"),
        "provider_generation": int(
            d.get("provider_generation")
            or 0
        ),
    }


def prod_is_scale_model(identity):
    return (
        prod_norm(identity["model"]) == prod_norm(KRYSTAL_MODEL)
        and int(identity["checksum"]) == int(KRYSTAL_CHECKSUM)
    )


def prod_character_record(identity, authority_context=None):
    return {
        "schema_version": PROD_SCHEMA_VERSION,
        "record_kind": u"character",
        "library_key": prod_key(
            identity[
                "model"
            ]
        ),
        "identity_policy": u"normalized-model-path-sha256-v1",
        "display_name": u(
            identity[
                "animset_name"
            ]
        ),
        "model_ref": {
            "path": prod_norm(
                identity[
                    "model"
                ]
            ),
            "last_validated_checksum": int(
                identity[
                    "checksum"
                ]
            ),
        },
        "default_body_preset_id": None,
        "semantic_overrides": {},
        "semantic_override_revision": 0,
        "structural_capabilities": {},
        "created_at": p03_now_stamp(),
        "updated_at": p03_now_stamp(),
        "semantic_policy": PROD_SEMANTIC_POLICY,
        "last_validated_provider": prod_provider_capture(
            ProdCpmUnmigratedProvider("prod_character_record")
            if authority_context is None
            else authority_context["persistence"]["last_validated_provider"]
        ),
    }


def prod_load_character(identity):
    path = prod_paths(identity)["profile"]
    if not os.path.isfile(path):
        return None
    r = p02_read_json(path)
    if r.get("schema_version") != 3 or r.get("record_kind") != u"character":
        raise RuntimeError("Current character library schema is unsupported.")
    if r.get("library_key") != prod_key(identity["model"]):
        raise RuntimeError("Current character library belongs to another model.")
    mr = r.get("model_ref")
    if not isinstance(mr, dict) or mr.get("path") != prod_norm(identity["model"]):
        raise RuntimeError("Current character library model path differs from the selected model.")
    return r


def prod_ensure_character(identity, authority_context=None):
    r = prod_load_character(identity)
    if r is None:
        r = prod_character_record(identity, authority_context=authority_context)
    else:
        r["display_name"] = u(identity["animset_name"])
        r.setdefault("model_ref", {})["last_validated_checksum"] = int(identity["checksum"])
        r.setdefault("semantic_overrides", {})
        r.setdefault("semantic_override_revision", 0)
        r["structural_capabilities"] = {}
        r["updated_at"] = p03_now_stamp()
        r["last_validated_provider"] = prod_provider_capture(
            ProdCpmUnmigratedProvider("prod_ensure_character")
            if authority_context is None
            else authority_context["persistence"]["last_validated_provider"]
        )
    p02_safe_write_json(prod_paths(identity)["profile"], r)
    return p02_read_json(prod_paths(identity)["profile"])


def prod_scope(
    identity,
    provider=None,
):
    row = prod_resolve(
        identity
    )
    if provider is None:
        provider = prod_cpm_open_adapter()
    provider_descriptor = provider.generation_descriptor()
    snap = semantic_snapshot_for_model_row(
        row,
        provider,
    )

    by_literal = {}
    for binding in snap[
        "bindings"
    ]:
        by_literal.setdefault(
            binding[
                "literal"
            ],
            [],
        ).append(
            binding
        )

    expr_names = set(
        snap[
            "semantic"
        ][
            "accepted_expression_literals"
        ]
    )
    body_names = set(
        snap[
            "semantic"
        ][
            "accepted_body_literals"
        ]
    )
    rows = snap[
        "semantic"
    ][
        "rows"
    ]
    misses = set(
        item[
            "literal"
        ]
        for item in rows
        if item.get(
            "semantic_class"
        )
        == u"master-miss"
    )
    conflicts = sorted(
        item[
            "literal"
        ]
        for item in rows
        if item.get(
            "semantic_status"
        )
        == P01_STATUS_CONFLICT
    )

    profile = prod_load_character(
        identity
    )
    overrides = (
        profile.get(
            "semantic_overrides",
            {},
        )
        if profile
        else {}
    )
    applied = {}
    excluded = set()

    for literal, override in overrides.items():
        if (
            literal not in misses
            or not isinstance(
                override,
                dict,
            )
            or override.get(
                "applies_when"
            )
            != u"master-miss"
        ):
            continue

        decision = u(
            override.get(
                "decision"
            )
        )

        if decision == u"expression":
            expr_names.add(
                literal
            )
            body_names.discard(
                literal
            )
        elif decision == u"body":
            body_names.add(
                literal
            )
            expr_names.discard(
                literal
            )
        elif decision == u"exclude":
            expr_names.discard(
                literal
            )
            body_names.discard(
                literal
            )
            excluded.add(
                literal
            )
        else:
            continue

        applied[
            literal
        ] = decision

    def descriptors(
        names,
        label,
    ):
        out = {}

        for literal in sorted(
            names
        ):
            live_rows = by_literal.get(
                literal,
                [],
            )

            if len(
                live_rows
            ) != 1:
                raise RuntimeError(
                    "%s literal %r has %d live bindings."
                    % (
                        label,
                        literal,
                        len(
                            live_rows
                        ),
                    )
                )

            out[
                literal
            ] = prod_binding_descriptor(
                live_rows[
                    0
                ]
            )

        return out

    semantic_rows = [
        prod_pure_semantic_row(
            semantic_row
        )
        for semantic_row in rows
    ]
    semantic_counts = dict(
        snap[
            "semantic"
        ][
            "counts"
        ]
    )
    signatures = prod_live_binding_signatures(
        snap[
            "bindings"
        ]
    )

    scope = {
        "schema": u"csp-semantic-scope-pure-v1",
        "identity": dict(
            identity
        ),
        "authority": {
            "provider_generation": int(
                provider_descriptor.get(
                    "provider_generation"
                )
                or 0
            ),
            "provider_sha256": provider_descriptor.get(
                "source_sha256"
            ),
            "semantic_policy_revision": PROD_SEMANTIC_POLICY,
            "override_revision": prod_override_revision(
                profile
            ),
        },
        "provider_descriptor": dict(
            provider_descriptor
        ),
        "live_signature": signatures,
        "semantic": {
            "rows": semantic_rows,
            "counts": semantic_counts,
        },
        "expression": descriptors(
            expr_names,
            "Expression",
        ),
        "body": descriptors(
            body_names,
            "Body",
        ),
        "unresolved": sorted(
            misses
            - set(
                applied.keys()
            )
        ),
        "conflicts": conflicts,
        "overrides": dict(
            applied
        ),
        "excluded": sorted(
            excluded
        ),
    }

    prod_scope_pure_assert(
        scope
    )

    return scope


def prod_set_override(
    identity,
    literal,
    decision,
    scope=None,
    phase_callback=None,
    authority_context=None,
):
    if scope is None:
        scope = prod_scope(
            identity
        )

    # CPM Step 3: the durable Review edit consumes a fresh operation
    # authorization of the scope's generation.
    if authority_context is None:
        authority_context = prod_cpm_authorize_operation(
            identity,
            scope,
            None,
            u"Review Flex",
        )

    if not prod_scope_matches_identity(
        scope,
        identity,
        authority_context=authority_context,
    ):
        raise RuntimeError(
            "The selected model's semantic scope is stale. Reselect the model."
        )

    if literal not in scope[
        "unresolved"
    ]:
        raise RuntimeError(
            "Only a current genuine Master MISS can receive a model-local decision."
        )

    if decision not in (
        u"expression",
        u"body",
        u"exclude",
    ):
        raise RuntimeError(
            "Unsupported review decision."
        )

    record = prod_ensure_character(
        identity,
        authority_context=authority_context,
    )
    overrides = record.setdefault(
        "semantic_overrides",
        {},
    )
    overrides[
        literal
    ] = {
        "source": u"user",
        "applies_when": u"master-miss",
        "decision": decision,
        "created_at": p03_now_stamp(),
    }

    try:
        current_revision = int(
            record.get(
                "semantic_override_revision"
            )
            or 0
        )
    except Exception:
        current_revision = 0

    record[
        "semantic_override_revision"
    ] = current_revision + 1
    record[
        "updated_at"
    ] = p03_now_stamp()

    path = prod_paths(
        identity
    )[
        "profile"
    ]
    p02_safe_write_json(
        path,
        record,
    )

    if phase_callback is not None:
        phase_callback(
            "durable-commit",
            {
                "path": path,
                "kind": u"semantic-override",
                "literal": literal,
                "decision": decision,
            },
        )

    loaded = p02_read_json(
        path
    )

    if loaded != record:
        raise RuntimeError(
            "Saved flex choice did not read back exactly."
        )

    if phase_callback is not None:
        phase_callback(
            "durable-verified",
            {
                "path": path,
                "kind": u"semantic-override",
                "literal": literal,
                "decision": decision,
            },
        )

    try:
        log_line(
            "PROD_OVERRIDE_SET model=%r literal=%r decision=%r override_revision=%r"
            % (
                identity[
                    "model"
                ],
                literal,
                decision,
                loaded.get(
                    "semantic_override_revision"
                ),
            )
        )
    except Exception:
        pass

    return loaded



def prod_clear_override(
    identity,
    literal,
    scope=None,
    phase_callback=None,
    authority_context=None,
):
    if scope is None:
        scope = prod_scope(
            identity
        )

    # CPM Step 3: the durable Review edit consumes a fresh operation
    # authorization of the scope's generation.
    if authority_context is None:
        authority_context = prod_cpm_authorize_operation(
            identity,
            scope,
            None,
            u"Reclassify Flex",
        )

    if not prod_scope_matches_identity(
        scope,
        identity,
        authority_context=authority_context,
    ):
        raise RuntimeError(
            "The selected model's semantic scope is stale. Reselect the model."
        )

    if literal not in scope[
        "overrides"
    ]:
        raise RuntimeError(
            "Only a current reviewed choice can be reclassified."
        )

    record = prod_ensure_character(
        identity,
        authority_context=authority_context,
    )
    overrides = record.setdefault(
        "semantic_overrides",
        {},
    )
    current = overrides.get(
        literal
    )

    if (
        not isinstance(
            current,
            dict,
        )
        or current.get(
            "source"
        )
        != u"user"
        or current.get(
            "applies_when"
        )
        != u"master-miss"
    ):
        raise RuntimeError(
            "This reviewed choice is not a user-created Master-miss classification."
        )

    del overrides[
        literal
    ]

    try:
        current_revision = int(
            record.get(
                "semantic_override_revision"
            )
            or 0
        )
    except Exception:
        current_revision = 0

    record[
        "semantic_override_revision"
    ] = current_revision + 1
    record[
        "updated_at"
    ] = p03_now_stamp()

    path = prod_paths(
        identity
    )[
        "profile"
    ]
    p02_safe_write_json(
        path,
        record,
    )

    if phase_callback is not None:
        phase_callback(
            "durable-commit",
            {
                "path": path,
                "kind": u"semantic-override-clear",
                "literal": literal,
            },
        )

    loaded = p02_read_json(
        path
    )

    if loaded != record:
        raise RuntimeError(
            "Reclassification change did not read back exactly."
        )

    if literal in (
        loaded.get(
            "semantic_overrides"
        )
        or {}
    ):
        raise RuntimeError(
            "Reclassification change did not remove the saved choice."
        )

    if phase_callback is not None:
        phase_callback(
            "durable-verified",
            {
                "path": path,
                "kind": u"semantic-override-clear",
                "literal": literal,
            },
        )

    try:
        log_line(
            "PROD_OVERRIDE_CLEAR model=%r literal=%r override_revision=%r"
            % (
                identity[
                    "model"
                ],
                literal,
                loaded.get(
                    "semantic_override_revision"
                ),
            )
        )
    except Exception:
        pass

    return loaded

def prod_preset_dir(identity, kind):
    return prod_paths(identity)["body" if kind == P03_KIND_BODY else "expression"]


def prod_safe_name(value):
    v = u(value)
    for ch in u'<>:"/\\|?*':
        v = v.replace(ch, u"_")
    return v.strip(u" .") or u"Preset"


def prod_unique_path(identity, kind, name_value, preset_id):
    folder = prod_preset_dir(identity, kind)
    p02_ensure_dir(folder)
    stem = prod_safe_name(name_value)[:100] + u"--" + u(preset_id)[:12]
    p = os.path.join(folder, stem + u".json")
    n = 2
    while os.path.exists(p):
        p = os.path.join(folder, stem + u"-" + unicode(n) + u".json"); n += 1
        if n > 999:
            raise RuntimeError("Could not allocate preset filename.")
    return p


def prod_validate_preset(
    identity,
    record,
    kind=None,
):
    if (
        not isinstance(
            record,
            dict,
        )
        or record.get(
            "schema_version"
        )
        != 3
        or record.get(
            "record_kind"
        )
        != u"preset"
    ):
        raise RuntimeError(
            "Preset schema is unsupported."
        )

    preset_id = u(
        record.get(
            "preset_id"
        )
        or u""
    ).strip()

    migration_source = record.get(
        "migration_source"
    )

    if not preset_id:
        raise RuntimeError(
            "Preset identity is missing or malformed."
        )

    if (
        not preset_id.startswith(
            u"preset-"
        )
        and not isinstance(
            migration_source,
            dict,
        )
    ):
        raise RuntimeError(
            "Preset identity is missing or malformed."
        )

    record_kind = u(
        record.get(
            "kind"
        )
        or u""
    )

    if record_kind not in (
        P03_KIND_BODY,
        P03_KIND_EXPRESSION,
    ):
        raise RuntimeError(
            "Preset kind is unsupported."
        )

    if record.get(
        "character_key"
    ) != prod_key(
        identity[
            "model"
        ]
    ):
        raise RuntimeError(
            "Preset belongs to another model library."
        )

    if (
        kind is not None
        and record_kind
        != kind
    ):
        raise RuntimeError(
            "Preset kind does not match this library."
        )

    model_ref = record.get(
        "model_ref"
    )

    if (
        not isinstance(
            model_ref,
            dict,
        )
        or model_ref.get(
            "path"
        )
        != prod_norm(
            identity[
                "model"
            ]
        )
    ):
        raise RuntimeError(
            "Preset belongs to another model path."
        )

    try:
        int(
            model_ref.get(
                "capture_checksum"
            )
        )
    except Exception:
        raise RuntimeError(
            "Preset model reference is malformed."
        )

    values = record.get(
        "values"
    )

    if not isinstance(
        values,
        dict,
    ):
        raise RuntimeError(
            "Preset values are missing."
        )

    for logical_id, value_record in values.items():
        logical_id = u(
            logical_id
        )

        if logical_id == P04_SCALE_LOGICAL_ID:
            # Historical unsupported test field is rejected later with its
            # established user-facing compatibility message.
            continue

        if not logical_id.startswith(
            u"flex."
        ):
            raise RuntimeError(
                "Preset contains an unsupported mutation-bearing value."
            )

        if not isinstance(
            value_record,
            dict,
        ):
            raise RuntimeError(
                "Saved FLEX data is malformed."
            )

        representation = u(
            value_record.get(
                "representation"
            )
            or u""
        )

        if representation == u"MONO":
            if (
                set(
                    value_record.keys()
                )
                != set(
                    (
                        "representation",
                        "mono",
                    )
                )
                or as_float(
                    value_record.get(
                        "mono"
                    )
                )
                is None
            ):
                raise RuntimeError(
                    "Saved MONO FLEX data is malformed or non-finite."
                )

        elif representation == u"STEREO":
            if (
                set(
                    value_record.keys()
                )
                != set(
                    (
                        "representation",
                        "left",
                        "right",
                    )
                )
                or as_float(
                    value_record.get(
                        "left"
                    )
                )
                is None
                or as_float(
                    value_record.get(
                        "right"
                    )
                )
                is None
            ):
                raise RuntimeError(
                    "Saved STEREO FLEX data is malformed or non-finite."
                )

        else:
            raise RuntimeError(
                "Saved FLEX representation is unsupported."
            )

    for timestamp_key in (
        "created_at",
        "modified_at",
    ):
        timestamp = record.get(
            timestamp_key
        )

        if (
            timestamp is not None
            and not u(
                timestamp
            ).strip()
        ):
            raise RuntimeError(
                "Preset timestamp is malformed."
            )

    return True


def prod_legacy_descriptor(identity):
    root = os.path.join(prod_paths(identity)["root"], u"Characters")
    model = prod_norm(identity["model"])
    if model == prod_norm(P01_MODEL_PATH):
        return {"profile_id": P02_PROFILE_ID, "root": os.path.join(root, P02_CHARACTER_FOLDER)}
    if model == prod_norm(KRYSTAL_MODEL):
        return {"profile_id": P04_PROFILE_ID, "root": os.path.join(root, P04_CHARACTER_FOLDER)}
    return None


def prod_convert_legacy_record(identity, record):
    values = record.get("values")
    if not isinstance(values, dict):
        raise RuntimeError("Legacy preset values are malformed.")
    converted = {}
    for key, value in values.items():
        key = u(key)
        if key.startswith(u"body.flex."):
            target = u"flex." + key[len(u"body.flex."):]
        elif key.startswith(u"flex.") or key == P04_SCALE_LOGICAL_ID:
            target = key
        else:
            raise RuntimeError("Legacy preset contains unsupported value key %r." % key)
        if target in converted:
            raise RuntimeError("Legacy preset conversion produced duplicate value key %r." % target)
        converted[target] = value
    return {
        "schema_version": 3,
        "record_kind": u"preset",
        "preset_id": u(record["preset_id"]),
        "character_key": prod_key(identity["model"]),
        "kind": u(record["kind"]),
        "name": u(record.get("name") or record["preset_id"]),
        "model_ref": {"path": prod_norm(identity["model"]), "capture_checksum": int(identity["checksum"])},
        "capture_semantic_policy": u"legacy-v2-preserved-values-v1",
        "migration_source": {"schema_version": 2, "profile_id": u(record["profile_id"]), "preset_id": u(record["preset_id"])},
        "values": converted,
    }


def prod_discover(
    identity,
    kind,
):
    out = []
    current_ids = set()

    for path in p03_json_candidates(
        prod_preset_dir(
            identity,
            kind,
        )
    ):
        try:
            record = p02_read_json(
                path
            )
            prod_validate_preset(
                identity,
                record,
                kind,
            )
        except Exception as exc:
            try:
                log_line(
                    "PROD_LIBRARY_MALFORMED path=%r error=%r"
                    % (
                        path,
                        exc,
                    )
                )
            except Exception:
                pass
            continue

        preset_id = u(
            record.get(
                "preset_id"
            )
        )

        if preset_id in current_ids:
            raise RuntimeError(
                "Preset library contains duplicate preset ID %r."
                % preset_id
            )

        current_ids.add(
            preset_id
        )
        out.append(
            {
                "path": path,
                "record": record,
                "source": u"v3",
                "revision": prod_json_digest(
                    record
                ),
            }
        )

    desc = prod_legacy_descriptor(
        identity
    )

    if (
        desc is not None
        and os.path.isdir(
            desc[
                "root"
            ]
        )
    ):
        for path in p03_json_candidates(
            desc[
                "root"
            ]
        ):
            if (
                os.path.basename(
                    path
                ).lower()
                == "character.json"
            ):
                continue

            try:
                legacy = p02_read_json(
                    path
                )

                if (
                    legacy.get(
                        "schema_version"
                    )
                    != 2
                    or legacy.get(
                        "profile_id"
                    )
                    != desc[
                        "profile_id"
                    ]
                ):
                    continue

                if (
                    u(
                        legacy.get(
                            "kind"
                        )
                    )
                    != kind
                    or not u(
                        legacy.get(
                            "preset_id"
                        )
                    )
                ):
                    continue

                if u(
                    legacy.get(
                        "preset_id"
                    )
                ) in current_ids:
                    continue

                converted = prod_convert_legacy_record(
                    identity,
                    legacy,
                )

            except Exception as exc:
                try:
                    log_line(
                        "PROD_LEGACY_SKIP path=%r error=%r"
                        % (
                            path,
                            exc,
                        )
                    )
                except Exception:
                    pass
                continue

            out.append(
                {
                    "path": path,
                    "record": converted,
                    "source": u"legacy-v2",
                    "revision": prod_json_digest(
                        converted
                    ),
                }
            )

    out.sort(
        key=lambda item: (
            u(
                item[
                    "record"
                ].get(
                    "name"
                )
                or u""
            ).lower(),
            (
                0
                if item.get(
                    "source"
                )
                == u"v3"
                else 1
            ),
            u(
                item[
                    "record"
                ].get(
                    "preset_id"
                )
                or u""
            ),
        )
    )

    return out


def prod_assert_unique_library_ids(
    body_items,
    expression_items,
):
    seen = {}

    for item in list(
        body_items
    ) + list(
        expression_items
    ):
        if item.get(
            "source"
        ) != u"v3":
            continue

        preset_id = u(
            item.get(
                "record",
                {},
            ).get(
                "preset_id"
            )
            or u""
        )

        if not preset_id:
            continue

        previous = seen.get(
            preset_id
        )

        if previous is not None:
            raise RuntimeError(
                "Preset library contains duplicate preset ID %r across current libraries."
                % preset_id
            )

        seen[
            preset_id
        ] = item.get(
            "path"
        )

    return True



def prod_move_current_preset_to_trash(
    identity,
    item,
    phase_callback=None,
):
    if not isinstance(
        item,
        dict,
    ):
        raise RuntimeError(
            "Preset selection is invalid."
        )

    if item.get(
        "source"
    ) != u"v3":
        raise RuntimeError(
            "Legacy presets are read-only. Only current-library presets can be deleted."
        )

    path = item.get(
        "path"
    )

    if (
        not path
        or not os.path.isfile(
            path
        )
    ):
        raise RuntimeError(
            "Preset file no longer exists."
        )

    record = prod_reread_selected_record(
        identity,
        item,
        u(
            item.get(
                "record",
                {},
            ).get(
                "kind"
            )
        ),
    )

    expected_dirs = (
        os.path.normcase(
            os.path.abspath(
                prod_preset_dir(
                    identity,
                    P03_KIND_BODY,
                )
            )
        ),
        os.path.normcase(
            os.path.abspath(
                prod_preset_dir(
                    identity,
                    P03_KIND_EXPRESSION,
                )
            )
        ),
    )
    source_dir = os.path.normcase(
        os.path.abspath(
            os.path.dirname(
                path
            )
        )
    )

    if source_dir not in expected_dirs:
        raise RuntimeError(
            "Preset is outside the selected model's current library."
        )

    trash = os.path.join(
        prod_paths(
            identity
        )[
            "root"
        ],
        P03_TRASH_DIRNAME,
    )
    p02_ensure_dir(
        trash
    )

    target = os.path.join(
        trash,
        p03_now_stamp()
        + u"--"
        + unicode(
            uuid.uuid4().hex
        )[:8]
        + u"--"
        + os.path.basename(
            path
        ),
    )

    result = ctypes.windll.kernel32.MoveFileExW(
        ctypes.c_wchar_p(
            path
        ),
        ctypes.c_wchar_p(
            target
        ),
        0,
    )

    if not result:
        code = ctypes.windll.kernel32.GetLastError()
        raise RuntimeError(
            "Could not move preset to Trash (Windows error %d)."
            % code
        )

    if phase_callback is not None:
        phase_callback(
            "durable-commit",
            {
                "path": target,
                "source_path": path,
                "kind": u"trash-move",
                "preset_id": record.get(
                    "preset_id"
                ),
            },
        )

    if (
        os.path.exists(
            path
        )
        or not os.path.isfile(
            target
        )
    ):
        raise RuntimeError(
            "Preset Trash move could not be verified."
        )

    if phase_callback is not None:
        phase_callback(
            "durable-verified",
            {
                "path": target,
                "source_path": path,
                "kind": u"trash-move",
                "preset_id": record.get(
                    "preset_id"
                ),
            },
        )

    try:
        prod_set_favorite(
            identity,
            record,
            False,
        )
    except Exception as exc:
        try:
            log_line(
                "PROD_FAVORITE_CLEANUP_WARNING preset=%r error=%r"
                % (
                    record.get(
                        "preset_id"
                    ),
                    exc,
                )
            )
        except Exception:
            pass

    try:
        profile = prod_load_character(
            identity
        )

        if (
            profile is not None
            and record.get(
                "kind"
            )
            == P03_KIND_BODY
            and profile.get(
                "default_body_preset_id"
            )
            == record.get(
                "preset_id"
            )
        ):
            profile[
                "default_body_preset_id"
            ] = None
            profile[
                "updated_at"
            ] = p03_now_stamp()
            p02_safe_write_json(
                prod_paths(
                    identity
                )[
                    "profile"
                ],
                profile,
            )

    except Exception as exc:
        try:
            log_line(
                "PROD_DELETE_PROFILE_CLEANUP_WARNING preset=%r error=%r"
                % (
                    record.get(
                        "preset_id"
                    ),
                    exc,
                )
            )
        except Exception:
            pass

    try:
        log_line(
            "PROD_DELETE=PASS model=%r kind=%r name=%r source=%r trash=%r"
            % (
                identity[
                    "model"
                ],
                record.get(
                    "kind"
                ),
                record.get(
                    "name"
                ),
                path,
                target,
            )
        )
    except Exception:
        pass

    return target


def prod_preset_name_key(value):
    return u(value).strip().lower()


def prod_assert_unique_preset_name(identity, kind, name_value):
    requested = prod_preset_name_key(name_value)

    if not requested:
        raise RuntimeError("Enter a preset name.")

    matches = []

    for item in prod_discover(identity, kind):
        existing = u(
            item["record"].get("name")
            or item["record"].get("preset_id")
            or u""
        )

        if prod_preset_name_key(existing) == requested:
            matches.append({
                "name": existing,
                "source": item.get("source"),
                "path": item.get("path"),
            })

    if matches:
        label = (
            "Body Preset"
            if kind == P03_KIND_BODY
            else "Expression"
        )

        raise RuntimeError(
            "A %s named '%s' already exists. Choose a different name."
            % (
                label,
                u(name_value).strip(),
            )
        )

    return True


def prod_capture_scale(identity):
    if not prod_is_scale_model(identity):
        return None

    row = prod_resolve(identity)
    shot = sfmApp.GetShotAtCurrentTime()

    if shot is None:
        raise RuntimeError("No current shot.")

    # The exact-qualified Krystal adapter has two safe structural states:
    #
    #   1. Existing complete Head Scale topology:
    #      capture its evaluated physical multiplier.
    #
    #   2. Cleanly absent Head Scale topology:
    #      capture the implicit neutral physical multiplier (1.0) WITHOUT
    #      mutating the scene.  The already-qualified Apply path may later
    #      provision the native Head Scale graph transactionally if required.
    #
    # Partial/conflicting topology still fails closed in p04_scale_topology_probe.
    probe = p04_scale_topology_probe(
        row,
        shot,
    )

    if probe["kind"] == "absent":
        log_line(
            "PROD_SCALE_CAPTURE kind='clean-absent' "
            "physical_multiplier=1.0 mutation=False"
        )
        return {
            "representation": u"scale_multiplier",
            "value": 1.0,
        }

    binding = probe["binding"]
    state = probe["baseline"]

    if (
        binding is None
        or state is None
        or probe.get("origin") == "UNSUPPORTED"
    ):
        raise RuntimeError(
            "Head Scale is outside the qualified static contract."
        )

    if not scale_evaluated_matches(
        binding,
        state,
        state["source"],
    ):
        raise RuntimeError(
            "Head Scale is not fully coherent/evaluated."
        )

    log_line(
        "PROD_SCALE_CAPTURE kind='existing' "
        "physical_multiplier=%r mutation=False"
        % float(
            state["bone_scale"]
        )
    )

    return {
        "representation": u"scale_multiplier",
        "value": float(
            state["bone_scale"]
        ),
    }



# -------------------------------------------------------------------------------------------------
# Generic bone-scale production layer.
# Qualified by G12A-G12F:
# - ordinary SFM bone scaling is channel-driven through <bone>_scale -> lerp(value,0,10)
# - coherent static state is ONE_KEY_ZERO
# - existing-control writes are transaction-safe with exact native Undo
# - missing-control creation is generic and undoes exactly back to clean absence
# - complete physical bone-scale maps can coexist atomically with Body FLEX in one Apply transaction
# -------------------------------------------------------------------------------------------------

PROD_BS_BONE_RE = re.compile(r"^bone\s+(\d+)\s+\((.+)\)$", re.I)
PROD_BS_LO = 0.0
PROD_BS_HI = 10.0
PROD_BS_NEUTRAL_NATIVE = 0.1
PROD_BS_TEST_PHYSICAL = 1.25

def prod_bs_animset_controls(animset):
    candidates = {}

    for control in r26_animset_controls(animset):
        candidates[(handle(control), ptr(control))] = control

    for control in subtree_controls(root_group(animset)):
        candidates[(handle(control), ptr(control))] = control

    return list(candidates.values())

def prod_bs_group_paths(animset, control):
    paths = []

    for row in group_inventory(animset):
        for member in arr(row["group"], "controls"):
            if same_dme(member, control):
                paths.append(row["path"])
                break

    return sorted(set(paths))

def prod_bs_scale_channels(animset, shot, transform):
    clip = get_channels_clip(animset, shot)
    rows = []

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue

        destination = attr_value(channel, "toElement")

        if destination is None or not same_dme(destination, transform):
            continue

        if u(attr_value(channel, "toAttribute")) != u"scale":
            continue

        source = attr_value(channel, "fromElement")

        try:
            log = channel.GetLog()
        except Exception:
            log = attr_value(channel, "log")

        count = None
        empty = None
        current = None
        key0_time = None
        key0_value = None

        if log is not None:
            try:
                empty = bool(log.IsEmpty())
            except Exception:
                pass

            try:
                current = as_float(
                    log.GetValue(
                        channel.GetCurrentTime()
                    )
                )
            except Exception:
                pass

            try:
                layer = log.GetLayer(0)
            except Exception:
                try:
                    layers = arr(log, "layers")
                    layer = layers[0] if layers else None
                except Exception:
                    layer = None

            if layer is not None:
                count = key_count(layer)

                if count == 1:
                    try:
                        key0_time = seconds(
                            layer.GetKeyTime(0)
                        )
                    except Exception:
                        pass

                    try:
                        key0_value = as_float(
                            layer.GetKeyValue(0)
                        )
                    except Exception:
                        pass

        rows.append({
            "channel_id": dme_id(channel),
            "channel_name": name(channel),
            "mode": attr_value(channel, "mode"),
            "source_id": dme_id(source),
            "source_type": typ(source),
            "source_name": name(source),
            "source_attribute": u(
                attr_value(channel, "fromAttribute")
            ),
            "log_type": typ(log),
            "key_count": count,
            "is_empty": empty,
            "evaluated": current,
            "key0_time": key0_time,
            "key0_value": key0_value,
        })

    return rows

def prod_bs_bone_rows(model_row):
    animset = model_row["animset"]
    shot = model_row["shot"]

    by_identity = {}
    transform_owners = {}
    raw = []

    for control in prod_bs_animset_controls(animset):
        if typ(control) != u"DmeTransformControl":
            continue

        try:
            casted = vs.CastElementAsDmeTransformControl(control)
        except Exception:
            casted = control

        if casted is None or typ(casted) != u"DmeTransformControl":
            continue

        try:
            transform = casted.GetTransform()
        except Exception:
            transform = None

        if transform is None or typ(transform) != u"DmeTransform":
            continue

        transform_name = u(name(transform) or u"")
        match = PROD_BS_BONE_RE.match(transform_name)

        if not match:
            continue

        bone_index = int(match.group(1))
        bone_name = u(match.group(2))
        control_name = u(name(casted) or u"")

        scale_attr = get_attr(transform, "scale")
        scale_present = scale_attr is not None

        if scale_present:
            scale_value = as_float(
                attr_value(
                    transform,
                    "scale",
                )
            )
        else:
            scale_value = 1.0

        channels = prod_bs_scale_channels(
            animset,
            shot,
            transform,
        )

        identity = (
            bone_index,
            bone_name.lower(),
        )

        row = {
            "bone_index": bone_index,
            "bone_name": bone_name,
            "control_name": control_name,
            "control_matches_bone_name": (
                control_name.lower()
                == bone_name.lower()
            ),
            "control_id": dme_id(casted),
            "transform_name": transform_name,
            "transform_id": dme_id(transform),
            "group_paths": prod_bs_group_paths(
                animset,
                casted,
            ),
            "scale_attr_present": scale_present,
            "scale_value": scale_value,
            "scale_channel_count": len(channels),
            "scale_channels": channels,
        }

        raw.append(row)
        by_identity.setdefault(
            identity,
            [],
        ).append(row)
        transform_owners.setdefault(
            row["transform_id"],
            [],
        ).append(row)

    result = []

    for row in raw:
        identity = (
            row["bone_index"],
            row["bone_name"].lower(),
        )

        duplicate_identity = (
            len(
                by_identity.get(
                    identity,
                    [],
                )
            )
            != 1
        )

        shared_transform = (
            len(
                transform_owners.get(
                    row["transform_id"],
                    [],
                )
            )
            != 1
        )

        if duplicate_identity or shared_transform:
            classification = "AMBIGUOUS_IDENTITY"

        elif row["scale_channel_count"] > 0:
            classification = "CHANNEL_DRIVEN_SCALE"

        elif not row["scale_attr_present"]:
            classification = "IMPLICIT_NEUTRAL"

        elif (
            row["scale_value"] is not None
            and close_enough(
                row["scale_value"],
                1.0,
            )
        ):
            classification = "DIRECT_NEUTRAL"

        elif row["scale_value"] is not None:
            classification = "DIRECT_NON_NEUTRAL"

        else:
            classification = "UNREADABLE_DIRECT_SCALE"

        row["duplicate_identity"] = duplicate_identity
        row["shared_transform"] = shared_transform
        row["classification"] = classification
        row["portable_identity"] = {
            "model": model_row["model"],
            "checksum": model_row["checksum"],
            "bone_index": row["bone_index"],
            "bone_name": row["bone_name"],
        }

        result.append(row)

    result.sort(
        key=lambda row: (
            row["bone_index"],
            row["bone_name"].lower(),
        )
    )

    return result

def prod_bs_log_state(channel):
    try:
        log = channel.GetLog()
    except Exception:
        log = attr_value(channel, "log")

    result = {
        "log_type": typ(log),
        "layer_count": None,
        "key_count": None,
        "is_empty": None,
        "key0_time": None,
        "key0_value": None,
        "evaluated": None,
    }

    if log is None:
        return result

    try:
        result["layer_count"] = layer_count(log)
    except Exception:
        pass

    try:
        result["is_empty"] = bool(log.IsEmpty())
    except Exception:
        pass

    try:
        result["evaluated"] = as_float(
            log.GetValue(
                channel.GetCurrentTime()
            )
        )
    except Exception:
        pass

    try:
        layer = get_layer(log, 0)
    except Exception:
        layer = None

    if layer is not None:
        result["key_count"] = key_count(layer)

        if result["key_count"] == 1:
            try:
                result["key0_time"] = seconds(
                    layer.GetKeyTime(0)
                )
            except Exception:
                pass

            try:
                result["key0_value"] = as_float(
                    layer.GetKeyValue(0)
                )
            except Exception:
                pass

    return result

def prod_bs_control_membership(animset, control):
    animset_hits = 0
    group_paths = []

    for item in r26_animset_controls(animset):
        if same_dme(item, control):
            animset_hits += 1

    for row in group_inventory(animset):
        for member in arr(row["group"], "controls"):
            if same_dme(member, control):
                group_paths.append(row["path"])
                break

    return {
        "animset_control_hits": animset_hits,
        "group_paths": sorted(set(group_paths)),
    }

def prod_bs_trace_scaled_bone(model_row, bone_row):
    animset = model_row["animset"]
    shot = model_row["shot"]
    clip = get_channels_clip(animset, shot)

    # Resolve the exact native bone transform from the already-read inventory row.
    transform_matches = []

    for control in prod_bs_animset_controls(animset):
        if typ(control) != u"DmeTransformControl":
            continue

        try:
            casted = vs.CastElementAsDmeTransformControl(control)
        except Exception:
            casted = control

        if casted is None or typ(casted) != u"DmeTransformControl":
            continue

        try:
            transform = casted.GetTransform()
        except Exception:
            transform = None

        if transform is None or typ(transform) != u"DmeTransform":
            continue

        if dme_id(transform) == bone_row["transform_id"]:
            transform_matches.append(
                (casted, transform)
            )

    if len(transform_matches) != 1:
        raise RuntimeError(
            "Expected one live transform for %r; found %d."
            % (
                bone_row["portable_identity"],
                len(transform_matches),
            )
        )

    bone_control, transform = transform_matches[0]

    output_matches = []

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue

        destination = attr_value(channel, "toElement")

        if destination is None or not same_dme(destination, transform):
            continue

        if u(attr_value(channel, "toAttribute")) != u"scale":
            continue

        output_matches.append(channel)

    if len(output_matches) != 1:
        raise RuntimeError(
            "Expected one output channel to %r.scale; found %d."
            % (
                bone_row["portable_identity"],
                len(output_matches),
            )
        )

    output = output_matches[0]
    expression = attr_value(output, "fromElement")

    if expression is None or typ(expression) != u"DmeExpressionOperator":
        raise RuntimeError(
            "Scale output source is not a DmeExpressionOperator."
        )

    if u(attr_value(output, "fromAttribute")) != u"result":
        raise RuntimeError(
            "Scale output does not source expression.result."
        )

    expression_text = u(
        attr_value(expression, "expr")
        or u""
    )
    normalized_expr = expression_text.replace(
        " ",
        "",
    ).lower()

    lo = as_float(
        attr_value(
            expression,
            "lo",
        )
    )
    hi = as_float(
        attr_value(
            expression,
            "hi",
        )
    )
    expression_value = as_float(
        attr_value(
            expression,
            "value",
        )
    )
    expression_result = as_float(
        attr_value(
            expression,
            "result",
        )
    )

    input_matches = []

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue

        destination = attr_value(channel, "toElement")

        if destination is None or not same_dme(destination, expression):
            continue

        if u(attr_value(channel, "toAttribute")) != u"value":
            continue

        input_matches.append(channel)

    input_rows = []

    for channel in input_matches:
        source = attr_value(channel, "fromElement")
        source_attr_name = u(
            attr_value(
                channel,
                "fromAttribute",
            )
            or u""
        )

        source_value = (
            as_float(
                attr_value(
                    source,
                    source_attr_name,
                )
            )
            if source is not None and source_attr_name
            else None
        )

        membership = (
            prod_bs_control_membership(
                animset,
                source,
            )
            if source is not None
            else {
                "animset_control_hits": 0,
                "group_paths": [],
            }
        )

        input_rows.append({
            "channel_id": dme_id(channel),
            "channel_name": name(channel),
            "mode": attr_value(channel, "mode"),
            "source_id": dme_id(source),
            "source_type": typ(source),
            "source_name": name(source),
            "source_attribute": source_attr_name,
            "source_value": source_value,
            "source_default_value": (
                as_float(
                    attr_value(
                        source,
                        "defaultValue",
                    )
                )
                if source is not None
                else None
            ),
            "source_channel_id": (
                dme_id(
                    attr_value(
                        source,
                        "channel",
                    )
                )
                if source is not None
                else None
            ),
            "membership": membership,
            "log": prod_bs_log_state(
                channel
            ),
        })

    physical_scale = as_float(
        attr_value(
            transform,
            "scale",
        )
    )

    expected_physical = None

    if (
        normalized_expr == u"lerp(value,lo,hi)"
        and expression_value is not None
        and lo is not None
        and hi is not None
    ):
        expected_physical = (
            lo
            + expression_value
            * (
                hi - lo
            )
        )

    topology_match = (
        normalized_expr
        == u"lerp(value,lo,hi)"
        and lo is not None
        and hi is not None
        and not close_enough(
            lo,
            hi,
        )
        and len(input_rows) == 1
        and input_rows[0][
            "source_type"
        ] == u"DmElement"
        and input_rows[0][
            "source_attribute"
        ] == u"value"
        and input_rows[0][
            "membership"
        ][
            "animset_control_hits"
        ] == 1
        and int(
            attr_value(
                output,
                "mode",
            )
        )
        == 1
    )

    physical_matches = (
        expected_physical is not None
        and physical_scale is not None
        and close_enough(
            expected_physical,
            physical_scale,
        )
    )

    return {
        "portable_identity": bone_row[
            "portable_identity"
        ],
        "bone_control_id": dme_id(
            bone_control
        ),
        "bone_group_paths": prod_bs_group_paths(
            animset,
            bone_control,
        ),
        "transform_id": dme_id(
            transform
        ),
        "physical_scale": physical_scale,
        "output": {
            "id": dme_id(output),
            "name": name(output),
            "mode": attr_value(
                output,
                "mode",
            ),
            "log": prod_bs_log_state(
                output
            ),
        },
        "expression": {
            "id": dme_id(
                expression
            ),
            "name": name(
                expression
            ),
            "expr": expression_text,
            "normalized_expr": normalized_expr,
            "lo": lo,
            "hi": hi,
            "value": expression_value,
            "result": expression_result,
        },
        "input_count": len(
            input_rows
        ),
        "inputs": input_rows,
        "expected_physical": expected_physical,
        "physical_matches_lerp": physical_matches,
        "generic_lerp_topology": topology_match,
    }

def prod_bs_find_model_row(identity):
    matches = []

    for row in p03_model_animsets():
        if (
            u(row["model"]).lower()
            == u(identity["model"]).lower()
            and int(row["checksum"])
            == int(identity["checksum"])
        ):
            matches.append(row)

    if len(matches) != 1:
        raise RuntimeError(
            "The selected model could not be resolved uniquely."
        )

    return matches[0]

def prod_bs_find_bone_row(model_row, identity):
    matches = []

    for row in prod_bs_bone_rows(model_row):
        if (
            int(row["bone_index"])
            == int(identity["bone_index"])
            and u(row["bone_name"]).lower()
            == u(identity["bone_name"]).lower()
        ):
            matches.append(row)

    if len(matches) != 1:
        raise RuntimeError(
            "The selected bone could not be resolved uniquely."
        )

    return matches[0]

def prod_bs_resolve_binding(identity):
    model_row = prod_bs_find_model_row(identity)
    bone_row = prod_bs_find_bone_row(
        model_row,
        identity,
    )

    trace = prod_bs_trace_scaled_bone(
        model_row,
        bone_row,
    )

    if not trace["generic_lerp_topology"]:
        raise RuntimeError(
            "This bone scale is outside the qualified generic topology."
        )

    if not trace["physical_matches_lerp"]:
        raise RuntimeError(
            "This bone scale is not evaluating coherently."
        )

    animset = model_row["animset"]
    shot = model_row["shot"]
    clip = get_channels_clip(
        animset,
        shot,
    )

    bone_controls = []

    for control in prod_bs_animset_controls(animset):
        if typ(control) != u"DmeTransformControl":
            continue

        try:
            casted = vs.CastElementAsDmeTransformControl(control)
        except Exception:
            casted = control

        if casted is None:
            continue

        try:
            transform = casted.GetTransform()
        except Exception:
            transform = None

        if transform is None:
            continue

        if dme_id(transform) == bone_row["transform_id"]:
            bone_controls.append(
                (casted, transform)
            )

    if len(bone_controls) != 1:
        raise RuntimeError(
            "The selected bone transform is ambiguous."
        )

    bone_control, transform = bone_controls[0]

    outputs = []

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue

        destination = attr_value(
            channel,
            "toElement",
        )

        if destination is None or not same_dme(
            destination,
            transform,
        ):
            continue

        if u(
            attr_value(
                channel,
                "toAttribute",
            )
        ) != u"scale":
            continue

        outputs.append(channel)

    if len(outputs) != 1:
        raise RuntimeError(
            "The selected bone does not have one scale output channel."
        )

    output = outputs[0]
    expression = attr_value(
        output,
        "fromElement",
    )

    if (
        expression is None
        or typ(expression)
        != u"DmeExpressionOperator"
    ):
        raise RuntimeError(
            "The selected bone scale output is not expression-driven."
        )

    inputs = []

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue

        destination = attr_value(
            channel,
            "toElement",
        )

        if destination is None or not same_dme(
            destination,
            expression,
        ):
            continue

        if u(
            attr_value(
                channel,
                "toAttribute",
            )
        ) != u"value":
            continue

        inputs.append(channel)

    if len(inputs) != 1:
        raise RuntimeError(
            "The selected bone scale does not have one input channel."
        )

    input_channel = inputs[0]
    control = attr_value(
        input_channel,
        "fromElement",
    )

    if (
        control is None
        or typ(control) != u"DmElement"
        or u(
            attr_value(
                input_channel,
                "fromAttribute",
            )
        ) != u"value"
    ):
        raise RuntimeError(
            "The selected bone scale input control is unsupported."
        )

    try:
        input_log = input_channel.GetLog()
    except Exception:
        input_log = attr_value(
            input_channel,
            "log",
        )

    if input_log is None:
        raise RuntimeError(
            "The selected bone scale input log is unavailable."
        )

    input_layer = get_layer(
        input_log,
        0,
    )

    if input_layer is None:
        raise RuntimeError(
            "The selected bone scale input layer is unavailable."
        )

    source_attr = get_attr(
        control,
        "value",
    )

    if source_attr is None:
        raise RuntimeError(
            "The selected bone scale value attribute is unavailable."
        )

    lo = as_float(
        attr_value(
            expression,
            "lo",
        )
    )
    hi = as_float(
        attr_value(
            expression,
            "hi",
        )
    )

    return {
        "identity": dict(identity),
        "model_row": model_row,
        "bone_row": bone_row,
        "shot": shot,
        "animset": animset,
        "bone_control": bone_control,
        "transform": transform,
        "output": output,
        "expression": expression,
        "input_channel": input_channel,
        "control": control,
        "source_attr": source_attr,
        "input_log": input_log,
        "input_layer": input_layer,
        "lo": lo,
        "hi": hi,
    }

def prod_bs_snapshot(binding):
    count = key_count(
        binding["input_layer"]
    )

    try:
        empty = bool(
            binding["input_log"].IsEmpty()
        )
    except Exception:
        empty = None

    key_time = None
    key_value = None

    if count == 1:
        key_time = seconds(
            binding["input_layer"].GetKeyTime(0)
        )
        key_value = float(
            binding["input_layer"].GetKeyValue(0)
        )

    return {
        "source": as_float(
            attr_value(
                binding["control"],
                "value",
            )
        ),
        "default": as_float(
            attr_value(
                binding["control"],
                "defaultValue",
            )
        ),
        "expr_input": as_float(
            attr_value(
                binding["expression"],
                "value",
            )
        ),
        "expr_result": as_float(
            attr_value(
                binding["expression"],
                "result",
            )
        ),
        "physical_scale": as_float(
            attr_value(
                binding["transform"],
                "scale",
            )
        ),
        "key_count": count,
        "is_empty": empty,
        "key_time": key_time,
        "key_value": key_value,
        "input_mode": attr_value(
            binding["input_channel"],
            "mode",
        ),
        "output_mode": attr_value(
            binding["output"],
            "mode",
        ),
        "control_id": dme_id(
            binding["control"]
        ),
        "input_channel_id": dme_id(
            binding["input_channel"]
        ),
        "input_log_id": dme_id(
            binding["input_log"]
        ),
        "input_layer_id": dme_id(
            binding["input_layer"]
        ),
        "expression_id": dme_id(
            binding["expression"]
        ),
        "output_id": dme_id(
            binding["output"]
        ),
        "transform_id": dme_id(
            binding["transform"]
        ),
    }

def prod_bs_static_one_key_zero(snapshot):
    return (
        snapshot["key_count"] == 1
        and snapshot["is_empty"] is False
        and close_enough(
            snapshot["key_time"],
            0.0,
        )
        and close_enough(
            snapshot["key_value"],
            snapshot["source"],
        )
        and int(
            snapshot["input_mode"]
        ) == 3
        and int(
            snapshot["output_mode"]
        ) == 1
    )

def prod_bs_expected_physical(binding, native_value):
    return (
        binding["lo"]
        + float(native_value)
        * (
            binding["hi"]
            - binding["lo"]
        )
    )

def prod_bs_authored_matches(binding, snapshot, native_value):
    return (
        prod_bs_static_one_key_zero(
            snapshot
        )
        and close_enough(
            snapshot["source"],
            native_value,
        )
        and close_enough(
            snapshot["expr_input"],
            native_value,
        )
        and close_enough(
            snapshot["key_value"],
            native_value,
        )
    )

def prod_bs_evaluated_matches(binding, snapshot, native_value):
    expected = prod_bs_expected_physical(
        binding,
        native_value,
    )

    return (
        prod_bs_authored_matches(
            binding,
            snapshot,
            native_value,
        )
        and close_enough(
            snapshot["expr_result"],
            expected,
        )
        and close_enough(
            snapshot["physical_scale"],
            expected,
        )
    )

def prod_bs_names(bone_name):
    literal = u(bone_name) + u"_scale"
    return {
        "literal": literal,
        "expression": literal + u"_rescale",
        "output": u"scaled_" + literal + u"_channel",
    }

def prod_bs_group_rows(animset, control):
    rows = []

    for row in group_inventory(animset):
        if any(
            same_dme(member, control)
            for member in arr(
                row["group"],
                "controls",
            )
        ):
            rows.append(row)

    return rows

def prod_bs_exact_control_hits(animset, shot, literal):
    candidates = {}

    def add(control):
        if control is None or name(control) != literal:
            return
        candidates[
            (
                handle(control),
                ptr(control),
            )
        ] = control

    for control in r26_animset_controls(animset):
        add(control)

    for control in subtree_controls(
        root_group(animset)
    ):
        add(control)

    clip = get_channels_clip(
        animset,
        shot,
    )

    for channel in r26_clip_channels(clip):
        if typ(channel) != u"DmeChannel":
            continue
        add(
            attr_value(
                channel,
                "fromElement",
            )
        )

    try:
        add(
            animset.FindControl(
                b(literal)
            )
        )
    except Exception:
        try:
            add(
                animset.FindControl(
                    literal
                )
            )
        except Exception:
            pass

    return list(
        candidates.values()
    )

def prod_bs_named_channels(clip, literal):
    return [
        channel
        for channel in r26_clip_channels(clip)
        if (
            typ(channel) == u"DmeChannel"
            and name(channel) == literal
        )
    ]

def prod_bs_clean_candidate(model_row, bone_row):
    animset = model_row["animset"]
    shot = model_row["shot"]

    if (
        bone_row["classification"]
        != "IMPLICIT_NEUTRAL"
    ):
        return None

    if not bone_row[
        "control_matches_bone_name"
    ]:
        return None

    # Resolve exact transform control + transform.
    matches = []

    for control in prod_bs_animset_controls(animset):
        if typ(control) != u"DmeTransformControl":
            continue

        try:
            casted = vs.CastElementAsDmeTransformControl(
                control
            )
        except Exception:
            casted = control

        if casted is None:
            continue

        try:
            transform = casted.GetTransform()
        except Exception:
            transform = None

        if transform is None:
            continue

        if (
            dme_id(transform)
            == bone_row["transform_id"]
        ):
            matches.append(
                (
                    casted,
                    transform,
                )
            )

    if len(matches) != 1:
        return None

    bone_control, transform = matches[0]
    groups = prod_bs_group_rows(
        animset,
        bone_control,
    )

    if len(groups) != 1:
        return None

    names = prod_bs_names(
        bone_row[
            "bone_name"
        ]
    )
    clip = get_channels_clip(
        animset,
        shot,
    )

    if get_attr(
        transform,
        "scale",
    ) is not None:
        return None

    if prod_bs_exact_control_hits(
        animset,
        shot,
        names[
            "literal"
        ],
    ):
        return None

    if r26_named_operator_count(
        animset,
        names[
            "expression"
        ],
    ) != 0:
        return None

    if prod_bs_named_channels(
        clip,
        names[
            "literal"
        ],
    ):
        return None

    if prod_bs_named_channels(
        clip,
        names[
            "output"
        ],
    ):
        return None

    return {
        "identity": {
            "model": model_row[
                "model"
            ],
            "checksum": model_row[
                "checksum"
            ],
            "bone_index": bone_row[
                "bone_index"
            ],
            "bone_name": bone_row[
                "bone_name"
            ],
        },
        "animset_name": model_row[
            "name"
        ],
        "group_path": groups[0][
            "path"
        ],
    }

def prod_bs_resolve_clean_fixture(identity):
    model_row = prod_bs_find_model_row(
        identity
    )
    bone_row = prod_bs_find_bone_row(
        model_row,
        identity,
    )

    candidate = prod_bs_clean_candidate(
        model_row,
        bone_row,
    )

    if candidate is None:
        raise RuntimeError(
            "The selected bone is no longer clean and unscaled."
        )

    animset = model_row[
        "animset"
    ]
    shot = model_row[
        "shot"
    ]
    clip = get_channels_clip(
        animset,
        shot,
    )

    matches = []

    for control in prod_bs_animset_controls(animset):
        if typ(control) != u"DmeTransformControl":
            continue

        try:
            casted = vs.CastElementAsDmeTransformControl(
                control
            )
        except Exception:
            casted = control

        if casted is None:
            continue

        try:
            transform = casted.GetTransform()
        except Exception:
            transform = None

        if transform is None:
            continue

        if (
            dme_id(transform)
            == bone_row["transform_id"]
        ):
            matches.append(
                (
                    casted,
                    transform,
                )
            )

    if len(matches) != 1:
        raise RuntimeError(
            "The selected bone could not be resolved uniquely."
        )

    bone_control, transform = matches[0]
    groups = prod_bs_group_rows(
        animset,
        bone_control,
    )

    if len(groups) != 1:
        raise RuntimeError(
            "The selected bone does not have one control group."
        )

    names = prod_bs_names(
        identity[
            "bone_name"
        ]
    )

    baseline = {
        "shot_id": dme_id(
            shot
        ),
        "animset_id": dme_id(
            animset
        ),
        "bone_control_id": dme_id(
            bone_control
        ),
        "transform_id": dme_id(
            transform
        ),
        "group_id": dme_id(
            groups[0][
                "group"
            ]
        ),
        "group_path": groups[0][
            "path"
        ],
        "animset_control_count": len(
            r26_animset_controls(
                animset
            )
        ),
        "animset_operator_count": len(
            r26_animset_operators(
                animset
            )
        ),
        "channel_count": len(
            r26_clip_channels(
                clip
            )
        ),
        "group_control_count": len(
            arr(
                groups[0][
                    "group"
                ],
                "controls",
            )
        ),
    }

    return {
        "identity": dict(
            identity
        ),
        "model_row": model_row,
        "bone_row": bone_row,
        "shot": shot,
        "animset": animset,
        "clip": clip,
        "bone_control": bone_control,
        "transform": transform,
        "group": groups[0],
        "names": names,
        "baseline": baseline,
    }

def prod_bs_add_float_attr(element, attr_name, value):
    if get_attr(
        element,
        attr_name,
    ) is not None:
        raise RuntimeError(
            "Unexpected existing %s attribute."
            % attr_name
        )

    attr = element.AddAttributeAsFloat(
        b(attr_name)
    )

    if attr is None:
        raise RuntimeError(
            "Could not create %s."
            % attr_name
        )

    attr.SetValue(
        float(
            value
        )
    )

    if not close_enough(
        as_float(
            attr_value(
                element,
                attr_name,
            )
        ),
        value,
    ):
        raise RuntimeError(
            "%s did not retain its value."
            % attr_name
        )

    return attr

def prod_bs_create_graph(fixture, physical_value):
    animset = fixture[
        "animset"
    ]
    shot = fixture[
        "shot"
    ]
    clip = fixture[
        "clip"
    ]
    transform = fixture[
        "transform"
    ]
    group = fixture[
        "group"
    ]
    names = fixture[
        "names"
    ]

    native_value = (
        float(
            physical_value
        )
        - PROD_BS_LO
    ) / (
        PROD_BS_HI
        - PROD_BS_LO
    )

    # Exact native-style construction order proven by the earlier R23/R27
    # experiments, now parameterized only by the selected ordinary bone.
    scale_attr = transform.AddAttributeAsFloat(
        "scale"
    )

    if scale_attr is None:
        raise RuntimeError(
            "Could not create the bone scale attribute."
        )

    scale_attr.SetValue(
        1.0
    )

    control = animset.FindOrAddControl(
        b(
            names[
                "literal"
            ]
        ),
        False,
        True,
    )

    if (
        control is None
        or name(control)
        != names[
            "literal"
        ]
    ):
        raise RuntimeError(
            "SFM did not create the bone scale control."
        )

    prod_bs_add_float_attr(
        control,
        "value",
        PROD_BS_NEUTRAL_NATIVE,
    )
    prod_bs_add_float_attr(
        control,
        "defaultValue",
        PROD_BS_NEUTRAL_NATIVE,
    )

    input_channel = vs.CreateElement(
        "DmeChannel",
        b(
            names[
                "literal"
            ]
        ),
        shot.GetFileId(),
    )

    if (
        input_channel is None
        or typ(input_channel)
        != u"DmeChannel"
    ):
        raise RuntimeError(
            "Could not create the input channel."
        )

    input_log = vs.CreateElement(
        "DmeFloatLog",
        "float log",
        shot.GetFileId(),
    )

    if (
        input_log is None
        or typ(input_log)
        != u"DmeFloatLog"
    ):
        raise RuntimeError(
            "Could not create the input log."
        )

    input_channel.SetLog(
        input_log
    )
    input_log.SetKey(
        make_zero_time(),
        float(
            PROD_BS_NEUTRAL_NATIVE
        ),
    )

    clip.channels.AddToTail(
        input_channel
    )

    control.SetValue(
        "channel",
        input_channel,
    )
    input_channel.SetInput(
        control,
        "value",
    )
    input_channel.SetMode(
        3
    )

    expression = vs.CreateElement(
        "DmeExpressionOperator",
        b(
            names[
                "expression"
            ]
        ),
        animset.GetFileId(),
    )

    if (
        expression is None
        or typ(expression)
        != u"DmeExpressionOperator"
    ):
        raise RuntimeError(
            "Could not create the scale expression."
        )

    expression.expr = b(
        "lerp(value, lo, hi)"
    )
    expression.SetValue(
        "value",
        float(
            PROD_BS_NEUTRAL_NATIVE
        ),
    )
    expression.SetValue(
        "lo",
        float(
            PROD_BS_LO
        ),
    )
    expression.SetValue(
        "hi",
        float(
            PROD_BS_HI
        ),
    )
    animset.AddOperator(
        expression
    )

    input_channel.SetOutput(
        expression,
        "value",
    )

    output = clip.CreatePassThruConnection(
        b(
            names[
                "output"
            ]
        ),
        expression,
        "result",
        transform,
        "scale",
    )

    if (
        output is None
        or typ(output)
        != u"DmeChannel"
    ):
        raise RuntimeError(
            "Could not create the scale output channel."
        )

    group[
        "group"
    ].AddControl(
        control
    )

    # Author saved/test value using the qualified ONE_KEY_ZERO writer pattern.
    input_layer = get_layer(
        input_log,
        0,
    )

    if (
        input_layer is None
        or key_count(
            input_layer
        ) != 1
    ):
        raise RuntimeError(
            "Created input log is not ONE_KEY_ZERO."
        )

    input_layer.SetKeyValue(
        0,
        float(
            native_value
        ),
    )
    get_attr(
        control,
        "value",
    ).SetValue(
        float(
            native_value
        )
    )
    input_channel.Operate()

    return native_value

def prod_bs_resolve_created(identity):
    model_row = prod_bs_find_model_row(
        identity
    )
    bone_row = prod_bs_find_bone_row(
        model_row,
        identity,
    )

    if (
        bone_row[
            "classification"
        ]
        != "CHANNEL_DRIVEN_SCALE"
    ):
        raise RuntimeError(
            "The created bone scale did not resolve as channel-driven."
        )

    trace = prod_bs_trace_scaled_bone(
        model_row,
        bone_row,
    )

    expected_names = prod_bs_names(
        identity[
            "bone_name"
        ]
    )

    if not trace[
        "generic_lerp_topology"
    ]:
        raise RuntimeError(
            "The created bone scale graph is not generic native topology."
        )

    if not trace[
        "physical_matches_lerp"
    ]:
        raise RuntimeError(
            "The created bone scale does not evaluate coherently."
        )

    if (
        trace[
            "inputs"
        ][0][
            "source_name"
        ]
        != expected_names[
            "literal"
        ]
    ):
        raise RuntimeError(
            "Created scale control name does not match the native pattern."
        )

    if (
        trace[
            "expression"
        ][
            "name"
        ]
        != expected_names[
            "expression"
        ]
    ):
        raise RuntimeError(
            "Created expression name does not match the native pattern."
        )

    return {
        "model_row": model_row,
        "bone_row": bone_row,
        "trace": trace,
    }

def prod_bs_static_scale_trace(trace):
    if not trace["generic_lerp_topology"]:
        return False

    if not trace["physical_matches_lerp"]:
        return False

    if trace["input_count"] != 1:
        return False

    row = trace["inputs"][0]
    log = row["log"]

    return (
        row["mode"] == 3
        and row["source_type"] == u"DmElement"
        and row["source_attribute"] == u"value"
        and log["key_count"] == 1
        and log["is_empty"] is False
        and close_enough(
            log["key0_time"],
            0.0,
        )
        and close_enough(
            log["key0_value"],
            row["source_value"],
        )
        and trace["output"]["mode"] == 1
    )

def prod_bs_full_bone_scale_map(model_row):
    rows = prod_bs_bone_rows(
        model_row
    )

    result = []
    existing_scaled = []

    for row in rows:
        classification = row["classification"]

        if classification == "IMPLICIT_NEUTRAL":
            multiplier = 1.0
            source_state = u"implicit-neutral"

        elif classification == "CHANNEL_DRIVEN_SCALE":
            trace = prod_bs_trace_scaled_bone(
                model_row,
                row,
            )

            if not prod_bs_static_scale_trace(
                trace
            ):
                raise RuntimeError(
                    "Bone %s has scale state outside the qualified static contract."
                    % row["bone_name"]
                )

            multiplier = float(
                trace["physical_scale"]
            )
            source_state = u"existing-static-control"
            existing_scaled.append({
                "bone_index": row["bone_index"],
                "bone_name": row["bone_name"],
                "physical_scale": multiplier,
            })

        else:
            raise RuntimeError(
                "Bone %s has unsupported scale state %s."
                % (
                    row["bone_name"],
                    classification,
                )
            )

        result.append({
            "bone_index": int(
                row["bone_index"]
            ),
            "bone_name": u(
                row["bone_name"]
            ),
            "representation": u"uniform_local_scale_multiplier",
            "value": float(
                multiplier
            ),
            "capture_state": source_state,
        })

    result.sort(
        key=lambda item: (
            item["bone_index"],
            item["bone_name"].lower(),
        )
    )

    existing_scaled.sort(
        key=lambda item: (
            item["bone_index"],
            item["bone_name"].lower(),
        )
    )

    return result, existing_scaled

def prod_bs_bone_record_index(record):
    result = {}

    for row in record[
        "bone_scales"
    ]:
        key = (
            int(
                row[
                    "bone_index"
                ]
            ),
            u(
                row[
                    "bone_name"
                ]
            ).lower(),
        )
        result[key] = row

    return result

def prod_bs_current_bone_index(identity):
    model_row = prod_bs_find_model_row(
        identity
    )
    result = {}

    for row in prod_bs_bone_rows(
        model_row
    ):
        key = (
            int(
                row[
                    "bone_index"
                ]
            ),
            u(
                row[
                    "bone_name"
                ]
            ).lower(),
        )

        if key in result:
            raise RuntimeError(
                "Current bone identity is ambiguous."
            )

        result[key] = row

    return model_row, result

def prod_bs_existing_binding_for_row(model_row, bone_row):
    trace = prod_bs_trace_scaled_bone(
        model_row,
        bone_row,
    )

    if not prod_bs_static_scale_trace(
        trace
    ):
        raise RuntimeError(
            "Bone %s is outside the qualified static scale contract."
            % bone_row[
                "bone_name"
            ]
        )

    identity = {
        "model": model_row[
            "model"
        ],
        "checksum": int(
            model_row[
                "checksum"
            ]
        ),
        "bone_index": int(
            bone_row[
                "bone_index"
            ]
        ),
        "bone_name": u(
            bone_row[
                "bone_name"
            ]
        ),
    }

    return prod_bs_resolve_binding(
        identity
    )

def prod_bs_write_existing_scale(item):
    binding = item[
        "binding"
    ]
    native = float(
        item[
            "desired_native"
        ]
    )

    layer = binding[
        "input_layer"
    ]

    if key_count(
        layer
    ) != 1:
        raise RuntimeError(
            "Bone %s no longer has one static scale key."
            % item[
                "bone_name"
            ]
        )

    layer.SetKeyValue(
        0,
        native,
    )
    binding[
        "source_attr"
    ].SetValue(
        native
    )
    binding[
        "input_channel"
    ].Operate()

    authored = prod_bs_snapshot(
        binding
    )

    if not prod_bs_authored_matches(
        binding,
        authored,
        native,
    ):
        raise RuntimeError(
            "Bone %s failed authored-state verification."
            % item[
                "bone_name"
            ]
        )

def prod_bs_verify_saved_scales(identity, record):
    saved = prod_bs_bone_record_index(
        record
    )
    model_row, current = prod_bs_current_bone_index(
        identity
    )

    if set(saved.keys()) != set(
        current.keys()
    ):
        return False

    for key in saved:
        desired = float(
            saved[key][
                "value"
            ]
        )
        bone_row = current[
            key
        ]

        if (
            bone_row[
                "classification"
            ]
            == "IMPLICIT_NEUTRAL"
        ):
            if not close_enough(
                desired,
                1.0,
            ):
                return False
            continue

        if (
            bone_row[
                "classification"
            ]
            != "CHANNEL_DRIVEN_SCALE"
        ):
            return False

        trace = prod_bs_trace_scaled_bone(
            model_row,
            bone_row,
        )

        if not prod_bs_static_scale_trace(
            trace
        ):
            return False

        if not close_enough(
            trace[
                "physical_scale"
            ],
            desired,
        ):
            return False

    return True

def prod_bs_build_mixed_plan(identity, record):
    saved = prod_bs_bone_record_index(record)
    model_row, current = prod_bs_current_bone_index(identity)

    if set(saved.keys()) != set(current.keys()):
        raise RuntimeError(
            "The model's current bone layout differs from the saved preset."
        )

    existing_writes = []
    create_writes = []

    for key in sorted(saved.keys()):
        desired = float(saved[key]["value"])
        bone_row = current[key]

        if bone_row["classification"] == "IMPLICIT_NEUTRAL":
            if close_enough(desired, 1.0):
                continue

            fixture = prod_bs_resolve_clean_fixture({
                "model": identity["model"],
                "checksum": int(identity["checksum"]),
                "bone_index": int(bone_row["bone_index"]),
                "bone_name": u(bone_row["bone_name"]),
            })

            create_writes.append({
                "key": key,
                "bone_name": u(bone_row["bone_name"]),
                "desired_physical": desired,
                "fixture": fixture,
            })
            continue

        if bone_row["classification"] != "CHANNEL_DRIVEN_SCALE":
            raise RuntimeError(
                "Bone %s has unsupported current scale state."
                % bone_row["bone_name"]
            )

        binding = prod_bs_existing_binding_for_row(
            model_row,
            bone_row,
        )
        baseline = prod_bs_snapshot(binding)

        if not prod_bs_evaluated_matches(
            binding,
            baseline,
            baseline["source"],
        ):
            raise RuntimeError(
                "Bone %s is not coherent before Apply."
                % bone_row["bone_name"]
            )

        native = (
            desired - binding["lo"]
        ) / (
            binding["hi"] - binding["lo"]
        )

        existing_writes.append({
            "key": key,
            "bone_name": u(bone_row["bone_name"]),
            "binding": binding,
            "desired_physical": desired,
            "desired_native": native,
            "needs_write": not close_enough(
                baseline["physical_scale"],
                desired,
            ),
            "baseline": baseline,
        })

    return {
        "existing": existing_writes,
        "create": create_writes,
    }




PROD_Q1_INDEXED_CAPTURE_PARITY = False


def prod_bs_index_snapshot(identity):

    model_row = prod_bs_find_model_row(identity)
    animset = model_row["animset"]
    shot = model_row["shot"]
    clip = get_channels_clip(animset, shot)

    all_controls = prod_bs_animset_controls(animset)
    animset_controls = r26_animset_controls(animset)
    channels = [
        channel
        for channel in r26_clip_channels(clip)
        if typ(channel) == u"DmeChannel"
    ]
    groups = group_inventory(animset)
    operators = r26_animset_operators(animset)


    # Stable object indexes.
    control_by_id = {}
    controls_by_name = {}
    animset_control_hits = {}

    for control in all_controls:
        cid = dme_id(control)
        control_by_id[cid] = control
        controls_by_name.setdefault(
            u(name(control) or u""),
            [],
        ).append(control)

    for control in animset_controls:
        cid = dme_id(control)
        animset_control_hits[cid] = (
            animset_control_hits.get(cid, 0)
            + 1
        )

    group_rows_by_control_id = {}
    group_paths_by_control_id = {}

    for row in groups:
        group = row["group"]
        path = row["path"]

        for member in arr(group, "controls"):
            mid = dme_id(member)
            group_rows_by_control_id.setdefault(
                mid,
                [],
            ).append(row)
            group_paths_by_control_id.setdefault(
                mid,
                [],
            ).append(path)

    channels_by_name = {}
    channels_to_dest_attr = {}
    channel_sources_by_name = {}

    for channel in channels:
        cname = u(name(channel) or u"")
        channels_by_name.setdefault(
            cname,
            [],
        ).append(channel)

        destination = attr_value(
            channel,
            "toElement",
        )
        to_attribute = u(
            attr_value(
                channel,
                "toAttribute",
            )
            or u""
        )

        if destination is not None:
            channels_to_dest_attr.setdefault(
                (
                    dme_id(destination),
                    to_attribute,
                ),
                [],
            ).append(channel)

        source = attr_value(
            channel,
            "fromElement",
        )

        if source is not None:
            channel_sources_by_name.setdefault(
                u(name(source) or u""),
                [],
            ).append(source)

    operators_by_name = {}

    for operator in operators:
        operators_by_name.setdefault(
            u(name(operator) or u""),
            [],
        ).append(operator)

    # Build native-bone rows once.
    raw = []
    by_identity = {}
    transform_owners = {}

    for control in all_controls:
        if typ(control) != u"DmeTransformControl":
            continue

        try:
            casted = vs.CastElementAsDmeTransformControl(
                control
            )
        except Exception:
            casted = control

        if (
            casted is None
            or typ(casted) != u"DmeTransformControl"
        ):
            continue

        try:
            transform = casted.GetTransform()
        except Exception:
            transform = None

        if (
            transform is None
            or typ(transform) != u"DmeTransform"
        ):
            continue

        transform_name = u(
            name(transform)
            or u""
        )
        match = PROD_BS_BONE_RE.match(
            transform_name
        )

        if not match:
            continue

        bone_index = int(
            match.group(1)
        )
        bone_name = u(
            match.group(2)
        )
        control_name = u(
            name(casted)
            or u""
        )
        cid = dme_id(casted)
        tid = dme_id(transform)

        scale_attr = get_attr(
            transform,
            "scale",
        )
        scale_present = (
            scale_attr is not None
        )

        if scale_present:
            scale_value = as_float(
                attr_value(
                    transform,
                    "scale",
                )
            )
        else:
            scale_value = 1.0

        scale_channels = list(
            channels_to_dest_attr.get(
                (
                    tid,
                    u"scale",
                ),
                [],
            )
        )

        identity_key = (
            bone_index,
            bone_name.lower(),
        )

        row = {
            "bone_index": bone_index,
            "bone_name": bone_name,
            "control_name": control_name,
            "control_matches_bone_name": (
                control_name.lower()
                == bone_name.lower()
            ),
            "control_id": cid,
            "transform_name": transform_name,
            "transform_id": tid,
            "group_paths": sorted(
                set(
                    group_paths_by_control_id.get(
                        cid,
                        [],
                    )
                )
            ),
            "scale_attr_present": scale_present,
            "scale_value": scale_value,
            "scale_channel_count": len(
                scale_channels
            ),
            "scale_channels": scale_channels,
            "_control": casted,
            "_transform": transform,
            "_group_rows": list(
                group_rows_by_control_id.get(
                    cid,
                    [],
                )
            ),
        }

        raw.append(row)
        by_identity.setdefault(
            identity_key,
            [],
        ).append(row)
        transform_owners.setdefault(
            tid,
            [],
        ).append(row)

    bone_index_map = {}

    for row in raw:
        identity_key = (
            row["bone_index"],
            row["bone_name"].lower(),
        )

        duplicate_identity = (
            len(
                by_identity.get(
                    identity_key,
                    [],
                )
            )
            != 1
        )
        shared_transform = (
            len(
                transform_owners.get(
                    row["transform_id"],
                    [],
                )
            )
            != 1
        )

        if (
            duplicate_identity
            or shared_transform
        ):
            classification = "AMBIGUOUS_IDENTITY"

        elif row["scale_channel_count"] > 0:
            classification = "CHANNEL_DRIVEN_SCALE"

        elif not row["scale_attr_present"]:
            classification = "IMPLICIT_NEUTRAL"

        elif (
            row["scale_value"] is not None
            and close_enough(
                row["scale_value"],
                1.0,
            )
        ):
            classification = "DIRECT_NEUTRAL"

        elif row["scale_value"] is not None:
            classification = "DIRECT_NON_NEUTRAL"

        else:
            classification = "UNREADABLE_DIRECT_SCALE"

        row["duplicate_identity"] = duplicate_identity
        row["shared_transform"] = shared_transform
        row["classification"] = classification
        row["portable_identity"] = {
            "model": model_row["model"],
            "checksum": model_row["checksum"],
            "bone_index": row["bone_index"],
            "bone_name": row["bone_name"],
        }

        if identity_key in bone_index_map:
            raise RuntimeError(
                "Current bone identity is ambiguous."
            )

        bone_index_map[
            identity_key
        ] = row


    snapshot = {
        "identity": dict(identity),
        "model_row": model_row,
        "animset": animset,
        "shot": shot,
        "clip": clip,
        "all_controls": all_controls,
        "animset_controls": animset_controls,
        "channels": channels,
        "groups": groups,
        "operators": operators,
        "control_by_id": control_by_id,
        "controls_by_name": controls_by_name,
        "animset_control_hits": animset_control_hits,
        "group_rows_by_control_id": group_rows_by_control_id,
        "group_paths_by_control_id": group_paths_by_control_id,
        "channels_by_name": channels_by_name,
        "channels_to_dest_attr": channels_to_dest_attr,
        "channel_sources_by_name": channel_sources_by_name,
        "operators_by_name": operators_by_name,
        "bone_index": bone_index_map,
        "counts": {
            "animset_controls": len(
                animset_controls
            ),
            "operators": len(
                operators
            ),
            "channels": len(
                channels
            ),
        },
    }


    return snapshot


def prod_bs_index_log_state(channel):
    return prod_bs_log_state(
        channel
    )


def prod_bs_index_trace(snapshot, bone_row):
    transform = bone_row[
        "_transform"
    ]
    bone_control = bone_row[
        "_control"
    ]

    output_matches = list(
        snapshot[
            "channels_to_dest_attr"
        ].get(
            (
                bone_row[
                    "transform_id"
                ],
                u"scale",
            ),
            [],
        )
    )

    if len(output_matches) != 1:
        raise RuntimeError(
            "Expected one output channel to %r.scale; found %d."
            % (
                bone_row[
                    "portable_identity"
                ],
                len(
                    output_matches
                ),
            )
        )

    output = output_matches[0]
    expression = attr_value(
        output,
        "fromElement",
    )

    if (
        expression is None
        or typ(expression)
        != u"DmeExpressionOperator"
    ):
        raise RuntimeError(
            "Scale output source is not a DmeExpressionOperator."
        )

    if u(
        attr_value(
            output,
            "fromAttribute",
        )
    ) != u"result":
        raise RuntimeError(
            "Scale output does not source expression.result."
        )

    expression_text = u(
        attr_value(
            expression,
            "expr",
        )
        or u""
    )
    normalized_expr = expression_text.replace(
        " ",
        "",
    ).lower()

    lo = as_float(
        attr_value(
            expression,
            "lo",
        )
    )
    hi = as_float(
        attr_value(
            expression,
            "hi",
        )
    )
    expression_value = as_float(
        attr_value(
            expression,
            "value",
        )
    )
    expression_result = as_float(
        attr_value(
            expression,
            "result",
        )
    )

    input_matches = list(
        snapshot[
            "channels_to_dest_attr"
        ].get(
            (
                dme_id(expression),
                u"value",
            ),
            [],
        )
    )

    input_rows = []

    for channel in input_matches:
        source = attr_value(
            channel,
            "fromElement",
        )
        source_attr_name = u(
            attr_value(
                channel,
                "fromAttribute",
            )
            or u""
        )

        source_value = (
            as_float(
                attr_value(
                    source,
                    source_attr_name,
                )
            )
            if (
                source is not None
                and source_attr_name
            )
            else None
        )

        source_id = (
            dme_id(source)
            if source is not None
            else None
        )

        membership = {
            "animset_control_hits": (
                snapshot[
                    "animset_control_hits"
                ].get(
                    source_id,
                    0,
                )
                if source_id is not None
                else 0
            ),
            "group_paths": sorted(
                set(
                    snapshot[
                        "group_paths_by_control_id"
                    ].get(
                        source_id,
                        [],
                    )
                )
            ) if source_id is not None else [],
        }

        input_rows.append({
            "channel_id": dme_id(
                channel
            ),
            "channel_name": name(
                channel
            ),
            "mode": attr_value(
                channel,
                "mode",
            ),
            "source_id": source_id,
            "source_type": typ(
                source
            ),
            "source_name": name(
                source
            ),
            "source_attribute": source_attr_name,
            "source_value": source_value,
            "source_default_value": (
                as_float(
                    attr_value(
                        source,
                        "defaultValue",
                    )
                )
                if source is not None
                else None
            ),
            "source_channel_id": (
                dme_id(
                    attr_value(
                        source,
                        "channel",
                    )
                )
                if source is not None
                else None
            ),
            "membership": membership,
            "log": prod_bs_index_log_state(
                channel
            ),
            "_channel": channel,
            "_source": source,
        })

    physical_scale = as_float(
        attr_value(
            transform,
            "scale",
        )
    )

    expected_physical = None

    if (
        normalized_expr
        == u"lerp(value,lo,hi)"
        and expression_value is not None
        and lo is not None
        and hi is not None
    ):
        expected_physical = (
            lo
            + expression_value
            * (
                hi - lo
            )
        )

    topology_match = (
        normalized_expr
        == u"lerp(value,lo,hi)"
        and lo is not None
        and hi is not None
        and not close_enough(
            lo,
            hi,
        )
        and len(
            input_rows
        ) == 1
        and input_rows[0][
            "source_type"
        ] == u"DmElement"
        and input_rows[0][
            "source_attribute"
        ] == u"value"
        and input_rows[0][
            "membership"
        ][
            "animset_control_hits"
        ] == 1
        and int(
            attr_value(
                output,
                "mode",
            )
        ) == 1
    )

    physical_matches = (
        expected_physical is not None
        and physical_scale is not None
        and close_enough(
            expected_physical,
            physical_scale,
        )
    )

    return {
        "portable_identity": bone_row[
            "portable_identity"
        ],
        "bone_control_id": dme_id(
            bone_control
        ),
        "bone_group_paths": list(
            bone_row[
                "group_paths"
            ]
        ),
        "transform_id": dme_id(
            transform
        ),
        "physical_scale": physical_scale,
        "output": {
            "id": dme_id(
                output
            ),
            "name": name(
                output
            ),
            "mode": attr_value(
                output,
                "mode",
            ),
            "log": prod_bs_index_log_state(
                output
            ),
            "_channel": output,
        },
        "expression": {
            "id": dme_id(
                expression
            ),
            "name": name(
                expression
            ),
            "expr": expression_text,
            "normalized_expr": normalized_expr,
            "lo": lo,
            "hi": hi,
            "value": expression_value,
            "result": expression_result,
            "_operator": expression,
        },
        "input_count": len(
            input_rows
        ),
        "inputs": input_rows,
        "expected_physical": expected_physical,
        "physical_matches_lerp": physical_matches,
        "generic_lerp_topology": topology_match,
    }


def prod_bs_index_binding(snapshot, bone_row):
    trace = prod_bs_index_trace(
        snapshot,
        bone_row,
    )

    if not trace[
        "generic_lerp_topology"
    ]:
        raise RuntimeError(
            "This bone scale is outside the qualified generic topology."
        )

    if not trace[
        "physical_matches_lerp"
    ]:
        raise RuntimeError(
            "This bone scale is not evaluating coherently."
        )

    if trace["input_count"] != 1:
        raise RuntimeError(
            "The selected bone scale does not have one input channel."
        )

    input_row = trace[
        "inputs"
    ][0]
    input_channel = input_row[
        "_channel"
    ]
    control = input_row[
        "_source"
    ]
    expression = trace[
        "expression"
    ][
        "_operator"
    ]
    output = trace[
        "output"
    ][
        "_channel"
    ]

    try:
        input_log = input_channel.GetLog()
    except Exception:
        input_log = attr_value(
            input_channel,
            "log",
        )

    if input_log is None:
        raise RuntimeError(
            "The selected bone scale input log is unavailable."
        )

    input_layer = get_layer(
        input_log,
        0,
    )

    if input_layer is None:
        raise RuntimeError(
            "The selected bone scale input layer is unavailable."
        )

    source_attr = get_attr(
        control,
        "value",
    )

    if source_attr is None:
        raise RuntimeError(
            "The selected bone scale value attribute is unavailable."
        )

    return {
        "identity": dict(
            bone_row[
                "portable_identity"
            ]
        ),
        "model_row": snapshot[
            "model_row"
        ],
        "bone_row": bone_row,
        "shot": snapshot[
            "shot"
        ],
        "animset": snapshot[
            "animset"
        ],
        "bone_control": bone_row[
            "_control"
        ],
        "transform": bone_row[
            "_transform"
        ],
        "output": output,
        "expression": expression,
        "input_channel": input_channel,
        "control": control,
        "source_attr": source_attr,
        "input_log": input_log,
        "input_layer": input_layer,
        "lo": trace[
            "expression"
        ][
            "lo"
        ],
        "hi": trace[
            "expression"
        ][
            "hi"
        ],
    }


def prod_bs_index_clean_fixture(snapshot, bone_row):
    if (
        bone_row[
            "classification"
        ]
        != "IMPLICIT_NEUTRAL"
    ):
        raise RuntimeError(
            "The selected bone is no longer clean and unscaled."
        )

    if not bone_row[
        "control_matches_bone_name"
    ]:
        raise RuntimeError(
            "The selected bone control does not match its native bone name."
        )

    group_rows = list(
        bone_row[
            "_group_rows"
        ]
    )

    if len(group_rows) != 1:
        raise RuntimeError(
            "The selected bone does not have one control group."
        )

    names = prod_bs_names(
        bone_row[
            "bone_name"
        ]
    )
    transform = bone_row[
        "_transform"
    ]

    if get_attr(
        transform,
        "scale",
    ) is not None:
        raise RuntimeError(
            "The selected bone is no longer clean and unscaled."
        )

    control_hits = {}
    literal = names[
        "literal"
    ]

    for control in snapshot[
        "controls_by_name"
    ].get(
        literal,
        [],
    ):
        control_hits[
            dme_id(control)
        ] = control

    for control in snapshot[
        "channel_sources_by_name"
    ].get(
        literal,
        [],
    ):
        control_hits[
            dme_id(control)
        ] = control

    try:
        found = snapshot[
            "animset"
        ].FindControl(
            b(literal)
        )
    except Exception:
        try:
            found = snapshot[
                "animset"
            ].FindControl(
                literal
            )
        except Exception:
            found = None

    if found is not None:
        control_hits[
            dme_id(found)
        ] = found

    if control_hits:
        raise RuntimeError(
            "The selected bone scale control is no longer absent."
        )

    if len(
        snapshot[
            "operators_by_name"
        ].get(
            names[
                "expression"
            ],
            [],
        )
    ) != 0:
        raise RuntimeError(
            "The selected bone scale expression is no longer absent."
        )

    if snapshot[
        "channels_by_name"
    ].get(
        names[
            "literal"
        ],
        [],
    ):
        raise RuntimeError(
            "The selected bone scale input channel is no longer absent."
        )

    if snapshot[
        "channels_by_name"
    ].get(
        names[
            "output"
        ],
        [],
    ):
        raise RuntimeError(
            "The selected bone scale output channel is no longer absent."
        )

    group_row = group_rows[0]

    return {
        "identity": dict(
            bone_row[
                "portable_identity"
            ]
        ),
        "model_row": snapshot[
            "model_row"
        ],
        "bone_row": bone_row,
        "shot": snapshot[
            "shot"
        ],
        "animset": snapshot[
            "animset"
        ],
        "clip": snapshot[
            "clip"
        ],
        "bone_control": bone_row[
            "_control"
        ],
        "transform": transform,
        "group": group_row,
        "names": names,
        "baseline": {
            "shot_id": dme_id(
                snapshot[
                    "shot"
                ]
            ),
            "animset_id": dme_id(
                snapshot[
                    "animset"
                ]
            ),
            "bone_control_id": bone_row[
                "control_id"
            ],
            "transform_id": bone_row[
                "transform_id"
            ],
            "group_id": dme_id(
                group_row[
                    "group"
                ]
            ),
            "group_path": group_row[
                "path"
            ],
            "animset_control_count": snapshot[
                "counts"
            ][
                "animset_controls"
            ],
            "animset_operator_count": snapshot[
                "counts"
            ][
                "operators"
            ],
            "channel_count": snapshot[
                "counts"
            ][
                "channels"
            ],
            "group_control_count": len(
                arr(
                    group_row[
                        "group"
                    ],
                    "controls",
                )
            ),
        },
    }


def prod_bs_index_validate_saved_map(
    bone_scales,
    snapshot,
):
    if not isinstance(
        bone_scales,
        list,
    ):
        raise RuntimeError(
            "This older Body Preset does not include bone scaling. Delete it and save a new Body Preset."
        )

    seen = set()

    for row in bone_scales:
        if not isinstance(
            row,
            dict,
        ):
            raise RuntimeError(
                "Saved bone-scale data is malformed."
            )

        try:
            bone_index = int(
                row[
                    "bone_index"
                ]
            )
            bone_name = u(
                row[
                    "bone_name"
                ]
            )
            representation = u(
                row[
                    "representation"
                ]
            )
        except Exception:
            raise RuntimeError(
                "Saved bone-scale data is malformed."
            )

        value = as_float(
            row.get(
                "value"
            )
        )

        if value is None:
            raise RuntimeError(
                "A saved bone scale is not finite."
            )

        if (
            representation
            != u"uniform_local_scale_multiplier"
        ):
            raise RuntimeError(
                "Saved bone-scale data uses an unsupported format."
            )

        if value <= 0.0:
            raise RuntimeError(
                "A saved bone scale is invalid."
            )

        key = (
            bone_index,
            bone_name.lower(),
        )

        if key in seen:
            raise RuntimeError(
                "Saved bone-scale data contains a duplicate bone."
            )

        seen.add(
            key
        )

    if set(
        seen
    ) != set(
        snapshot[
            "bone_index"
        ].keys()
    ):
        raise RuntimeError(
            "This Body Preset does not match the selected model's current bone layout."
        )

    return True


def prod_bs_index_build_plan(
    identity,
    record,
    snapshot,
):
    prod_bs_index_validate_saved_map(
        record.get(
            "bone_scales"
        ),
        snapshot,
    )

    saved = prod_bs_bone_record_index(
        record
    )
    current = snapshot[
        "bone_index"
    ]

    existing_writes = []
    create_writes = []

    for key in sorted(
        saved.keys()
    ):
        desired = float(
            saved[key][
                "value"
            ]
        )
        bone_row = current[
            key
        ]

        if (
            bone_row[
                "classification"
            ]
            == "IMPLICIT_NEUTRAL"
        ):
            if close_enough(
                desired,
                1.0,
            ):
                continue

            fixture = prod_bs_index_clean_fixture(
                snapshot,
                bone_row,
            )

            create_writes.append({
                "key": key,
                "bone_name": u(
                    bone_row[
                        "bone_name"
                    ]
                ),
                "desired_physical": desired,
                "fixture": fixture,
            })
            continue

        if (
            bone_row[
                "classification"
            ]
            != "CHANNEL_DRIVEN_SCALE"
        ):
            raise RuntimeError(
                "Bone %s has unsupported current scale state."
                % bone_row[
                    "bone_name"
                ]
            )

        binding = prod_bs_index_binding(
            snapshot,
            bone_row,
        )
        baseline = prod_bs_snapshot(
            binding
        )

        if not prod_bs_evaluated_matches(
            binding,
            baseline,
            baseline[
                "source"
            ],
        ):
            raise RuntimeError(
                "Bone %s is not coherent before Apply."
                % bone_row[
                    "bone_name"
                ]
            )

        native = (
            desired
            - binding[
                "lo"
            ]
        ) / (
            binding[
                "hi"
            ]
            - binding[
                "lo"
            ]
        )

        existing_writes.append({
            "key": key,
            "bone_name": u(
                bone_row[
                    "bone_name"
                ]
            ),
            "binding": binding,
            "desired_physical": desired,
            "desired_native": native,
            "needs_write": not close_enough(
                baseline[
                    "physical_scale"
                ],
                desired,
            ),
            "baseline": baseline,
        })

    return {
        "existing": existing_writes,
        "create": create_writes,
    }


def prod_bs_index_verify_saved(
    record,
    snapshot,
):
    prod_bs_index_validate_saved_map(
        record.get(
            "bone_scales"
        ),
        snapshot,
    )

    saved = prod_bs_bone_record_index(
        record
    )
    current = snapshot[
        "bone_index"
    ]

    for key in saved:
        desired = float(
            saved[key][
                "value"
            ]
        )
        bone_row = current[
            key
        ]

        if (
            bone_row[
                "classification"
            ]
            == "IMPLICIT_NEUTRAL"
        ):
            if not close_enough(
                desired,
                1.0,
            ):
                return False
            continue

        if (
            bone_row[
                "classification"
            ]
            != "CHANNEL_DRIVEN_SCALE"
        ):
            return False

        trace = prod_bs_index_trace(
            snapshot,
            bone_row,
        )

        if not prod_bs_static_scale_trace(
            trace
        ):
            return False

        if not close_enough(
            trace[
                "physical_scale"
            ],
            desired,
        ):
            return False

    return True


def prod_validate_bone_scale_map(
    identity,
    bone_scales,
):

    if not isinstance(
        bone_scales,
        list,
    ):
        raise RuntimeError(
            "This older Body Preset does not include bone scaling. Delete it and save a new Body Preset."
        )

    seen = set()

    for row in bone_scales:
        if not isinstance(
            row,
            dict,
        ):
            raise RuntimeError(
                "Saved bone-scale data is malformed."
            )

        try:
            bone_index = int(
                row[
                    "bone_index"
                ]
            )
            bone_name = u(
                row[
                    "bone_name"
                ]
            )
            representation = u(
                row[
                    "representation"
                ]
            )
        except Exception:
            raise RuntimeError(
                "Saved bone-scale data is malformed."
            )

        value = as_float(
            row.get(
                "value"
            )
        )

        if value is None:
            raise RuntimeError(
                "A saved bone scale is not finite."
            )

        if (
            representation
            != u"uniform_local_scale_multiplier"
        ):
            raise RuntimeError(
                "Saved bone-scale data uses an unsupported format."
            )

        if value <= 0.0:
            raise RuntimeError(
                "A saved bone scale is invalid."
            )

        key = (
            bone_index,
            bone_name.lower(),
        )

        if key in seen:
            raise RuntimeError(
                "Saved bone-scale data contains a duplicate bone."
            )

        seen.add(
            key
        )


    model_row, current = prod_bs_current_bone_index(
        identity
    )

    if set(
        seen
    ) != set(
        current.keys()
    ):
        raise RuntimeError(
            "This Body Preset does not match the selected model's current bone layout."
        )


    return True



def prod_bs_index_capture_static_trace(
    trace,
):
    """
    Capture admission for an existing static scale control.

    Preserve the qualified historical topology, but close the bounded
    admission gap identified by Astra: the input must be a one-layer
    DmeFloatLog. This is intentionally stricter than the historical
    prod_bs_static_scale_trace predicate.
    """
    if not prod_bs_static_scale_trace(
        trace
    ):
        return False

    if trace.get(
        "input_count"
    ) != 1:
        return False

    row = trace[
        "inputs"
    ][0]
    log = row.get(
        "log"
    ) or {}

    return (
        log.get(
            "log_type"
        )
        == u"DmeFloatLog"
        and log.get(
            "layer_count"
        )
        == 1
    )


def prod_bone_scale_keys_from_records(
    bone_scales,
):
    keys = []

    if not isinstance(
        bone_scales,
        list,
    ):
        return keys

    for row in bone_scales:
        if not isinstance(
            row,
            dict,
        ):
            continue

        try:
            key = (
                int(
                    row[
                        "bone_index"
                    ]
                ),
                u(
                    row[
                        "bone_name"
                    ]
                ).lower(),
            )
        except Exception:
            continue

        keys.append(
            key
        )

    keys.sort()
    return keys


def prod_validate_bone_scale_map_against_keys(
    bone_scales,
    expected_keys,
):
    """
    Pure-data Body bone-map validation.

    This validates the persisted representation and complete key coverage
    against the independently enumerated operation-local expected key set.
    It performs no scene/DME traversal.
    """
    if not isinstance(
        bone_scales,
        list,
    ):
        raise RuntimeError(
            "This older Body Preset does not include bone scaling. Delete it and save a new Body Preset."
        )

    try:
        expected = set(
            (
                int(
                    key[
                        0
                    ]
                ),
                u(
                    key[
                        1
                    ]
                ).lower(),
            )
            for key in expected_keys
        )
    except Exception:
        raise RuntimeError(
            "Current bone identity data is malformed."
        )

    if not expected:
        raise RuntimeError(
            "No native model bones could be captured safely."
        )

    seen = set()

    for row in bone_scales:
        if not isinstance(
            row,
            dict,
        ):
            raise RuntimeError(
                "Saved bone-scale data is malformed."
            )

        try:
            bone_index = int(
                row[
                    "bone_index"
                ]
            )
            bone_name = u(
                row[
                    "bone_name"
                ]
            )
            representation = u(
                row[
                    "representation"
                ]
            )
        except Exception:
            raise RuntimeError(
                "Saved bone-scale data is malformed."
            )

        value = as_float(
            row.get(
                "value"
            )
        )

        if value is None:
            raise RuntimeError(
                "A saved bone scale is not finite."
            )

        if (
            representation
            != u"uniform_local_scale_multiplier"
        ):
            raise RuntimeError(
                "Saved bone-scale data uses an unsupported format."
            )

        if value <= 0.0:
            raise RuntimeError(
                "A saved bone scale is invalid."
            )

        key = (
            bone_index,
            bone_name.lower(),
        )

        if key in seen:
            raise RuntimeError(
                "Saved bone-scale data contains a duplicate bone."
            )

        seen.add(
            key
        )

    if seen != expected:
        raise RuntimeError(
            "This Body Preset does not match the selected model's current bone layout."
        )

    return True



def prod_bs_capture_trace_diagnostic(
    trace,
):
    """
    Pure diagnostic summary only. Never returns native/DME references.
    """
    inputs = trace.get(
        "inputs"
    ) or []
    row = (
        inputs[
            0
        ]
        if len(
            inputs
        ) == 1
        else {}
    )
    log = row.get(
        "log"
    ) or {}
    output = trace.get(
        "output"
    ) or {}

    return {
        "historical_static_ok": bool(
            prod_bs_static_scale_trace(
                trace
            )
        ),
        "indexed_static_ok": bool(
            prod_bs_index_capture_static_trace(
                trace
            )
        ),
        "generic_lerp_topology": bool(
            trace.get(
                "generic_lerp_topology"
            )
        ),
        "physical_matches_lerp": bool(
            trace.get(
                "physical_matches_lerp"
            )
        ),
        "input_count": trace.get(
            "input_count"
        ),
        "input_mode": row.get(
            "mode"
        ),
        "source_type": row.get(
            "source_type"
        ),
        "source_attribute": row.get(
            "source_attribute"
        ),
        "source_value": row.get(
            "source_value"
        ),
        "source_default_value": row.get(
            "source_default_value"
        ),
        "log_type": log.get(
            "log_type"
        ),
        "layer_count": log.get(
            "layer_count"
        ),
        "key_count": log.get(
            "key_count"
        ),
        "is_empty": log.get(
            "is_empty"
        ),
        "key0_time": log.get(
            "key0_time"
        ),
        "key0_value": log.get(
            "key0_value"
        ),
        "output_mode": output.get(
            "mode"
        ),
        "physical_scale": trace.get(
            "physical_scale"
        ),
        "expected_physical": trace.get(
            "expected_physical"
        ),
    }


def prod_bs_index_capture_map(
    identity,
):
    """
    One fresh indexed native acquisition projected immediately to pure data.
    No live DME/native object is returned from this function.
    """
    snapshot = None
    trace = None
    row = None

    try:
        snapshot = prod_bs_index_snapshot(
            identity
        )
        prod_resource_snapshot(
            u"Q2_INDEX_ACQUIRED"
        )

        expected_keys = sorted(
            snapshot[
                "bone_index"
            ].keys()
        )

        if not expected_keys:
            raise RuntimeError(
                "No native model bones could be captured safely."
            )

        result = []
        existing_scaled = []


        for key in expected_keys:
            row = snapshot[
                "bone_index"
            ][
                key
            ]
            classification = row[
                "classification"
            ]

            if classification == "IMPLICIT_NEUTRAL":
                multiplier = 1.0
                source_state = u"implicit-neutral"

            elif classification == "CHANNEL_DRIVEN_SCALE":
                trace = prod_bs_index_trace(
                    snapshot,
                    row,
                )

                if not prod_bs_index_capture_static_trace(
                    trace
                ):
                    try:
                        diagnostic = prod_bs_capture_trace_diagnostic(
                            trace
                        )
                        log_line(
                            "Q3_SCALE_CAPTURE_REJECT bone=%r diagnostic=%r"
                            % (
                                row[
                                    "bone_name"
                                ],
                                diagnostic,
                            )
                        )
                    except Exception:
                        pass
                    diagnostic = None
                    raise RuntimeError(
                        "Bone %s has scale state outside the qualified static contract."
                        % row[
                            "bone_name"
                        ]
                    )


                multiplier = as_float(
                    trace.get(
                        "physical_scale"
                    )
                )

                if (
                    multiplier is None
                    or multiplier <= 0.0
                ):
                    raise RuntimeError(
                        "Bone %s has an invalid physical scale."
                        % row[
                            "bone_name"
                        ]
                    )

                multiplier = float(
                    multiplier
                )
                source_state = u"existing-static-control"
                existing_scaled.append({
                    "bone_index": int(
                        row[
                            "bone_index"
                        ]
                    ),
                    "bone_name": u(
                        row[
                            "bone_name"
                        ]
                    ),
                    "physical_scale": multiplier,
                })

                # Do not retain trace-side native references across bones.
                trace = None

            else:
                raise RuntimeError(
                    "Bone %s has unsupported scale state %s."
                    % (
                        row[
                            "bone_name"
                        ],
                        classification,
                    )
                )

            result.append({
                "bone_index": int(
                    row[
                        "bone_index"
                    ]
                ),
                "bone_name": u(
                    row[
                        "bone_name"
                    ]
                ),
                "representation": u"uniform_local_scale_multiplier",
                "value": float(
                    multiplier
                ),
                "capture_state": source_state,
            })

            row = None

        prod_resource_snapshot(
            u"Q2_INDEX_PROJECTED_LIVE"
        )

        result.sort(
            key=lambda item: (
                item[
                    "bone_index"
                ],
                item[
                    "bone_name"
                ].lower(),
            )
        )
        existing_scaled.sort(
            key=lambda item: (
                item[
                    "bone_index"
                ],
                item[
                    "bone_name"
                ].lower(),
            )
        )

        # Validate against the independently enumerated complete inventory
        # while only pure data remains relevant to the result.
        prod_validate_bone_scale_map_against_keys(
            result,
            expected_keys,
        )

        counts = {
            "bones": len(
                expected_keys
            ),
            "channels": int(
                snapshot.get(
                    "counts",
                    {},
                ).get(
                    "channels"
                )
                or 0
            ),
            "animset_controls": int(
                snapshot.get(
                    "counts",
                    {},
                ).get(
                    "animset_controls"
                )
                or 0
            ),
            "operators": int(
                snapshot.get(
                    "counts",
                    {},
                ).get(
                    "operators"
                )
                or 0
            ),
        }

        return {
            "bone_scales": result,
            "existing_scaled": existing_scaled,
            "expected_bone_keys": list(
                expected_keys
            ),
            "index_counts": counts,
        }

    finally:
        # The indexed acquisition is operation-local by contract. Explicitly
        # sever the large native-reference graph before serialization.
        trace = None
        row = None

        if isinstance(
            snapshot,
            dict,
        ):
            snapshot.clear()

        snapshot = None
        prod_resource_snapshot(
            u"Q2_INDEX_RELEASED"
        )



def prod_q1_compare_body_capture(
    identity,
    indexed_capture,
):
    """
    Q1-only read-only oracle comparison.

    The historical slow capture remains unchanged and is invoked only while
    PROD_Q1_INDEXED_CAPTURE_PARITY is True. It must never become a production
    fallback.
    """
    old_bone_scales, old_existing_scaled = prod_capture_bone_scale_map(
        identity
    )

    new_bone_scales = indexed_capture[
        "bone_scales"
    ]
    new_existing_scaled = indexed_capture[
        "existing_scaled"
    ]

    if old_bone_scales != new_bone_scales:
        raise RuntimeError(
            "Q1 indexed Body capture does not match the historical supported capture."
        )

    if old_existing_scaled != new_existing_scaled:
        raise RuntimeError(
            "Q1 indexed Body existing-scale summary does not match the historical capture."
        )

    old_keys = prod_bone_scale_keys_from_records(
        old_bone_scales
    )
    expected_keys = sorted(
        indexed_capture[
            "expected_bone_keys"
        ]
    )

    if old_keys != expected_keys:
        raise RuntimeError(
            "Q1 indexed Body expected bone coverage does not match the historical capture."
        )

    try:
        log_line(
            "Q1_CAPTURE_PARITY=PASS model=%r records=%d existing_scaled=%d"
            % (
                identity[
                    "model"
                ],
                len(
                    new_bone_scales
                ),
                len(
                    new_existing_scaled
                ),
            )
        )
    except Exception:
        pass

    return True


def prod_capture_body_snapshot(
    identity,
    accepted,
    operation_context=None,
):
    """
    Coherent Body read: FLEX values plus one indexed bone acquisition.

    Returns pure Python data only. No event pumping or modal work occurs inside
    this capture frame.
    """

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )

    values, _ = p03_capture_values(
        accepted
    )

    indexed = prod_bs_index_capture_map(
        identity
    )
    prod_resource_snapshot(
        u"Q2_BODY_CAPTURE_PURE_ONLY"
    )

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )

    if PROD_Q1_INDEXED_CAPTURE_PARITY:
        prod_q1_compare_body_capture(
            identity,
            indexed,
        )

        if operation_context is not None:
            prod_validate_context_token(
                operation_context
            )

    result = {
        "values": values,
        "bone_scales": indexed[
            "bone_scales"
        ],
        "existing_scaled": indexed[
            "existing_scaled"
        ],
        "expected_bone_keys": indexed[
            "expected_bone_keys"
        ],
        "index_counts": indexed[
            "index_counts"
        ],
    }

    indexed = None


    return result


def prod_capture_bone_scale_map(identity):

    model_row = prod_bs_find_model_row(identity)

    bone_map, existing_scaled = prod_bs_full_bone_scale_map(model_row)

    if not bone_map:
        raise RuntimeError("No native model bones could be captured safely.")


    return bone_map, existing_scaled


def prod_build_bone_scale_plan(identity, record):

    prod_validate_bone_scale_map(
        identity,
        record.get("bone_scales"),
    )

    result = prod_bs_build_mixed_plan(
        identity,
        record,
    )


    return result


def prod_verify_bone_scale_map(identity, record):

    prod_validate_bone_scale_map(
        identity,
        record.get("bone_scales"),
    )

    result = prod_bs_verify_saved_scales(
        identity,
        record,
    )


    return result






def prod_save(
    identity,
    kind,
    name_value,
    scope=None,
    existing_items=None,
    phase_callback=None,
    operation_context=None,
):
    prod_resource_snapshot(
        u"Q2_SAVE_POST_CONFIRM"
    )

    # Name uniqueness is checked against a fresh disk inventory. This is
    # intentionally library-only and does not traverse scene/DME state.
    fresh_items = prod_discover(
        identity,
        kind,
    )
    prod_assert_unique_preset_name_items(
        fresh_items,
        kind,
        name_value,
    )

    if scope is None:
        scope = prod_scope(
            identity
        )

    # CPM Step 3: post-prompt authorization; everything later consumes it.
    authority_context = prod_cpm_authorize_operation(
        identity,
        scope,
        kind,
        u"Save Preset",
    )

    live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        kind,
        authority_context=authority_context,
    )
    accepted = live[
        "accepted"
    ]

    if not accepted:
        raise RuntimeError(
            "Selected model has no qualified controls for this preset type."
        )

    bone_scales = None
    existing_scaled = []
    expected_bone_keys = None

    if kind == P03_KIND_BODY:
        body_capture = prod_capture_body_snapshot(
            identity,
            accepted,
            operation_context=operation_context,
        )
        values = body_capture[
            "values"
        ]
        bone_scales = body_capture[
            "bone_scales"
        ]
        existing_scaled = body_capture[
            "existing_scaled"
        ]
        expected_bone_keys = body_capture[
            "expected_bone_keys"
        ]
        body_capture = None

    else:
        values, _ = p03_capture_values(
            accepted
        )

    pid = u"preset-" + unicode(
        uuid.uuid4().hex
    )

    record = {
        "schema_version": 3,
        "record_kind": u"preset",
        "preset_id": pid,
        "character_key": prod_key(
            identity[
                "model"
            ]
        ),
        "kind": kind,
        "name": u(
            name_value
        ),
        "model_ref": {
            "path": prod_norm(
                identity[
                    "model"
                ]
            ),
            "capture_checksum": int(
                identity[
                    "checksum"
                ]
            ),
        },
        "capture_semantic_policy": PROD_SEMANTIC_POLICY,
        "capture_provider": prod_provider_capture(
            scope[
                "provider_descriptor"
            ]
        ),
        "created_at": p03_now_stamp(),
        "values": values,
    }

    if kind == P03_KIND_BODY:
        record[
            "bone_scales"
        ] = bone_scales
        record[
            "bone_scale_policy"
        ] = u"complete-native-bone-map-physical-uniform-v1"

    # Reject malformed/non-finite mutation-bearing values before durable write.
    prod_validate_preset(
        identity,
        record,
        kind,
    )

    if kind == P03_KIND_BODY:
        prod_validate_bone_scale_map_against_keys(
            bone_scales,
            expected_bone_keys,
        )

    prod_resource_snapshot(
        u"Q2_SAVE_AFTER_PURE_VALIDATION"
    )

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )

    prod_ensure_character(
        identity,
        authority_context=authority_context,
    )

    path = prod_unique_path(
        identity,
        kind,
        name_value,
        pid,
    )

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )

    p02_safe_write_json(
        path,
        record,
    )

    if phase_callback is not None:
        phase_callback(
            "durable-commit",
            {
                "path": path,
                "kind": kind,
                "preset_id": pid,
            },
        )

    prod_resource_snapshot(
        u"Q2_SAVE_AFTER_DURABLE_COMMIT"
    )

    loaded = p02_read_json(
        path
    )
    prod_validate_preset(
        identity,
        loaded,
        kind,
    )

    if kind == P03_KIND_BODY:
        prod_validate_bone_scale_map_against_keys(
            loaded.get(
                "bone_scales"
            ),
            expected_bone_keys,
        )

    if loaded != record:
        raise RuntimeError(
            "Saved preset did not read back exactly."
        )

    if phase_callback is not None:
        phase_callback(
            "durable-verified",
            {
                "path": path,
                "kind": kind,
                "preset_id": pid,
            },
        )

    prod_resource_snapshot(
        u"Q2_SAVE_AFTER_READBACK"
    )

    try:
        log_line(
            "PROD_SAVE=PASS model=%r kind=%r name=%r controls=%d "
            "bone_records=%d existing_scale_controls=%d path=%r "
            "cached_semantic_scope=True indexed_body_capture=%r q1_parity=%r"
            % (
                identity[
                    "model"
                ],
                kind,
                name_value,
                len(
                    accepted
                ),
                len(
                    bone_scales
                )
                if bone_scales is not None
                else 0,
                len(
                    existing_scaled
                ),
                path,
                (
                    kind
                    == P03_KIND_BODY
                ),
                (
                    PROD_Q1_INDEXED_CAPTURE_PARITY
                    if kind == P03_KIND_BODY
                    else False
                ),
            )
        )
    except Exception:
        pass


    return path




def prod_update_preset(
    identity,
    item,
    scope=None,
    phase_callback=None,
    operation_context=None,
):
    prod_resource_snapshot(
        u"Q2_UPDATE_POST_CONFIRM"
    )

    if (
        not isinstance(
            item,
            dict,
        )
        or item.get(
            "source"
        )
        != u"v3"
    ):
        raise RuntimeError(
            "Only current-library presets can be updated."
        )

    path = item.get(
        "path"
    )

    if (
        not path
        or not os.path.isfile(
            path
        )
    ):
        raise RuntimeError(
            "Preset file no longer exists."
        )

    cached_record = item.get(
        "record"
    ) or {}
    cached_kind = u(
        cached_record.get(
            "kind"
        )
    )

    record = prod_reread_selected_record(
        identity,
        item,
        cached_kind,
    )
    kind = u(
        record.get(
            "kind"
        )
    )

    expected_dir = os.path.normcase(
        os.path.abspath(
            prod_preset_dir(
                identity,
                kind,
            )
        )
    )
    actual_dir = os.path.normcase(
        os.path.abspath(
            os.path.dirname(
                path
            )
        )
    )

    if actual_dir != expected_dir:
        raise RuntimeError(
            "Preset is outside the selected model's current library."
        )

    if scope is None:
        scope = prod_scope(
            identity
        )

    # CPM Step 3: post-prompt authorization before durable replacement.
    authority_context = prod_cpm_authorize_operation(
        identity,
        scope,
        kind,
        u"Update Preset",
    )

    live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        kind,
        authority_context=authority_context,
    )
    accepted = live[
        "accepted"
    ]

    if not accepted:
        raise RuntimeError(
            "Selected model has no qualified controls for this preset type."
        )

    updated = dict(
        record
    )
    updated[
        "model_ref"
    ] = {
        "path": prod_norm(
            identity[
                "model"
            ]
        ),
        "capture_checksum": int(
            identity[
                "checksum"
            ]
        ),
    }
    updated[
        "capture_semantic_policy"
    ] = PROD_SEMANTIC_POLICY
    updated[
        "capture_provider"
    ] = prod_provider_capture(
        scope[
            "provider_descriptor"
        ]
    )
    updated[
        "modified_at"
    ] = p03_now_stamp()

    expected_bone_keys = None

    if kind == P03_KIND_BODY:
        body_capture = prod_capture_body_snapshot(
            identity,
            accepted,
            operation_context=operation_context,
        )
        values = body_capture[
            "values"
        ]
        bone_scales = body_capture[
            "bone_scales"
        ]
        existing_scaled = body_capture[
            "existing_scaled"
        ]
        expected_bone_keys = body_capture[
            "expected_bone_keys"
        ]
        body_capture = None

        updated[
            "values"
        ] = values
        updated[
            "bone_scales"
        ] = bone_scales
        updated[
            "bone_scale_policy"
        ] = u"complete-native-bone-map-physical-uniform-v1"

    else:
        values, _ = p03_capture_values(
            accepted
        )
        updated[
            "values"
        ] = values
        existing_scaled = []

    prod_validate_preset(
        identity,
        updated,
        kind,
    )

    if kind == P03_KIND_BODY:
        prod_validate_bone_scale_map_against_keys(
            updated.get(
                "bone_scales"
            ),
            expected_bone_keys,
        )

    prod_resource_snapshot(
        u"Q2_UPDATE_AFTER_PURE_VALIDATION"
    )

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )

    p02_safe_write_json(
        path,
        updated,
    )

    if phase_callback is not None:
        phase_callback(
            "durable-commit",
            {
                "path": path,
                "kind": kind,
                "preset_id": updated.get(
                    "preset_id"
                ),
            },
        )

    prod_resource_snapshot(
        u"Q2_UPDATE_AFTER_DURABLE_COMMIT"
    )

    loaded = p02_read_json(
        path
    )
    prod_validate_preset(
        identity,
        loaded,
        kind,
    )

    if kind == P03_KIND_BODY:
        prod_validate_bone_scale_map_against_keys(
            loaded.get(
                "bone_scales"
            ),
            expected_bone_keys,
        )

    if loaded != updated:
        raise RuntimeError(
            "Updated preset did not read back exactly."
        )

    if phase_callback is not None:
        phase_callback(
            "durable-verified",
            {
                "path": path,
                "kind": kind,
                "preset_id": updated.get(
                    "preset_id"
                ),
            },
        )

    prod_resource_snapshot(
        u"Q2_UPDATE_AFTER_READBACK"
    )

    try:
        log_line(
            "PROD_UPDATE=PASS model=%r kind=%r preset=%r controls=%d "
            "bone_records=%d existing_scale_controls=%d path=%r "
            "cached_semantic_scope=True indexed_body_capture=%r q1_parity=%r"
            % (
                identity[
                    "model"
                ],
                kind,
                updated.get(
                    "preset_id"
                ),
                len(
                    accepted
                ),
                len(
                    updated.get(
                        "bone_scales"
                    )
                    or []
                ),
                len(
                    existing_scaled
                ),
                path,
                (
                    kind
                    == P03_KIND_BODY
                ),
                (
                    PROD_Q1_INDEXED_CAPTURE_PARITY
                    if kind == P03_KIND_BODY
                    else False
                ),
            )
        )
    except Exception:
        pass


    return path



def prod_flex_record(record):
    r = dict(record); r["values"] = dict((u(k), v) for k, v in record["values"].items() if u(k).startswith(u"flex.")); return r



def prod_validate_scale_plan_finite(
    scale_plan,
):
    for item in scale_plan.get(
        "existing",
        [],
    ):
        desired_physical = as_float(
            item.get(
                "desired_physical"
            )
        )
        desired_native = as_float(
            item.get(
                "desired_native"
            )
        )
        binding = item.get(
            "binding"
        ) or {}
        lo = as_float(
            binding.get(
                "lo"
            )
        )
        hi = as_float(
            binding.get(
                "hi"
            )
        )

        if (
            desired_physical is None
            or desired_physical <= 0.0
            or desired_native is None
            or lo is None
            or hi is None
            or close_enough(
                lo,
                hi,
            )
        ):
            raise RuntimeError(
                "Bone-scale Apply contains an invalid or non-finite native conversion."
            )

    for item in scale_plan.get(
        "create",
        [],
    ):
        desired_physical = as_float(
            item.get(
                "desired_physical"
            )
        )

        if (
            desired_physical is None
            or desired_physical <= 0.0
        ):
            raise RuntimeError(
                "Bone-scale Apply contains an invalid or non-finite physical multiplier."
            )

    return True




class ProdRecoveryUnverifiedError(RuntimeError):
    """An owned native transaction failed and restoration could not be proven."""
    pass


def prod_optional_float_matches(
    observed,
    baseline,
):
    if (
        observed is None
        or baseline is None
    ):
        return (
            observed is None
            and baseline is None
        )

    return close_enough(
        observed,
        baseline,
    )


def prod_bs_snapshot_matches_baseline(
    observed,
    baseline,
):
    exact_fields = (
        "key_count",
        "is_empty",
        "input_mode",
        "output_mode",
        "control_id",
        "input_channel_id",
        "input_log_id",
        "input_layer_id",
        "expression_id",
        "output_id",
        "transform_id",
    )
    float_fields = (
        "source",
        "default",
        "expr_input",
        "expr_result",
        "physical_scale",
        "key_time",
        "key_value",
    )

    for field in exact_fields:
        if observed.get(
            field
        ) != baseline.get(
            field
        ):
            return False

    for field in float_fields:
        if not prod_optional_float_matches(
            observed.get(
                field
            ),
            baseline.get(
                field
            ),
        ):
            return False

    return True


def prod_verify_apply_abort_baseline(
    identity,
    kind,
    scope,
    built,
    scale_plan,
    authority_context=None,
):
    """Freshly verify only the state owned by the failed Apply transaction,
    against the operation's pinned authorized membership (CPM Step 3)."""
    live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        kind,
        authority_context=authority_context,
    )

    if not p03_verify_baselines(
        live[
            "accepted"
        ],
        built[
            "baselines"
        ],
    ):
        return False

    if kind != P03_KIND_BODY:
        return True

    post_snapshot = prod_bs_index_snapshot(
        identity
    )

    for item in scale_plan[
        "existing"
    ]:
        if not item.get(
            "needs_write"
        ):
            continue

        row = post_snapshot[
            "bone_index"
        ].get(
            item[
                "key"
            ]
        )

        if (
            row is None
            or row.get(
                "classification"
            )
            != "CHANNEL_DRIVEN_SCALE"
        ):
            return False

        binding = prod_bs_index_binding(
            post_snapshot,
            row,
        )
        observed = prod_bs_snapshot(
            binding
        )

        if not prod_bs_snapshot_matches_baseline(
            observed,
            item[
                "baseline"
            ],
        ):
            return False

    for item in scale_plan[
        "create"
    ]:
        row = post_snapshot[
            "bone_index"
        ].get(
            item[
                "key"
            ]
        )

        if row is None:
            return False

        # This helper proves the scale attribute, named control, expression,
        # input/output channels and graph attachments are absent again.
        restored_fixture = prod_bs_index_clean_fixture(
            post_snapshot,
            row,
        )

        if (
            restored_fixture.get(
                "baseline"
            )
            != item[
                "fixture"
            ].get(
                "baseline"
            )
        ):
            return False

    return True


def prod_abort_apply_and_verify(
    dm_obj,
    identity,
    kind,
    scope,
    built,
    scale_plan,
    original_error,
    authority_context=None,
):
    abort_error = None
    restored = False

    try:
        dm_obj.AbortUndoableOperation()

        same_time_refresh(
            float(
                sfmApp.GetHeadTimeInSeconds()
            ),
            "PROD_APPLY_ABORT",
        )

        restored = bool(
            prod_verify_apply_abort_baseline(
                identity,
                kind,
                scope,
                built,
                scale_plan,
                authority_context=authority_context,
            )
        )

    except Exception as exc:
        abort_error = exc
        restored = False

    try:
        log_line(
            "PROD_APPLY_ABORT_VERIFY restored=%r original_error=%r abort_or_verify_error=%r"
            % (
                restored,
                original_error,
                abort_error,
            )
        )
    except Exception:
        pass

    if not restored:
        raise ProdRecoveryUnverifiedError(
            "Preset Apply failed and recovery could not be verified. "
            "Inspect the model before retrying; use SFM Undo if an Apply entry is present."
        )

    return True


def prod_abort_fit_and_verify(
    dm_obj,
    plan,
    original_error,
):
    abort_error = None
    restored = False

    try:
        dm_obj.AbortUndoableOperation()

        same_time_refresh(
            float(
                sfmApp.GetHeadTimeInSeconds()
            ),
            "PROD_CLOTHING_FIT_ABORT",
        )

        restored = bool(
            p03_target_matches_baseline(
                plan
            )
        )

    except Exception as exc:
        abort_error = exc
        restored = False

    try:
        log_line(
            "PROD_CLOTHING_FIT_ABORT_VERIFY target=%r restored=%r original_error=%r abort_or_verify_error=%r"
            % (
                plan.get(
                    "identity"
                ),
                restored,
                original_error,
                abort_error,
            )
        )
    except Exception:
        pass

    if not restored:
        raise ProdRecoveryUnverifiedError(
            "Clothing Fit failed and recovery of the target could not be verified. "
            "Inspect that target before retrying."
        )

    return True



def prod_apply(
    identity,
    record,
    scope=None,
    phase_callback=None,
    operation_context=None,
):
    kind = u(record["kind"])

    if scope is None:
        scope = prod_scope(
            identity
        )

    # CPM Step 3: authorize once, before any mutation; postcommit and abort
    # verification consume this pinned context and never reacquire authority.
    authority_context = prod_cpm_authorize_operation(
        identity,
        scope,
        kind,
        u"Apply Preset",
    )
    live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        kind,
        authority_context=authority_context,
    )
    accepted = live[
        "accepted"
    ]

    flex = prod_flex_record(record)
    expected = set(
        u"flex." + x
        for x in accepted.keys()
    )
    actual = set(
        flex["values"].keys()
    )

    if expected != actual:
        raise RuntimeError(
            "This preset does not match the selected model's current sliders. Choose another preset or model."
        )

    if (
        record["values"].get(
            P04_SCALE_LOGICAL_ID
        )
        is not None
    ):
        raise RuntimeError(
            "This old test preset contains unsupported Head Scale data. Delete it and save a new Body Preset."
        )

    built = p03_build_plan(
        accepted,
        flex,
    )

    scale_plan = {
        "existing": [],
        "create": [],
    }

    pre_snapshot = None

    if kind == P03_KIND_BODY:
        pre_snapshot = prod_bs_index_snapshot(
            identity
        )

        scale_plan = prod_bs_index_build_plan(
            identity,
            record,
            pre_snapshot,
        )
        prod_validate_scale_plan_finite(
            scale_plan
        )

    changed_existing_scales = [
        item
        for item in scale_plan[
            "existing"
        ]
        if item[
            "needs_write"
        ]
    ]
    created_missing_scales = list(
        scale_plan[
            "create"
        ]
    )

    total = (
        built[
            "changed_sides"
        ]
        + len(
            changed_existing_scales
        )
        + len(
            created_missing_scales
        )
    )


    before = undo_state(
        "PROD_APPLY_UNDO_BEFORE"
    )

    if total == 0:
        if (
            undo_state(
                "PROD_APPLY_UNDO_AFTER_NOOP"
            )
            != before
        ):
            raise RuntimeError(
                "True no-op changed Undo state."
            )

        try:
            log_line(
                "PROD_APPLY outcome='no-op' model=%r kind=%r preset=%r"
                % (
                    identity[
                        "model"
                    ],
                    kind,
                    record.get(
                        "name"
                    ),
                )
            )
        except Exception:
            pass
        return prod_outcome(
            "no-op",
            native_committed=False,
            durable_persisted=False,
            verified=True,
        )

    dm_obj = dm()
    opened = False
    label = (
        u"Apply Body Preset"
        if kind == P03_KIND_BODY
        else u"Apply Expression"
    )


    try:
        dm_obj.StartUndo(
            b(label),
            b(
                u"Redo "
                + label
            ),
        )
        opened = True

        for item in created_missing_scales:
            prod_bs_create_graph(
                item[
                    "fixture"
                ],
                item[
                    "desired_physical"
                ],
            )

        for item in changed_existing_scales:
            prod_bs_write_existing_scale(
                item
            )

        for item in built[
            "plan"
        ]:
            if item[
                "needs_write"
            ]:
                write_side(
                    item[
                        "binding"
                    ],
                    item[
                        "side"
                    ],
                    item[
                        "origin"
                    ],
                    item[
                        "desired"
                    ],
                )

        if not p03_verify_saved_values(
            accepted,
            flex,
        ):
            raise RuntimeError(
                "Preset values failed precommit verification."
            )

        for item in changed_existing_scales:
            observed = prod_bs_snapshot(
                item[
                    "binding"
                ]
            )

            if not prod_bs_authored_matches(
                item[
                    "binding"
                ],
                observed,
                item[
                    "desired_native"
                ],
            ):
                raise RuntimeError(
                    "Bone %s failed precommit verification."
                    % item[
                        "bone_name"
                    ]
                )

        dm_obj.FinishUndo()
        opened = False

        if phase_callback is not None:
            phase_callback(
                "native-commit",
                {
                    "kind": kind,
                    "model": identity.get(
                        "model"
                    ),
                    "preset_id": record.get(
                        "preset_id"
                    ),
                },
            )

    except Exception as exc:
        if opened:
            prod_abort_apply_and_verify(
                dm_obj,
                identity,
                kind,
                scope,
                built,
                scale_plan,
                exc,
                authority_context=authority_context,
            )
            opened = False

        raise


    same_time_refresh(
        float(
            sfmApp.GetHeadTimeInSeconds()
        ),
        "PROD_APPLY",
    )

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )


    fresh_live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        kind,
        authority_context=authority_context,
    )
    fresh_accepted = fresh_live[
        "accepted"
    ]

    flex_ok = p03_verify_saved_values(
        fresh_accepted,
        flex,
    )

    if not flex_ok:
        try:
            log_line(
                "PROD_APPLY outcome='committed-unverified' reason='flex' "
                "model=%r kind=%r"
                % (
                    identity[
                        "model"
                    ],
                    kind,
                )
            )
        except Exception:
            pass
        return prod_outcome(
            "committed-unverified",
            native_committed=True,
            durable_persisted=False,
            verified=False,
            recovery=u"Use SFM Undo or inspect the result before retrying.",
        )

    scales_ok = True

    if kind == P03_KIND_BODY:
        post_snapshot = prod_bs_index_snapshot(
            identity
        )

        scales_ok = prod_bs_index_verify_saved(
            record,
            post_snapshot,
        )

    if not scales_ok:
        try:
            log_line(
                "PROD_APPLY outcome='committed-unverified' reason='bone-scales' "
                "model=%r"
                % identity[
                    "model"
                ]
            )
        except Exception:
            pass
        return prod_outcome(
            "committed-unverified",
            native_committed=True,
            durable_persisted=False,
            verified=False,
            recovery=u"Use SFM Undo or inspect the result before retrying.",
        )

    try:
        log_line(
            "PROD_APPLY outcome='committed' model=%r kind=%r preset=%r "
            "changed_sides=%d changed_existing_scales=%d created_missing_scales=%d"
            % (
                identity[
                    "model"
                ],
                kind,
                record.get(
                    "name"
                ),
                built[
                    "changed_sides"
                ],
                len(
                    changed_existing_scales
                ),
                len(
                    created_missing_scales
                ),
            )
        )
    except Exception:
        pass


    return prod_outcome(
        "committed-verified",
        native_committed=True,
        durable_persisted=False,
        verified=True,
    )


def prod_body_source(
    identity,
    scope=None,
    authority_context=None,
):
    if scope is None:
        scope = prod_scope(
            identity
        )

    live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        P03_KIND_BODY,
        authority_context=authority_context,
    )
    accepted = live[
        "accepted"
    ]

    if not accepted:
        raise RuntimeError(
            "The selected model has no Body flexes available for Clothing Fit."
        )

    values, snapshots = p03_capture_values(
        accepted
    )

    descriptors = dict(
        (
            literal,
            prod_binding_descriptor(
                binding
            ),
        )
        for literal, binding in accepted.items()
    )

    source_native = p03_native_index(
        live[
            "row"
        ][
            "gm"
        ]
    )

    # Pure retained baseline only: no DME bindings, provider objects, rows,
    # animation sets, channels, logs, or widgets survive into queued stages.
    return {
        "identity": dict(
            identity
        ),
        "scope_identity": {
            "authority": dict(
                scope[
                    "authority"
                ]
            ),
            "live_signature": dict(
                scope[
                    "live_signature"
                ]
            ),
            "body": dict(
                scope[
                    "body"
                ]
            ),
        },
        "source_descriptors": descriptors,
        "source_native": source_native,
        "source_snapshots": snapshots,
        "source_values": values,
    }



def prod_body_source_live_from_baseline(
    baseline,
    scope,
    authority_context=None,
    stage_authority=None,
):
    identity = baseline[
        "identity"
    ]
    live = prod_live_bindings_for_cached_scope(
        identity,
        scope,
        P03_KIND_BODY,
        authority_context=authority_context,
    )
    accepted = live[
        "accepted"
    ]

    observed_descriptors = dict(
        (
            literal,
            prod_binding_descriptor(
                binding
            ),
        )
        for literal, binding in accepted.items()
    )

    if observed_descriptors != baseline.get(
        "source_descriptors"
    ):
        raise RuntimeError(
            "The source Body FLEX representation changed while Clothing Fit was running."
        )

    if not p03_verify_baselines(
        accepted,
        baseline[
            "source_snapshots"
        ],
    ):
        raise RuntimeError(
            "The source body changed while Clothing Fit was running."
        )

    return {
        "identity": dict(
            identity
        ),
        # CPM Step 4: the target stage's held Gfit authority; without one,
        # the Step 2b fail-closed stand-in (no historical fallback).
        "provider": (
            stage_authority
            if stage_authority is not None
            else live[
                "provider"
            ]
        ),
        "accepted": accepted,
        "source_list": [
            accepted[
                key
            ]
            for key in sorted(
                accepted.keys()
            )
        ],
        "source_native": p03_native_index(
            live[
                "row"
            ][
                "gm"
            ]
        ),
        "source_snapshots": baseline[
            "source_snapshots"
        ],
    }



def prod_source_matches(
    baseline,
    scope,
):
    try:
        prod_body_source_live_from_baseline(
            baseline,
            scope,
        )
        return True
    except Exception:
        return False


def prod_match_candidates(source):
    result=[]
    for row in p03_model_animsets():
        if same_dme(source["row"]["animset"], row["animset"]): continue
        try: plan=g11a_safe_plan(source,row)
        except Exception: continue
        result.append({"identity":g11a_target_identity(row), "mappings":len(plan["mapping"]["mappings"]), "warnings":len(plan["warnings"])})
    return sorted(result,key=lambda x:(u(x["identity"]["name"]).lower(),u(x["identity"]["model"]).lower()))


def prod_apply_match(
    plan,
    phase_callback=None,
    operation_context=None,
):
    if plan[
        "changed_sides"
    ] == 0:
        return prod_outcome(
            "no-op",
            native_committed=False,
            verified=True,
            target_identity=plan.get(
                "identity"
            ),
        )

    label = (
        u"Clothing Fit: "
        + u(
            plan[
                "identity"
            ][
                "name"
            ]
        )
    )
    dm_obj = dm()
    opened = False

    try:
        dm_obj.StartUndo(
            b(
                label
            ),
            b(
                u"Redo "
                + label
            ),
        )
        opened = True

        for entry in plan[
            "entries"
        ]:
            for side_entry in entry[
                "sides"
            ]:
                if side_entry[
                    "needs_write"
                ]:
                    write_side(
                        entry[
                            "target_binding"
                        ],
                        side_entry[
                            "side"
                        ],
                        side_entry[
                            "origin"
                        ],
                        side_entry[
                            "desired"
                        ],
                    )

        for entry in plan[
            "entries"
        ]:
            observed = binding_snapshot(
                entry[
                    "target_binding"
                ]
            )

            for side_entry in entry[
                "sides"
            ]:
                if not matches_value(
                    observed[
                        "sides"
                    ][
                        side_entry[
                            "side_name"
                        ]
                    ],
                    side_entry[
                        "desired"
                    ],
                ):
                    raise RuntimeError(
                        "Clothing Fit write failed for %r."
                        % plan[
                            "identity"
                        ][
                            "name"
                        ]
                    )

        dm_obj.FinishUndo()
        opened = False

        if phase_callback is not None:
            phase_callback(
                "native-commit",
                {
                    "target_identity": dict(
                        plan[
                            "identity"
                        ]
                    ),
                    "kind": u"clothing-fit",
                },
            )

    except Exception as exc:
        if opened:
            prod_abort_fit_and_verify(
                dm_obj,
                plan,
                exc,
            )
            opened = False

        raise

    same_time_refresh(
        float(
            sfmApp.GetHeadTimeInSeconds()
        ),
        label,
    )

    if operation_context is not None:
        prod_validate_context_token(
            operation_context
        )

    return prod_outcome(
        "committed-verified",
        native_committed=True,
        verified=True,
        target_identity=plan.get(
            "identity"
        ),
    )


# Legacy standalone Match Clothing dialog removed in G17F.
# Production uses the persistent Clothing Fit tab in ProdWindow.



def prod_fit_expected_skip_error(exc):
    raw = u(
        exc
    )
    expected_fragments = (
        u"has no supported FLEX controls",
        u"has no established compatible Body mappings",
        u"has incompatible established mappings",
        u"has unqualified ambiguity",
        u"has unsupported state at",
    )

    return any(
        fragment in raw
        for fragment in expected_fragments
    )



def prod_operation_event_turn_sample(
    operation_id,
    label,
):
    try:
        log_line(
            "PROD_OPERATION_EVENT_TURN id=%d kind=%r run_id=%r pid=%d"
            % (
                int(operation_id),
                u(label),
                PROD_RUN_ID,
                PROD_PID,
            )
        )
    except Exception:
        pass
    prod_resource_snapshot(
        u"Q2_SETTLED_EVENT_TURN:%s"
        % u(label)
    )


class ProdWindow(QtGui.QDialog):
    def __init__(
        self,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )
        self.setAttribute(
            QtCore.Qt.WA_DeleteOnClose,
            True,
        )

        self.setWindowTitle(
            TOOL_NAME
        )

        # Use normal dialog chrome so Windows renders the project icon.
        # WindowStaysOnTopHint preserves the qualified persistent-palette
        # behavior; the Manager remains nonmodal.
        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowSystemMenuHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        self.setWindowModality(
            QtCore.Qt.NonModal
        )
        # Apply after setWindowFlags(): changing native window flags can
        # recreate the underlying window and discard a previously set icon.
        tool_apply_window_icon(
            self
        )
        self.setMinimumSize(
            540,
            650,
        )
        self.resize(
            580,
            800,
        )

        self.busy = False
        self.operation = None
        self.operation_generation = 0
        self.status_generation = 0
        self.closing_requested = False
        self.fit_stage_running = False

        # Foreign-modal priority.
        #
        # This timer is Qt-only: it must never dereference SFM document/shot/
        # model/control wrappers.  When a foreign application modal appears,
        # scene-facing activity is suspended before the always-on-top palette
        # is hidden.  CPM currently has no persistent scene polling timer;
        # queued Clothing Fit staging is the one asynchronous scene-facing
        # continuation and is deferred until the modal closes.
        self.modal_yield_active = False
        self.scene_activity_suspended = False
        self.modal_yield_was_visible = False
        self.modal_deferred_fit_stage = None
        self.modal_watch_timer = QtCore.QTimer(
            self
        )
        self.modal_watch_timer.setInterval(
            100
        )
        self.modal_watch_timer.timeout.connect(
            self.poll_foreign_modal
        )

        self.candidates = []
        self.identity = None
        self.scope = None
        self.body_items = []
        self.expr_items = []
        self.review_items = []
        self.review_item_widgets = {}
        self.review_pending_count = 0
        self.library_meta = None
        self.provider_health = None

        # Clothing Fit is a persistent main-window workflow.
        self.fit_active = False
        self.fit_generation = 0
        self.fit_source_baseline = None
        self.fit_selected_identities = []
        self.fit_identity_tokens = []
        self.fit_changed = []
        self.fit_unchanged = []
        self.fit_committed_order = []
        self.fit_partial = []
        self.fit_skipped = []
        self.fit_failed = []
        self.fit_unattempted = []

        outer = QtGui.QVBoxLayout(
            self
        )

        # Model-level controls.  Two compact rows keep the palette narrow
        # without reducing the established UI font size.
        model_row = QtGui.QHBoxLayout()
        model_row.addWidget(
            QtGui.QLabel(
                "<b>Character Model:</b>"
            )
        )

        self.combo = QtGui.QComboBox()
        self.combo.currentIndexChanged.connect(
            self.select_model
        )
        model_row.addWidget(
            self.combo,
            1,
        )
        outer.addLayout(
            model_row
        )

        utility_row = QtGui.QHBoxLayout()
        utility_row.addStretch(
            1
        )

        self.refresh = QtGui.QPushButton(
            "Refresh Model List"
        )
        self.refresh.setAutoDefault(
            False
        )
        self.refresh.setDefault(
            False
        )
        self.refresh.clicked.connect(
            self.populate
        )
        utility_row.addWidget(
            self.refresh
        )

        self.details = QtGui.QPushButton(
            "Model Info"
        )
        self.details.setAutoDefault(
            False
        )
        self.details.setDefault(
            False
        )
        self.details.clicked.connect(
            self.open_details
        )
        utility_row.addWidget(
            self.details
        )

        self.help_button = QtGui.QPushButton(
            "Help"
        )
        self.help_button.setAutoDefault(
            False
        )
        self.help_button.setDefault(
            False
        )
        self.help_button.clicked.connect(
            self.open_help
        )
        utility_row.addWidget(
            self.help_button
        )

        outer.addLayout(
            utility_row
        )

        # Internal compatibility label retained for logging/details only.
        self.coverage = QtGui.QLabel(
            ""
        )
        self.coverage.hide()

        self.tabs = QtGui.QTabWidget()
        tool_apply_tab_style(
            self.tabs
        )
        self.tabs.currentChanged.connect(
            self.tab_changed
        )
        outer.addWidget(
            self.tabs,
            1,
        )

        # Body Presets.
        self.body_page = QtGui.QWidget()
        body_layout = QtGui.QVBoxLayout(self.body_page)

        self.body_summary = QtGui.QLabel("")
        self.body_summary.setWordWrap(True)
        body_layout.addWidget(self.body_summary)

        body_library = QtGui.QHBoxLayout()
        self.body_search = QtGui.QLineEdit()
        self.body_search.setPlaceholderText("Search presets")
        self.body_search.textChanged.connect(lambda value: self.refresh_preset_view(P03_KIND_BODY))
        body_library.addWidget(self.body_search, 1)
        body_library.addWidget(QtGui.QLabel("Sort:"))
        self.body_sort = QtGui.QComboBox()
        self.body_sort.addItems(["Name", "Recent"])
        self.body_sort.currentIndexChanged.connect(lambda index: self.refresh_preset_view(P03_KIND_BODY))
        body_library.addWidget(self.body_sort)
        self.body_favorites_only = QtGui.QCheckBox("Favorites only")
        self.body_favorites_only.toggled.connect(lambda checked: self.refresh_preset_view(P03_KIND_BODY))
        body_library.addWidget(self.body_favorites_only)
        body_layout.addLayout(body_library)

        self.body_list = QtGui.QListWidget()
        tool_apply_preset_list_style(self.body_list)
        self.body_list.currentRowChanged.connect(lambda row: self.preset_selection_changed(P03_KIND_BODY))
        body_layout.addWidget(self.body_list, 1)

        body_primary = QtGui.QHBoxLayout()
        self.apply_body = QtGui.QPushButton("Apply Preset")
        tool_apply_semantic_action_button(self.apply_body, u"primary")
        self.apply_body.clicked.connect(lambda: self.apply_kind(P03_KIND_BODY))
        body_primary.addWidget(self.apply_body)
        self.save_body = QtGui.QPushButton("Save New")
        tool_apply_main_action_button(self.save_body)
        self.save_body.clicked.connect(lambda: self.save_kind(P03_KIND_BODY))
        body_primary.addWidget(self.save_body)
        self.update_body = QtGui.QPushButton("Update Preset")
        tool_apply_main_action_button(self.update_body)
        self.update_body.clicked.connect(lambda: self.update_kind(P03_KIND_BODY))
        body_primary.addWidget(self.update_body)
        body_layout.addLayout(body_primary)

        body_secondary = QtGui.QHBoxLayout()
        self.favorite_body = QtGui.QPushButton("Add Favorite")
        tool_apply_semantic_action_button(self.favorite_body, u"favorite")
        self.favorite_body.clicked.connect(lambda: self.toggle_favorite(P03_KIND_BODY))
        body_secondary.addWidget(self.favorite_body, 1)
        self.info_body = QtGui.QPushButton("Preset Info")
        tool_apply_secondary_action_button(self.info_body)
        self.info_body.clicked.connect(lambda: self.open_preset_info(P03_KIND_BODY))
        body_secondary.addWidget(self.info_body, 1)
        self.delete_body = QtGui.QPushButton("Delete Preset")
        tool_apply_semantic_action_button(self.delete_body, u"destructive")
        self.delete_body.clicked.connect(lambda: self.delete_kind(P03_KIND_BODY))
        body_secondary.addWidget(self.delete_body, 1)
        body_layout.addLayout(body_secondary)

        self.tabs.addTab(self.body_page, "Body Presets")

        # Expressions.
        self.expr_page = QtGui.QWidget()
        expr_layout = QtGui.QVBoxLayout(self.expr_page)

        self.expr_summary = QtGui.QLabel("")
        self.expr_summary.setWordWrap(True)
        expr_layout.addWidget(self.expr_summary)

        expr_library = QtGui.QHBoxLayout()
        self.expr_search = QtGui.QLineEdit()
        self.expr_search.setPlaceholderText("Search presets")
        self.expr_search.textChanged.connect(lambda value: self.refresh_preset_view(P03_KIND_EXPRESSION))
        expr_library.addWidget(self.expr_search, 1)
        expr_library.addWidget(QtGui.QLabel("Sort:"))
        self.expr_sort = QtGui.QComboBox()
        self.expr_sort.addItems(["Name", "Recent"])
        self.expr_sort.currentIndexChanged.connect(lambda index: self.refresh_preset_view(P03_KIND_EXPRESSION))
        expr_library.addWidget(self.expr_sort)
        self.expr_favorites_only = QtGui.QCheckBox("Favorites only")
        self.expr_favorites_only.toggled.connect(lambda checked: self.refresh_preset_view(P03_KIND_EXPRESSION))
        expr_library.addWidget(self.expr_favorites_only)
        expr_layout.addLayout(expr_library)

        self.expr_list = QtGui.QListWidget()
        tool_apply_preset_list_style(self.expr_list)
        self.expr_list.currentRowChanged.connect(lambda row: self.preset_selection_changed(P03_KIND_EXPRESSION))
        expr_layout.addWidget(self.expr_list, 1)

        expr_primary = QtGui.QHBoxLayout()
        self.apply_expr = QtGui.QPushButton("Apply Preset")
        tool_apply_semantic_action_button(self.apply_expr, u"primary")
        self.apply_expr.clicked.connect(lambda: self.apply_kind(P03_KIND_EXPRESSION))
        expr_primary.addWidget(self.apply_expr)
        self.save_expr = QtGui.QPushButton("Save New")
        tool_apply_main_action_button(self.save_expr)
        self.save_expr.clicked.connect(lambda: self.save_kind(P03_KIND_EXPRESSION))
        expr_primary.addWidget(self.save_expr)
        self.update_expr = QtGui.QPushButton("Update Preset")
        tool_apply_main_action_button(self.update_expr)
        self.update_expr.clicked.connect(lambda: self.update_kind(P03_KIND_EXPRESSION))
        expr_primary.addWidget(self.update_expr)
        expr_layout.addLayout(expr_primary)

        expr_secondary = QtGui.QHBoxLayout()
        self.favorite_expr = QtGui.QPushButton("Add Favorite")
        tool_apply_semantic_action_button(self.favorite_expr, u"favorite")
        self.favorite_expr.clicked.connect(lambda: self.toggle_favorite(P03_KIND_EXPRESSION))
        expr_secondary.addWidget(self.favorite_expr, 1)
        self.info_expr = QtGui.QPushButton("Preset Info")
        tool_apply_secondary_action_button(self.info_expr)
        self.info_expr.clicked.connect(lambda: self.open_preset_info(P03_KIND_EXPRESSION))
        expr_secondary.addWidget(self.info_expr, 1)
        self.delete_expr = QtGui.QPushButton("Delete Preset")
        tool_apply_semantic_action_button(self.delete_expr, u"destructive")
        self.delete_expr.clicked.connect(lambda: self.delete_kind(P03_KIND_EXPRESSION))
        expr_secondary.addWidget(self.delete_expr, 1)
        expr_layout.addLayout(expr_secondary)

        self.tabs.addTab(self.expr_page, "Expressions")

        # Clothing Fit.
        self.fit_page = QtGui.QWidget()
        fit_layout = QtGui.QVBoxLayout(self.fit_page)
        fit_note = QtGui.QLabel("Match selected clothing to this model\'s body shape.")
        fit_note.setWordWrap(True)
        fit_layout.addWidget(fit_note)

        self.fit_tree = QtGui.QTreeWidget()
        self.fit_tree.setHeaderHidden(True)
        self.fit_tree.setRootIsDecorated(True)
        self.fit_tree.setAlternatingRowColors(False)
        self.fit_tree.itemChanged.connect(self.fit_selection_changed)
        fit_layout.addWidget(self.fit_tree, 1)

        fit_actions = QtGui.QHBoxLayout()
        self.fit_button = QtGui.QPushButton("Fit Selected to Model")
        tool_apply_semantic_action_button(self.fit_button, u"primary")
        self.fit_button.setEnabled(False)
        self.fit_button.clicked.connect(self.fit_selected)
        fit_actions.addWidget(self.fit_button)
        fit_actions.addStretch(1)
        fit_layout.addLayout(fit_actions)
        self.tabs.addTab(self.fit_page, "Clothing Fit")

        # Review is shown only when there is actionable content.
        self.review_page = QtGui.QWidget()
        review_layout = QtGui.QVBoxLayout(
            self.review_page
        )

        review_note = QtGui.QLabel(
            "Unrecognized flexes appear under Needs review. "
            "Classify each flex as Body, Expression, or Excluded."
        )
        review_note.setWordWrap(
            True
        )
        review_layout.addWidget(
            review_note
        )

        self.review_master_warning = QtGui.QLabel(
            PROD_MASTER_REVIEW_WARNING_COPY
        )
        self.review_master_warning.setWordWrap(
            True
        )
        tool_set_status(
            self.review_master_warning,
            PROD_MASTER_REVIEW_WARNING_COPY,
            u"warning",
        )
        self.review_master_warning.hide()
        review_layout.addWidget(
            self.review_master_warning
        )

        self.review = QtGui.QTreeWidget()
        self.review.setHeaderHidden(
            True
        )
        self.review.setRootIsDecorated(
            True
        )
        self.review.setAlternatingRowColors(
            False
        )
        self.review.setStyleSheet(
            """
            QTreeWidget::item:selected {
                background-color: #2f76b5;
                color: #ffffff;
            }
            """
        )
        self.review.currentItemChanged.connect(
            self.review_changed
        )
        review_layout.addWidget(
            self.review,
            1,
        )

        # Two rows: the existing order, carried into a 2x2 grid.
        review_actions = QtGui.QGridLayout()

        self.mark_expr = QtGui.QPushButton(
            "Classify as Expression"
        )
        self.mark_expr.setAutoDefault(
            False
        )
        self.mark_expr.clicked.connect(
            lambda: self.review_decision(
                u"expression"
            )
        )
        review_actions.addWidget(
            self.mark_expr,
            0, 0,
        )

        self.mark_body = QtGui.QPushButton(
            "Classify as Body"
        )
        self.mark_body.setAutoDefault(
            False
        )
        self.mark_body.clicked.connect(
            lambda: self.review_decision(
                u"body"
            )
        )
        review_actions.addWidget(
            self.mark_body,
            0, 1,
        )

        self.mark_out = QtGui.QPushButton(
            "Exclude from Presets"
        )
        self.mark_out.setAutoDefault(
            False
        )
        self.mark_out.clicked.connect(
            lambda: self.review_decision(
                u"exclude"
            )
        )
        review_actions.addWidget(
            self.mark_out,
            1, 0,
        )

        self.reclassify_flex = QtGui.QPushButton(
            "Clear Classification"
        )
        self.reclassify_flex.setAutoDefault(
            False
        )
        self.reclassify_flex.setEnabled(
            False
        )
        self.reclassify_flex.clicked.connect(
            self.review_reclassify
        )
        review_actions.addWidget(
            self.reclassify_flex,
            1, 1,
        )

        review_layout.addLayout(
            review_actions
        )

        self.tabs.addTab(
            self.review_page,
            "Review",
        )

        # The state/action readout remains a permanent bottom pane.
        self.status = QtGui.QLabel(
            ""
        )
        self.status.setWordWrap(
            True
        )
        outer.addWidget(
            self.status
        )

        tool_apply_visual_theme(
            self
        )
        tool_apply_dialog_font(
            self
        )

        # Main window Enter/Return must never activate an action button.
        for button in self.findChildren(
            QtGui.QPushButton
        ):
            button.setAutoDefault(
                False
            )
            button.setDefault(
                False
            )

        # CPM Step 2b: the development decision-parity shortcut (historical
        # TXT + development-sidecar providers) is not bound in the migrated
        # production window. The handler is retained, unreachable.
        self.g18an_parity_shortcut = None

        self.populate()

        # Start last, after construction/population is complete.  While a
        # foreign modal is present this remains the only persistent CPM timer.
        self.modal_watch_timer.start()
        try:
            log_line(
                "G18AN_MODAL_WATCHER_STARTED interval_ms=%d scene_pollers=0"
                % self.modal_watch_timer.interval()
            )
        except Exception:
            pass

    def modal_is_owned_by_manager(
        self,
        modal,
    ):
        """Qt-only ownership test; do not inspect SFM scene state here."""
        if modal is None:
            return False

        if modal is self:
            return True

        try:
            if self.isAncestorOf(
                modal
            ):
                return True
        except Exception:
            pass

        # Be conservative for top-level child dialogs whose QWidget ancestry
        # may be represented differently after native window creation.
        current = modal

        for _index in range(
            32
        ):
            try:
                current = current.parentWidget()
            except Exception:
                current = None

            if current is None:
                break

            if current is self:
                return True

        return False

    def suspend_scene_activity_for_foreign_modal(
        self,
    ):
        # Python-owned gate is published first.  Any future persistent
        # scene/context watcher must be stopped from this method before hide().
        self.scene_activity_suspended = True

    def resume_scene_activity_after_foreign_modal(
        self,
    ):
        if self.closing_requested:
            return

        self.scene_activity_suspended = False

        pending = self.modal_deferred_fit_stage
        self.modal_deferred_fit_stage = None

        if pending is None:
            return

        generation, index = pending

        if (
            not self.fit_active
            or generation != self.fit_generation
            or self.operation is None
        ):
            return

        try:
            log_line(
                "G18AN_MODAL_RESUME_FIT generation=%d index=%d"
                % (
                    generation,
                    index,
                )
            )
        except Exception:
            pass

        QtCore.QTimer.singleShot(
            0,
            lambda g=generation, i=index: self.fit_stage(
                g,
                i,
            ),
        )

    def poll_foreign_modal(
        self,
    ):
        """Qt-only watcher giving every foreign application modal priority."""
        if self.closing_requested:
            try:
                self.modal_watch_timer.stop()
            except Exception:
                pass
            return

        app = QtGui.QApplication.instance()

        if app is None:
            return

        try:
            modal = app.activeModalWidget()
        except Exception:
            modal = None

        foreign_modal = (
            modal is not None
            and not self.modal_is_owned_by_manager(
                modal
            )
        )

        if foreign_modal:
            if not self.modal_yield_active:
                # Required ordering: suspend every scene-facing continuation
                # before removing the palette from view.
                self.modal_yield_active = True
                self.suspend_scene_activity_for_foreign_modal()

                try:
                    self.modal_yield_was_visible = bool(
                        self.isVisible()
                    )
                except Exception:
                    self.modal_yield_was_visible = True

                try:
                    modal_class = u(
                        type(
                            modal
                        ).__name__
                    )
                except Exception:
                    modal_class = u"<unknown>"

                try:
                    modal_title = u(
                        modal.windowTitle()
                    )
                except Exception:
                    modal_title = u""

                try:
                    log_line(
                        "G18AN_MODAL_YIELD_ENTER class=%r title=%r "
                        "was_visible=%r operation=%r fit_active=%r"
                        % (
                            modal_class,
                            modal_title,
                            self.modal_yield_was_visible,
                            (
                                None
                                if self.operation is None
                                else self.operation.get(
                                    "kind"
                                )
                            ),
                            self.fit_active,
                        )
                    )
                except Exception:
                    pass

                if self.modal_yield_was_visible:
                    try:
                        self.hide()
                    except Exception:
                        pass

            return

        if not self.modal_yield_active:
            return

        restore_visible = bool(
            self.modal_yield_was_visible
        )

        self.modal_yield_active = False
        self.modal_yield_was_visible = False

        if (
            restore_visible
            and not self.closing_requested
        ):
            try:
                # Deliberately no raise_() and no activateWindow(): the user's
                # native modal action keeps focus priority after dismissal.
                self.show()
            except Exception:
                pass

        try:
            log_line(
                "G18AN_MODAL_YIELD_EXIT restored=%r deferred_fit=%r"
                % (
                    restore_visible,
                    self.modal_deferred_fit_stage,
                )
            )
        except Exception:
            pass

        # Resume scene-facing work only after the palette has been restored.
        self.resume_scene_activity_after_foreign_modal()

    def keyPressEvent(
        self,
        event,
    ):
        if event.key() in (
            QtCore.Qt.Key_Return,
            QtCore.Qt.Key_Enter,
        ):
            event.accept()
            return

        QtGui.QDialog.keyPressEvent(
            self,
            event,
        )

    def reject(
        self,
    ):
        # R15 -- pre-existing Escape/reject teardown defect, discovered during
        # R15 (not the shared-namespace defect). Base rejection hid the window
        # without closeEvent teardown; route it through close() so the
        # operation-unwind/deferred-close branches below stay authoritative.
        self.close()

    def set_status(
        self,
        text,
        level=u"neutral",
    ):
        self.status_generation = int(
            getattr(
                self,
                "status_generation",
                0,
            )
        ) + 1
        generation = self.status_generation

        tool_set_status(
            self.status,
            text,
            level,
        )

        health = getattr(
            self,
            "provider_health",
            None,
        )

        if (
            isinstance(
                health,
                dict,
            )
            and health.get(
                "status"
            )
            != u"healthy"
            and u(
                text
            )
            != PROD_MASTER_PROVIDER_WARNING_COPY
        ):
            try:
                QtCore.QTimer.singleShot(
                    4500,
                    lambda g=generation: self.restore_provider_warning_if_idle(
                        g
                    ),
                )
            except Exception:
                pass


    def restore_provider_warning_if_idle(
        self,
        generation,
    ):
        # Python-owned close flag is checked before any Qt access/reschedule.
        if getattr(
            self,
            "closing_requested",
            False,
        ):
            return

        if (
            int(
                generation
            )
            != int(
                getattr(
                    self,
                    "status_generation",
                    0,
                )
            )
        ):
            return

        health = getattr(
            self,
            "provider_health",
            None,
        )

        if (
            not isinstance(
                health,
                dict,
            )
            or health.get(
                "status"
            )
            == u"healthy"
        ):
            return

        if getattr(
            self,
            "operation",
            None,
        ) is not None:
            if getattr(
                self,
                "closing_requested",
                False,
            ):
                return

            try:
                QtCore.QTimer.singleShot(
                    1000,
                    lambda g=generation: self.restore_provider_warning_if_idle(
                        g
                    ),
                )
            except Exception:
                pass
            return

        self.status_generation += 1
        tool_set_status(
            self.status,
            PROD_MASTER_PROVIDER_WARNING_COPY,
            u"warning",
        )


    def operation_begin(
        self,
        label,
        pin_context=True,
    ):
        if self.scene_activity_suspended:
            try:
                log_line(
                    "G18AN_OPERATION_BLOCKED_MODAL kind=%r"
                    % u(
                        label
                    )
                )
            except Exception:
                pass
            return False

        if self.operation is not None:
            return False

        self.operation_generation += 1
        context = None

        if (
            pin_context
            and self.identity is not None
        ):
            context = prod_context_token(
                self.identity
            )

        self.operation = {
            "operation_id": int(
                self.operation_generation
            ),
            "generation": int(
                self.operation_generation
            ),
            "kind": u(
                label
            ),
            "phase": u"BEGIN",
            "context": context,
            "native_commit": None,
            "durable_commit": None,
            "durable_verified": None,
            "closing_requested": False,
        }
        self.busy = True

        try:
            log_line(
                "PROD_OPERATION_BEGIN id=%d kind=%r context=%r"
                % (
                    self.operation[
                        "operation_id"
                    ],
                    self.operation[
                        "kind"
                    ],
                    context,
                )
            )
        except Exception:
            pass


        return True


    def operation_mark_phase(
        self,
        phase,
        detail=None,
    ):
        if self.operation is None:
            return

        phase = u(
            phase
        )
        self.operation[
            "phase"
        ] = phase

        if phase == u"native-commit":
            self.operation[
                "native_commit"
            ] = dict(
                detail
                or {}
            )
        elif phase == u"durable-commit":
            self.operation[
                "durable_commit"
            ] = dict(
                detail
                or {}
            )
        elif phase == u"durable-verified":
            self.operation[
                "durable_verified"
            ] = dict(
                detail
                or {}
            )

        try:
            log_line(
                "PROD_OPERATION_PHASE id=%d phase=%r detail=%r"
                % (
                    self.operation[
                        "operation_id"
                    ],
                    phase,
                    detail,
                )
            )
        except Exception:
            pass


    def operation_revalidate(
        self,
    ):
        if (
            self.operation is not None
            and self.operation.get(
                "context"
            )
            is not None
        ):
            prod_validate_context_token(
                self.operation[
                    "context"
                ]
            )

        return True


    def operation_commit_state(
        self,
    ):
        if self.operation is None:
            return {
                "native_committed": False,
                "native_commit": None,
                "durable_persisted": False,
                "durable_commit": None,
                "durable_verified": False,
                "durable_verified_detail": None,
            }

        return {
            "native_committed": (
                self.operation.get(
                    "native_commit"
                )
                is not None
            ),
            "native_commit": self.operation.get(
                "native_commit"
            ),
            "durable_persisted": (
                self.operation.get(
                    "durable_commit"
                )
                is not None
            ),
            "durable_commit": self.operation.get(
                "durable_commit"
            ),
            "durable_verified": (
                self.operation.get(
                    "durable_verified"
                )
                is not None
            ),
            "durable_verified_detail": self.operation.get(
                "durable_verified"
            ),
        }


    def operation_end(
        self,
        label,
    ):
        operation = self.operation

        if operation is None:
            self.busy = False
            return

        operation_id = int(
            operation.get(
                "operation_id"
            )
            or 0
        )
        final_phase = operation.get(
            "phase"
        )
        native_commit = operation.get(
            "native_commit"
        )
        durable_commit = operation.get(
            "durable_commit"
        )

        self.operation = None
        self.busy = False

        try:
            log_line(
                "PROD_OPERATION_END id=%d kind=%r phase=%r native_commit=%r durable_commit=%r"
                % (
                    operation_id,
                    u(
                        label
                    ),
                    final_phase,
                    native_commit,
                    durable_commit,
                )
            )
        except Exception:
            pass


        try:
            QtCore.QTimer.singleShot(
                0,
                lambda l=u(label), oid=operation_id: prod_operation_event_turn_sample(
                    oid,
                    l,
                ),
            )
        except Exception:
            pass

        if self.closing_requested:
            try:
                QtCore.QTimer.singleShot(
                    0,
                    self.close,
                )
            except Exception:
                pass


    def operation_durable_error_copy(
        self,
        label,
        commit_state,
    ):
        verified = bool(
            commit_state.get(
                "durable_verified"
            )
        )
        detail = (
            commit_state.get(
                "durable_verified_detail"
            )
            or commit_state.get(
                "durable_commit"
            )
            or {}
        )
        kind = u(
            detail.get(
                "kind"
            )
            or u""
        )

        if label in (
            "Save Current Body",
            "Save Current Expression",
        ):
            if verified:
                return (
                    "Preset saved",
                    "The preset was saved and verified, but the Manager could not refresh its list. Reopen the Manager to see it.",
                )
            return (
                "Preset write needs verification",
                "A preset file was written, but readback verification did not finish. Reopen the Manager and inspect the preset before retrying.",
            )

        if label == "Update Preset":
            if verified:
                return (
                    "Preset updated",
                    "The preset update was saved and verified, but the Manager could not refresh its list. Reopen the Manager to see the updated preset.",
                )
            return (
                "Preset update needs verification",
                "The preset file was updated, but readback verification did not finish. Reopen the Manager and inspect it before retrying.",
            )

        if (
            label == "Favorite Preset"
            or kind == u"library-metadata"
        ):
            if verified:
                return (
                    "Favorite change saved",
                    "The Favorite change was saved and verified, but the Manager could not refresh its list. Reopen the Manager to see it.",
                )
            return (
                "Favorite change needs verification",
                "Favorite metadata was written, but readback verification did not finish. Reopen the Manager before retrying.",
            )

        if (
            label == "Delete Preset"
            or kind == u"trash-move"
        ):
            if verified:
                return (
                    "Preset moved to Trash",
                    "The preset was moved to Trash and the move was verified, but the Manager could not refresh its list. Reopen the Manager to continue.",
                )
            return (
                "Trash move needs verification",
                "The preset move to Trash completed, but verification did not finish. Check the Trash folder before retrying.",
            )

        if label in (
            "Review Flex",
            "Reclassify Flex",
        ) or kind in (
            u"semantic-override",
            u"semantic-override-clear",
        ):
            if verified:
                return (
                    "Flex choice saved",
                    "The flex classification change was saved and verified, but the Manager could not refresh Review. Reopen the Manager to continue.",
                )
            return (
                "Flex choice needs verification",
                "The flex classification file was written, but readback verification did not finish. Reopen the Manager and inspect Review before retrying.",
            )

        if verified:
            return (
                "Change saved",
                "The durable change was saved and verified, but the Manager could not refresh. Reopen the Manager to continue.",
            )

        return (
            "Saved change needs verification",
            "A durable change was written, but readback verification did not finish. Reopen the Manager and inspect the result before retrying.",
        )


    def operation_default_error_copy(
        self,
        label,
        raw,
    ):
        if (
            " already exists. Choose a different name."
            in raw
        ):
            return (
                "Name already in use",
                raw,
            )

        if label in (
            "Save Current Body",
            "Save Current Expression",
        ):
            return (
                "Can't save preset",
                "Preset could not be saved. Nothing was saved.",
            )

        if (
            label
            in (
                "Apply Body Preset",
                "Apply Expression",
            )
            and raw
            == u"This preset does not match the selected model's current sliders. Choose another preset or model."
        ):
            if label == "Apply Body Preset":
                return (
                    "Preset doesn't match current Body controls",
                    "This preset was not applied because this model's Body controls have changed since it was saved.\n\n"
                    "Check Review for unclassified flexes. If none are listed, this preset is no longer compatible; "
                    "use or create a Body Preset for the model's current controls.",
                )

            return (
                "Preset doesn't match current Expression controls",
                "This preset was not applied because this model's Expression controls have changed since it was saved.\n\n"
                "Check Review for unclassified flexes. If none are listed, this preset is no longer compatible; "
                "use or create an Expression preset for the model's current controls.",
            )

        if label in (
            "Apply Body Preset",
            "Apply Expression",
        ):
            return (
                "Can't apply preset",
                "Preset could not be applied safely. This preset was not applied.",
            )

        if label == "Update Preset":
            return (
                "Can't update preset",
                "Preset could not be updated. Nothing was replaced.",
            )

        if label == "Favorite Preset":
            return (
                "Can't change Favorite",
                "Favorite could not be changed. Try again.",
            )

        if label == "Delete Preset":
            return (
                "Can't delete preset",
                "Preset could not be moved to Trash. Try again.",
            )

        if label == "Refresh Models":
            return (
                "Can't refresh model list",
                "Model list could not be refreshed. Try again.",
            )

        if label == "Select Model":
            return (
                "Can't use this model",
                "This model could not be loaded. Refresh and try again.",
            )

        if label == "Clear Model":
            return (
                "Can't clear model selection",
                "The model selection could not be cleared safely. Try again.",
            )

        if label == "Review Flex":
            return (
                "Can't save flex choice",
                "Flex choice could not be saved. Try again.",
            )

        if label == "Reclassify Flex":
            return (
                "Can't clear classification",
                "The saved flex classification could not be cleared. Try again.",
            )

        if label == "Model Info":
            return (
                "Can't open Model Info",
                "Model Info could not open. Try again.",
            )

        if label == "Preset Info":
            return (
                "Can't open Preset Info",
                "Preset Info could not open. Try again.",
            )

        if label == "Help":
            return (
                "Can't open Help",
                "Help could not open. Try again.",
            )

        return (
            "Action could not finish",
            "Try again.",
        )




    def open_master_page(
        self,
    ):
        opened = QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(
                PROD_MASTER_GITHUB_URL
            )
        )
        try:
            log_line(
                "PROD_HELP_MASTER_LINK result=%r url=%r"
                % (
                    bool(opened),
                    PROD_MASTER_GITHUB_URL,
                )
            )
        except Exception:
            pass
        if not opened:
            tool_warning_message(
                self,
                "Can't open GitHub",
                "The Animation Groups Master page could not open.",
            )
        return bool(opened)


    def prod_cpm_request_stale_rebuild_if_needed(
        self,
    ):
        """CPM Step 2b plumbing for handoff section 13. If the selected scope's
        generation is no longer current, schedule one rebuild of the current
        selection through the existing select-model path. Neutral: no status
        text or UI state of its own. Never replays an action."""
        if getattr(self, "_cpm_stale_rebuild_pending", False):
            return False
        if self.scope is None or self.identity is None:
            return False
        if not prod_cpm_scope_generation_stale(self.scope):
            return False
        self._cpm_stale_rebuild_pending = True
        try:
            log_line(
                "PROD_CPM_STALE_GENERATION_REBUILD_SCHEDULED identity=%r"
                % (self.identity,)
            )
        except Exception:
            pass
        QtCore.QTimer.singleShot(
            0,
            self.prod_cpm_run_stale_rebuild,
        )
        return True

    def prod_cpm_run_stale_rebuild(
        self,
    ):
        if self.operation is not None or self.fit_active:
            QtCore.QTimer.singleShot(
                250,
                self.prod_cpm_run_stale_rebuild,
            )
            return False
        self._cpm_stale_rebuild_pending = False
        if self.identity is None:
            return False
        if self.scope is not None and not prod_cpm_scope_generation_stale(self.scope):
            return False
        # Discard the stale scope, then acquire current authority and rebuild
        # and republish through the existing selection path.
        self.scope = None
        try:
            log_line(
                "PROD_CPM_STALE_GENERATION_REBUILD identity=%r"
                % (self.identity,)
            )
        except Exception:
            pass
        self.select_model(
            self.combo.currentIndex()
        )
        return True

    def semantic_provider_ready(
        self,
    ):
        ready = bool(
            isinstance(
                self.provider_health,
                dict,
            )
            and self.provider_health.get("status") == u"healthy"
            and self.scope is not None
            and self.identity is not None
            and prod_scope_matches_identity(
                self.scope,
                self.identity,
            )
        )
        if (
            not ready
            and self.scope is not None
            and self.identity is not None
        ):
            self.prod_cpm_request_stale_rebuild_if_needed()
        return ready


    def set_master_warning_visible(
        self,
        visible,
    ):
        # G18L: global provider failure warnings live only in the bottom status panel.
        # Keep this compatibility hook so provider-state call sites stay stable.
        return None


    def apply_provider_unavailable_to_ui(
        self,
        health,
    ):
        self.provider_health = dict(
            health or {}
        )
        self.scope = None

        self.review.blockSignals(
            True
        )
        self.review.clear()
        self.review.blockSignals(
            False
        )
        self.review_items = []
        self.review_item_widgets = {}
        self.review_pending_count = 0
        self.sync_review_tab()

        self.coverage.setText(
            "Animation Groups Master unavailable."
        )
        self.body_summary.setText(
            "Save body flexes and bone scaling for this model."
        )
        self.expr_summary.setText(
            "Save facial flexes for this model."
        )
        self.review_master_warning.hide()

        self.fit_tree.clear()
        self.fit_tree.setEnabled(
            False
        )
        self.fit_button.setEnabled(
            False
        )
        self.details.setEnabled(
            False
        )

        self.disable_semantic_scene_actions()
        self.update_action_buttons()
        self.set_master_warning_visible(
            True
        )
        self.set_status(
            PROD_MASTER_PROVIDER_WARNING_COPY,
            u"warning",
        )

        try:
            log_line(
                "PROD_PROVIDER_GATE state=%r reason=%r review_rows=0 "
                "semantic_actions=False library_actions_preserved=True"
                % (
                    self.provider_health.get("status"),
                    self.provider_health.get("reason"),
                )
            )
        except Exception:
            pass


    def disable_semantic_scene_actions(
        self,
    ):
        for widget in (
            self.save_body,
            self.apply_body,
            self.update_body,
            self.save_expr,
            self.apply_expr,
            self.update_expr,
            self.fit_button,
        ):
            try:
                widget.setEnabled(
                    False
                )
            except Exception:
                pass

        self.set_review_enabled(
            False
        )



    def sync_review_tab(
        self,
    ):
        pending = int(
            self.review_pending_count
            or 0
        )
        has_content = bool(
            self.review_items
        )
        index = self.tabs.indexOf(
            self.review_page
        )

        if has_content:
            title = (
                "Review (%d)"
                % pending
                if pending > 0
                else "Review"
            )

            if index < 0:
                self.tabs.addTab(
                    self.review_page,
                    title,
                )
            else:
                self.tabs.setTabText(
                    index,
                    title,
                )
        else:
            if index >= 0:
                if (
                    self.tabs.currentWidget()
                    is self.review_page
                ):
                    self.tabs.setCurrentWidget(
                        self.body_page
                    )

                self.tabs.removeTab(
                    index
                )

    def guard(
        self,
        label,
        fn,
    ):
        if (
            self.operation is not None
            or self.fit_active
        ):
            self.set_status(
                "Finish the current action before starting another.",
                u"warning",
            )
            return

        pin_context = (
            self.identity is not None
            and label not in (
                "Refresh Models",
                "Select Model",
                "Clear Model",
            )
        )

        try:
            began = self.operation_begin(
                label,
                pin_context=pin_context,
            )
        except Exception as exc:
            try:
                log_line(
                    "PROD_OPERATION_BEGIN_FAIL label=%r error=%r"
                    % (
                        label,
                        exc,
                    )
                )
            except Exception:
                pass
            try:
                log_line(
                    traceback.format_exc()
                )
            except Exception:
                pass
            self.set_status(
                "The current model context could not be verified. Reselect the model and try again.",
                u"error",
            )
            return

        if not began:
            return

        try:
            try:
                prod_resource_snapshot(
                    u"ACTION_BEGIN:%s"
                    % u(
                        label
                    )
                )
            except Exception:
                pass

            result = fn()

            if self.operation is not None:
                self.operation[
                    "phase"
                ] = u"UI_PUBLISH"

            return result

        except Exception as exc:
            try:
                log_line(
                    "PROD_ACTION_ERROR label=%r error=%r"
                    % (
                        label,
                        exc,
                    )
                )
            except Exception:
                pass
            try:
                log_line(
                    traceback.format_exc()
                )
            except Exception:
                pass

            raw = u(
                exc
            )
            commit_state = self.operation_commit_state()


            if isinstance(
                exc,
                ProdRecoveryUnverifiedError,
            ):
                title = "Recovery could not be verified"
                message = raw

            elif commit_state[
                "native_committed"
            ]:
                title = "Action committed; verification did not finish"
                message = (
                    "The SFM change may already be applied. Check the result or use SFM Undo before retrying."
                )

            elif commit_state[
                "durable_persisted"
            ]:
                title, message = self.operation_durable_error_copy(
                    label,
                    commit_state,
                )

            else:
                title, message = self.operation_default_error_copy(
                    label,
                    raw,
                )

            status_message = message

            if (
                label == "Apply Body Preset"
                and raw
                == u"This preset does not match the selected model's current sliders. Choose another preset or model."
            ):
                status_message = (
                    "Preset not applied - current Body controls do not match this preset."
                )
            elif (
                label == "Apply Expression"
                and raw
                == u"This preset does not match the selected model's current sliders. Choose another preset or model."
            ):
                status_message = (
                    "Preset not applied - current Expression controls do not match this preset."
                )

            self.set_status(
                status_message,
                u"error",
            )

            try:
                tool_warning_message(
                    self,
                    title,
                    message,
                )
            except Exception:
                pass

            # CPM Step 2b (handoff section 13): a rejected action under a stale
            # generation discards the scope and schedules a current-generation
            # rebuild. The rejected action is never replayed.
            self.prod_cpm_request_stale_rebuild_if_needed()

        finally:
            try:
                prod_resource_snapshot(
                    u"ACTION_END:%s"
                    % u(
                        label
                    )
                )
            except Exception:
                pass

            self.operation_end(
                label
            )

    def refresh_animset_display_metadata(
        self,
        row,
    ):
        if (
            self.identity is None
            or row is None
        ):
            return False

        if (
            row.get(
                "model"
            )
            != self.identity.get(
                "model"
            )
            or row.get(
                "checksum"
            )
            != self.identity.get(
                "checksum"
            )
        ):
            raise RuntimeError(
                "Resolved model identity changed unexpectedly."
            )

        old_name = u(
            self.identity.get(
                "animset_name"
            )
            or u""
        )
        new_name = u(
            row.get(
                "animset_name"
            )
            or u""
        )

        if old_name == new_name:
            return False

        self.identity[
            "animset_name"
        ] = new_name

        # Semantic membership is model-derived. Only the copied display
        # metadata needs to follow the user-editable Animation Set name.
        if (
            isinstance(
                self.scope,
                dict,
            )
            and isinstance(
                self.scope.get(
                    "identity"
                ),
                dict,
            )
            and self.scope[
                "identity"
            ].get(
                "model"
            )
            == row.get(
                "model"
            )
            and self.scope[
                "identity"
            ].get(
                "checksum"
            )
            == row.get(
                "checksum"
            )
        ):
            self.scope[
                "identity"
            ][
                "animset_name"
            ] = new_name

        index = self.combo.currentIndex()

        if (
            index > 0
            and index <= len(
                self.candidates
            )
        ):
            candidate = self.candidates[
                index - 1
            ]

            if (
                candidate.get(
                    "model"
                )
                == row.get(
                    "model"
                )
                and candidate.get(
                    "checksum"
                )
                == row.get(
                    "checksum"
                )
            ):
                candidate[
                    "animset_name"
                ] = new_name

                self.combo.setItemText(
                    index,
                    u"%s \u2014 %s"
                    % (
                        new_name,
                        tool_model_relative_path(
                            row.get(
                                "model"
                            )
                        ),
                    )
                )

        try:
            log_line(
                "G18AN_ANIMSET_METADATA_REFRESH model=%r checksum=%r old=%r new=%r"
                % (
                    row.get(
                        "model"
                    ),
                    row.get(
                        "checksum"
                    ),
                    old_name,
                    new_name,
                )
            )
        except Exception:
            pass

        return True


    def current(
        self,
    ):
        if self.identity is None:
            raise RuntimeError(
                "Choose a model first."
            )

        if (
            self.operation is not None
            and self.operation.get(
                "context"
            )
            is not None
        ):
            self.operation_revalidate()

        row = prod_resolve(
            self.identity
        )
        self.refresh_animset_display_metadata(
            row
        )

        return dict(
            self.identity
        )

    def set_review_enabled(
        self,
        value,
    ):
        self.mark_expr.setEnabled(
            value
        )
        self.mark_body.setEnabled(
            value
        )
        self.mark_out.setEnabled(
            value
        )
        self.reclassify_flex.setEnabled(
            False
        )

    def populate(
        self,
    ):
        def work():
            self.candidates, empty_reason = prod_model_candidates()

            self.combo.blockSignals(
                True
            )
            self.combo.clear()
            self.combo.addItem(
                "Choose a character model"
            )

            for row in self.candidates:
                display = (
                    u"%s \u2014 %s"
                    % (
                        u(
                            row[
                                "animset_name"
                            ]
                        ),
                        tool_model_relative_path(
                            row[
                                "model"
                            ]
                        ),
                    )
                )

                self.combo.addItem(
                    display
                )
                index = (
                    self.combo.count()
                    - 1
                )
                self.combo.setItemData(
                    index,
                    u(
                        row[
                            "model"
                        ]
                    ),
                    QtCore.Qt.ToolTipRole,
                )

            self.combo.setCurrentIndex(
                0
            )
            self.combo.blockSignals(
                False
            )

            self.identity = None
            self.scope = None
            self.body_items = []
            self.expr_items = []
            self.review_items = []
            self.review_item_widgets = {}
            self.review_pending_count = 0
            self.library_meta = None
            self.provider_health = None
            self.set_master_warning_visible(
                False
            )

            self.body_list.clear()
            self.expr_list.clear()
            self.review.clear()
            self.body_search.clear()
            self.expr_search.clear()
            self.body_sort.setCurrentIndex(0)
            self.expr_sort.setCurrentIndex(0)
            self.body_favorites_only.setChecked(False)
            self.expr_favorites_only.setChecked(False)

            self.save_body.setEnabled(False)
            self.apply_body.setEnabled(False)
            self.update_body.setEnabled(False)
            self.favorite_body.setEnabled(False)
            self.info_body.setEnabled(False)
            self.delete_body.setEnabled(False)

            self.save_expr.setEnabled(False)
            self.apply_expr.setEnabled(False)
            self.update_expr.setEnabled(False)
            self.favorite_expr.setEnabled(False)
            self.info_expr.setEnabled(False)
            self.delete_expr.setEnabled(False)

            self.fit_active = False
            self.fit_generation += 1
            self.fit_source_baseline = None
            self.fit_selected_identities = []
            self.fit_changed = []
            self.fit_unchanged = []
            self.fit_committed_order = []
            self.fit_partial = []
            self.fit_skipped = []
            self.fit_failed = []
            self.fit_unattempted = []

            self.fit_tree.clear()
            self.fit_tree.setEnabled(False)
            self.fit_button.setEnabled(False)

            self.details.setEnabled(
                False
            )
            self.set_review_enabled(
                False
            )
            self.sync_review_tab()

            guidance = PROD_EMPTY_STATE_GUIDANCE.get(
                empty_reason,
                u"Choose a character model.",
            )
            self.coverage.setText(
                guidance
            )
            self.body_summary.setText(
                guidance
            )
            self.expr_summary.setText(
                guidance
            )
            if empty_reason is None:
                self.set_status(
                    "%d model(s) found. Choose a character model."
                    % len(
                        self.candidates
                    )
                )
            else:
                self.set_status(
                    guidance
                )

            try:
                log_line(
                    "PROD_MODELS count=%d initial_index=%d empty_reason=%r"
                    % (
                        len(
                            self.candidates
                        ),
                        self.combo.currentIndex(),
                        empty_reason,
                    )
                )
            except Exception:
                pass

        return self.guard(
            "Refresh Models",
            work,
        )

    def clear_model_selection(
        self,
    ):
        try:
            log_line(
                "PROD_MODEL_CLEAR_BEGIN previous_identity=%r"
                % self.identity
            )
        except Exception:
            pass

        self.fit_active = False
        self.fit_generation += 1
        self.fit_source_baseline = None
        self.fit_selected_identities = []
        self.fit_changed = []
        self.fit_unchanged = []
        self.fit_committed_order = []
        self.fit_partial = []
        self.fit_skipped = []
        self.fit_failed = []
        self.fit_unattempted = []

        signal_widgets = [
            self.tabs,
            self.body_list,
            self.expr_list,
            self.review,
            self.fit_tree,
            self.body_search,
            self.expr_search,
            self.body_sort,
            self.expr_sort,
            self.body_favorites_only,
            self.expr_favorites_only,
        ]

        for widget in signal_widgets:
            widget.blockSignals(
                True
            )

        try:
            self.identity = None
            self.scope = None
            self.body_items = []
            self.expr_items = []
            self.review_items = []
            self.review_item_widgets = {}
            self.review_pending_count = 0
            self.library_meta = None
            self.provider_health = None
            self.set_master_warning_visible(
                False
            )

            self.body_list.clear()
            self.expr_list.clear()
            self.review.clear()
            self.fit_tree.clear()

            self.body_search.clear()
            self.expr_search.clear()
            self.body_sort.setCurrentIndex(
                0
            )
            self.expr_sort.setCurrentIndex(
                0
            )
            self.body_favorites_only.setChecked(
                False
            )
            self.expr_favorites_only.setChecked(
                False
            )

            self.save_body.setEnabled(False)
            self.apply_body.setEnabled(False)
            self.update_body.setEnabled(False)
            self.favorite_body.setEnabled(False)
            self.info_body.setEnabled(False)
            self.delete_body.setEnabled(False)

            self.save_expr.setEnabled(False)
            self.apply_expr.setEnabled(False)
            self.update_expr.setEnabled(False)
            self.favorite_expr.setEnabled(False)
            self.info_expr.setEnabled(False)
            self.delete_expr.setEnabled(False)

            self.favorite_body.setText(
                "Add Favorite"
            )
            self.favorite_expr.setText(
                "Add Favorite"
            )

            self.fit_tree.setEnabled(
                False
            )
            self.fit_button.setEnabled(
                False
            )
            self.details.setEnabled(
                False
            )
            self.set_review_enabled(
                False
            )

            review_index = self.tabs.indexOf(
                self.review_page
            )
            if review_index >= 0:
                if (
                    self.tabs.currentWidget()
                    is self.review_page
                ):
                    self.tabs.setCurrentWidget(
                        self.body_page
                    )
                self.tabs.removeTab(
                    review_index
                )

            self.coverage.setText(
                "Choose a character model."
            )
            self.body_summary.setText(
                "Choose a character model."
            )
            self.expr_summary.setText(
                "Choose a character model."
            )

            self.set_status(
                "Choose a character model to begin."
            )

        finally:
            for widget in signal_widgets:
                widget.blockSignals(
                    False
                )



    def select_model(
        self,
        index,
    ):
        if (
            index <= 0
            or index > len(
                self.candidates
            )
        ):
            return self.guard(
                "Clear Model",
                self.clear_model_selection,
            )

        row = self.candidates[
            index - 1
        ]
        candidate = {
            "model": row[
                "model"
            ],
            "checksum": row[
                "checksum"
            ],
            "animset_name": row[
                "animset_name"
            ],
        }

        def work():
            # Resolve and build all non-UI state before publishing the new
            # selected identity. A failed transition leaves the prior model
            # selection intact rather than exposing a half-built context.
            resolved_row = prod_resolve(
                candidate
            )
            resolved_candidate = prod_identity_from_row(
                resolved_row
            )
            self.render(
                resolved_candidate
            )

            if (
                u(
                    resolved_candidate.get(
                        "animset_name"
                    )
                    or u""
                )
                != u(
                    candidate.get(
                        "animset_name"
                    )
                    or u""
                )
            ):
                old_name = candidate.get(
                    "animset_name"
                )
                self.candidates[
                    index - 1
                ][
                    "animset_name"
                ] = resolved_candidate[
                    "animset_name"
                ]
                self.combo.setItemText(
                    index,
                    u"%s \u2014 %s"
                    % (
                        u(
                            resolved_candidate[
                                "animset_name"
                            ]
                        ),
                        tool_model_relative_path(
                            resolved_candidate[
                                "model"
                            ]
                        ),
                    )
                )
                try:
                    log_line(
                        "G18AN_STALE_COMBO_NAME_REFRESH index=%d old=%r new=%r"
                        % (
                            index,
                            old_name,
                            resolved_candidate.get(
                                "animset_name"
                            ),
                        )
                    )
                except Exception:
                    pass


        return self.guard(
            "Select Model",
            work,
        )

    def render(
        self,
        identity=None,
    ):
        ident = (
            dict(
                identity
            )
            if identity is not None
            else self.current()
        )

        try:
            log_line(
                "PROD_MODEL_SWITCH_STAGE stage='scope-begin' target=%r previous=%r"
                % (
                    ident,
                    self.identity,
                )
            )
        except Exception:
            pass
        prod_resource_snapshot(
            "MODEL_RENDER_BEFORE_SCOPE"
        )

        provider, provider_health = prod_probe_semantic_provider(
            ident
        )
        scope = None

        if provider_health.get(
            "status"
        ) == u"healthy":
            scope = prod_scope(
                ident,
                provider,
            )
        provider = None

        prod_resource_snapshot(
            "MODEL_RENDER_AFTER_SCOPE"
        )
        try:
            log_line(
                "PROD_MODEL_SWITCH_STAGE stage='scope-ready' target=%r provider_health=%r scope_ready=%r"
                % (
                    ident,
                    provider_health.get("status"),
                    bool(scope is not None),
                )
            )
        except Exception:
            pass

        body_items = prod_discover(
            ident,
            P03_KIND_BODY,
        )

        expr_items = prod_discover(
            ident,
            P03_KIND_EXPRESSION,
        )

        library_meta = prod_load_library_meta(
            ident
        )

        prod_assert_unique_library_ids(
            body_items,
            expr_items,
        )

        old_identity = self.identity
        old_scope = self.scope
        old_body_items = self.body_items
        old_expr_items = self.expr_items
        old_library_meta = self.library_meta
        old_provider_health = self.provider_health

        try:
            self.identity = dict(
                ident
            )
            self.scope = scope
            self.provider_health = dict(
                provider_health
            )
            self.body_items = body_items
            self.expr_items = expr_items
            self.library_meta = library_meta

            self.refresh_preset_view(
                P03_KIND_BODY
            )
            self.refresh_preset_view(
                P03_KIND_EXPRESSION
            )


            if scope is not None:
                self.apply_scope_to_ui(
                    scope
                )

                self.refresh_fit_candidates()

            else:
                self.apply_provider_unavailable_to_ui(
                    provider_health
                )
                try:
                    log_line(
                        "PROD_MODEL_SWITCH_STAGE stage='scope-ui-unavailable' target=%r provider_health=%r reason=%r"
                        % (
                            ident,
                            provider_health.get("status"),
                            provider_health.get("reason"),
                        )
                    )
                except Exception:
                    pass

        except Exception:
            self.identity = old_identity
            self.scope = old_scope
            self.provider_health = old_provider_health
            self.body_items = old_body_items
            self.expr_items = old_expr_items
            self.library_meta = old_library_meta
            raise

        if scope is None:
            self.set_status(
                PROD_MASTER_PROVIDER_WARNING_COPY,
                u"warning",
            )
            try:
                log_line(
                    "PROD_SELECTION_PROVIDER_GATED model=%r checksum=%r animset=%r library_key=%r "
                    "provider_health=%r reason=%r review_rows=0 semantic_actions=False"
                    % (
                        ident["model"],
                        ident["checksum"],
                        ident["animset_name"],
                        prod_key(ident["model"]),
                        provider_health.get("status"),
                        provider_health.get("reason"),
                    )
                )
            except Exception:
                pass

        else:
            review_count = len(
                scope["unresolved"]
            )

            if (
                review_count
                >= PROD_MASTER_REVIEW_WARNING_THRESHOLD
            ):
                try:
                    log_line(
                        "PROD_PROVIDER_REVIEW_WARNING model=%r unresolved=%d threshold=%d location='review-pane'"
                        % (
                            ident["model"],
                            review_count,
                            PROD_MASTER_REVIEW_WARNING_THRESHOLD,
                        )
                    )
                except Exception:
                    pass

            self.set_status(
                "Select a preset, then choose an action above."
            )

            counts = scope["semantic"]["counts"]

            try:
                log_line(
                    "PROD_SELECTION model=%r checksum=%r animset=%r library_key=%r "
                    "expression=%d body=%d other=%d unresolved=%d conflict=%d overrides=%d "
                    "bone_scale_production=True "
                    "bone_scale_policy=complete-native-bone-map-physical-uniform-v1 "
                    "semantic_scope_builds_this_render=1 pure_scope=True provider_health='healthy'"
                    % (
                        ident["model"],
                        ident["checksum"],
                        ident["animset_name"],
                        prod_key(ident["model"]),
                        len(scope["expression"]),
                        len(scope["body"]),
                        counts.get("resolved_other", 0),
                        len(scope["unresolved"]),
                        len(scope["conflicts"]),
                        len(scope["overrides"]),
                    )
                )
            except Exception:
                pass






    def review_add_group(
        self,
        title,
        rows,
        expanded,
    ):
        group = QtGui.QTreeWidgetItem(
            [
                u"%s (%d)"
                % (
                    u(title),
                    len(
                        rows
                    ),
                )
            ]
        )
        group.setFlags(
            group.flags()
            & ~QtCore.Qt.ItemIsSelectable
        )
        self.review.addTopLevelItem(
            group
        )
        group.setExpanded(
            bool(
                expanded
            )
        )

        for literal, kind, decision, display in rows:
            row_index = len(
                self.review_items
            )
            self.review_items.append(
                (
                    literal,
                    kind,
                    decision,
                )
            )
            child = QtGui.QTreeWidgetItem(
                [
                    u(display)
                ]
            )
            child.setData(
                0,
                QtCore.Qt.UserRole,
                int(
                    row_index
                ),
            )
            group.addChild(
                child
            )
            self.review_item_widgets[
                (
                    literal,
                    kind,
                )
            ] = child

        return group


    def review_current_record(
        self,
    ):
        item = self.review.currentItem()

        if item is None:
            return None

        value = item.data(
            0,
            QtCore.Qt.UserRole,
        )

        try:
            row = int(
                value
            )
        except Exception:
            return None

        if (
            row < 0
            or row >= len(
                self.review_items
            )
        ):
            return None

        return self.review_items[
            row
        ]


    def review_select_literal(
        self,
        literal,
        kind,
    ):
        item = self.review_item_widgets.get(
            (
                literal,
                kind,
            )
        )

        if item is None:
            return False

        parent = item.parent()

        if parent is not None:
            parent.setExpanded(
                True
            )

        self.review.setCurrentItem(
            item
        )
        self.review.scrollToItem(
            item
        )

        return True


    def apply_scope_to_ui(
        self,
        scope,
        identity=None,
    ):
        display_identity = (
            self.identity
            if identity is None
            else identity
        )

        if (
            display_identity is None
            or not prod_scope_matches_identity(
                scope,
                display_identity,
            )
        ):
            raise RuntimeError(
                "Cannot display a stale semantic scope."
            )

        counts = scope[
            "semantic"
        ][
            "counts"
        ]
        review_count = len(
            scope[
                "unresolved"
            ]
        )

        self.coverage.setText(
            u"Expression: %d   Body: %d   Other: %d   Review: %d"
            % (
                len(
                    scope[
                        "expression"
                    ]
                ),
                len(
                    scope[
                        "body"
                    ]
                ),
                counts.get(
                    "resolved_other",
                    0,
                ),
                review_count,
            )
        )
        self.body_summary.setText(
            "Save body flexes and bone scaling for this model."
        )
        self.expr_summary.setText(
            "Save facial flexes for this model."
        )
        self.save_body.setEnabled(
            bool(
                scope[
                    "body"
                ]
            )
        )
        self.save_expr.setEnabled(
            bool(
                scope[
                    "expression"
                ]
            )
        )
        self.details.setEnabled(
            True
        )

        self.review.blockSignals(
            True
        )
        self.review.clear()
        self.review_items = []
        self.review_item_widgets = {}
        self.review_pending_count = len(
            scope[
                "unresolved"
            ]
        )

        unresolved_rows = [
            (
                literal,
                u"miss",
                None,
                literal,
            )
            for literal in scope[
                "unresolved"
            ]
        ]

        decision_names = {
            u"body": u"Body",
            u"expression": u"Expression",
            u"exclude": u"Excluded",
        }
        reviewed_rows = []

        for literal in sorted(
            scope[
                "overrides"
            ].keys()
        ):
            decision = u(
                scope[
                    "overrides"
                ][
                    literal
                ]
            )
            reviewed_rows.append(
                (
                    literal,
                    u"reviewed",
                    decision,
                    u"%s \u2014 %s"
                    % (
                        literal,
                        decision_names.get(
                            decision,
                            decision,
                        ),
                    ),
                )
            )

        conflict_rows = [
            (
                literal,
                u"conflict",
                None,
                literal,
            )
            for literal in scope[
                "conflicts"
            ]
        ]

        if unresolved_rows:
            self.review_add_group(
                "Needs review",
                unresolved_rows,
                len(
                    unresolved_rows
                )
                <= 20,
            )

        if reviewed_rows:
            self.review_add_group(
                "Reviewed choices",
                reviewed_rows,
                False,
            )

        if conflict_rows:
            self.review_add_group(
                "Master conflicts",
                conflict_rows,
                False,
            )

        self.review.blockSignals(
            False
        )
        self.sync_review_tab()
        self.set_review_enabled(
            False
        )
        self.review_master_warning.setVisible(
            review_count
            >= PROD_MASTER_REVIEW_WARNING_THRESHOLD
        )
        self.update_action_buttons()


    def preset_item_token(
        self,
        item,
    ):
        if not isinstance(
            item,
            dict,
        ):
            return None

        record = item.get(
            "record"
        )

        if not isinstance(
            record,
            dict,
        ):
            return None

        preset_id = u(
            record.get(
                "preset_id"
            )
            or u""
        )

        if not preset_id:
            return None

        return u"%s\x1f%s" % (
            u(
                item.get(
                    "source"
                )
                or u""
            ),
            preset_id,
        )


    def resolve_preset_item_token(
        self,
        kind,
        token,
    ):
        token = u(
            token
            or u""
        )

        if not token:
            return None

        source = (
            self.body_items
            if kind == P03_KIND_BODY
            else self.expr_items
        )

        matches = [
            item
            for item in source
            if self.preset_item_token(
                item
            ) == token
        ]

        if len(
            matches
        ) == 1:
            return matches[0]

        if not matches:
            return None

        raise RuntimeError(
            "Preset list token resolved ambiguously."
        )


    def selected_or_none(
        self,
        kind,
    ):
        widget = (
            self.body_list
            if kind == P03_KIND_BODY
            else self.expr_list
        )
        current = widget.currentItem()

        if current is None:
            return None

        token = current.data(
            QtCore.Qt.UserRole
        )

        if not token:
            return None

        return self.resolve_preset_item_token(
            kind,
            token,
        )


    def preset_filter_state(
        self,
        kind,
    ):
        if kind == P03_KIND_BODY:
            return {
                "query": u(
                    self.body_search.text()
                ),
                "sort": u(
                    self.body_sort.currentText()
                ),
                "favorites_only": bool(
                    self.body_favorites_only.isChecked()
                ),
            }

        return {
            "query": u(
                self.expr_search.text()
            ),
            "sort": u(
                self.expr_sort.currentText()
            ),
            "favorites_only": bool(
                self.expr_favorites_only.isChecked()
            ),
        }


    def favorite_keys(
        self,
    ):
        if not isinstance(
            self.library_meta,
            dict,
        ):
            return set()

        return set(
            u(value)
            for value in (
                self.library_meta.get(
                    "favorites"
                )
                or []
            )
        )


    def is_favorite_cached(
        self,
        record,
    ):
        return (
            prod_favorite_key(
                record
            )
            in self.favorite_keys()
        )


    def update_favorite_cache(
        self,
        record,
        enabled,
    ):
        if not isinstance(
            self.library_meta,
            dict,
        ):
            self.library_meta = {
                "schema_version": PROD_LIBRARY_META_SCHEMA,
                "record_kind": u"library-metadata",
                "favorites": [],
            }

        keys = self.favorite_keys()
        key = prod_favorite_key(
            record
        )

        if enabled:
            keys.add(
                key
            )
        else:
            keys.discard(
                key
            )

        self.library_meta[
            "favorites"
        ] = sorted(
            keys
        )


    def refresh_preset_view(
        self,
        kind,
        select_id=None,
    ):
        if self.identity is None:
            return

        widget = (
            self.body_list
            if kind == P03_KIND_BODY
            else self.expr_list
        )
        source = (
            self.body_items
            if kind == P03_KIND_BODY
            else self.expr_items
        )


        if select_id is None:
            current = self.selected_or_none(
                kind
            )
            if current is not None:
                select_id = u(
                    current[
                        "record"
                    ].get(
                        "preset_id"
                    )
                    or u""
                )


        state = self.preset_filter_state(
            kind
        )
        favorite_keys = self.favorite_keys()
        rows = []

        for item in source:
            if not prod_item_matches_search(
                item,
                state[
                    "query"
                ],
            ):
                continue

            favorite = (
                prod_favorite_key(
                    item[
                        "record"
                    ]
                )
                in favorite_keys
            )

            if (
                state[
                    "favorites_only"
                ]
                and not favorite
            ):
                continue

            copy_item = dict(
                item
            )
            copy_item[
                "_favorite"
            ] = favorite
            rows.append(
                copy_item
            )

        rows = prod_sort_items(
            rows,
            state[
                "sort"
            ],
        )


        widget.blockSignals(
            True
        )
        widget.clear()
        selected_row = -1

        for index, item in enumerate(
            rows
        ):
            record = item[
                "record"
            ]
            preset_id = u(
                record.get(
                    "preset_id"
                )
                or u""
            )
            token = self.preset_item_token(
                item
            )

            if not token:
                raise RuntimeError(
                    "Preset list item has no stable token."
                )

            title = prod_item_display_name(
                item
            )

            if (
                item.get(
                    "source"
                )
                == u"legacy-v2"
            ):
                title += u" [Read-only]"


            list_item = QtGui.QListWidgetItem(
                title
            )
            if item.get(
                "_favorite"
            ):
                list_item.setIcon(
                    tool_favorite_star_icon()
                )
            # G17I: Qt stores only a small Unicode token.  The full preset
            # record, including potentially large bone maps, remains owned by
            # the Python library cache and is resolved on demand.
            list_item.setData(
                QtCore.Qt.UserRole,
                token,
            )
            widget.addItem(
                list_item
            )


            if (
                select_id
                and preset_id
                == u(
                    select_id
                )
            ):
                selected_row = index

        if selected_row >= 0:
            widget.setCurrentRow(
                selected_row
            )

        widget.blockSignals(
            False
        )
        self.update_action_buttons()


    def reload_library_cache(
        self,
        select_body_id=None,
        select_expr_id=None,
    ):
        """Reload preset files/metadata only. Never traverse scene/DME state."""
        if self.identity is None:
            raise RuntimeError(
                "Choose a model first."
            )

        ident = dict(
            self.identity
        )

        self.body_items = prod_discover(
            ident,
            P03_KIND_BODY,
        )
        self.expr_items = prod_discover(
            ident,
            P03_KIND_EXPRESSION,
        )
        self.library_meta = prod_load_library_meta(
            ident
        )
        prod_assert_unique_library_ids(
            self.body_items,
            self.expr_items,
        )

        self.refresh_preset_view(
            P03_KIND_BODY,
            select_body_id,
        )
        self.refresh_preset_view(
            P03_KIND_EXPRESSION,
            select_expr_id,
        )

        try:
            log_line(
                "PROD_LIBRARY model=%r body_v3=%d expression_v3=%d favorites=%d "
                "semantic_scope_rebuild=False scene_traversal=False"
                % (
                    ident[
                        "model"
                    ],
                    len(
                        self.body_items
                    ),
                    len(
                        self.expr_items
                    ),
                    len(
                        self.library_meta.get(
                            "favorites"
                        )
                        or []
                    ),
                )
            )
        except Exception:
            pass


    def preset_selection_changed(self, kind):
        self.update_action_buttons()
        if self.identity is None:
            return
        item = self.selected_or_none(kind)
        if not self.semantic_provider_ready():
            self.set_status(
                PROD_MASTER_PROVIDER_WARNING_COPY,
                u"warning",
            )
            return
        if item is None:
            self.set_status("Select a preset, then choose an action above.")
            return
        self.set_status(u'Ready to apply "%s".' % prod_item_display_name(item))



    def review_changed(
        self,
        current=None,
        previous=None,
    ):
        self.set_review_enabled(
            False
        )

        record = self.review_current_record()

        if record is None:
            return

        literal, kind, decision = record

        if kind == u"miss":
            self.set_review_enabled(
                True
            )
            self.set_status(
                "Choose a classification for this flex."
            )
            return

        if kind == u"reviewed":
            self.reclassify_flex.setEnabled(
                True
            )
            decision_names = {
                u"body": u"Body",
                u"expression": u"Expression",
            }
            if decision == u"exclude":
                self.set_status(
                    "Excluded from presets. Click Clear Classification, then choose a new classification under Needs review."
                )
            else:
                self.set_status(
                    u"Classified as %s. Click Clear Classification, then choose a new classification under Needs review."
                    % decision_names.get(
                        decision,
                        decision,
                    )
                )
            return

        if kind == u"conflict":
            self.set_status(
                "This flex has a Master conflict and cannot be classified here.",
                u"warning",
            )


    def review_reclassify(
        self,
    ):
        def work():
            record = self.review_current_record()

            if (
                record is None
                or record[
                    1
                ]
                != u"reviewed"
            ):
                raise RuntimeError(
                    "Select a reviewed flex first."
                )

            ident = self.current()
            literal = record[
                0
            ]
            old_scope = self.scope

            if not prod_scope_matches_identity(
                old_scope,
                ident,
            ):
                raise RuntimeError(
                    "The selected model's semantic scope is stale. Reselect the model."
                )

            # CPM Step 3: authorize while the scope is still selected, so a
            # stale generation keeps the existing section 13 rebuild path.
            authority_context = prod_cpm_authorize_operation(
                ident,
                old_scope,
                None,
                u"Reclassify Flex",
            )

            self.scope = None
            self.disable_semantic_scene_actions()

            prod_clear_override(
                ident,
                literal,
                old_scope,
                phase_callback=self.operation_mark_phase,
                authority_context=authority_context,
            )
            authority_context = None

            self.operation_revalidate()

            prod_resource_snapshot(
                "RECLASSIFY_BEFORE_SCOPE_REBUILD"
            )

            new_scope = prod_scope(
                ident
            )

            prod_resource_snapshot(
                "RECLASSIFY_AFTER_SCOPE_REBUILD"
            )

            if literal in new_scope[
                "overrides"
            ]:
                raise RuntimeError(
                    "The flex did not return to Needs review after clearing its classification."
                )

            # CPM Step 3: the durable clear succeeded; the rebuilt scope is a
            # separate current-authority classification, which may no longer
            # be a miss if newer authority resolves or conflicts on it.
            outcome = prod_cpm_reclassify_outcome(
                literal,
                new_scope,
            )

            self.scope = new_scope
            self.apply_scope_to_ui(
                new_scope
            )

            try:
                log_line(
                    "PROD_RECLASSIFY_REFRESH=PASS literal=%r semantic_scope_rebuilds=1 "
                    "durable_edit=True returned_to_review=%r current_class=%r old_scope_reused=False"
                    % (
                        literal,
                        outcome["returned_to_review"],
                        outcome["current_semantic_class"],
                    )
                )
            except Exception:
                pass
            if outcome["returned_to_review"]:
                self.review_select_literal(
                    literal,
                    u"miss",
                )
                self.set_status(
                    "Choose a new classification for this flex.",
                    u"success",
                )
            else:
                self.set_status(
                    "Saved classification cleared. Current authority now classifies this flex.",
                    u"success",
                )

        return self.guard(
            "Reclassify Flex",
            work,
        )


    def review_decision(
        self,
        decision,
    ):
        def work():
            record = self.review_current_record()

            if (
                record is None
                or record[
                    1
                ]
                != u"miss"
            ):
                raise RuntimeError(
                    "Select an unrecognized flex first."
                )

            ident = self.current()
            literal = record[
                0
            ]
            old_scope = self.scope

            if not prod_scope_matches_identity(
                old_scope,
                ident,
            ):
                raise RuntimeError(
                    "The selected model's semantic scope is stale. Reselect the model."
                )

            # Invalidate semantic state before persistence. The prior scope is
            # never left active after a saved classification choice.
            # CPM Step 3: authorize while the scope is still selected, so a
            # stale generation keeps the existing section 13 rebuild path.
            authority_context = prod_cpm_authorize_operation(
                ident,
                old_scope,
                None,
                u"Review Flex",
            )

            self.scope = None
            self.disable_semantic_scene_actions()

            prod_set_override(
                ident,
                literal,
                decision,
                old_scope,
                phase_callback=self.operation_mark_phase,
                authority_context=authority_context,
            )
            authority_context = None

            self.operation_revalidate()

            prod_resource_snapshot(
                "REVIEW_BEFORE_SCOPE_REBUILD"
            )

            new_scope = prod_scope(
                ident
            )

            prod_resource_snapshot(
                "REVIEW_AFTER_SCOPE_REBUILD"
            )

            self.scope = new_scope
            self.apply_scope_to_ui(
                new_scope
            )

            try:
                log_line(
                    "PROD_REVIEW_REFRESH=PASS literal=%r decision=%r semantic_scope_rebuilds=1 library_rediscovery=False old_scope_reused=False"
                    % (
                        literal,
                        decision,
                    )
                )
            except Exception:
                pass
            self.set_status(
                "Flex choice saved.",
                u"success",
            )

        return self.guard(
            "Review Flex",
            work,
        )

    def prompt(
        self,
        title,
        default,
    ):
        dialog = QtGui.QInputDialog(
            self
        )
        tool_keep_modal_dialog_in_front(
            dialog
        )

        try:
            dialog.setWindowTitle(
                u(title)
            )
            dialog.setLabelText(
                "Preset name:"
            )
            dialog.setInputMode(
                QtGui.QInputDialog.TextInput
            )
            dialog.setTextEchoMode(
                QtGui.QLineEdit.Normal
            )
            dialog.setTextValue(
                u(default)
            )

            tool_apply_dialog_font(
                dialog
            )

            accepted = (
                dialog.exec_()
                == QtGui.QDialog.Accepted
            )

            if not accepted:
                return None

            value = u(
                dialog.textValue()
            ).strip()

        finally:
            dialog.deleteLater()

        if not value:
            raise RuntimeError(
                "Preset name cannot be blank."
            )

        return value


    def save_kind(
        self,
        kind,
    ):
        def work():
            ident = self.current()

            if not prod_scope_matches_identity(
                self.scope,
                ident,
            ):
                raise RuntimeError(
                    "The selected model's semantic scope is stale. Reselect the model."
                )

            title = (
                "Save New Body Preset"
                if kind == P03_KIND_BODY
                else "Save New Expression"
            )
            default = (
                u"Body"
                if kind == P03_KIND_BODY
                else u"Expression"
            )

            name_value = self.prompt(
                title,
                default,
            )

            if name_value is None:
                return

            # Modal return is an operation boundary.
            self.operation_revalidate()

            path = prod_save(
                ident,
                kind,
                name_value,
                scope=self.scope,
                phase_callback=self.operation_mark_phase,
                operation_context=(
                    self.operation.get(
                        "context"
                    )
                    if self.operation is not None
                    else None
                ),
            )
            prod_resource_snapshot(
                "SAVE_AFTER_PASS"
            )

            record = p02_read_json(
                path
            )
            prod_validate_preset(
                ident,
                record,
                kind,
            )
            preset_id = u(
                record.get(
                    "preset_id"
                )
            )
            new_item = {
                "path": path,
                "record": record,
                "source": u"v3",
                "revision": prod_json_digest(
                    record
                ),
            }

            source_items = (
                self.body_items
                if kind == P03_KIND_BODY
                else self.expr_items
            )
            source_items.append(
                new_item
            )

            self.refresh_preset_view(
                kind,
                preset_id,
            )
            prod_resource_snapshot(
                u"Q2_SAVE_AFTER_UI_PUBLISH"
            )


            if kind == P03_KIND_BODY:
                self.set_status(
                    "Body Preset saved.",
                    u"success",
                )
            else:
                self.set_status(
                    "Expression saved.",
                    u"success",
                )

        return self.guard(
            (
                "Save Current Body"
                if kind == P03_KIND_BODY
                else "Save Current Expression"
            ),
            work,
        )


    def selected(self, kind):
        item = self.selected_or_none(kind)
        if item is None:
            raise RuntimeError("Select a preset first.")
        return item


    def toggle_favorite(
        self,
        kind,
    ):
        def work():
            ident = self.current()
            item = self.selected(
                kind
            )
            record = item[
                "record"
            ]

            current = self.is_favorite_cached(
                record
            )
            result = prod_set_favorite(
                ident,
                record,
                not current,
                phase_callback=self.operation_mark_phase,
            )
            enabled = bool(
                result[
                    "enabled"
                ]
            )
            self.library_meta = dict(
                result[
                    "meta"
                ]
            )

            preset_id = u(
                record.get(
                    "preset_id"
                )
            )
            self.refresh_preset_view(
                kind,
                preset_id,
            )

            self.set_status(
                (
                    "Added to Favorites."
                    if enabled
                    else "Removed from Favorites."
                ),
                u"success",
            )

        return self.guard(
            "Favorite Preset",
            work,
        )


    def update_kind(
        self,
        kind,
    ):
        def work():
            ident = self.current()

            if not prod_scope_matches_identity(
                self.scope,
                ident,
            ):
                raise RuntimeError(
                    "The selected model's semantic scope is stale. Reselect the model."
                )

            item = self.selected(
                kind
            )

            if item.get(
                "source"
            ) != u"v3":
                raise RuntimeError(
                    "Read-only legacy presets cannot be updated."
                )

            record = item[
                "record"
            ]
            display_name = prod_item_display_name(
                item
            )

            box = QtGui.QMessageBox(
                self
            )
            tool_keep_modal_dialog_in_front(
                box
            )

            try:
                box.setWindowTitle(
                    "Update preset?"
                )

                state_text = (
                    "body flexes and bone scaling"
                    if kind == P03_KIND_BODY
                    else "facial flexes"
                )

                box.setText(
                    u'Copy the current %s into "%s"?'
                    % (
                        state_text,
                        display_name,
                    )
                )
                box.setInformativeText(
                    "The preset's current values will be overwritten."
                )

                update_button = box.addButton(
                    "Update Preset",
                    QtGui.QMessageBox.AcceptRole,
                )
                cancel_button = box.addButton(
                    "Cancel",
                    QtGui.QMessageBox.RejectRole,
                )
                box.setDefaultButton(
                    cancel_button
                )

                tool_apply_dialog_font(
                    box
                )
                box.exec_()
                confirmed = (
                    box.clickedButton()
                    is update_button
                )

            finally:
                box.deleteLater()

            if not confirmed:
                return

            self.operation_revalidate()

            prod_update_preset(
                ident,
                item,
                scope=self.scope,
                phase_callback=self.operation_mark_phase,
                operation_context=(
                    self.operation.get(
                        "context"
                    )
                    if self.operation is not None
                    else None
                ),
            )
            prod_resource_snapshot(
                "UPDATE_AFTER_PASS"
            )

            preset_id = u(
                record.get(
                    "preset_id"
                )
            )
            preset_path = item.get(
                "path"
            )

            fresh_record = p02_read_json(
                preset_path
            )
            prod_validate_preset(
                ident,
                fresh_record,
                kind,
            )

            source_items = (
                self.body_items
                if kind == P03_KIND_BODY
                else self.expr_items
            )
            replaced = False

            for source_item in source_items:
                if (
                    os.path.normcase(
                        os.path.abspath(
                            source_item.get(
                                "path"
                            )
                        )
                    )
                    == os.path.normcase(
                        os.path.abspath(
                            preset_path
                        )
                    )
                ):
                    source_item[
                        "record"
                    ] = fresh_record
                    source_item[
                        "revision"
                    ] = prod_json_digest(
                        fresh_record
                    )
                    replaced = True
                    break

            if not replaced:
                raise RuntimeError(
                    "Updated preset could not be refreshed in the library view."
                )

            self.refresh_preset_view(
                kind,
                preset_id,
            )
            prod_resource_snapshot(
                u"Q2_UPDATE_AFTER_UI_PUBLISH"
            )

            self.set_status(
                u'"%s" updated.'
                % display_name,
                u"success",
            )

        return self.guard(
            "Update Preset",
            work,
        )


    def update_action_buttons(self):
        body_item = self.selected_or_none(P03_KIND_BODY)
        expr_item = self.selected_or_none(P03_KIND_EXPRESSION)
        body_selected = body_item is not None
        expr_selected = expr_item is not None
        semantic_ready = self.semantic_provider_ready()
        body_current = (
            body_selected
            and body_item.get("source") == u"v3"
        )
        expr_current = (
            expr_selected
            and expr_item.get("source") == u"v3"
        )

        body_save_ready = bool(
            semantic_ready
            and isinstance(
                self.scope,
                dict,
            )
            and self.scope.get(
                "body"
            )
        )
        expr_save_ready = bool(
            semantic_ready
            and isinstance(
                self.scope,
                dict,
            )
            and self.scope.get(
                "expression"
            )
        )

        self.save_body.setEnabled(
            body_save_ready
        )
        self.save_expr.setEnabled(
            expr_save_ready
        )

        self.apply_body.setEnabled(
            body_selected
            and semantic_ready
        )
        self.update_body.setEnabled(
            body_current
            and semantic_ready
        )
        self.favorite_body.setEnabled(body_selected)
        self.info_body.setEnabled(body_selected)
        self.delete_body.setEnabled(body_current)
        self.apply_expr.setEnabled(
            expr_selected
            and semantic_ready
        )
        self.update_expr.setEnabled(
            expr_current
            and semantic_ready
        )
        self.favorite_expr.setEnabled(expr_selected)
        self.info_expr.setEnabled(expr_selected)
        self.delete_expr.setEnabled(expr_current)

        self.favorite_body.setText("Remove Favorite" if body_selected and self.is_favorite_cached(body_item["record"]) else "Add Favorite")
        self.favorite_expr.setText("Remove Favorite" if expr_selected and self.is_favorite_cached(expr_item["record"]) else "Add Favorite")



    def update_delete_buttons(self):
        self.update_action_buttons()


    def delete_kind(
        self,
        kind,
    ):
        def work():
            ident = self.current()
            item = self.selected(
                kind
            )

            if item.get(
                "source"
            ) != u"v3":
                raise RuntimeError(
                    "Legacy presets are read-only. Only current-library presets can be deleted."
                )

            record = item[
                "record"
            ]
            display_name = u(
                record.get(
                    "name"
                )
                or record.get(
                    "preset_id"
                )
            )

            trash_path = os.path.join(
                prod_paths(
                    ident
                )[
                    "root"
                ],
                P03_TRASH_DIRNAME,
            )

            box = QtGui.QDialog(
                self
            )

            try:
                box.setWindowTitle(
                    "Move preset to Trash?"
                )
                box.setMinimumWidth(590)
                box.setMaximumWidth(620)

                layout = QtGui.QVBoxLayout(box)
                layout.setContentsMargins(
                    12,
                    12,
                    12,
                    12,
                )
                layout.setSpacing(8)

                question = QtGui.QLabel(
                    u'<b>Move "%s" to Trash?</b>'
                    % display_name
                )
                question.setWordWrap(True)
                layout.addWidget(question)

                recovery = QtGui.QLabel(
                    "You can recover it from:"
                )
                layout.addWidget(recovery)

                path_label = QtGui.QLabel(
                    u(trash_path)
                )
                path_label.setWordWrap(False)
                path_label.setTextInteractionFlags(
                    QtCore.Qt.TextSelectableByMouse
                )
                layout.addWidget(path_label)

                buttons = QtGui.QDialogButtonBox()
                delete_button = buttons.addButton(
                    "Move to Trash",
                    QtGui.QDialogButtonBox.AcceptRole,
                )
                cancel_button = buttons.addButton(
                    "Cancel",
                    QtGui.QDialogButtonBox.RejectRole,
                )
                delete_button.clicked.connect(
                    box.accept
                )
                cancel_button.clicked.connect(
                    box.reject
                )
                cancel_button.setDefault(True)
                layout.addWidget(buttons)

                tool_apply_visual_theme(box)
                tool_apply_dialog_font(box)
                confirmed = (
                    box.exec_()
                    == QtGui.QDialog.Accepted
                )

            finally:
                box.deleteLater()

            if not confirmed:
                return

            self.operation_revalidate()

            prod_move_current_preset_to_trash(
                ident,
                item,
                phase_callback=self.operation_mark_phase,
            )
            prod_resource_snapshot(
                "DELETE_AFTER_PASS"
            )

            deleted_path = os.path.normcase(
                os.path.abspath(
                    item.get(
                        "path"
                    )
                )
            )

            source_items = (
                self.body_items
                if kind == P03_KIND_BODY
                else self.expr_items
            )

            remaining = [
                source_item
                for source_item in source_items
                if os.path.normcase(
                    os.path.abspath(
                        source_item.get(
                            "path"
                        )
                    )
                )
                != deleted_path
            ]

            if len(
                remaining
            ) != (
                len(
                    source_items
                )
                - 1
            ):
                raise RuntimeError(
                    "Deleted preset could not be removed from the library view."
                )

            if kind == P03_KIND_BODY:
                self.body_items = remaining
            else:
                self.expr_items = remaining

            # Publish the verified metadata record currently on disk. Trash
            # success remains authoritative even if optional Favorite cleanup
            # previously emitted a warning.
            self.library_meta = prod_load_library_meta(
                ident
            )

            self.refresh_preset_view(
                kind
            )

            self.set_status(
                "Preset moved to Trash.",
                u"success",
            )

        return self.guard(
            "Delete Preset",
            work,
        )

    def apply_kind(
        self,
        kind,
    ):
        def work():
            ident = self.current()
            item = self.selected(
                kind
            )

            if item.get(
                "source"
            ) == u"legacy-v2":
                record = item[
                    "record"
                ]
            else:
                record = prod_reread_selected_record(
                    ident,
                    item,
                    kind,
                )

            prod_validate_preset(
                ident,
                record,
                kind,
            )

            self.operation_revalidate()

            result = prod_apply(
                ident,
                record,
                scope=self.scope,
                phase_callback=self.operation_mark_phase,
                operation_context=(
                    self.operation.get(
                        "context"
                    )
                    if self.operation is not None
                    else None
                ),
            )


            if result[
                "phase"
            ] == u"no-op":
                self.set_status(
                    "Already matches this preset."
                )

            elif result[
                "phase"
            ] == u"committed-unverified":
                self.set_status(
                    "Applied, but verification did not finish. Check the result or use SFM Undo before retrying.",
                    u"error",
                )

            elif kind == P03_KIND_BODY:
                self.set_status(
                    "Body Preset applied.",
                    u"success",
                )

            else:
                self.set_status(
                    "Expression applied.",
                    u"success",
                )

        return self.guard(
            (
                "Apply Body Preset"
                if kind == P03_KIND_BODY
                else "Apply Expression"
            ),
            work,
        )

    def fit_model_folder(self, model_path):
        normalized = prod_norm(model_path)
        return normalized.rsplit(u"/", 1)[0] if u"/" in normalized else u""


    def fit_same_model_folder(
        self,
        source_folder,
        candidate_folder,
    ):
        if candidate_folder == source_folder:
            return True
        if not source_folder:
            return False
        return candidate_folder.startswith(
            source_folder.rstrip(u"/")
            + u"/"
        )


    def fit_nearby_model_folder(
        self,
        source_folder,
        candidate_folder,
    ):
        if self.fit_same_model_folder(
            source_folder,
            candidate_folder,
        ):
            return False

        if (
            not source_folder
            or u"/"
            not in source_folder
        ):
            return False

        source_parent = source_folder.rsplit(
            u"/",
            1,
        )[
            0
        ].rstrip(
            u"/"
        )

        if (
            not source_parent
            or source_parent
            == u"models"
        ):
            return False

        return (
            candidate_folder
            == source_parent
            or candidate_folder.startswith(
                source_parent
                + u"/"
            )
        )


    def fit_candidate_rows(self):
        ident = self.current()
        source_row = prod_resolve(ident)
        source_folder = self.fit_model_folder(ident["model"])
        same_folder = []
        nearby = []
        other = []
        for row in p03_model_animsets():
            if same_dme(source_row["animset"], row["animset"]):
                continue
            identity = g11a_target_identity(row)
            candidate_folder = self.fit_model_folder(identity["model"])
            entry = {
                "identity": identity,
                "same_folder": self.fit_same_model_folder(
                    source_folder,
                    candidate_folder,
                ),
                "nearby": False,
            }
            if entry["same_folder"]:
                same_folder.append(
                    entry
                )
            else:
                entry["nearby"] = self.fit_nearby_model_folder(
                    source_folder,
                    candidate_folder,
                )
                (
                    nearby
                    if entry[
                        "nearby"
                    ]
                    else other
                ).append(
                    entry
                )
        key = lambda row: (u(row["identity"]["name"]).lower(), u(row["identity"]["model"]).lower())
        same_folder.sort(key=key)
        nearby.sort(key=key)
        other.sort(key=key)
        return same_folder, nearby, other


    def fit_add_group(self, title, rows, expanded):
        group = QtGui.QTreeWidgetItem([u"%s (%d)" % (title, len(rows))])
        group.setFlags(group.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.fit_tree.addTopLevelItem(group)
        group.setExpanded(bool(expanded))
        for row in rows:
            ident = dict(
                row[
                    "identity"
                ]
            )
            token = len(
                self.fit_identity_tokens
            )
            self.fit_identity_tokens.append(
                ident
            )

            child = QtGui.QTreeWidgetItem([u"%s \u2014 %s" % (u(ident["name"]), tool_model_relative_path(ident["model"]))])
            child.setToolTip(0, u(ident["model"]))
            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
            child.setCheckState(0, QtCore.Qt.Unchecked)
            child.setData(
                0,
                QtCore.Qt.UserRole,
                int(
                    token
                ),
            )
            group.addChild(child)
        return group


    def refresh_fit_candidates(self):
        if self.identity is None:
            self.fit_tree.clear()
            self.fit_button.setEnabled(False)
            return
        same_folder, nearby, other = self.fit_candidate_rows()
        self.fit_tree.blockSignals(True)
        self.fit_tree.clear()
        self.fit_identity_tokens = []
        self.fit_same_root = self.fit_add_group("Same model folder", same_folder, True)
        self.fit_nearby_root = self.fit_add_group("Nearby folders", nearby, False)
        self.fit_other_root = self.fit_add_group("Other models in shot", other, False)
        self.fit_tree.blockSignals(False)
        self.fit_tree.setEnabled(True)
        self.fit_button.setEnabled(False)


    def fit_checked_identities(self):
        result = []
        for root_index in range(self.fit_tree.topLevelItemCount()):
            root = self.fit_tree.topLevelItem(root_index)
            for child_index in range(root.childCount()):
                item = root.child(child_index)
                if item.flags() & QtCore.Qt.ItemIsUserCheckable and item.checkState(0) == QtCore.Qt.Checked:
                    value = item.data(
                        0,
                        QtCore.Qt.UserRole,
                    )

                    try:
                        token = int(
                            value
                        )
                    except Exception:
                        continue

                    if (
                        token < 0
                        or token >= len(
                            self.fit_identity_tokens
                        )
                    ):
                        continue

                    result.append(
                        dict(
                            self.fit_identity_tokens[
                                token
                            ]
                        )
                    )
        return result


    def fit_selection_changed(self, item=None, column=0):
        if not self.fit_active:
            self.fit_button.setEnabled(
                bool(self.fit_checked_identities())
                and self.identity is not None
                and self.semantic_provider_ready()
            )


    def fit_set_enabled(
        self,
        enabled,
    ):
        enabled = bool(
            enabled
        )

        self.fit_tree.setEnabled(
            enabled
        )
        self.combo.setEnabled(
            enabled
        )
        self.refresh.setEnabled(
            enabled
        )

        if not enabled:
            for widget in (
                self.save_body,
                self.apply_body,
                self.update_body,
                self.favorite_body,
                self.delete_body,
                self.save_expr,
                self.apply_expr,
                self.update_expr,
                self.favorite_expr,
                self.delete_expr,
                self.fit_button,
            ):
                widget.setEnabled(
                    False
                )

            self.set_review_enabled(
                False
            )
            return

        self.fit_button.setEnabled(
            bool(
                self.fit_checked_identities()
            )
            and self.identity is not None
            and self.semantic_provider_ready()
        )
        self.update_action_buttons()

        if self.review.currentItem() is not None:
            self.review_changed(
                self.review.currentItem(),
                None,
            )


    def fit_clear_checks(self):
        self.fit_tree.blockSignals(True)
        for root_index in range(self.fit_tree.topLevelItemCount()):
            root = self.fit_tree.topLevelItem(root_index)
            for child_index in range(root.childCount()):
                item = root.child(child_index)
                if item.flags() & QtCore.Qt.ItemIsUserCheckable:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
        self.fit_tree.blockSignals(False)


    def fit_selected(
        self,
    ):
        if (
            self.fit_active
            or self.operation is not None
        ):
            self.set_status(
                "Finish the current action before starting Clothing Fit.",
                u"warning",
            )
            return

        selected = self.fit_checked_identities()

        if not selected:
            self.set_status(
                "Select at least one clothing or accessory model.",
                u"warning",
            )
            return

        try:
            if not self.operation_begin(
                "Clothing Fit",
                pin_context=True,
            ):
                return

            prod_resource_snapshot(
                "ACTION_BEGIN:Clothing Fit"
            )
            ident = self.current()
            # CPM Step 4: one user Fit owns one semantic generation, Gfit.
            fit_context = prod_cpm_authorize_operation(
                ident,
                self.scope,
                P03_KIND_BODY,
                u"Clothing Fit",
            )
            source = prod_body_source(
                ident,
                self.scope,
                authority_context=fit_context,
            )

            self.fit_active = True
            self.fit_generation += 1
            generation = self.fit_generation
            self.fit_authority_context = fit_context
            self.fit_semantic_generation = fit_context[
                "master_sha256"
            ]
            fit_context = None
            self.fit_source_baseline = source
            self.fit_selected_identities = [
                dict(
                    item
                )
                for item in selected
            ]
            self.fit_changed = []
            self.fit_unchanged = []
            self.fit_committed_order = []
            self.fit_partial = []
            self.fit_skipped = []
            self.fit_failed = []
            self.fit_unattempted = []
            self.fit_set_enabled(
                False
            )
            self.set_status(
                "Fitting selected models to this model..."
            )

            try:
                log_line(
                    "CLOTHING_FIT_START generation=%d operation_id=%d source=%r selected=%r pure_source_baseline=True"
                    % (
                        generation,
                        self.operation[
                            "operation_id"
                        ],
                        ident,
                        selected,
                    )
                )
            except Exception:
                pass

            QtCore.QTimer.singleShot(
                0,
                lambda: self.fit_stage(
                    generation,
                    0,
                ),
            )

        except Exception as exc:
            try:
                log_line(
                    "CLOTHING_FIT_START_FAIL error=%r"
                    % exc
                )
            except Exception:
                pass
            try:
                log_line(
                    traceback.format_exc()
                )
            except Exception:
                pass
            self.fit_active = False
            self.fit_source_baseline = None
            self.fit_authority_context = None
            self.fit_semantic_generation = None
            self.set_status(
                "Clothing Fit could not start. Nothing changed.",
                u"error",
            )
            self.operation_end(
                "Clothing Fit"
            )
            self.prod_cpm_request_stale_rebuild_if_needed()


    def fit_stage(
        self,
        generation,
        index,
    ):
        # Check only Python-owned lifecycle fields before touching Qt/DME.
        if (
            self.closing_requested
            or not self.fit_active
            or generation
            != self.fit_generation
            or self.operation is None
        ):
            return

        if self.scene_activity_suspended:
            self.modal_deferred_fit_stage = (
                generation,
                index,
            )
            try:
                log_line(
                    "G18AN_MODAL_DEFER_FIT generation=%d index=%d"
                    % (
                        generation,
                        index,
                    )
                )
            except Exception:
                pass
            return

        if index >= len(
            self.fit_selected_identities
        ):
            self.fit_finish(
                generation
            )
            self.fit_authority_context = None
            self.fit_semantic_generation = None
            return

        identity = dict(
            self.fit_selected_identities[
                index
            ]
        )
        stage_state = {
            "committed": False,
        }
        source_live = None
        target_row = None
        plan = None
        stage_authority = None
        self.fit_stage_running = True

        def stage_phase(
            phase,
            detail=None,
        ):
            # Commit truth is Python-owned and published before diagnostics.
            if phase == u"native-commit":
                stage_state[
                    "committed"
                ] = True

                committed_identity = dict(
                    identity
                )

                if committed_identity not in self.fit_committed_order:
                    self.fit_committed_order.append(
                        committed_identity
                    )

            self.operation_mark_phase(
                phase,
                detail,
            )

        try:
            self.operation_revalidate()

            target_row = g11a_resolve_target(
                identity
            )
            # CPM Step 4: prove Gfit for this target at the stage boundary
            # (after any foreign-modal deferral above) and hold the stage
            # lease through planning, mutation and post-stage verification.
            stage_authority = prod_cpm_open_fit_stage(
                self.fit_authority_context,
                target_row,
                index,
            )
            source_live = prod_body_source_live_from_baseline(
                self.fit_source_baseline,
                self.scope,
                authority_context=self.fit_authority_context,
                stage_authority=stage_authority,
            )

            try:
                plan = g11a_safe_plan(
                    source_live,
                    target_row,
                )
            except Exception as exc:
                if not prod_fit_expected_skip_error(
                    exc
                ):
                    raise

                self.fit_skipped.append(
                    {
                        "identity": dict(
                            identity
                        ),
                        "reason": u(
                            exc
                        ),
                    }
                )
                try:
                    log_line(
                        "CLOTHING_FIT_STAGE=SKIP generation=%d index=%d target=%r reason=%r"
                        % (
                            generation,
                            index,
                            identity,
                            exc,
                        )
                    )
                except Exception:
                    pass

                source_live = None
                target_row = None
                plan = None
                stage_authority = prod_cpm_release_fit_stage(
                    stage_authority,
                    index,
                )

                QtCore.QTimer.singleShot(
                    0,
                    lambda: self.fit_stage(
                        generation,
                        index + 1,
                    ),
                )
                return

            outcome = prod_apply_match(
                plan,
                phase_callback=stage_phase,
                operation_context=self.operation.get(
                    "context"
                ),
            )

            if (
                self.closing_requested
                or generation
                != self.fit_generation
            ):
                self.fit_unattempted = [
                    dict(
                        item
                    )
                    for item in self.fit_selected_identities[
                        index + 1:
                    ]
                ]
                self.fit_active = False
                self.fit_source_baseline = None
                try:
                    log_line(
                        "CLOTHING_FIT_STAGE_CANCEL_AFTER_COMMIT generation=%d index=%d target=%r committed=%r unattempted=%r"
                        % (
                            generation,
                            index,
                            identity,
                            stage_state[
                                "committed"
                            ],
                            self.fit_unattempted,
                        )
                    )
                except Exception:
                    pass
                self.operation_end(
                    "Clothing Fit"
                )
                return

            # Fresh source and target bindings for post-stage verification.
            source_verify = prod_body_source_live_from_baseline(
                self.fit_source_baseline,
                self.scope,
                authority_context=self.fit_authority_context,
                stage_authority=stage_authority,
            )
            verify = g11a_safe_plan(
                source_verify,
                g11a_resolve_target(
                    identity
                ),
            )

            if verify[
                "changed_sides"
            ] != 0:
                raise RuntimeError(
                    "The fitted model did not match the current body after its transaction."
                )

            if plan[
                "warnings"
            ]:
                self.fit_partial.append(
                    {
                        "identity": dict(
                            identity
                        ),
                        "mapping_count": len(
                            plan[
                                "mapping"
                            ][
                                "mappings"
                            ]
                        ),
                        "warning_count": len(
                            plan[
                                "warnings"
                            ]
                        ),
                        "changed": (
                            outcome[
                                "phase"
                            ]
                            == u"committed-verified"
                        ),
                    }
                )
            elif outcome[
                "phase"
            ] == u"committed-verified":
                self.fit_changed.append(
                    dict(
                        identity
                    )
                )
            else:
                self.fit_unchanged.append(
                    dict(
                        identity
                    )
                )

            try:
                log_line(
                    "CLOTHING_FIT_STAGE=PASS generation=%d index=%d target=%r phase=%r mappings=%d warnings=%d committed=%r"
                    % (
                        generation,
                        index,
                        identity,
                        outcome[
                            "phase"
                        ],
                        len(
                            plan[
                                "mapping"
                            ][
                                "mappings"
                            ]
                        ),
                        len(
                            plan[
                                "warnings"
                            ]
                        ),
                        stage_state[
                            "committed"
                        ],
                    )
                )
            except Exception:
                pass

            source_live = None
            target_row = None
            plan = None
            source_verify = None
            verify = None
            stage_authority = prod_cpm_release_fit_stage(
                stage_authority,
                index,
            )

            QtCore.QTimer.singleShot(
                0,
                lambda: self.fit_stage(
                    generation,
                    index + 1,
                ),
            )

        except Exception as exc:
            if stage_authority is not None:
                try:
                    stage_authority.release()
                except Exception:
                    pass
                stage_authority = None
            committed_current = bool(
                stage_state[
                    "committed"
                ]
            )
            unattempted_from = getattr(
                exc,
                "unattempted_from",
                None,
            )

            abort_unverified = isinstance(
                exc,
                ProdRecoveryUnverifiedError,
            )

            if committed_current:
                verification = u"uncertain"
            elif abort_unverified:
                verification = u"abort-unverified"
            else:
                verification = u"not-committed"

            if unattempted_from is None:
                self.fit_failed.append(
                    {
                        "identity": dict(
                            identity
                        ),
                        "reason": u(
                            exc
                        ),
                        "committed": committed_current,
                        "verification": verification,
                    }
                )
                unattempted_from = index + 1

            # CPM Step 4: a Gfit change (or stage-release failure) stops the
            # Fit; the current target is only unattempted, never failed.
            self.fit_unattempted = [
                dict(
                    item
                )
                for item in self.fit_selected_identities[
                    unattempted_from:
                ]
            ]

            try:
                log_line(
                    "CLOTHING_FIT_FAIL generation=%d index=%d target=%r error=%r committed_current=%r changed=%r failed=%r unattempted=%r"
                    % (
                        generation,
                        index,
                        identity,
                        exc,
                        committed_current,
                        self.fit_changed,
                        self.fit_failed,
                        self.fit_unattempted,
                    )
                )
            except Exception:
                pass
            try:
                log_line(
                    traceback.format_exc()
                )
            except Exception:
                pass

            self.fit_active = False
            self.fit_source_baseline = None

            if not self.closing_requested:
                self.fit_set_enabled(
                    True
                )
                self.fit_clear_checks()
                self.fit_button.setEnabled(
                    False
                )

                committed_count = len(
                    self.fit_committed_order
                )

                recovery_unverified = any(
                    item.get(
                        "verification"
                    )
                    == u"abort-unverified"
                    for item in self.fit_failed
                )

                if committed_count or recovery_unverified:
                    if committed_count:
                        self.set_status(
                            "Clothing Fit stopped after changing %d item%s."
                            % (
                                committed_count,
                                (
                                    ""
                                    if committed_count == 1
                                    else "s"
                                ),
                            ),
                            u"error",
                        )
                    else:
                        self.set_status(
                            "Clothing Fit stopped. Recovery of the failed target could not be verified.",
                            u"error",
                        )

                    self.fit_show_partial_failure()
                else:
                    self.set_status(
                        "Clothing Fit could not finish. Nothing changed.",
                        u"error",
                    )

            self.operation_end(
                "Clothing Fit"
            )
            self.fit_authority_context = None
            self.fit_semantic_generation = None
            self.prod_cpm_request_stale_rebuild_if_needed()

        finally:
            if stage_authority is not None:
                try:
                    stage_authority.release()
                except Exception:
                    pass
            stage_authority = None
            source_live = None
            target_row = None
            plan = None
            self.fit_stage_running = False


    def fit_show_partial_failure(
        self,
    ):
        committed = [
            dict(
                item
            )
            for item in self.fit_committed_order
        ]
        unattempted = [
            dict(
                item
            )
            for item in self.fit_unattempted
        ]

        committed_uncertain = [
            dict(
                item.get(
                    "identity"
                )
            )
            for item in self.fit_failed
            if (
                item.get(
                    "committed"
                )
                and item.get(
                    "verification"
                )
                == u"uncertain"
                and isinstance(
                    item.get(
                        "identity"
                    ),
                    dict,
                )
            )
        ]
        recovery_unverified = [
            dict(
                item.get(
                    "identity"
                )
            )
            for item in self.fit_failed
            if (
                item.get(
                    "verification"
                )
                == u"abort-unverified"
                and isinstance(
                    item.get(
                        "identity"
                    ),
                    dict,
                )
            )
        ]

        def identity_key(
            identity,
        ):
            return (
                identity.get(
                    "model"
                ),
                identity.get(
                    "checksum"
                ),
                identity.get(
                    "name"
                )
                or identity.get(
                    "animset_name"
                ),
            )

        uncertain_keys = set(
            identity_key(
                item
            )
            for item in committed_uncertain
        )
        verified_committed = [
            item
            for item in committed
            if identity_key(
                item
            )
            not in uncertain_keys
        ]

        def display_names(
            items,
        ):
            names = []
            for identity in items:
                name = u(
                    identity.get(
                        "name"
                    )
                    or identity.get(
                        "animset_name"
                    )
                    or identity.get(
                        "model"
                    )
                    or "Unknown item"
                )
                names.append(
                    name
                )
            return names

        changed_names = display_names(
            verified_committed
        )
        uncertain_names = display_names(
            committed_uncertain
        )
        recovery_names = display_names(
            recovery_unverified
        )
        unattempted_names = display_names(
            unattempted
        )

        dialog = QtGui.QDialog(
            self
        )

        try:
            dialog.setWindowTitle(
                "Clothing Fit stopped"
            )
            dialog.setMinimumWidth(
                520
            )
            dialog.setMaximumWidth(
                620
            )

            outer = QtGui.QVBoxLayout(
                dialog
            )
            outer.setContentsMargins(
                14,
                14,
                14,
                14,
            )
            outer.setSpacing(
                7
            )

            if committed:
                lead_text = (
                    "Clothing Fit stopped after committing %d target%s."
                    % (
                        len(
                            committed
                        ),
                        (
                            ""
                            if len(
                                committed
                            )
                            == 1
                            else "s"
                        ),
                    )
                )
            else:
                lead_text = (
                    "Clothing Fit stopped before a completed target change."
                )

            lead = QtGui.QLabel(
                lead_text
            )
            lead.setWordWrap(
                True
            )
            outer.addWidget(
                lead
            )

            if changed_names:
                changed_label = QtGui.QLabel(
                    u"<b>Changed and verified</b><br>%s"
                    % u"<br>".join(
                        [
                            u"- " + name
                            for name in changed_names
                        ]
                    )
                )
                changed_label.setWordWrap(
                    True
                )
                outer.addWidget(
                    changed_label
                )

            if uncertain_names:
                uncertain_label = QtGui.QLabel(
                    u"<b>Committed; verification did not finish</b><br>%s"
                    % u"<br>".join(
                        [
                            u"- " + name
                            for name in uncertain_names
                        ]
                    )
                )
                uncertain_label.setWordWrap(
                    True
                )
                outer.addWidget(
                    uncertain_label
                )

            if recovery_names:
                recovery_label = QtGui.QLabel(
                    u"<b>Recovery could not be verified</b><br>%s"
                    % u"<br>".join(
                        [
                            u"- " + name
                            for name in recovery_names
                        ]
                    )
                )
                recovery_label.setWordWrap(
                    True
                )
                outer.addWidget(
                    recovery_label
                )

            if unattempted_names:
                unattempted_label = QtGui.QLabel(
                    u"<b>Not attempted</b><br>%s"
                    % u"<br>".join(
                        [
                            u"- " + name
                            for name in unattempted_names
                        ]
                    )
                )
                unattempted_label.setWordWrap(
                    True
                )
                outer.addWidget(
                    unattempted_label
                )

            if committed:
                undo_label = QtGui.QLabel(
                    "Each committed target has its own Clothing Fit Undo entry. "
                    "To revert these changes, use SFM Undo immediately %d time%s, before making other edits."
                    % (
                        len(
                            committed
                        ),
                        (
                            ""
                            if len(
                                committed
                            )
                            == 1
                            else "s"
                        ),
                    )
                )
                undo_label.setWordWrap(
                    True
                )
                outer.addWidget(
                    undo_label
                )

            if recovery_names:
                recovery_note = QtGui.QLabel(
                    "Inspect the recovery-unverified target before retrying. "
                    "If SFM shows an Undo entry for the failed attempt, use it before making other edits."
                )
                recovery_note.setWordWrap(
                    True
                )
                outer.addWidget(
                    recovery_note
                )

            buttons = QtGui.QDialogButtonBox(
                QtGui.QDialogButtonBox.Ok
            )
            buttons.accepted.connect(
                dialog.accept
            )
            outer.addWidget(
                buttons
            )

            tool_apply_visual_theme(
                dialog
            )
            tool_apply_dialog_font(
                dialog
            )

            try:
                log_line(
                    "G18AN_FIT_FAILURE_DIALOG verified_changed=%r committed_uncertain=%r "
                    "recovery_unverified=%r unattempted=%r undo_count=%d"
                    % (
                        changed_names,
                        uncertain_names,
                        recovery_names,
                        unattempted_names,
                        len(
                            committed
                        ),
                    )
                )
            except Exception:
                pass

            dialog.exec_()

        finally:
            dialog.deleteLater()


    def fit_finish(
        self,
        generation,
    ):
        if (
            not self.fit_active
            or generation
            != self.fit_generation
        ):
            return

        partial_changed = sum(
            1
            for item in self.fit_partial
            if bool(
                item.get(
                    "changed"
                )
            )
        )
        partial_unchanged = (
            len(
                self.fit_partial
            )
            - partial_changed
        )
        changed = (
            len(
                self.fit_changed
            )
            + partial_changed
        )
        unchanged = (
            len(
                self.fit_unchanged
            )
            + partial_unchanged
        )
        partial = len(
            self.fit_partial
        )
        skipped = len(
            self.fit_skipped
        )
        failed = len(
            self.fit_failed
        )
        unattempted = len(
            self.fit_unattempted
        )

        self.fit_active = False
        self.fit_source_baseline = None

        if not self.closing_requested:
            self.fit_set_enabled(
                True
            )
            self.fit_clear_checks()
            self.fit_button.setEnabled(
                False
            )

            if failed or unattempted:
                parts = []

                if changed:
                    parts.append(
                        "%d updated"
                        % changed
                    )

                if unchanged:
                    parts.append(
                        "%d already matched"
                        % unchanged
                    )

                if skipped:
                    parts.append(
                        "%d skipped"
                        % skipped
                    )

                if failed:
                    parts.append(
                        "%d failed"
                        % failed
                    )

                if unattempted:
                    parts.append(
                        "%d not attempted"
                        % unattempted
                    )

                message = (
                    "; ".join(
                        parts
                    )
                    + "."
                )
                level = u"error"

            elif skipped:
                parts = []

                if changed:
                    parts.append(
                        "%d updated"
                        % changed
                    )

                if unchanged:
                    parts.append(
                        "%d already matched"
                        % unchanged
                    )

                parts.append(
                    "%d skipped"
                    % skipped
                )

                message = (
                    "; ".join(
                        parts
                    )
                    + "."
                )
                level = u"warning"

            elif changed:
                if (
                    changed == 1
                    and unchanged == 0
                ):
                    message = u"1 item updated."
                elif unchanged:
                    message = (
                        "%d updated; %d already matched."
                        % (
                            changed,
                            unchanged,
                        )
                    )
                else:
                    message = (
                        "%d items updated."
                        % changed
                    )

                level = u"success"

            else:
                if unchanged == 1:
                    message = (
                        u"Selected item already matches this model."
                    )
                else:
                    message = (
                        u"Selected items already match this model."
                    )

                level = u"neutral"

            self.set_status(
                message,
                level,
            )

        try:
            log_line(
                "CLOTHING_FIT_RESULT generation=%d selected=%d changed=%d already_matched=%d "
                "partial=%d partial_changed=%d partial_already_matched=%d skipped=%d failed=%d "
                "unattempted=%d committed_order=%r reusable=True pure_source_baseline=True"
                % (
                    generation,
                    len(
                        self.fit_selected_identities
                    ),
                    changed,
                    unchanged,
                    partial,
                    partial_changed,
                    partial_unchanged,
                    skipped,
                    failed,
                    unattempted,
                    self.fit_committed_order,
                )
            )
        except Exception:
            pass

        if not self.closing_requested:
            log_line(
                "G18AN_POST_FIT_ACTION_STATE save_body=%r save_expr=%r semantic_ready=%r"
                % (
                    self.save_body.isEnabled(),
                    self.save_expr.isEnabled(),
                    self.semantic_provider_ready(),
                )
            )

        if self.operation is not None:
            self.operation[
                "phase"
            ] = u"UI_PUBLISH"

        self.operation_end(
            "Clothing Fit"
        )


    def tab_changed(self, index):
        if not hasattr(self, "status"):
            return
        page = self.tabs.currentWidget()
        if (
            self.identity is not None
            and not self.semantic_provider_ready()
        ):
            self.set_status(
                PROD_MASTER_PROVIDER_WARNING_COPY,
                u"warning",
            )
            return
        if page is self.fit_page:
            self.set_status("Select clothing or accessories to fit to this model.")
            return
        if hasattr(self, "review_page") and page is self.review_page:
            self.set_status("Select an unrecognized flex to classify.")
            return
        if page is self.body_page:
            item = self.selected_or_none(P03_KIND_BODY)
            self.set_status(u'Ready to apply "%s".' % prod_item_display_name(item) if item is not None else "Select a preset, then choose an action above.")
            return
        if page is self.expr_page:
            if not u(
                self.expr_search.text()
            ):
                QtCore.QTimer.singleShot(
                    0,
                    lambda: self.tabs.setFocus(
                        QtCore.Qt.OtherFocusReason
                    )
                )
            item = self.selected_or_none(P03_KIND_EXPRESSION)
            self.set_status(u'Ready to apply "%s".' % prod_item_display_name(item) if item is not None else "Select a preset, then choose an action above.")


    def open_details(
        self,
    ):
        def work():
            ident = self.current()
            scope = self.scope

            if not prod_scope_matches_identity(
                scope,
                ident,
            ):
                raise RuntimeError(
                    "The selected model's semantic scope is stale. Reselect the model."
                )

            review_count = (
                len(scope["unresolved"])
                + len(scope["conflicts"])
            )

            model_file_path = tool_resolve_model_file(
                ident["model"]
            )
            model_folder = (
                os.path.dirname(model_file_path)
                if model_file_path
                else None
            )

            preset_folder = prod_paths(ident)["char"]

            dialog = QtGui.QDialog(self)
            dialog.setWindowTitle("Model Info")
            dialog.resize(740, 500)

            outer = QtGui.QVBoxLayout(dialog)

            model_group = QtGui.QGroupBox(
                "Selected Model"
            )
            model_layout = QtGui.QVBoxLayout(
                model_group
            )
            model_form = QtGui.QFormLayout()

            model_name = QtGui.QLabel(
                u(ident["animset_name"])
            )
            model_name.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            model_form.addRow("Model:", model_name)

            model_file = QtGui.QLabel(
                u(ident["model"])
            )
            model_file.setWordWrap(True)
            model_file.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            model_form.addRow("Model path:", model_file)

            model_layout.addLayout(model_form)

            open_model = QtGui.QPushButton(
                "Open Model Folder"
            )
            open_model.setAutoDefault(False)
            open_model.setDefault(False)
            open_model.setEnabled(
                bool(model_folder)
            )
            if model_file_path:
                open_model.setToolTip(model_file_path)
            else:
                open_model.setToolTip(
                    "The model's physical folder could not be resolved."
                )
            open_model.clicked.connect(
                lambda: tool_open_folder(
                    dialog,
                    model_folder,
                    "Open Model Folder",
                )
            )
            model_layout.addWidget(open_model)

            outer.addWidget(model_group)

            flex_group = QtGui.QGroupBox(
                "Available Flexes"
            )
            flex_form = QtGui.QFormLayout(
                flex_group
            )
            flex_form.addRow(
                "Body:",
                QtGui.QLabel(
                    unicode(len(scope["body"]))
                ),
            )
            flex_form.addRow(
                "Facial:",
                QtGui.QLabel(
                    unicode(
                        len(scope["expression"])
                    )
                ),
            )
            flex_form.addRow(
                "Unrecognized flexes:",
                QtGui.QLabel(
                    unicode(review_count)
                    if review_count
                    else u"None"
                ),
            )
            outer.addWidget(flex_group)

            presets_group = QtGui.QGroupBox(
                "Saved Presets"
            )
            presets_form = QtGui.QFormLayout(
                presets_group
            )
            presets_form.addRow(
                "Body:",
                QtGui.QLabel(
                    unicode(len(self.body_items))
                ),
            )
            presets_form.addRow(
                "Expressions:",
                QtGui.QLabel(
                    unicode(len(self.expr_items))
                ),
            )
            outer.addWidget(presets_group)

            library_group = QtGui.QGroupBox(
                "Preset Library"
            )
            library_layout = QtGui.QVBoxLayout(
                library_group
            )
            library_layout.addWidget(
                QtGui.QLabel(
                    "Presets for this model are stored here:"
                )
            )

            library_path = QtGui.QLabel(
                u(preset_folder)
            )
            library_path.setWordWrap(True)
            library_path.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            library_layout.addWidget(library_path)

            open_library = QtGui.QPushButton(
                "Open Preset Folder"
            )
            open_library.setAutoDefault(False)
            open_library.setDefault(False)
            open_library.setEnabled(
                os.path.isdir(preset_folder)
            )
            open_library.clicked.connect(
                lambda: tool_open_folder(
                    dialog,
                    preset_folder,
                    "Open Preset Folder",
                )
            )
            library_layout.addWidget(open_library)
            outer.addWidget(library_group)

            buttons = QtGui.QDialogButtonBox(
                QtGui.QDialogButtonBox.Close
            )
            buttons.rejected.connect(
                dialog.reject
            )
            outer.addWidget(buttons)

            tool_apply_visual_theme(dialog)
            tool_apply_dialog_font(dialog)


            try:
                dialog.exec_()
            finally:
                dialog.deleteLater()

        return self.guard("Model Info", work)

    def open_preset_info(
        self,
        kind,
    ):
        def work():
            ident = self.current()
            item = self.selected(kind)
            record = item["record"]

            name_value = u(
                record.get("name")
                or record.get("preset_id")
                or u"Preset"
            )

            dialog = QtGui.QDialog(self)
            dialog.setWindowTitle("Preset Info")
            dialog.resize(700, 560)

            outer = QtGui.QVBoxLayout(dialog)

            summary = QtGui.QGroupBox("Preset")
            form = QtGui.QFormLayout(summary)

            name_label = QtGui.QLabel(name_value)
            name_label.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            form.addRow("Name:", name_label)

            form.addRow(
                "Type:",
                QtGui.QLabel(
                    "Body Preset"
                    if kind == P03_KIND_BODY
                    else "Expression"
                ),
            )
            form.addRow(
                "Model:",
                QtGui.QLabel(
                    u(ident["animset_name"])
                ),
            )

            model_path_value = u(
                ident["model"]
            ).replace(
                u"\\",
                u"/",
            )
            model_path_label = QtGui.QLabel(
                model_path_value
            )
            model_path_label.setWordWrap(
                True
            )
            model_path_label.setTextInteractionFlags(
                QtCore.Qt.TextSelectableByMouse
            )
            form.addRow(
                "Model path:",
                model_path_label,
            )

            form.addRow(
                "Saved:",
                QtGui.QLabel(
                    tool_format_saved_stamp(
                        record.get("created_at")
                    )
                ),
            )

            modified_value = record.get("modified_at")
            if modified_value:
                form.addRow(
                    "Updated:",
                    QtGui.QLabel(
                        tool_format_saved_stamp(modified_value)
                    ),
                )

            form.addRow(
                "Favorite:",
                QtGui.QLabel(
                    "Yes" if self.is_favorite_cached(record) else "No"
                ),
            )

            if item.get("source") == u"legacy-v2":
                form.addRow(
                    "Library:",
                    QtGui.QLabel(
                        "Read-only legacy preset"
                    ),
                )

            outer.addWidget(summary)

            content_group = QtGui.QGroupBox(
                "Saved Values"
            )
            content_layout = QtGui.QVBoxLayout(
                content_group
            )

            if kind == P03_KIND_BODY:
                note_text = (
                    u"Flexes saved at 0 and bone scales saved at 1.0\u00d7 are hidden."
                )
                first_header = "Flex / Bone"
            else:
                note_text = (
                    "Flexes saved at 0 are hidden."
                )
                first_header = "Flex"

            note = QtGui.QLabel(note_text)
            note.setWordWrap(True)
            content_layout.addWidget(note)

            tree = tool_make_value_tree(
                content_group,
                first_header,
            )
            content_layout.addWidget(tree, 1)

            values = record.get("values") or {}
            flex_rows = []

            for key in sorted(values.keys()):
                key_u = u(key)
                if not key_u.startswith(u"flex."):
                    continue

                literal = key_u[len(u"flex."):]
                value_record = values[key]
                representation = u(
                    value_record.get(
                        "representation"
                    )
                    or u""
                )

                if representation == u"MONO":
                    value = as_float(
                        value_record.get("mono")
                    )
                    if (
                        value is not None
                        and not close_enough(
                            value,
                            0.0,
                        )
                    ):
                        flex_rows.append(
                            (
                                literal,
                                tool_format_number(value),
                            )
                        )

                elif representation == u"STEREO":
                    left = as_float(
                        value_record.get("left")
                    )
                    right = as_float(
                        value_record.get("right")
                    )
                    left = 0.0 if left is None else left
                    right = 0.0 if right is None else right

                    if (
                        close_enough(left, 0.0)
                        and close_enough(right, 0.0)
                    ):
                        continue

                    if close_enough(left, right):
                        display = tool_format_number(left)
                    else:
                        display = (
                            u"Left %s / Right %s"
                            % (
                                tool_format_number(left),
                                tool_format_number(right),
                            )
                        )

                    flex_rows.append(
                        (
                            literal,
                            display,
                        )
                    )

            flex_title = (
                "Body flexes (%d)" % len(flex_rows)
                if kind == P03_KIND_BODY
                else "Facial flexes (%d)" % len(flex_rows)
            )
            flex_root = QtGui.QTreeWidgetItem(
                [
                    flex_title,
                    "",
                ]
            )
            tree.addTopLevelItem(flex_root)
            tool_add_banded_value_rows(
                flex_root,
                flex_rows,
            )

            if kind == P03_KIND_BODY:
                scale_rows = []

                for row in (
                    record.get("bone_scales")
                    or []
                ):
                    try:
                        bone_name = u(
                            row["bone_name"]
                        )
                        value = float(
                            row["value"]
                        )
                    except Exception:
                        continue

                    if close_enough(value, 1.0):
                        continue

                    scale_rows.append(
                        (
                            bone_name,
                            u"%s\u00d7"
                            % tool_format_number(value),
                        )
                    )

                scale_rows.sort(
                    key=lambda row: row[0].lower()
                )

                scale_root = QtGui.QTreeWidgetItem(
                    [
                        "Scaled bones (%d)"
                        % len(scale_rows),
                        "",
                    ]
                )
                tree.addTopLevelItem(scale_root)
                tool_add_banded_value_rows(
                    scale_root,
                    scale_rows,
                )

            tree.expandAll()
            outer.addWidget(content_group, 1)

            buttons = QtGui.QDialogButtonBox(
                QtGui.QDialogButtonBox.Close
            )
            buttons.rejected.connect(
                dialog.reject
            )
            outer.addWidget(buttons)

            tool_apply_visual_theme(dialog)
            tool_apply_dialog_font(dialog)


            try:
                dialog.exec_()
            finally:
                dialog.deleteLater()

        return self.guard("Preset Info", work)

    def open_help(
        self,
    ):
        def work():
            dialog = QtGui.QDialog(self)
            dialog.setWindowTitle(
                "SFM Character Preset Manager - Help"
            )
            dialog.resize(820, 770)

            outer = QtGui.QVBoxLayout(dialog)

            help_text = QtGui.QTextBrowser(dialog)
            help_text.setOpenExternalLinks(False)
            help_text.setHtml(
                u"""
                <style>
                    h3 { color: #7c8f9c; margin-top: 12px; margin-bottom: 3px; }
                    p  { margin-top: 0px; margin-bottom: 9px; }
                </style>
                <h3>Getting started</h3>
                <p>Choose the character you want to edit. Use <b>Body Presets</b> for body shape and <b>Expressions</b> for facial expressions. In <b>Clothing Fit</b>, choose clothing or accessories to fit to that character.</p>
                <p>The model list shows models in the shot under the playhead. To use a character from another shot, move the playhead into that shot, click <b>Refresh Model List</b>, then choose the character.</p>

                <h3>Body Presets</h3>
                <p>Save body flexes and bone scaling together as one preset. <b>Apply Preset</b> copies those saved values to the selected model.</p>

                <h3>Expressions</h3>
                <p>Save facial flexes as their own preset. <b>Apply Preset</b> copies those saved facial values to the selected model.</p>

                <h3>Clothing Fit</h3>
                <p>Match selected clothing and accessories to the selected model's body shape.</p>

                <h3>Preset controls</h3>
                <p><b>Save New</b> creates a new preset from the current values. <b>Update Preset</b> overwrites the selected preset with the current values. <b>Add Favorite</b> marks presets for the <b>Favorites only</b> filter. <b>Delete Preset</b> moves the selected preset to Trash.</p>

                <h3>Undo</h3>
                <p>Use SFM's normal Undo command <b>(Ctrl+Z)</b> to reverse applied Body Presets, Expressions, and Clothing Fit changes.</p>

                <h3>Why does Review appear?</h3>
                <p>Review appears when the Manager cannot classify a flex. For each unrecognized flex, decide whether it belongs in <b>Body Presets</b> or <b>Expressions</b>, or should be excluded from presets. Your choices are saved for this model. To change one later, select it under <b>Reviewed choices</b> and click <b>Clear Classification</b>.</p>

                <h3>Where presets are saved</h3>
                <p>Each model has its own preset library. Use <b>Model Info &gt; Open Preset Folder</b> to open it.</p>

                <h3>Why are so many flexes in Review?</h3>
                <p>The Manager uses the Animation Groups Master to identify Body and Expression controls. If many flexes appear in Review, your Master may be missing or out of date. Update it before reviewing controls manually.</p>
                """
            )
            outer.addWidget(help_text, 1)

            master_row = QtGui.QHBoxLayout()
            master_button = QtGui.QPushButton(
                "Download / Update Master on GitHub"
            )
            master_button.setAutoDefault(False)
            master_button.setDefault(False)
            master_button.setToolTip(
                "Opens GitHub"
            )

            master_button.clicked.connect(
                self.open_master_page
            )
            master_row.addWidget(
                master_button
            )
            master_row.addStretch(1)
            outer.addLayout(
                master_row
            )

            footer_row = QtGui.QHBoxLayout()

            footer = QtGui.QLabel(
                u"License: CC0 1.0 Universal \u00b7 Author: ChadChan3D"
            )
            footer.setStyleSheet(
                "color: #a8a8a8;"
            )
            footer_row.addWidget(
                footer
            )
            footer_row.addStretch(
                1
            )

            buttons = QtGui.QDialogButtonBox(
                QtGui.QDialogButtonBox.Close
            )
            buttons.rejected.connect(
                dialog.reject
            )
            footer_row.addWidget(
                buttons
            )
            outer.addLayout(
                footer_row
            )

            tool_apply_visual_theme(dialog)
            tool_apply_dialog_font(dialog)

            try:
                dialog.exec_()
            finally:
                dialog.deleteLater()

        return self.guard("Help", work)

    def closeEvent(
        self,
        event,
    ):
        self.closing_requested = True
        self.scene_activity_suspended = True
        self.modal_deferred_fit_stage = None

        try:
            self.modal_watch_timer.stop()
        except Exception:
            pass

        self.status_generation = int(
            getattr(
                self,
                "status_generation",
                0,
            )
        ) + 1


        try:
            log_line(
                "PROD_CLOSE_REQUEST operation=%r fit_active=%r fit_stage_running=%r"
                % (
                    (
                        None
                        if self.operation is None
                        else self.operation.get(
                            "kind"
                        )
                    ),
                    self.fit_active,
                    self.fit_stage_running,
                )
            )
        except Exception:
            pass

        if self.fit_active:
            self.fit_generation += 1
            self.fit_active = False
            self.fit_source_baseline = None

        if self.fit_stage_running:
            # The executing stage must unwind before the C++ window is
            # destroyed. Hide immediately; its finally/operation_end path
            # will schedule a second close.
            try:
                event.ignore()
                self.hide()
            except Exception:
                pass
            return

        if self.operation is not None:
            if self.operation.get(
                "kind"
            ) == u"Clothing Fit":
                # Pending queued stage: generation is already invalidated, so
                # it can be ended without waiting for another callback.
                self.operation_end(
                    "Clothing Fit"
                )

            try:
                event.ignore()
                self.hide()
            except Exception:
                pass
            return

        try:
            app = QtGui.QApplication.instance()

            if (
                app is not None
                and getattr(
                    app,
                    PROD_APP_ATTR,
                    None,
                )
                is self
            ):
                setattr(
                    app,
                    PROD_APP_ATTR,
                    None,
                )

        except Exception:
            pass

        log_line(
            "PROD_CLOSE_FINALIZED=True"
        )

        # R15: finalize through the base rejection path. The base closeEvent
        # would call the reject() override (close()) while this close is in
        # progress, leaving the window visible and the close ignored. Do not
        # access window state after this terminal call.
        event.accept()
        QtGui.QDialog.reject(
            self
        )



# CPM R15: startup state of the one stable private application module.
# The launcher owns module loading (ABSENT -> LOADING -> READY) and the launch
# notice; this module owns window decisions. READY is permanent; windows come
# and go. STARTING refuses re-entry; FAILED_RESTART_REQUIRED latches after an
# unexpected failure once window construction has begun.
PROD_R15_STARTUP_IDLE = u"idle"
PROD_R15_STARTUP_STARTING = u"starting"
PROD_R15_STARTUP_FAILED = u"failed-restart-required"
PROD_R15_STARTUP = {
    "state": PROD_R15_STARTUP_IDLE,
    "failure": None,
}
PROD_R15_NOTICE_COPY = {
    u"refuse-closing": u"Character Preset Manager is still closing. Wait a moment, then open it again.",
    u"refuse-modal-yield": u"Character Preset Manager is waiting for another dialog to close.",
    u"refuse-foreign-modal": u"Close the open dialog, then open Character Preset Manager again.",
    u"refuse-owned-modal": u"Finish the open Character Preset Manager dialog first.",
    u"refuse-foreign-window": (
        u"Another Character Preset Manager window (a different build) is open. "
        u"Close it, then open Character Preset Manager again."
    ),
    u"refuse-malformed": u"Character Preset Manager could not start in this SFM session. Restart SFM to use it.",
    u"refuse-uncertain": (
        u"Character Preset Manager could not confirm the state of its existing window. "
        u"Restart SFM to use it again."
    ),
    u"refuse-starting": u"Character Preset Manager is already starting.",
    u"refuse-failed-restart-required": (
        u"Character Preset Manager could not open earlier in this SFM session. "
        u"Restart SFM to use it again."
    ),
    u"refuse-reuse-failed": u"Character Preset Manager could not show its window. Try again.",
    u"open-failed": u"Character Preset Manager could not open. Try again.",
    u"failed-restart-required": u"Character Preset Manager could not open. Restart SFM to use it again.",
}


def prod_r15_qt_alive(
    obj,
):
    """True if the Qt object is alive, False only if it is definitively
    deleted, None if liveness cannot be established. Exceptions from other
    calls are never treated as proof of deletion."""
    try:
        from PySide import shiboken
    except Exception:
        return None

    try:
        return bool(
            shiboken.isValid(
                obj
            )
        )
    except Exception:
        return None


def prod_r15_result(
    outcome,
    code,
    detail=None,
):
    notice = PROD_R15_NOTICE_COPY.get(
        code
    )

    if outcome != u"created" and outcome != u"reused":
        try:
            log_line(
                "PROD_R15_LAUNCH_REFUSED outcome=%r code=%r detail=%r run_id=%r"
                % (
                    outcome,
                    code,
                    detail,
                    PROD_RUN_ID,
                )
            )
        except Exception:
            pass

    return {
        "outcome": outcome,
        "code": code,
        "notice": notice,
    }


def prod_r15_launcher_refusal(
    code,
    detail=None,
):
    """Logs a refusal decided by the launcher while this READY module is
    loaded (for example, changed installed bytes). The module, its window
    and its lifecycle state are left untouched."""
    global OUTPUT_PATH
    OUTPUT_PATH = PROD_OUTPUT_PATH
    return prod_r15_result(
        u"refused",
        code,
        detail,
    )


def prod_r15_window_decision(
    app,
):
    """(decision, window, detail) for the application window slot. Only a
    ProdWindow of this module is owned; foreign occupants are never closed,
    adopted or replaced; uncertainty is never read as an empty slot."""
    try:
        modal = app.activeModalWidget()
    except Exception as exc:
        return (u"refuse-uncertain", None, u"active-modal-unreadable %r" % (exc,))

    try:
        existing = getattr(
            app,
            PROD_APP_ATTR,
            None,
        )
    except Exception as exc:
        return (u"refuse-uncertain", None, u"slot-unreadable %r" % (exc,))

    if existing is not None:
        if not isinstance(
            existing,
            QtGui.QWidget,
        ):
            return (u"refuse-malformed", None, u"slot-type %r" % (type(existing).__name__,))

        owned = isinstance(
            existing,
            ProdWindow,
        )
        alive = prod_r15_qt_alive(
            existing
        )

        if alive is None:
            return (u"refuse-uncertain", None, u"liveness-unknown owned=%r" % (owned,))

        if alive is False:
            try:
                if getattr(
                    app,
                    PROD_APP_ATTR,
                    None,
                ) is existing:
                    setattr(
                        app,
                        PROD_APP_ATTR,
                        None,
                    )
            except Exception as exc:
                return (u"refuse-uncertain", None, u"slot-clear-failed %r" % (exc,))

            try:
                log_line(
                    "PROD_R15_SLOT_CLEARED reason='deleted-qt-object' owned=%r"
                    % owned
                )
            except Exception:
                pass
            existing = None

        elif not owned:
            return (u"refuse-foreign-window", None, u"class=%r" % (type(existing).__name__,))

    if existing is None:
        if modal is not None:
            return (u"refuse-foreign-modal", None, u"class=%r" % (type(modal).__name__,))

        return (u"create", None, None)

    if getattr(
        existing,
        "closing_requested",
        True,
    ):
        return (u"refuse-closing", None, None)

    if getattr(
        existing,
        "modal_yield_active",
        True,
    ):
        return (u"refuse-modal-yield", None, None)

    if modal is not None:
        if existing.modal_is_owned_by_manager(
            modal
        ):
            return (u"refuse-owned-modal", None, u"class=%r" % (type(modal).__name__,))

        return (u"refuse-foreign-modal", None, u"class=%r" % (type(modal).__name__,))

    return (u"reuse", existing, None)


def prod_r15_close_partial_window(
    app,
    window,
):
    """Best-effort close of the known, owned window from a failed startup.
    Arbitrary Qt widgets are never swept."""
    if window is None:
        return False

    try:
        if getattr(
            app,
            PROD_APP_ATTR,
            None,
        ) is window:
            setattr(
                app,
                PROD_APP_ATTR,
                None,
            )
    except Exception:
        pass

    try:
        window.modal_watch_timer.stop()
    except Exception:
        pass

    try:
        window.close()
        return True
    except Exception:
        pass

    try:
        window.hide()
        window.deleteLater()
        return True
    except Exception:
        return False


def StartProdTool():
    """CPM R15 startup. Called by the launcher only after the private module
    is READY. Returns {"outcome", "code", "notice"}; the launcher presents
    any notice. Never reloads or resets module state."""
    global OUTPUT_PATH
    OUTPUT_PATH = PROD_OUTPUT_PATH

    app = QtGui.QApplication.instance()

    if app is None:
        return prod_r15_result(u"refused", u"no-qapplication")

    state = PROD_R15_STARTUP.get(
        "state"
    )

    if state == PROD_R15_STARTUP_FAILED:
        return prod_r15_result(u"refused", u"refuse-failed-restart-required")

    if state != PROD_R15_STARTUP_IDLE:
        return prod_r15_result(u"refused", u"refuse-starting", state)

    decision, window, detail = prod_r15_window_decision(
        app
    )

    if decision == u"reuse":
        try:
            window.show(); window.raise_(); window.activateWindow()
        except Exception as exc:
            return prod_r15_result(u"refused", u"refuse-reuse-failed", u"%r" % (exc,))

        try:
            log_line("PROD_R15_WINDOW_REUSED run_id=%r" % (PROD_RUN_ID,))
        except Exception:
            pass
        return prod_r15_result(u"reused", u"reuse")

    if decision != u"create":
        return prod_r15_result(u"refused", decision, detail)

    PROD_R15_STARTUP["state"] = PROD_R15_STARTUP_STARTING
    window = None
    constructing = False

    try:
        if not os.path.isfile(OUTPUT_PATH): reset_log()
        log_line("="*120)
        try:
            log_line("%s %s"%(TOOL_NAME,PROD_VERSION))
        except Exception:
            pass
        try:
            log_line("G18AN_RUN run_id=%r pid=%d parity_oracle=%r" % (PROD_RUN_ID, PROD_PID, PROD_Q1_INDEXED_CAPTURE_PARITY))
        except Exception:
            pass
        try:
            log_line("PROD_R15_MODULE name=%r loader=%r state=%r build_sha256=%r file=%r" % (__name__, globals().get("__chadchan3d_cpm_loader__"), globals().get("__chadchan3d_cpm_state__"), globals().get("__chadchan3d_cpm_build_sha256__"), globals().get("__file__")))
        except Exception:
            pass
        prod_prepare_library_root()
        constructing = True
        window=ProdWindow(qt_parent())
        setattr(app,PROD_APP_ATTR,window)
        window.show()
        window.raise_()
        window.activateWindow()
        try:
            log_line("PROD_WINDOW_SHOWN=True initial_index=%d"%window.combo.currentIndex())
        except Exception:
            pass
        log_line("MAINMENU_CALLBACK_RETURNING=True")
        log_line("="*120)
    except BaseException as exc:
        diagnostics = traceback.format_exc()
        try:
            log_line("PROD_OPEN_FAIL=%r"%exc)
        except Exception:
            pass
        try:
            log_line(diagnostics)
        except Exception:
            pass

        if constructing:
            PROD_R15_STARTUP["state"] = PROD_R15_STARTUP_FAILED
            PROD_R15_STARTUP["failure"] = diagnostics
            closed = prod_r15_close_partial_window(
                app,
                window,
            )
            try:
                log_line(
                    "PROD_R15_STARTUP_FAILED_RESTART_REQUIRED=True partial_window=%r closed=%r"
                    % (
                        window is not None,
                        closed,
                    )
                )
            except Exception:
                pass
            result = prod_r15_result(u"failed", u"failed-restart-required", u"%r" % (exc,))
        else:
            PROD_R15_STARTUP["state"] = PROD_R15_STARTUP_IDLE
            result = prod_r15_result(u"failed", u"open-failed", u"%r" % (exc,))

        if not isinstance(
            exc,
            Exception,
        ):
            raise exc

        window = None
        exc = None

        try:
            sys.exc_clear()
        except AttributeError:
            pass

        return result

    PROD_R15_STARTUP["state"] = PROD_R15_STARTUP_IDLE
    return prod_r15_result(u"created", u"create")
