"""Invented Worker35 fixtures only; no real catalog, observations or games.

Explicit candidate/reference byte pins and benchmark-only ceilings are required.
Production custom profiling and an outer physical meter are both enabled. These
measurements inform a later resource freeze, never select policy/scientific rules.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
from random import Random
import resource
import sys
import time

import worker35_resources as bounded

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-candidate-sha256', required=True)
    parser.add_argument('--expected-reference-sha256', required=True)
    parser.add_argument('--wall-seconds', required=True, type=int)
    parser.add_argument('--memory-mib', required=True, type=int)
    parser.add_argument('--sizes', required=True)
    args = parser.parse_args(argv)
    if args.wall_seconds <= 0 or args.memory_mib <= 0:
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
    from bandido_alcatraz.game import PlayerObservation
    from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
    from bandido_alcatraz.quota_reserve_closure import QuotaReserveClosurePolicy
    from bandido_alcatraz.quota_reserve_closure_reference import QuotaReserveClosureReference
    from bandido_alcatraz.setup import SOLO_EASY
    from bandido_alcatraz.worker32.evidence import canonical, observation, sha, move
    N,E,S,W = Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST
    def card(name, edges=(), material=None, exit=False):
        return CardDefinition(name, (CellSpec(0,0,frozenset(edges),False),),material,exit)
    executable = Path(sys.executable).resolve()
    runtime = {'implementation': platform.python_implementation(), 'version': platform.python_version(),
               'executable_sha256': bounded.file_hash(executable)['sha256'], 'executable': str(executable)}
    for n in sizes:
        start = CardDefinition('start_easy', (CellSpec(0,0,frozenset((W,N,E))),CellSpec(1,0,frozenset((W,N,E,S)))))
        coats = [card(f'coat-{i}',(W,),Material.RAINCOAT) for i in range(12)]
        ropes = [card(f'rope-{i}',(W,),Material.ROPE) for i in range(8)]
        ordinary = [card(f'ordinary-{i}',(N,E,S,W) if i < n else ()) for i in range(48)]
        exit_card = card('exit',(W,),exit=True)
        inputs = {'catalog': tuple(coats+ropes+ordinary+[exit_card]), 'start_card':start,'exit_card':exit_card}
        board=Board();board.seed(start)
        for i in range(n):board.place(ordinary[i],(2+i,0),0)
        public=PlayerObservation(board,tuple(coats[:6]),0,0,False,False,n,0,(),SOLO_EASY)
        output = {'schema':'worker35-synthetic-resource-v1','invented_fourway_placements':n,
            'runtime':runtime,'sources':sources,'memory_mib':args.memory_mib,'per_fixture_wall_seconds':args.wall_seconds,
            'observation_sha256':sha(observation(public)),'observation_bytes':len(canonical(observation(public))),
            'implementations':{},'scientific_agreement':False}
        results=[]
        try:
            for scope, cls in (('candidate',QuotaReserveClosurePolicy),('reference',QuotaReserveClosureReference)):
                policy=cls(**inputs);rng=Random(11);obs=copy.deepcopy(public)
                began,cpu=time.monotonic(),time.process_time()
                meter=bounded.Meter(rng=rng)
                try:
                    with bounded.deadline(args.wall_seconds,'invented '+scope),meter:
                        chosen,science,cost=policy.evaluate(obs,rng)
                    bounded.require(cost == {**meter.counts,'roots':len(science['roots'])}, 'physical profiling disagreement')
                    bounded.require(sha(observation(obs)) == output['observation_sha256'], 'invented public mutation')
                    results.append((move(chosen),science,rng.getstate()))
                    output['implementations'][scope]={'status':'passed','cost':cost,
                        'science_sha256':sha(science),'science_bytes':len(canonical(science)),
                        'wall_seconds':time.monotonic()-began,'cpu_seconds':time.process_time()-cpu,
                        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
                except Exception as error:
                    output['implementations'][scope]={'status':'failed','error_type':type(error).__name__,
                        'error':str(error),'observed_operations':meter.counts,
                        'wall_seconds':time.monotonic()-began,'cpu_seconds':time.process_time()-cpu,
                        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
                    raise
            bounded.require(canonical(results[0]) == canonical(results[1]), 'independent invented science/RNG disagreement')
            output['scientific_agreement']=True
            output['status']='passed'
        except Exception as error:
            output['status']='failed';output['error_type']=type(error).__name__;output['error']=str(error)
        print(json.dumps(output,sort_keys=True,separators=(',',':'),allow_nan=False),flush=True)
        if output['status']!='passed':return 1
    return 0


if __name__=='__main__':
    try:
        result = main()
    except Exception as error:
        print(json.dumps({'schema':'worker35-synthetic-resource-v1','status':'failed',
            'phase':'administrative_preflight','error_type':type(error).__name__,'error':str(error)},
            sort_keys=True,separators=(',',':')),flush=True)
        result = 1
    raise SystemExit(result)
