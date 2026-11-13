"""M1 reference model: all nine placements and complete finite-state control.

Reference: M0 v1.0 (2026-10-13), Section 6; M1 v0.1 (2026-10-17).
The physical snapshot can be evaluated with fractions.Fraction without rounding.
The experiment DP enumerates all admissible edges and uses float64 arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product
from typing import Sequence
import math

import numpy as np

TIERS = ("R", "M", "C")
STATES = tuple("".join(s) for s in product(TIERS, repeat=2))
INDEX = {s: i for i, s in enumerate(STATES)}
DISTANCE = np.array([[sum(a != b for a, b in zip(s, p)) for p in STATES]
                     for s in STATES], dtype=int)
TOL = 1e-12


@dataclass(frozen=True)
class Service:
    b: F
    eta: F
    compute: F
    slo: F
    nominal: tuple[F, F, F]
    radio: F = F(2)


@dataclass(frozen=True)
class Parameters:
    services: tuple[Service, Service] = (
        Service(F(1), F(1, 10), F(18), F(18), (F(5, 2), F(2), F(3, 2))),
        Service(F(7, 10), F(1, 2), F(12), F(20), (F(2), F(17, 10), F(13, 10))),
    )
    mec: F = F(60)
    core: F = F(120)
    bandwidth: tuple[F, F] = (F(12, 5), F(9, 5))
    base_delay: tuple[F, F] = (F(1), F(2))
    coefficient: tuple[F, F] = (F(1, 2), F(4, 5))


@dataclass(frozen=True)
class Snapshot:
    feasible: bool
    q: tuple
    loads: tuple
    network: object | None = None
    latency: tuple = ()
    stress: tuple = ()
    cost: object = math.inf


class Model:
    def __init__(self, parameters: Parameters | None = None):
        self.parameters = parameters or Parameters()

    def snapshot(self, placement: str, headroom) -> Snapshot:
        """Occupied tiers must satisfy strict capacity inequalities, including H=0."""
        if placement not in INDEX:
            raise ValueError(f"Unknown placement: {placement}")
        if headroom < 0:
            raise ValueError("Headroom must be nonnegative")
        p = self.parameters
        q = tuple(sum((s.compute for s, k in zip(p.services, placement) if k == tier), F(0))
                  for tier in TIERS)
        loads = (
            sum((s.b * (s.eta if k == "R" else 1) for s, k in zip(p.services, placement)), F(0)),
            sum((s.b * (s.eta if k != "C" else 1) for s, k in zip(p.services, placement)), F(0)),
        )
        capacity = (headroom, p.mec, p.core)
        if any(load >= cap for load, cap in zip(loads, p.bandwidth)) or any(
            load > 0 and load >= cap for load, cap in zip(q, capacity)
        ):
            return Snapshot(False, q, loads)
        network = sum((d + a * load / (cap - load)
                       for d, a, load, cap in zip(p.base_delay, p.coefficient, loads, p.bandwidth)), F(0))
        latency = []
        for service, tier in zip(p.services, placement):
            j = TIERS.index(tier)
            processing = service.nominal[j] * capacity[j] / (capacity[j] - q[j])
            latency.append(service.radio + network + processing)
        stress = tuple(d / s.slo for d, s in zip(latency, p.services))
        return Snapshot(True, q, loads, network, tuple(latency), stress, max(stress))

    def costs(self, headroom) -> np.ndarray:
        return np.array([float(self.snapshot(s, headroom).cost) for s in STATES])


def switching_matrix(weights=(0.0025, 0.0025)) -> np.ndarray:
    if len(weights) != 2 or min(weights) < 0:
        raise ValueError("Need two nonnegative per-service switching weights")
    return np.array([[sum(float(w) for w, a, b in zip(weights, s, p) if a != b)
                      for p in STATES] for s in STATES])


def action_mask(costs: np.ndarray, budget: int, emergency: bool = True):
    """Return all state-dependent admissible edges and override flags.

    Emergency is enabled only if the normal action set is EMPTY. It admits
    only feasible placements with the minimum number of moves from that state.
    """
    if budget not in (0, 1, 2):
        raise ValueError("For two services the budget must be 0, 1, or 2")
    finite = np.isfinite(costs)
    allowed = (DISTANCE <= budget) & finite[None, :]
    override = np.zeros(len(STATES), dtype=bool)
    if emergency and finite.any():
        for i in range(len(STATES)):
            if not allowed[i].any():
                nearest = DISTANCE[i, finite].min()
                allowed[i] = finite & (DISTANCE[i] == nearest)
                override[i] = True
    return allowed, override


def pick(values: np.ndarray, previous: int) -> int:
    """Ties: retain current placement, then fewest moves, then STATES order."""
    best = np.min(values)
    if not np.isfinite(best):
        return -1
    ties = np.flatnonzero(np.abs(values - best) <= TOL)
    return min(ties, key=lambda j: (j != previous, DISTANCE[previous, j], j))


def solve_dp(cost_table: np.ndarray, initial: str, budget: int = 1,
             weights=(0.0025, 0.0025), emergency=True):
    """Offline optimum with zero terminal cost; no path pruning/heuristic."""
    table = np.asarray(cost_table, dtype=float)
    n = len(STATES)
    switching = switching_matrix(weights)
    value = np.zeros(n)
    policy = np.full((len(table), n), -1, dtype=int)
    for t in range(len(table) - 1, -1, -1):
        allowed, _ = action_mask(table[t], budget, emergency)
        candidates = table[t][None, :] + switching + value[None, :]
        candidates = np.where(allowed, candidates, np.inf)
        value = np.min(candidates, axis=1)
        for s in range(n):
            policy[t, s] = pick(candidates[s], s)
    previous = INDEX[initial]
    optimum = value[previous]
    path = []
    for t in range(len(table)):
        selected = policy[t, previous]
        if selected < 0:
            return math.inf, []
        path.append(STATES[selected])
        previous = selected
    return float(optimum), path


def simulate(table: np.ndarray, initial: str, budget: int = 1,
             weights=(0.0025, 0.0025), horizon: int | None = 1, emergency=True):
    """Perfect-preview receding horizon; horizon=None gives offline DP.

    Every replan has zero terminal value, including truncated end windows.
    H=1 is the M1 myopic controller. No learned/estimated forecasts are used.
    """
    if horizon is not None and horizon < 1:
        raise ValueError("Lookahead horizon must be positive")
    if horizon is None:
        _, path = solve_dp(table, initial, budget, weights, emergency)
        return path
    path, previous = [], initial
    for t in range(len(table)):
        _, plan = solve_dp(table[t:t + horizon], previous, budget, weights, emergency)
        if not plan:
            return []
        previous = plan[0]
        path.append(previous)
    return path


def evaluate(table, path, initial, budget=1, weights=(0.0025, 0.0025), emergency=True):
    """Charge every occupied slot, including intermediate placement slots."""
    if len(path) != len(table):
        return {"status": "infeasible", "total_cost": math.inf}
    rec = switching_matrix(weights)
    previous = INDEX[initial]
    rows = []
    for t, (costs, state) in enumerate(zip(table, path), 1):
        j = INDEX[state]
        allowed, overrides = action_mask(costs, budget, emergency)
        if not allowed[previous, j]:
            raise AssertionError(f"Illegal edge at slot {t}: {STATES[previous]} -> {state}")
        rows.append({"slot": t, "previous": STATES[previous], "placement": state,
                     "operating_cost": float(costs[j]), "switching_cost": float(rec[previous, j]),
                     "moves": int(DISTANCE[previous, j]), "override": int(overrides[previous]),
                     "slo_violation": int(costs[j] > 1 + TOL)})
        previous = j
    operating = sum(r["operating_cost"] for r in rows)
    switching = sum(r["switching_cost"] for r in rows)
    return {"status": "ok", "operating_cost": operating, "switching_cost": switching,
            "total_cost": operating + switching, "service_moves": sum(r["moves"] for r in rows),
            "placement_switches": sum(r["moves"] > 0 for r in rows),
            "overrides": sum(r["override"] for r in rows),
            "slo_violation_slots": sum(r["slo_violation"] for r in rows),
            "peak_stress": max((r["operating_cost"] for r in rows), default=0), "rows": rows}


def minimum_constant_horizon(costs, initial="MR", budget=1, exchange_cost=0.005,
                             max_horizon=60):
    """First horizon whose exact DP value strictly improves on staying."""
    s0 = INDEX[initial]
    # If staying already attains the global operating minimum, nonnegative
    # switching penalties cannot help. This also prevents long-horizon roundoff
    # from reporting false gains at the exact static tie H=78.
    if costs[s0] <= np.min(costs) + TOL:
        return 0
    switching = switching_matrix((exchange_cost / 2,) * 2)
    allowed, _ = action_mask(costs, budget)
    edge = np.where(allowed, costs[None, :] + switching, np.inf)
    value = np.zeros(len(STATES))
    for length in range(1, max_horizon + 1):
        value = np.min(edge + value[None, :], axis=1)
        arithmetic_tolerance = max(TOL, 128*np.finfo(float).eps*length*max(1.,abs(costs[s0])))
        if value[s0] < length * costs[s0] - arithmetic_tolerance:
            return length
    return 0  # right-censored: no gain within max_horizon


def exact_dp(model: Model, headrooms: Sequence, initial="MR", budget=1,
             weights=(F(1, 400), F(1, 400)), emergency=True):
    """Rational-arithmetic DP for independent short-horizon certification.

    Deliberately uses dictionaries/Python fractions instead of numpy matrices.
    Returns None if infeasible. Exact equality uses the M1 tie rule.
    """
    value = {s: F(0) for s in STATES}
    policies = []
    for h in reversed(headrooms):
        costs = {s: model.snapshot(s, h).cost for s in STATES}
        finite = [s for s in STATES if costs[s] != math.inf]
        new, policy = {}, {}
        for s in STATES:
            distance = lambda p: sum(a != b for a, b in zip(s, p))
            allowed = [p for p in finite if distance(p) <= budget]
            if not allowed and emergency and finite:
                nearest = min(map(distance, finite))
                allowed = [p for p in finite if distance(p) == nearest]
            candidates = []
            for p in allowed:
                penalty = sum((w for w, a, b in zip(weights, s, p) if a != b), F(0))
                if value[p] != math.inf:
                    candidates.append((costs[p] + penalty + value[p], p != s, distance(p), INDEX[p], p))
            if candidates:
                choice = min(candidates)
                new[s], policy[s] = choice[0], choice[-1]
            else:
                new[s], policy[s] = math.inf, None
        value = new
        policies.append(policy)
    current, path = initial, []
    for policy in reversed(policies):
        current = policy[current]
        if current is None:
            return math.inf, []
        path.append(current)
    return value[initial], path
