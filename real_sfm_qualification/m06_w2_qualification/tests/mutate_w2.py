# -*- coding: utf-8 -*-
"""M-06 W2 instrument mutation check: each mutant is one deliberate defect applied to a scratch copy of the W2
folder; the full offline suite (this interpreter) must fail. The W2 folder itself is never modified.

usage: python -B mutate_w2.py RESULTS_JSON
"""
from __future__ import print_function

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
REPO_APP = os.path.join(os.path.dirname(os.path.dirname(SRC)), "cpm", "app", "SFM_Character_Preset_Manager.py")
C, K, J, S, P, Q = ("tools/compare_obs.py", "instruments/m06w2_core.py",
                    "instruments/M06_Qualification_Abort_Injector.py", "tools/scan_deferred_fixture.py",
                    "native/M06_Deferred_Fixture_Preparation.py", "tools/compare_probes.py")
O, T = "instruments/M06_Qualification_Observer.py", "tools/stage_instruments.py"
# W01-W30: the previous W2 defect classes, retargeted at the corrected code where the text moved (same defect).
# W31-W62: the Astra-required corrections (findings 1-6), one deliberate regression each.
# W63-W80: Astra's final W2 review (R1 compressed data, R2A empty output log, R2B EMPTY -> one key, R3 configuration).
# W81-W82: Astra's configuration-digest ruling (R4).
MUTANTS = [
    ("W01 presence disagreement read as absence", K,
     'return ABSENT if has is False else unreadable(u"GetAttribute(%s) returned None but HasAttribute is True" % attr)',
     "return ABSENT"),
    ("W02 unreadable array reported empty", K,
     'return (r if r["s"] != u"null" else unreadable(u"array attribute %s is null" % attr)), None',
     "return present(0), []"),
    ("W03 scale writer without the scale attribute", K,
     'for w in scene.writers(k, "scale")]})', "for w in scene.writers(k)]})"),
    ("W04 unresolved channels not tracked", K, "            self.unresolved.append(crec[\"v\"])", "            pass"),
    ("W05 pointer-style id accepted", K,
     'if not uid_text or uid_text.startswith(u"<") or u" at 0x" in uid_text.lower():', "if not uid_text:"),
    ("W06 end context not compared", K, '    if record["context_end"] != record["context_begin"]:', "    if False:"),
    ("W07 non-boolean Undo flag accepted", K, 'out[k] = present(v) if type(v) is bool else',
     "out[k] = present(v) if True else"),
    ("W08 representation ignores the stored source", K, "        if k == stored:", "        if False:"),
    ("W09 created channels not recorded", K, '                add(ch, u"channel")', "                pass"),
    ("W10 unreadable markers not scanned", C, '            if value["s"] not in STATES:', "            if False:"),
    ("W11 required fields not enforced", C, "    missing = [k for k in keys if k not in obj]", "    missing = []"),
    ("W12 changed context accepted", C, '    if obs["context_begin"] != obs["context_end"]:', "    if False:"),
    ("W13 wrong instance accepted", C, "                if kf(va) != kf(vb):", "                if False:"),
    ("W14 Undo change accepted as unchanged", C, "    if undo_fields(a) != undo_fields(b):", "    if False:"),
    ("W15 attached created element accepted after abort", C, "        if i in attached:", "        if False:"),
    ("W16 resolvable created element accepted after abort", C, '        if now.get("s") != "gone":',
     "        if False:"),
    ("W17 undeclared Apply change accepted", C,
     '    reasons.extend("undeclared Apply change: %s" % d for d in differences(pa, pb)[:40])', "    pass"),
    ("W18 replaced existing graph accepted", C, "            if graph_ids(ga[0]) != graph_ids(gb[0]):",
     "            if False:"),
    ("W19 incomplete preset bone coverage accepted", C,
     "    if sorted(seen) != sorted(bones) or any(len(v) != 1 for v in seen.values()):", "    if False:"),
    ("W20 one-sided key treated as equal", C, "            if k not in a or k not in b:\n                out.append(",
     "            if False:\n                out.append("),
    ("W21 undeclared literal set accepted", C,
     "                if rec is not None and sorted(rec.get(kind) or {}) != sorted(declared[listing]):",
     "                if False:"),
    ("W22 other changes accepted in fixture preparation", C,
     '    reasons.extend("undeclared change: %s" % d for d in differences(pa, pb)[:40])', "    pass"),
    ("W23 sole-writer admission evidence ignored", C,
     '    if [w.get("id") for w in pv(side["destination_writers"]) or []] != [pv(side["channel"])["id"]]:',
     "    if False:"),
    ("W24 injector pin removed", J, "    if installed != CANDIDATE_SHA256:", "    if False:"),
    ("W25 injector arms on an incomplete baseline", J, '    if not baseline["complete"]:', "    if False:"),
    ("W26 fixture scan ignores the channel mode", S, '        if d.val(ch, "mode") != 3:', "        if False:"),
    ("W27 fixture scan ignores the graph input mode", S,
     'd.val(o, "toAttribute") == "scale" and d.val(cin, "mode") == 3 and', 'd.val(o, "toAttribute") == "scale" and'),
    ("W28 preparation on the wrong document", P,
     '    if norm(path) != norm(prep["disposable_copy"]) or norm(path) == norm(prep["protected_original"]):',
     "    if False:"),
    ("W29 surviving reload keys accepted", Q, "        if not changed:\n            failures.append(",
     "        if False:\n            failures.append("),
    ("W30 presence disagreement accepted by the probe evaluation", Q,
     '        ok = (has == "has=True(bool)" and get == "get=attribute") or \\', "        ok = True or \\"),
    # ---- finding 1: Observer completeness and independent nested validation
    ("W31 layer curveinfo not read", K,
     '    crec, _ = element_ref(layer, "curveinfo")\n    rec["curveinfo"] = ob.require(path + u"/curveinfo", crec)',
     '    rec["curveinfo"] = ABSENT'),
    ("W32 installed CPM mismatch not insufficient in the Observer", K,
     '            ob.insufficient.append(u"integrity/cpm: installed CPM %s is not the accepted W1 candidate" % '
     'actual[:16])', "            pass"),
    ("W33 created logs not inventoried", K, '                        add(log["log"]["v"], u"log")',
     "                        pass"),
    ("W34 nested log evidence not validated", C, '    check_log(view["log"], path + "/log", problems)', "    pass"),
    ("W35 raw key arrays not reconciled with the keys", C,
     "        if len(times) != len(keys) or len(values) != len(keys) or raw != keys:", "        if False:"),
    ("W36 claimed representation trusted", C, "    if claimed != representation_of(side):", "    if False:"),
    ("W37 CPM identity trusted", C,
     '    if not isinstance(cpm, dict) or cpm.get("actual") != ACCEPTED_W1_SHA256 or cpm.get("match") is not True:',
     "    if False:"),
    # ---- finding 2: Apply preserves undeclared state
    ("W38 declared literal's whole log removed from the comparison", C,
     '    s["log"] = mask_log_values(side["log"], empty_origin)', '    s["log"] = DECLARED'),
    ("W39 stored source masked though declared unchanged", C,
     '    if stored_declared:\n        s["stored"] = DECLARED', '    if True:\n        s["stored"] = DECLARED'),
    ("W40 undeclared stereo side masked", C,
     "        for side, want in sorted(sides.items()):",
     "        for side, want in sorted(dict((x, sides.get(x, list(sides.values())[0])) for x in "
     "(('mono',) if ra['shape'] == 'MONO' else ('left', 'right'))).items()):"),
    ("W41 scale control source value not checked", C,
     '        if not close(pv(view["source_attributes"]["value"]), cv, tol):', "        if False:"),
    ("W42 scale control value not required in the SPEC", C,
     "    if not number(cv) or not number(scale):", "    if not number(scale):"),
    ("W43 scale expression masked", C,
     '    m["operator_attributes"]["value"] = m["operator_attributes"]["result"] = DECLARED',
     '    m["operator_attributes"] = DECLARED'),
    # ---- finding 3: abort and graph-removal proof
    ("W44 recorded creation list not reconciled", C, "    if sorted(recorded) != sorted(created):",
     "    if False:"),
    ("W45 fired event, injector or candidate not checked", C,
     '    if fired["event"] != "fired" or fired["injector"] != "v3" or fired["candidate_sha256"] != ACCEPTED_W1_SHA256:',
     "    if False:"),
    ("W46 armed baseline not compared with A", C, "    if differences(authored(a), authored(baseline)):",
     "    if False:"),
    ("W47 recorded peer change ignored", C, '    if fired["peer_changes"] != [] or peer_diffs:', "    if False:"),
    ("W48 in-transaction observation not validated", C, '    sufficiency(during, "fired/in_transaction")',
     "    pass"),
    ("W49 missing resolvability evidence accepted", C,
     '        if now is None:\n            insufficient(', '        if now is None:\n            continue\n            insufficient('),
    # ---- finding 4: reload prerequisite checker
    ("W50 unreadable token component accepted", Q, '        if not isinstance(rec, dict) or rec.get("s") != "present" or "v" not in rec:',
     '        if not isinstance(rec, dict) or "v" not in rec and rec.get("s") == "present":'),
    ("W51 document file id change ignored", Q, '    if tb["document_file_id"]["v"] != ta["document_file_id"]["v"]:',
     "    if False:"),
    ("W52 incomplete presence coverage accepted", Q, "        if n != examined:", "        if False:"),
    ("W53 empty presence coverage accepted", Q, "            examined <= 0:", "            examined < 0:"),
    # ---- finding 5: configuration selection and the output-mode gate
    ("W54 graph output mode not checked", C,
     '        if pv(g["output"]["mode"]) != 3 or any(pv(i["mode"]) != 3 for i in g["inputs"]):',
     '        if any(pv(i["mode"]) != 3 for i in g["inputs"]):'),
    ("W55 fixture scan ignores the graph output mode", S, '                                          d.val(o, "mode") == 3)})',
     "                                          True)})"),
    ("W56 Save As offered without a prepared PASS", P, '    if verdict != compare["PASS"]:', "    if False:"),
    ("W57 preparation does not verify its configuration", P,
     '    if config.get("config_name") != u"m06w2_deferred_config.json":', "    if False:"),
    ("W58 Observer does not verify its configuration", O, '        if config.get("config_name") != CONFIG_NAME:',
     "        if False:"),
    ("W59 deferred Observer not staged", T,
     "    staged += [(OBSERVER[0], OBSERVER[1], OBSERVERS[c], c) for c in CONFIGS if c in configs]",
     "    staged += [(OBSERVER[0], OBSERVER[1], OBSERVERS[c], c) for c in CONFIGS[:1] if c in configs]"),
    # ---- finding 6: effective value from the verified representation
    ("W60 EMPTY effective value without coherence", C,
     "        if not (number(stored) and close(stored, evaluated, CPM_EPS) and close(stored, dest, CPM_EPS)):",
     "        if not number(stored):"),
    ("W61 EMPTY recognised without IsEmpty", C,
     '        return "EMPTY" if pv(log["is_empty"]) is True else "OTHER"', '        return "EMPTY"'),
    ("W62 preset reads the first key (previous defect)", C,
     "            want, problem = effective_value(row[side])",
     '            want, problem = pv(pv(row[side]["log"])["layers"][0]["keys"])[0][1], None'),
    # ---- R1: compressed data
    ("W63 compressed data masked as an authored value (previous defect)", C,
     '        layer["values"] = DECLARED\n    return {"s": "present", "v": log}',
     '        layer["values"] = DECLARED\n        layer["compressed"] = DECLARED\n    return {"s": "present", "v": log}'),
    ("W64 zero-length block accepted with any digest", C,
     '    if n == 0:\n        return "empty" if h == EMPTY_SHA256 else "malformed"', '    if n == 0:\n        return "empty"'),
    ("W65 malformed compressed record accepted", C, '        if compressed_state(layer) == "malformed":',
     "        if False:"),
    ("W66 static play recognised with compressed data (comparator)", C,
     '            and compressed_state(layer) in ("absent", "empty"))', "            and True)"),
    ("W67 static play claimed with compressed data (core)", K,
     "        if mode == 3 and k == evaluated and k == dest and static_play_metadata(log):",
     "        if mode == 3 and k == evaluated and k == dest:"),
    # ---- R2A: the M-05 empty output log
    ("W68 output log masked again", C,
     '    m = copy.deepcopy(g)\n    for view, orig in zip(m["inputs"], g["inputs"]):',
     '    m = copy.deepcopy(g)\n    m["output"]["log"] = mask_log_values(g["output"]["log"])\n'
     '    for view, orig in zip(m["inputs"], g["inputs"]):'),
    ("W69 physical result not checked against lerp(control)", C, "            if not close(got, expected, tol):",
     "            if False:"),
    ("W70 output representation not checked", C,
     "    problems.extend(output_representation_problems(g))\n    return problems", "    return problems"),
    ("W71 mode-3 output usedefaultvalue not required", C, '            pv(out["usedefaultvalue"]) is not False:',
     "            False:"),
    ("W72 unsupported scale expression accepted", C,
     '    if not isinstance(expr, TEXT) or expr.replace(" ", "") != "lerp(value,lo,hi)":',
     "    if not isinstance(expr, TEXT):"),
    # ---- R2B: EMPTY origin -> one key at time zero
    ("W73 EMPTY-origin write not validated", C,
     '            if origin == "EMPTY":\n                reasons.extend(', '            if False:\n                reasons.extend('),
    ("W74 EMPTY-origin key time not checked", C,
     '        if keys[0][0] != 0 or [t.get("ticks") for t in times] != [0]:', "        if False:"),
    ("W75 key structure exempted for every origin", C,
     '            ra[side] = mask_side(ra[side], stored != "unchanged", origin == "EMPTY")\n'
     '            rb[side] = mask_side(sb, stored != "unchanged", origin == "EMPTY")',
     '            ra[side] = mask_side(ra[side], stored != "unchanged", True)\n'
     '            rb[side] = mask_side(sb, stored != "unchanged", True)'),
    ("W76 unsupported origin representation accepted", C, "            if origin not in SUPPORTED_ORIGINS:",
     "            if False:"),
    # ---- R3: configuration handoff
    ("W77 configuration identity not required across the abort evidence", C,
     "    if names != [ORDINARY_CONFIG] * 4:", "    if False:"),
    ("W78 injector baseline omits the configuration identity", J,
     '    baseline = core["observe"](sfmApp, vs, config, label=u"injector-armed-baseline", config_name=CONFIG_NAME)',
     '    baseline = core["observe"](sfmApp, vs, config, label=u"injector-armed-baseline")'),
    ("W79 injector in-transaction observation omits the configuration identity", J,
     '                during = core["observe"](sfmApp, vs, config, label=u"injector-in-transaction",\n'
     '                                         config_name=CONFIG_NAME)',
     '                during = core["observe"](sfmApp, vs, config, label=u"injector-in-transaction")'),
    ("W80 injector does not verify its configuration", J,
     '    if config.get("config_name") != CONFIG_NAME:\n        # The staged',
     '    if False:\n        # The staged'),
    # ---- R4: configuration digests
    ("W81 config_sha256 not validated (previous defect)", C, '    if not sha256_text(obs["config_sha256"]):',
     "    if False:"),
    ("W82 any text accepted as a configuration digest", C,
     '    return isinstance(value, TEXT) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)',
     "    return isinstance(value, TEXT)"),
]


def main(results_path):
    out = {}
    for name, rel, old, new in MUTANTS:
        work = tempfile.mkdtemp(prefix="m06w2_mut_")
        tree = os.path.join(work, "w2")
        shutil.copytree(SRC, tree)
        path = os.path.join(tree, rel)
        with io.open(path, encoding="utf-8") as f:
            text = f.read()
        if text.count(old) != 1:
            raise SystemExit("%s: target text found %d times" % (name, text.count(old)))
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace(old, new))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", M06W2_W1_APP=REPO_APP)
        proc = subprocess.Popen([sys.executable, "-B", os.path.join(tree, "tests", "test_m06w2.py")],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.join(tree, "tests"),
                                env=env)
        text = proc.communicate()[0].decode("utf-8", "replace")
        failing = re.findall(r"^(?:FAIL|ERROR): (\S+) \((?:__main__\.)?(\w+)\)", text, re.M)
        out[name] = {"file": rel, "returncode": proc.returncode, "failing_tests": len(failing),
                     "first_failing": ["%s.%s" % (c, t) for t, c in failing[:5]],
                     "detected": proc.returncode != 0 and len(failing) > 0}
        print("%-62s detected=%s failing=%d" % (name, out[name]["detected"], len(failing)))
        shutil.rmtree(work, True)
    with io.open(results_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"python": sys.version, "mutants": out}, indent=1, sort_keys=True).encode("ascii")
                .decode("ascii"))
    print("detected %d/%d" % (sum(1 for r in out.values() if r["detected"]), len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
