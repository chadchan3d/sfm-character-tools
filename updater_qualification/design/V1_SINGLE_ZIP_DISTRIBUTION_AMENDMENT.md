# v1 Single-ZIP Distribution Amendment

**Status:** owner-requested, approved by Astra, 2026-10-23. **Narrow; distribution only.** It supersedes only:
- release adjudication ruling 5 / plan decision D5 (separate core and updater ZIPs, with Quick Launch as its own
  optional ZIP);
- the QL-3 requirement that Quick Launch ship as a separate archive;
- the step 8 three-ZIP assembly expectations.

Every other ruling, every product identity and every accepted qualification is unchanged. No executable is rebuilt,
no signature regenerated and no product behavior changed. The signed `data-v1.0.0` package stays separate and
unchanged. This amendment authorizes no L-6 execution or publication.

## Distribution

One archive, `SFM Character Tools v1.0.0.zip`:

```text
README.txt
usermod/
  scripts/        the 31 inventoried files, the signed inventory pair and the updater menu launcher
  tools/
    SFM Control Group Updater/   the unchanged 965-file application
OPTIONAL - CPM Button/
  README.txt
  usermod/scripts/sfm/autoinit/ChadChan3D/ChadChan3D_CPM_ASE_Button.py
  usermod/scripts/ChadChan3D_CPM/cpm_ase_quick_launch.py
```

- There is no enclosing product folder, no nested ZIP and no checksum file inside the archive.
- Copying the root `usermod` into `SourceFilmmaker\game` installs the core tools and the updater together, at the
  location the menu launcher expects. It does not install the optional button, which keeps its QL-3 manual
  install, update and removal safeguards in its own README.
- The 31-file signed inventory authenticates only the files it lists. It does not cover the updater application,
  the menu launcher or the optional button.
- Release evidence stays outside the ZIP: a complete path and SHA-256 manifest of every file in it (both READMEs
  included) and the ZIP checksum. These are committed in `release/v1.0.0/`, with the two READMEs.

## Superseded evidence

The step 8 three-ZIP artifacts (core `7e95519f…`, updater `96067dcc…`, Quick Launch `e3630efd…`, checksums
`9f2760e4…`) and the QL-3 standalone archive are historical, superseded distribution evidence, not product
failures. Their verified contents are the same accepted bytes that the single ZIP carries.
