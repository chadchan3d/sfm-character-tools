# -*- coding: utf-8 -*-
"""Get Official Data, online (L-3; R2 D4-D5): explicit-action GitHub release discovery and bounded
download. This is the product's only network code. It runs only for the worker commands
`check-official` and `download-official`, each started by an explicit user action; nothing here
runs in the background, at import time or from any other command.

Discovery lists the official repository's releases (complete pagination, or "Couldn't check for
updates"), authenticates each data release's signed descriptor with the L-2 verifier and reports
the highest compatible authenticated release that the check found. GitHub's "latest" designation
is never used, and no release is ever called the newest.

Download authenticates the descriptor first, bound to the descriptor the check reported, then
fetches each payload file bounded by its signed byte length and verifies its SHA-256 before
anything is written. The five files then go through the unchanged L-2 path
(backend.prepare_official), which authenticates and validates them again from disk.

Identity is strict: requests go only to the fixed official repository on api.github.com. A redirect
of the listing or of the descriptor/signature metadata (for example GitHub's rename redirect from an
older repository name) is not followed. An asset may redirect exactly once, to a GitHub
release-asset download host. No credentials are sent.
"""
import hashlib
import http.client
import json
import os
import re
import ssl
import time
import uuid
from urllib.parse import urlsplit

from . import VERSION, backend, hooks, official, staging, w32
from .messages import MESSAGES, Stop

API_HOST = "api.github.com"
RELEASES_URL = "https://%s/repos/%s/releases" % (API_HOST, official.REPOSITORY)
_RELEASE_URL = re.compile(r"^%s/(\d{1,20})$" % re.escape(RELEASES_URL))
_ASSET_URL = re.compile(r"^%s/assets/(\d{1,20})$" % re.escape(RELEASES_URL))
DATA_TAG = re.compile(r"^data-v\d{1,6}\.\d{1,6}\.\d{1,6}$")
ASSET_HOSTS = frozenset(("objects.githubusercontent.com", "release-assets.githubusercontent.com",
                         "github-releases.githubusercontent.com"))
PER_PAGE = 100
MAX_PAGES = 10
MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_DATA_RELEASES = 50
TIMEOUT = 30.0
CHECK_DEADLINE = 300.0
DOWNLOAD_DEADLINE = 1800.0
USER_AGENT = "SFM-Character-Tools-Updater/%s" % VERSION
DOWNLOAD_PREFIX = "download-"


class NetFail(Exception):
    def __init__(self, code, **details):
        Exception.__init__(self, code)
        self.code = code
        self.details = details


def sha(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- transport
def _timeout():
    return TIMEOUT if hooks.network_timeout is None else hooks.network_timeout


def _request(url, accept, limit, deadline):
    """One GET; redirects are returned, never followed. Returns (status, headers, body); the body
    is read only for 200 and is bounded by `limit` bytes."""
    target = url if hooks.network_rewrite is None else hooks.network_rewrite(url)
    u = urlsplit(target)
    if u.scheme == "https":
        conn = http.client.HTTPSConnection(u.hostname, u.port or 443, timeout=_timeout(),
                                           context=ssl.create_default_context())
    elif u.scheme == "http" and hooks.network_rewrite is not None:
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=_timeout())
    else:
        raise NetFail("unsupported URL", url=url[:200])
    try:
        conn.request("GET", u.path + ("?" + u.query if u.query else ""),
                     headers={"Accept": accept, "User-Agent": USER_AGENT, "X-GitHub-Api-Version": "2022-11-28"})
        r = conn.getresponse()
        headers = {k.lower(): v for k, v in r.getheaders()}
        if r.status != 200:
            return r.status, headers, b""
        cl = headers.get("content-length")
        if cl is not None and (not cl.isdigit() or int(cl) > limit):
            raise NetFail("too large", limit=limit, content_length=cl[:32])
        chunks, n = [], 0
        while True:
            if time.monotonic() > deadline:
                raise NetFail("deadline exceeded")
            b = r.read(min(65536, limit + 1 - n))
            if not b:
                break
            chunks.append(b)
            n += len(b)
            if n > limit:
                raise NetFail("too large", limit=limit)
        body = b"".join(chunks)
        if cl is not None and len(body) != int(cl):
            raise NetFail("truncated", received=len(body), content_length=int(cl))
        return 200, headers, body
    except NetFail:
        raise
    except (OSError, http.client.HTTPException, ssl.SSLError, ValueError) as e:
        raise NetFail("network error", error="%s: %s" % (type(e).__name__, str(e)[:200]))
    finally:
        conn.close()


def _asset(url, limit, deadline):
    """An asset's bytes: its API URL, then at most one redirect to a GitHub release-asset host."""
    if not _ASSET_URL.match(url):
        raise NetFail("asset outside the official repository", url=url[:200])
    st, h, body = _request(url, "application/octet-stream", limit, deadline)
    if st in (301, 302, 303, 307, 308):
        loc = h.get("location", "")
        u = urlsplit(loc)
        if u.scheme != "https" or u.hostname not in ASSET_HOSTS or u.username or u.password or \
                u.port not in (None, 443):
            raise NetFail("asset redirect to an unexpected location", host=(u.hostname or "")[:100])
        st, h, body = _request(loc, "application/octet-stream", limit, deadline)
    if st != 200:
        raise NetFail("asset download failed", status=st)
    return body


# ---------------------------------------------------------------- listing
def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key %r" % k)
        out[k] = v
    return out


def _release(x):
    """The fields used, type-checked; the release and its assets must belong to the official
    repository. Anything else makes the whole listing unusable."""
    try:
        if not _RELEASE_URL.match(x["url"]):
            raise NetFail("release outside the official repository", url=str(x["url"])[:200])
        rel = {"id": x["id"], "tag": x["tag_name"], "draft": x["draft"], "prerelease": x["prerelease"], "assets": []}
        ok = (isinstance(rel["id"], int) and isinstance(rel["tag"], str) and isinstance(rel["draft"], bool)
              and isinstance(rel["prerelease"], bool) and isinstance(x["assets"], list))
        for a in x["assets"] if ok else ():
            if not _ASSET_URL.match(a["url"]):
                raise NetFail("asset outside the official repository", url=str(a["url"])[:200])
            item = {"name": a["name"], "size": a["size"], "url": a["url"], "state": a["state"]}
            ok = ok and isinstance(item["name"], str) and isinstance(item["size"], int) and \
                not isinstance(item["size"], bool) and isinstance(item["state"], str)
            rel["assets"].append(item)
    except (KeyError, TypeError) as e:
        raise NetFail("release listing malformed", error=str(e)[:100])
    if not ok:
        raise NetFail("release listing malformed")
    return rel


def list_releases(deadline):
    """Every release of the official repository, or NetFail: a partial listing is never used."""
    releases = []
    for page in range(1, MAX_PAGES + 1):
        st, h, body = _request("%s?per_page=%d&page=%d" % (RELEASES_URL, PER_PAGE, page),
                               "application/vnd.github+json", MAX_PAGE_BYTES, deadline)
        if st != 200:
            raise NetFail("release listing failed", status=st, page=page)
        try:
            items = json.loads(body.decode("utf-8"), object_pairs_hook=_pairs)
        except (UnicodeDecodeError, ValueError) as e:
            raise NetFail("release listing is not valid JSON", page=page, error=str(e)[:100])
        if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
            raise NetFail("release listing is not a list of releases", page=page)
        releases += [_release(x) for x in items]
        if len(items) < PER_PAGE:
            return releases
    raise NetFail("release listing longer than allowed", pages=MAX_PAGES)


def data_releases(releases):
    """Stable data releases: a data tag, neither draft nor prerelease. Everything else is ignored."""
    return [r for r in releases if DATA_TAG.match(r["tag"]) and not r["draft"] and not r["prerelease"]]


# ---------------------------------------------------------------- authentication
def authenticate(rel, deadline):
    """Download and authenticate a release's descriptor. Returns ({...}, None) for an authenticated
    release whose assets are exactly the signed files, or (None, (message_key, reason, details)).
    Network failures raise NetFail (the query is then incomplete)."""
    names = [a["name"] for a in rel["assets"]]
    if len(set(names)) != len(names):
        return None, ("PACKAGE_INVALID", "duplicate asset names", {})
    by = {a["name"]: a for a in rel["assets"]}
    if official.DESCRIPTOR not in by or official.SIGNATURE not in by:
        return None, ("PACKAGE_INVALID", "descriptor or signature asset missing", {})
    if any(a["state"] != "uploaded" for a in rel["assets"]):
        return None, ("PACKAGE_INVALID", "asset not fully uploaded", {})
    if not 0 < by[official.DESCRIPTOR]["size"] <= official.MAX_DESCRIPTOR_BYTES or by[official.SIGNATURE]["size"] != 64:
        return None, ("PACKAGE_INVALID", "descriptor or signature size invalid", {})
    try:
        db = _asset(by[official.DESCRIPTOR]["url"], official.MAX_DESCRIPTOR_BYTES, deadline)
        sig = _asset(by[official.SIGNATURE]["url"], 64, deadline)
    except NetFail as e:
        if e.code == "too large":
            return None, ("PACKAGE_INVALID", "descriptor or signature larger than allowed", {})
        raise
    try:
        d = official.parse_descriptor(db)
        official.verify_signature(db, sig, d["signing_key_id"])
    except Stop as e:
        return None, (e.message_key, e.details.get("reason", "descriptor refused"),
                      {k: v for k, v in e.details.items() if k != "reason"})
    if d["release_tag"] != rel["tag"]:
        return None, ("PACKAGE_INVALID", "signed release tag differs from the GitHub release tag",
                      {"signed_tag": d["release_tag"]})
    files = d["files"]
    want = {official.DESCRIPTOR, official.SIGNATURE, files["master"]["name"], files["manifest"]["name"],
            files["sidecar"]["name"]}
    if set(by) != want:
        return None, ("PACKAGE_INVALID", "release assets differ from the signed file list",
                      {"unexpected": sorted(set(by) - want), "missing": sorted(want - set(by))})
    for role in ("master", "manifest", "sidecar"):
        if by[files[role]["name"]]["size"] != files[role]["byte_length"]:
            return None, ("PACKAGE_DAMAGED", "asset size differs from the signed length", {"file": files[role]["name"]})
    return {"descriptor": d, "descriptor_bytes": db, "signature": sig, "descriptor_sha256": sha(db), "assets": by}, None


def _summary(rel, auth=None):
    s = {"release_tag": rel["tag"]}
    if auth:
        d = auth["descriptor"]
        s.update(sequence=d["sequence"], data_version=d["data_version"], descriptor_sha256=auth["descriptor_sha256"])
    return s


def _read_log(layout):
    log = official.ReleaseLog(layout)
    try:
        return log.high_water(), {r["sequence"]: log.seen(r["sequence"]) for r in log.records}
    finally:
        log.close()


# ---------------------------------------------------------------- check-official
def check_official(layout):
    """Explicit "check for official data". Reads the release record and the installed TXT;
    writes nothing."""
    res = {"operation": "check-official", "repository": official.REPOSITORY}
    deadline = time.monotonic() + CHECK_DEADLINE
    try:
        listed = list_releases(deadline)
        data = data_releases(listed)
        if len(data) > MAX_DATA_RELEASES:
            raise NetFail("more data releases than allowed", count=len(data))
        checked = [(r,) + authenticate(r, deadline) for r in data]
    except NetFail as e:
        raise Stop("CHECK_FAILED", "CHECK_FAILED", reason=e.code, **e.details)
    res.update(releases_listed=len(listed), data_releases=len(data), releases=[])
    if not data:
        res.update(outcome="NONE_PUBLISHED", message=MESSAGES["NONE_PUBLISHED"])
        return res
    hw, seen = _read_log(layout)
    by_seq = {}
    for rel, auth, why in checked:
        if auth:
            by_seq.setdefault(auth["descriptor"]["sequence"], set()).add(auth["descriptor_sha256"])
    conflicts = sorted(q for q, digests in by_seq.items()
                       if len(digests) > 1 or (seen.get(q) and not digests <= seen[q]))
    compatible, newer_needed, incompatible = [], [], []
    for rel, auth, why in checked:
        s = _summary(rel, auth)
        if why:
            s.update(status="not_offered", message_key=why[0], reason=why[1], **why[2])
        elif auth["descriptor"]["sequence"] in conflicts:
            s.update(status="conflict")
        else:
            try:
                official.check_compatibility(auth["descriptor"])
                s["status"] = "compatible"
                compatible.append((auth["descriptor"]["sequence"], rel, auth))
            except Stop as e:
                s.update(status="needs_newer_updater" if e.message_key == "PACKAGE_NEEDS_NEWER" else "incompatible",
                         reason=e.details.get("reason"))
                (newer_needed if e.message_key == "PACKAGE_NEEDS_NEWER" else incompatible).append(
                    auth["descriptor"]["sequence"])
        res["releases"].append(s)
    res["high_water"] = hw
    if conflicts:
        res.update(outcome="RELEASE_CONFLICT", message=MESSAGES["RELEASE_CONFLICT"], conflicting_sequences=conflicts)
        return res
    best = max(compatible, key=lambda c: c[0]) if compatible else None
    best_seq = best[0] if best else 0
    newer_note = any(q > best_seq for q in newer_needed)
    res["newer_needs_newer_updater"] = newer_note
    if best is None:
        key = ("NEEDS_NEWER_UPDATER" if newer_needed else "OFFICIAL_INCOMPATIBLE" if incompatible
               else "OFFICIAL_UNVERIFIED")
        res.update(outcome=key, message=MESSAGES[key])
        return res
    d = best[2]["descriptor"]
    found = {"release_tag": d["release_tag"], "sequence": d["sequence"], "data_version": d["data_version"],
             "descriptor_sha256": best[2]["descriptor_sha256"]}
    m0 = backend.observe_path(layout.master)
    installed = bool(m0 and m0.get("sha256") == d["files"]["master"]["sha256"])
    if installed:
        res.update(outcome="INSTALLED_CURRENT", message=MESSAGES["INSTALLED_CURRENT"] % d["data_version"],
                   installed_release=found)
    elif d["sequence"] < hw:
        res.update(outcome="OLDER_ONLY", message=MESSAGES["OFFICIAL_OLDER_ONLY"] % d["data_version"],
                   older_release=found)
    else:
        res.update(outcome="AVAILABLE", message=MESSAGES["AVAILABLE"] % d["data_version"], offer=found)
    if newer_note:
        res["message"] = "%s %s" % (res["message"], MESSAGES["NEWER_NEEDS_UPDATER_NOTE"])
    return res


# ---------------------------------------------------------------- download-official
def download_official(layout, release_tag, descriptor_sha, allow_older=False):
    """Explicit "get this official data": the release the check reported (tag and descriptor
    digest), downloaded with every file bounded and verified before it is written, then prepared
    through the unchanged L-2 path. Nothing outside updater-private staging is written."""
    deadline = time.monotonic() + DOWNLOAD_DEADLINE
    try:
        rels = [r for r in data_releases(list_releases(deadline)) if r["tag"] == release_tag]
        if len(rels) != 1:
            raise Stop("REFUSED", "RELEASE_CHANGED", reason="release not found", release_tag=release_tag)
        auth, why = authenticate(rels[0], deadline)
    except NetFail as e:
        raise Stop("REFUSED", "DOWNLOAD_FAILED", reason=e.code, **e.details)
    if why:
        raise Stop("REFUSED", why[0], reason=why[1], **why[2])
    d = auth["descriptor"]
    if auth["descriptor_sha256"] != descriptor_sha:
        raise Stop("REFUSED", "RELEASE_CHANGED", reason="descriptor differs from the one checked",
                   release_tag=release_tag)
    official.check_compatibility(d)
    log = official.ReleaseLog(layout)
    try:
        official.check_sequence(log, d, auth["descriptor_sha256"], allow_older)
    finally:
        log.close()
    payload = []
    try:
        for role in ("master", "manifest", "sidecar"):
            f = d["files"][role]
            body = _asset(auth["assets"][f["name"]]["url"], f["byte_length"], deadline)
            if len(body) != f["byte_length"] or sha(body) != f["sha256"]:
                raise Stop("REFUSED", "PACKAGE_DAMAGED", reason="downloaded file does not match the signed descriptor",
                           file=f["name"])
            payload.append((f["name"], body))
    except NetFail as e:
        if e.code == "too large":
            raise Stop("REFUSED", "PACKAGE_DAMAGED", reason="downloaded file longer than signed", **e.details)
        raise Stop("REFUSED", "DOWNLOAD_FAILED", reason=e.code, **e.details)
    layout.ensure_updater_dirs()
    ddir = os.path.join(layout.staging, DOWNLOAD_PREFIX + uuid.uuid4().hex)
    os.mkdir(ddir)
    for n, data in payload + [(official.DESCRIPTOR, auth["descriptor_bytes"]), (official.SIGNATURE, auth["signature"])]:
        ok, err = w32.write_new_file(os.path.join(ddir, n), data)
        if not ok:
            raise Stop("REFUSED", "NOTHING", reason="download write failed", error=w32.ename(err))
    try:
        res = backend.prepare_official(layout, ddir, allow_older)
    finally:
        # The preparation copies what it needs; the download folder is never used again (L-4).
        kept = staging.remove(layout, os.path.basename(ddir))
    res["download"] = {"repository": official.REPOSITORY, "release_tag": release_tag,
                       "descriptor_sha256": auth["descriptor_sha256"],
                       "folder": os.path.relpath(ddir, layout.cfg), "folder_removed": kept is None,
                       "bytes": sum(len(b) for _, b in payload)}
    return res

