"""Verified package installation with TXT-only backups and completion-oriented retry.

The updater installation lock is shared; updater code and records are unchanged.
"""
import hashlib
import ctypes
import sys
from datetime import datetime, timezone
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path

from updater.sfm_character_tools_updater import journal as updater_journal
from updater.sfm_character_tools_updater import w32
from updater.sfm_character_tools_updater.layout import Layout, TXID_RE
from updater.sfm_character_tools_updater.process_gate import process_status


from . import release

RELEASE_SHA256 = release.SHA256
MASTER = "cfg/sfm_defaultanimationgroups.txt"
AUTH_DIR = "cfg/sfm_shared_authority"
MANIFEST = AUTH_DIR + "/manifest.json"
BUTTON = "scripts/sfm/autoinit/ChadChan3D/ChadChan3D_CPM_ASE_Button.py"
BUTTON_IMPL = "scripts/ChadChan3D_CPM/cpm_ase_quick_launch.py"
MANAGER = "scripts/sfm/mainmenu/SFM Character Tools/Manage Installation.py"
HELPER = "tools/SFM Character Tools Installer/SCT_Setup.exe"
AUTH_RE = re.compile(r"^cfg/sfm_shared_authority/sfm_master_0_[0-9a-f]{64}\.sfmsidecar$")
BUTTON_HASHES = {
    BUTTON: "23e3a8813057642400b7e06e0b55e13c89f47b684779d907740905a5e28e4070",
    BUTTON_IMPL: "7a01bd5eb828631a6bc0f2df2e5a7f692eae812877e0debe7e0a364199b63f67",
}
STATE_REL = "cfg/sfm_character_tools_installer"
STATE_SCHEMA = "sct-workshop-install-2"


class Refusal(RuntimeError):
    """A safe, expected refusal with no success claim."""


class RecoveryConflict(Refusal):
    """A recorded destination changed after an interrupted operation."""

    def __init__(self, path):
        self.path = path
        super().__init__("Automatic recovery cannot continue because this file changed after Setup was interrupted:\n" +
                         path + "\n\nPreserve your changes and seek recovery assistance.")


def digest_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _write_json(path, data):
    """Replace a record only after its new bytes have reached the filesystem."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".new." + uuid.uuid4().hex)
    raw = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")
    try:
        with open(temp, "xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _read_json(path):
    with open(path, "rb") as f:
        return json.load(f)


def _plain(path):
    """Reject Windows reparse points in existing target ancestors and files."""
    path = Path(path)
    for p in (path, *path.parents):
        try:
            st = p.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & 0x400:
            raise Refusal("A target path contains a link or reparse point")


def _target(game, rel):
    if rel.startswith("/") or "\\" in rel or ":" in rel or any(p in ("", ".", "..") for p in rel.split("/")):
        raise Refusal("Invalid relative destination")
    p = Path(game) / "usermod" / Path(*rel.split("/"))
    if len(str(p)) >= 260:
        raise Refusal("Installed path exceeds the SFM Python 2.7 path limit")
    _plain(p)
    return p


def _existing_hash(path):
    if not path.exists():
        return None
    if not path.is_file():
        raise Refusal("A destination is not a regular file")
    return digest_file(path)


def _validate_game(game):
    game = Path(game).absolute()
    if str(game).startswith("\\\\"):
        raise Refusal("A network SFM installation is outside the supported path boundary")
    if not game.is_dir() or not (game / "usermod").is_dir() or not (game / "workshop").is_dir():
        raise Refusal("Select the SFM game folder containing usermod and workshop")
    _plain(game)
    _plain(game / "usermod")
    return game


def _autoinit_mounts(game):
    """Read only ordinary Game mounts from the installation's SearchPaths block."""
    config = game / "usermod" / "gameinfo.txt"
    _plain(config)
    with config.open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("gameinfo.txt exceeds the supported configuration size")
    text = raw.decode("utf-8-sig")
    token = re.compile(r'(?P<skip>\s+|//[^\r\n]*|/\*.*?\*/)|'
                       r'(?P<string>"(?:\\.|[^"\\])*")|(?P<brace>[{}])|'
                       r'(?P<bare>(?:(?!//|/\*)[^\s{}"])+)', re.DOTALL)
    tokens, pos = [], 0
    while pos < len(text):
        match = token.match(text, pos)
        if match is None:
            raise ValueError("unsupported or incomplete gameinfo.txt syntax")
        pos = match.end()
        kind, value = match.lastgroup, match.group()
        if kind == "skip":
            continue
        if kind == "bare" and any(c in value for c in "#[]"):
            raise ValueError("conditional/include syntax is not supported")
        tokens.append((kind, value[1:-1] if kind == "string" else value))

    wanted = ("gameinfo", "filesystem", "searchpaths")
    blocks = {wanted[:n]: 0 for n in (1, 2, 3)}
    stack, paths, index = [], [], 0
    while index < len(tokens):
        kind, key = tokens[index]
        if kind == "brace" and key == "}":
            if not stack:
                raise ValueError("unbalanced gameinfo.txt blocks")
            stack.pop()
            index += 1
            continue
        if kind == "brace" or key.startswith("#") or index + 1 >= len(tokens):
            raise ValueError("unsupported or incomplete gameinfo.txt entry")
        value_kind, value = tokens[index + 1]
        if value_kind == "brace":
            if value != "{":
                raise ValueError("missing gameinfo.txt entry value")
            stack.append(key.lower())
            block = tuple(stack)
            if block in blocks:
                blocks[block] += 1
        elif tuple(stack) == wanted and key.lower() == "game":
            paths.append(value)
        index += 2
    if stack or any(count != 1 for count in blocks.values()):
        raise ValueError("one complete GameInfo/FileSystem/SearchPaths block is required")

    roots = []
    for value in paths:
        if value.lower() == "|gameinfo_path|.":
            root = game / "usermod"
        else:
            relative = value.replace("\\", "/")
            if any(c in relative for c in "*?|[]\x00\""):
                raise ValueError("unsupported Game search path")
            _validate_rel(relative)
            root = game / Path(*relative.split("/"))
        # Relative paths have no absolute or traversal components.
        root.relative_to(game)
        roots.append(root)
    return roots


def _check_autoinit(game):
    """Require the complete dependency together in a configured safe mount."""
    game = Path(game).absolute()
    try:
        roots = _autoinit_mounts(game)
        for mount in roots:
            root = mount / "scripts" / "sfm"
            files = (root / "autoinit" / "autoinit_manager.py", root / "sfm_init_local.py",
                     root / "mainmenu" / "kiwifruitdev" / "autoinit_manager.py")
            if all(path.is_file() for path in files):
                _plain(mount)
                for path in files:
                    _plain(path)
                return True
    except (OSError, UnicodeError, ValueError, Refusal) as exc:
        raise Refusal("Autoinit Manager's location could not be verified from "
                      "usermod/gameinfo.txt: " + str(exc)) from exc
    return False


def _zip_member_kind(info):
    mode = info.external_attr >> 16
    if (mode and stat.S_ISLNK(mode)) or info.filename.endswith("/"):
        raise Refusal("Unsupported ZIP entry type")


def _map_member(name):
    if name.startswith("usermod/"):
        return name[len("usermod/"):]
    optional = "OPTIONAL - CPM Button/usermod/"
    if name.startswith(optional):
        return name[len(optional):]
    if name in ("README.txt", "OPTIONAL - CPM Button/README.txt"):
        return None
    raise Refusal("Unexpected release ZIP entry")


def _validate_rel(rel):
    if not rel or rel.startswith("/") or "\\" in rel or ":" in rel:
        raise Refusal("Unsafe ZIP destination")
    if any(part in ("", ".", "..") or part.rstrip(". ") != part for part in rel.split("/")):
        raise Refusal("Unsafe ZIP destination")


def _validate_authority(files, stage):
    sidecars = [p for p in files if AUTH_RE.match(p)]
    if len(sidecars) != 1 or MASTER not in files or MANIFEST not in files:
        raise Refusal("Release authority is incomplete")
    meta = _read_json(stage / Path(*MANIFEST.split("/")))
    if (meta.get("source_sha256") != files[MASTER] or
            meta.get("sidecar_sha256") != files[sidecars[0]] or
            meta.get("generation_basename") != sidecars[0].rsplit("/", 1)[-1]):
        raise Refusal("Release Master, sidecar and manifest disagree")
    return sidecars[0]


def _validate_inventory(files, stage):
    name = "scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json"
    sig = name[:-5] + ".sig"
    if name not in files or sig not in files:
        raise Refusal("Signed software inventory is absent")
    inventory = _read_json(stage / Path(*name.split("/")))
    rows = inventory.get("files")
    if not isinstance(rows, list) or len(rows) != release.INVENTORY_ENTRIES:
        raise Refusal("Unexpected software inventory")
    for item in rows:
        rel = item.get("path")
        if rel not in files or files[rel] != item.get("sha256") or (stage / Path(*rel.split("/"))).stat().st_size != item.get("byte_length"):
            raise Refusal("Release software inventory differs from payload")


def _manager_source(helper_hash):
    # Keep every name local: SFM executes Scripts-menu code in a shared namespace.
    text = '''# -*- coding: ascii -*-
def _sct_manage_installation_v1():
    import ctypes
    import hashlib
    import os
    import subprocess
    import sys
    buf = ctypes.create_unicode_buffer(32768)
    used = ctypes.windll.kernel32.GetModuleFileNameW(None, buf, len(buf))
    if not used or used >= len(buf):
        sys.stdout.write("SFM installation location could not be determined.\\n")
        return
    sfm_exe = buf.value
    game = os.path.dirname(sfm_exe)
    if os.path.basename(sfm_exe).lower() != "sfm.exe" or not os.path.isdir(os.path.join(game, "usermod")):
        sys.stdout.write("This script must run from the intended SFM installation.\\n")
        return
    helper = os.path.join(game, "usermod", "tools", "SFM Character Tools Installer", "SCT_Setup.exe")
    if not os.path.isfile(helper):
        sys.stdout.write("SFM Character Tools setup is missing.\\n")
        return
    h = hashlib.sha256()
    with open(helper, "rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    if h.hexdigest() != "%(sha)s":
        sys.stdout.write("SFM Character Tools setup has changed; refusing to launch.\\n")
        return
    subprocess.Popen([helper, "--game", game, "--manage"], cwd=os.path.dirname(helper),
                     close_fds=True, creationflags=0x00000008 | 0x00000200)
try:
    _sct_manage_installation_v1()
finally:
    del _sct_manage_installation_v1
''' % {"sha": helper_hash}
    return text.encode("ascii")


class Prepared:
    def __init__(self, root, files, sidecar, version=release.VERSION, package=release.SHA256):
        self.root = Path(root)
        self.files = files
        self.sidecar = sidecar
        self.version = version
        self.package = package

    def close(self):
        shutil.rmtree(self.root)


def prepare(release_zip, helper_exe):
    """Pin and extract source bytes outside Workshop before the user closes SFM."""
    if digest_file(release_zip) != RELEASE_SHA256:
        raise Refusal("The Workshop release ZIP is not the approved v1.0.0 artifact")
    helper_hash = digest_file(helper_exe)
    root = Path(tempfile.mkdtemp(prefix="sct_workshop_setup_"))
    try:
        snapshot = root / release.ARCHIVE
        shutil.copyfile(release_zip, snapshot)
        if digest_file(snapshot) != RELEASE_SHA256:
            raise Refusal("The release changed during snapshot")
        stage = root / "data"
        stage.mkdir()
        files = {}
        names = set()
        with zipfile.ZipFile(snapshot) as z:
            if len(z.infolist()) != release.ARCHIVE_ENTRIES:
                raise Refusal("Unexpected release ZIP entry count")
            for info in z.infolist():
                _zip_member_kind(info)
                rel = _map_member(info.filename)
                if rel is None:
                    continue
                _validate_rel(rel)
                folded = rel.casefold()
                if folded in names:
                    raise Refusal("Case-insensitive duplicate ZIP destination")
                names.add(folded)
                dst = stage / Path(*rel.split("/"))
                dst.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as source, open(dst, "xb") as out:
                    shutil.copyfileobj(source, out, 1024 * 1024)
                files[rel] = digest_file(dst)
        if set(files) != set(release.PATHS) or any(files.get(p) != h for p, h in BUTTON_HASHES.items()):
            raise Refusal("Release file set or button pair differs")
        sidecar = _validate_authority(files, stage)
        _validate_inventory(files, stage)
        helper_target = stage / Path(*HELPER.split("/"))
        helper_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(helper_exe, helper_target)
        if digest_file(helper_target) != helper_hash:
            raise Refusal("Setup helper changed during snapshot")
        files[HELPER] = helper_hash
        manager_target = stage / Path(*MANAGER.split("/"))
        manager_target.parent.mkdir(parents=True, exist_ok=True)
        manager_target.write_bytes(_manager_source(helper_hash))
        files[MANAGER] = digest_file(manager_target)
        return Prepared(root, files, sidecar)
    except Exception:
        shutil.rmtree(root)
        raise


def _state_path(game, *parts):
    """Validate every installer-state component, including journal and backup paths."""
    return _target(game, "/".join((STATE_REL,) + parts))


def _state_root(game):
    return _state_path(game)


class ProcessRefusal(Refusal):
    """Preserve process-check evidence without parsing user-facing prose."""
    def __init__(self, status, detail):
        self.status, self.detail = status, detail
        super().__init__("SFM process check: %s (%s)" % (status, detail))


def _process_clear():
    status, detail = process_status(no_window=True)
    if status != "CLEAR":
        raise ProcessRefusal(status, detail)


def _updater_records_clear(game):
    layout = Layout(str(game / "usermod" / "cfg"))
    _plain(Path(layout.txroot))
    if not Path(layout.txroot).exists():
        return
    for entry in sorted(os.listdir(layout.txroot)):
        if not TXID_RE.match(entry):
            raise Refusal("Unrecognized updater transaction; run updater recovery first")
        txdir = Path(layout.txroot) / entry
        for path in (txdir, txdir / "intent.json", txdir / "journal"):
            _plain(path)
        if (updater_journal.intent_schema(layout, entry) != updater_journal.SCHEMA or
                updater_journal.transaction_status(layout, entry) not in updater_journal.TERMINAL):
            raise Refusal("Unresolved updater transaction; run updater recovery first")


class _Lock:
    def __init__(self, game):
        self.game = game
        self.handle = None

    def __enter__(self):
        cfg = self.game / "usermod" / "cfg"
        if not cfg.is_dir():
            raise Refusal("SFM usermod/cfg is unavailable")
        lock_dir = cfg / "sfm_character_tools_updater"
        _plain(lock_dir)
        lock_dir.mkdir(exist_ok=True)
        path = lock_dir / "installation.lock"
        _plain(path)
        self.handle, err = w32.create_file(str(path), w32.GENERIC_READ | w32.GENERIC_WRITE,
                                            0, w32.OPEN_ALWAYS, inherit=False)
        if self.handle is None:
            raise Refusal("Control Group Updater installation lock is busy (%s)" % w32.ename(err))
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle is not None:
            w32.close(self.handle)
            self.handle = None



# Paths in these dedicated program namespaces may be retained from a prior receipt.
# No directory walk is used to infer ownership.
PROGRAM_ROOTS = (
    "scripts/ChadChan3D_CPM/", "scripts/SFM Character Tools/",
    "scripts/sfm/mainmenu/SFM Character Tools/", "tools/SFM Control Group Updater/",
    "tools/SFM Character Tools Installer/",
)


def _program_path(rel):
    _validate_rel(rel)
    return (rel in (BUTTON, BUTTON + "c", BUTTON + "o") or
            any(rel.startswith(root) for root in PROGRAM_ROOTS))


def _derived(paths):
    return {p + suffix for p in paths if p.endswith(".py") for suffix in ("c", "o")}


def _authority_paths(prepared):
    return {MASTER, MANIFEST, prepared.sidecar}


def _recognized_sidecars(game):
    root = _target(game, AUTH_DIR)
    if not root.exists():
        return set()
    if not root.is_dir():
        raise Refusal("The sidecar location is not a directory")
    return {AUTH_DIR + "/" + p.name for p in root.iterdir()
            if AUTH_RE.fullmatch(AUTH_DIR + "/" + p.name)}


def _receipt_paths(record):
    return set(record["programs"]) if record else set()


def _current_record(game):
    path = _state_path(game, "installation.json")
    if not path.exists():
        return None
    record = _read_json(path)
    if record.get("schema") != STATE_SCHEMA:
        raise Refusal("Unrecognized installation record; no files were changed")
    paths = record.get("programs")
    if (not isinstance(paths, list) or len(paths) > 10000 or
            len(set(paths)) != len(paths) or not all(_program_path(p) for p in paths)):
        raise Refusal("Invalid installation file list")
    if not _hash_value(record.get("package")) or not isinstance(record.get("version"), str):
        raise Refusal("Invalid installation identity")
    return record


def _hash_value(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _operation(game):
    path = _state_path(game, "operation.json")
    if not path.exists():
        return None
    record = _read_json(path)
    if (record.get("schema") != STATE_SCHEMA or record.get("kind") not in ("install", "uninstall") or
            not TXID_RE.fullmatch(record.get("id", ""))):
        raise Refusal("Unrecognized unfinished setup operation")
    entries = record.get("entries")
    if not isinstance(entries, list) or len(entries) > 20000:
        raise Refusal("Invalid unfinished file list")
    seen = set()
    for e in entries:
        p = e.get("path")
        _validate_rel(p)
        if (p.casefold() in seen or
                not (_program_path(p) or p in (MASTER, MANIFEST) or AUTH_RE.fullmatch(p)) or
                any(v is not None and not _hash_value(v) for v in (e.get("old"), e.get("new")))):
            raise Refusal("Invalid unfinished file entry")
        seen.add(p.casefold())
        if record["kind"] == "uninstall" and (p == MASTER or e.get("new") is not None):
            raise Refusal("Invalid removal operation")
    if record["kind"] == "install":
        if not _hash_value(record.get("package")):
            raise Refusal("Invalid unfinished package identity")
        backup = record.get("backup")
        if backup is not None:
            if (not isinstance(backup, dict) or
                    not re.fullmatch(r"Animation Groups - [0-9TZ-]+ - [0-9a-f]{8}\.txt", backup.get("name", "")) or
                    not _hash_value(backup.get("sha256"))):
                raise Refusal("Invalid Animation Groups backup record")
        master = next((e for e in entries if e["path"] == MASTER), None)
        if master is None or (master["old"] is not None and
                              (backup is None or backup["sha256"] != master["old"])):
            raise Refusal("Missing original Animation Groups backup identity")
    return record


def _legacy_record_clear(game):
    # Pre-release PR candidates used a different rollback contract. Never discard
    # one of those unfinished operations or reinterpret its backups as this policy.
    path = _state_path(game, "transaction.json")
    if path.exists():
        raise Refusal("An earlier experimental Setup record exists. Resolve it before using this Setup.")


def _classify(game, prepared):
    prior = _current_record(game)
    programs = {p for p in prepared.files if p not in _authority_paths(prepared)}
    obsolete = (_receipt_paths(prior) | set(release.OBSOLETE)) - programs
    if not all(_program_path(p) for p in programs | obsolete):
        raise Refusal("Package contains an unsupported program location")
    obsolete |= _derived(obsolete)
    obsolete |= _recognized_sidecars(game) - {prepared.sidecar}
    entries = []
    for rel in sorted(set(prepared.files) | obsolete):
        entries.append({"path": rel, "old": _existing_hash(_target(game, rel)),
                        "new": prepared.files.get(rel)})
    return entries, sorted(programs)


def preview(game, prepared):
    game = _validate_game(game)
    _legacy_record_clear(game)
    if _operation(game):
        raise Refusal("An unfinished Setup operation must be completed first.")
    entries, programs = _classify(game, prepared)
    prior = _current_record(game)
    return {"existing": bool(prior or any(e["old"] is not None for e in entries
                                          if _program_path(e["path"]))),
            "installed_version": prior["version"] if prior else None,
            "version": prepared.version, "programs": programs,
            "snapshot": {e["path"]: e["old"] for e in entries}}


def removal_preview(game):
    game = _validate_game(game)
    _legacy_record_clear(game)
    prior = _current_record(game)
    programs = _receipt_paths(prior) | {p for p in release.PATHS
                                       if p not in (MASTER, MANIFEST) and not AUTH_RE.fullmatch(p)}
    programs |= {HELPER, MANAGER} | set(release.OBSOLETE)
    if not all(_program_path(p) for p in programs):
        raise Refusal("Invalid removal file list")
    paths = programs | _derived(programs) | _recognized_sidecars(game) | {MANIFEST}
    return {p: _existing_hash(_target(game, p)) for p in sorted(paths)}


def _put_file(source, destination, previous, temporary=None):
    _plain(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _plain(destination.parent)
    if _existing_hash(destination) != previous:
        raise Refusal("A destination changed during Setup; review it before retrying.")
    if temporary is None:
        fd, tmp = tempfile.mkstemp(prefix=".sct_install_", dir=destination.parent)
    else:
        tmp = str(temporary)
        _plain(temporary)
        # This exact sibling is named by the operation, never a wildcard cleanup.
        if temporary.exists():
            if not temporary.is_file():
                raise Refusal("An installation temporary path is not a regular file")
            temporary.unlink()
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as out, open(source, "rb") as src:
            shutil.copyfileobj(src, out, 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if digest_file(tmp) != digest_file(source):
            raise Refusal("Staged write verification failed")
        if _existing_hash(destination) != previous:
            raise Refusal("A destination changed while its replacement was being prepared.")
        if previous is None:
            os.rename(tmp, destination)
        else:
            os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _remove_if_new(game, rel, expected):
    target = _target(game, rel)
    if _existing_hash(target) != expected:
        raise Refusal("A file changed during removal; review it before retrying.")
    target.unlink()


class _LegacyLock:
    """Hold the actual verified legacy object; never delete a reopened pathname."""
    def __init__(self, game):
        self.path = _target(game, AUTH_DIR + "/publisher.lock")
        self.handle = None

    def __enter__(self):
        if not self.path.exists():
            return self
        h, err = w32.create_file(str(self.path), w32.GENERIC_READ | w32.DELETE, 0,
                                w32.OPEN_EXISTING, flags=0x00200000, inherit=False)
        if h is None:
            raise Refusal("The sidecar publisher lock is in use or unavailable. Close the publisher and retry.")
        self.handle = h
        try:
            tag = (ctypes.c_ulong * 2)()
            if not w32.k32.GetFileInformationByHandleEx(h, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
                raise Refusal("The sidecar publisher lock could not be inspected.")
            info = w32.std_info(h)
            if (tag[0] & (w32.FILE_ATTRIBUTE_DIRECTORY | w32.FILE_ATTRIBUTE_REPARSE_POINT) or
                    info["size"] != 0 or info["links"] != 1 or info["delete_pending"]):
                raise Refusal("The sidecar publisher lock is not a recognized empty lock file.")
            return self
        except Exception:
            w32.close(h)
            self.handle = None
            raise

    def remove(self):
        if self.handle is None:
            if self.path.exists():
                raise Refusal("A sidecar publisher lock appeared during removal. Retry after closing the publisher.")
            return
        delete = ctypes.c_int(1)  # FILE_DISPOSITION_INFO.DeleteFile is a Windows BOOL.
        if not w32.k32.SetFileInformationByHandle(self.handle, 4, ctypes.byref(delete), ctypes.sizeof(delete)):
            raise Refusal("The sidecar publisher lock could not be removed.")
        w32.close(self.handle)
        self.handle = None
        if self.path.exists():
            raise Refusal("The sidecar publisher lock remains; removal is incomplete.")

    def __exit__(self, *args):
        if self.handle is not None:
            w32.close(self.handle)
            self.handle = None


def _check_sources(prepared):
    for rel, wanted in prepared.files.items():
        source = prepared.root / "data" / Path(*rel.split("/"))
        if digest_file(source) != wanted:
            raise Refusal("The captured installation package changed.")
    _validate_authority(prepared.files, prepared.root / "data")
    _validate_inventory(prepared.files, prepared.root / "data")


def _backup_master(game, expected):
    if expected is None:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    name = "Animation Groups - %s - %s.txt" % (stamp, uuid.uuid4().hex[:8])
    dst = _state_path(game, "backups", name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    _plain(dst)
    src = _target(game, MASTER)
    with open(src, "rb") as source, open(dst, "xb") as out:
        shutil.copyfileobj(source, out, 1024 * 1024)
        out.flush()
        os.fsync(out.fileno())
    if digest_file(dst) != expected or _existing_hash(src) != expected:
        raise Refusal("Animation Groups changed during backup; no installation files were changed.")
    return {"name": name, "sha256": expected}


def _verify_backup(game, record):
    backup = record.get("backup")
    if backup:
        path = _state_path(game, "backups", backup["name"])
        if _existing_hash(path) != backup["sha256"]:
            raise Refusal("The original Animation Groups backup is missing or changed. Setup cannot continue.")


def _matches_snapshot(entries, expected):
    if expected is None or {e["path"]: e["old"] for e in entries} != expected:
        raise Refusal("Installation files changed since consent. Review the installation again.")


def _resume_states(game, record):
    # Inspect the full operation before further writes. No guesses about new edits.
    for e in record["entries"]:
        current = _existing_hash(_target(game, e["path"]))
        if current not in (e["old"], e["new"]):
            raise RecoveryConflict(e["path"])


def _clean_dirs(game, paths):
    dirs = set()
    base = game / "usermod"
    shared = {base / p for p in ("cfg", "scripts", "scripts/sfm", "scripts/sfm/mainmenu", "scripts/sfm/autoinit", "scripts/sfm/autoinit/ChadChan3D", "tools")}
    for rel in paths:
        parent = _target(game, rel).parent
        while parent != base and parent not in shared:
            dirs.add(parent)
            parent = parent.parent
    remaining = []
    for p in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        _plain(p)
        try:
            p.rmdir()
        except FileNotFoundError:
            pass
        except OSError:
            # Nonempty or locked directories are never recursively removed.
            if p.exists():
                remaining.append(p.relative_to(base).as_posix())
    return remaining


def _finish_install(game, prepared, record):
    if record["package"] != prepared.package or record["files"] != prepared.files:
        raise Refusal("Setup needs the exact package used for this unfinished installation.")
    if (not set(prepared.files).issubset({e["path"] for e in record["entries"]}) or
            any(e["new"] != prepared.files.get(e["path"]) for e in record["entries"]) or
            set(record["programs"]) != set(prepared.files) - _authority_paths(prepared)):
        raise Refusal("The unfinished operation does not match the required package.")
    _check_sources(prepared)
    _verify_backup(game, record)
    _resume_states(game, record)
    _process_clear()
    order = sorted(record["entries"], key=lambda e: (
        0 if e["path"] == HELPER else 1 if e["path"] == MANAGER else
        3 if e["path"] == MANIFEST else 2, e["path"]))
    for index, e in enumerate(order):
        target = _target(game, e["path"])
        current = _existing_hash(target)
        temporary = target.with_name(".sct_%s_%d.tmp" % (record["id"][:8], index))
        _plain(temporary)
        if current == e["new"]:
            if temporary.exists():
                temporary.unlink()
            continue
        if e["new"] is None:
            _remove_if_new(game, e["path"], e["old"])
        else:
            _put_file(prepared.root / "data" / Path(*e["path"].split("/")), target, e["old"], temporary)
    for e in record["entries"]:
        if _existing_hash(_target(game, e["path"])) != e["new"]:
            raise Refusal("Installation verification failed; run Setup again to complete it.")
    # Validate the installed authority set itself, not merely the captured input.
    _validate_authority(prepared.files, game / "usermod")
    _clean_dirs(game, [e["path"] for e in record["entries"] if e["new"] is None])
    installed = {"schema": STATE_SCHEMA, "version": record["version"],
                 "package": record["package"], "programs": record["programs"]}
    _write_json(_state_path(game, "installation.json"), installed)
    _state_path(game, "operation.json").unlink()
    return {"backup": record.get("backup"), "version": record["version"]}


def install(game, prepared, expected_snapshot):
    game = _validate_game(game)
    _legacy_record_clear(game)
    _check_sources(prepared)
    _process_clear()
    with _Lock(game), _LegacyLock(game):
        _process_clear()
        _updater_records_clear(game)
        if _operation(game):
            raise Refusal("Finish the interrupted Setup operation before starting another.")
        entries, programs = _classify(game, prepared)
        _matches_snapshot(entries, expected_snapshot)
        master = next(e for e in entries if e["path"] == MASTER)
        backup = _backup_master(game, master["old"])
        # Recheck all consented destinations after the backup, before program writes.
        _matches_snapshot(_classify(game, prepared)[0], expected_snapshot)
        record = {"schema": STATE_SCHEMA, "kind": "install", "id": uuid.uuid4().hex,
                  "package": prepared.package, "version": prepared.version,
                  "files": dict(prepared.files), "programs": programs,
                  "backup": backup, "entries": entries}
        _write_json(_state_path(game, "operation.json"), record)
        return _finish_install(game, prepared, record)


def recover(game, prepared):
    game = _validate_game(game)
    _legacy_record_clear(game)
    _process_clear()
    with _Lock(game), _LegacyLock(game):
        _process_clear()
        _updater_records_clear(game)
        record = _operation(game)
        if not record or record["kind"] != "install":
            raise Refusal("There is no unfinished installation to complete.")
        return _finish_install(game, prepared, record)


def _running_helper(game):
    return os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(str(_target(game, HELPER)))


def uninstall(game, expected_snapshot=None):
    game = _validate_game(game)
    _legacy_record_clear(game)
    _process_clear()
    with _Lock(game), _LegacyLock(game) as legacy:
        _process_clear()
        _updater_records_clear(game)
        record = _operation(game)
        if record and record["kind"] != "uninstall":
            raise Refusal("Complete the interrupted installation before uninstalling.")
        if not record:
            snapshot = removal_preview(game)
            if expected_snapshot is None or snapshot != expected_snapshot:
                raise Refusal("Installation files changed since consent. Review removal again.")
            entries = [{"path": p, "old": h, "new": None} for p, h in snapshot.items()]
            record = {"schema": STATE_SCHEMA, "kind": "uninstall", "id": uuid.uuid4().hex,
                      "entries": entries}
            _write_json(_state_path(game, "operation.json"), record)
        _resume_states(game, record)
        # New generations appearing after consent must not silently escape removal.
        known = {e["path"] for e in record["entries"]}
        if _recognized_sidecars(game) - known:
            raise Refusal("Sidecar files changed since removal was approved.")
        _process_clear()
        entries = sorted(record["entries"], key=lambda e: (
            2 if e["path"] == MANAGER else 1 if e["path"] == HELPER else 0, e["path"]))
        leftover = []
        for e in entries:
            if e["path"] in (MANAGER, HELPER):
                continue
            current = _existing_hash(_target(game, e["path"]))
            if current is None:
                continue
            _remove_if_new(game, e["path"], e["old"])
        # A failed publisher cleanup must leave BOTH management files usable.
        legacy.remove()
        for e in entries:
            if e["path"] not in (MANAGER, HELPER) and _existing_hash(_target(game, e["path"])) is not None:
                raise Refusal("Removal verification failed.")
        # Substantive removal is verified. Remove the menu entry, then clean up
        # Setup itself when possible. A running/locked EXE is reported explicitly.
        manager = next((e for e in entries if e["path"] == MANAGER), None)
        if manager and _existing_hash(_target(game, MANAGER)) is not None:
            _remove_if_new(game, MANAGER, manager["old"])
        helper = next((e for e in entries if e["path"] == HELPER), None)
        if helper and _existing_hash(_target(game, HELPER)) is not None:
            if _running_helper(game):
                leftover.append(HELPER)
            else:
                try:
                    _remove_if_new(game, HELPER, helper["old"])
                except PermissionError:
                    leftover.append(HELPER)
        remaining_dirs = _clean_dirs(game, known | {AUTH_DIR + "/publisher.lock"})
        installation = _state_path(game, "installation.json")
        if installation.exists():
            installation.unlink()
        _state_path(game, "operation.json").unlink()
        # Only installer records are removed; backups and unknown files remain.
        _clean_dirs(game, [STATE_REL + "/operation.json"])
        auth = _target(game, AUTH_DIR)
        remaining = sorted(p.name for p in auth.iterdir()) if auth.exists() else []
        return {"remaining_helper": leftover, "authority_remaining": remaining,
                "remaining_directories": remaining_dirs}
