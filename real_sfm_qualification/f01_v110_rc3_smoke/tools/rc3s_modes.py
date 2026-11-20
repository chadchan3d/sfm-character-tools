# -*- coding: utf-8 -*-
"""F-01 RC3S: the offline production-mode check of the RC3 CPM, run on the CPM's own code (ast-extracted; nothing
else of the CPM is executed) and the two RC3 registries.

It keeps every RC1 production-mode check unchanged (rc1s_modes: production mode, generic v3 usable as in the
qualification build, the carried rule disabled, Krystal v2 and the left arm qualified, only experimental mappings left
out), and adds the structural rig adapter that RC3 enables:

  structural_status      PROD_BODY_RIG_STATUS is "qualified"
  structural_production  structural_rig_v1 revisions 1 (Fox) and 2 (Tails' JIGGLE leaves) are usable in production
                         exactly as in the qualification build, so no qualification-only switch is needed
  structural_bounded     an unknown revision (0 or 3), another rule or an unknown build mode stays unusable
"""
from __future__ import print_function

import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "f01_v110_rc1_smoke",
                                "tools"))
import rc1s_modes  # noqa: E402

RIG_NAMES = ("PROD_BODY_RIG_RULE", "PROD_BODY_RIG_REVISION", "PROD_BODY_RIG_LEAF_REVISION",
             "PROD_BODY_RIG_REVISIONS", "PROD_BODY_RIG_STATUS")
RIG_FUNCTIONS = ("prod_body_rig_usable",)


def extract_rig(cpm_bytes):
    """The structural adapter's gate: its constants and prod_body_rig_usable, executed alone."""
    tree = ast.parse(cpm_bytes)
    body, found = [], []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and \
                node.targets[0].id in RIG_NAMES:
            body.append(node)
            found.append(node.targets[0].id)
        elif isinstance(node, ast.FunctionDef) and node.name in RIG_FUNCTIONS:
            body.append(node)
            found.append(node.name)
    if sorted(found) != sorted(RIG_NAMES + RIG_FUNCTIONS):
        raise ValueError("the CPM's structural gate is not defined exactly once: %s" % sorted(found))
    g = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), "rc3-cpm-rig-extract", "exec"), g)
    return g


def check(cpm_bytes, pose_registry, body_registry, pose_sha256, body_sha256):
    r = rc1s_modes.check(cpm_bytes, pose_registry, body_registry, pose_sha256, body_sha256)
    g = extract_rig(cpm_bytes)
    usable, rule = g["prod_body_rig_usable"], g["PROD_BODY_RIG_RULE"]
    revisions = (g["PROD_BODY_RIG_REVISION"], g["PROD_BODY_RIG_LEAF_REVISION"])
    r["structural_status"] = g["PROD_BODY_RIG_STATUS"] == u"qualified"
    r["structural_production"] = rule == u"structural_rig_v1" and revisions == (1, 2) and \
        tuple(g["PROD_BODY_RIG_REVISIONS"]) == revisions and \
        all(usable(u"production", rule, n) is True and usable(u"qualification", rule, n) is True for n in revisions)
    r["structural_bounded"] = not any(usable(m, rule, n) for m in (u"production", u"qualification") for n in (0, 3)) \
        and not usable(u"production", u"other_rule_v1", 1) and not usable(u"other", rule, 1) and \
        not usable(u"production", rule, True)
    r["pass"] = r["pass"] and r["structural_status"] and r["structural_production"] and r["structural_bounded"]
    return r
