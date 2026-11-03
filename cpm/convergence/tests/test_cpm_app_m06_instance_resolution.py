# -*- coding: utf-8 -*-
"""M-06 W1 -- real-path integration qualification of selected-instance resolution in the CPM application source
(cpm/app/SFM_Character_Preset_Manager.py).

Design authority: Astra's M-06/M-05 Integration Correction Design (2026-10-29), W1 "Required integration tests".

Technique: the production functions are extracted verbatim by name, as in the M-05 / M-06 suites, but this layer
does NOT replace the paths under test. Real here: production model enumeration and instance resolution, the
selection token and operation context (prod_selection_rows, prod_resolve_instance, prod_context_token,
prod_context_token_matches, prod_validate_context_token, ProdWindow.operation_begin / select_model / current),
live flex binding acquisition (p01_all_supported_flex_bindings, flex_binding, prod_live_bindings_for_cached_scope,
prod_scope_matches_identity), bone-scale acquisition (prod_bs_find_model_row, prod_bs_index_snapshot and its
traversals: animation-set controls, control groups, channels clip), Body capture, preset validation, Save, Update,
Apply planning, postcommit, deferred and abort verification, and preset serialization, rereading and replacement
on a disposable filesystem (p02_safe_write_json, p02_read_json, prod_unique_path, prod_discover,
prod_ensure_character).

Simulated (explicit boundaries): the native DME graph and its evaluation (a fake scene with two same-model
instances), native Undo transactions, Qt scheduling, the semantic provider/master file (a conditional authority
fixture that refuses a stale generation, identity or kind -- never an unconditional "authorized" result), the
library root folder, the studio-header flex-controller index (p03_native_index), and native scale-graph construction (prod_bs_create_graph builds the fake graph; actual
construction is W2 native evidence).

Usage: --phase=run (Python 2.7.5 and Python 3.10). --phase=counterexample reports which starting-candidate defects
an application source reproduces; CPM_TEST_APP_PATH selects that source (used to show that the starting candidate
fails the duplicate-instance, deletion-retarget and duplicate-name clip cases). Offline only; nothing here demonstrates
native SFM behaviour.
"""
from __future__ import print_function

import json
import os
import re
import shutil
import sys
import tempfile
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_m05_static_scale as m05  # noqa: E402
import test_cpm_app_m06_static_play_flex as m06  # noqa: E402  (installs the native-faithful attribute reader)

PY2 = sys.version_info[0] == 2
try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

RESULTS = []
MODEL = u"models/synthetic/zz_twin_rig.mdl"
CHECKSUM = 4242
STATIC = "STATIC_PLAY_ONE_KEY_ZERO"


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def close(a, b, tol=1.0e-5):
    return abs(float(a) - float(b)) <= tol


def raises(fn):
    try:
        fn()
    except Exception as exc:
        return exc
    return None


# ---------------------------------------------------------------------------
# Fake DME scene: one shot, several model-backed animation sets
# ---------------------------------------------------------------------------

class UniqueId(object):
    """Fake native UniqueId_t: an opaque value with a text form; equality only through vs.tier1."""

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class Tier1(object):
    @staticmethod
    def IsUniqueIdValid(uid):
        return isinstance(uid, UniqueId) and bool(uid.text)

    @staticmethod
    def IsUniqueIdEqual(a, b):
        return isinstance(a, UniqueId) and isinstance(b, UniqueId) and a.text == b.text


def _fake_get_id(self):
    # Stable per element for its lifetime; a re-created element (reload, replacement) gets a new ID.
    uid = self.__dict__.get("_uid")
    if uid is None:
        uid = self.__dict__["_uid"] = UniqueId(u"%08x-w1-%d" % (self._handle * 2654435761 % (1 << 32), self._handle))
    return uid


m05.FakeElement.GetId = _fake_get_id  # this suite's process only; the historical suites are unaffected


class DataModel(m05.FakeDataModel):
    """FakeDataModel plus IDataModel's handle lookups over the scene's live elements."""

    def GetElement(self, handle):
        for element in self.scene.elements:
            if element._handle == handle:
                return element
        return None

    def GetElementId(self, handle):
        # An independent wrapper of the registered ID (not the element's own object).
        element = self.GetElement(handle)
        return UniqueId(element.GetId().text) if element is not None else UniqueId(u"")


class BrokenAttr(object):
    """An attribute that exists but whose value cannot be read."""

    def __init__(self, owner, attr_name):
        self.owner = owner
        self.name = attr_name

    def GetValue(self):
        raise RuntimeError("synthetic unreadable attribute")

    def GetName(self):
        return self.name


class Live(m05.FakeElement):
    """A fake element whose authored attributes are also reachable as Python attributes, as the vs wrapper allows
    (animset.gameModel, shot.animationSets, animset.controls)."""

    def __getattr__(self, attr_name):
        if attr_name.startswith("_") or attr_name in ("this",):
            raise AttributeError(attr_name)
        attr = self.__dict__.get("_attrs", {}).get(attr_name)
        if attr is None:
            raise AttributeError(attr_name)
        return attr.GetValue()


class Hdr(object):
    def __init__(self, value):
        self.checksum = value


class GameModel(Live):
    def __init__(self, element_name, model, check):
        Live.__init__(self, u"DmeGameModel", element_name, modelName=model, bones=[], globalFlexControllers=[])
        self.check = check

    def GetStudioHdr(self):
        return Hdr(self.check)


class Shot(Live):
    def FindTrackGroup(self, group_name):
        for group in self.raw("trackGroups"):
            if group._name == group_name:
                return group
        return None

    def GetFileId(self):
        return MultiScene.current_scene().file_id


class TrackGroup(Live):
    def FindTrack(self, track_name):
        for track in self.raw("tracks"):
            if track._name == track_name:
                return track
        return None


class Track(Live):
    def FindNamedClip(self, clip_name):
        # Native semantics: the FIRST child clip with that name.
        for clip in self.raw("children"):
            if clip._name == clip_name:
                return clip
        return None


class Instance(object):
    def __init__(self, scene, set_name, model=MODEL, check=CHECKSUM):
        self.name = set_name
        self.controls = []
        self.channels = []
        self.operators = []
        self.flex_channels = []
        self.gm = GameModel(set_name + u"_model", model, check)
        self.group = Live(u"DmeControlGroup", u"Body", controls=[], children=[])
        self.root = Live(u"DmeControlGroup", u"root", controls=[], children=[self.group])
        self.animset = Live(u"DmeAnimationSet", set_name, gameModel=self.gm, controls=self.controls,
                            operators=self.operators, rootControlGroup=self.root)
        self.clip = Live(u"DmeChannelsClip", set_name, channels=[])
        self.clip_channels = None  # test override of the clip's channel membership
        self.clip_channels_unreadable = False  # the clip's channels attribute exists but cannot be read

    def sync(self):
        if self.animset is not None:
            self.animset.put("controls", self.controls)
            self.animset.put("operators", self.operators)
        if self.clip is not None:
            if self.clip_channels is not None:
                self.clip.put("channels", list(self.clip_channels))
            else:
                self.clip.put("channels", list(self.flex_channels) + list(self.channels))
            if self.clip_channels_unreadable:
                self.clip._attrs["channels"] = BrokenAttr(self.clip, "channels")
        bones = []
        for control in self.controls:
            if isinstance(control, m05.FakeTransformControl):
                bones.append(control.transform)
        self.gm.put("bones", bones)


class MultiScene(m06.FlexScene):
    """The M-06 fake scene generalized to several animation sets in one shot. Building helpers write into the
    instance selected by use(); evaluation, Undo snapshots and the movie cover every instance."""

    def __init__(self):
        m06.FlexScene.__init__(self)
        self.instances = []
        self.file_id = 7
        self.document = Live(u"DmElement", u"session")
        self.alt_shot = None
        self.on_shot = True
        self.dm = DataModel(self)
        self._group = TrackGroup(u"DmeTrackGroup", u"channelTrackGroup", tracks=[])
        self._track = Track(u"DmeTrack", u"animSetEditorChannels", children=[])
        self._group.put("tracks", [self._track])
        self.shot = Shot(u"DmeFilmClip", u"shot01", trackGroups=[self._group], animationSets=[], operators=[])
        self._film = Live(u"DmeTrack", u"Film", children=[self.shot])
        self._sub = Live(u"DmeTrackGroup", u"subClipTrackGroup", tracks=[self._film])
        self._movie = Live(u"DmeFilmClip", u"movie", subClipTrackGroup=self._sub, trackGroups=[])
        self.order_reversed = False

    @staticmethod
    def current_scene():
        return m05.Scene.current

    def add_instance(self, set_name, **kw):
        inst = Instance(self, set_name, **kw)
        self.instances.append(inst)
        return inst

    def use(self, inst):
        self.animset = inst.animset
        self.controls = inst.controls
        self.channels = inst.channels
        self.operators = inst.operators
        self.flex_channels = inst.flex_channels
        self.group = inst.group
        self.flex_model = inst.gm

    def sync(self):
        for inst in self.instances:
            inst.sync()
        sets = [inst.animset for inst in self.instances if inst.animset is not None]
        if self.order_reversed:
            sets = list(reversed(sets))
        self.shot.put("animationSets", sets)
        clips = [inst.clip for inst in self.instances if inst.clip is not None]
        if self.order_reversed:
            clips = list(reversed(clips))
        self._track.put("children", clips)
        if getattr(self, "children_unreadable", False):
            self._track._attrs["children"] = BrokenAttr(self._track, "children")

    def movie(self):
        self.sync()
        return self._movie

    def current_shot(self):
        self.sync()
        if not self.on_shot:
            return None
        return self.alt_shot if self.alt_shot is not None else self.shot

    # Evaluation over every instance.
    def refresh(self):
        for inst in self.instances:
            self.use_lists(inst)
            m05.Scene.refresh(self)

    def event_turn(self):
        for inst in self.instances:
            self.use_lists(inst)
            m05.Scene.event_turn(self)

    def use_lists(self, inst):
        self.operators = inst.operators
        self.channels = inst.channels

    # Undo snapshots cover every instance's list membership.
    def capture(self):
        snap = m05.Scene.capture(self)
        snap["present"] = dict((e._handle, sorted(e._attrs.keys())) for e in self.elements)
        snap["lists"] = dict((id(inst), {"channels": list(inst.channels), "controls": list(inst.controls),
                                         "operators": list(inst.operators), "group": list(inst.group.raw("controls")),
                                         "flex": list(inst.flex_channels)}) for inst in self.instances)
        snap["elements"] = list(self.elements)
        return snap

    def restore(self, snap):
        for e in self.elements:
            if e._handle in snap["present"]:
                for k in list(e._attrs.keys()):
                    if k not in snap["present"][e._handle]:
                        del e._attrs[k]
                for k in snap["present"][e._handle]:
                    value = snap["attrs"].get((e._handle, k))
                    if k not in e._attrs:
                        e._attrs[k] = m05.FakeAttr(e, k, value)
        m05.Scene.restore(self, snap)
        for inst in self.instances:
            lists = snap["lists"].get(id(inst))
            if lists is None:
                continue
            inst.channels[:] = lists["channels"]
            inst.controls[:] = lists["controls"]
            inst.operators[:] = lists["operators"]
            inst.flex_channels[:] = lists["flex"]
            inst.group.put("controls", lists["group"])
        self.elements[:] = snap["elements"]
        self.sync()

    # Per-instance authored-state digest (peer preservation).
    def instance_digest(self, inst):
        handles = set()
        for control in inst.controls:
            handles.add(control._handle)
            for key in ("channel", "leftvaluechannel", "rightvaluechannel"):
                if key in control._attrs and control.raw(key) is not None:
                    ch = control.raw(key)
                    handles.add(ch._handle)
                    handles.add(ch.log._handle)
                    for layer in ch.log.layers:
                        handles.add(layer._handle)
                    handles.add(ch.raw("toElement")._handle)
            if isinstance(control, m05.FakeTransformControl):
                handles.add(control.transform._handle)
        for ch in inst.channels:
            handles.add(ch._handle)
            handles.add(ch.log._handle)
            for layer in ch.log.layers:
                handles.add(layer._handle)
        for op in inst.operators:
            handles.add(op._handle)
        rows = []
        for e in self.elements:
            if e._handle in handles:
                attrs = sorted((k, repr(a.value)) for k, a in e._attrs.items() if not k.startswith("#"))
                keys = repr(e.keys) if isinstance(e, m05.FakeLayer) else None
                rows.append((e._type, e._name, attrs, keys))
        rows.sort()
        membership = (sorted(c._name for c in inst.controls), sorted(c._name for c in inst.channels),
                      sorted(o._name for o in inst.operators), sorted(c._name for c in inst.group.raw("controls")))
        return json.dumps([rows, membership], sort_keys=True, default=repr)


def twin_scene(peer_name=u"zz_peer", target_name=u"zz_target", target_first=False, same_name=False, plain=False):
    """Two instances of one model/checksum with different flex and bone-scale values. The target's Body flex
    'zz_smile' is an imported static-play flex (stored 0.0, key/effective 0.30); the peer's is 0.70. The target's
    head scale is 0.113 (physical 1.13); the peer's 0.2 (2.0). plain=True authors ordinary flexes (stored value equals
    the key) for paths that predate static-play support (Clothing Fit capture)."""
    m06.scene()  # resets the shared logs, timers, app state and the store; its own scene is discarded
    s = MultiScene()
    m05.Scene.current = s
    names = [target_name, peer_name] if target_first else [peer_name, target_name]
    if same_name:
        names = [target_name, target_name]
    built = {}
    for set_name, role in zip(names, ([u"target", u"peer"] if target_first or same_name else [u"peer", u"target"])):
        inst = s.add_instance(set_name)
        s.use(inst)
        s.bone(0, u"zz_root")
        head = s.bone(4, u"zz_crest")
        if role == u"target":
            s.scale_graph(head, u"zz_crest", 0.113, output_mode=3)
            s.mono(u"zz_smile", 0.30, stored=0.30 if plain else 0.0)
            s.mono(u"zz_brow", 0.10)
        else:
            s.scale_graph(head, u"zz_crest", 0.2, output_mode=3)
            s.mono(u"zz_smile", 0.70, stored=0.70 if plain else 0.0)
            s.mono(u"zz_brow", 0.55)
        inst.role = role
        built[role] = inst
    s.target, s.peer = built[u"target"], built[u"peer"]
    s.use(s.target)
    s.sync()
    return s


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------

REAL_EXTRACT = [
    # identity and resolution
    "PROD_INSTANCE_TOKEN_KIND", "PROD_INSTANCE_SESSION", "PROD_INSTANCE_RESELECT_COPY", "PROD_INSTANCE_CHANNEL_ATTRS", "prod_strict_identity",
    "prod_instance_document", "prod_instance_rows", "prod_bone_layout_sha256", "prod_instance_model",
    "prod_selection_token", "prod_instance_token", "prod_instance_kw", "prod_resolve_instance",
    "prod_selection_rows", "prod_instance_channels_clip", "prod_instance_strict_text",
    "prod_instance_strict_members", "prod_instance_pair_check", "prod_context_token",
    "prod_context_token_matches", "prod_validate_context_token", "prod_resolve", "prod_resolve_from_rows",
    "prod_identity_from_row", "prod_bs_find_model_row", "p03_model_animsets", "p01_model_backed_animsets",
    "get_game_model", "model_asset", "checksum", "prod_json_digest", "prod_model_candidates",
    # scene traversal under bone-scale acquisition
    "get_channels_clip", "r26_animset_controls", "r26_animset_operators", "r26_clip_channels",
    "prod_bs_animset_controls", "group_inventory", "root_group", "child_groups", "subtree_controls", "MAX_GROUPS",
    "MAX_CONTROLS",
    # live flex binding acquisition
    "p01_all_supported_flex_bindings", "prod_live_bindings_for_cached_scope", "prod_live_binding_signatures",
    "prod_binding_descriptor", "prod_scope_matches_identity", "prod_cpm_context_matches_identity",
    "prod_override_revision", "prod_load_character", "PROD_SEMANTIC_POLICY",
    # preset library on a disposable filesystem
    "prod_paths", "prod_label", "g09a_safe_label", "g09a_normalize_model_path", "prod_key", "prod_norm", "prod_unique_path", "prod_ensure_character",
    "p02_safe_write_json", "p02_read_json", "prod_validate_preset", "prod_discover",
    "prod_assert_unique_preset_name_items", "prod_preset_name_key", "prod_update_preset",
    "prod_selected_record_revision", "prod_reread_selected_record",
    # Clothing Fit source (selected instance)
    "prod_body_source", "prod_body_source_live_from_baseline",
]

WINDOW_EXTRACT = ["select_model", "current", "refresh_animset_display_metadata", "save_kind"]
CLOSURE = []


class Library(object):
    root = None


class Authority(object):
    """Conditional fixture for the semantic provider / master file: one current generation; a scope captured
    under another generation, a mismatched identity or an unknown kind refuses."""
    generation = [1]
    sha = u"f" * 64
    calls = []

    @classmethod
    def authorize(cls, identity, scope, kind, label):
        cls.calls.append(_TEXT(label))
        auth = (scope or {}).get("authority") or {}
        current = (scope or {}).get("identity") or {}
        if int(auth.get("provider_generation") or 0) != cls.generation[0]:
            raise m05._OperationAuthorityError("stale semantic generation (fixture)")
        if _TEXT(current.get("model")).lower() != _TEXT(identity.get("model")).lower() or \
                int(current.get("checksum")) != int(identity.get("checksum")):
            raise m05._OperationAuthorityError("scope identity mismatch (fixture)")
        key = {u"body": "body", u"expression": "expression"}.get(_TEXT(kind))
        if key is None:
            raise m05._OperationAuthorityError("unknown kind (fixture)")
        return {"operation": _TEXT(label), "identity": dict(identity), "master_sha256": cls.sha,
                "provider_capture": {"provider_generation": cls.generation[0]},
                "membership": {"kind": _TEXT(kind), "descriptors": dict(scope[key])},
                "persistence": {"last_validated_provider": {"provider": u"fixture"}}}


def build_namespace(app):
    ns, methods = m06.build_namespace(app)
    import base64, binascii, ctypes, datetime, errno, hashlib, time, uuid
    ns.update({"hashlib": hashlib, "base64": base64, "binascii": binascii, "ctypes": ctypes, "datetime": datetime,
               "errno": errno, "time": time, "shutil": shutil, "uuid": uuid, "tempfile": tempfile})
    missing = [n for n in REAL_EXTRACT if n not in app.top]
    check("extraction.every_integration_name_present", not missing, missing)
    for name in REAL_EXTRACT:
        if name not in missing:
            route._run_source(app.top_text(name), "app:%s" % name, ns)
    for name in WINDOW_EXTRACT:
        route._run_source(app.method_text("ProdWindow", name), "ProdWindow.%s" % name, ns, methods)
    # Dependency closure: production helpers referenced by the extracted code that the M-05/M-06 harness does not
    # already define are extracted verbatim too. Names the harness defines (its simulated boundaries) are never
    # overwritten, and the explicit boundaries below are excluded.
    boundaries = set(["prod_library_root", "prod_cpm_authorize_operation", "prod_bs_create_graph", "sfmApp", "vs",
                      "ProdWindow", "prod_current_provider_descriptor", "prod_cpm_open_adapter", "p03_native_index"])
    # Studio-header boundary (native flex-controller index): records which game model it was asked to index.
    ns["p03_native_index"] = lambda gm: {"fixture_native_index_of": gm._handle}
    # Semantic provider boundary: the current generation is the conditional fixture's.
    ns["prod_current_provider_descriptor"] = lambda: {"provider_generation": Authority.generation[0],
                                                      "source_sha256": Authority.sha}
    closure = []
    seen = set()

    def deps(text):
        return [i for i in sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text)))
                if i not in seen and i not in boundaries and i not in ns and i in app.top
                and (app.top[i][2].__class__.__name__ != "ClassDef" or i.startswith("ProdCpm"))]

    def ensure(ident):
        # Post-order: a module-level constant's own dependencies are defined before it executes.
        seen.add(ident)
        source = app.top_text(ident)
        for dep in deps(source):
            if dep not in seen:
                ensure(dep)
        route._run_source(source, "app:%s" % ident, ns)
        closure.append(ident)

    roots = [app.method_text("ProdWindow", m) for m in WINDOW_EXTRACT]
    roots += [app.top_text(n) for n in REAL_EXTRACT if n in app.top]
    for text in roots:
        for dep in deps(text):
            if dep not in seen:
                ensure(dep)
    print("dependency closure (%d): %s" % (len(closure), ", ".join(sorted(closure))))
    CLOSURE[:] = sorted(closure)

    class _Sfm(m05._SfmApp):
        @staticmethod
        def HasDocument():
            return m05.Scene.current.document is not None

        @staticmethod
        def GetDocumentRoot():
            return m05.Scene.current.document

        @staticmethod
        def GetShotAtCurrentTime():
            return m05.Scene.current.current_shot()

        @staticmethod
        def GetMovie():
            return m05.Scene.current.movie()
    ns["sfmApp"] = _Sfm

    class _VsW1(m05._Vs):
        tier1 = Tier1
    ns["vs"] = _VsW1()
    # Boundaries: library root, provider capture, authority, native graph construction.
    ns["prod_library_root"] = lambda: Library.root
    ns["prod_cpm_authorize_operation"] = Authority.authorize

    def create_graph(fixture, physical):
        scene = m05.Scene.current
        inst = [i for i in scene.instances if i.animset is fixture["animset"]][0]
        scene.created.append((inst.name, fixture["names"]["literal"], physical))
        scene.use(inst)
        graph = scene.scale_graph(fixture["transform"], fixture["bone_row"]["bone_name"], physical / 10.0,
                                  output_mode=1)
        scene.use(scene.target)
        scene.sync()
        return graph
    ns["prod_bs_create_graph"] = create_graph
    # The suite's stubs that hid instance resolution are replaced by the real functions above; make sure.
    for name in ("prod_bs_find_model_row", "prod_context_token", "prod_context_token_matches",
                 "prod_live_bindings_for_cached_scope", "p03_capture_values", "prod_discover", "prod_unique_path",
                 "prod_ensure_character", "p02_safe_write_json", "p02_read_json", "prod_validate_preset",
                 "r26_clip_channels", "r26_animset_controls", "prod_bs_animset_controls", "group_inventory",
                 "get_channels_clip", "prod_reread_selected_record"):
        check("namespace.real.%s" % name, getattr(ns[name], "__code__", None) is not None
              and ns[name].__code__.co_filename.startswith("app:"), ns[name])
    return ns, methods


def make_window(ns, methods):
    Base = m05.make_window_class(methods)

    class Window(Base):
        def __init__(self):
            Base.__init__(self, None)
            self.identity = None
            self.selection_token = None
            self.candidates = []
            self.renders = []
            self.combo = type("Combo", (object,), {"setItemText": lambda s, i, t: None,
                                                   "currentIndex": lambda s: 1})()
            self.init_ui()

        def render(self, identity=None, selection_token=None):
            # UI boundary: the scope/provider build and widget publication. Records the request and publishes
            # identity and token as the production render does on success.
            self.renders.append((dict(identity), selection_token))
            self.identity = dict(identity)
            self.selection_token = selection_token

        def clear_model_selection(self):
            self.identity = None
            self.selection_token = None

        # UI boundaries of the production Save/Apply entry paths.
        prompts = None
        selected_item = None
        body_items = None
        expr_items = None

        def prompt(self, title, default):
            self.prompts.append(_TEXT(title))
            return u"UI Entry Preset"

        def selected(self, kind):
            if self.selected_item is None:
                raise RuntimeError("no preset selected (fixture)")
            return self.selected_item

        def refresh_preset_view(self, kind, preset_id=None):
            pass

    def init_ui(win):
        win.prompts = []
        win.body_items = []
        win.expr_items = []
    Window.init_ui = init_ui
    return Window


def make_scope(ns, identity, token):
    """The cached semantic scope for one selected instance, built from that instance's real live bindings
    (semantic classification itself is the simulated provider)."""
    row = ns["prod_resolve_instance"](token, identity)
    bindings = ns["p01_all_supported_flex_bindings"](row["animset"])
    body = dict((b["literal"], ns["prod_binding_descriptor"](b)) for b in bindings)
    profile = ns["prod_load_character"](identity)
    return {"identity": dict(identity), "live_signature": ns["prod_live_binding_signatures"](bindings),
            "body": body, "expression": {},
            "authority": {"provider_generation": Authority.generation[0], "provider_sha256": Authority.sha,
                          "semantic_policy_revision": ns["PROD_SEMANTIC_POLICY"],
                          "override_revision": ns["prod_override_revision"](profile)},
            "provider_descriptor": {"provider": u"fixture"}}


# ---------------------------------------------------------------------------
# Procedure helpers
# ---------------------------------------------------------------------------

def fresh_library():
    if Library.root and os.path.isdir(Library.root):
        shutil.rmtree(Library.root, ignore_errors=True)
    Library.root = tempfile.mkdtemp(prefix="cpm_w1_lib_")


def select(ns, win, inst):
    """Refresh (real production model list) and select the row of one instance through ProdWindow.select_model."""
    win.candidates, empty = ns["prod_model_candidates"]()
    index = [i for i, row in enumerate(win.candidates)
             if row["selection_token"]["animset_key"][1] == inst.animset._handle]
    assert len(index) == 1, (index, [r["animset_name"] for r in win.candidates])
    win.select_model(index[0] + 1)
    return index[0] + 1


def begin(win, label=u"Save Current Body"):
    win.operation = None
    ok = win.operation_begin(label)
    return win.operation["context"] if ok and win.operation else None


def end(win):
    win.operation = None
    win.busy = False


def body_record(scene, smile, brow, crest):
    rows = []
    for control in scene.target.controls:
        if isinstance(control, m05.FakeTransformControl):
            tname = control.transform._name
            index = int(tname.split()[1])
            bone = tname[tname.index("(") + 1:-1]
            value = crest if bone == u"zz_crest" else 1.0
            state = u"existing-static-control" if bone == u"zz_crest" else u"implicit-neutral"
            rows.append({"bone_index": index, "bone_name": bone, "representation": u"uniform_local_scale_multiplier",
                         "value": value, "capture_state": state})
    rows.sort(key=lambda r: r["bone_index"])
    return {"kind": u"body", "name": u"W1", "preset_id": u"preset-w1", "bone_scales": rows,
            "values": {u"flex.zz_smile": {"representation": u"MONO", "mono": smile},
                       u"flex.zz_brow": {"representation": u"MONO", "mono": brow}}}


def flex_value(inst, literal):
    control = [c for c in inst.controls if c._name == literal][0]
    ch = control.raw("channel")
    return {"stored": control.raw("value"), "key": ch.log.layers[0].keys[0][1], "dest": ch.raw("toElement").raw("flexWeight")}


def crest_scale(inst):
    t = [c for c in inst.controls if isinstance(c, m05.FakeTransformControl) and u"zz_crest" in c.transform._name][0]
    return t.transform.raw("scale")


def run_events(scene):
    for _ in range(4):
        scene.event_turn()
        m05.Timer.run_all()


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_selection(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    rows, empty = ns["prod_model_candidates"]()
    check("S1 production model list: one row per instance, each with its own runtime token",
          len(rows) == 2 and empty is None and len(set(r["selection_token"]["animset_key"] for r in rows)) == 2
          and all(r["model"] == MODEL and r["checksum"] == CHECKSUM for r in rows), rows)
    check("S1 token has no name and no portable-only identity",
          all("animset_name" not in r["selection_token"] for r in rows)
          and all(r["selection_token"]["animset_key"][0] == u"DmeAnimationSet" for r in rows))
    select(ns, win, s.target)
    check("S2 select_model publishes the selected row's token and portable identity",
          win.selection_token is not None and win.selection_token["animset_key"][1] == s.target.animset._handle
          and win.identity == {"model": MODEL, "checksum": CHECKSUM, "animset_name": u"zz_target"},
          (win.identity, win.selection_token))
    s.order_reversed = True
    s.sync()
    ctx = begin(win)
    check("S3 reversed enumeration order: the pinned context still names the selected instance",
          ctx is not None and ctx["instance"]["animset_key"][1] == s.target.animset._handle
          and ns["prod_context_token_matches"](ctx), ctx)
    end(win)
    s.order_reversed = False
    # Stale row at selection: the row's instance was replaced after Refresh.
    win2 = Window()
    win2.candidates, _ = ns["prod_model_candidates"]()
    idx = [i for i, r in enumerate(win2.candidates) if r["animset_name"] == u"zz_target"][0]
    old = s.target.animset
    s.target.animset = Live(u"DmeAnimationSet", u"zz_target", gameModel=s.target.gm, controls=s.target.controls,
                            operators=s.target.operators, rootControlGroup=s.target.root)
    s.sync()
    win2.select_model(idx + 1)
    check("S4 stale row (instance replaced after Refresh) is refused at selection; nothing published",
          win2.identity is None and win2.selection_token is None and win2.renders == []
          and any(level == u"error" for _, level in win2.statuses), win2.statuses)
    s.target.animset = old
    s.sync()
    # A row captured without a token (historical) cannot select.
    win3 = Window()
    win3.candidates = [dict(r, selection_token=None) for r in ns["prod_model_candidates"]()[0]]
    win3.select_model(1)
    check("S5 a row without a runtime token never selects by name", win3.identity is None and win3.renders == [])
    # Operation entry without a token refuses (pre-pin interval).
    win4 = Window()
    win4.identity = {"model": MODEL, "checksum": CHECKSUM, "animset_name": u"zz_target"}
    exc = raises(lambda: win4.operation_begin(u"Save Current Body"))
    check("S6 operation entry without a selection token refuses", exc is not None and win4.operation is None, exc)


def section_resolution(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    token = win.selection_token
    ident = win.identity
    row = ns["prod_bs_find_model_row"](ident, instance_context=token)
    check("R1 pinned bone-scale row is the selected instance, not the first compatible model",
          row["animset"] is s.target.animset and row["instance"] is token)
    exc = raises(lambda: ns["prod_bs_find_model_row"](ident))
    check("R2 context-free historical bone resolution still refuses two same-model instances",
          exc is not None and "resolved uniquely" in str(exc), exc)
    exc = raises(lambda: ns["prod_bs_find_model_row"](ident, instance_context={"token": u"x"}))
    check("R3 an explicit but unusable context refuses (never treated as context-free)", exc is not None, exc)
    snap = ns["prod_bs_index_snapshot"](ident, instance_context=token)
    check("R4 indexed snapshot reads the selected instance and its own channels clip",
          snap["animset"] is s.target.animset and snap["clip"] is s.target.clip
          and snap["instance_key"] == token["animset_key"])
    peer_row = {"kind": token["kind"]}
    peer_row.update(token)
    peer_row["animset_key"] = ns["prod_strict_identity"](s.peer.animset, u"peer")
    peer_row["gm_key"] = ns["prod_strict_identity"](s.peer.gm, u"peer model")
    peer_snap = ns["prod_bs_index_snapshot"](ident, instance_context=peer_row)
    live = ns["prod_live_bindings_for_cached_scope"](ident, make_scope(ns, ident, token), u"body",
                                                    instance_context=token)
    exc = raises(lambda: ns["prod_instance_pair_check"](token, snapshot=peer_snap))
    check("R5 a bone snapshot from the peer paired with the target context refuses",
          exc is not None and "bone-scale snapshot" in str(exc), exc)
    peer_live = ns["prod_live_bindings_for_cached_scope"](ident, make_scope(ns, ident, peer_row), u"body",
                                                         instance_context=peer_row)
    exc = raises(lambda: ns["prod_instance_pair_check"](token, accepted=peer_live["accepted"]))
    check("R6 peer flex bindings paired with the target context refuse",
          exc is not None and "does not belong" in str(exc), exc)
    check("R7 target bindings and target snapshot pair",
          ns["prod_instance_pair_check"](token, accepted=live["accepted"], snapshot=snap) is True)
    # Name collision: two instances with the same animation-set name.
    s2 = twin_scene(same_name=True)
    fresh_library()
    winc = Window()
    select(ns, winc, s2.target)
    ctx = begin(winc)
    snap2 = ns["prod_bs_index_snapshot"](winc.identity, instance_context=ctx)
    legacy_clip = ns["get_channels_clip"](s2.target.animset, s2.shot)
    check("R8 duplicate names: the selected instance and its own clip are used; the name-only clip lookup would "
          "have returned the first same-named clip",
          snap2["animset"] is s2.target.animset and snap2["clip"] is s2.target.clip
          and s2.instances[0] is s2.target and legacy_clip is s2.target.clip, (snap2["clip"]._handle, legacy_clip._handle))
    s2.order_reversed = True
    s2.sync()
    snap3 = ns["prod_bs_index_snapshot"](winc.identity, instance_context=ctx)
    legacy_clip = ns["get_channels_clip"](s2.target.animset, s2.shot)
    check("R8b duplicate names, reversed clip order: the name-only lookup now returns the peer's clip; the pinned "
          "snapshot still takes the target's own clip",
          legacy_clip is s2.peer.clip and snap3["clip"] is s2.target.clip and snap3["animset"] is s2.target.animset,
          (snap3["clip"]._handle, legacy_clip._handle))
    s2.order_reversed = False
    s2.sync()
    exc = raises(lambda: ns["prod_resolve"](winc.identity))
    check("R9 duplicate names: context-free name resolution refuses (never chooses by name alone)",
          exc is not None and "ambiguous" in str(exc), exc)
    end(winc)


def save(ns, win, scene, name=u"W1 Body"):
    ctx = begin(win)
    try:
        scope = make_scope(ns, win.identity, win.selection_token)
        path = ns["prod_save"](win.identity, u"body", name, scope=scope, operation_context=ctx)
        return path, None
    except Exception as exc:
        return None, exc
    finally:
        end(win)


def section_save(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    peer_before = s.instance_digest(s.peer)
    path, exc = save(ns, win, s)
    rec = ns["p02_read_json"](path) if path else None
    values = (rec or {}).get("values") or {}
    crest = [r for r in (rec or {}).get("bone_scales") or [] if r["bone_name"] == u"zz_crest"]
    check("V1 Save with two same-model instances succeeds and captures the selected instance only",
          exc is None and path is not None and close(values[u"flex.zz_smile"]["mono"], 0.30)
          and close(values[u"flex.zz_brow"]["mono"], 0.10) and len(crest) == 1 and close(crest[0]["value"], 1.13),
          (exc, values, crest))
    check("V2 Save wrote a portable preset: no runtime handles, pointers or instance ownership",
          rec is not None and "instance" not in json.dumps(rec) and "animset_key" not in json.dumps(rec)
          and set(rec["model_ref"]) == set(["path", "capture_checksum"]), rec and sorted(rec))
    check("V3 Save left the peer unchanged", s.instance_digest(s.peer) == peer_before)
    # Reversed enumeration: same result.
    s.order_reversed = True
    path2, exc2 = save(ns, win, s, name=u"W1 Body reversed")
    rec2 = ns["p02_read_json"](path2) if path2 else {}
    check("V4 reversed enumeration order: identical captured values",
          exc2 is None and rec2.get("values") == rec["values"] and rec2.get("bone_scales") == rec["bone_scales"],
          exc2)
    s.order_reversed = False
    # Update through the real path (reread, replace).
    item = {"source": u"v3", "path": path, "record": rec, "revision": ns["prod_json_digest"](rec)}
    ctx = begin(win, u"Update Body Preset")
    s.target.controls  # noqa
    smile = [c for c in s.target.controls if c._name == u"zz_smile"][0]
    smile.raw("channel").log.layers[0].keys[0][1] = 0.33
    smile.raw("channel").raw("toElement").put("flexWeight", 0.33)
    exc3 = raises(lambda: ns["prod_update_preset"](win.identity, item, scope=make_scope(ns, win.identity,
                                                                                                 win.selection_token),
                                                   operation_context=ctx))
    end(win)
    rec3 = ns["p02_read_json"](path)
    check("V5 Update rereads, recaptures from the selected instance and replaces the preset file",
          exc3 is None and close(rec3["values"][u"flex.zz_smile"]["mono"], 0.33)
          and rec3["preset_id"] == rec["preset_id"], exc3)
    check("V6 Update left the peer unchanged", s.instance_digest(s.peer) == peer_before)


def apply_body(ns, win, scene, record, label=u"Apply Body Preset", hook=None):
    ctx = begin(win, label)
    try:
        if hook is not None:
            hook(scene)
        return ns["prod_apply"](win.identity, record, scope=make_scope(ns, win.identity, win.selection_token),
                                operation_context=ctx), None
    except Exception as exc:
        return None, exc
    finally:
        end(win)


def section_apply(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    peer_before = s.instance_digest(s.peer)
    # True no-op: the selected instance already matches.
    result, exc = apply_body(ns, win, s, body_record(s, 0.30, 0.10, 1.13))
    check("A1 no-op Apply against the selected instance: verified, nothing written",
          exc is None and result is not None and result.get("outcome") == u"no-op"
          and s.dm.stack == [], (exc, result and result.get("outcome")))
    check("A1 peer unchanged", s.instance_digest(s.peer) == peer_before)
    # Changed Apply: flex and existing mode-3 scale (deferred verification).
    result, exc = apply_body(ns, win, s, body_record(s, 0.45, 0.20, 1.5))
    pending = (result or {}).get("pending")
    check("A2 changed Apply commits on the selected instance and defers verification",
          exc is None and result is not None and pending is not None and len(s.dm.stack) == 1,
          (exc, result and result.get("outcome")))
    check("A2 selected instance authored (flex key 0.45, brow 0.20)",
          close(flex_value(s.target, u"zz_smile")["key"], 0.45) and close(flex_value(s.target, u"zz_brow")["key"], 0.20),
          (flex_value(s.target, u"zz_smile"), flex_value(s.target, u"zz_brow")))
    check("A2 peer unchanged after commit", s.instance_digest(s.peer) == peer_before)
    run_events(s)
    out = ns["prod_apply_deferred_verify"](pending) if pending else None
    check("A3 deferred verification on the pinned instance: verified, physical scale correct",
          out is not None and out.get("phase") == u"committed-verified" and out.get("verified") is True
          and close(crest_scale(s.target), 1.5), (out, crest_scale(s.target)))
    check("A3 peer unchanged after deferred verification", s.instance_digest(s.peer) == peer_before)
    # Context changes before deferred verification: committed-unverified, no peer access.
    result, exc = apply_body(ns, win, s, body_record(s, 0.5, 0.25, 1.6))
    pending = (result or {}).get("pending")
    removed = s.target.animset
    s.target.animset = None
    s.sync()
    peer_reads_before = len(s.events)
    out = ns["prod_apply_deferred_verify"](pending) if pending else None
    check("A4 selected instance deleted before deferred verification: committed-unverified (context-changed)",
          out is not None and out.get("phase") == u"committed-unverified" and out.get("verified") is not True
          and out.get("reason") == u"context-changed", out)
    check("A4 peer unchanged; nothing written to the peer", s.instance_digest(s.peer) == peer_before)
    s.target.animset = removed
    s.sync()


def section_refusals(ns, Window):
    cases = []

    def run(label, mutate, when=u"before"):
        s = twin_scene()
        fresh_library()
        win = Window()
        select(ns, win, s.target)
        peer_before = s.instance_digest(s.peer)
        target_before = s.instance_digest(s.target)
        if when == u"before":
            mutate(s)
            ctx = None
            exc = raises(lambda: win.operation_begin(u"Apply Body Preset"))
            started = win.operation is not None
            end(win)
            check("X %s: refused at operation entry" % label, exc is not None and not started, exc)
        else:
            result, exc = apply_body(ns, win, s, body_record(s, 0.45, 0.20, 1.5), hook=mutate)
            check("X %s: refused before any write" % label, exc is not None and s.dm.stack == []
                  and s.instance_digest(s.target) == target_before, (exc, s.dm.stack))
        check("X %s: peer unchanged" % label, s.instance_digest(s.peer) == peer_before)

    def delete_target(s):
        s.target.animset = None
        s.target.clip = None
        s.sync()
    run("delete selected instance; compatible peer remains", delete_target)

    def replace_target(s):
        s.target.animset = Live(u"DmeAnimationSet", u"zz_target", gameModel=s.target.gm, controls=s.target.controls,
                                operators=s.target.operators, rootControlGroup=s.target.root)
        s.sync()
    run("replace selected instance with same name/model", replace_target)

    def retarget(s):
        s.target.animset.put("gameModel", s.peer.gm)
        s.sync()
    run("retarget selected animation set to another game model", retarget)

    def new_document(s):
        s.document = Live(u"DmElement", u"session")
    run("document changes after selection", new_document)

    def other_shot(s):
        s.alt_shot = Shot(u"DmeFilmClip", u"shot02", trackGroups=[s._group], animationSets=[s.peer.animset],
                          operators=[])
    run("shot changes after selection", other_shot)

    def unreadable_identity(s):
        m06.native_identity_fails(s.peer.animset)
    run("unreadable peer identity (could be the target)", unreadable_identity)

    def unreadable_target(s):
        m06.native_identity_fails(s.target.animset)
    run("unreadable selected-instance identity", unreadable_target)

    def replace_game_model(s):
        gm = GameModel(s.target.name + u"_model", MODEL, CHECKSUM)
        s.target.gm = gm
        s.target.animset.put("gameModel", gm)
        s.sync()
    run("game model replaced by an identical same-model element", replace_game_model)
    run("game model replaced after pinning, before mutation", replace_game_model, when=u"during")

    run("delete selected instance after pinning, before mutation", delete_target, when=u"during")
    run("replace selected instance after pinning, before mutation", replace_target, when=u"during")


def section_recovery(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    peer_before = s.instance_digest(s.peer)
    target_before = s.instance_digest(s.target)
    real_write = ns["write_side"]
    count = [0]

    def failing(binding, side, origin, desired):
        count[0] += 1
        if count[0] == 2:
            raise RuntimeError("synthetic second flex write failure")
        return real_write(binding, side, origin, desired)
    ns["write_side"] = failing
    try:
        result, exc = apply_body(ns, win, s, body_record(s, 0.45, 0.20, 1.5))
    finally:
        ns["write_side"] = real_write
    check("P1 partial failure inside the transaction: aborted and verified restored on the selected instance",
          exc is not None and not isinstance(exc, ns["ProdRecoveryUnverifiedError"])
          and s.instance_digest(s.target) == target_before and s.dm.stack == [], exc)
    check("P1 peer unchanged", s.instance_digest(s.peer) == peer_before)
    # Failure, and the selected instance disappears before abort verification: recovery-unverified.
    count[0] = 0

    def failing_then_delete(binding, side, origin, desired):
        count[0] += 1
        if count[0] == 2:
            s.dm.after_abort = lambda scene: (setattr(scene.target, "animset", None), scene.sync())
            raise RuntimeError("synthetic failure")
        return real_write(binding, side, origin, desired)
    ns["write_side"] = failing_then_delete
    try:
        result, exc = apply_body(ns, win, s, body_record(s, 0.45, 0.20, 1.5))
    finally:
        ns["write_side"] = real_write
        s.dm.after_abort = None
    check("P2 selected instance unresolvable during abort verification: recovery-unverified, no peer fallback",
          isinstance(exc, ns["ProdRecoveryUnverifiedError"]), exc)
    check("P2 peer unchanged", s.instance_digest(s.peer) == peer_before)


def section_reload(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    path, exc = save(ns, win, s, name=u"Portable")
    old_token = win.selection_token
    identity = dict(win.identity)
    # Reload: a fresh scene with the same content (new native identities).
    s2 = twin_scene()
    exc_old = raises(lambda: ns["prod_resolve_instance"](old_token, identity))
    win.operation = None
    exc_begin = raises(lambda: win.operation_begin(u"Apply Body Preset"))
    check("L1 reload: the old token is unusable and operation entry refuses",
          exc_old is not None and exc_begin is not None and win.operation is None, (exc_old, exc_begin))
    win2 = Window()
    select(ns, win2, s2.target)
    rec = ns["p02_read_json"](path)
    peer_before = s2.instance_digest(s2.peer)
    rec_for_apply = dict(rec)
    rec_for_apply["values"] = dict(rec["values"])
    rec_for_apply["values"][u"flex.zz_smile"] = {"representation": u"MONO", "mono": 0.45}
    result, exc2 = apply_body(ns, win2, s2, rec_for_apply)
    check("L2 fresh selection after reload applies the portable preset to the newly selected instance",
          exc2 is None and result is not None and close(flex_value(s2.target, u"zz_smile")["key"], 0.45),
          (exc2, result and result.get("outcome")))
    check("L2 peer unchanged", s2.instance_digest(s2.peer) == peer_before)


def library_files():
    out = {}
    for base, _, files in os.walk(Library.root):
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as handle:
                out[os.path.relpath(p, Library.root)] = handle.read()
    return out


def delete_instance(s, inst):
    inst.animset = None
    inst.clip = None
    s.sync()


def section_ui(ns, Window):
    """Astra counterexample on the production UI path: select A, delete A, leave the differently named
    same-model instance B as the sole survivor, then invoke ProdWindow.current() and the Save/Apply entry paths."""
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    win.scope = make_scope(ns, win.identity, win.selection_token)
    path, exc = save(ns, win, s, name=u"Before deletion")
    check("U0 fixture: a preset saved from A before deletion", path is not None and exc is None, exc)
    rec = ns["p02_read_json"](path)
    win.selected_item = {"path": path, "record": rec, "source": u"v3", "revision": ns["prod_json_digest"](rec)}
    identity_before = dict(win.identity)
    token_before = win.selection_token
    scope_identity_before = dict(win.scope["identity"])
    peer_before = s.instance_digest(s.peer)
    files_before = library_files()
    writes_before = list(s.cpm_writes)
    delete_instance(s, s.target)
    exc = raises(win.current)
    check("U1 ProdWindow.current() refuses; it never resolves the surviving zz_peer",
          exc is not None and "zz_peer" not in str(exc), exc)
    check("U1 no metadata retarget: identity, token and scope identity unchanged",
          win.identity == identity_before and win.selection_token is token_before
          and win.scope["identity"] == scope_identity_before, (win.identity, win.scope["identity"]))
    statuses = len(win.statuses)
    win.save_kind(u"body")
    save_statuses = win.statuses[statuses:]
    check("U2 production Save entry refuses before the name prompt and before any write",
          win.prompts == [] and library_files() == files_before and s.dm.stack == []
          and s.cpm_writes == writes_before and any(level == u"error" for _, level in save_statuses)
          and not any(level == u"success" for _, level in save_statuses), (win.prompts, save_statuses))
    check("U2 Save published no preset (no new or replaced library file)",
          sorted(library_files()) == sorted(files_before) and win.body_items == [])
    statuses = len(win.statuses)
    win.apply_kind(u"body")
    apply_statuses = win.statuses[statuses:]
    check("U3 production Apply entry refuses before any write",
          s.dm.stack == [] and s.cpm_writes == writes_before and library_files() == files_before
          and any(level == u"error" for _, level in apply_statuses)
          and not any(level == u"success" for _, level in apply_statuses), apply_statuses)
    check("U4 B (zz_peer) unchanged; no metadata retargeted to B",
          s.instance_digest(s.peer) == peer_before and win.identity == identity_before
          and win.identity["animset_name"] == u"zz_target" and win.operation is None)


def section_ui_pinning(ns, Window):
    """Deletion after pinning, inside each production entry action (fresh fixture per entry path)."""
    for entry in (u"save", u"apply"):
        s = twin_scene()
        fresh_library()
        win = Window()
        select(ns, win, s.target)
        win.scope = make_scope(ns, win.identity, win.selection_token)
        path, _ = save(ns, win, s, name=u"Before deletion")
        rec = ns["p02_read_json"](path)
        win.selected_item = {"path": path, "record": rec, "source": u"v3", "revision": ns["prod_json_digest"](rec)}
        identity_before = dict(win.identity)
        peer_before = s.instance_digest(s.peer)
        files_before = library_files()
        writes_before = list(s.cpm_writes)
        real_snapshot = ns["prod_resource_snapshot"]
        pinned = []

        def snapshot(label, *a, **k):
            if _TEXT(label).startswith(u"ACTION_BEGIN:") and s.target.animset is not None:
                pinned.append(win.operation is not None and win.operation.get("context") is not None)
                delete_instance(s, s.target)
            return real_snapshot(label, *a, **k)
        ns["prod_resource_snapshot"] = snapshot
        try:
            statuses = len(win.statuses)
            if entry == u"save":
                win.save_kind(u"body")
            else:
                win.apply_kind(u"body")
            new = win.statuses[statuses:]
        finally:
            ns["prod_resource_snapshot"] = real_snapshot
        check("U5[%s] deletion after pinning: the operation was pinned, then the action refused before writes"
              % entry, pinned == [True] and win.prompts == [] and s.dm.stack == [] and s.cpm_writes == writes_before
              and library_files() == files_before and any(level == u"error" for _, level in new)
              and not any(level == u"success" for _, level in new), (pinned, new))
        check("U5[%s] B unchanged; identity not retargeted; operation closed" % entry,
              s.instance_digest(s.peer) == peer_before and win.identity == identity_before
              and win.operation is None)


def section_clip(ns, Window):
    """The selected instance's channels clip resolution is fail-closed."""
    def attempt(label, mutate, same_name=True):
        for plain in (False, True):
            attempt_one(label, mutate, same_name, plain)

    def attempt_one(label, mutate, same_name, plain):
        # Static-play flexes (default): the M-06 flex reader also needs the clip and may refuse first. Plain flexes:
        # the operation reaches the bone snapshot, which must refuse at the channels-clip resolver itself.
        label = u"%s [%s flexes]" % (label, u"plain" if plain else u"static-play")
        s = twin_scene(same_name=same_name, plain=plain)
        fresh_library()
        win = Window()
        select(ns, win, s.target)
        peer_before = s.instance_digest(s.peer)
        target_before = s.instance_digest(s.target)
        mutate(s)
        s.sync()
        exc = raises(lambda: ns["prod_instance_channels_clip"](s.target.animset, s.shot))
        ctx = begin(win, u"Apply Body Preset")
        exc2 = raises(lambda: ns["prod_bs_index_snapshot"](win.identity, instance_context=ctx)) if ctx else u"no ctx"
        end(win)
        check("K %s: own-clip resolution refuses and the pinned bone snapshot refuses" % label,
              exc is not None and exc2 is not None, (exc, exc2))
        result, exc3 = apply_body(ns, win, s, body_record(s, 0.45, 0.20, 1.5))
        check("K %s: Apply refuses before any write; both instances unchanged" % label,
              exc3 is not None and s.dm.stack == [] and s.instance_digest(s.target) == target_before
              and s.instance_digest(s.peer) == peer_before, (exc3, s.dm.stack))
        if plain:
            check("K %s: the Apply refusal is the channels-clip resolver's own" % label,
                  exc3 is not None and (u"channels clip" in _TEXT(exc3) or u"channel identity" in _TEXT(exc3)),
                  exc3)

    attempt("target clip missing while a same-named peer clip exists", lambda s: setattr(s.target, "clip", None))
    attempt("target clip holds none of the target's channels", lambda s: setattr(s.target, "clip_channels", []))
    attempt("two same-named clips both hold the target's channels",
            lambda s: setattr(s.peer, "clip_channels", list(s.target.flex_channels) + list(s.target.channels)))
    attempt("channels-clip children unreadable", lambda s: setattr(s, "children_unreadable", True))

    def rename_clip(s):
        s.target.clip._name = u"zz_target_renamed"
    attempt("target clip under another name (no name-only fallback)", rename_clip, same_name=False)

    def unreadable_channel(s):
        m06.native_identity_fails(s.target.flex_channels[0])
    attempt("a clip channel's native identity unreadable", unreadable_channel)


def section_contracts(ns, Window):
    s = twin_scene()
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    token = win.selection_token
    identity = dict(win.identity)
    stale = dict(token)
    stale["session"] = u"0" * 16
    exc = raises(lambda: ns["prod_resolve_instance"](stale, identity))
    check("N1 a token from another session (restart) refuses", exc is not None and "earlier session" in str(exc), exc)
    exc = raises(lambda: ns["prod_context_token"](identity))
    check("N2 an operation context cannot be built without a selection token", exc is not None, exc)
    # Fit source carries the selected instance; live reacquisition stays on it (plain flexes: Clothing Fit capture
    # predates static-play support).
    s = twin_scene(plain=True)
    fresh_library()
    win = Window()
    select(ns, win, s.target)
    token = win.selection_token
    identity = dict(win.identity)
    scope = make_scope(ns, identity, token)
    source = ns["prod_body_source"](identity, scope, instance_context=token)
    check("F1 Clothing Fit source baseline carries the selected instance token (runtime only)",
          source["instance"] is not None and source["instance"]["animset_key"] == token["animset_key"], source["instance"])
    check("F1 Clothing Fit source values are the selected instance's (smile 0.30, brow 0.10), not the peer's",
          repr(source["source_values"]).count("0.3") >= 1 and "0.7" not in repr(source["source_values"])
          and "0.55" not in repr(source["source_values"]), source["source_values"])
    live = ns["prod_body_source_live_from_baseline"](source, scope)
    check("F2 live reacquisition from the baseline resolves the selected instance's bindings",
          sorted(live["accepted"]) == sorted(source["source_descriptors"])
          and live["source_native"] == {"fixture_native_index_of": s.target.gm._handle}
          and source["source_native"] == live["source_native"], (live["source_native"], s.target.gm._handle))
    peer_before = s.instance_digest(s.peer)
    removed = s.target.animset
    delete_instance(s, s.target)
    exc = raises(lambda: ns["prod_body_source_live_from_baseline"](source, scope))
    check("F3 selected source deleted during Clothing Fit: reacquisition refuses (no same-model peer fallback)",
          exc is not None, exc)
    # Context-free resolution never retargets to a differently named sole survivor.
    exc = raises(lambda: ns["prod_resolve"](identity))
    check("N3 context-free prod_resolve refuses the differently named sole survivor",
          exc is not None and "was not found" in str(exc), exc)
    peer_identity = {"model": MODEL, "checksum": CHECKSUM, "animset_name": u"zz_peer"}
    row = ns["prod_resolve"](peer_identity)
    check("N4 context-free resolution of the survivor by its own name is unchanged",
          row["animset"] is s.peer.animset)
    check("N5 peer unchanged", s.instance_digest(s.peer) == peer_before)
    s.target.animset = removed
    s.sync()
    # Context-free ambiguity refusal is preserved (two same-named instances, no token).
    s2 = twin_scene(same_name=True)
    exc = raises(lambda: ns["prod_resolve"]({"model": MODEL, "checksum": CHECKSUM, "animset_name": u"zz_target"}))
    check("N6 context-free ambiguity refusal preserved", exc is not None and "ambiguous" in str(exc), exc)
    # Nothing runtime is persisted: every library file after Save/Update is free of runtime identity.
    s3 = twin_scene()
    fresh_library()
    win3 = Window()
    select(ns, win3, s3.target)
    save(ns, win3, s3, name=u"Persist check")
    blob = b"".join(library_files().values()).decode("utf-8")
    # Unique-ID text must be a content rendering; pointer-style or per-call renderings fail closed.
    s4 = twin_scene()
    counter = [0]

    class PointerId(UniqueId):
        def __str__(self):
            counter[0] += 1
            return "<Swig Object of type 'DmObjectId_t *' at 0x%08x>" % (0x1000 + counter[0])

    class VaryingId(UniqueId):
        def __str__(self):
            counter[0] += 1
            return u"%s-%d" % (self.text, counter[0])
    for label, cls in ((u"pointer-style", PointerId), (u"per-call varying", VaryingId)):
        element = s4.target.animset
        original = element.__dict__.pop("_uid", None)
        element.__dict__["_uid"] = cls(original.text if original else u"x")
        exc = raises(lambda: ns["prod_strict_identity"](element, u"An animation set"))
        rows, _ = ns["prod_model_candidates"]()
        target_rows = [r for r in rows if r["animset_name"] == u"zz_target"]
        check("N8 %s unique-ID text: strict identity refuses and the row cannot be selected" % label,
              exc is not None and len(target_rows) == 1 and target_rows[0]["selection_token"] is None, exc)
        element.__dict__["_uid"] = original
    check("N7 no library file contains runtime identity (session, keys, handles, unique IDs)",
          blob and all(t not in blob for t in (u"animset_key", u"gm_key", u"document_key", u"shot_key",
                                               u"session", u"-w1-", u"prod-selected-instance")), len(blob))


def section_clip_ownership(ns, Window):
    """Astra's W1 review counterexample: two same-named clips both hold the selected instance's channel; the
    second clip's channels membership becomes unreadable. An unreadable, potentially relevant clip is never
    treated as unrelated; production Body Save and Apply refuse before any preset or scene write."""
    def two_owners(plain=True):
        s = twin_scene(same_name=True, plain=plain)
        s.peer.clip_channels = list(s.peer.flex_channels) + list(s.peer.channels) + [s.target.flex_channels[0]]
        s.sync()
        return s

    s = two_owners()
    exc = raises(lambda: ns["prod_instance_channels_clip"](s.target.animset, s.shot))
    check("O1 two same-named clips with readable membership in a selected channel: resolution refuses (two "
          "owners)", exc is not None and "found 2" in _TEXT(exc), exc)
    s.peer.clip_channels_unreadable = True
    s.sync()
    exc = raises(lambda: ns["prod_instance_channels_clip"](s.target.animset, s.shot))
    check("O2 second clip's channels membership unreadable: resolution refuses; the clip is not classified as "
          "unrelated", exc is not None and "unreadable" in _TEXT(exc) and "found 1" not in _TEXT(exc), exc)

    for plain in (True, False):
        label = u"plain" if plain else u"static-play"
        s = twin_scene(same_name=True, plain=plain)
        fresh_library()
        win = Window()
        select(ns, win, s.target)
        win.scope = make_scope(ns, win.identity, win.selection_token)
        path, _ = save(ns, win, s, name=u"Before ownership loss")
        rec = ns["p02_read_json"](path) if path else None
        win.selected_item = {"path": path, "record": rec, "source": u"v3",
                             "revision": ns["prod_json_digest"](rec)} if rec else None
        s.peer.clip_channels = list(s.peer.flex_channels) + list(s.peer.channels) + [s.target.flex_channels[0]]
        s.peer.clip_channels_unreadable = True
        s.sync()
        files_before = library_files()
        writes_before = list(s.cpm_writes)
        peer_before = s.instance_digest(s.peer)
        target_before = s.instance_digest(s.target)
        statuses = len(win.statuses)
        win.save_kind(u"body")
        new = win.statuses[statuses:]
        check("O3[%s] production Body Save with unresolved clip ownership refuses before preset creation" % label,
              library_files() == files_before and win.body_items == []
              and any(level == u"error" for _, level in new) and not any(level == u"success" for _, level in new),
              (win.prompts, new, sorted(set(library_files()) - set(files_before))))
        check("O3[%s] no scene or peer write" % label,
              s.dm.stack == [] and s.cpm_writes == writes_before and s.instance_digest(s.peer) == peer_before
              and s.instance_digest(s.target) == target_before)
        if win.selected_item is not None:
            statuses = len(win.statuses)
            record = dict(rec)
            record["values"] = dict(rec["values"])
            record["values"][u"flex.zz_brow"] = {"representation": u"MONO", "mono": 0.25}
            win.selected_item = {"path": path, "record": record, "source": u"legacy-v2"}
            win.apply_kind(u"body")
            new = win.statuses[statuses:]
            check("O4[%s] production Apply with unresolved clip ownership refuses before mutation" % label,
                  s.dm.stack == [] and s.cpm_writes == writes_before and s.instance_digest(s.peer) == peer_before
                  and s.instance_digest(s.target) == target_before and library_files() == files_before
                  and any(level == u"error" for _, level in new)
                  and not any(level == u"success" for _, level in new), new)
        else:
            check("O4[%s] fixture: preset saved before the ownership loss" % label, False)

    # Positive coverage: one uniquely verified clip, and correctly verified unrelated clips.
    s = twin_scene(same_name=True)
    clip = ns["prod_instance_channels_clip"](s.target.animset, s.shot)
    check("O5 one uniquely verified owner among same-named clips is resolved", clip is s.target.clip)
    s = twin_scene()
    s.peer.clip_channels_unreadable = True                  # differently named: verified unrelated by its name
    extra_type = Live(u"DmeFilmClip", u"zz_target", channels=[])  # same name, other type: verified unrelated
    extra_type._attrs["channels"] = BrokenAttr(extra_type, "channels")
    s.sync()
    s._track.put("children", list(s._track.raw("children")) + [extra_type])
    try:
        clip = ns["prod_instance_channels_clip"](s.target.animset, s.shot)
    except Exception as exc:
        clip = exc
    check("O6 clips verified unrelated by name or type are not read and do not block resolution",
          clip is s.target.clip, clip)

    # The same ownership proof: unreadable control-channel references and unreadable clip identity refuse.
    def refuses(label, mutate, same_name=True):
        s = twin_scene(same_name=same_name)
        mutate(s)
        exc = raises(lambda: ns["prod_instance_channels_clip"](s.target.animset, s.shot))
        check("O7 %s: resolution refuses" % label, exc is not None, exc)

    def control_channel_unreadable(s):
        control = [c for c in s.target.controls if c._name == u"zz_smile"][0]
        control._attrs["channel"] = BrokenAttr(control, "channel")
    refuses("a selected control's channel reference unreadable", control_channel_unreadable)

    def controls_unreadable(s):
        s.target.animset._attrs["controls"] = BrokenAttr(s.target.animset, "controls")
    refuses("the selected animation set's controls unreadable", controls_unreadable)

    def clip_name_unreadable(s):
        s.peer.clip.GetName = raiser
    refuses("a candidate clip's name unreadable", clip_name_unreadable, same_name=False)

    def clip_type_unreadable(s):
        m06.native_type_fails(s.peer.clip)
    refuses("a candidate clip's type unreadable", clip_type_unreadable)

    def null_clip(s):
        s.sync()
        s._track.put("children", list(s._track.raw("children")) + [None])
    refuses("a null channels-clip entry", null_clip)

    def null_member(s):
        s.peer.clip_channels = list(s.peer.flex_channels) + [None]
        s.sync()
    refuses("a null membership entry in a same-named clip", null_member)


def raiser(*a, **k):
    raise RuntimeError("synthetic native failure")


def section_static(app):
    body = app.top_text("prod_resolve_instance")
    check("static.resolver_never_matches_by_name", "animset_name\") ==" not in body and "\"animset_name\")\n" not in body
          and "animset_key" in body)
    token = app.top_text("prod_selection_token")
    check("static.token_has_no_name", "name(" not in token)
    finder = app.top_text("prod_bs_find_model_row")
    check("static.legacy_route_kept_for_context_free_calls", "for row in p03_model_animsets()" in finder
          and "resolved uniquely" in finder)
    check("static.created_helper_unchanged_context_free",
          "instance_context" not in app.top_text("prod_bs_resolve_created"))
    for method, n in (("review_reclassify", 2), ("review_decision", 2), ("fit_selected", 1),
                      ("fit_candidate_rows", 1), ("render", 2), ("current", 1)):
        text = app.method_text("ProdWindow", method)
        check("static.%s_propagates_selection_token" % method,
              text.count("prod_instance_kw(") >= n and "selection_token" in text, text.count("prod_instance_kw("))
    for fn in ("prod_set_override", "prod_clear_override", "prod_scope", "prod_probe_semantic_provider",
               "prod_live_bindings_for_cached_scope", "prod_body_source", "prod_body_source_live_from_baseline",
               "prod_bs_index_snapshot", "prod_capture_bone_scale_map", "prod_bs_current_bone_index",
               "prod_bs_resolve_binding", "prod_bs_resolve_clean_fixture"):
        check("static.%s_carries_instance_context" % fn, "prod_instance_kw(" in app.top_text(fn))
    for fn in ("prod_apply", "prod_capture_body_snapshot", "prod_body_source",
               "prod_body_source_live_from_baseline"):
        check("static.%s_pairs_bindings_with_the_pinned_instance" % fn, "prod_instance_pair_check(" in app.top_text(fn))
    for fn in ("prod_save", "prod_update_preset"):
        text = app.top_text(fn)
        check("static.%s_acquires_on_the_pinned_instance_and_captures_through_the_pair_check" % fn,
              "prod_instance_kw(" in text and "prod_validate_context_token(" in text
              and "prod_capture_body_snapshot(" in text and "operation_context=operation_context" in text)
    check("static.strict_identity_uses_native_unique_ids",
          all(t in app.top_text("prod_strict_identity") for t in ("GetHandle()", "GetId()", "IsUniqueIdValid",
                                                                    "IsUniqueIdEqual", "GetElementId(", "GetElement(")))
    check("static.dme_id_not_replaced", "def dme_id(" in app.text(*app.top["dme_id"][:2]) if "dme_id" in app.top
          else False)


def main():
    print("M-06 W1 selected-instance integration (Python %s)" % sys.version.split()[0])
    app = route.AppSource(route.APP_PATH)
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    try:
        ns, methods = build_namespace(app)
        Window = make_window(ns, methods)
    except Exception:
        check("namespace.built", False, traceback.format_exc())
        return finish()
    for section in (lambda: section_selection(ns, Window), lambda: section_resolution(ns, Window),
                    lambda: section_save(ns, Window), lambda: section_apply(ns, Window),
                    lambda: section_refusals(ns, Window), lambda: section_recovery(ns, Window),
                    lambda: section_reload(ns, Window), lambda: section_ui(ns, Window),
                    lambda: section_ui_pinning(ns, Window), lambda: section_clip(ns, Window),
                    lambda: section_contracts(ns, Window), lambda: section_clip_ownership(ns, Window),
                    lambda: section_static(app)):
        try:
            section()
        except Exception:
            check("section.completed", False, traceback.format_exc())
    return finish()


def counterexamples():
    """--phase=counterexample: the starting-candidate defects, run against CPM_TEST_APP_PATH (base or candidate).
    Each line reports whether the defect is REPRODUCED by that application source. Nothing here is a pass/fail
    assertion of the candidate; the run phase is."""
    print("M-06 W1 counterexamples (Python %s)" % sys.version.split()[0])
    app = route.AppSource(route.APP_PATH)
    print("App sha256: %s" % route._sha(route.APP_PATH))
    del RESULTS[:]
    ns, methods = build_namespace(app)
    Window = make_window(ns, methods)
    del RESULTS[:]
    has_token = "prod_resolve_instance" in app.top
    print("selected-instance token support: %s" % ("present" if has_token else "absent"))
    rows = []

    def report(label, reproduced, detail):
        rows.append((label, reproduced))
        print("[%s] %s\n      %s" % ("DEFECT REPRODUCED" if reproduced else "not reproduced", label, detail))

    target = {"model": MODEL, "checksum": CHECKSUM, "animset_name": u"zz_target"}

    # C1: two same-model instances; the bone-scale model row is matched by model/checksum only.
    # Production route: the base has only the context-free call; the candidate's operations pass the pinned token
    # (the context-free helper is kept, unchanged, for context-free callers).
    s1 = twin_scene()
    exc = raises(lambda: ns["prod_bs_find_model_row"](target))
    legacy = exc if exc is not None else u"resolved"
    if has_token:
        fresh_library()
        win = Window()
        select(ns, win, s1.target)
        row = ns["prod_bs_find_model_row"](win.identity, instance_context=win.selection_token)
        reproduced, detail = row["animset"] is not s1.target.animset, u"pinned route resolves %s; context-free "             u"helper: %s" % (row["animset"]._name, legacy)
    else:
        reproduced, detail = exc is not None and "resolved uniquely" in str(exc), legacy
    report("C1 two same-model instances: the production bone-scale route cannot reach the selected instance "
           "(Save/Update/Apply of a Body preset with bone scales refuses)", reproduced, detail)

    # C2: select A, delete A; differently named same-model B is the sole survivor.
    s2 = twin_scene()
    delete_instance(s2, s2.target)
    try:
        row = ns["prod_resolve"](dict(target))
        survivor = row["animset"]._name
    except Exception as exc2:
        survivor = None
        row = exc2
    report("C2 context-free prod_resolve after deleting A returns the surviving B (silent retarget)",
           survivor == u"zz_peer", survivor or row)
    win = Window()
    win.identity = dict(target)
    win.selection_token = None
    if has_token:
        s2 = twin_scene()
        fresh_library()
        select(ns, win, s2.target)
        delete_instance(s2, s2.target)
    try:
        current = win.current()
        published = (current.get("animset_name"), win.identity.get("animset_name"))
    except Exception as exc3:
        published = exc3
    report("C2 production ProdWindow.current() after deleting A resolves B and retargets the window metadata",
           isinstance(published, tuple) and u"zz_peer" in published, published)

    # C3: two same-named instances; the channels clip is found by animation-set name only.
    s3 = twin_scene(same_name=True)
    s3.order_reversed = True
    s3.sync()
    clip = ns["get_channels_clip"](s3.target.animset, s3.shot)
    legacy = u"name-only get_channels_clip returns %s clip" % (u"the peer's" if clip is s3.peer.clip else u"the target's")
    if has_token:
        fresh_library()
        win = Window()
        s3.order_reversed = False
        s3.sync()
        select(ns, win, s3.target)
        ctx = begin(win)
        s3.order_reversed = True
        s3.sync()
        snap = ns["prod_bs_index_snapshot"](win.identity, instance_context=ctx)
        end(win)
        reproduced = snap["clip"] is not s3.target.clip
        detail = u"pinned snapshot takes %s clip; %s" % (u"the target's own" if not reproduced else u"another",
                                                         legacy)
    else:
        reproduced, detail = clip is s3.peer.clip, legacy
    report("C3 duplicate animation-set names, reversed clip order: the production bone snapshot reads the peer's "
           "channels clip for the target", reproduced, detail)
    if Library.root:
        shutil.rmtree(Library.root, ignore_errors=True)
    print("COUNTEREXAMPLES: %d/%d defects reproduced" % (sum(1 for _, r in rows if r), len(rows)))
    return 0


def finish():
    if Library.root:
        shutil.rmtree(Library.root, ignore_errors=True)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    if "--phase=counterexample" in sys.argv[1:]:
        sys.exit(counterexamples())
    if "--phase=run" not in sys.argv[1:]:
        print("usage: test_cpm_app_m06_instance_resolution.py --phase=run|--phase=counterexample")
        sys.exit(2)
    sys.exit(main())
