"""Complete finite-state M0/M1 reference for arbitrary n (no state pruning).

The physical laws and action rules are those of the frozen two-service M1.
Sparse storage enumerates every allowed edge; emergency repairs are added only
when the entire normal action set is empty. Floating DP uses float64; snapshot
and rational_dp provide independent Fraction checks on short problems.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product
import math
import numpy as np

TIERS = ('R', 'M', 'C')
TOL = 1e-12
GAIN_TOL = 1e-11


@dataclass(frozen=True)
class Service:
    b: object
    eta: object
    compute: object
    slo: object
    nominal: tuple
    radio: object = F(2)


@dataclass(frozen=True)
class Parameters:
    services: tuple = (
        Service(F(1), F(1,10), F(18), F(18), (F(5,2), F(2), F(3,2))),
        Service(F(7,10), F(1,2), F(12), F(20), (F(2), F(17,10), F(13,10))),
    )
    mec: object = F(60)
    core: object = F(120)
    bandwidth: tuple = (F(12,5), F(9,5))
    base_delay: tuple = (F(1), F(2))
    coefficient: tuple = (F(1,2), F(4,5))


class Model:
    def __init__(self, parameters=None):
        self.p = parameters or Parameters()
        self.n = len(self.p.services)
        self.states = tuple(''.join(p) for p in product(TIERS, repeat=self.n))
        self.index = {s:i for i,s in enumerate(self.states)}
        self.tiers = np.array(list(product(range(3), repeat=self.n)), dtype=np.int8)
        self.S = len(self.states)
        self.changed = self.tiers[:,None,:] != self.tiers[None,:,:]
        self.distance = self.changed.sum(axis=2).astype(np.int8)
        b = np.array([float(s.b) for s in self.p.services])
        eta = np.array([float(s.eta) for s in self.p.services])
        c = np.array([float(s.compute) for s in self.p.services])
        # Sum the rational population data before conversion, preserving exact
        # capacity boundaries when the supplied H equals a subset compute sum.
        self.q = np.array([[float(sum((s.compute for s,t in zip(self.p.services,state)
                                       if t==k),F(0))) for k in TIERS] for state in self.states])
        self.loads = np.array([[float(sum((s.b*(s.eta if t=='R' else 1)
                                          for s,t in zip(self.p.services,state)),F(0))),
                                float(sum((s.b*(s.eta if t!='C' else 1)
                                          for s,t in zip(self.p.services,state)),F(0)))]
                               for state in self.states])
        B = np.asarray(self.p.bandwidth, dtype=float)
        self.link_feasible = np.all(self.loads < B, axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            self.network = (np.asarray(self.p.base_delay,dtype=float) +
                np.asarray(self.p.coefficient,dtype=float)*self.loads/(B-self.loads)).sum(axis=1)
        self.nominal = np.array([list(map(float,s.nominal)) for s in self.p.services])
        self.slo = np.array([float(s.slo) for s in self.p.services])
        self.radio = np.array([float(s.radio) for s in self.p.services])

    def stress(self, headroom):
        if headroom < 0: raise ValueError('Negative headroom')
        cap = np.array([headroom, float(self.p.mec), float(self.p.core)])
        feasible = self.link_feasible & np.all((self.q==0)|(self.q<cap),axis=1)
        # Every selected service occupies its tier, so no empty-tier 0/0 is used.
        capacity = cap[self.tiers]
        load = np.take_along_axis(self.q, self.tiers, axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            processing = self.nominal[np.arange(self.n),self.tiers]*capacity/(capacity-load)
            stress = (self.radio+self.network[:,None]+processing)/self.slo
        stress[~feasible] = np.inf
        return stress

    def costs(self, headroom):
        return self.stress(headroom).max(axis=1)

    def table(self, trace):
        cache = {float(h):self.costs(float(h)) for h in set(trace)}
        return np.array([cache[float(h)] for h in trace])

    def snapshot(self, placement, headroom):
        """Independent scalar implementation; exact for Fraction parameters/H."""
        if placement not in self.index or headroom<0: raise ValueError('Invalid state/headroom')
        p=self.p
        q=tuple(sum((s.compute for s,k in zip(p.services,placement) if k==tier),F(0)) for tier in TIERS)
        loads=(sum((s.b*(s.eta if k=='R' else 1) for s,k in zip(p.services,placement)),F(0)),
               sum((s.b*(s.eta if k!='C' else 1) for s,k in zip(p.services,placement)),F(0)))
        cap=(headroom,p.mec,p.core)
        if any(l>=b for l,b in zip(loads,p.bandwidth)) or any(qi>0 and qi>=h for qi,h in zip(q,cap)):
            return {'feasible':False,'cost':math.inf,'q':q,'loads':loads}
        network=sum((d+a*l/(b-l) for d,a,l,b in zip(p.base_delay,p.coefficient,loads,p.bandwidth)),F(0))
        latency=tuple(s.radio+network+s.nominal[TIERS.index(k)]*cap[TIERS.index(k)]/
                      (cap[TIERS.index(k)]-q[TIERS.index(k)]) for s,k in zip(p.services,placement))
        stress=tuple(d/s.slo for d,s in zip(latency,p.services))
        return {'feasible':True,'q':q,'loads':loads,'network':network,
                'latency':latency,'stress':stress,'cost':max(stress)}


@dataclass
class Step:
    index: np.ndarray
    valid: np.ndarray
    cost: np.ndarray
    override: np.ndarray


class Problem:
    def __init__(self, model, table, initial, budget=1, weights=None, emergency=True):
        self.model=model
        self.table=np.asarray(table,dtype=float)
        self.initial=model.index[initial] if isinstance(initial,str) else int(initial)
        self.budget=int(budget)
        if not 0<=self.budget<=model.n: raise ValueError('Invalid move budget')
        if self.table.ndim!=2 or self.table.shape[1]!=model.S: raise ValueError('Wrong cost-table shape')
        self.weights=np.array(weights if weights is not None else [.0025]*model.n,dtype=float)
        if self.weights.shape!=(model.n,) or np.any(self.weights<0): raise ValueError('Invalid switching costs')
        self.switch=model.changed @ self.weights
        self.steps=[]
        graphs={}
        for costs in self.table:
            finite=np.isfinite(costs)
            key=finite.tobytes()
            if key not in graphs:
                normal=(model.distance<=self.budget)&finite[None,:]
                override=np.zeros(model.S,dtype=bool)
                rows=[]
                for s in range(model.S):
                    js=np.flatnonzero(normal[s])
                    if len(js)==0 and emergency and finite.any():
                        nearest=np.min(model.distance[s,finite])
                        js=np.flatnonzero(finite & (model.distance[s]==nearest))
                        override[s]=True
                    # Order makes first near-minimum implement the frozen M1 tie rule.
                    js=sorted(js,key=lambda j:(j!=s,model.distance[s,j],j))
                    rows.append(js)
                width=max(1,max(map(len,rows)))
                index=np.zeros((model.S,width),dtype=np.int32)
                valid=np.zeros((model.S,width),dtype=bool)
                for s,js in enumerate(rows):
                    index[s,:len(js)]=js
                    valid[s,:len(js)]=True
                graphs[key]=(index,valid,override)
            index,valid,override=graphs[key]
            penalty=self.switch[np.arange(model.S)[:,None],index]
            edge=np.where(valid,costs[index]+penalty,np.inf)
            self.steps.append(Step(index,valid,edge,override))

    def path_cost(self, path, initial=None, start=0):
        s=self.initial if initial is None else initial
        total=0.
        for t,j in enumerate(path,start):
            step=self.steps[t]
            if not np.any(step.valid[s] & (step.index[s]==j)):return math.inf
            total+=self.table[t,j]+self.switch[s,j]
            s=j
        return float(total)


def values(steps, S, terminal=None):
    V=np.empty((len(steps)+1,S))
    V[-1]=0. if terminal is None else np.inf
    if terminal is not None:V[-1,terminal]=0.
    for t in range(len(steps)-1,-1,-1):
        e=steps[t]
        V[t]=np.min(e.cost+V[t+1,e.index],axis=1)
    return V


def choose(step,s,next_value):
    candidates=step.cost[s]+next_value[step.index[s]]
    best=np.min(candidates)
    if not np.isfinite(best):return -1
    return int(step.index[s,np.flatnonzero(candidates<=best+TOL)[0]])


def recover(steps,V,initial):
    path=[];s=initial
    for t,step in enumerate(steps):
        s=choose(step,s,V[t+1])
        if s<0:return []
        path.append(s)
    return path


def mpc(problem,horizon=1):
    if horizon is not None and horizon<1:raise ValueError('Positive horizon required')
    S=problem.model.S
    if horizon is None:return recover(problem.steps,values(problem.steps,S),problem.initial)
    path=[];s=problem.initial
    for t in range(len(problem.steps)):
        steps=problem.steps[t:t+horizon]
        V=values(steps,S)
        s=choose(steps[0],s,V[1])
        if s<0:return []
        path.append(s)
    return path


def return_rollout(problem,preview=8,levels=None):
    """Same completed-return/incumbent algorithm as frozen n=2 RAR."""
    if preview<1:raise ValueError('Positive preview required')
    levels=(preview,) if levels is None else tuple(sorted(set(k for k in levels if 1<=k<=preview)))
    if not levels or levels[-1]!=preview:levels=levels+(preview,)
    baseline=mpc(problem,1)
    T=len(problem.steps);S=problem.model.S
    if len(baseline)!=T:return [],[]
    s=problem.initial;incumbent=[];path=[];audit=[]
    for t in range(T):
        windows=sorted(set(min(k,T-t) for k in levels if min(k,T-t)>=len(incumbent)))
        if not windows:raise AssertionError('Incumbent extends beyond preview')
        accepted=False;gain=0.;accepted_h=0;queried=0;dp_slots=0;dp_windows=0
        for length in windows:
            end=t+length
            fallback=incumbent+baseline[t+len(incumbent):end]
            old=problem.path_cost(fallback,s,t)
            if not np.isfinite(old):raise AssertionError('Perfect-preview fallback infeasible')
            terminal=None if end==T else baseline[end-1]
            steps=problem.steps[t:end]
            V=values(steps,S,terminal)
            queried=max(queried,length);dp_slots+=length;dp_windows+=1
            if V[0,s]<old-GAIN_TOL:
                candidate=recover(steps,V,s)
                new=problem.path_cost(candidate,s,t)
                if len(candidate)==length and new<old-GAIN_TOL:
                    incumbent=candidate;accepted=True;gain=old-new;accepted_h=length
                    break
        if not incumbent:incumbent=[baseline[t]]
        endpoint=t+len(incumbent)
        j=incumbent.pop(0)
        if not np.isfinite(problem.path_cost([j],s,t)):raise AssertionError('Illegal RAR action')
        path.append(j)
        audit.append({'slot':t+1,'previous':problem.model.states[s],'placement':problem.model.states[j],
                      'baseline':problem.model.states[baseline[t]],'accepted_improvement':int(accepted),
                      'accepted_gain':gain,'accepted_horizon':accepted_h,'preview_queried':queried,
                      'dp_slots':dp_slots,'dp_windows':dp_windows,'incumbent_remaining':len(incumbent),
                      'plan_end_slot':endpoint,'terminal_free':int(endpoint==T),
                      'plan_anchor':'*' if endpoint==T else problem.model.states[baseline[endpoint-1]]})
        s=j
    realized=problem.path_cost(path)
    base=problem.path_cost(baseline)
    residual=base-realized-sum(a['accepted_gain'] for a in audit)
    if abs(residual)>1e-8 or realized>base+1e-9:raise AssertionError('RAR ledger/baseline bound failed')
    return path,audit


def evaluate(problem,path,trace=None,with_stress=False):
    if len(path)!=len(problem.steps):return {'status':'infeasible','total_cost':math.inf}
    m=problem.model;s=problem.initial;rows=[]
    for t,j in enumerate(path):
        if not np.isfinite(problem.path_cost([j],s,t)):raise AssertionError('Illegal trajectory')
        op=float(problem.table[t,j]);sw=float(problem.switch[s,j])
        row={'slot':t+1,'previous':m.states[s],'placement':m.states[j],
             'operating_cost':op,'switching_cost':sw,'moves':int(m.distance[s,j]),
             'override':int(problem.steps[t].override[s]),'slo_violation':int(op>1+TOL)}
        if trace is not None:row['H']=float(trace[t])
        if with_stress:
            stress=m.snapshot(m.states[j],float(trace[t]))['stress']
            row.update({f'rho_{i+1}':float(r) for i,r in enumerate(stress)})
        rows.append(row);s=j
    op=sum(r['operating_cost'] for r in rows);sw=sum(r['switching_cost'] for r in rows)
    return {'status':'ok','operating_cost':op,'switching_cost':sw,'total_cost':op+sw,
            'service_moves':sum(r['moves'] for r in rows),
            'placement_switches':sum(r['moves']>0 for r in rows),
            'overrides':sum(r['override'] for r in rows),
            'slo_violation_slots':sum(r['slo_violation'] for r in rows),
            'peak_stress':max((r['operating_cost'] for r in rows),default=0.),'rows':rows}


def rational_dp(model,trace,initial,budget=1,weights=None,terminal=None):
    """Independent all-state Fraction DP, intended for small certification cases."""
    states=model.states;weights=weights or (F(1,400),)*model.n
    V={s:(F(0) if terminal is None or s==terminal else math.inf) for s in states}
    policies=[]
    for h in reversed(trace):
        costs={s:model.snapshot(s,h)['cost'] for s in states}
        finite=[s for s in states if costs[s]!=math.inf]
        new={};policy={}
        for s in states:
            distance=lambda p:sum(a!=b for a,b in zip(s,p))
            allowed=[p for p in finite if distance(p)<=budget]
            if not allowed and finite:
                nearest=min(map(distance,finite));allowed=[p for p in finite if distance(p)==nearest]
            candidates=[]
            for p in allowed:
                if V[p]==math.inf:continue
                penalty=sum((w for w,a,b in zip(weights,s,p) if a!=b),F(0))
                candidates.append((costs[p]+penalty+V[p],p!=s,distance(p),model.index[p],p))
            if candidates:
                choice=min(candidates);new[s]=choice[0];policy[s]=choice[-1]
            else:new[s]=math.inf;policy[s]=None
        V=new;policies.append(policy)
    value=V[initial];path=[];s=initial
    for policy in reversed(policies):
        s=policy[s]
        if s is None:return math.inf,[]
        path.append(s)
    return value,path
