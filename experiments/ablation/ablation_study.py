"""Focused, reproducible one-factor ablation of the published M0/M1 model.

The ablations REMOVE a physical mechanism, not the placement feasibility constraints.
- no_transform: eta_i=1 for all i, so there is no traffic reduction
- no_transport_congestion: a1=a2=0 (base link delay remains); link feasibility remains
- no_compute_congestion: base processing p0_it with no utilization multiplier; capacity feasibility remains

The 72 population sample and static H grid replicate the multiservice v0.3 setup.
All results are descriptive for fixed synthetic inputs.
"""
from __future__ import annotations
import sys, json, csv, math
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
import numpy as np

HERE=Path(__file__).resolve().parent
SRC=HERE/'source'
sys.path.insert(0,str(SRC))
from populations import population, COUNTS
from m1_general import Model, Parameters
from structural import static_sweep, escape_distance

MODES=('full','no_transform','no_transport_congestion','no_compute_congestion')

class CongestionAblatedModel(Model):
    """Neutralize only the utilization factor in computing latency."""
    def stress(self,headroom):
        if headroom<0: raise ValueError('Negative headroom')
        cap=np.array([headroom, float(self.p.mec),float(self.p.core)])
        feasible=self.link_feasible & np.all((self.q==0)|(self.q<cap),axis=1)
        processing=self.nominal[np.arange(self.n),self.tiers]
        stress=(self.radio+self.network[:,None]+processing)/self.slo
        stress[~feasible]=np.inf
        return stress
    def snapshot(self, placement, headroom):
        v=super().snapshot(placement,headroom)
        if not v['feasible']:return v
        p=self.p
        latency=tuple(s.radio+v['network']+s.nominal[('R','M','C').index(k)] for s,k in zip(p.services,placement))
        stress=tuple(l/s.slo for l,s in zip(latency,p.services))
        return {**v,'latency':latency,'stress':stress,'cost':max(stress)}


def make_model(parameters,mode):
    if mode=='full': return Model(parameters)
    if mode=='no_transform':
        parameters=replace(parameters,services=tuple(replace(s,eta=F(1)) for s in parameters.services))
        return Model(parameters)
    if mode=='no_transport_congestion':
        return Model(replace(parameters,coefficient=(F(0),F(0))))
    if mode=='no_compute_congestion':
        return CongestionAblatedModel(parameters)
    raise KeyError(mode)


def costs_per_distance(model,H,s):
    cs=model.costs(H); initial=model.index[s]
    ans=[]
    for d in range(model.n+1):
        js=np.flatnonzero(np.isfinite(cs)&(model.distance[initial]==d))
        if len(js):
            j=js[np.argmin(cs[js])]
            ans.append({'distance':d,'minimum_state':model.states[j],
                        'minimum_cost':float(cs[j]),'minus_start':float(cs[j]-cs[initial]),
                        'candidate_count':int(len(js))})
    nei=[r for r in ans if r['distance']==1]
    local=bool(nei and nei[0]['minus_start']>1e-8)
    better=bool(np.min(cs)<cs[initial]-1e-8)
    return ans,local,better,int(escape_distance(model,cs,initial)) if better else 0


def strict_reversals(model,headrooms):
    rows,nm=static_sweep(model,headrooms)
    return nm,rows


def inherited_strict_trap(model,lo,hi):
    low_costs=model.costs(lo); si=int(np.argmin(low_costs)); s=model.states[si]
    c=model.costs(hi)
    if not np.isfinite(c[si]):return False,None
    nei=np.flatnonzero(np.isfinite(c)&(model.distance[si]==1))
    if not len(nei):return False,None
    cond=bool(np.min(c[nei])>c[si]+1e-8 and np.min(c)<c[si]-1e-8)
    return cond, {'low':lo,'high':hi,'state':s,'escape':int(escape_distance(model,c,si)),'operating_gain':float(c[si]-np.min(c))} if cond else None


if __name__=="__main__":
    print("Run `python run_selected.py` and `python run_fast.py` to reproduce the results.")
