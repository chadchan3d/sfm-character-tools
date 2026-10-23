# -*- coding: utf-8 -*-
"""Authority compatibility profiles (L-5; R2 E2-E3).

A profile is the small set of contracts the updater implements and verifies. It binds the installation
layout, Master path resolution, sidecar format and semantics, the canonical compiler and the FINAL
R3-A2B validator/provider identity, the runtime API/build, the CPM and Normalizer consumer contracts,
static admission rules and limits, the installed-publication protocol and the accepted deployment
policy. Its identity is the SHA-256 of its canonical JSON, which a signed software inventory must
name exactly: a profile ID alone (or an unsigned version string) proves nothing.

The values below are the qualified state of K (2026-10-10) and L-1 to L-4, read from the qualified
sources; they are not optimistic version ranges.

Profile 2 (v1.0.0 integration correction, 2026-10-23; menu isolation, same day, before any signing) puts the
three Scripts-menu commands and the signed inventory in scripts/sfm/mainmenu/SFM Character Tools/ (Scripts > SFM
Character Tools) and the internal library (CPM adapter and projection, the authority package, the sidecar reader)
in scripts/SFM Character Tools/, outside the menu tree: SFM lists every .py under scripts/sfm/mainmenu as a menu
item. Every other contract is profile 1's, unchanged. This updater implements profile 2 only; profile 1 is kept as the
historical definition its signed records name.
"""
import copy
import hashlib
import json

PROFILE_1 = {
    "profile_schema": 1,
    "profile_id": "sct-authority-profile-1",
    "installation_layout": {
        "contract": "sct-layout-1",
        "root": "usermod",
        "master": "cfg/sfm_defaultanimationgroups.txt",
        "authority_dir": "cfg/sfm_shared_authority",
        "authority_entries": ["exactly one sfm_master_0_<sha256>.sfmsidecar", "manifest.json",
                              "publisher.lock (optional legacy file, recognized and preserved in place)"],
        "updater_dir": "cfg/sfm_character_tools_updater",
        "user_backup_dir": "cfg/sfm_character_tools_backups",
        "software_inventory": "scripts/sfm/mainmenu/ChadChan3D/sfm_character_tools_inventory.json",
    },
    "master_path_resolution": {
        "contract": "usermod-first-searchpath-1",
        "effective_master": "usermod/cfg/sfm_defaultanimationgroups.txt",
        "consumer_path_limit_exclusive": 260,
    },
    "sidecar": {
        "format_contract_version": 0,
        "authority_semantics_version": 0,
        "magic": "SFMMSTR\\x00",
        "name": "sfm_master_0_<sha256 of sidecar bytes>.sfmsidecar",
        "selection": "first *.sfmsidecar whose source hash matches the effective Master",
    },
    "compiler": {
        "sfm_master_sidecar/__init__.py": "8cad865fd9954035aebb3e02d5c454228e80a095595bd9cd3746df0b357f904c",
        "sfm_master_sidecar/compiler.py": "50dd18045c30aa5258b7821bb02d4f68fc0fa88d4e2fa9a335a2972d4e3f7643",
        "sfm_master_sidecar/format.py": "b401967db8d07943e9f171058a006c30f0e23eb70a7b43bb5ab950203a3c3259",
        "sfm_master_sidecar/manifest.py": "edc646679e326115a4c8f3b52452476db7cf1885c5d7992ff647e5c0d90c5173",
        "sfm_master_sidecar/reader.py": "1b95261c52d95c306b28fc6e5e9340afa65de4ea2574ed29c2bab427d252719f",
        "sfm_master_sidecar/writer.py": "770d5beb1809e425869d12cd697e87fa741f085078589bcb982be8279f07d55d",
        "sfm_master_core.py": "a76e7e4e66f6ee0b4e15f4f2d5c412dcef120240c93d4cd1dd4dd0deff9ef37b",
    },
    "validator_provider": {
        "contract": "final-r3a2b",
        "candidate_packed_validator_r3a2b.py": "74fe8d9655018a9450d0803018d61e42ec3d17b2947b60915df6b598ffc1563f",
        "candidate_packed_provider_r3a2b.py": "d6ef96502194c15e594b3e5754e2f5826af1d0ec01b0b358fff08598f7e6b677",
    },
    "runtime": {"api_version": "1.0.0-b2a", "build_id": "package-boundary-corrected-2026-09-22"},
    "consumers": {
        "cpm": {"provider_contract": "sfm-character-semantic-provider-v1", "projection_contract": "cpm-compat-v1",
                "expected_api_version": "1.0.0-b2a", "expected_build_id": "package-boundary-corrected-2026-09-22"},
        "normalizer": {"projection_contract": "normalizer-compat-adapter-1",
                       "expected_api_version": "1.0.0-b2a",
                       "expected_build_id": "package-boundary-corrected-2026-09-22"},
    },
    "static_admission": {
        "admission": "FINAL R3-A2B bounded provider admission of the exact sidecar bytes for the effective Master",
        "default_runtime_admission_cap_bytes": 16777216,
        "absolute_runtime_cap_ceiling_bytes": 268435456,
        "max_single_fold_occurrence_rows": 20000,
        "retained_gate_bytes": 16777216,
        "transient_gate_bytes": 33554432,
        "max_source_bytes": 67108864,
        "max_sidecar_bytes": 268435456,
        "note": "requested-family cumulative admission stays with the live broker; not a global compiler rule",
    },
    "installed_publication": {
        "transaction_schema": "sct-updater-tx-1",
        "move": "handle rename, ReplaceIfExists=FALSE, journaled, no-clobber",
        "lock": "cfg/sfm_character_tools_updater/installation.lock",
        "offline": "installation only with SFM closed (A3 RUNNING/UNKNOWN refuse)",
    },
    "deployment_policy": {
        "authoritative": "Python 2.7 source (.py) files listed by the signed inventory",
        "bytecode": ".pyc files are derived by SFM's Python 2.7 and are not inventoried",
        "mutable_not_inventoried": ["animation-group TXT", "sidecars", "manifest.json", "publisher.lock",
                                    "presets and libraries", "logs", "updater records and backups"],
    },
}

PROFILE_2 = copy.deepcopy(PROFILE_1)
PROFILE_2["profile_id"] = "sct-authority-profile-2"
PROFILE_2["installation_layout"]["contract"] = "sct-layout-2"
PROFILE_2["installation_layout"]["menu_dir"] = "scripts/sfm/mainmenu/SFM Character Tools"
PROFILE_2["installation_layout"]["library_dir"] = "scripts/SFM Character Tools"
PROFILE_2["installation_layout"]["software_inventory"] =     "scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json"

# The profile this updater implements.
CURRENT = PROFILE_2

REQUIRED_ROLES = ("cpm_app", "cpm_launcher", "cpm_adapter", "cpm_projection", "normalizer", "authority_package",
                  "authority_validator", "authority_provider", "sidecar_reader")


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def contract_sha256(profile):
    return hashlib.sha256(canonical(profile)).hexdigest()


PROFILES = {CURRENT["profile_id"]: CURRENT}
PROFILE_SHA256 = {pid: contract_sha256(p) for pid, p in PROFILES.items()}
