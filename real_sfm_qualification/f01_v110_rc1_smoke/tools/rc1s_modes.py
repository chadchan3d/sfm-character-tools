# -*- coding: utf-8 -*-
"""F-01 RC1S: the offline production-mode equivalence check, run on the RC1 CPM's own code (ast-extracted, nothing
else of the CPM is executed) and the two RC1 registries.

The CPM's build mode changes only three things: the registry mappings it selects (prod_pose_registry_select), whether
an engine rule is usable (prod_scope_rule_usable) and the qualification-only fault injector. This check establishes,
for the tested models, that production keeps no former qualification restriction and needs no unsupported route:

  production       the RC1 CPM's PROD_POSE_REGISTRY_MODE is "production"
  generic_v3       direct_fk_v1 revision 1 is usable in production exactly as in the qualification build
  carried          constant_channel_carried_v1 is usable in neither mode (disabled; never required by production)
  krystal_v2       production selects the same Krystal full_body mapping as the qualification build, as qualified
  left_arm         production selects the qualified Krystal left_arm mapping (Selected parts, version 1 records)
  only_unqualified the only mappings production leaves out are experimental (the right arm), none used by the smoke
"""
from __future__ import print_function

import ast

NAMES = ("PROD_POSE_REGISTRY_MODE", "PROD_SCOPE_RULE", "PROD_SCOPE_RULES", "PROD_SCOPE_CARRIED_RULE",
         "PROD_SCOPE_CARRIED_REVISION", "PROD_SCOPE_CARRIED_ENABLED")
FUNCTIONS = ("prod_scope_rule_usable", "prod_pose_registry_select")
CLASSES = ("ProdPoseError",)


def extract(cpm_bytes):
    """The named module-level assignments, functions and classes of the CPM, executed alone."""
    tree = ast.parse(cpm_bytes)
    body = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and \
                node.targets[0].id in NAMES:
            body.append(node)
            found.add(node.targets[0].id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in FUNCTIONS + CLASSES:
            body.append(node)
            found.add(node.name)
    missing = sorted(set(NAMES + FUNCTIONS + CLASSES) - found)
    if missing:
        raise ValueError("the CPM does not define %s" % ", ".join(missing))
    if sum(1 for n in body if isinstance(n, ast.Assign)) != len(NAMES):
        raise ValueError("a checked constant is assigned more than once")
    g = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), "rc1-cpm-extract", "exec"), g)
    return g


def keys(selection, region=None):
    return sorted((m["region"], m["from"], m["to"], m["status"]) for m in selection["mappings"]
                  if region is None or m["region"] == region)


def check(cpm_bytes, pose_registry, body_registry, pose_sha256, body_sha256):
    g = extract(cpm_bytes)
    reg = dict(pose_registry)
    reg["_sha256"] = pose_sha256
    body = dict(body_registry)
    body["_sha256"] = body_sha256
    reg["_body"] = body
    prod = g["prod_pose_registry_select"](reg, u"production")
    qual = g["prod_pose_registry_select"](reg, u"qualification")
    rule, carried = g["PROD_SCOPE_RULE"], g["PROD_SCOPE_CARRIED_RULE"]
    usable = g["prod_scope_rule_usable"]
    krystal = ("full_body", "krystal-v1", "krystal-v1", "qualified")
    left = ("left_arm", "krystal-v1", "krystal-v1", "qualified")
    left_out = sorted(set(keys(qual)) - set(keys(prod)))
    r = {
        "production": g["PROD_POSE_REGISTRY_MODE"] == u"production",
        "generic_v3": rule == u"direct_fk_v1" and usable(u"production", rule, 1) is True and
        usable(u"production", rule, 1) == usable(u"qualification", rule, 1) and
        g["PROD_SCOPE_RULES"].get(rule, {}).get(u"status") == u"qualified",
        "carried": carried == u"constant_channel_carried_v1" and g["PROD_SCOPE_CARRIED_ENABLED"] == [False] and
        usable(u"production", carried) is False and usable(u"qualification", carried) is False,
        "krystal_v2": keys(prod, "full_body") == [krystal] and keys(qual, "full_body") == [krystal],
        "left_arm": left in keys(prod, "left_arm"),
        "only_unqualified": all(k[3] == "experimental" for k in left_out),
        "rule_table": dict((k, dict(v)) for k, v in g["PROD_SCOPE_RULES"].items()),
        "production_mappings": [list(k) for k in keys(prod)],
        "not_in_production": [list(k) for k in left_out],
    }
    r["pass"] = all(r[k] for k in ("production", "generic_v3", "carried", "krystal_v2", "left_arm",
                                   "only_unqualified"))
    return r
