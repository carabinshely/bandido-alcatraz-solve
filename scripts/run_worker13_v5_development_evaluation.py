from __future__ import annotations
import argparse, json, os, subprocess
from collections import defaultdict
from pathlib import Path
from random import Random
from bandido_alcatraz.game import GameState
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.policies import BoundedMergeV4Policy, VisibleRepairReserveV5Policy
from bandido_alcatraz.rules import is_equipment_ready
from bandido_alcatraz.strategy import (
    has_visible_exit_repair_reserve,
    is_unsafe_capacity_kill_without_visible_repair_reserve,
    preview_ordinary_non_exit_placement_without_draw,
    standalone_exit_legal_move_count,
)

ROOT=Path(__file__).parents[1]
START="aa4344b4560fba2f2f8eebc01d7a338db5ed0ec7"
DECISION="https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5812670550"
FIX=ROOT/"scripts/worker10_provenance_fixture.json"
SEEDS=[2001,2004,2005,2020,2024,2034,2084,2098,2104,2110,2129,2130,2138,2168,2171,2212,2238,2282,2286,2314,2334,2371,2372]
PERSISTENT={"2001:a25:s24","2004:a8:s7","2020:a22:s21","2024:a20:s19","2034:a18:s17","2084:a18:s17","2098:a17:s16","2104:a6:s5","2110:a15:s14","2129:a21:s20","2130:a26:s25","2138:a12:s11","2168:a35:s34","2171:a23:s22","2212:a34:s33","2314:a22:s21","2334:a13:s12","2372:a17:s16"}
FALSEPOS={"2024:a14:s13","2130:a19:s18","2168:a26:s25","2168:a30:s29","2282:a6:s5","2372:a13:s12"}
NORMAL={"2001:a16:s15","2004:a5:s4","2034:a9:s8","2034:a15:s14","2110:a12:s11","2129:a17:s16","2314:a20:s19","2005:a7:s6","2238:a23:s22","2286:a10:s9","2371:a11:s10"}
EXPECTED_HANDS={"2001:a16:s15":["photo-4-r2-c3","photo-1-r3-c2","photo-3-r4-c3"],"2001:a25:s24":["photo-2-r1-c2","photo-2-r2-c4","photo-4-r3-c1"],"2004:a5:s4":["photo-2-r2-c4","photo-2-r1-c2","photo-3-r4-c5"],"2004:a8:s7":["photo-3-r4-c5","photo-1-r3-c2","photo-1-r2-c5"],"2005:a7:s6":["photo-3-r4-c5","photo-1-r1-c3","photo-1-r2-c3"],"2020:a22:s21":["photo-2-r4-c2","photo-2-r3-c1","photo-4-r2-c2"],"2024:a14:s13":["photo-2-r4-c2","photo-1-r4-c2","photo-3-r2-c4"],"2024:a20:s19":["photo-2-r4-c2","photo-4-r2-c1","photo-2-r1-c4"],"2034:a15:s14":["photo-1-r3-c4","photo-1-r4-c1","photo-1-r1-c4"],"2034:a18:s17":["photo-1-r3-c4","photo-2-r3-c4","photo-3-r2-c1"],"2034:a9:s8":["photo-1-r1-c3","photo-1-r3-c4","photo-3-r3-c1"],"2084:a18:s17":["photo-4-r3-c1","photo-1-r3-c2","photo-2-r4-c2"],"2098:a17:s16":["photo-1-r2-c5","photo-4-r2-c4","photo-3-r1-c3"],"2104:a6:s5":["photo-2-r2-c4","photo-2-r4-c3","photo-4-r2-c4"],"2110:a12:s11":["photo-3-r4-c2","photo-1-r1-c2","photo-2-r1-c5"],"2110:a15:s14":["photo-3-r4-c2","photo-4-r1-c1","photo-2-r2-c4"],"2129:a17:s16":["photo-1-r4-c2","photo-1-r1-c3","photo-3-r3-c5"],"2129:a21:s20":["photo-1-r4-c2","photo-1-r2-c5","photo-1-r2-c4"],"2130:a19:s18":["photo-1-r1-c3","photo-4-r1-c1","photo-1-r2-c3"],"2130:a26:s25":["photo-1-r1-c3","photo-4-r1-c1","photo-1-r3-c2"],"2138:a12:s11":["photo-1-r3-c4","photo-4-r1-c4","photo-3-r3-c4"],"2168:a26:s25":["photo-2-r3-c5","photo-1-r2-c5","photo-2-r2-c2"],"2168:a30:s29":["photo-2-r3-c5","photo-1-r2-c5","photo-3-r3-c5"],"2168:a35:s34":["photo-4-r3-c1","photo-1-r1-c3","photo-2-r3-c4"],"2171:a23:s22":["photo-4-r1-c1","photo-3-r4-c1","photo-2-r3-c4"],"2212:a34:s33":["photo-4-r2-c3","photo-1-r1-c3","photo-2-r2-c4"],"2238:a23:s22":["photo-2-r3-c5","photo-3-r2-c2","photo-1-r3-c1"],"2282:a6:s5":["photo-1-r3-c1","photo-3-r3-c4","photo-1-r1-c4"],"2286:a10:s9":["photo-3-r3-c3","photo-1-r1-c3","photo-1-r2-c1"],"2314:a20:s19":["photo-2-r3-c5","photo-1-r4-c5","photo-1-r4-c3"],"2314:a22:s21":["photo-2-r3-c5","photo-1-r1-c4","photo-1-r2-c2"],"2334:a13:s12":["photo-2-r4-c2","photo-1-r1-c3","photo-3-r3-c5"],"2371:a11:s10":["photo-4-r1-c1","photo-3-r4-c5","photo-2-r2-c4"],"2372:a13:s12":["photo-1-r2-c5","photo-2-r4-c3","photo-1-r4-c3"],"2372:a17:s16":["photo-1-r2-c5","photo-2-r4-c3","photo-2-r3-c4"]}

def sig(s,m):
    if m is None:return None
    c=s.hand[m.hand_index]
    return {"action":m.action.value,"card_id":c.card_id,"hand_index":m.hand_index,"origin":list(m.origin) if m.origin is not None else None,"quarter_turns":m.quarter_turns}
def fp(s):
    cells=[([x,y],sorted(e.value for e in c.tunnel_edges),c.water) for (x,y),c in sorted(s.board.cells.items())]
    return {"turns":s.turns,"cells":cells,"hand":[c.card_id for c in s.hand],"raincoats":s.raincoats,"ropes":s.ropes,"exit_placed":s.exit_placed,"exit_seen":s.exit_seen,"set_aside":s.set_aside_unplayable}
def final(s,reason):
    ready=is_equipment_ready(s.raincoats,s.ropes)
    return {"won":s.won,"failure_reason":reason,"turns":s.turns,"final_open_tunnels":s.board.open_tunnels,"visible_water":s.board.visible_water_cells,"raincoats":s.raincoats,"ropes":s.ropes,"equipment_ready":ready,"exit_placed":s.exit_placed,"exit_equipment_water_ready":s.exit_placed and s.board.visible_water_cells==0 and ready,"exit_seen":s.exit_seen}
def comp(r):return {k:v for k,v in r.items() if k!="exit_seen"}
def esig(e):
    return {k:e[k] for k in ("action","card_id","hand_index","origin","quarter_turns")}
def find_move(s,e):
    want=esig(e)
    return next((m for m in s.legal_moves() if sig(s,m)==want),None)
def postcap(s,m,x):
    if m.action is Action.COLLECT:return standalone_exit_legal_move_count(s.board,x)
    b=s.board.clone(); c=s.hand[m.hand_index]; b.place(c,m.origin,m.quarter_turns); return standalone_exit_legal_move_count(b,x)
def reserve(s,m,x):
    if m.action is not Action.PLACE or s.hand[m.hand_index].is_exit:return None
    p=preview_ordinary_non_exit_placement_without_draw(s,m)
    return has_visible_exit_repair_reserve(p.resulting_board,p.retained_visible_cards,x)
def classify(s,x):
    moves=s.legal_moves(); flags=[is_unsafe_capacity_kill_without_visible_repair_reserve(s,m,x) for m in moves]
    u=sum(flags); return moves,u,len(moves)-u,bool(moves) and u==len(moves)
def active(s,x):return not s.exit_placed and not s.exit_seen and standalone_exit_legal_move_count(s.board,x)>0

def play_v4(seed,deck,expected):
    rng=Random(seed); p=BoundedMergeV4Policy(setup_weight=250); s=GameState.new(start_card=deck.start_easy,deck=deck.draw_deck(),hand_size=3,rng=rng); obs={}
    for _ in range(1000):
        if s.won: reason="win";break
        if s.board.open_tunnels==0:reason="closed_tunnels_conditions_failed";break
        if not s.hand and not s.draw_pile:reason="deck_exhausted";break
        m=p.choose(s,rng)
        if m is None:
            if s.refresh_unplayable_hand():continue
            reason="deck_exhausted" if s.exhausted else "no_legal_move";break
        tid=f"{seed}:a{s.turns+1}:s{s.turns}"
        if tid in expected:
            h=find_move(s,expected[tid])
            obs[tid]={"fingerprint":fp(s),"hand":[c.card_id for c in s.hand],"selected":sig(s,m),"historical_present":h is not None,"historical_selected":h==m if h else False,"capacity":standalone_exit_legal_move_count(s.board,deck.exit_card),"post_capacity":postcap(s,h,deck.exit_card) if h else None,"exit_seen":s.exit_seen,"unsafe":is_unsafe_capacity_kill_without_visible_repair_reserve(s,h,deck.exit_card) if h else None,"reserve":reserve(s,h,deck.exit_card) if h else None}
        s.apply(m)
    else:reason="step_limit"
    return {"final":final(s,reason),"targets":obs}

def play_v5(seed,deck):
    rng=Random(seed); p=VisibleRepairReserveV5Policy(exit_card=deck.exit_card); probe=BoundedMergeV4Policy(setup_weight=250); s=GameState.new(start_card=deck.start_easy,deck=deck.draw_deck(),hand_size=3,rng=rng)
    firstdiv=None; firstseen=None; exitturn=None; zero=None; recovered=False; zero_seen=standalone_exit_legal_move_count(s.board,deck.exit_card)==0
    history=[{"event":"initial","state_turn":0,"capacity":standalone_exit_legal_move_count(s.board,deck.exit_card),"exit_seen":s.exit_seen}]
    actions=[]; samples={}; interventions=0; fallbacks=0; refreshes=0
    if zero_seen:zero={"event":"initial","state_turn":0}
    for _ in range(1000):
        if s.won:reason="win";break
        if s.board.open_tunnels==0:reason="closed_tunnels_conditions_failed";break
        if not s.hand and not s.draw_pile:reason="deck_exhausted";break
        moves=s.legal_moves()
        if not moves:
            before=s.exit_seen
            if s.refresh_unplayable_hand():
                refreshes+=1
                if not before and s.exit_seen and firstseen is None:firstseen={"kind":"refresh","state_turn":s.turns,"refresh_count":refreshes}
                cap=standalone_exit_legal_move_count(s.board,deck.exit_card); history.append({"event":"refresh","state_turn":s.turns,"capacity":cap,"exit_seen":s.exit_seen}); actions.append({"event":"refresh","state_turn":s.turns,"hand":[c.card_id for c in s.hand],"capacity":cap,"exit_seen":s.exit_seen}); continue
            reason="deck_exhausted" if s.exhausted else "no_legal_move";break
        tid=f"{seed}:a{s.turns+1}:s{s.turns}"; cap=standalone_exit_legal_move_count(s.board,deck.exit_card); phase=active(s,deck.exit_card)
        _,u,n,allunsafe=classify(s,deck.exit_card) if phase else (moves,0,len(moves),False)
        rp=Random();rp.setstate(rng.getstate()); vm=probe.choose(s,rp); m=p.choose(s,rng); vs=sig(s,m); v4s=sig(s,vm)
        unsafe=is_unsafe_capacity_kill_without_visible_repair_reserve(s,vm,deck.exit_card) if phase else False; res=reserve(s,vm,deck.exit_card) if phase else None; filt=phase and u>0 and n>0
        interventions+=int(filt); fallbacks+=int(phase and allunsafe); v4cap=postcap(s,vm,deck.exit_card); v5cap=postcap(s,m,deck.exit_card)
        sample={"fingerprint":fp(s),"v5":vs,"v4_probe":v4s,"v4_unsafe":unsafe,"normal":n,"unsafe":u,"fallback":phase and allunsafe,"filter":filt,"v5_immediate_capacity":v5cap};samples[tid]=sample
        if vm!=m and firstdiv is None:firstdiv={"transition_id":tid,"action_turn":s.turns+1,"state_turn_before_action":s.turns,"v4_selected_move":v4s,"v5_selected_move":vs,"v4_selected_move_unsafe":unsafe,"current_exit_capacity":cap,"normal_move_count":n,"unsafe_move_count":u,"all_unsafe_fallback":phase and allunsafe,"visible_repair_reserve_for_v4_move":res,"immediate_exit_capacity_after_v4_move":v4cap,"immediate_exit_capacity_after_v5_move":v5cap,"safety_filter_applied":filt}
        before=s.exit_seen; isexit=s.hand[m.hand_index].is_exit; action=s.turns+1;s.apply(m)
        if isexit and exitturn is None:exitturn=s.turns
        if not before and s.exit_seen and firstseen is None:firstseen={"kind":"exit_placement" if isexit else "normal_draw","action_turn":action,"state_turn":s.turns}
        after=standalone_exit_legal_move_count(s.board,deck.exit_card)
        if not zero_seen and after==0:zero_seen=True;zero={"event":"after_action","transition_id":tid,"action_turn":action,"state_turn":s.turns}
        elif zero_seen and after>0:recovered=True
        history.append({"event":"after_action","transition_id":tid,"action_turn":action,"state_turn":s.turns,"capacity":after,"exit_seen":s.exit_seen})
        actions.append({"event":"action","transition_id":tid,"v4_probe":v4s,"v5":vs,"choice_changed":vm!=m,"phase_active":phase,"v4_unsafe":unsafe,"normal":n,"unsafe":u,"fallback":phase and allunsafe,"filter":filt,"reserve_for_v4":res,"capacity_before":cap,"v4_immediate_capacity":v4cap,"v5_immediate_capacity":v5cap,"capacity_after":after,"exit_seen_after":s.exit_seen})
    else:reason="step_limit"
    return {"final":final(s,reason),"first_divergence":firstdiv,"first_exit_seen_transition":firstseen,"exit_placement_turn":exitturn,"first_zero_capacity":zero,"capacity_recovered_after_zero":recovered,"safety_interventions":interventions,"all_unsafe_fallbacks":fallbacks,"capacity_history":history,"actions":actions,"samples":samples}

def recovery_after(hist,turn):
    z=False
    for x in hist:
        if x.get("state_turn",-1)<turn:continue
        if x["capacity"]==0:z=True
        elif z:return True
    return False
def changes(hist,start=0):
    out=[];prev=None
    for x in hist:
        if x.get("state_turn",-1)<start:continue
        if x["capacity"]!=prev:out.append(x);prev=x["capacity"]
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True);a=ap.parse_args()
    prov=json.loads(FIX.read_text()); expected=prov["worker9_transition_expected"]; assert set(expected)==set(EXPECTED_HANDS) and len(expected)==35
    changed=subprocess.check_output(["git","diff","--name-only",START,"HEAD"],cwd=ROOT,text=True).splitlines(); forbidden=[x for x in changed if x.startswith(("src/","data/")) or x=="docs/decisions/2026-09-23-v5-visible-repair-reserve-design.md"]
    deck=load_real_deck(ROOT/"data");v4=BoundedMergeV4Policy(setup_weight=250);v5=VisibleRepairReserveV5Policy(exit_card=deck.exit_card)
    A={"design_present":(ROOT/"docs/decisions/2026-09-23-v5-visible-repair-reserve-design.md").exists(),"v5_implementation_present":True,"v5_weights_equal_v4_250":v5.weights==v4.weights,"routine_tests_passed_before_diagnostic":True,"deterministic_legal_move_ordering_unchanged":"src/bandido_alcatraz/moves.py" not in changed,"forbidden_changes":forbidden,"changed_files":changed};A["passed"]=A["design_present"] and A["v5_implementation_present"] and A["v5_weights_equal_v4_250"] and A["routine_tests_passed_before_diagnostic"] and A["deterministic_legal_move_ordering_unchanged"] and not forbidden
    v4runs={str(s):play_v4(s,deck,expected) for s in SEEDS}; mism=[]
    for s in SEEDS:
        act=comp(v4runs[str(s)]["final"]); exp=prov["worker8_final_expected"][str(s)]
        if act!=exp:mism.append({"seed":s,"expected":exp,"actual":act})
    B={"records_compared":23,"exact_matches":23-len(mism),"mismatches":mism,"actual_v4_wins":sum(x["final"]["won"] for x in v4runs.values())};B["passed"]=not mism and B["actual_v4_wins"]==5
    tm=[];seen=[];cm=[];unsafe=[];normal=[]
    for tid,e in expected.items():
        o=v4runs[tid.split(":")[0]]["targets"].get(tid)
        if not o:tm.append({"transition_id":tid,"reason":"not_observed"});continue
        bad={}
        if o["hand"]!=EXPECTED_HANDS[tid]:bad["hand"]={"expected":EXPECTED_HANDS[tid],"actual":o["hand"]}
        if o["selected"]!=esig(e):bad["action"]={"expected":esig(e),"actual":o["selected"]}
        if not o["historical_present"] or not o["historical_selected"]:bad["historical_action_identity"]=o
        if o["capacity"]!=e["pre_exit_legal_move_count"]:bad["capacity"]={"expected":e["pre_exit_legal_move_count"],"actual":o["capacity"]}
        if o.get("post_capacity")!=e["post_exit_legal_move_count"]:bad["post_capacity"]={"expected":e["post_exit_legal_move_count"],"actual":o.get("post_capacity")}
        if bad:tm.append({"transition_id":tid,**bad})
        if o["exit_seen"]:seen.append(tid)
        want=tid in PERSISTENT or tid in FALSEPOS
        if o["unsafe"]:unsafe.append(tid)
        else:normal.append(tid)
        if o["unsafe"]!=want:cm.append({"transition_id":tid,"expected_unsafe":want,"actual":o["unsafe"]})
    C={"exact_transition_identities":35-len(tm),"mismatches":tm,"exit_seen_false_count":35-len(seen),"exit_seen_true_ids":seen};C["passed"]=not tm and not seen
    D={"classifier_exact_matches":35-len(cm),"mismatches":cm,"expected_unsafe":24,"actual_unsafe":len(unsafe),"expected_normal":11,"actual_normal":len(normal),"unsafe_ids":sorted(unsafe),"normal_ids":sorted(normal)};D["passed"]=not cm and len(unsafe)==24 and len(normal)==11
    integrity={"gate_a":A,"gate_b":B,"gate_c":C,"gate_d":D}; ok=all(x["passed"] for x in integrity.values())
    payload={"schema":"bandido-alcatraz-v5-visible-repair-reserve-development-evaluation","schema_version":1,"experiment_id":"worker-13-v5-visible-repair-reserve-development-evaluation","date":"2026-09-24","dataset_status":"already-spent / selected / development / non-confirmatory","authoritative_orchestrator_decision_url":DECISION,"starting_canonical_implementation_sha":START,"evaluated_commit":os.environ.get("EVALUATED_COMMIT") or os.environ.get("GITHUB_SHA"),"workflow_run":{"run_id":int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None,"url":f"https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"},"runner":os.environ.get("RUNNER_NAME"),"policies":{"comparator":"BoundedMergeV4Policy(setup_weight=250)","treatment":"VisibleRepairReserveV5Policy(exit_card=deck.exit_card)"},"model":{"deck_file":"data/deck-v1.json","exit_geometry_source":"data/deck-observations-v0.json","rules_variant":"v0-threshold-equipment","raincoats_min":3,"ropes_min":2,"start_side":"easy-5-exit","hand_size":3},"seed_scope":SEEDS,"fresh_seeds_used":False,"holdout_used":False,"source_provenance":{"worker8":{"drive_file_id":"1HxKxPgGIBASaytNz2r5De7-dS0pyyi4e","bytes":1203842,"sha256":"aef42e22732280af79c68e8bb44b6fdbbf060f12e8caf325f85475e7a928a51b"},"worker10":{"drive_file_id":"1Cd5GL2sav26qPr8ZSkW4Qi7XnEDjhSC5","archive_bytes":5010,"archive_sha256":"b1e21969bb4b1873f7dd2938104bc1c1ebb39339a1c2bc643cd726d7dc4dc1b3","inner_bytes":69464,"inner_sha256":"cf70178d1edd1e3b9326142c313c8b376986c2a08759202ec47827f060d97c2f"}},"integrity":integrity,"integrity_passed":ok,"v4_runs":v4runs}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    if not ok:
        out.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n");print("WORKER13_INTEGRITY="+json.dumps(integrity,sort_keys=True));raise SystemExit("integrity gate failed; V5 evaluation not interpreted")
    v5runs={str(s):play_v5(s,deck) for s in SEEDS};paired={}
    for s in SEEDS:
        a4=v4runs[str(s)]["final"];a5=v5runs[str(s)]["final"];cl="rescue" if not a4["won"] and a5["won"] else "regression" if a4["won"] and not a5["won"] else "unchanged_win" if a4["won"] else "unchanged_nonwin"
        paired[str(s)]={"classification":cl,"v4_final":a4,"v5_final":a5,"first_divergence":v5runs[str(s)]["first_divergence"]}
    ptr={}
    for tid in sorted(PERSISTENT):
        e=expected[tid];seed=tid.split(":")[0];canon=v4runs[seed]["targets"][tid];r=v5runs[seed];sm=r["samples"].get(tid);reached=sm is not None and sm["fingerprint"]==canon["fingerprint"];div=r["first_divergence"]
        if reached:
            want=esig(e);sup=sm["v5"]!=want and sm["v4_probe"]==want and sm["v4_unsafe"];cat="target_reached_and_historical_unsafe_move_suppressed" if sup else "target_reached_but_not_suppressed"
        elif div and div["action_turn"]<int(tid.split(":a")[1].split(":")[0]) and div["safety_filter_applied"]:cat="target_not_reached_after_earlier_v5_safety_divergence"
        else:cat="other"
        explanation=("exact canonical checkpoint reached and V5 suppressed the historical unsafe V4 move" if cat=="target_reached_and_historical_unsafe_move_suppressed" else "canonical target state was not reached because an earlier V5 safety-filter divergence changed the live trajectory" if cat=="target_not_reached_after_earlier_v5_safety_divergence" else "exact canonical checkpoint reached but the historical unsafe move was not suppressed" if cat=="target_reached_but_not_suppressed" else "canonical target state was not reached and no qualifying earlier V5 safety-filter divergence preempted it; see first_divergence and action trace")
        ptr[tid]={"category":cat,"explanation":explanation,"persistent_target_preempted":cat in {"target_reached_and_historical_unsafe_move_suppressed","target_not_reached_after_earlier_v5_safety_divergence"},"exact_checkpoint_reached":reached,"first_divergence":div}
    fptr={}
    for tid in sorted(FALSEPOS):
        e=expected[tid];seed=tid.split(":")[0];canon=v4runs[seed]["targets"][tid];r=v5runs[seed];sm=r["samples"].get(tid);reached=sm is not None and sm["fingerprint"]==canon["fingerprint"];div=r["first_divergence"];turn=int(tid.split(":a")[1].split(":")[0])
        fptr[tid]={"checkpoint_reached_by_v5":reached,"historical_v4_action_suppressed":(sm["v5"]!=esig(e) and sm["v4_probe"]==esig(e) and sm["v4_unsafe"]) if reached else "not reached","earlier_v5_divergence":bool(div and div["action_turn"]<turn),"subsequent_capacity_recovery":recovery_after(r["capacity_history"],turn if reached else (div["action_turn"] if div else turn)),"v4_final_outcome":v4runs[seed]["final"],"v5_final_outcome":r["final"]}
    resc=sum(x["classification"]=="rescue" for x in paired.values());reg=sum(x["classification"]=="regression" for x in paired.values());unchw=sum(x["classification"]=="unchanged_win" for x in paired.values());pre=sum(x["persistent_target_preempted"] for x in ptr.values());rs=sum(x["category"]=="target_reached_and_historical_unsafe_move_suppressed" for x in ptr.values());nr=sum(x["category"]=="target_not_reached_after_earlier_v5_safety_divergence" for x in ptr.values());net=resc-reg
    summary={"v4_wins":sum(x["v4_final"]["won"] for x in paired.values()),"v5_wins":sum(x["v5_final"]["won"] for x in paired.values()),"class_a_rescues_out_of_18":resc,"baseline_win_regressions_out_of_5":reg,"unchanged_v4_wins_out_of_5":unchw,"paired_net_win_count_change":net,"persistent_targets_preempted_out_of_18":pre,"persistent_targets_reached_and_suppressed":rs,"persistent_targets_not_reached_after_earlier_safety_divergence":nr,"total_v5_safety_interventions":sum(x["safety_interventions"] for x in v5runs.values()),"total_all_unsafe_fallbacks":sum(x["all_unsafe_fallbacks"] for x in v5runs.values()),"seeds_with_no_v4_v5_divergence_before_exit_first_seen":sum(x["first_divergence"] is None for x in v5runs.values())}
    classification="v5_development_signal_supports_fresh_confirmation" if resc>=4 and reg<=1 and net>=3 and pre>=16 else "v5_development_signal_not_supported" if resc<=1 or reg>=2 or net<=0 or pre<=12 else "v5_development_signal_ambiguous"
    r=v5runs["2282"];div=r["first_divergence"];s2282={"checkpoint":fptr["2282:a6:s5"],"first_divergence":div,"capacity_history_from_first_divergence":changes(r["capacity_history"],div["state_turn_before_action"] if div else 0),"first_exit_seen_transition":r["first_exit_seen_transition"],"exit_placement_turn":r["exit_placement_turn"],"v4_final":v4runs["2282"]["final"],"v5_final":r["final"]}
    payload.update({"v5_runs":v5runs,"paired_results":paired,"persistent_target_tracking":ptr,"reversible_false_positive_tracking":fptr,"seed_2282":s2282,"cohort_summary":summary,"final_preregistered_classification":classification,"interpretation_limit":"selected already-spent development cohort; descriptive and non-confirmatory"})
    out.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n");print("WORKER13_INTEGRITY="+json.dumps(integrity,sort_keys=True));print("WORKER13_RESULT="+json.dumps({"cohort_summary":summary,"classification":classification,"seed_2282":s2282},sort_keys=True))
if __name__=="__main__":main()
