"""Unfiltered local +/-2% parameter probes around the discovered witnesses.

This is separate from the predeclared 72-population ensemble. Resource totals
are renormalized to the same 1.7/30 values. Initial placement is recomputed as
the optimum at the same low H; the high/low headrooms are fixed.
"""
import json
from fractions import Fraction as F
import numpy as np
from m1_general import Model,Parameters,Service
from populations import population,rounded
from structural import trapped_states,escape_distance,payback
from run_experiments import DATA,write


def normalize(raw,total):
    v=np.rint(np.asarray(raw)/sum(raw)*total*10000).astype(int)
    v[-1]+=round(total*10000)-int(v.sum())
    return [F(int(x),10000) for x in v]


def main():
    result=[]
    for w in json.loads((DATA/'selected_witnesses.json').read_text()):
        meta,p=population(w['n'],w['replicate'])
        for replicate in range(50):
            seed=700000+1000*w['n']+replicate;rng=np.random.default_rng(seed)
            b=normalize([float(s.b)*rng.uniform(.98,1.02) for s in p.services],1.7)
            c=normalize([float(s.compute)*rng.uniform(.98,1.02) for s in p.services],30.)
            services=tuple(Service(b[i],rounded(float(s.eta)*rng.uniform(.98,1.02)),c[i],
                                   rounded(float(s.slo)*rng.uniform(.98,1.02)),
                                   tuple(rounded(float(x)*rng.uniform(.98,1.02)) for x in s.nominal))
                           for i,s in enumerate(p.services))
            m=Model(Parameters(services));s=int(np.argmin(m.costs(w['low'])));cost=m.costs(w['high'])
            trapped=s in trapped_states(m,cost)
            finite=np.isfinite(cost)&(m.distance[s]==1)
            strict=trapped and min(cost[finite])>cost[s]+1e-8
            depth=escape_distance(m,cost,s) if trapped else 0
            pb=payback(m,cost,s,512) if trapped else {'horizon':0}
            result.append({'source_id':w['id'],'n':w['n'],'replicate':replicate,'seed':seed,
                           'low':w['low'],'high':w['high'],'initial':m.states[s],
                           'same_initial':int(m.states[s]==w['initial']),'myopic_trapped':int(trapped),
                           'strict_trap':int(strict),'min_moves_to_better':depth,'payback':pb['horizon']})
        print('local probes',w['id'],flush=True)
    write('local_robustness.csv',result)


if __name__=='__main__':main()
