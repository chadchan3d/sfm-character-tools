# -*- coding: utf-8 -*-
"""The bounded worker (L-4; card §5): every backend operation of the GUI runs in a separate worker
process inside a Windows Job Object.

- The worker is created suspended, assigned to the job, and only then resumed, so no worker code
  runs outside the limits. If the assignment fails, the worker is terminated and nothing runs.
- Job-wide committed-memory ceiling (JOB_OBJECT_LIMIT_JOB_MEMORY, MEMORY_LIMIT bytes) covering the
  worker and its children (the tasklist process query).
- JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: closing the job handle, including the GUI process exiting or
  being killed, terminates every process in the job. No worker outlives its GUI.
- JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION: no error dialog can keep a dead worker alive.

The worker is the unchanged backend entry point (`python -m sfm_character_tools_updater.worker`):
one command in, exactly one JSON result file out. This module only starts, contains, waits for and
classifies it; it is not a publication mechanism.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

# Ceiling for the worker job. The supported workload (a Master the size of the current official
# data, about 4 MB, with its 9.5 MB sidecar) peaks well below this; see the L-4 report for the
# measured peaks. The ceiling leaves room for larger customized Masters while keeping a runaway
# worker from exhausting the machine.
MEMORY_LIMIT = 2 * 1024 * 1024 * 1024
MEMORY_LIMIT_MARGIN = 16 * 1024 * 1024

UPDATER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)

JobObjectExtendedLimitInformation = 9
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
TH32CS_SNAPTHREAD = 0x00000004
THREAD_SUSPEND_RESUME = 0x0002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount",
                                                   "OtherOperationCount", "ReadTransferCount",
                                                   "WriteTransferCount", "OtherTransferCount")]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wt.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION), ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ThreadID", wt.DWORD),
                ("th32OwnerProcessID", wt.DWORD), ("tpBasePri", wt.LONG), ("tpDeltaPri", wt.LONG),
                ("dwFlags", wt.DWORD)]


_k32.CreateJobObjectW.restype = wt.HANDLE
_k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
_k32.SetInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
_k32.QueryInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p]
_k32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
_k32.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]
_k32.CloseHandle.argtypes = [wt.HANDLE]
_k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
_k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
_k32.Thread32First.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
_k32.Thread32Next.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
_k32.OpenThread.restype = wt.HANDLE
_k32.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
_k32.ResumeThread.argtypes = [wt.HANDLE]
_k32.ResumeThread.restype = wt.DWORD


class JobError(Exception):
    pass


def default_worker_argv():
    """The shipping worker: the unchanged backend entry point. (L-5 decides the packaged form.)"""
    return [sys.executable, "-E", "-s", "-B", "-m", "sfm_character_tools_updater.worker"]


class Job(object):
    """One Job Object holding one worker process (and its children)."""

    def __init__(self, memory_limit):
        self.limit = memory_limit
        self.h = _k32.CreateJobObjectW(None, None)
        if not self.h:
            raise JobError("CreateJobObject failed (%d)" % ctypes.get_last_error())
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = (JOB_OBJECT_LIMIT_JOB_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                                                 | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION)
        info.JobMemoryLimit = memory_limit
        if not _k32.SetInformationJobObject(self.h, JobObjectExtendedLimitInformation, ctypes.byref(info),
                                            ctypes.sizeof(info)):
            err = ctypes.get_last_error()
            self.close()
            raise JobError("SetInformationJobObject failed (%d)" % err)

    def assign(self, process_handle):
        if not _k32.AssignProcessToJobObject(self.h, int(process_handle)):
            raise JobError("AssignProcessToJobObject failed (%d)" % ctypes.get_last_error())

    def peak_memory(self):
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        if not _k32.QueryInformationJobObject(self.h, JobObjectExtendedLimitInformation, ctypes.byref(info),
                                              ctypes.sizeof(info), None):
            return None
        return info.PeakJobMemoryUsed

    def terminate(self):
        if self.h:
            _k32.TerminateJobObject(self.h, 1)

    def close(self):
        """Closing the handle kills anything still in the job (KILL_ON_JOB_CLOSE)."""
        if self.h:
            _k32.CloseHandle(self.h)
            self.h = None


def _resume_process(pid):
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        raise JobError("thread snapshot failed (%d)" % ctypes.get_last_error())
    resumed = 0
    try:
        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(te)
        ok = _k32.Thread32First(snap, ctypes.byref(te))
        while ok:
            if te.th32OwnerProcessID == pid:
                th = _k32.OpenThread(THREAD_SUSPEND_RESUME, False, te.th32ThreadID)
                if th:
                    if _k32.ResumeThread(th) != 0xFFFFFFFF:
                        resumed += 1
                    _k32.CloseHandle(th)
            ok = _k32.Thread32Next(snap, ctypes.byref(te))
    finally:
        _k32.CloseHandle(snap)
    if not resumed:
        raise JobError("worker thread could not be resumed")


class WorkerRun(object):
    """One bounded worker run. start() returns at once; wait() blocks for the classified result.

    Classified result: the worker's own JSON result, or one of the supervisor outcomes
    WORKER_MEMORY_LIMIT (stopped at the memory ceiling), WORKER_STOPPED (stopped on request, for
    example because the window was closed) or WORKER_FAILED (ended without a result). The
    supervisor never turns a missing or failed result into success."""

    def __init__(self, command_args, worker_argv=None, memory_limit=None, cwd=None, env=None):
        self.args = list(command_args)
        self.worker_argv = list(worker_argv or default_worker_argv())
        self.limit = memory_limit or MEMORY_LIMIT
        self.cwd = cwd or UPDATER_ROOT
        self.env = env
        self.proc = None
        self.job = None
        self.dir = None
        self.stop_requested = False
        self.result = None
        self.done = threading.Event()

    def start(self):
        self.dir = tempfile.mkdtemp(prefix="sct-updater-")
        self.result_path = os.path.join(self.dir, "result.json")
        argv = self.worker_argv + [self.args[0], "--result", self.result_path] + self.args[1:]
        self.job = Job(self.limit)
        out = open(os.path.join(self.dir, "stdout.txt"), "wb")
        err = open(os.path.join(self.dir, "stderr.txt"), "wb")
        try:
            self.proc = subprocess.Popen(argv, cwd=self.cwd, env=self.env, stdin=subprocess.DEVNULL, stdout=out,
                                         stderr=err, creationflags=CREATE_SUSPENDED | CREATE_NO_WINDOW)
        finally:
            out.close()
            err.close()
        try:
            self.job.assign(self.proc._handle)
            _resume_process(self.proc.pid)
        except Exception:
            self.proc.kill()
            self.proc.wait()
            self.job.close()
            raise
        threading.Thread(target=self._wait, daemon=True).start()
        return self

    @property
    def pid(self):
        return self.proc.pid if self.proc else None

    def request_stop(self):
        """Stop the worker now (window closed or cancelled). Everything in its job ends."""
        self.stop_requested = True
        if self.job:
            self.job.terminate()

    def _read(self, name, limit=200000):
        try:
            with open(os.path.join(self.dir, name), "rb") as f:
                return f.read(limit).decode("utf-8", "replace")
        except OSError:
            return ""

    def _wait(self):
        rc = self.proc.wait()
        peak = self.job.peak_memory()
        self.job.close()
        res = None
        try:
            with open(self.result_path, "rb") as f:
                res = json.loads(f.read().decode("utf-8"))
            if not isinstance(res, dict) or "outcome" not in res:
                res = None
        except (OSError, ValueError):
            res = None
        near_limit = peak is not None and peak >= self.limit - MEMORY_LIMIT_MARGIN
        tb = json.dumps((res or {}).get("details", ""))
        if self.stop_requested:
            out = {"outcome": "WORKER_STOPPED"}
        elif res is not None and not (res.get("outcome") == "ERROR" and ("MemoryError" in tb or near_limit)):
            out = res
        elif near_limit or "MemoryError" in tb or "MemoryError" in self._read("stderr.txt"):
            out = {"outcome": "WORKER_MEMORY_LIMIT"}
        else:
            out = {"outcome": "WORKER_FAILED"}
        out.setdefault("details", {})
        out["worker"] = {"exit_code": rc, "pid": self.proc.pid, "peak_job_memory": peak, "memory_limit": self.limit,
                         "command": self.args[0], "stderr_tail": self._read("stderr.txt")[-2000:],
                         "result_present": res is not None}
        if res is not None and out is not res:
            out["worker"]["worker_result"] = res
        self.result = out
        shutil.rmtree(self.dir, ignore_errors=True)
        self.done.set()

    def wait(self, timeout=None):
        self.done.wait(timeout)
        return self.result
