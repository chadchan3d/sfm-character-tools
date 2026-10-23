# -*- coding: utf-8 -*-
"""CPM bounded diagnostic logging -- focused verification.

Design: Astra's adjudication of 2026-10-23 (recorded in
cpm/qualification/CPM_BOUNDED_LOGGING_CORRECTION.md).

Logger units run the actual logger block of the canonical application
(extracted verbatim from cpm/app/SFM_Character_Preset_Manager.py, from
reset_log through prod_log_operation_end) with PROD_LOG_DIR pointed at a
temporary folder. Integration scenarios launch the ACTUAL application through
the R15 harness (real launcher, real module, real ProdWindow; the folder
below C:\\Users is remapped into the fixture), so no real log folder or the
historical log is touched.

Cases (Astra section 4): 1 creation/identification, 2 size boundary,
rotation, retention and truncation, 3 preservation of unrelated and
historical files, 4 failures (unwritable folder, deletion, write, lock
contention) without changing CPM behavior, 5 two concurrent writers,
6 reuse and close/reopen identity, 7 correlated success/refusal/failure.

Usage: <python> -E -B test_cpm_app_bounded_logging.py
       internal: --child=writer|holdlock ...
"""
from __future__ import print_function

import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types

sys.dont_write_bytecode = True
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

PY2 = sys.version_info[0] == 2
PYTHON = sys.executable  # the R15 harness later replaces sys.executable with a fake sfm.exe
_TEXT = unicode if PY2 else str  # noqa: F821
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir, os.pardir, os.pardir))
APP_PATH = os.path.join(_REPO_ROOT, "cpm", "app", "SFM_Character_Preset_Manager.py")
WORK = os.path.join(tempfile.gettempdir(), "cpm_bounded_logging_%d" % sys.version_info[0])
LIMIT_FILE = 2097152
LIMIT_TOTAL = 10485760
LIMIT_RECORD = 65536
NAME_RE = re.compile(r"^CPM - \d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}Z - pid\d+ - [0-9a-f]{6} - \d{3}\.log$")
RECORD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z #(\d{6}) s=([0-9a-f]{6}) w=(\S+) op=(\S+) \| ")
NOTICE = ("CPM couldn't write its diagnostic log. You can keep using the tool. "
          "If you need troubleshooting help, check that the log folder is writable.")
RESULTS = []
SAMPLES = {}


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def fresh(path):
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for n in files:
                os.chmod(os.path.join(root, n), stat.S_IWRITE | stat.S_IREAD)
        shutil.rmtree(path)
    os.makedirs(path)
    return path


# ---------------------------------------------------------------------------
# The actual logger block, executed in an isolated namespace.
# ---------------------------------------------------------------------------
def logger_source():
    with io.open(APP_PATH, "r", encoding="ascii", newline="") as f:
        text = f.read().replace("\r\n", "\n")
    start = text.index("\ndef reset_log():\n") + 1
    end = text.index("\n\n\ndef ptr(obj):\n")
    block = text[start:end]
    for name in ("def log_line(", "def prod_log_operation_end(", "PROD_LOG_DIR = "):
        assert block.count(name) == 1, name
    u_start = text.index("\ndef u(value):\n") + 1
    u_end = text.index("\n\n\ndef b(value):\n")
    w_start = text.index("\n_PROD_PRIVATE_WINDLL = {}\n") + 1
    w_end = text.index("\n\n\ndef prod_resource_snapshot(label):\n")
    return text[u_start:u_end] + "\n\n\n" + text[w_start:w_end] + "\n\n\n" + block + "\n"


_SOURCE = None


def load_ns(log_dir, build=u"b" * 64):
    global _SOURCE
    if _SOURCE is None:
        _SOURCE = logger_source()
    import binascii
    import ctypes
    import datetime
    import errno
    ns = {"__name__": "cpm_logger_under_test", "os": os, "re": re, "sys": sys, "datetime": datetime,
          "binascii": binascii, "errno": errno, "ctypes": ctypes,
          "__chadchan3d_cpm_build_sha256__": build, "PROD_VERSION": u"test-version",
          "PROD_RUN_ID": u"20261023-000000-pid%d" % os.getpid()}
    if not PY2:
        ns["unicode"] = str
        ns["long"] = int
    else:
        ns["unicode"] = unicode  # noqa: F821
    exec(compile(_SOURCE, APP_PATH + ":logger", "exec"), ns)
    ns["PROD_LOG_DIR"] = _TEXT(log_dir)
    return ns


def owned(log_dir):
    return sorted(n for n in os.listdir(log_dir) if NAME_RE.match(n))


def sizes(log_dir):
    return dict((n, os.path.getsize(os.path.join(log_dir, n))) for n in owned(log_dir))


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")  # strict


class Capture(object):
    def __enter__(self):
        self.old = sys.stdout
        self.buf = io.BytesIO() if PY2 else io.StringIO()
        sys.stdout = self
        return self

    def write(self, text):
        if PY2 and isinstance(text, unicode):  # noqa: F821
            text = text.encode("utf-8")
        self.buf.write(text)

    def flush(self):
        pass

    def __exit__(self, *exc):
        sys.stdout = self.old

    def text(self):
        value = self.buf.getvalue()
        return value.decode("utf-8") if PY2 else value


# ---------------------------------------------------------------------------
# 1. Creation, identification, UTF-8.
# ---------------------------------------------------------------------------
def case_creation():
    d = fresh(os.path.join(WORK, "c1"))
    ns = load_ns(d)
    text = u"PROD_TEST_EVENT caf\u00e9 \u65e5\u672c \U0001F600 path=C:\\x"
    ok = ns["log_line"](text)
    files = owned(d)
    check("1.write_returns_true", ok is True)
    check("1.one_segment_and_lock_only", len(files) == 1 and sorted(os.listdir(d)) == sorted(files + ["CPM - writer.lock"]),
          os.listdir(d))
    name = files[0] if files else ""
    check("1.filename_grammar", NAME_RE.match(name) is not None and (" - pid%d - " % os.getpid()) in name
          and (" - %s - 001.log" % ns["PROD_LOG_STATE"]["session"]) in name, name)
    body = read_text(os.path.join(d, name))
    lines = body.split(u"\r\n")
    header = lines[0]
    check("1.header_identifies_build_run_segment_format",
          header.startswith(u"SFM Character Preset Manager diagnostic log cpm-log-v1 | ")
          and u"build_sha256=%s" % (u"b" * 64) in header and u"version=test-version" in header
          and u"session=%s pid=%d run_id=20261023-000000-pid%d" % (ns["PROD_LOG_STATE"]["session"], os.getpid(), os.getpid()) in header
          and u"segment=001 created=" in header and re.search(u"created=\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z", header)
          and u"limits file_bytes=2097152 files=5 total_bytes=10485760 record_bytes=65536" in header, header)
    m = RECORD_RE.match(lines[1])
    check("1.record_utc_timestamp_sequence_session", m is not None and m.group(1) == u"000001"
          and m.group(2) == ns["PROD_LOG_STATE"]["session"] and m.group(3) == u"-" and m.group(4) == u"-", lines[1])
    check("1.utf8_text_roundtrip_crlf", lines[1].endswith(text) and body.endswith(u"\r\n") and len(lines) == 3, lines)
    check("1.lock_file_is_fixed_empty", os.path.getsize(os.path.join(d, "CPM - writer.lock")) == 0)
    ns["PROD_LOG_CONTEXT"]["window"] = 3
    ns["PROD_LOG_CONTEXT"]["operation"] = 7
    ns["log_line"]("CORRELATED")
    last = read_text(os.path.join(d, name)).split(u"\r\n")[-2]
    m = RECORD_RE.match(last)
    check("1.record_carries_window_and_operation", m is not None and m.group(3) == u"3" and m.group(4) == u"7"
          and m.group(1) == u"000002", last)
    SAMPLES["header"] = header
    check("1.reset_log_never_touches_files", ns["reset_log"]() is False and sorted(os.listdir(d)) == sorted(files + ["CPM - writer.lock"]))


# ---------------------------------------------------------------------------
# 2. Exact size boundary, rotation, five-file retention, record truncation.
# ---------------------------------------------------------------------------
def case_boundary_rotation_retention():
    d = fresh(os.path.join(WORK, "c2"))
    ns = load_ns(d)
    log_line = ns["log_line"]
    log_line(u"FIRST")
    name = owned(d)[0]
    path = os.path.join(d, name)
    first = read_text(path).split(u"\r\n")[1]
    prefix_len = len(first) - len(u"FIRST")
    # Largest record that is not truncated: exactly 65,536 bytes.
    max_text = LIMIT_RECORD - prefix_len - 2
    before = os.path.getsize(path)
    log_line(u"M" * max_text)
    check("2.record_of_exactly_65536_bytes_is_kept_whole", os.path.getsize(path) - before == LIMIT_RECORD
          and u"TRUNCATED" not in read_text(path))
    before = os.path.getsize(path)
    log_line(u"N" * (max_text + 1))
    grown = os.path.getsize(path) - before
    check("2.one_byte_more_is_truncated_within_65536", grown <= LIMIT_RECORD and u"TRUNCATED" in read_text(path), grown)
    # Fill to exactly the 2 MiB file limit.
    while True:
        remaining = LIMIT_FILE - os.path.getsize(path)
        if remaining <= LIMIT_RECORD:
            break
        log_line(u"F" * min(max_text, remaining - LIMIT_RECORD - prefix_len - 2 if remaining - LIMIT_RECORD > prefix_len + 2 else max_text))
    remaining = LIMIT_FILE - os.path.getsize(path)
    log_line(u"E" * (remaining - prefix_len - 2))
    check("2.file_filled_to_exactly_2097152", os.path.getsize(path) == LIMIT_FILE and owned(d) == [name],
          (os.path.getsize(path), owned(d)))
    full_sha = sha(path)
    log_line(u"NEXT")
    files = owned(d)
    check("2.rotation_before_exceeding_limit", len(files) == 2 and files[0] == name and files[1].endswith(u" - 002.log")
          and sha(path) == full_sha and os.path.getsize(path) == LIMIT_FILE, files)
    second = read_text(os.path.join(d, files[1]))
    check("2.new_segment_starts_with_header", second.startswith(u"SFM Character Preset Manager diagnostic log cpm-log-v1 | ")
          and u"segment=002" in second.split(u"\r\n")[0] and second.split(u"\r\n")[1].endswith(u"NEXT"))
    # Retention across seven segments.
    worst = (0, 0, 0)
    created = set(files)
    while ns["PROD_LOG_STATE"]["segment"] < 7:
        log_line(u"R" * max_text)
        s = sizes(d)
        created.update(s)
        worst = (max(worst[0], len(s)), max(worst[1], max(s.values())), max(worst[2], sum(s.values())))
    log_line(u"R" * max_text)
    s = sizes(d)
    check("2.never_more_than_five_files_2mib_each_10mib_total",
          worst[0] <= 5 and worst[1] <= LIMIT_FILE and worst[2] <= LIMIT_TOTAL, worst)
    check("2.oldest_segments_pruned_five_retained",
          len(s) == 5 and sorted(n[-7:-4] for n in s) == [u"003", u"004", u"005", u"006", u"007"]
          and len(created) == 7, sorted(s))
    SAMPLES["retention"] = {"segments_created": len(created), "retained": sorted(s), "max_files_seen": worst[0],
                            "max_file_bytes_seen": worst[1], "max_total_bytes_seen": worst[2]}
    # Oversized and enormous messages.
    d2 = fresh(os.path.join(WORK, "c2t"))
    ns2 = load_ns(d2)
    text = u"HEAD-START" + (u"\u00e9\u65e5" * 150000) + u"TAIL-END"
    ns2["log_line"](text)
    p2 = os.path.join(d2, owned(d2)[0])
    with open(p2, "rb") as f:
        raw = f.read()
    record = raw.split(b"\r\n")[1] + b"\r\n"
    try:
        decoded = record.decode("utf-8")
        valid = True
    except UnicodeDecodeError:
        decoded, valid = u"", False
    check("2.truncated_record_valid_utf8_within_limit", valid and len(record) <= LIMIT_RECORD
          and len(record) >= LIMIT_RECORD - 8, len(record))
    check("2.truncation_keeps_beginning_and_end_with_notice",
          u"| HEAD-START" in decoded and decoded.endswith(u"TAIL-END\r\n")
          and u"...[TRUNCATED: record over 65536 bytes; %d characters originally; beginning and end kept]..." % len(text) in decoded)
    SAMPLES["truncation"] = decoded[:120] + u" ... " + decoded[decoded.index(u" ...[TRUNCATED"):decoded.index(u"kept]...") + 8]
    started = time.time()
    ns2["log_line"](u"Z" * 10000000)
    elapsed = time.time() - started
    with open(p2, "rb") as f:
        last = f.read().split(b"\r\n")[-2]
    check("2.ten_million_character_message_bounded", len(last) + 2 <= LIMIT_RECORD and elapsed < 5.0, (len(last), elapsed))


# ---------------------------------------------------------------------------
# 3. Unrelated and historical files are preserved.
# ---------------------------------------------------------------------------
def case_preservation():
    parent = fresh(os.path.join(WORK, "c3"))
    d = os.path.join(parent, "SFM Character Preset Manager Logs")
    os.makedirs(d)
    keep = {}

    def put(path, data):
        with open(path, "wb") as f:
            f.write(data)
        keep[path] = sha(path)

    put(os.path.join(parent, "SFM_CSP_G18AN_SaveNewCopy.log"), b"[00:00:00.000000] historical\r\n" * 1000)
    put(os.path.join(d, "SFM_CSP_G18AN_SaveNewCopy.log"), b"historical copy in the log folder\r\n")
    put(os.path.join(d, "notes.log"), b"unrelated\r\n")
    put(os.path.join(d, "CPM - something else.log"), b"near-miss name\r\n")
    # Oldest possible grammar names, but not this logger's files:
    put(os.path.join(d, "CPM - 2000-01-01_00-00-00Z - pid1 - abcdef - 001.log"), b"foreign content, no header\r\n")
    put(os.path.join(d, "cpm - 2000-01-01_00-00-03z - pid1 - abcdef - 004.txt"), b"other extension\r\n")
    os.makedirs(os.path.join(d, "CPM - 2000-01-01_00-00-01Z - pid1 - abcdef - 002.log"))
    outside = fresh(os.path.join(WORK, "c3_outside"))
    target = os.path.join(outside, "CPM - 2000-01-01_00-00-02Z - pid1 - abcdef - 003.log")
    put(target, b"SFM Character Preset Manager diagnostic log cpm-log-v1 | outside the folder\r\n")
    junction_dir = os.path.join(outside, "junction-target")
    os.makedirs(junction_dir)
    put(os.path.join(junction_dir, "inside.log"), b"behind a junction\r\n")
    junction = os.path.join(d, "CPM - 2000-01-01_00-00-04Z - pid1 - abcdef - 005.log")
    jr = subprocess.call(["cmd", "/c", "mklink", "/J", junction, junction_dir], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
    link = os.path.join(d, "CPM - 2000-01-01_00-00-02Z - pid1 - abcdef - 003.log")
    lr = subprocess.call(["cmd", "/c", "mklink", link, target], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
    ns = load_ns(d)
    for _ in range(int(7.5 * 32) + 8):
        ns["log_line"](u"P" * 65000)
    mine = [n for n in owned(d) if os.path.isfile(os.path.join(d, n)) and " - %s - " % ns["PROD_LOG_STATE"]["session"] in n]
    check("3.retention_applied_to_own_segments_only", len(mine) == 5 and ns["PROD_LOG_STATE"]["segment"] >= 7,
          (mine, ns["PROD_LOG_STATE"]["segment"]))
    check("3.historical_and_unrelated_files_byte_identical",
          all(os.path.isfile(p) and sha(p) == h for p, h in keep.items()), [p for p, h in keep.items() if not os.path.isfile(p) or sha(p) != h])
    check("3.grammar_named_directory_kept", os.path.isdir(os.path.join(d, "CPM - 2000-01-01_00-00-01Z - pid1 - abcdef - 002.log")))
    check("3.junction_not_followed_or_removed", jr != 0 or (os.path.isdir(junction) and os.path.isfile(os.path.join(junction_dir, "inside.log"))), jr)
    check("3.symbolic_link_not_followed_or_removed", lr != 0 or (os.path.lexists(link) and os.path.isfile(target)), lr)
    SAMPLES["preservation"] = {"junction_case_ran": jr == 0, "file_symlink_case_ran": lr == 0}
    for p in (junction,):
        if jr == 0:
            os.rmdir(p)
    if lr == 0:
        os.remove(link)


# ---------------------------------------------------------------------------
# 4. Failures are contained.
# ---------------------------------------------------------------------------
def case_failures():
    base = fresh(os.path.join(WORK, "c4"))
    # a. Unwritable folder (its parent is a file).
    blocker = os.path.join(base, "blocker")
    with open(blocker, "wb") as f:
        f.write(b"x")
    ns = load_ns(os.path.join(blocker, "Logs"))
    with Capture() as cap:
        results = [ns["log_line"](u"A%d" % i) for i in range(50)]
    state = ns["PROD_LOG_STATE"]
    check("4a.unwritable_folder_returns_false_without_raising", results == [False] * 50)
    check("4a.one_console_notice_per_episode", cap.text() == NOTICE + "\n", cap.text())
    check("4a.suspended_with_bounded_drop_count", state["suspended"] and state["dropped"] == 50, (state["suspended"], state["dropped"]))
    good = os.path.join(base, "a-good")
    ns["PROD_LOG_DIR"] = _TEXT(good)
    with Capture() as cap:
        still = ns["log_line"](u"WHILE-SUSPENDED")
    check("4a.no_retry_until_launch_or_reopen", still is False and not os.path.exists(good) and cap.text() == u"")
    ns["prod_log_rearm"]()
    after = ns["log_line"](u"AFTER-REARM")
    text = read_text(os.path.join(good, owned(good)[0])) if os.path.isdir(good) and owned(good) else u""
    check("4a.rearm_retries_and_reports_dropped_records", after is True
          and u"PROD_LOG_DROPPED count=51 last_reason=" in text and text.rstrip().endswith(u"AFTER-REARM")
          and state["dropped"] == 0 and not state["noticed"], text[-300:])
    SAMPLES["dropped"] = [l for l in text.split(u"\r\n") if u"PROD_LOG_DROPPED" in l][0] if u"PROD_LOG_DROPPED" in text else None

    # b. Deletion failure: no sixth file, writing stops.
    d = fresh(os.path.join(base, "b"))
    ns = load_ns(d)
    while not (ns["PROD_LOG_STATE"]["segment"] == 5 and ns["PROD_LOG_STATE"]["size"] > LIMIT_FILE - 70000):
        ns["log_line"](u"B" * 65000)
    oldest = os.path.join(d, owned(d)[0])
    os.chmod(oldest, stat.S_IREAD)
    before = sorted(os.listdir(d))
    with Capture() as cap:
        r1 = ns["log_line"](u"B" * 65000)
        r2 = ns["log_line"](u"B" * 65000)
    os.chmod(oldest, stat.S_IWRITE | stat.S_IREAD)
    check("4b.failed_deletion_creates_no_extra_file", r1 is False and r2 is False and sorted(os.listdir(d)) == before
          and len(owned(d)) == 5, sorted(os.listdir(d)))
    check("4b.failed_deletion_suspends_with_one_notice", ns["PROD_LOG_STATE"]["suspended"] and cap.text() == NOTICE + "\n"
          and ns["PROD_LOG_STATE"]["drop_reason"].startswith(u"write-failed"), (cap.text(), ns["PROD_LOG_STATE"]["drop_reason"]))

    # c. Write failure on the current segment.
    d = fresh(os.path.join(base, "c"))
    ns = load_ns(d)
    ns["log_line"](u"C1")
    current = os.path.join(d, owned(d)[0])
    size = os.path.getsize(current)
    os.chmod(current, stat.S_IREAD)
    with Capture() as cap:
        r = ns["log_line"](u"C2")
    os.chmod(current, stat.S_IWRITE | stat.S_IREAD)
    check("4c.write_failure_contained", r is False and os.path.getsize(current) == size and len(owned(d)) == 1
          and ns["PROD_LOG_STATE"]["suspended"] and cap.text() == NOTICE + "\n", (r, cap.text()))

    # d. Lock contention: drop and count, never wait or suspend.
    d = fresh(os.path.join(base, "d"))
    ns = load_ns(d)
    ns["log_line"](u"D1")
    ready = os.path.join(base, "lock-ready")
    holder = subprocess.Popen([PYTHON, "-E", "-B", os.path.abspath(__file__), "--child=holdlock",
                               "--dir=%s" % d, "--ready=%s" % ready, "--seconds=3"])
    deadline = time.time() + 20
    while not os.path.exists(ready) and time.time() < deadline:
        time.sleep(0.02)
    with Capture() as cap:
        started = time.time()
        busy = [ns["log_line"](u"D-busy-%d" % i) for i in range(5)]
        elapsed = time.time() - started
    holder.wait()
    ok = ns["log_line"](u"D-after")
    text = read_text(os.path.join(d, owned(d)[0]))
    check("4d.contention_drops_without_waiting", busy == [False] * 5 and elapsed < 1.0, (busy, elapsed))
    check("4d.contention_is_not_a_failure_episode", cap.text() == u"" and not ns["PROD_LOG_STATE"]["suspended"])
    check("4d.next_write_reports_lock_drops", ok is True and u"PROD_LOG_DROPPED count=5 last_reason=u'lock-busy'" in text.replace(u"last_reason='lock-busy'", u"last_reason=u'lock-busy'")
          and u"D-busy" not in text, text[-300:])


def child_holdlock(args):
    import msvcrt
    fd = os.open(os.path.join(args["dir"], "CPM - writer.lock"), os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0))
    os.lseek(fd, 0, 0)
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    open(args["ready"], "wb").close()
    time.sleep(float(args["seconds"]))
    os.lseek(fd, 0, 0)
    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    os.close(fd)


# ---------------------------------------------------------------------------
# 5. Two concurrent writers share one retention limit.
# ---------------------------------------------------------------------------
def child_writer(args):
    ns = load_ns(args["dir"])
    count = int(args["count"])
    go = args["go"]
    while not os.path.exists(go):
        time.sleep(0.001)
    written = reported = 0
    state = ns["PROD_LOG_STATE"]

    def write(text):
        pending = state["dropped"]
        ok = ns["log_line"](text)
        return ok, (pending if ok else 0)

    for i in range(count + 1):
        text = (u"W-%s-%05d " % (state["session"], i) + u"w" * (60000 if i % 3 else 300)) if i < count else u"W-FINAL"
        ok, rep = write(text)
        written += 1 if ok else 0
        reported += rep
    with open(args["out"], "w") as f:
        json.dump({"session": state["session"], "attempts": count + 1, "written": written, "reported_drops": reported,
                   "dropped_pending": state["dropped"], "suspended": state["suspended"],
                   "segments": state["segment"]}, f)


def case_concurrency():
    d = fresh(os.path.join(WORK, "c5"))
    # Pre-fill the folder with five full owned segments of a third session,
    # so every rotation during the race must prune.
    seed = load_ns(d)
    while not (seed["PROD_LOG_STATE"]["segment"] == 5 and seed["PROD_LOG_STATE"]["size"] > LIMIT_FILE - 70000):
        seed["log_line"](u"S" * 65000)
    seeded = set(owned(d))
    go = os.path.join(WORK, "c5.go")
    if os.path.exists(go):
        os.remove(go)
    outs = [os.path.join(WORK, "c5_%d.json" % i) for i in range(2)]
    procs = [subprocess.Popen([PYTHON, "-E", "-B", os.path.abspath(__file__), "--child=writer", "--dir=%s" % d,
                               "--count=400", "--go=%s" % go, "--out=%s" % outs[i]]) for i in range(2)]
    seen = {"files": 0, "total": 0, "file": 0, "polls": 0}
    stop = []

    def observe():
        while not stop:
            try:
                s = {}
                for n in os.listdir(d):
                    if NAME_RE.match(n):
                        try:
                            s[n] = os.path.getsize(os.path.join(d, n))
                        except OSError:
                            pass
                seen["files"] = max(seen["files"], len(s))
                seen["total"] = max(seen["total"], sum(s.values()))
                seen["file"] = max(seen["file"], max(s.values()) if s else 0)
                seen["polls"] += 1
            except OSError:
                pass

    t = threading.Thread(target=observe)
    t.start()
    time.sleep(1.0)
    open(go, "wb").close()
    for p in procs:
        p.wait()
    stop.append(True)
    t.join()
    reports = [json.load(open(o)) for o in outs]
    s = sizes(d)
    check("5.both_writers_wrote_and_rotated_through_shared_folder", all(r["written"] > 0 and r["segments"] >= 1 for r in reports)
          and sum(r["segments"] for r in reports) >= 3, reports)
    check("5.rotations_during_the_race_pruned_shared_segments", len(seeded) == 5 and len(seeded - set(owned(d))) >= 3,
          sorted(seeded - set(owned(d))))
    check("5.shared_retention_never_exceeded_while_running", seen["files"] <= 5 and seen["file"] <= LIMIT_FILE
          and seen["total"] <= LIMIT_TOTAL and seen["polls"] > 10, seen)
    check("5.final_state_within_limits", len(s) <= 5 and sum(s.values()) <= LIMIT_TOTAL and max(s.values()) <= LIMIT_FILE, s)
    sessions = set(r["session"] for r in reports) | set([seed["PROD_LOG_STATE"]["session"]])
    clean = True
    for n in s:
        text = read_text(os.path.join(d, n))
        lines = [l for l in text.split(u"\r\n")[1:] if l]
        owners = set(RECORD_RE.match(l).group(2) for l in lines if RECORD_RE.match(l))
        seqs = [int(RECORD_RE.match(l).group(1)) for l in lines if RECORD_RE.match(l)]
        if len(owners) != 1 or not owners <= sessions or seqs != sorted(seqs) or (u"session=%s" % list(owners)[0]) not in text.split(u"\r\n")[0]:
            clean = False
    check("5.each_file_written_by_one_process_in_order", clean)
    check("5.every_record_written_or_counted_as_dropped", all(r["written"] + r["reported_drops"] + r["dropped_pending"] == r["attempts"]
          and not r["suspended"] for r in reports), reports)
    SAMPLES["concurrency"] = {"reports": reports, "observer": seen, "final": s}


# ---------------------------------------------------------------------------
# 6/7 and 4e. The actual application through the R15 harness.
# ---------------------------------------------------------------------------
def integration():
    import test_cpm_app_r15_namespace_isolation as r15
    try:
        import PySide  # noqa: F401
        qt = "real"
    except ImportError:
        qt = "model"
    env = r15.Env(qt, os.path.join(WORK, "integration"))
    QtGui = env.QtGui
    boxes = []
    QtGui.QMessageBox.exec_ = lambda self: boxes.append((self.windowTitle(), self.text())) or 0
    sfm = sys.modules["sfmApp"]
    sfm.HasDocument = lambda: True  # an open session with an empty current shot
    logdir = os.path.join(env.docs, r15.CPM_LOG_DIR.lower())

    # 4e. The log folder cannot be created: CPM launches and works normally.
    with open(logdir, "wb") as f:
        f.write(b"not a folder")
    console = env.click()
    env.settle()
    window = env.slot()
    ns = env.module().__dict__
    check("4e.blocked_log_folder_window_created_normally", window is not None and isinstance(window, ns["ProdWindow"])
          and window.isVisible())
    check("4e.blocked_log_folder_one_console_notice", console.count(NOTICE) == 1, console)
    check("4e.blocked_log_folder_suspended_not_unbounded", ns["PROD_LOG_STATE"]["suspended"] is True
          and sorted(os.listdir(env.docs)) == [r15.CPM_LOG_DIR.lower()] and os.path.isfile(logdir))
    status_blocked = window.status.text()
    window.populate()
    env.settle()
    check("4e.operations_continue_while_logging_suspended", window.status.text() == status_blocked and not boxes,
          (window.status.text(), boxes))
    window.close()
    env.settle()
    os.remove(logdir)
    state = ns["PROD_LOG_STATE"]
    session = state["session"]
    dropped_before = state["dropped"]

    # 6. Fresh launch after the folder becomes writable (explicit launch = retry).
    console = env.click()
    env.settle()
    window1 = env.slot()
    log = env.log() or u""
    files = env.log_files()
    check("6.launch_rearms_and_creates_one_segment", len(files) == 1 and console.count(NOTICE) == 0
          and (u"PROD_LOG_DROPPED count=%d" % dropped_before) in log, (files, console))
    header = log.split(u"\r\n")[0]
    build = env.module().__dict__.get("__chadchan3d_cpm_build_sha256__")
    check("6.header_carries_loader_build_identity", build and (u"build_sha256=%s" % build) in header
          and (u"session=%s" % session) in header and (u"run_id=%s" % ns["PROD_RUN_ID"]) in header, header)
    w1 = window1.log_window_id
    check("6.created_window_identified", re.search(u"w=%d op=- \\| PROD_R15_LAUNCH_RESULT outcome=u?'created' code=u?'create' window=%d" % (w1, w1), log) is not None, w1)
    size1 = os.path.getsize(files[0])
    env.click()
    env.settle()
    log2 = env.log()
    check("6.reuse_same_window_identity_same_segment_no_truncation", env.slot() is window1 and env.log_files() == files
          and log2.startswith(log) and re.search(u"w=%d op=- \\| PROD_R15_WINDOW_REUSED" % w1, log2)
          and re.search(u"PROD_R15_LAUNCH_RESULT outcome=u?'reused' code=u?'reuse' window=%d" % w1, log2), w1)
    window1.close()
    env.settle()
    log3 = env.log()
    check("6.close_finalized_with_window_identity", re.search(u"w=%d op=- \\| PROD_CLOSE_FINALIZED=True" % w1, log3) is not None)
    env.click()
    env.settle()
    window2 = env.slot()
    w2 = window2.log_window_id
    log4 = env.log()
    seqs = [int(m.group(1)) for m in (RECORD_RE.match(l) for l in log4.split(u"\r\n")) if m]
    sess = set(m.group(2) for m in (RECORD_RE.match(l) for l in log4.split(u"\r\n")) if m)
    check("6.reopen_new_window_distinguishable_same_process_identity", window2 is not window1 and w2 == w1 + 1
          and env.module().__dict__["PROD_LOG_STATE"]["session"] == session and sess == set([session])
          and env.log_files() == files and log4.startswith(log3)
          and re.search(u"PROD_R15_LAUNCH_RESULT outcome=u?'created' code=u?'create' window=%d" % w2, log4), (w1, w2))
    check("6.sequence_continues_across_reuse_and_reopen", len(seqs) > 10 and seqs == sorted(seqs)
          and len(set(seqs)) == len(seqs), seqs[:5])

    # 7. Correlated outcomes through the real ProdWindow.guard decision points.
    ns = env.module().__dict__

    def run(label, fn):
        mark = env.log()
        del boxes[:]
        window2.guard(label, fn)
        env.settle()
        return env.log()[len(mark):]

    def records(chunk):
        out = []
        for line in chunk.split(u"\r\n"):
            m = RECORD_RE.match(line)
            if m:
                out.append((m.group(3), m.group(4), line[m.end():]))
        return out

    def outcome_of(chunk):
        m = re.search(u"PROD_OPERATION_RESULT id=(\\d+) kind=u?'[^']*' outcome=u?'([a-z-]+)'", chunk)
        return m.group(2) if m else None

    def correlated(chunk):
        recs = records(chunk)
        begin = [r for r in recs if r[2].startswith(u"PROD_OPERATION_BEGIN ")]
        if len(begin) != 1:
            return False
        op = re.search(u"id=(\\d+)", begin[0][2]).group(1)
        inside = [r for r in recs if r[2].startswith((u"PROD_OPERATION_BEGIN", u"PROD_OPERATION_OUTCOME", u"PROD_ACTION_ERROR",
                                                       u"PROD_OPERATION_END", u"PROD_OPERATION_RESULT", u"Traceback"))]
        return all(r[0] == u"%d" % w2 and r[1] == op for r in inside) and any(r[2].startswith(u"PROD_OPERATION_RESULT id=%s " % op) for r in inside)

    def phases(*marks):
        def fn():
            for m in marks:
                if m[0] == "phase":
                    window2.operation_mark_phase(m[1], {"kind": u"test"})
                elif m[0] == "outcome":
                    ns["prod_log_outcome"](m[1], {"test": True})
                elif m[0] == "recovery":
                    ns["prod_log_note_recovery"](m[1])
                elif m[0] == "raise":
                    raise m[1]
        return fn

    matrix = [
        ("verified", "Save Current Body", phases(("phase", "durable-commit"), ("phase", "durable-verified"), ("outcome", u"verified"))),
        ("no-op", "Update Preset", phases(("outcome", u"no-op"))),
        ("completed", "Model Info", phases()),
        ("not-recorded", "Save Current Body", phases()),
        ("failed-precommit", "Apply Body Preset", phases(("raise", RuntimeError("synthetic precommit failure")))),
        ("refused", "Apply Body Preset", phases(("raise", ns["ProdCpmOperationAuthorityError"]("synthetic authority refusal")))),
        ("refused", "Apply Body Preset", phases(("raise", RuntimeError(
            "This preset does not match the selected model's current sliders. Choose another preset or model.")))),
        ("committed-unverified", "Apply Body Preset", phases(("phase", "native-commit"), ("raise", RuntimeError("post-commit verify failed")))),
        ("recovery-verified", "Apply Body Preset", phases(("recovery", True), ("raise", RuntimeError("aborted and restored")))),
        ("recovery-unverified", "Apply Body Preset", phases(("recovery", False), ("raise", ns["ProdRecoveryUnverifiedError"]("restore unproven")))),
        ("verified", "Update Preset", phases(("phase", "durable-commit"), ("phase", "durable-verified"), ("raise", RuntimeError("list refresh failed")))),
        ("committed-unverified", "Update Preset", phases(("phase", "durable-commit"), ("raise", RuntimeError("readback failed")))),
    ]
    for expected, label, fn in matrix:
        chunk = run(label, fn)
        got = outcome_of(chunk)
        check("7.%s_%s" % (label.replace(" ", "_"), expected), got == expected and correlated(chunk), (got, chunk[-600:]))
        SAMPLES.setdefault("outcomes", {}).setdefault(expected, chunk)
    # Existing user-facing behavior is unchanged by the outcome records.
    chunk = run("Apply Body Preset", phases(("phase", "native-commit"), ("raise", RuntimeError("x"))))
    check("7.dialog_copy_unchanged_for_committed_unverified",
          boxes == [(u"Action committed; verification did not finish",
                     u"The SFM change may already be applied. Check the result or use SFM Undo before retrying.")], boxes)
    check("7.status_copy_unchanged_for_committed_unverified", qt != "real" or
          window2.status.text() == u"The SFM change may already be applied. Check the result or use SFM Undo before retrying.",
          window2.status.text())

    # Real refusals and real failures through product code.
    window2.fit_active = True
    chunk = run("Apply Expression", phases(("outcome", u"verified")))
    window2.fit_active = False
    check("7.refused_while_another_action_active", u"PROD_OPERATION_REFUSED kind=u'Apply Expression' reason=u'another-action-active'"
          in chunk.replace(u"kind='", u"kind=u'").replace(u"reason='", u"reason=u'") and u"PROD_OPERATION_BEGIN" not in chunk, chunk)
    SAMPLES["refused_busy"] = chunk
    mark = env.log()
    window2.fit_selected()
    env.settle()
    chunk = env.log()[len(mark):]
    check("7.clothing_fit_without_targets_refused", u"PROD_OPERATION_REFUSED" in chunk and u"no-target-selected" in chunk, chunk)
    real_candidates = ns["g09a_candidates"]

    def failing():
        raise RuntimeError("synthetic discovery failure")
    ns["g09a_candidates"] = failing
    mark = env.log()
    window2.populate()
    env.settle()
    chunk = env.log()[len(mark):]
    ns["g09a_candidates"] = real_candidates
    check("7.real_refresh_failure_correlated_failed_precommit", outcome_of(chunk) == u"failed-precommit" and correlated(chunk)
          and u"PROD_ACTION_ERROR label='Refresh Models'" in chunk and u"Traceback" in chunk, chunk[-800:])
    SAMPLES["failed_refresh"] = chunk
    mark = env.log()
    window2.populate()
    env.settle()
    chunk = env.log()[len(mark):]
    check("7.real_refresh_success_completed", outcome_of(chunk) == u"completed" and correlated(chunk), chunk)
    SAMPLES["refresh_ok"] = chunk

    # Deferred close: requested during an operation, finalized after it ends.
    mark = env.log()
    window2.guard("Model Info", lambda: window2.close())
    env.settle()
    chunk = env.log()[len(mark):]
    order = [k for k in (u"PROD_CLOSE_REQUEST", u"PROD_CLOSE_DEFERRED reason='operation-active'", u"PROD_OPERATION_RESULT",
                         u"PROD_CLOSE_FINALIZED=True") if k in chunk]
    check("7.deferred_close_then_finalized", len(order) == 4 and chunk.index(order[1]) < chunk.index(order[2]) < chunk.index(order[3])
          and env.slot() is None, chunk)
    SAMPLES["deferred_close"] = chunk
    return env


def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("--child="):
        args = dict(a[2:].split("=", 1) for a in sys.argv[1:])
        {"writer": child_writer, "holdlock": child_holdlock}[args["child"]](args)
        return
    real_dir = u"C:\\Users\\Public\\Documents\\SFM Character Preset Manager Logs"
    historical = u"C:\\Users\\Public\\Documents\\SFM_CSP_G18AN_SaveNewCopy.log"
    real_before = (os.path.exists(real_dir), sha(historical) if os.path.isfile(historical) else None)
    fresh(WORK)
    print("Python %s" % sys.version.split()[0])
    case_creation()
    case_boundary_rotation_retention()
    case_preservation()
    case_failures()
    case_concurrency()
    integration()
    # The R15 harness remaps C:\Users in this process, so the real disk is read by a clean interpreter.
    probe = subprocess.check_output([PYTHON, "-E", "-B", "-c",
                                     "import hashlib,os,sys;d,h=sys.argv[1:3];"
                                     "print(repr((os.path.exists(d), hashlib.sha256(open(h,'rb').read()).hexdigest() if os.path.isfile(h) else None)))",
                                     real_dir, historical]).decode("ascii").strip()
    real_after = eval(probe)
    check("guard.real_log_folder_absent_and_historical_log_unchanged", real_before == real_after and not real_after[0],
          (real_before, real_after))
    with io.open(os.path.join(WORK, "samples.json"), "w", encoding="utf-8") as f:
        f.write(_TEXT(json.dumps(SAMPLES, indent=1, ensure_ascii=False, default=repr)))
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    sys.stdout.flush()
    os._exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
