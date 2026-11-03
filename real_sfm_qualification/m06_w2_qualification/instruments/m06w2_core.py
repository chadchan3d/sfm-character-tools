# -*- coding: utf-8 -*-
"""M-06 W2 qualification core: strict, read-only native observation (temporary qualification instrument; not
product code).

Loaded by exec() into a private namespace by the Observer, the Abort Injector and the native probes (nothing is
placed in sys.modules or any CPM module). Python 2.7 (SFM) and 3.

Every native read records one of four states:

    {"s": "present", "v": value}    the attribute exists and was read (an element reference may be present-null)
    {"s": "null"}                   the attribute exists and holds a null element reference
    {"s": "absent"}                 the attribute verifiably does not exist (GetAttribute agrees with HasAttribute)
    {"s": "unreadable", "e": text}  anything else: an accessor failure, a disagreement, a non-Boolean presence

An exception is never converted into an apparently valid empty collection or neutral value. Unreadable evidence that
the observation requires is listed in record["insufficient"], which makes the whole observation insufficient.
Read-only by construction: no SetValue, key write, Operate, mode change, Undo command, playhead move, save or timer.
"""
import hashlib
import json
import math
import os
import re
import sys

try:
    text_type = unicode  # noqa: F821  (Python 2)
except NameError:
    text_type = str
try:
    INTEGER_TYPES = (int, long)  # noqa: F821
except NameError:
    INTEGER_TYPES = (int,)

FORMAT = u"M06W2-observation-v2"
CORE_VERSION = u"m06w2-core-v2"
# The accepted W1 application: an observation of any other installed CPM is insufficient.
ACCEPTED_W1_SHA256 = u"fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
CHANNEL_ATTRS = ("channel", "leftvaluechannel", "rightvaluechannel", "positionChannel", "orientationChannel")
BONE_RE = re.compile(r"^bone (\d+) \((.+)\)$")
MAX_KEYS_PER_LAYER = 20000
MAX_ELEMENTS = 200000


class Insufficient(Exception):
    """Raised only where the observation cannot continue at all (no document, wrong shot)."""


def text(v):
    if v is None:
        return None
    if isinstance(v, text_type):
        return v
    if isinstance(v, bytes):
        return v.decode("utf-8", "strict")
    return text_type(v)


def present(v):
    return {"s": u"present", "v": v}


def unreadable(why):
    return {"s": u"unreadable", "e": text(why) if not isinstance(why, BaseException) else text(repr(why))}


ABSENT = {"s": u"absent"}
NULL = {"s": u"null"}


def is_element(v):
    # GetId too: native array-attribute values also expose GetHandle and GetTypeString (G3-a obs_003).
    return v is not None and hasattr(v, "GetHandle") and hasattr(v, "GetTypeString") and hasattr(v, "GetId")


# ---------------------------------------------------------------------------
# Strict primitives
# ---------------------------------------------------------------------------

def strict_call(obj, method, *args):
    """(True, value) or (False, error text). Never a substituted value."""
    try:
        fn = getattr(obj, method)
    except Exception as exc:
        return False, u"%s unavailable: %r" % (method, exc)
    if not callable(fn):
        return False, u"%s not callable" % method
    try:
        return True, fn(*args)
    except Exception as exc:
        return False, u"%s raised %r" % (method, exc)


def handle_of(obj):
    ok, h = strict_call(obj, "GetHandle")
    if not ok or isinstance(h, bool) or not isinstance(h, INTEGER_TYPES + (float,)):
        return None
    try:
        return int(h)
    except Exception:
        return None


def ident(obj):
    """Strict identity of an element: type, name, handle and the unique-id text, each read natively."""
    if obj is None:
        return NULL
    row = {}
    for key, method in (("type", "GetTypeString"), ("name", "GetName")):
        ok, v = strict_call(obj, method)
        if not ok:
            return unreadable(u"%s: %s" % (key, v))
        try:
            row[key] = text(v)
        except Exception as exc:
            return unreadable(u"%s not text: %r" % (key, exc))
    h = handle_of(obj)
    if h is None:
        return unreadable(u"handle unreadable")
    row["handle"] = h
    ok, uid = strict_call(obj, "GetId")
    if not ok:
        return unreadable(u"id: %s" % uid)
    try:
        uid_text = text(str(uid))
    except Exception as exc:
        return unreadable(u"id text: %r" % exc)
    if not uid_text or uid_text.startswith(u"<") or u" at 0x" in uid_text.lower():
        return unreadable(u"id rendering is not content: %r" % uid_text)
    row["id"] = uid_text
    return present(row)


def native_attr_name(attr):
    """An attribute name for SFM's SWIG char* parameters: on Python 2 a unicode name is passed as an ASCII str (the
    proven production CPM native_attr_name pattern; SWIG rejects unicode). A non-ASCII name raises."""
    if str is bytes and isinstance(attr, text_type):
        return attr.encode("ascii")
    return attr


def read(element, attr):
    """The four-state read of one attribute (agreement of GetAttribute and HasAttribute, as M-06's strict reader)."""
    if element is None:
        return unreadable(u"element is null")
    try:
        name = native_attr_name(attr)
    except Exception as exc:
        return unreadable(u"attribute name %r is not a native name: %r" % (attr, exc))
    ok, has = strict_call(element, "HasAttribute", name)
    if not ok:
        return unreadable(has)
    if type(has) is not bool:
        return unreadable(u"HasAttribute(%s) returned %r" % (attr, has))
    try:
        a = element.GetAttribute(name)
    except AttributeError:
        a = None
    except Exception as exc:
        return unreadable(u"GetAttribute(%s) raised %r" % (attr, exc))
    if a is None:
        return ABSENT if has is False else unreadable(u"GetAttribute(%s) returned None but HasAttribute is True" % attr)
    if has is not True:
        return unreadable(u"GetAttribute(%s) returned an attribute but HasAttribute is False" % attr)
    ok, v = strict_call(a, "GetValue")
    if not ok:
        return unreadable(v)
    if v is None:
        return NULL
    return present(v)


def read_list(element, attr):
    """(record, items): items is the list of native elements/values only when the read is present."""
    r = read(element, attr)
    if r["s"] != u"present":
        return (r if r["s"] != u"null" else unreadable(u"array attribute %s is null" % attr)), None
    v = r["v"]
    # Bounded indexing only (the natively proven attempt-3 reader): never open-ended iteration of a native proxy.
    try:
        n = int(len(v))
    except Exception as exc:
        return unreadable(u"array %s length unreadable: %r" % (attr, exc)), None
    if n > MAX_ELEMENTS:
        return unreadable(u"array %s too large (%d)" % (attr, n)), None
    try:
        items = [v[i] for i in range(n)]
    except Exception as exc:
        return unreadable(u"array %s not indexable: %r" % (attr, exc)), None
    return present(len(items)), items


def finite(x):
    if isinstance(x, bool) or not isinstance(x, INTEGER_TYPES + (float,)):
        return False
    return not (math.isnan(float(x)) or math.isinf(float(x)))


def plain(v):
    """A JSON-safe rendering of a native value; elements become identities. Raises ValueError when the value cannot
    be rendered faithfully (the caller records it as unreadable)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, INTEGER_TYPES):
        return int(v)
    if isinstance(v, float):
        if not finite(v):
            raise ValueError("non-finite number")
        return v
    if isinstance(v, (text_type, bytes)):
        return text(v)
    if is_element(v):
        rec = ident(v)
        if rec["s"] != u"present":
            raise ValueError(u"element identity %s" % rec.get("e", rec["s"]))
        return rec
    if hasattr(v, "GetTenthsOfMS"):
        return {"ticks": int(v.GetTenthsOfMS())}
    comps = []
    for c in ("x", "y", "z", "w"):
        if hasattr(v, c):
            comps.append(getattr(v, c))
    if comps:
        out = [float(c) for c in comps]
        if not all(finite(c) for c in out):
            raise ValueError("non-finite component")
        return out
    try:
        n = int(len(v))
    except Exception:
        raise ValueError("unsupported native value %r" % (type(v),))
    if n > MAX_ELEMENTS:
        raise ValueError("native sequence too large (%d)" % n)
    return [plain(v[i]) for i in range(n)]


def value(element, attr):
    """read() rendered with plain()."""
    r = read(element, attr)
    if r["s"] != u"present":
        return r
    try:
        return present(plain(r["v"]))
    except Exception as exc:
        return unreadable(u"%s: %r" % (attr, exc))


def element_ref(element, attr):
    """(record, element): an element reference attribute. record is the identity (or null/absent/unreadable)."""
    r = read(element, attr)
    if r["s"] != u"present":
        return r, None
    if not is_element(r["v"]):
        return unreadable(u"%s is not an element" % attr), None
    rec = ident(r["v"])
    return rec, (r["v"] if rec["s"] == u"present" else None)


def key_of(rec):
    """Identity key (handle, id) of an identity record, or None."""
    if not isinstance(rec, dict) or rec.get("s") != u"present":
        return None
    return (rec["v"]["handle"], rec["v"]["id"])


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(1 << 20)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class Observation(object):
    def __init__(self):
        self.insufficient = []

    def require(self, path, rec):
        """Required evidence: anything but a readable state makes the observation insufficient."""
        if not isinstance(rec, dict) or rec.get("s") == u"unreadable":
            self.insufficient.append(u"%s: %s" % (path, (rec or {}).get("e", u"missing")))
        return rec

    def require_present(self, path, rec):
        if not isinstance(rec, dict) or rec.get("s") != u"present":
            self.insufficient.append(u"%s: required but %s" % (path, (rec or {}).get("s", u"missing")))
        return rec


def layer_record(ob, path, layer):
    rec = {"layer": ob.require_present(path + u"/layer", ident(layer))}
    ok, n = strict_call(layer, "GetKeyCount")
    if not ok or isinstance(n, bool) or not isinstance(n, INTEGER_TYPES):
        rec["key_count"] = ob.require(path + u"/key_count", unreadable(n))
        rec["keys"] = ob.require(path + u"/keys", unreadable(u"key count unknown"))
        return rec
    n = int(n)
    rec["key_count"] = present(n)
    if n > MAX_KEYS_PER_LAYER:
        rec["keys"] = ob.require(path + u"/keys", unreadable(u"too many keys (%d)" % n))
        return rec
    keys = []
    for i in range(n):
        ok_t, t = strict_call(layer, "GetKeyTime", i)
        ok_v, v = strict_call(layer, "GetKeyValue", i)
        try:
            if not (ok_t and ok_v):
                raise ValueError(t if not ok_t else v)
            keys.append([int(t.GetTenthsOfMS()), plain(v)])
        except Exception as exc:
            rec["keys"] = ob.require(path + u"/keys/%d" % i, unreadable(exc))
            return rec
    rec["keys"] = present(keys)
    for attr in ("times", "values", "curvetypes"):
        rec[attr] = ob.require(path + u"/" + attr, value(layer, attr))
    rec["compressed"] = ob.require(path + u"/compressed", binary_record(layer, "compressed"))
    crec, _ = element_ref(layer, "curveinfo")
    rec["curveinfo"] = ob.require(path + u"/curveinfo", crec)
    return rec


def binary_record(element, attr):
    """A binary attribute as its length and SHA-256 (never decoded as text)."""
    r = read(element, attr)
    if r["s"] != u"present":
        return r
    v = r["v"]
    try:
        if isinstance(v, bytes):
            data = v
        else:
            n = int(len(v))
            if n > MAX_ELEMENTS * 64:
                raise ValueError("binary attribute too large (%d)" % n)
            items = [v[i] for i in range(n)]
            data = b"".join(x if isinstance(x, bytes) else bytearray([int(x) & 0xFF]) for x in items) \
                if items else b""
        return present({"length": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    except Exception as exc:
        return unreadable(u"%s: %r" % (attr, exc))


def log_record(ob, path, channel):
    ok, log = strict_call(channel, "GetLog")
    if not ok:
        return ob.require(path, unreadable(log))
    if log is None:
        return NULL
    out = {"log": ob.require_present(path + u"/log", ident(log))}
    # The channel's "log" attribute must name the element GetLog() returned (the channel-log relationship).
    attr_rec, _ = element_ref(channel, "log")
    out["channel_log_attribute"] = ob.require(path + u"/channel_log_attribute", attr_rec)
    if attr_rec.get("s") == u"present" and key_of(attr_rec) != key_of(out["log"]):
        ob.insufficient.append(u"%s: the channel's log attribute and GetLog() disagree" % path)
    for k in ("usedefaultvalue", "defaultvalue", "bookmarks"):
        out[k] = ob.require(path + u"/" + k, value(log, k))
    crec, _ = element_ref(log, "curveinfo")
    out["curveinfo"] = ob.require(path + u"/curveinfo", crec)
    ok_e, empty = strict_call(log, "IsEmpty")
    out["is_empty"] = ob.require(path + u"/is_empty", present(empty) if ok_e and type(empty) is bool
                                 else unreadable(u"IsEmpty returned %r" % (empty,)))
    ok, n = strict_call(log, "GetNumLayers")
    if not ok or isinstance(n, bool) or not isinstance(n, INTEGER_TYPES):
        out["layer_count"] = ob.require(path + u"/layer_count", unreadable(n))
        return present(out)
    out["layer_count"] = present(int(n))
    layers = []
    for i in range(int(n)):
        ok, layer = strict_call(log, "GetLayer", i)
        if not ok or layer is None:
            layers.append(ob.require(path + u"/layers/%d" % i, unreadable(layer)))
            continue
        layers.append(layer_record(ob, path + u"/layers/%d" % i, layer))
    out["layers"] = layers
    # Transient: the native evaluation at the channel's current time (recorded, compared only where declared).
    ok_t, t = strict_call(channel, "GetCurrentTime")
    ok_v, ev = strict_call(log, "GetValue", t) if ok_t else (False, t)
    try:
        out["evaluated"] = present(plain(ev)) if ok_v else unreadable(ev)
        out["current_ticks_transient"] = present(int(t.GetTenthsOfMS())) if ok_t else unreadable(t)
    except Exception as exc:
        out["evaluated"] = unreadable(exc)
    ob.require(path + u"/evaluated", out["evaluated"])
    return present(out)


class Scene(object):
    """Shot-wide channel inventory: every channels clip and its channels, read strictly once."""

    def __init__(self, ob, shot):
        self.ob = ob
        self.clips = []
        self.channels = {}      # key -> native channel
        self.endpoints = {}     # key -> {"from":..., "from_attribute":..., "to":..., "to_attribute":..., "mode":...}
        self.unresolved = []    # channels whose endpoints cannot be read: they may write anything
        groups_rec, groups = read_list(shot, "trackGroups")
        ob.require(u"shot/trackGroups", groups_rec)
        for gi, group in enumerate(groups or []):
            tracks_rec, tracks = read_list(group, "tracks")
            ob.require(u"shot/trackGroups/%d/tracks" % gi, tracks_rec)
            for ti, track in enumerate(tracks or []):
                kids_rec, kids = read_list(track, "children")
                ob.require(u"shot/trackGroups/%d/tracks/%d/children" % (gi, ti), kids_rec)
                for ci, clip in enumerate(kids or []):
                    path = u"shot/trackGroups/%d/tracks/%d/children/%d" % (gi, ti, ci)
                    cid = ob.require_present(path, ident(clip))
                    has_channels = read(clip, "channels")
                    if has_channels["s"] == u"absent":
                        continue
                    ch_rec, chans = read_list(clip, "channels")
                    ob.require(path + u"/channels", ch_rec)
                    members = []
                    for ch in chans or []:
                        crec = ident(ch)
                        if crec["s"] != u"present":
                            ob.require(path + u"/channels/<member>", crec)
                            continue
                        k = key_of(crec)
                        members.append(crec["v"])
                        if k not in self.channels:
                            self.channels[k] = ch
                            self.endpoints[k] = self._endpoints(ch, crec)
                    self.clips.append({"clip": cid, "channels": members})

    def _endpoints(self, ch, crec):
        row = {"channel": crec}
        for side in ("from", "to"):
            erec, el = element_ref(ch, side + "Element")
            if el is not None:
                _ELEMENTS[key_of(erec)] = el
            row[side] = erec
            row[side + "_key"] = key_of(erec)
            row[side + "_attribute"] = value(ch, side + "Attribute")
        row["mode"] = value(ch, "mode")
        if any(row[k]["s"] == u"unreadable" for k in ("to", "to_attribute", "from", "from_attribute")):
            self.unresolved.append(crec["v"])
        return row

    def writers(self, target_key, attribute=None):
        out = []
        for k, ep in sorted(self.endpoints.items()):
            if ep["to_key"] == target_key:
                if attribute is None or (ep["to_attribute"].get("s") == u"present" and
                                         ep["to_attribute"]["v"] == attribute):
                    out.append(k)
        return out

    def readers(self, source_key):
        return [k for k, ep in sorted(self.endpoints.items()) if ep["from_key"] == source_key]

    def channel_view(self, k):
        ep = self.endpoints[k]
        return {"channel": ep["channel"], "from": ep["from"], "from_attribute": ep["from_attribute"], "to": ep["to"],
                "to_attribute": ep["to_attribute"], "mode": ep["mode"],
                "log": log_record(self.ob, u"channel/%s/log" % ep["channel"]["v"]["name"], self.channels[k])}

    def clip_of(self, k):
        hits = [c["clip"] for c in self.clips if any((m["handle"], m["id"]) == k for m in c["channels"])]
        return hits


def side_record(ob, path, scene, control, source_attr, channel_attr):
    rec = {"source_attr": source_attr, "channel_attr": channel_attr,
           "stored": ob.require(path + u"/stored", value(control, source_attr))}
    crec, ch = element_ref(control, channel_attr)
    rec["channel"] = ob.require(path + u"/channel", crec)
    if ch is None:
        return rec
    k = key_of(crec)
    if k not in scene.endpoints:
        rec["in_shot_clip"] = present(False)
        ob.insufficient.append(u"%s: channel is not in any channels clip of the shot" % path)
        return rec
    view = scene.channel_view(k)
    rec.update(view)
    rec["clips"] = present(scene.clip_of(k))
    to_key = scene.endpoints[k]["to_key"]
    to_attr = scene.endpoints[k]["to_attribute"]
    if to_key is not None and to_attr.get("s") == u"present":
        rec["destination_writers"] = present([scene.endpoints[w]["channel"]["v"]
                                              for w in scene.writers(to_key, to_attr["v"])])
        ok_el = [e for e in [scene_element(scene, rec["to"])] if e is not None]
        rec["destination_value"] = ob.require(path + u"/destination_value",
                                              value(ok_el[0], to_attr["v"]) if ok_el else unreadable(u"no target"))
    rec["control_writers"] = present([scene.endpoints[w]["channel"]["v"]
                                      for w in scene.writers(key_of(ident(control)))])
    rec["representation"] = representation(rec)
    return rec


_ELEMENTS = {}


def scene_element(scene, rec):
    k = key_of(rec)
    return _ELEMENTS.get(k)


def remember(obj):
    rec = ident(obj)
    k = key_of(rec)
    if k is not None:
        _ELEMENTS[k] = obj
    return rec


def representation(side):
    """Shape of one flex side from its own strict evidence (CPM's admission additionally needs writer evidence)."""
    try:
        log = side["log"]["v"]
        layers = log["layers"]
        mode = side["mode"]["v"]
        stored = side["stored"]["v"]
        evaluated = log["evaluated"]["v"]
        dest = side["destination_value"]["v"]
        if len(layers) != 1:
            return present(u"OTHER")
        keys = layers[0]["keys"]["v"]
    except Exception:
        return unreadable(u"representation evidence incomplete")
    if not keys:
        # CPM's EMPTY: no key and the log reports IsEmpty() True (coherence is checked by the comparator).
        return present(u"EMPTY") if (log.get("is_empty") or {}).get("v") is True else present(u"OTHER")
    if len(keys) == 1 and keys[0][0] == 0 and (log.get("is_empty") or {}).get("v") is False:
        k = keys[0][1]
        if k == stored:
            return present(u"ONE_KEY_ZERO")
        if mode == 3 and k == evaluated and k == dest and static_play_metadata(log):
            return present(u"STATIC_PLAY_ONE_KEY_ZERO")
    return present(u"OTHER")


def static_play_metadata(log):
    """CPM's flex_static_play_admitted() metadata: no curve info on the log or its layer, no per-key curve types, and
    an empty or absent compressed block (zero bytes)."""
    layer = log["layers"][0]

    def state(rec):
        return (rec or {}).get("s")
    compressed = layer.get("compressed") or {}
    return (state(log.get("curveinfo")) in (u"null", u"absent") and
            state(layer.get("curveinfo")) in (u"null", u"absent") and
            (state(layer.get("curvetypes")) == u"absent" or (layer.get("curvetypes") or {}).get("v") == []) and
            (state(compressed) == u"absent" or
             (state(compressed) == u"present" and (compressed.get("v") or {}).get("length") == 0)))


def control_record(ob, path, scene, control):
    rec = {"control": ob.require_present(path + u"/control", remember(control))}
    left, right = read(control, "leftValue"), read(control, "rightValue")
    ob.require(path + u"/leftValue", left)
    ob.require(path + u"/rightValue", right)
    if left["s"] == u"present" and right["s"] == u"present":
        rec["shape"] = u"STEREO"
        rec["left"] = side_record(ob, path + u"/left", scene, control, "leftValue", "leftvaluechannel")
        rec["right"] = side_record(ob, path + u"/right", scene, control, "rightValue", "rightvaluechannel")
    else:
        rec["shape"] = u"MONO"
        rec["mono"] = side_record(ob, path + u"/mono", scene, control, "value", "channel")
    return rec


def transform_control_record(ob, path, scene, control):
    rec = {"control": ob.require_present(path + u"/control", remember(control))}
    for attr in ("valuePosition", "valueOrientation"):
        rec[attr] = ob.require(path + u"/" + attr, value(control, attr))
    for attr in ("positionChannel", "orientationChannel"):
        crec, ch = element_ref(control, attr)
        rec[attr] = ob.require(path + u"/" + attr, crec)
        if ch is not None and key_of(crec) in scene.endpoints:
            rec[attr + "_view"] = scene.channel_view(key_of(crec))
    return rec


def by_name(ob, path, items):
    """name -> [element]; an unreadable name fails the observation (it could be a required control)."""
    out = {}
    for el in items:
        rec = ident(el)
        if rec["s"] != u"present":
            ob.require(path + u"/<element>", rec)
            continue
        out.setdefault(rec["v"]["name"], []).append(el)
    return out


def bones_record(ob, path, scene, gm):
    bones_rec, bones = read_list(gm, "bones")
    ob.require(path + u"/bones", bones_rec)
    out = []
    for i, bone in enumerate(bones or []):
        brec = ob.require_present(path + u"/bones/%d" % i, remember(bone))
        if brec["s"] != u"present":
            continue
        m = BONE_RE.match(brec["v"]["name"])
        if m is None:
            ob.insufficient.append(u"%s/bones/%d: bone transform name %r has no index" % (path, i, brec["v"]["name"]))
            continue
        k = key_of(brec)
        writers = []
        for wk in scene.writers(k):
            ep = scene.endpoints[wk]
            writers.append({"channel": ep["channel"]["v"], "to_attribute": ep["to_attribute"], "mode": ep["mode"]})
        out.append({"index": int(m.group(1)), "name": m.group(2), "transform": brec,
                    "scale": ob.require(path + u"/bones/%d/scale" % i, value(bone, "scale")),
                    "writers": writers,
                    # Corrected filter: the exact bone endpoint AND toAttribute == "scale".
                    "scale_writers": [scene.endpoints[w]["channel"]["v"] for w in scene.writers(k, "scale")]})
    return out


def graph_record(ob, path, scene, bone, writer_key):
    """One bone-scale graph from its scale writer: output channel <- operator <- input channel(s) <- control."""
    out = {"bone": bone["name"], "bone_index": bone["index"], "output": scene.channel_view(writer_key)}
    op_key = scene.endpoints[writer_key]["from_key"]
    op = scene_element(scene, scene.endpoints[writer_key]["from"])
    out["operator"] = scene.endpoints[writer_key]["from"]
    if op is None:
        ob.insufficient.append(u"%s: scale writer has no readable source operator" % path)
        return out
    out["operator_attributes"] = dict((k, ob.require(path + u"/operator/" + k, value(op, k)))
                                      for k in ("expr", "lo", "hi", "value", "result"))
    inputs = []
    for ik in scene.writers(op_key):
        view = scene.channel_view(ik)
        src = scene_element(scene, scene.endpoints[ik]["from"])
        view["source_attributes"] = dict((k, ob.require(path + u"/input/" + k, value(src, k)))
                                         for k in ("value", "defaultValue")) if src is not None else None
        inputs.append(view)
    out["inputs"] = inputs
    return out


def group_membership(ob, path, root):
    """Group membership over the control-group tree, read strictly: [{"group": {...}, "control": {...}}]."""
    pairs, seen, pending = [], set(), [(root, path)]
    while pending:
        group, gpath = pending.pop()
        grec = ident(group)
        if grec["s"] != u"present":
            ob.require(gpath, grec)
            continue
        k = key_of(grec)
        if k in seen:
            continue
        seen.add(k)
        crec, controls = read_list(group, "controls")
        ob.require(gpath + u"/controls", crec)
        for c in controls or []:
            r = ident(c)
            ob.require_present(gpath + u"/controls/<member>", r)
            if r["s"] == u"present":
                pairs.append({"group": {"id": grec["v"]["id"], "name": grec["v"]["name"]},
                              "control": {"id": r["v"]["id"], "name": r["v"]["name"]}})
        kids_rec, kids = read_list(group, "children")
        ob.require(gpath + u"/children", kids_rec)
        for j, kid in enumerate(kids or []):
            pending.append((kid, gpath + u"/children/%d" % j))
    return sorted(pairs, key=lambda p: (p["group"]["name"], p["control"]["name"], p["group"]["id"],
                                        p["control"]["id"]))


def checksum_of(gm):
    ok, hdr = strict_call(gm, "GetStudioHdr")
    if not ok:
        return unreadable(hdr)
    try:
        c = hdr.checksum
        if isinstance(c, bool) or not isinstance(c, INTEGER_TYPES):
            return unreadable(u"checksum %r" % (c,))
        return present(int(c))
    except Exception as exc:
        return unreadable(exc)


def animset_record(ob, path, scene, animset, config):
    rec = {"identity": {"animset": ob.require_present(path + u"/animset", remember(animset))}}
    gm_rec, gm = element_ref(animset, "gameModel")
    rec["identity"]["game_model"] = ob.require_present(path + u"/gameModel", gm_rec)
    rec["identity"]["model"] = ob.require_present(path + u"/model", value(gm, "modelName") if gm is not None
                                                  else unreadable(u"no game model"))
    rec["identity"]["checksum"] = ob.require_present(path + u"/checksum", checksum_of(gm) if gm is not None
                                                     else unreadable(u"no game model"))
    if gm is not None:
        remember(gm)
    c_rec, controls = read_list(animset, "controls")
    ob.require(path + u"/controls", c_rec)
    o_rec, operators = read_list(animset, "operators")
    ob.require(path + u"/operators", o_rec)
    rec["controls"] = sorted([r["v"] for r in (remember(c) for c in controls or []) if r["s"] == u"present"],
                             key=lambda v: (v["name"], v["id"]))
    rec["operators"] = sorted([r["v"] for r in (remember(o) for o in operators or []) if r["s"] == u"present"],
                              key=lambda v: (v["name"], v["id"]))
    if len(rec["controls"]) != len(controls or []) or len(rec["operators"]) != len(operators or []):
        ob.insufficient.append(u"%s: a control or operator identity is unreadable" % path)
    root_rec, root = element_ref(animset, "rootControlGroup")
    ob.require(path + u"/rootControlGroup", root_rec)
    rec["control_groups"] = group_membership(ob, path + u"/rootControlGroup", root) if root is not None else []
    named = by_name(ob, path + u"/controls", controls or [])
    rec["flex"], rec["nonbody"] = {}, {}
    for kind, literals in (("flex", config.get("body") or []), ("nonbody", config.get("nonbody") or [])):
        for lit in literals:
            hits = named.get(lit, [])
            if len(hits) != 1:
                rec[kind][lit] = {"unavailable": u"control hits %d" % len(hits)}
                ob.insufficient.append(u"%s/%s/%s: expected exactly one control, found %d" % (path, kind, lit,
                                                                                              len(hits)))
                continue
            rec[kind][lit] = control_record(ob, u"%s/%s/%s" % (path, kind, lit), scene, hits[0])
    rec["transform_controls"] = {}
    wanted = config.get("transform_controls")
    for c in controls or []:
        r = ident(c)
        if r["s"] != u"present" or r["v"]["type"] != u"DmeTransformControl":
            continue
        if wanted not in (None, u"all", "all") and r["v"]["name"] not in wanted:
            continue
        rec["transform_controls"][r["v"]["name"]] = transform_control_record(
            ob, u"%s/transform_controls/%s" % (path, r["v"]["name"]), scene, c)
    rec["bones"] = bones_record(ob, path, scene, gm) if gm is not None else []
    rec["graphs"] = []
    for bone in rec["bones"]:
        bkey = key_of(bone["transform"])
        for wk in scene.writers(bkey, "scale"):
            rec["graphs"].append(graph_record(ob, u"%s/graphs/%s" % (path, bone["name"]), scene, bone, wk))
    return rec


def undo_record(dm):
    out = {}
    for k, m, kind in (("enabled", "IsUndoEnabled", "bool"), ("can_undo", "CanUndo", "bool"),
                       ("can_redo", "CanRedo", "bool"), ("undo_desc", "GetUndoDesc", "text"),
                       ("redo_desc", "GetRedoDesc", "text"), ("item_count", "GetUndoItemCount", "int")):
        ok, v = strict_call(dm, m)
        if not ok:
            out[k] = unreadable(v)
        elif kind == "bool":
            out[k] = present(v) if type(v) is bool else unreadable(u"%s returned %r" % (m, v))
        elif kind == "text":
            try:
                out[k] = present(text(v)) if isinstance(v, (bytes, text_type)) else unreadable(u"%r" % (v,))
            except Exception as exc:
                out[k] = unreadable(exc)
        else:
            out[k] = present(int(v)) if isinstance(v, INTEGER_TYPES) and not isinstance(v, bool) else \
                unreadable(u"%s returned %r" % (m, v))
    return out


def context_record(ob, label, sfmApp, vs, config):
    out = {}
    ok, has = strict_call(sfmApp, "HasDocument")
    # Native SFM returns a non-zero integer (not a Python bool) while a document is open (G3-a, 2026-10-30:
    # HasDocument() == 103071744 with the scene open). Production CPM tests this call by truthiness.
    document_open = has is True or (isinstance(has, INTEGER_TYPES) and not isinstance(has, bool) and has != 0)
    if not ok or not document_open:
        raise Insufficient(u"No document open (%r)" % (has,))
    ok, doc = strict_call(sfmApp, "GetDocumentRoot")
    out["document_root"] = ob.require_present(label + u"/document_root", ident(doc) if ok else unreadable(doc))
    ok_f, fid = strict_call(doc, "GetFileId") if ok else (False, doc)
    out["file_id"] = ob.require_present(label + u"/file_id", present(int(fid)) if ok_f and
                                        isinstance(fid, INTEGER_TYPES) and not isinstance(fid, bool)
                                        else unreadable(fid))
    ok_p, p = strict_call(vs.g_pDataModel, "GetFileName", fid) if ok_f else (False, fid)
    try:
        out["document_path"] = ob.require_present(label + u"/document_path", present(text(p)) if ok_p
                                                  else unreadable(p))
    except Exception as exc:
        out["document_path"] = ob.require_present(label + u"/document_path", unreadable(exc))
    ok, shot = strict_call(sfmApp, "GetShotAtCurrentTime")
    out["shot"] = ob.require_present(label + u"/shot", ident(shot) if ok else unreadable(shot))
    ok, head = strict_call(sfmApp, "GetHeadTimeInSeconds")
    out["head_seconds"] = ob.require_present(label + u"/head_seconds", present(float(head)) if ok and finite(head)
                                             else unreadable(head))
    return out, (shot if ok else None)


def integrity_record(ob, config):
    out = {"protected": {}, "instruments": {}}
    for label, row in sorted((config.get("protected") or {}).items()):
        try:
            actual = sha256_file(row["path"])
            rec = present({"expected": row["sha256"], "actual": actual, "match": actual == row["sha256"]})
        except Exception as exc:
            rec = unreadable(exc)
        out["protected"][label] = ob.require_present(u"integrity/protected/" + label, rec)
        if rec["s"] == u"present" and not rec["v"]["match"]:
            ob.insufficient.append(u"integrity/protected/%s: hash changed" % label)
    for label, path in sorted((config.get("instrument_files") or {}).items()):
        try:
            out["instruments"][label] = present(sha256_file(path))
        except Exception as exc:
            out["instruments"][label] = ob.require(u"integrity/instruments/" + label, unreadable(exc))
    cpm = config.get("cpm") or {}
    if not cpm.get("path") or cpm.get("sha256") != ACCEPTED_W1_SHA256:
        out["cpm"] = ob.require(u"integrity/cpm", unreadable(u"no candidate CPM pinned to the accepted W1 hash"))
        return out
    try:
        actual = sha256_file(cpm["path"])
        out["cpm"] = present({"expected": cpm["sha256"], "actual": actual, "match": actual == ACCEPTED_W1_SHA256})
        if actual != ACCEPTED_W1_SHA256:
            ob.insufficient.append(u"integrity/cpm: installed CPM %s is not the accepted W1 candidate" % actual[:16])
    except Exception as exc:
        out["cpm"] = ob.require(u"integrity/cpm", unreadable(exc))
    return out


def watch_record(vs, watch):
    """Post-abort: is each element the injector saw created still resolvable through the data model?"""
    out = []
    for row in watch or []:
        ok, el = strict_call(vs.g_pDataModel, "GetElement", row["handle"])
        if not ok:
            out.append({"watched": row, "now": unreadable(el)})
        elif el is None:
            out.append({"watched": row, "now": {"s": u"gone"}})
        else:
            out.append({"watched": row, "now": ident(el)})
    return out


def observe(sfmApp, vs, config, label=u"observation", watch=None, config_name=None):
    """One complete read-only observation. Never raises for unreadable evidence: it is recorded and listed in
    record["insufficient"]. Raises Insufficient only when there is no document or the shot is wrong."""
    _ELEMENTS.clear()
    ob = Observation()
    record = {"format": FORMAT, "core": CORE_VERSION, "label": text(label), "python": text(sys.version),
              "config_name": text(config_name) if config_name else None,
              "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()}
    # The declared scope: the comparator requires exactly these records (a missing one is never "unchanged").
    record["declared"] = {"shot": config["shot"], "target_animset": config["target_animset"],
                          "peers": list(config.get("peers") or []), "body": list(config.get("body") or []),
                          "nonbody": list(config.get("nonbody") or [])}
    record["context_begin"], shot = context_record(ob, u"context_begin", sfmApp, vs, config)
    shot_name = (record["context_begin"]["shot"].get("v") or {}).get("name")
    if shot is None or shot_name != config["shot"]:
        raise Insufficient(u"The playhead is not in %s (current shot %r)" % (config["shot"], shot_name))
    record["integrity"] = integrity_record(ob, config)
    scene = Scene(ob, shot)
    record["channels_clips"] = scene.clips
    sets_rec, sets = read_list(shot, "animationSets")
    ob.require(u"shot/animationSets", sets_rec)
    named = by_name(ob, u"shot/animationSets", sets or [])
    target = named.get(config["target_animset"], [])
    if len(target) != 1:
        ob.insufficient.append(u"target animation set %r: found %d" % (config["target_animset"], len(target)))
        record["target"] = None
    else:
        record["target"] = animset_record(ob, u"target", scene, target[0], config)
    record["peers"] = {}
    for peer in config.get("peers") or []:
        hits = named.get(peer, [])
        if len(hits) != 1:
            ob.insufficient.append(u"peer animation set %r: found %d" % (peer, len(hits)))
            record["peers"][peer] = None
            continue
        record["peers"][peer] = animset_record(ob, u"peers/" + peer, scene, hits[0], config)
        tk = key_of((record["target"] or {}).get("identity", {}).get("animset"))
        if tk is not None and key_of(record["peers"][peer]["identity"]["animset"]) == tk:
            ob.insufficient.append(u"peer %r is the target instance" % peer)
        if record["target"] is not None:
            for k in ("model", "checksum"):
                if record["peers"][peer]["identity"][k] != record["target"]["identity"][k]:
                    ob.insufficient.append(u"peer %r is not a same-model instance (%s differs)" % (peer, k))
    record["unresolved_channels"] = scene.unresolved
    if scene.unresolved:
        ob.insufficient.append(u"%d channel(s) with unreadable endpoints: possible unrecorded writers" %
                               len(scene.unresolved))
    record["undo"] = undo_record(vs.g_pDataModel)
    for k, r in record["undo"].items():
        if k != "item_count":
            ob.require(u"undo/" + k, r)
    record["watch"] = watch_record(vs, watch)
    for i, row in enumerate(record["watch"]):
        ob.require(u"watch/%d" % i, row["now"])
    record["context_end"], _ = context_record(ob, u"context_end", sfmApp, vs, config)
    if record["context_end"] != record["context_begin"]:
        ob.insufficient.append(u"context changed during the observation")
    record["insufficient"] = ob.insufficient
    record["complete"] = not ob.insufficient
    return record


def _stable(value):
    """A comparison form without transient fields."""
    if isinstance(value, dict):
        return dict((k, _stable(v)) for k, v in value.items() if k not in ("current_ticks_transient", "label"))
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def created_elements(before, during):
    """Independent record of what an operation created, from two complete observations of the same instance:
    new controls, operators and channels (with endpoints), new animation-set, channel-container and control-group
    memberships, scale attributes created (with physical value) and any nonselected peer change."""
    if not (before.get("complete") and during.get("target") and before.get("target")):
        raise Insufficient(u"created-element evidence needs a complete baseline and an in-transaction target record")
    tb, td = before["target"], during["target"]
    created, memberships, scale_created, seen = [], [], [], set()

    def add(row, role):
        if row["id"] in seen:
            return
        seen.add(row["id"])
        created.append({"handle": row["handle"], "id": row["id"], "type": row["type"], "name": row["name"],
                        "role": role})

    for listing, role in (("controls", u"control"), ("operators", u"operator")):
        known = set(r["id"] for r in tb[listing])
        for r in td[listing]:
            if r["id"] not in known:
                add(r, role)
                memberships.append([u"animset." + listing, r["id"], r["name"]])
    known = set(ch["id"] for clip in before["channels_clips"] for ch in clip["channels"])
    views = {}
    for g in td["graphs"]:
        for view in [g["output"]] + list(g["inputs"]):
            if view["channel"].get("s") == u"present":
                views[view["channel"]["v"]["id"]] = view
    for clip in during["channels_clips"]:
        cname = (clip["clip"].get("v") or {}).get("name")
        for ch in clip["channels"]:
            if ch["id"] not in known:
                add(ch, u"channel")
                memberships.append([u"channels_clip:%s" % cname, ch["id"], ch["name"]])
                view = views.get(ch["id"])
                if view is not None:
                    created[-1]["endpoints"] = dict((k, view[k]) for k in ("from", "from_attribute", "to",
                                                                           "to_attribute", "mode"))
                    log = view["log"].get("v") if view["log"].get("s") == u"present" else None
                    if log is not None and log["log"].get("s") == u"present":
                        add(log["log"]["v"], u"log")
                        for layer in log.get("layers") or []:
                            if isinstance(layer, dict) and (layer.get("layer") or {}).get("s") == u"present":
                                add(layer["layer"]["v"], u"layer")
    pairs = set((p["group"]["id"], p["control"]["id"]) for p in tb["control_groups"])
    for p in td["control_groups"]:
        if (p["group"]["id"], p["control"]["id"]) not in pairs:
            memberships.append([u"control_group:%s" % p["group"]["name"], p["control"]["id"], p["control"]["name"]])
    before_bones = dict((b["index"], b) for b in tb["bones"])
    for b in td["bones"]:
        was = before_bones.get(b["index"])
        if was is not None and was["scale"].get("s") == u"absent" and b["scale"].get("s") == u"present":
            scale_created.append({"bone": b["name"], "index": b["index"], "transform": b["transform"],
                                  "physical": b["scale"]["v"]})
    peer_changes = [p for p in sorted(before.get("peers") or {})
                    if json.dumps(_stable(before["peers"][p]), sort_keys=True) !=
                    json.dumps(_stable((during.get("peers") or {}).get(p)), sort_keys=True)]
    return {"created": created, "memberships_added": memberships, "scale_attributes_created": scale_created,
            "peer_changes": peer_changes}


def dumps(record):
    return json.dumps(record, indent=1, sort_keys=True, ensure_ascii=True, allow_nan=False)
