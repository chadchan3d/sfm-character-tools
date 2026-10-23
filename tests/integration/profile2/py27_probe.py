# -*- coding: utf-8 -*-
"""Profile-2 menu-directory probe (TEST-ONLY). Runs under SFM's Python 2.7.5, one scenario per process
(one process = one SFM session), against a scratch SFM installation. Prints one JSON line.

usage: <SFM python 2.7.5> -E -B py27_probe.py SCENARIO GAME_DIR REPO_DIR

The CPM application and the Normalizer are SFM MAINMENU scripts and cannot be imported offline; the
functions under test are extracted verbatim from the installed copies (by name, with ast) and executed
with only SFM/Qt boundaries stubbed. Everything else is real: the installed adapter, authority package,
broker and the installed sidecar.
"""
import ast
import json
import os
import sys
import textwrap

SCENARIO, GAME, REPO = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
MENU = os.path.join(GAME, "usermod", "scripts", "sfm", "mainmenu", "SFM Character Tools")
LIB = os.path.join(GAME, "usermod", "scripts", "SFM Character Tools")
LEGACY = os.path.join(GAME, "usermod", "scripts", "sfm", "mainmenu", "ChadChan3D")
APP = os.path.join(GAME, "usermod", "scripts", "ChadChan3D_CPM", "SFM_Character_Preset_Manager.py")
NORMALIZER = os.path.join(MENU, "Rebuild_Control_Groups_Normalizer.py")
MASTER = os.path.join(GAME, "usermod", "cfg", "sfm_defaultanimationgroups.txt")
sys.executable = os.path.join(GAME, "sfm.exe")   # SFM: sys.executable is game\sfm.exe
OUT = {"scenario": SCENARIO}


def read(p):
    with open(p, "rb") as f:
        return f.read()


def extract(path, names):
    """Top-level assignments and functions, and methods of any class, by name, verbatim."""
    raw = read(path)
    lines = raw.decode("utf-8").splitlines(True)
    tree = ast.parse(raw)   # bytes: Python 2.7 honours the coding declaration
    got = {}
    for node in ast.walk(tree):
        name = getattr(node, "name", None)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        if name in names and name not in got and hasattr(node, "lineno"):
            start = node.lineno - 1
            if hasattr(node, "decorator_list") and node.decorator_list:
                start = node.decorator_list[0].lineno - 1
            end = start + 1
            indent = len(lines[start]) - len(lines[start].lstrip())
            while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > indent
                                        or lines[end].lstrip().startswith(")")):
                end += 1
            got[name] = textwrap.dedent("".join(lines[start:end]))
    missing = [n for n in names if n not in got]
    if missing:
        raise RuntimeError("not found: %r" % missing)
    return [got[n] for n in names]


def normalizer_authority_block():
    """The Normalizer's module-level authority bootstrap, verbatim: from its pinned API/build constants and
    locator through the import-time identity verification call."""
    src = read(NORMALIZER).decode("utf-8")
    a = src.index("_AUTHORITY_EXPECTED_API_VERSION = ")
    b = src.index("_authority_verify_bootstrap_identity()\n", src.index("def _authority_verify_bootstrap_identity():") + 10)
    return src[a:b + len("_authority_verify_bootstrap_identity()\n")]


def run_normalizer_block(ns):
    exec(compile("import os, sys\n" + normalizer_authority_block(), "Normalizer:authority-bootstrap", "exec"), ns)
    return ns


class _QtCore(object):
    class QThread(object):
        T = object()

        @staticmethod
        def currentThread():
            return _QtCore.QThread.T

    class QCoreApplication(object):
        class _App(object):
            def thread(self):
                return _QtCore.QThread.T

        @staticmethod
        def instance():
            return _QtCore.QCoreApplication._App()


def cpm_import_adapter():
    ns = {"os": os, "sys": sys}
    for s in extract(APP, ["PROD_CPM_MAINMENU_RELATIVE_PARTS", "PROD_CPM_ADAPTER_MODULES",
                           "ProdCpmAuthorityBootstrapError", "prod_cpm_mainmenu_dir", "prod_cpm_import_adapter"]):
        exec(compile(s, "CPM", "exec"), ns)
    return ns


def outcome(fn):
    try:
        return "OK", fn()
    except Exception as exc:
        return "REFUSED", "%s: %s" % (type(exc).__name__, str(exc)[:300])


if SCENARIO == "locators":
    cpm = cpm_import_adapter()
    OUT["cpm_app"] = cpm["prod_cpm_mainmenu_dir"]()
    nz = {"os": os, "sys": sys}
    exec(compile(extract(NORMALIZER, ["_authority_locate_mainmenu_dir"])[0], "N", "exec"), nz)
    OUT["normalizer"] = nz["_authority_locate_mainmenu_dir"]()
    sys.path.insert(0, LIB)
    import cpm_authority_adapter as adapter
    OUT["adapter"] = adapter.locate_mainmenu_dir()
    from sfm_master_authority_productionized import bootstrap
    OUT["bootstrap"] = bootstrap.bootstrap_import_path()
    ql = {}
    exec(compile(extract(os.path.join(REPO, "cpm", "quick_launch", "cpm_ase_quick_launch.py"),
                         ["LAUNCHER_RELATIVE_PARTS"])[0], "QL", "exec"), ql)
    OUT["quick_launch_launcher"] = os.path.join(GAME, *ql["LAUNCHER_RELATIVE_PARTS"])
    OUT["expected"] = LIB
    OUT["menu"] = MENU
    OUT["origins"] = {"adapter": os.path.dirname(os.path.abspath(adapter.__file__)),
                      "package": os.path.dirname(os.path.dirname(os.path.abspath(bootstrap.__file__)))}

elif SCENARIO == "acquire":
    # Normalizer first, exactly as its module import would run, then its acquisition method.
    ns = run_normalizer_block({"__name__": "normalizer"})
    rt = ns["authority_runtime"]
    meth = extract(NORMALIZER, ["acquire_master_index_via_qualified_authority"])[0]

    class ProbeError(Exception):
        pass
    ns.update(QtCore=_QtCore, ProbeError=ProbeError)
    exec(compile(meth, "Normalizer:acquire", "exec"), ns)
    import hashlib
    master_sha = hashlib.sha256(read(MASTER)).hexdigest()

    class Cmd(object):
        master_path = MASTER
        master_hash = master_sha
        master_index_scope_folds = frozenset([u"head", u"jaw", u"eyelid_upper_l"])
    cmd = Cmd()
    payload = ns["acquire_master_index_via_qualified_authority"](cmd, os.path.join(GAME, "usermod"))
    n_broker = cmd._master_index_broker
    cmd._master_index_broker.release_lease(cmd._master_index_lease) if hasattr(n_broker, "release_lease") else None
    OUT["normalizer"] = {"payload_type": type(payload).__name__, "keys": sorted(payload)[:8]}
    # CPM: the application's own import route, then the adapter's canonical bootstrap and a bounded read.
    cpm = cpm_import_adapter()
    adapter = cpm["prod_cpm_import_adapter"]()
    auth = adapter.open_canonical_authority(MASTER)
    desc = auth.generation_descriptor()
    answers = auth.query_many([u"Head", u"Jaw"])
    OUT["cpm"] = {"source_sha256": desc["source_sha256"], "answers": len(answers),
                  "shipped_root": auth._shipped_root if hasattr(auth, "_shipped_root") else None}
    OUT["same_broker"] = auth._broker is n_broker
    OUT["master_sha256"] = master_sha
    OUT["canonical"] = rt.is_canonical()

elif SCENARIO == "stray_menu_copy_first":
    # A copy of the internal library left inside the menu folder (the superseded, never-signed layout) is
    # imported first: the Normalizer and CPM must refuse it as the wrong origin.
    sys.path.insert(0, MENU)
    import sfm_master_authority_productionized.runtime as stray_rt
    OUT["loaded_first_from"] = os.path.dirname(os.path.dirname(os.path.abspath(stray_rt.__file__)))
    OUT["normalizer"] = outcome(lambda: run_normalizer_block({"__name__": "normalizer"}) and "loaded")
    cpm = cpm_import_adapter()
    OUT["cpm"] = outcome(lambda: cpm["prod_cpm_import_adapter"]().canonical_bootstrap() and "loaded")

elif SCENARIO in ("mixed_legacy_first", "mixed_new_first"):
    if SCENARIO == "mixed_legacy_first":
        # A legacy Normalizer from mainmenu\ChadChan3D imports its own package copy first.
        sys.path.insert(0, LEGACY)
        import sfm_master_authority_productionized.runtime as legacy_rt
        OUT["loaded_first_from"] = os.path.dirname(os.path.dirname(os.path.abspath(legacy_rt.__file__)))
        OUT["normalizer"] = outcome(lambda: run_normalizer_block({"__name__": "normalizer"}) and "loaded")
        cpm = cpm_import_adapter()
        OUT["cpm"] = outcome(lambda: cpm["prod_cpm_import_adapter"]().canonical_bootstrap() and "loaded")
    else:
        OUT["normalizer"] = outcome(lambda: run_normalizer_block({"__name__": "normalizer"}) and "loaded")
        # A legacy CPM adapter from mainmenu\ChadChan3D attempts its canonical bootstrap afterwards.
        legacy = {"__name__": "legacy_adapter", "__file__": os.path.join(LEGACY, "cpm_authority_adapter.py")}
        sys.path.insert(0, LEGACY)
        exec(compile(read(os.path.join(LEGACY, "cpm_authority_adapter.py")), "legacy_adapter", "exec"), legacy)
        OUT["legacy_adapter"] = outcome(lambda: legacy["canonical_bootstrap"]() and "loaded")
else:
    raise SystemExit("unknown scenario")

print(json.dumps(OUT, default=repr))
