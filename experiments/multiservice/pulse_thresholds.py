"""First profitable high-H duration, pricing all preposition/return slots.

Every duration 1..512 is checked in ascending order until first gain vs staying
at the inherited low-H optimum. Prefix and suffix each have 64 low-H slots.
Forward/backward factorization is exactly equivalent to full trace DP, and
the first winning trace is recovered and cross-checked using the ordinary DP.
"""
import json
import numpy as np
from m1_general import Model,Problem,mpc
from populations import population
from run_experiments import DATA,KAPPAS,write,encode_path


def main():
    rows=[]
    for w in json.loads((DATA/'selected_witnesses.json').read_text()):
        meta,par=population(w['n'],w['replicate']);m=Model(par)
        low=m.costs(w['low']);high=m.costs(w['high']);s=m.index[w['initial']]
        for budget in [1,2,m.n]:
            for kappa in KAPPAS:
                p=Problem(m,np.array([low,high]),s,budget,[kappa]*m.n)
                a,b=p.steps
                dense=np.full((m.S,m.S),np.inf)
                ii,jj=np.where(a.valid);dense[ii,a.index[ii,jj]]=a.cost[ii,jj]
                prefix=np.full(m.S,np.inf);prefix[s]=0.
                suffix=np.zeros(m.S)
                for _ in range(64):
                    prefix=np.min(prefix[:,None]+dense,axis=0)
                    suffix=np.min(a.cost+suffix[a.index],axis=1)
                previous_margin=0.;first=0;path=[]
                for D in range(1,513):
                    suffix=np.min(b.cost+suffix[b.index],axis=1)
                    optimum=float(np.min(prefix+suffix))
                    stay=128*low[s]+D*high[s];margin=float(stay-optimum)
                    if margin>1e-10:
                        first=D
                        trace=[w['low']]*64+[w['high']]*D+[w['low']]*64
                        check=Problem(m,m.table(trace),s,budget,[kappa]*m.n)
                        path=mpc(check,None)
                        assert abs(check.path_cost(path)-optimum)<1e-8
                        break
                    previous_margin=margin
                rows.append({**meta,'low':w['low'],'high':w['high'],'budget':budget,
                             'kappa_per_service':kappa,'first_high_duration':first,
                             'margin_before':previous_margin,'margin_at':margin,
                             'path_rle':json.dumps(encode_path(m,path))})
        print('pulse threshold',w['id'],flush=True)
    write('pulse_thresholds.csv',rows)


if __name__=='__main__':main()
