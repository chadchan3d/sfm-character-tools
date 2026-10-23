# SFM Control Group Updater: packaging (L-5)

**Application:** SFM Control Group Updater **v0.1.0**, a Windows x64 one-folder application.
**Data:** animation-group data releases are versioned separately (`data-v1.0.0`, ...).

## 1. Build recipe (reproducible)

1. **Base interpreter:** CPython **3.10.6** x64 from python.org.
2. **Build environment:** a new virtual environment from that interpreter, outside the repository, with exactly the
   locked packages, installed offline and hash-checked:

   ```
   python -m venv BUILD_VENV
   BUILD_VENV\Scripts\python.exe -m pip install --no-index --find-links WHEELS --require-hashes -r requirements-build.txt
   ```

   `WHEELS` holds the wheels named in `requirements-build.txt`, downloaded from PyPI with their SHA-256 recorded
   there.
3. **Build:**

   ```
   BUILD_VENV\Scripts\python.exe -E -s -B updater\packaging\build.py --out NEW_FOLDER_OUTSIDE_THE_REPOSITORY
   ```

### What `build.py` does

- **Checks the environment:**
  - the interpreter and the locked versions (PyInstaller 6.11.1, hooks 2024.10, cryptography 50.0.2, cffi 2.1.1,
    pycparser 3.11);
  - the nine pinned dependency sources against `candidate.PINS` and the authority profile.
- **Builds:**
  - writes the Windows version resource from `sfm_character_tools_updater.VERSION`;
  - runs PyInstaller on `sct_updater.spec`, with no UPX, a fixed `PYTHONHASHSEED` and `SOURCE_DATE_EPOCH`, and a
    **minimal `PATH`** (Windows and the build interpreter only). Without it, PyInstaller collected an unrelated
    OpenSSL 3 from another program on `PATH`.
- **Verifies the result:**
  - checks the bundled pinned sources byte-for-byte;
  - refuses test or development material;
  - scans every bundled file for workstation path markers;
  - writes `bundle_manifest.json`: every file with its size and SHA-256, plus the bundle identity (SHA-256 of the
    sorted path/hash list).
- **Reproducibility:** two builds from the same source have the same file set, and every file is byte-identical
  except the two executables' embedded archive (`PYZ`) and one `.pyc` in `base_library.zip`. All embedded modules
  unmarshal to identical code objects, so the residual difference is CPython 3.10 `marshal` serialization (its
  reference flags depend on runtime reference counts), not code.

## 2. Bundle layout

```
SFM Control Group Updater\
  SFM Control Group Updater.exe     GUI (windowed); the only file a user starts
  sct-updater-worker.exe            the backend worker (one command, one JSON result); started by the GUI
                                    with CREATE_NO_WINDOW inside a Job Object (2 GiB, kill-on-close)
  _internal\
    python310.dll, python3.dll, VCRUNTIME140.dll, libffi-7.dll      CPython 3.10.6 runtime
    _ssl.pyd, libssl-1_1.dll, libcrypto-1_1.dll                     TLS (OpenSSL 1.1.1n, from CPython)
    _tkinter.pyd, tcl86t.dll, tk86t.dll, _tcl_data\, _tk_data\, tcl8\   Tkinter (Tk 8.6)
    other stdlib extension modules (.pyd), base_library.zip
    cryptography\ (50.0.2, OpenSSL statically linked), _cffi_backend   Ed25519 signature verification
    sct_deps\                        the nine pinned sources, byte-exact, loaded after SHA-256 verification:
      sfm_master_sidecar\{__init__,compiler,format,manifest,reader,writer}.py
      sfm_master_core.py
      authority\candidate_packed_{validator,provider}_r3a2b.py
```

- **Product code:** the package `sfm_character_tools_updater` is compiled into the executables' embedded archive.
  Tests, test seams' callers (`tests/support`), release tools and keys are never bundled.
- **Pinned sources:** they are the same files as in the repository. In the development tree `candidate.py` reads
  them from `tools/` and the authority package's qualified copy; frozen, from `_internal\sct_deps`. The pins are the
  same.
- **Runtime requirements:** Windows 10 or later x64. The Universal C Runtime is part of Windows, so no Python
  installation is needed.

## 3. Dependency inventory (bundled)

| Component | Version | Origin |
|---|---|---|
| CPython runtime and standard library | 3.10.6 | python.org installer |
| OpenSSL (for `ssl`) | 1.1.1n | shipped with CPython 3.10.6 |
| Tcl/Tk | 8.6 | shipped with CPython 3.10.6 |
| cryptography | 50.0.2 | PyPI wheel `4e81d95e…` |
| cffi | 2.1.1 | PyPI wheel `a48d62ab…` |
| pycparser | 3.11 | PyPI wheel `51d5a8ba…` (cffi dependency) |
| typing_extensions | 4.16.0 | PyPI wheel `481caa48…` (cryptography dependency) |
| Canonical compiler and reader (`tools/sfm_master_sidecar`, `sfm_master_core.py`) | pinned | repository, pins in `candidate.py` and the profile |
| FINAL R3-A2B validator and provider | `74fe8d96…`, `d6ef9650…` | repository (production authority package's qualified copy) |

The build tools (PyInstaller 6.11.1, pyinstaller-hooks-contrib 2024.10, altgraph 0.17.4, pefile 2023.2.7,
pywin32-ctypes 0.2.3, packaging 24.2, setuptools 75.3.0) are not application code. Only the PyInstaller bootloader
is part of the executables. The exact file list is `bundle_manifest.json` of each build.

## 4. Compatibility profile and signed software inventory (`compat/`)

### Profile

`compat/profile.py` defines `sct-authority-profile-1` as canonical JSON. Its identity is the SHA-256 of that JSON.
The updater implements **`sct-authority-profile-2`** (`e0a9b64e…`, 2026-10-23). It is profile 1 (`2bbd93d0…`) with
the software and its signed inventory under `scripts/sfm/mainmenu/SFM Character Tools` (layout contract
`sct-layout-2`). Every other contract is unchanged, and profile 1 is no longer accepted.
It binds:
- the installation layout and the Master path resolution;
- sidecar format and semantics 0;
- the compiler and validator/provider file hashes;
- runtime API `1.0.0-b2a` and build `package-boundary-corrected-2026-09-22`;
- the CPM (`sfm-character-semantic-provider-v1`, `cpm-compat-v1`) and Normalizer consumer contracts;
- the static admission limits;
- the installed-publication protocol (`sct-updater-tx-1`);
- the deployment policy (source authoritative; bytecode derived and not inventoried).

### Signed inventory

The Character Tools software release installs a signed inventory beside its menu scripts:

```
usermod\scripts\sfm\mainmenu\SFM Character Tools\sfm_character_tools_inventory.json
usermod\scripts\sfm\mainmenu\SFM Character Tools\sfm_character_tools_inventory.sig
```

- **Contents:** the inventory lists the 31 immutable software files (CPM app and launcher, Normalizer, CPM adapter
  and projection, the authority package, and the sidecar reader) with role, length and SHA-256. It names the
  profile ID, its exact contract hash and the runtime API/build.
- **Signature:** `.sig` is Ed25519 over the exact JSON bytes, made with a key trusted by the updater: the same
  release trust as official data. The shipping trust list holds exactly the owner's production key
  (`ed25519-5d879134807dff6d`, embedded 2026-10-22). Test keys reach trust only through the test-only seam, never in
  the bundle. During L-5 only test keys were used. The owner performs all production signing.
- **Producer:** `release_tools/make_software_inventory.py` builds the inventory from
  `release_tools/character_tools_software_v1.json`. That spec records the accepted release identities (K-qualified,
  with the amendment's Normalizer and the 2026-10-22 CPM reconciliation; see its `qualification` note), and the
  producer refuses any other bytes.

### Enforcement

- **When:** before **any** data is installed, for all three actions, and re-verified immediately before installation
  when preparation happened earlier. Published data is also checked before it is prepared.
- **What is checked:** the signature, the profile and contract hash, the runtime identity, the required roles and
  every listed file.
- **Refusals:** a missing or unverifiable inventory gives SOFTWARE_UNVERIFIED; a changed or missing file gives
  SOFTWARE_MODIFIED; an unsupported profile or runtime gives SOFTWARE_UNSUPPORTED.
- **Not checked:** mutable data (TXT, sidecars, manifest, presets, logs, `.pyc`).
- **Custom TXT files** remain supported and need no signature: TXT validation shows the data is valid; the software
  check shows the installed Character Tools can consume it. Compiling and validating (preparation) stay available
  without a verified installation, and recovery of an already-started transaction is never gated. Modified programs
  are never overwritten or repaired by the updater (owner-approved correction, 2026-10-18).

## 5. Deployment and SFM menu integration (for L-6; not deployed)

- **Location:** the application folder goes to `<SFM game>\usermod\tools\SFM Control Group Updater\`, the folder
  the menu entry starts it from. It is never placed in `usermod\scripts`, where SFM would treat files as scripts.
  Started directly, the updater also works from any folder.
- **SFM menu entry (implemented):** `updater/menu/SFM_Control_Group_Updater.py`, installed as
  `usermod\scripts\sfm\mainmenu\SFM Character Tools\SFM_Control_Group_Updater.py` (Scripts > SFM Character Tools;
  profile 2, 2026-10-23).
  - It runs under SFM's Python 2.7.
  - It resolves the SFM `game` folder from `sys.executable`, then starts
    `usermod\tools\SFM Control Group Updater\SFM Control Group Updater.exe` with
    `--sfm-folder <this SourceFilmmaker folder>`. It uses an argument list (no shell), a detached new process group,
    and the updater folder as working directory.
  - It returns at once: it never waits for or talks to the updater, and shows no success popup.
  - When the executable is missing or can't start, one non-modal notice names the expected path and the folder to
    extract into.
  - It imports no updater, CPM or authority code and leaves nothing in SFM's shared Scripts-menu namespace.
  - Installing data still requires SFM to be closed: the updater's process gate refuses while SFM runs.
  - Offline checks: `updater/tests/test_menu_launcher.py`, under SFM Python 2.7.5.
- **Software release (single-ZIP distribution amendment, superseding adjudication ruling 5):** one archive,
  `SFM Character Tools v1.0.0.zip`.
  - Its root `usermod` holds the 31 inventoried scripts, the signed inventory and the menu entry under `scripts`,
    and this one-folder application under `tools\SFM Control Group Updater\`. One copy into `SourceFilmmaker\game`
    installs both.
  - The optional CPM button is in a separate `OPTIONAL - CPM Button` folder with its own README.
  - The external path/SHA-256 manifest is in `release/v1.0.0/`. The signed inventory covers only its 31 files.
- **Data:** official data installs only from packages signed with the production key.
