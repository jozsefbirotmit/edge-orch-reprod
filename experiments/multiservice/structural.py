"""Static envelopes and exact local-trap / shortest-escape diagnostics."""
from collections import deque
from fractions import Fraction as F
import math
import numpy as np
from m1_general import Problem,values,recover,TOL


def static_sweep(model,headrooms):
    table=model.table(headrooms)
    best=np.argmin(table,axis=1)
    ordered=np.sort(table,axis=1)
    gap=ordered[:,1]-ordered[:,0]
    rows=[]
    for h,c,s,g in zip(headrooms,table,best,gap):
        stress=model.stress(h)[s]
        rows.append({'H':float(h),'placement':model.states[s],'cost':float(c[s]),
                     'uniqueness_gap':float(g),'bottleneck':int(np.argmax(stress))+1})
    nonmono=[]
    strict=np.flatnonzero(gap>1e-8)
    for i in range(model.n):
        sequence=[]
        for t in strict:
            k=model.tiers[best[t],i]
            if not sequence or sequence[-1][0]!=k:sequence.append((int(k),int(t)))
        # M0 phenomenon specifically R -> M -> R, allowing other intervening states.
        r1=None;m=None
        for k,t in sequence:
            if r1 is None and k==0:r1=t
            elif r1 is not None and m is None and k==1:m=t
            elif m is not None and k==0:
                nonmono.append({'service':i+1,'H1':float(headrooms[r1]),'H2':float(headrooms[m]),
                                'H3':float(headrooms[t]),'state1':model.states[best[r1]],
                                'state2':model.states[best[m]],'state3':model.states[best[t]],
                                'min_uniqueness_gap':float(min(gap[r1],gap[m],gap[t]))})
                break
    return rows,nonmono


def trapped_states(model,costs,kappa=.0025):
    finite=np.isfinite(costs)
    switch=model.distance*kappa
    candidates=np.where((model.distance<=1)&finite[None,:],costs[None,:]+switch,np.inf)
    local=finite & (np.min(candidates,axis=1)>=costs-TOL)
    suboptimal=costs>np.min(costs)+1e-8
    return np.flatnonzero(local&suboptimal)


def escape_distance(model,costs,initial):
    """Fewest single-service moves to ANY strictly lower operating-cost state."""
    finite=np.isfinite(costs)
    goals=finite & (costs<costs[initial]-1e-8)
    queue=deque([initial]);depth={initial:0}
    while queue:
        s=queue.popleft()
        if goals[s]:return depth[s]
        for j in np.flatnonzero(finite & (model.distance[s]==1)):
            j=int(j)
            if j not in depth:depth[j]=depth[s]+1;queue.append(j)
    return 0


def payback(model,costs,initial,max_horizon=256,budget=1,kappa=.0025,closed=False):
    """First strict gain vs staying; exact graph, float64 Bellman recurrence.

    closed=True requires return to initial after the final charged slot. The
    actual experimental trace remains free-terminal; this is a diagnostic.
    """
    p=Problem(model,np.array([costs]),initial,budget,[kappa]*model.n)
    step=p.steps[0];s=p.initial
    v=np.zeros(model.S) if not closed else np.full(model.S,np.inf)
    if closed:v[s]=0.
    base=costs[s]
    for K in range(1,max_horizon+1):
        v=np.min(step.cost+v[step.index],axis=1)
        tol=max(1e-11,128*np.finfo(float).eps*K*max(1.,abs(base)))
        if v[s]<K*base-tol:
            steps=[step]*K
            V=values(steps,model.S,s if closed else None)
            path=recover(steps,V,s)
            move_path=[s]+path
            moves=sum(int(model.distance[a,b]) for a,b in zip(move_path,move_path[1:]))
            changed=set()
            for a,b in zip(move_path,move_path[1:]):changed.update(np.flatnonzero(model.changed[a,b]))
            intermediate=max(float(costs[j]-base) for j in path)
            return {'horizon':K,'gain':float(K*base-v[s]),'path':[model.states[j] for j in path],
                    'service_moves':moves,'distinct_services':len(changed),'max_intermediate_excess':intermediate}
    return {'horizon':0,'gain':0.,'path':[],'service_moves':0,'distinct_services':0,
            'max_intermediate_excess':0.}


def fraction_payback(model,H,initial,budget=1,kappa=F(1,400),closed=False,max_horizon=512):
    """Independent exact-rational constant-H certificate, all states/edges."""
    costs={s:model.snapshot(s,H)['cost'] for s in model.states}
    finite=[s for s in model.states if costs[s]!=math.inf]
    edges={}
    for s in model.states:
        distance=lambda p:sum(a!=b for a,b in zip(s,p))
        js=[p for p in finite if distance(p)<=budget]
        if not js and finite:
            nearest=min(map(distance,finite));js=[p for p in finite if distance(p)==nearest]
        edges[s]=[(j,costs[j]+kappa*distance(j)) for j in js]
    v={s:(F(0) if not closed or s==initial else math.inf) for s in model.states}
    baseline=costs[initial];previous_margin=F(0)
    for K in range(1,max_horizon+1):
        v={s:min((c+v[j] for j,c in js if v[j]!=math.inf),default=math.inf) for s,js in edges.items()}
        margin=K*baseline-v[initial]
        if margin>0:
            return {'horizon':K,'margin_before':str(previous_margin),'margin_at':str(margin),
                    'stay_at':str(K*baseline),'optimum_at':str(v[initial])}
        previous_margin=margin
    return {'horizon':0,'margin_before':str(previous_margin),'margin_at':'0','stay_at':'','optimum_at':''}
