"""Fixed-payload installation and recovery. All destination writes require SFM to be closed.

The existing updater owns the installation lock and its own transaction records.
This installer uses the same lock but keeps a separate journal and backups.
"""
import hashlib
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


RELEASE_SHA256 = "5323b1431a200c0bea3641e7dcb2f9fac45920d889f749ac9bf07972f5a89458"
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
STATE_SCHEMA = "sct-workshop-install-1"


class Refusal(RuntimeError):
    """A safe, expected refusal with no success claim."""


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


def _append_step(path, phase, rel):
    """Durably identify each intended and completed file mutation."""
    line = (json.dumps({"phase": phase, "path": rel}, sort_keys=True) + "\n").encode("utf-8")
    with open(path, "ab") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def _plain(path):
    """Reject Windows reparse points in existing target ancestors and files."""
    path = Path(path)
    for p in (path, *path.parents):
        if p.exists() or p.is_symlink():
            st = p.lstat()
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


def _check_autoinit(game):
    """Source discovery is supported in both the Workshop and usermod trees."""
    for mod in ("workshop", "usermod"):
        root = game / mod / "scripts" / "sfm"
        manager = root / "autoinit" / "autoinit_manager.py"
        startup = root / "sfm_init_local.py"
        menu = root / "mainmenu" / "kiwifruitdev" / "autoinit_manager.py"
        if manager.is_file() and startup.is_file() and menu.is_file():
            _plain(manager)
            _plain(startup)
            _plain(menu)
            return True
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
    if not isinstance(rows, list) or len(rows) != 31:
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
    def __init__(self, root, files, sidecar):
        self.root = Path(root)
        self.files = files
        self.sidecar = sidecar

    def close(self):
        shutil.rmtree(self.root)


def prepare(release_zip, helper_exe):
    """Pin and extract source bytes outside Workshop before the user closes SFM."""
    if digest_file(release_zip) != RELEASE_SHA256:
        raise Refusal("The Workshop release ZIP is not the approved v1.0.0 artifact")
    helper_hash = digest_file(helper_exe)
    root = Path(tempfile.mkdtemp(prefix="sct_workshop_setup_"))
    try:
        snapshot = root / "SFM.Character.Tools.v1.0.0.zip"
        shutil.copyfile(release_zip, snapshot)
        if digest_file(snapshot) != RELEASE_SHA256:
            raise Refusal("The release changed during snapshot")
        stage = root / "data"
        stage.mkdir()
        files = {}
        names = set()
        with zipfile.ZipFile(snapshot) as z:
            if len(z.infolist()) != 1006:
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
        if len(files) != 1004 or any(files.get(p) != h for p, h in BUTTON_HASHES.items()):
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


def _state_root(game):
    return game / "usermod" / Path(*STATE_REL.split("/"))


def _authority_paths(prepared):
    return {MASTER, MANIFEST, prepared.sidecar}


def _classify(game, prepared, replace_authority):
    auth = game / "usermod" / Path(*AUTH_DIR.split("/"))
    old_sidecars = []
    if auth.exists():
        _plain(auth)
        for entry in auth.iterdir():
            if entry.name.endswith(".sfmsidecar") and entry.name != prepared.sidecar.rsplit("/", 1)[-1]:
                old_sidecars.append(AUTH_DIR + "/" + entry.name)
    if len(old_sidecars) > 1:
        raise Refusal("Multiple existing sidecars require manual review")
    button_exists = [_target(game, p).exists() for p in BUTTON_HASHES]
    if any(button_exists) and not all(button_exists):
        raise Refusal("Only one CPM button file exists; refusing a partial replacement")
    for p in BUTTON_HASHES:
        if _existing_hash(_target(game, p)) not in (None, BUTTON_HASHES[p]):
            raise Refusal("A CPM button file has been modified or is foreign")
    authority = _authority_paths(prepared)
    entries = []
    authority_changed = False
    for rel in sorted(set(prepared.files) | set(old_sidecars)):
        new_hash = prepared.files.get(rel)
        old = _existing_hash(_target(game, rel))
        if rel in authority or rel in old_sidecars:
            authority_changed |= old not in (None, new_hash)
        elif old not in (None, new_hash):
            raise Refusal("Existing software differs from the approved release: %s" % rel)
        entries.append({"path": rel, "old": old, "new": new_hash,
                        "adopted": old == new_hash})
    if authority_changed and not replace_authority:
        raise Refusal("Existing Animation Groups data needs explicit replacement consent")
    return entries, authority_changed


def preview(game, prepared):
    game = _validate_game(game)
    if not _check_autoinit(game):
        raise Refusal("Autoinit Manager is not verifiably installed; all four components are required")
    # Preview may run while SFM is open; it does not create an installation lock or modify files.
    entries, authority_changed = _classify(game, prepared, True)
    return {"game": str(game), "file_count": len(entries),
            "write_count": sum(not e["adopted"] for e in entries),
            "authority_replacement_needs_consent": authority_changed}


def _process_clear():
    status, detail = process_status()
    if status != "CLEAR":
        raise Refusal("SFM must be closed and its process check readable (%s)" % status)


def _updater_records_clear(game):
    layout = Layout(str(game / "usermod" / "cfg"))
    if not Path(layout.txroot).exists():
        return
    for entry in sorted(os.listdir(layout.txroot)):
        if not TXID_RE.match(entry):
            raise Refusal("Unrecognized updater transaction; run updater recovery first")
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


def _current_record(game):
    path = _state_root(game) / "transaction.json"
    if not path.exists():
        return None
    record = _read_json(path)
    if record.get("schema") != STATE_SCHEMA or record.get("status") not in (
            "PREPARED", "COMPLETE", "ROLLED_BACK", "UNINSTALLING", "UNINSTALLED"):
        raise Refusal("Unknown installer transaction; manual review required")
    if not TXID_RE.match(record.get("id", "")):
        raise Refusal("Invalid installer transaction identity")
    entries = record.get("entries")
    if not isinstance(entries, list) or len(entries) > 1007:
        raise Refusal("Invalid installer transaction entries")
    seen = set()
    for entry in entries:
        rel = entry.get("path")
        _validate_rel(rel)
        if rel in seen or not all(x is None or re.match(r"^[0-9a-f]{64}$", x)
                                       for x in (entry.get("old"), entry.get("new"))):
            raise Refusal("Invalid installer transaction entry")
        seen.add(rel)
    return record


def _put_file(source, destination, previous):
    _plain(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _plain(destination.parent)
    now = _existing_hash(destination)
    if now != previous:
        raise Refusal("Destination changed during installation")
    fd, tmp = tempfile.mkstemp(prefix=".sct_install_", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as out, open(source, "rb") as src:
            shutil.copyfileobj(src, out, 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if digest_file(tmp) != digest_file(source):
            raise Refusal("Staged write verification failed")
        if previous is None:
            # On Windows rename refuses an existing destination rather than replacing it.
            os.rename(tmp, destination)
        else:
            os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _remove_if_new(game, rel, new_hash):
    target = _target(game, rel)
    if _existing_hash(target) != new_hash:
        raise Refusal("A file changed after installation; preserving it")
    target.unlink()


def _restore(game, record):
    """Idempotent rollback; inspect every destination before changing any of them."""
    txdir = _state_root(game) / "transactions" / record["id"]
    jobs = []
    for e in record["entries"]:
        if e["adopted"]:
            continue
        rel = e["path"]
        current = _existing_hash(_target(game, rel))
        if current not in (e["old"], e["new"]):
            raise Refusal("Rollback refused: a destination changed after interruption")
        if e["old"] is not None:
            backup = txdir / "backups" / Path(*rel.split("/"))
            if not backup.is_file() or digest_file(backup) != e["old"]:
                raise Refusal("Rollback refused: verified backup missing")
        jobs.append((e, current))
    for e, current in reversed(jobs):
        if current == e["old"]:
            continue
        if e["old"] is None:
            _remove_if_new(game, e["path"], e["new"])
        else:
            source = txdir / "backups" / Path(*e["path"].split("/"))
            _put_file(source, _target(game, e["path"]), e["new"])
    for e, _ in jobs:
        if _existing_hash(_target(game, e["path"])) != e["old"]:
            raise Refusal("Rollback verification failed")


def recover(game):
    game = _validate_game(game)
    _process_clear()
    with _Lock(game):
        _process_clear()
        _updater_records_clear(game)
        record = _current_record(game)
        if record is None or record["status"] != "PREPARED":
            raise Refusal("There is no incomplete installer transaction")
        _restore(game, record)
        record["status"] = "ROLLED_BACK"
        _write_json(_state_root(game) / "transaction.json", record)
    return "Previous files restored and verified"


def install(game, prepared, replace_authority=False):
    game = _validate_game(game)
    if not _check_autoinit(game):
        raise Refusal("Autoinit Manager is not verifiably installed")
    _process_clear()
    with _Lock(game):
        _process_clear()
        _updater_records_clear(game)
        prior = _current_record(game)
        if prior and prior["status"] == "PREPARED":
            raise Refusal("An incomplete installer transaction must be recovered first")
        if prior and prior["status"] == "UNINSTALLING":
            raise Refusal("Complete the interrupted removal before installing")
        if prior and prior["status"] == "COMPLETE":
            raise Refusal("Already installed; verify or uninstall before installing again")
        entries, authority_changed = _classify(game, prepared, replace_authority)
        if authority_changed and not replace_authority:
            raise Refusal("Animation Groups replacement was not authorized")
        # Recheck the captured source before creating a transaction.
        for rel, wanted in prepared.files.items():
            source = prepared.root / "data" / Path(*rel.split("/"))
            if digest_file(source) != wanted:
                raise Refusal("Captured installation source changed")
        _validate_authority(prepared.files, prepared.root / "data")
        _validate_inventory(prepared.files, prepared.root / "data")
        txid = uuid.uuid4().hex
        root = _state_root(game)
        txdir = root / "transactions" / txid
        txdir.mkdir(parents=True)
        for e in entries:
            if e["old"] is None or e["adopted"]:
                continue
            src = _target(game, e["path"])
            dst = txdir / "backups" / Path(*e["path"].split("/"))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            if digest_file(dst) != e["old"] or digest_file(src) != e["old"]:
                raise Refusal("A destination changed while creating its backup")
        record = {"schema": STATE_SCHEMA, "id": txid, "status": "PREPARED",
                  "release_sha256": RELEASE_SHA256, "authority_replaced": authority_changed,
                  "entries": entries}
        _write_json(root / "transaction.json", record)
        try:
            # Make unsubscribe-independent management available as early as
            # possible in a partially completed installation.
            write_order = [e for e in entries if e["path"] in (HELPER, MANAGER)]
            write_order += [e for e in entries if e["path"] not in (HELPER, MANAGER)]
            for e in write_order:
                if e["adopted"]:
                    continue
                _append_step(txdir / "steps.jsonl", "BEFORE", e["path"])
                if e["new"] is None:
                    _remove_if_new(game, e["path"], e["old"])
                else:
                    source = prepared.root / "data" / Path(*e["path"].split("/"))
                    if digest_file(source) != e["new"]:
                        raise Refusal("Transaction-local source changed")
                    _put_file(source, _target(game, e["path"]), e["old"])
                _append_step(txdir / "steps.jsonl", "AFTER", e["path"])
            for e in entries:
                if _existing_hash(_target(game, e["path"])) != e["new"]:
                    raise Refusal("Post-install file verification failed")
            _validate_authority(prepared.files, prepared.root / "data")
            record["status"] = "COMPLETE"
            _write_json(root / "transaction.json", record)
        except Exception:
            # A crash leaves PREPARED for a later explicit recovery. This immediate
            # rollback is safe only while the same lock is still held.
            try:
                _restore(game, record)
                record["status"] = "ROLLED_BACK"
                _write_json(root / "transaction.json", record)
            except Exception:
                pass
            raise
    return "Installed and verified all four components"


def verify(game):
    game = _validate_game(game)
    record = _current_record(game)
    if not record or record["status"] != "COMPLETE":
        raise Refusal("There is no completed managed installation")
    mismatches = [e["path"] for e in record["entries"]
                  if _existing_hash(_target(game, e["path"])) != e["new"]]
    return {"files": len(record["entries"]), "mismatches": mismatches}


def uninstall(game):
    game = _validate_game(game)
    _process_clear()
    with _Lock(game):
        _process_clear()
        _updater_records_clear(game)
        record = _current_record(game)
        if not record or record["status"] not in ("COMPLETE", "UNINSTALLING"):
            raise Refusal("There is no completed managed installation")
        txdir = _state_root(game) / "transactions" / record["id"]
        authority = {MASTER, MANIFEST} | {e["path"] for e in record["entries"] if AUTH_RE.match(e["path"])}
        button = set(BUTTON_HASHES)
        if record["status"] == "COMPLETE":
            changed_auth = any(_existing_hash(_target(game, e["path"])) != e["new"]
                               for e in record["entries"] if e["path"] in authority)
            changed_button = any(_existing_hash(_target(game, e["path"])) != e["new"]
                                 for e in record["entries"] if e["path"] in button)
            record["preserve_authority"] = changed_auth
            record["preserve_button"] = changed_button
            record["status"] = "UNINSTALLING"
            _write_json(_state_root(game) / "transaction.json", record)
        else:
            changed_auth = record["preserve_authority"]
            changed_button = record["preserve_button"]
            for e in record["entries"]:
                if _existing_hash(_target(game, e["path"])) not in (e["old"], e["new"]):
                    raise Refusal("An installation file changed during removal; manual review required")
        # An interrupted removal is retried from the durable UNINSTALLING state.
        preserved = []
        removal_order = [e for e in reversed(record["entries"]) if e["path"] != MANAGER]
        removal_order += [e for e in record["entries"] if e["path"] == MANAGER]
        for e in removal_order:
            rel = e["path"]
            if e["adopted"]:
                continue
            if (rel in authority and changed_auth) or (rel in button and changed_button):
                preserved.append(rel)
                continue
            current = _existing_hash(_target(game, rel))
            if current == e["old"]:
                continue
            if current != e["new"]:
                preserved.append(rel)
                continue
            if e["old"] is None:
                # The helper executing from this path must remain on disk. A later
                # management action can remove it after the user closes the helper.
                if rel == HELPER:
                    preserved.append(rel)
                    continue
                _append_step(txdir / "removal_steps.jsonl", "BEFORE", rel)
                _remove_if_new(game, rel, e["new"])
                _append_step(txdir / "removal_steps.jsonl", "AFTER", rel)
            else:
                backup = txdir / "backups" / Path(*rel.split("/"))
                if not backup.is_file() or digest_file(backup) != e["old"]:
                    preserved.append(rel)
                    continue
                _append_step(txdir / "removal_steps.jsonl", "BEFORE", rel)
                _put_file(backup, _target(game, rel), e["new"])
                _append_step(txdir / "removal_steps.jsonl", "AFTER", rel)
        record["status"] = "UNINSTALLED"
        record["preserved"] = sorted(preserved)
        _write_json(_state_root(game) / "transaction.json", record)
    return {"preserved": sorted(preserved)}
