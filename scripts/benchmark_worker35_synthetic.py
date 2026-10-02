"""Invented Worker35 production-path preflight: no real cards, games or shuffle.

Construct a public board and a conserved invented69-card GameState directly,
then call AuditPolicy.choose once under the whole-cohort meter. This measures
all three profiling layers plus public/real-state fingerprints, independent
checking, canonical serialization, bounded journal writes and fsync. Source pins
and benchmark-only protections are explicit; none is a research resource freeze.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
from random import Random
import resource
import sys
import tempfile
import time

import worker35_resources as bounded
import run_quota_reserve_closure_development as harness

ROOT = Path(__file__).resolve().parents[1]


def measure_wrapper(audited, state, total_caps, wall_seconds):
    """The exact whole-cohort -> decision -> candidate/reference hook path."""
    meter = bounded.Meter(total_caps=total_caps)
    began, cpu = time.monotonic(), time.process_time()
    previous = sys.getprofile()
    bounded.require(previous is None or callable(previous), 'native profile hook cannot safely be forwarded')
    wall_guard = bounded.deadline(wall_seconds, 'invented complete wrapper')
    try:
        meter.__enter__()
        with wall_guard:
            audited.choose(state.observation(), Random(11))
    finally:
        try:
            wall_guard.gen.close()
        finally:
            sys.setprofile(previous)
    return {'wall_seconds': time.monotonic() - began, 'cpu_seconds': time.process_time() - cpu,
            'operations': meter.counts, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-candidate-sha256', required=True)
    parser.add_argument('--expected-reference-sha256', required=True)
    parser.add_argument('--wall-seconds', required=True, type=int)
    parser.add_argument('--memory-mib', required=True, type=int)
    parser.add_argument('--operation-ceiling', required=True, type=int)
    parser.add_argument('--sizes', required=True)
    args = parser.parse_args(argv)
    if min(args.wall_seconds, args.memory_mib, args.operation_ceiling) <= 0:
        parser.error('positive explicit benchmark ceilings required')
    sizes = [int(item) for item in args.sizes.split(',')]
    if not sizes or len(sizes) != len(set(sizes)) or any(n < 0 or n > 48 for n in sizes):
        parser.error('distinct invented fixture sizes in0..48 required')
    sources = {}
    for kind, filename in (('candidate', 'quota_reserve_closure.py'), ('reference', 'quota_reserve_closure_reference.py')):
        sources[kind] = bounded.file_hash(ROOT / 'src' / 'bandido_alcatraz' / filename)['sha256']
        if sources[kind] != getattr(args, 'expected_' + kind + '_sha256'):
            raise ValueError(kind + ': benchmark source differs from explicit pin')
    bounded.enforce_memory(args.memory_mib * 1024 ** 2)
    sys.path.insert(0, str(ROOT / 'src'))
    from bandido_alcatraz.board import Board
    from bandido_alcatraz.game import GameState
    from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
    from bandido_alcatraz import quota_reserve_closure as candidate
    from bandido_alcatraz import quota_reserve_closure_reference as reference
    from bandido_alcatraz.setup import SOLO_EASY
    from bandido_alcatraz.worker32.evidence import canonical, observation, sha
    N,E,S,W = Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST
    def card(name, edges=(), material=None, exit=False):
        return CardDefinition(name, (CellSpec(0,0,frozenset(edges),False),),material,exit)
    caps = {**dict.fromkeys((*bounded.OPS, 'roots'), args.operation_ceiling),
            'wall_seconds': args.wall_seconds, 'cpu_seconds': args.wall_seconds}
    total_caps = {k: 2 * args.operation_ceiling for k in bounded.OPS}
    limits = {'per_call': {name: dict(caps) for name in bounded.SCOPES},
        'evidence_bytes': 64 * bounded.MIB, 'receipt_bytes': bounded.MIB,
        'trace_bytes': 16 * bounded.MIB, 'line_bytes': 8 * bounded.MIB}
    harness.FREEZE = {'resources': limits}
    executable = Path(sys.executable).resolve()
    runtime = {'implementation': platform.python_implementation(), 'version': platform.python_version(),
               'executable_sha256': bounded.file_hash(executable)['sha256'], 'executable': str(executable)}
    for n in sizes:
        start = CardDefinition('start_easy', (CellSpec(0,0,frozenset((W,N,E))),CellSpec(1,0,frozenset((W,N,E,S)))))
        coats = [card(f'coat-{i}',(W,),Material.RAINCOAT) for i in range(12)]
        ropes = [card(f'rope-{i}',(W,),Material.ROPE) for i in range(8)]
        ordinary = [card(f'ordinary-{i}',(N,E,S,W) if i < n else ()) for i in range(48)]
        exit_card = card('exit',(W,),exit=True)
        catalog = tuple(coats+ropes+ordinary+[exit_card])
        inputs = {'catalog': catalog, 'start_card':start,'exit_card':exit_card}
        board=Board();board.seed(start)
        for i in range(n):board.place(ordinary[i],(2+i,0),0)
        used = {c.card_id for c in coats[:6] + ordinary[:n]}
        state = GameState(board=board, hand=list(coats[:6]),
            draw_pile=[c for c in catalog if c.card_id not in used], turns=n, setup=SOLO_EASY)
        public = state.observation()
        output = {'schema':'worker35-synthetic-resource-v2','invented_fourway_placements':n,
            'runtime':runtime,'sources':sources,'memory_mib':args.memory_mib,
            'per_call_wall_seconds':args.wall_seconds,'whole_wrapper_wall_seconds':2 * args.wall_seconds,
            'operation_ceiling':args.operation_ceiling,'profile_path':'whole-cohort/decision/policy plus durable AuditPolicy journals',
            'observation_sha256':sha(observation(public)),'observation_bytes':len(canonical(observation(public))),
            'implementations':{},'scientific_agreement':False}
        with tempfile.TemporaryDirectory(prefix='worker35-invented-profile-') as directory:
            folder=Path(directory)
            harness.BUDGET=bounded.EvidenceBudget(folder, limits)
            audited=harness.AuditPolicy(candidate.QuotaReserveClosurePolicy(**inputs),
                reference=reference.QuotaReserveClosureReference(**inputs), catalog=catalog,
                output=folder, pass_number=2, seed=11, limits=limits['per_call'],
                candidate_limits=candidate.OperationLimits(**dict.fromkeys(bounded.OPS,args.operation_ceiling)),
                reference_limits=reference.OperationLimits(**dict.fromkeys(bounded.OPS,args.operation_ceiling)),
                state_provider=lambda:state)
            try:
                output['whole_wrapper']=measure_wrapper(audited,state,total_caps,2 * args.wall_seconds)
                calls=harness.read_trace(audited.calls_path)
                science=calls[0]['result']['scientific']
                bounded.require(calls[1]['result']['scientific_sha256']==sha(science),'independent science digest mismatch')
                for metric in harness.iter_jsonl(folder/'resource-metrics.jsonl'):
                    output['implementations'][metric['scope']]={
                        'status':'passed','cost':metric['cost'],'science_sha256':sha(science),
                        'science_bytes':len(canonical(science)),
                        **{k:metric[k] for k in ('wall_seconds','cpu_seconds','peak_rss_kib')}}
                output['scientific_agreement']=True
                output['status']='passed'
            except Exception as error:
                output['status']='failed';output['error_type']=type(error).__name__;output['error']=str(error)
            finally:
                output['journal_files']={p.relative_to(folder).as_posix():bounded.file_hash(p)
                    for p in sorted(folder.rglob('*')) if p.is_file()}
                output['journal_bytes']=sum(item['size_bytes'] for item in output['journal_files'].values())
                harness.BUDGET=None
                print(json.dumps(output,sort_keys=True,separators=(',',':'),allow_nan=False),flush=True)
        if output['status']!='passed':return 1
    return 0


if __name__=='__main__':
    try:
        result = main()
    except Exception as error:
        print(json.dumps({'schema':'worker35-synthetic-resource-v2','status':'failed',
            'phase':'administrative_preflight','error_type':type(error).__name__,'error':str(error)},
            sort_keys=True,separators=(',',':')),flush=True)
        result = 1
    raise SystemExit(result)
