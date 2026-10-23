# -*- coding: utf-8 -*-
"""Build the optional CPM Quick Launch ZIP from the repository, deterministically.

usage: py -3 make_quick_launch_archive.py OUT.zip

The archive contains exactly, under one root folder:
  README.txt, SHA256SUMS.txt and the two program files at their installed paths
  (usermod/...). Program bytes must equal quick_launch_component_v1.json; nothing else is added.
Entries are stored (no compression) in a fixed order with a fixed timestamp and permissions, so the same
repository content always gives the same archive bytes. Refuses to overwrite OUT.
"""
import hashlib
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
RECORD = os.path.join(HERE, "quick_launch_component_v1.json")
README = os.path.join(HERE, "README.txt")
FIXED_TIME = (2026, 10, 22, 0, 0, 0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fail(message):
    raise SystemExit("REFUSED: " + message)


def entries():
    """[(archive path, bytes)] in archive order, after every identity check."""
    record = json.load(open(RECORD, encoding="utf-8"))
    root = record["distribution"]["archive_root"]
    if record["core_inventory"].split(":")[0] != "NOT LISTED":
        fail("the component must stay outside the core inventory")
    readme = open(README, "rb").read()
    text = readme.decode("ascii")
    if b"\r" in readme:
        fail("README.txt must be LF-only")
    files = []
    for f in record["files"]:
        data = open(os.path.join(REPO, *f["source"].split("/")), "rb").read()
        if len(data) != f["byte_length"] or sha(data) != f["sha256"]:
            fail("%s does not match the recorded QL-2 identity" % f["source"])
        windows_path = "game\\" + f["installed_path"].replace("/", "\\")
        if windows_path not in text or f["sha256"] not in text:
            fail("README.txt does not state the path and fingerprint of %s" % f["installed_path"])
        files.append((f["installed_path"], data))
    for release in record["known_releases"]:
        for path, digest in release["files"].items():
            if digest not in text:
                fail("README.txt does not list known release %s fingerprint for %s" % (release["version"], path))
    if ("CPM Quick Launch %s" % record["version"]) not in text:
        fail("README.txt version does not match the record")
    sums = "".join("%s  %s\n" % (sha(data), path) for path, data in files).encode("ascii")
    out = [(root + "/README.txt", readme), (root + "/SHA256SUMS.txt", sums)]
    out += [(root + "/" + path, data) for path, data in files]
    return out


def build(path):
    if os.path.exists(path):
        fail("output already exists: %s" % path)
    items = entries()
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as z:
        for name, data in items:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0
            info.external_attr = 0
            z.writestr(info, data)
    data = open(path, "rb").read()
    print("archive %s\n  bytes %d\n  sha256 %s" % (path, len(data), sha(data)))
    for name, content in items:
        print("  %-80s %8d %s" % (name, len(content), sha(content)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(sys.argv[1])
