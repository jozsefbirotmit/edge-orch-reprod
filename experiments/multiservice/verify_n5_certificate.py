"""Independent, auditable n5_14 exact barrier certificate (no paper-specific shortcuts).

Quick mode: exact Fraction per state, all placements, four-move route, and checks
against archived rational payback certificates.
Optional --deep-payback: recomputes exact finite-horizon DP for 64/129 slots.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from fractions import Fraction as F
from pathlib import Path
from m1_general import Model
from populations import population
from structural import fraction_payback

HERE=Path(__file__).resolve().parent
OUT=None  # Read-only unless --output-dir is supplied


def to_float_or_none(x):
    return None if x == math.inf else float(x)


def write_csv(filename,fields,rows):
    if OUT is None:
        return
    with (OUT/filename).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--deep-payback',action='store_true',help='Run independent exact-rational DP through H=129 (slower).')
    parser.add_argument('--output-dir',type=Path,default=None,help='Optional directory for regenerated certificate outputs. By default no files are written.')
    args=parser.parse_args()
    global OUT
    OUT=args.output_dir.resolve() if args.output_dir is not None else None
    if OUT is not None: OUT.mkdir(parents=True,exist_ok=True)
    meta,params=population(5,14)
    model=Model(params)
    H=F(30)
    initial='MCCMR'
    path=['MCCMR','RCCMR','RMCMR','RMMMR','RMMCR']
    assert model.S==243 and meta['seed']==109743 and meta['family']=='independent'
    assert sum((s.b for s in params.services),F(0))==F(17,10)
    assert sum((s.compute for s in params.services),F(0))==F(30)

    params_rows=[]
    for i,s in enumerate(params.services,1):
        params_rows.append(dict(service=i,b=float(s.b),eta=float(s.eta),compute=float(s.compute),
             slo=float(s.slo),p_R=float(s.nominal[0]),p_M=float(s.nominal[1]),
             p_C=float(s.nominal[2]),radio=float(s.radio)))
    write_csv('n5_14_parameters.csv',list(params_rows[0]),params_rows)

    exact={state:model.snapshot(state,H) for state in model.states}
    base=exact[initial]['cost']
    assert base!=math.inf
    by_distance={}
    rows=[]
    counts={}
    for state in model.states:
        d=sum(a!=b for a,b in zip(initial,state))
        snap=exact[state]
        counts[d]=counts.get(d,0)+1
        cost=snap['cost']
        if cost!=math.inf:
            if d not in by_distance or cost<by_distance[d][1]:
                by_distance[d]=(state,cost)
            bottleneck=max(range(5), key=lambda j:snap['stress'][j])+1
        else:
            bottleneck=''
        rows.append(dict(placement=state,distance_from_initial=d,feasible=int(snap['feasible']),
               J_exact=str(cost) if cost!=math.inf else 'infeasible',
               J_decimal=to_float_or_none(cost), delta_from_initial=to_float_or_none(cost-base) if cost!=math.inf else None,
               N_decimal=to_float_or_none(snap['network']) if cost!=math.inf else None,
               bottleneck_service=bottleneck))
    assert sum(counts.values())==243
    assert all(by_distance[d][1]>base for d in (1,2,3))
    assert by_distance[4][1]<base
    assert by_distance[4][0]=='RMMCR'
    write_csv('n5_14_all_placements.csv',list(rows[0]),rows)

    path_rows=[]
    bottlenecks=[]
    previous=None
    for t,state in enumerate(path):
        snap=exact[state]
        if previous is None:
            moved=''
        else:
            changed=[i+1 for i,(a,b) in enumerate(zip(previous,state)) if a!=b]
            assert len(changed)==1
            moved=changed[0]
        bottleneck=max(range(5),key=lambda j:snap['stress'][j])+1
        bottlenecks.append(bottleneck)
        path_rows.append(dict(step=t,placement=state,relocated_service=moved,
                   H=float(H),J_exact=str(snap['cost']),J_decimal=float(snap['cost']),
                   delta_vs_start=float(snap['cost']-base),network_delay=float(snap['network']),
                   compute_R=float(snap['q'][0]),compute_M=float(snap['q'][1]),compute_C=float(snap['q'][2]),
                   bottleneck_service=bottleneck))
        previous=state
    assert all(exact[p]['cost']>base for p in path[1:-1])
    assert exact[path[-1]]['cost']<base
    assert bottlenecks==[1,1,2,3,1]
    assert exact[path[-2]]['network']<exact[path[0]]['network']
    assert exact[path[-1]]['network']>exact[path[-2]]['network']
    released=exact[path[-2]]['q'][1]-exact[path[-1]]['q'][1]
    assert released==F(107113,10000)
    write_csv('n5_14_path.csv',list(path_rows[0]),path_rows)

    stored=json.loads((HERE/'data/fraction_certificates.json').read_text(encoding='utf-8'))
    certs={bool(c['closed']):c for c in stored if c['id']=='n5_14'}
    assert set(certs)=={False,True}
    assert int(certs[False]['horizon'])==64
    assert int(certs[True]['horizon'])==129
    for closed in (False,True):
        c=certs[closed]
        assert F(c['margin_at'])>0
        assert F(c['margin_before'])<=0
        assert F(c['stay_at'])-F(c['optimum_at'])==F(c['margin_at'])
    if args.deep_payback:
        for closed,expected in ((False,64),(True,129)):
            actual=fraction_payback(model,H,initial,budget=1,kappa=F(1,400),closed=closed,max_horizon=130)
            assert int(actual['horizon'])==expected
            for k in ('margin_before','margin_at','stay_at','optimum_at'):
                assert F(actual[k])==F(certs[closed][k]), (closed,k)
    report={
       'certificate':'n5_14', 'source_seed':meta['seed'], 'family':meta['family'],
       'services':5,'headroom':30,'initial':initial,'goal':path[-1],
       'total_placements':model.S,'feasible_placements':sum(s['feasible'] for s in exact.values()),
       'counts_by_distance':{str(k):v for k,v in sorted(counts.items())},
       'strictly_worse_at_all_distances_1_to_3':True,'minimum_improving_distance':4,
       'initial_J_exact':str(base),'goal_J_exact':str(exact[path[-1]]['cost']),
       'operating_saving_per_slot':float(base-exact[path[-1]]['cost']),
       'best_at_each_distance':{str(k):{'placement':v[0],'J_exact':str(v[1]),'J_decimal':float(v[1])}
                                for k,v in sorted(by_distance.items())},
       'witness_path':path,'bottleneck_services_on_path':bottlenecks,
       'last_move_frees_MEC_compute':float(released),
       'migration_budget':1,'per_service_migration_penalty':'1/400',
       'one_way_payback':64,'closed_return_payback':129,
       'stored_rational_certificate_verified':True,
       'independent_deep_payback_rerun':bool(args.deep_payback),
       'interpretation':'All four-move barrier claims are exact Fractions for the archived synthetic model; payback values are separate constant-H cost diagnostics.'}
    if OUT is not None:
        (OUT/'n5_14_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','feasible':report['feasible_placements'],'minimum_improving_distance':4,
      'Kout':64,'Kret':129,'deep_payback':args.deep_payback,'per_slot_saving':report['operating_saving_per_slot']},indent=2))

if __name__=='__main__':main()
