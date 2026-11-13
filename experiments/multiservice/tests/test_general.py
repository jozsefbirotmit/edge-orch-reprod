from fractions import Fraction as F
from itertools import product
import importlib.util
import math
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from m1_general import Model,Parameters,Problem,values,recover,mpc,return_rollout,evaluate,rational_dp
from populations import population,all_populations
from structural import payback


def load_reference():
    spec=importlib.util.spec_from_file_location('m1',ROOT/'inputs/m1_n2_reference.py')
    m=importlib.util.module_from_spec(spec);sys.modules['m1']=m;spec.loader.exec_module(m)
    spec=importlib.util.spec_from_file_location('return_ref',ROOT/'inputs/return_n2_reference.py')
    r=importlib.util.module_from_spec(spec);sys.modules['return_ref']=r;spec.loader.exec_module(r)
    return m,r


class GeneralTests(unittest.TestCase):
    def test_n2_reference_physics_and_rational_anchor(self):
        old,_=load_reference();m=Model();ref=old.Model()
        for h in [F(0),F(10),F(18),F(30),F(60),F(78),F(100),F(400)]:
            for s in m.states:
                snap=m.snapshot(s,h);old_snap=ref.snapshot(s,h)
                self.assertEqual(snap['cost'],old_snap.cost)
                self.assertEqual(snap['feasible'],old_snap.feasible)
            np.testing.assert_allclose(m.costs(float(h)),ref.costs(h),rtol=1e-13)
        self.assertEqual(m.snapshot('MR',F(100))['cost'],F(263,540))
        self.assertEqual(m.snapshot('RM',F(100))['cost'],F(21071,44280))
        self.assertEqual(m.snapshot('RR',F(100))['cost'],F(24443,49140))

    def test_n2_exact_paths_match_existing_controllers(self):
        old,rar=load_reference();m=Model()
        for trace in [[100]*12,[60]*8+[100]*4+[60]*12,[400,10,0,100,80,60,400]]:
            table=m.table(trace)
            for budget in [1,2]:
                p=Problem(m,table,'MR',budget);ref=rar.Problem(table,'MR',budget)
                for h in [1,3,5,8,None]:
                    path=[m.states[j] for j in mpc(p,h)]
                    self.assertEqual(path,rar.mpc(ref,h))
                for cap,levels in [(8,None),(64,(3,5,8,16,32,64))]:
                    path,audit=return_rollout(p,cap,levels)
                    rp,ra=rar.return_rollout(ref,cap,levels)
                    self.assertEqual([m.states[j] for j in path],rp)
                    self.assertEqual([a['accepted_horizon'] for a in audit],[a['accepted_horizon'] for a in ra])

    def test_balanced_non_negligible_populations(self):
        for meta,p in all_populations():
            self.assertEqual(sum(s.b for s in p.services),F(17,10))
            self.assertEqual(sum(s.compute for s in p.services),F(30))
            for s in p.services:
                # Rounding can move a share by at most 0.0001 units.
                self.assertGreaterEqual(float(s.b),1.7*.5/meta['n']-.0001)
                self.assertGreaterEqual(float(s.compute),30*.5/meta['n']-.0001)

    def test_vector_costs_match_scalar_all_states(self):
        for n in [3,4,5]:
            _,par=population(n,0);m=Model(par)
            self.assertEqual(m.S,3**n)
            for h in [0.,10.,20.,30.,78.,100.,400.]:
                independent=[float(m.snapshot(s,h)['cost']) for s in m.states]
                np.testing.assert_allclose(m.costs(h),independent,rtol=2e-13,atol=2e-13)

    def test_exact_subset_capacity_boundary(self):
        _,par=population(5,2);m=Model(par)
        for state in ['RMMMM','RRMMM','RRRMM','RRRRR']:
            h=sum((s.compute for s,k in zip(par.services,state) if k=='R'),F(0))
            self.assertFalse(m.snapshot(state,h)['feasible'])
            self.assertFalse(np.isfinite(m.costs(float(h))[m.index[state]]))

    def test_sparse_edges_equal_full_emergency_rule(self):
        for n in [3,4,5]:
            _,par=population(n,1);m=Model(par)
            table=m.table([0,5,10,20,100])
            for budget in [0,1,2,n]:
                p=Problem(m,table,'R'*n,budget)
                for c,step in zip(table,p.steps):
                    finite=np.isfinite(c)
                    for s in range(m.S):
                        expected=finite & (m.distance[s]<=budget)
                        override=not expected.any()
                        if override:expected=finite & (m.distance[s]==m.distance[s,finite].min())
                        actual=np.zeros(m.S,dtype=bool);actual[step.index[s,step.valid[s]]]=True
                        np.testing.assert_array_equal(actual,expected)
                        self.assertEqual(bool(step.override[s]),override)

    def test_n3_fraction_dp_and_brute_paths(self):
        _,par=population(3,1);m=Model(par);trace=[F(30),F(100),F(20)]
        initial='MRM';p=Problem(m,m.table(trace),initial)
        exact,path=rational_dp(m,trace,initial)
        actual=mpc(p,None)
        self.assertEqual([m.states[s] for s in actual],path)
        self.assertAlmostEqual(p.path_cost(actual),float(exact),places=12)
        # Fully enumerate every physically admissible 3-slot path, independent
        # of Bellman recursion. Initial is feasible, so ordinary 1-move edges.
        brute=math.inf
        for path in product(m.states,repeat=3):
            s=initial;total=F(0)
            for h,j in zip(trace,path):
                d=sum(a!=b for a,b in zip(s,j))
                if d>1:break
                c=m.snapshot(j,h)['cost']
                if c==math.inf:break
                total+=c+F(d,400);s=j
            else:brute=min(brute,total)
        self.assertEqual(exact,brute)

    def test_general_dp_against_independent_dense_recursion(self):
        for n in [3,4,5]:
            _,par=population(n,0);m=Model(par);trace=[400,0,20,100,10]
            p=Problem(m,m.table(trace),'R'*n)
            v=np.zeros(m.S)
            for t in range(len(trace)-1,-1,-1):
                nv=np.full(m.S,np.inf);c=p.table[t];finite=np.isfinite(c)
                for s in range(m.S):
                    js=np.flatnonzero(finite & (m.distance[s]<=1))
                    if not len(js):js=np.flatnonzero(finite & (m.distance[s]==m.distance[s,finite].min()))
                    nv[s]=min(c[js]+p.switch[s,js]+v[js])
                v=nv
            path=mpc(p,None)
            self.assertAlmostEqual(p.path_cost(path),v[p.initial],places=11)

    def test_general_rar_bound_ledger_full_preview(self):
        for n in [3,4,5]:
            _,par=population(n,1);m=Model(par)
            trace=[100]*8+[10]*3+[400]*8+[0]*3+[80]*8
            for budget in [1,2]:
                p=Problem(m,m.table(trace),'R'*n,budget)
                base=p.path_cost(mpc(p,1));opt=p.path_cost(mpc(p,None))
                for cap,levels in [(5,None),(8,None),(32,(3,5,8,16,32))]:
                    path,audit=return_rollout(p,cap,levels);cost=p.path_cost(path)
                    self.assertLessEqual(cost,base+1e-10)
                    self.assertGreaterEqual(cost,opt-1e-10)
                    self.assertAlmostEqual(base-cost,sum(a['accepted_gain'] for a in audit),places=10)
                    ev=evaluate(p,path)
                    self.assertAlmostEqual(cost,ev['operating_cost']+ev['switching_cost'],places=11)
                    if cap>=len(trace):self.assertAlmostEqual(cost,opt,places=11)

    def test_no_preview_leak_general_population(self):
        for n in [3,4,5]:
            _,par=population(n,3);m=Model(par);initial=m.states[int(np.argmin(m.costs(20)))]
            a=Problem(m,m.table([100]*8+[0]*40),initial)
            b=Problem(m,m.table([100]*8+[400]*40),initial)
            pa,aa=return_rollout(a,8);pb,ab=return_rollout(b,8)
            self.assertEqual(pa[0],pb[0]);self.assertEqual(aa[0],ab[0])
            self.assertTrue(all(r['preview_queried']<=8 for r in aa+ab))

    def test_outage_and_strict_budget_fail(self):
        _,par=population(3,0);m=Model(par)
        p=Problem(m,np.full((3,m.S),np.inf),'RRR')
        self.assertEqual(mpc(p,None),[]);self.assertEqual(return_rollout(p,8),([],[]))
        p=Problem(m,m.table([0]),'RRR',emergency=False)
        self.assertEqual(mpc(p,1),[])

    def test_original_payback_and_closed_return(self):
        m=Model();c=m.costs(100)
        self.assertEqual(payback(m,c,'MR',closed=False)['horizon'],3)
        self.assertEqual(payback(m,c,'MR',closed=True)['horizon'],6)

    def test_genuine_four_move_operating_barrier(self):
        _,par=population(5,14);m=Model(par);initial='MCCMR'
        baseline=m.snapshot(initial,F(30))['cost']
        goal=m.snapshot('RMMCR',F(30))['cost']
        self.assertLess(goal,baseline)
        for state in m.states:
            d=sum(a!=b for a,b in zip(initial,state))
            c=m.snapshot(state,F(30))['cost']
            if 1<=d<=3:self.assertGreater(c,baseline)
        self.assertEqual(sum(a!=b for a,b in zip(initial,'RMMCR')),4)


if __name__=='__main__':unittest.main(verbosity=2)
