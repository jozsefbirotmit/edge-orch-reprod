"""Return-aware rollout on the unchanged nine-state M1 model.

Each accepted plan rejoins a shadow myopic trajectory at its window boundary.
The remaining incumbent plan is retained as a feasible alternative. Windows
must cover that incumbent before accepting a replacement. At the TRUE end of
the problem the terminal state is free, exactly as in M1.

Correct headroom preview over every queried window is assumed. No headroom
after the queried window enters the optimization. A finite preview cap does
not imply equality with offline DP. The guarantee is relative to the shadow
baseline and concerns total cost, not prefix cost or separate SLO/move counts.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

from m1 import STATES, INDEX, TOL, action_mask, switching_matrix, pick

GAIN_TOL = 1e-11


@dataclass
class Problem:
    table: np.ndarray
    initial: str
    budget: int = 1
    weights: tuple = (.0025,.0025)
    emergency: bool = True

    def __post_init__(self):
        self.table=np.asarray(self.table,dtype=float)
        if self.table.ndim!=2 or self.table.shape[1]!=len(STATES):
            raise ValueError('Cost table must have nine columns')
        if self.initial not in INDEX:
            raise ValueError('Unknown initial state')
        rec=switching_matrix(self.weights)
        self.edge=np.empty((len(self.table),len(STATES),len(STATES)))
        self.override=np.empty((len(self.table),len(STATES)),dtype=bool)
        for t,costs in enumerate(self.table):
            allowed,override=action_mask(costs,self.budget,self.emergency)
            self.edge[t]=np.where(allowed,costs[None,:]+rec,np.inf)
            self.override[t]=override


def window_values(edges: np.ndarray, terminal_state: int | None = None):
    """Exact all-state Bellman minimization, optionally with a terminal anchor.

    Unlike m1.solve_dp this postpones tie-breaking until a path is requested;
    numerical values and all admissible transitions are identical.
    """
    values=np.empty((len(edges)+1,len(STATES)))
    values[-1]=0 if terminal_state is None else np.inf
    if terminal_state is not None:
        values[-1,terminal_state]=0
    for t in range(len(edges)-1,-1,-1):
        values[t]=np.min(edges[t]+values[t+1][None,:],axis=1)
    return values


def recover_path(edges, values, initial):
    s=initial
    path=[]
    for t,edge in enumerate(edges):
        s=pick(edge[s]+values[t+1],s)
        if s<0:
            return []
        path.append(s)
    return path


def path_cost(edges, path, initial):
    if len(path)!=len(edges):
        return math.inf
    total=0.
    previous=initial
    for edge,state in zip(edges,path):
        total+=edge[previous,state]
        previous=state
    return float(total)


def myopic(problem: Problem):
    previous=INDEX[problem.initial]
    path=[]
    for edge in problem.edge:
        previous=pick(edge[previous],previous)
        if previous<0:
            return []
        path.append(previous)
    return path


def mpc(problem: Problem, horizon: int | None = 1):
    """Ordinary zero-terminal MPC with exactly the same preview as RAR-K."""
    if horizon is None:
        value=window_values(problem.edge)
        return [STATES[s] for s in recover_path(problem.edge,value,INDEX[problem.initial])]
    if horizon<1:
        raise ValueError('Positive preview required')
    previous=INDEX[problem.initial]
    path=[]
    for t in range(len(problem.edge)):
        edges=problem.edge[t:t+horizon]
        value=window_values(edges)
        previous=pick(edges[0,previous]+value[1],previous)
        if previous<0:
            return []
        path.append(STATES[previous])
    return path


def return_rollout(problem: Problem, preview: int=8, levels=None):
    """Execute RAR-K or adaptive RAR, returning path and an auditable plan ledger.

    Fixed policy: levels=None, preview=K.
    Adaptive policy: ascending levels, capped at preview. It accepts the first
    strict improvement over the incumbent, and tries longer windows otherwise.
    Every window covers the unexecuted incumbent. The initially empty incumbent
    means following the shadow myopic path. At t+K<T an anchor is mandatory;
    t+K=T uses the actual M1 free terminal condition.

    The baseline is precomputed for convenience, but only its entries through
    each window endpoint are queried; these are determined by headroom in that
    same prefix. The prefix-invariance test checks for future information leaks.
    """
    if preview<1:
        raise ValueError('Positive preview required')
    if levels is None:
        levels=(preview,)
    else:
        levels=tuple(sorted(set(int(k) for k in levels if 1<=int(k)<=preview)))
        if not levels or levels[-1]!=preview:
            levels=levels+(preview,)
    baseline=myopic(problem)
    if len(baseline)!=len(problem.edge):
        return [],[]
    previous=INDEX[problem.initial]
    incumbent=[]
    path=[]
    audit=[]
    total=len(problem.edge)
    for t in range(total):
        remaining=total-t
        min_window=len(incumbent)
        windows=sorted(set(min(k,remaining) for k in levels if min(k,remaining)>=min_window))
        if not windows:
            raise AssertionError('Preview does not cover the incumbent plan')
        accepted=False
        chosen_gain=0.
        old_cost=new_cost=math.nan
        chosen_window=0
        dp_slots=0
        examined=0
        queried=0
        for length in windows:
            end=t+length
            edges=problem.edge[t:end]
            fallback=incumbent+baseline[t+len(incumbent):end]
            if len(fallback)!=length:
                raise AssertionError('Incumbent and baseline extension do not align')
            old_cost=path_cost(edges,fallback,previous)
            if not np.isfinite(old_cost):
                raise AssertionError('Perfect-preview incumbent became infeasible')
            terminal=None if end==total else baseline[end-1]
            value=window_values(edges,terminal)
            examined+=1
            dp_slots+=length
            queried=max(queried,length)
            # Recover a full plan only when its Bellman value can improve.
            if value[0,previous]<old_cost-GAIN_TOL:
                candidate=recover_path(edges,value,previous)
                new_cost=path_cost(edges,candidate,previous)
                if new_cost<old_cost-GAIN_TOL:
                    incumbent=candidate
                    accepted=True
                    chosen_gain=old_cost-new_cost
                    chosen_window=length
                    break
        if not incumbent:
            incumbent=[baseline[t]]
        plan_end=t+len(incumbent)
        selected=incumbent.pop(0)
        if not np.isfinite(problem.edge[t,previous,selected]):
            raise AssertionError('Selected move is not physically admissible')
        path.append(STATES[selected])
        audit.append({'slot':t+1,'previous':STATES[previous],'placement':STATES[selected],
                      'baseline':STATES[baseline[t]],'accepted_improvement':int(accepted),
                      'accepted_gain':chosen_gain,'accepted_horizon':chosen_window,
                      'preview_queried':queried,'dp_windows':examined,'dp_slots':dp_slots,
                      'incumbent_remaining':len(incumbent),'plan_end_slot':plan_end,
                      'terminal_free':int(plan_end==total),
                      'plan_anchor':('*' if plan_end==total else STATES[baseline[plan_end-1]])})
        previous=selected
    # Every accepted replacement swaps a window with a common baseline suffix.
    base_cost=path_cost(problem.edge,baseline,INDEX[problem.initial])
    realized=path_cost(problem.edge,[INDEX[s] for s in path],INDEX[problem.initial])
    gain=sum(a['accepted_gain'] for a in audit)
    error=(base_cost-realized)-gain
    if abs(error)>1e-8*max(1.,base_cost):
        raise AssertionError(f'Replacement ledger does not telescope: {error}')
    if realized>base_cost+1e-9:
        raise AssertionError('Baseline dominance violated under perfect preview')
    return path,audit
