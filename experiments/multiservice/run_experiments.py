"""Reproduce the n=3--5 M1 generalization study. See README for sections.

No post-hoc population exclusion. Selected witnesses are explicitly separate
from population frequencies. Every controller uses the same physical graph,
per-service migration weights, initial state, trace and actual terminal rule.
"""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np

from m1_general import Model,Problem,mpc,return_rollout,evaluate
from populations import all_populations,population,rows as population_rows,COUNTS,BASE_SEED
from structural import static_sweep,trapped_states,escape_distance,payback,fraction_payback

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
PRIMARY=['myopic','MPC3','MPC5','MPC8','MPC16','MPC64','RAR8','RAR-A64','offline']
MAP=['myopic','MPC8','RAR8','MPC64','RAR-A64','offline']
LEVELS=(3,5,8,16,32,64,128)
LOW=[10,15,20,25,30,40,50,60]
HIGH=[20,25,30,40,50,60,70,80,90,100,120,150]
DURATIONS=[1,2,3,4,5,6,8,12,16,24,32,48,64,96,128]
KAPPAS=[0.,.001,.0025,.005,.01,.02]


def write(name,rows):
    rows=list(rows)
    if not rows:return
    with (DATA/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def read(name):return list(csv.DictReader((DATA/name).open()))


def dump(name,obj):
    (DATA/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def structural():
    params=[];static=[];nonmono=[];traps=[];inherited=[];summary=[];selected=[]
    H=np.unique(np.r_[0,np.geomspace(2,400,481)])
    trap_H=[20,30,40,50,60,70,80,90,100,150,200,300]
    for meta,par in all_populations():
        m=Model(par);params.extend(population_rows(meta,par))
        envelope,nm=static_sweep(m,H)
        static.extend({**meta,**r} for r in envelope)
        nonmono.extend({**meta,**r} for r in nm)
        trap_count=strict_count=0;max_escape=0
        for h in trap_H:
            c=m.costs(h)
            for s in trapped_states(m,c):
                neighbor=(m.distance[s]==1)&np.isfinite(c)
                excess=float(np.min(c[neighbor])-c[s])
                kind='strict' if excess>1e-8 else 'flat' if excess>=-1e-8 else 'penalty'
                depth=escape_distance(m,c,s)
                traps.append({**meta,'H':h,'initial':m.states[s],'J_initial':float(c[s]),
                              'J_global':float(np.min(c)),'neighbor_excess':excess,
                              'kind':kind,'min_moves_to_better':depth})
                trap_count+=1;strict_count+=(kind=='strict');max_escape=max(max_escape,depth)
        candidates={}
        for low in LOW:
            s=int(np.argmin(m.costs(low)))
            for high in HIGH:
                if high<=low:continue
                c=m.costs(high)
                if s not in trapped_states(m,c):continue
                neighbor=(m.distance[s]==1)&np.isfinite(c)
                excess=float(np.min(c[neighbor])-c[s])
                if excess<=1e-8:continue
                key=(s,high)
                if key in candidates:continue
                depth=escape_distance(m,c,s)
                pb=payback(m,c,s,256)
                row={**meta,'low':low,'high':high,'initial':m.states[s],
                     'neighbor_excess':excess,'operating_gap':float(c[s]-np.min(c)),
                     'min_moves_to_better':depth,'payback':pb['horizon'],
                     'payback_moves':pb['service_moves'],'distinct_services':pb['distinct_services']}
                candidates[key]=row
        inherited.extend(candidates.values())
        summary.append({**meta,'placements':m.S,'nonmonotone_services':len(nm),
                        'traps_grid':trap_count,'strict_traps_grid':strict_count,
                        'max_escape_distance':max_escape,'inherited_strict_traps':len(candidates),
                        'min_traffic_share':min(float(s.b/F(17,10)) for s in par.services),
                        'min_compute_share':min(float(s.compute/30) for s in par.services),
                        'static_bottleneck_services':len(set(r['bottleneck'] for r in envelope))})
        print('structure',meta['id'],'nonmono',len(nm),'inherited strict traps',len(candidates),flush=True)
    for n in COUNTS:
        eligible=[r for r in inherited if r['n']==n and r['payback']>0]
        # Discovery cohort, not an unbiased estimate: most complex inherited
        # escape, then broadest profitable plan, then largest operating gap.
        chosen=sorted(eligible,key=lambda r:(-r['min_moves_to_better'],-r['distinct_services'],
                     -r['operating_gap'],r['id'],r['low'],r['high']))[0]
        selected.append(chosen)
    write('populations.csv',params);write('static_envelopes.csv',static)
    write('nonmonotone_witnesses.csv',nonmono);write('all_state_traps.csv',traps)
    write('inherited_strict_traps.csv',inherited);write('population_summary.csv',summary)
    dump('selected_witnesses.json',selected)


def traces(meta):
    rng=np.random.default_rng(meta['seed']+900000)
    blocks=[]
    while len(blocks)<128:
        blocks.extend([float(rng.choice([0,5,10,15,20,30,40,60,80,100,200,400]))]*int(rng.integers(2,11)))
    return {
        'pulse':np.r_[np.full(16,20.),np.full(12,80.),np.full(36,20.)],
        'exchange_ramp':np.r_[np.linspace(10,120,64),np.linspace(120,10,64)],
        'oscillation':40+30*np.sin(2*np.pi*(np.arange(128)-8)/32),
        'all_phase_ramp':np.r_[np.geomspace(5,400,64),np.geomspace(400,5,64)],
        'withdrawal':np.repeat([400.,10.,100.,0.,400.],[16,8,16,8,16]),
        'seeded_blocks':np.array(blocks[:128])}


def run(m,trace,initial,budget=1,kappa=.0025,controllers=PRIMARY,details=False):
    p=Problem(m,m.table(trace),initial,budget,[kappa]*m.n)
    basepath=mpc(p,1);offpath=mpc(p,None)
    base=evaluate(p,basepath);off=evaluate(p,offpath)
    out={}
    for name in controllers:
        audit=[];start=time.monotonic()
        if name=='myopic':path=basepath
        elif name=='offline':path=offpath
        elif name.startswith('MPC'):path=mpc(p,int(name[3:]))
        elif name.startswith('RAR-A'):
            cap=int(name[5:]);path,audit=return_rollout(p,cap,tuple(k for k in LEVELS if k<=cap))
        else:path,audit=return_rollout(p,int(name[3:]))
        seconds=time.monotonic()-start
        result=evaluate(p,path,trace,details)
        if result['status']!='ok':raise AssertionError('Global feasible set unexpectedly empty')
        cost=result['total_cost'];delta=cost-off['total_cost'];gain=base['total_cost']-cost
        assert delta>=-1e-8
        residual=gain-sum(a['accepted_gain'] for a in audit) if audit else 0.
        if audit:assert gain>=-1e-9 and abs(residual)<1e-8
        result.update({'controller':name,'gap_to_offline':0. if abs(delta)<1e-10 else delta,
                       'gap_to_offline_pct':100*max(0.,delta)/off['total_cost'],
                       'saving_vs_myopic':0. if abs(gain)<1e-10 else gain,
                       'saving_vs_myopic_pct':100*gain/base['total_cost'],
                       'operating_saving_vs_myopic':base['operating_cost']-result['operating_cost'],
                       'extra_migration_vs_myopic':result['switching_cost']-base['switching_cost'],
                       'accepted_plans':sum(a['accepted_improvement'] for a in audit),
                       'ledger_residual':residual,'max_preview_queried':max((a['preview_queried'] for a in audit),default=0),
                       'dp_slots':sum(a['dp_slots'] for a in audit),'controller_seconds':seconds,
                       'path':path,'audit':audit,'final':m.states[path[-1]]})
        out[name]=result
    return out


def compact(r):return {k:v for k,v in r.items() if k not in ['rows','path','audit']}


def encode_path(m,path):
    out=[]
    for j in path:
        s=m.states[j]
        if out and out[-1][0]==s:out[-1][1]+=1
        else:out.append([s,1])
    return out


def primary():
    summaries=[];inputs=[]
    with gzip.open(DATA/'controller_paths.jsonl.gz','wt') as pathfile:
        for meta,par in all_populations():
            m=Model(par)
            for name,trace in traces(meta).items():
                initial=m.states[int(np.argmin(m.costs(trace[0])))]
                inputs.extend({**meta,'trace':name,'slot':t+1,'H':float(h),'initial':initial}
                              for t,h in enumerate(trace))
                for budget in [1,2,m.n]:
                    controllers=PRIMARY if budget==1 else ['myopic','offline']
                    outputs=run(m,trace,initial,budget,controllers=controllers)
                    for controller,r in outputs.items():
                        context={**meta,'trace':name,'T':len(trace),'initial':initial,'budget':budget,'kappa_per_service':.0025}
                        summaries.append({**context,**compact(r)})
                        pathfile.write(json.dumps({**context,'controller':controller,'rle':encode_path(m,r['path'])})+'\n')
            print('primary',meta['id'],'runs',len(summaries),flush=True)
            # A reproducible checkpoint also makes an interrupted long run inspectable.
            write('primary_summary.csv',summaries)
    write('primary_traces.csv',inputs)


def witnesses():
    selected=json.loads((DATA/'selected_witnesses.json').read_text())
    certificates=[];cost_rows=[];summaries=[];series=[];audits=[];paybacks=[]
    for w in selected:
        meta,par=population(w['n'],w['replicate']);m=Model(par)
        c=m.costs(w['high']);s=m.index[w['initial']]
        for state in m.states:
            exact=m.snapshot(state,F(w['high']))
            cost_rows.append({**meta,'H':w['high'],'placement':state,'feasible':int(exact['feasible']),
                              'J_exact':str(exact['cost']),'J_float':float(exact['cost'])})
        for budget in [1,2,m.n]:
            for closed in [False,True]:
                pb=payback(m,c,s,512,budget,closed=closed)
                paybacks.append({**meta,'H':w['high'],'initial':w['initial'],'budget':budget,
                                 'closed':int(closed),**{k:v for k,v in pb.items() if k!='path'},
                                 'path_rle':json.dumps(encode_path(m,[m.index[s] for s in pb['path']]))})
                if budget==1:
                    exact=fraction_payback(m,F(w['high']),w['initial'],closed=closed)
                    assert exact['horizon']==pb['horizon']
                    certificates.append({**meta,'H':w['high'],'initial':w['initial'],'closed':closed,**exact})
        for name,trace in {
            'plateau':np.full(256,float(w['high'])),
            'pulse':np.r_[np.full(64,float(w['low'])),np.full(12 if m.n==3 else 24 if m.n==4 else 96,float(w['high'])),
                          np.full(64,float(w['low']))]}.items():
            controllers=['myopic']+[f'MPC{k}' for k in [2,3,4,5,8,16,32,64,128,129]]+['RAR8','RAR-A64','RAR-A128','RAR129','offline']
            out=run(m,trace,w['initial'],controllers=controllers,details=True)
            for controller,r in out.items():
                ctx={**meta,'trace':name,'T':len(trace),'initial':w['initial'],'budget':1,'controller':controller}
                summaries.append({**ctx,**compact(r)})
                for row in r['rows']:series.append({**ctx,**row,**{f'rho_{i}':row.get(f'rho_{i}','') for i in range(1,6)}})
                audits.extend({**ctx,**row} for row in r['audit'])
        print('witness',meta['id'],'certified',[(r['closed'],r['horizon']) for r in certificates if r['id']==meta['id']],flush=True)
    # All rows use the same schema even though the number of stress columns varies.
    fields=list(series[0])
    series=[{k:r.get(k,'') for k in fields} for r in series]
    write('witness_summary.csv',summaries);write('witness_timeseries.csv',series)
    write('witness_plan_audit.csv',audits);write('witness_exact_costs.csv',cost_rows)
    write('witness_paybacks.csv',paybacks);dump('fraction_certificates.json',certificates)


def pulse_map():
    selected=json.loads((DATA/'selected_witnesses.json').read_text())
    summaries=[]
    for w in selected:
        meta,par=population(w['n'],w['replicate']);m=Model(par)
        for kappa in KAPPAS:
            for duration in DURATIONS:
                trace=np.r_[np.full(64,float(w['low'])),np.full(duration,float(w['high'])),np.full(64,float(w['low']))]
                budgets=[1,2,m.n] if kappa==.0025 else [1]
                for budget in budgets:
                    controllers=MAP if budget==1 else ['myopic','MPC8','RAR8','offline']
                    out=run(m,trace,w['initial'],budget,kappa,controllers)
                    for controller,r in out.items():
                        summaries.append({**meta,'low':w['low'],'high':w['high'],'duration':duration,
                                          'budget':budget,'kappa_per_service':kappa,'T':len(trace),
                                          'initial':w['initial'],**compact(r)})
            print('map',meta['id'],'kappa',kappa,'runs',len(summaries),flush=True)
            write('pulse_map_summary.csv',summaries)


def regression():
    import importlib.util
    path=ROOT/'inputs/m1_n2_reference.py'
    spec=importlib.util.spec_from_file_location('m1',path)
    reference=importlib.util.module_from_spec(spec);sys.modules['m1']=reference;spec.loader.exec_module(reference)
    path=ROOT/'inputs/return_n2_reference.py'
    spec=importlib.util.spec_from_file_location('return_ref',path)
    rr=importlib.util.module_from_spec(spec);sys.modules['return_ref']=rr;spec.loader.exec_module(rr)
    raw=list(csv.DictReader((ROOT/'inputs/n2_reference_traces.csv').open()))
    old=list(csv.DictReader((ROOT/'inputs/n2_reference_summary.csv').open()))
    checks=[];m=Model()
    for name in dict.fromkeys(r['trace'] for r in raw):
        samples=[r for r in raw if r['trace']==name];trace=[float(r['H']) for r in samples];initial=samples[0]['initial']
        for budget in [1,2]:
            out=run(m,trace,initial,budget,controllers=PRIMARY)
            rp=rr.Problem(m.table(trace),initial,budget)
            for controller,r in out.items():
                oldrow=next(x for x in old if x['trace']==name and int(x['budget'])==budget and x['controller']==controller)
                difference=r['total_cost']-float(oldrow['total_cost'])
                assert abs(difference)<1e-9
                if controller.startswith('RAR'):
                    op,_=rr.return_rollout(rp,64,LEVELS[:-1]) if controller=='RAR-A64' else rr.return_rollout(rp,8)
                else:op=rr.mpc(rp,None if controller=='offline' else 1 if controller=='myopic' else int(controller[3:]))
                equal=[m.states[j] for j in r['path']]==op
                assert equal
                checks.append({'trace':name,'budget':budget,'controller':controller,
                               'total_cost':r['total_cost'],'old_total_cost':float(oldrow['total_cost']),
                               'difference':difference,'identical_path':int(equal)})
    write('n2_regression.csv',checks)
    print('n2 regression',len(checks),'identical paths',flush=True)


def summarize():
    primary=read('primary_summary.csv');pop=read('population_summary.csv');maps=read('pulse_map_summary.csv')
    witnesses=read('witness_summary.csv');paybacks=read('witness_paybacks.csv')
    facts={'populations':{},'primary':{},'map':{},'witnesses':json.loads((DATA/'selected_witnesses.json').read_text()),
           'paybacks':paybacks,'primary_runs':len(primary),'map_runs':len(maps),'witness_runs':len(witnesses),
           'n2_regression_runs':len(read('n2_regression.csv'))}
    agg=[]
    for n,count in COUNTS.items():
        pp=[r for r in pop if int(r['n'])==n]
        facts['populations'][n]={'count':count,'nonmonotone':sum(int(r['nonmonotone_services'])>0 for r in pp),
            'with_inherited_strict_trap':sum(int(r['inherited_strict_traps'])>0 for r in pp),
            'max_escape_all_state':max(int(r['max_escape_distance']) for r in pp),
            'min_traffic_share':min(float(r['min_traffic_share']) for r in pp),
            'min_compute_share':min(float(r['min_compute_share']) for r in pp),
            'family':{f:{'count':sum(r['family']==f for r in pp),
                         'nonmonotone':sum(r['family']==f and int(r['nonmonotone_services'])>0 for r in pp),
                         'inherited_strict_trap':sum(r['family']==f and int(r['inherited_strict_traps'])>0 for r in pp)}
                      for f in ['independent','coupled']}}
        facts['primary'][n]={};facts['map'][n]={}
        for controller in PRIMARY:
            rr=[r for r in primary if int(r['n'])==n and int(r['budget'])==1 and r['controller']==controller]
            gaps=np.array([float(r['gap_to_offline_pct']) for r in rr]);savings=np.array([float(r['saving_vs_myopic_pct']) for r in rr])
            a={'n':n,'controller':controller,'traces':len(rr),'mean_gap_pct':float(np.mean(gaps)),
               'max_gap_pct':float(max(gaps)),'mean_saving_pct':float(np.mean(savings)),
               'max_saving_pct':float(max(savings)),'wins_vs_myopic':sum(float(r['saving_vs_myopic'])>1e-9 for r in rr),
               'losses_vs_myopic':sum(float(r['saving_vs_myopic'])< -1e-9 for r in rr),
               'mean_moves':float(np.mean([int(r['service_moves']) for r in rr])),
               'violation_slots':sum(int(r['slo_violation_slots']) for r in rr),
               'overrides':sum(int(r['overrides']) for r in rr),
               'max_ledger_residual':max(abs(float(r['ledger_residual'])) for r in rr)}
            facts['primary'][n][controller]=a;agg.append(a)
        for controller in MAP:
            rr=[r for r in maps if int(r['n'])==n and int(r['budget'])==1 and r['controller']==controller]
            oracle={(r['kappa_per_service'],r['duration']):r for r in maps if int(r['n'])==n and int(r['budget'])==1 and r['controller']=='offline'}
            facts['map'][n][controller]={'cases':len(rr),'harmful':sum(float(r['saving_vs_myopic'])< -1e-9 for r in rr),
                'offline_profitable':sum(float(oracle[(r['kappa_per_service'],r['duration'])]['saving_vs_myopic'])>1e-9 for r in rr),
                'missed_all_gain':sum(float(r['saving_vs_myopic'])<=1e-9 and float(oracle[(r['kappa_per_service'],r['duration'])]['saving_vs_myopic'])>1e-9 for r in rr),
                'matches_offline':sum(float(r['gap_to_offline'])<1e-9 for r in rr),
                'max_gap_pct':max(float(r['gap_to_offline_pct']) for r in rr)}
    ledger=[abs(float(r['ledger_residual'])) for r in primary+maps+witnesses if r['controller'].startswith('RAR')]
    facts['rar_runs']=len(ledger);facts['max_ledger_residual']=max(ledger)
    facts['rar_harmful']=sum(float(r['saving_vs_myopic'])< -1e-9 for r in primary+maps+witnesses if r['controller'].startswith('RAR'))
    write('aggregate_primary.csv',agg);dump('findings.json',facts)
    print(json.dumps({k:facts[k] for k in ['populations','primary_runs','map_runs','witness_runs','rar_runs','max_ledger_residual','rar_harmful']},indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--section',choices=['all','structure','primary','witness','map','regression','summarize'],default='all');args=parser.parse_args()
    t0=time.monotonic()
    for section,fn in [('structure',structural),('regression',regression),('primary',primary),('witness',witnesses),('map',pulse_map),('summarize',summarize)]:
        if args.section in ['all',section]:fn()
    dump('last_run.json',{'section':args.section,'seconds':time.monotonic()-t0,
                         'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform()})


if __name__=='__main__':main()
