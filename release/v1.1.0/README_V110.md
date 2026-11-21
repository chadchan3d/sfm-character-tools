# SFM Character Tools v1.1.0: final signed release package

Record: `cpm/qualification/F01_V110_FINAL_PACKAGE.md`. Authority: "SFM Character Tools v1.1.0 — Final GitHub
Documentation Corrections" (Owner, Option C).

The signed RC5 package (`release/v1.1.0-rc5/`, ZIP `9ca68df3…`, preserved) with one change: `OPTIONAL - CPM Button/
README.txt` is the Owner-approved simplified button README of the public v1.0.0 download (`06af2636…`), with its two
version lines changed from v1.0.0 to v1.1.0. The software inventory, the Owner's signature, the CPM, both registries and
the main README are unchanged; the button README is outside `usermod/`, so no re-signing was needed.

| Artifact | SHA-256 |
|---|---|
| **`SFM.Character.Tools.v1.1.0.zip`** (17,846,671 bytes, 1008 entries, signed) | **`0f64eb1306a57f7065db6dcc8419e7e909525a9057af1ee67dce0c8fcc6b8b57`** |
| `SHA256SUMS.txt` (release asset; copy here) | `e2019ba700337ec89f797068109b53984f2fccfbbded7b5ac75d7b3277c03155` |
| `ZIP_CONTENTS_SHA256.txt` (release asset; copy here) | `8985f4c93293031c28ba54e864cc9c3b84b4f996bd857e503d7030f2085d63b9` |
| `README.txt` (main README; copy here) | `af87797bad22e446e002a776d41cdebb5a1a23e236cef74ade9a5705e836a04f` |
| `OPTIONAL - CPM Button/README.txt` (copy here) | `2022457133d2b7f8af9ee3c49402c62eaf42860c86696b6276661328f6d22a9c` |
| CPM | `b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525` |
| Registries | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00`, `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` |
| Signed inventory / signature | `15db1c1aa9a53f59c82c5068d7b60a741f9a35b8de641080311d2ac33864f948` / `28bd1fcaf7583aa7e2fd0b3aaabf568248a0e3f02be850d6724a68d654464ad4` (key `ed25519-5d879134807dff6d`) |
| Unsigned build of the same entries | `b8b4c578bffe48c3ee1ef45d59f98f61efa9af9d4133c58705251cea8827c498` |

`GITHUB_RELEASE_NOTES.md` holds the proposed GitHub release text.

## Build and verify

Python with `cryptography` (the updater build environment), `-I`; `rc.template.json` copied to `<Q>\rc.json`:

1. `v110_tool.py <Q>\rc.json package`, then `verify` (RC VERIFY).
2. `v110_tool.py <Q>\rc.json package-signed <folder with the Owner's inventory.json and .sig>`, then `verify-signed`
   (production-key signature, updater `verify_installation`, version, installer dry run, rollback, identities).
3. `v110_tool.py <Q>\rc.json assets` (the two checksum files).

Two independent builds give identical ZIPs, manifests, verification records and checksum files.
