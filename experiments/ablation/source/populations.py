"""Predeclared balanced parameter ensembles, without response-based filtering.

Both traffic and compute totals equal the original two-service totals. Each
service has at least half of the equal share of BOTH totals. The two families
sample independent parameters or the original compression/compute trade-off;
neither appends tiny dummy services to a two-service witness.
"""
from fractions import Fraction as F
import numpy as np
from m1_general import Service, Parameters

COUNTS={3:32,4:24,5:16}
BASE_SEED=104729


def rounded(x):return F(round(float(x)*10000),10000)


def allocate(raw,total):
    n=len(raw)
    shares=.5/n+.5*np.asarray(raw)/sum(raw)
    units=np.rint(shares*total).astype(int)
    units[-1]+=total-int(units.sum())
    return [F(int(x),10000) for x in units]


def population(n,replicate):
    seed=BASE_SEED+1000*n+replicate
    rng=np.random.default_rng(seed)
    family='independent' if replicate%2==0 else 'coupled'
    if family=='independent':
        b=allocate(rng.gamma(3,1,n),17000)
        c=allocate(rng.gamma(3,1,n),300000)
        eta=rng.uniform(.08,.65,n)
        pr=rng.uniform(1.8,3.,n)
        pm=pr*rng.uniform(.65,.90,n)
        pc=pm*rng.uniform(.65,.90,n)
        tau=rng.uniform(16,23,n)
    else:
        z=rng.uniform(0,1,n)
        b=allocate((1.5-.8*z)*rng.uniform(.85,1.15,n),17000)
        c=allocate((1.7-1.1*z)*rng.uniform(.85,1.15,n),300000)
        eta=np.clip(.08+.57*z+rng.uniform(-.04,.04,n),.05,.70)
        pr=(2.7-.6*z)*rng.uniform(.92,1.08,n)
        pm=(2.1-.4*z)*rng.uniform(.92,1.08,n)
        pc=(1.55-.25*z)*rng.uniform(.92,1.08,n)
        tau=(17.5+3*z)*rng.uniform(.96,1.04,n)
    services=tuple(Service(b[i],rounded(eta[i]),c[i],rounded(tau[i]),
                           tuple(rounded(x[i]) for x in (pr,pm,pc))) for i in range(n))
    return {'id':f'n{n}_{replicate:02d}','n':n,'replicate':replicate,'seed':seed,'family':family},Parameters(services)


def rows(meta,p):
    return [{**meta,'service':i+1,'b':float(s.b),'eta':float(s.eta),'compute':float(s.compute),
             'slo':float(s.slo),'p_R':float(s.nominal[0]),'p_M':float(s.nominal[1]),
             'p_C':float(s.nominal[2]),'radio':float(s.radio),
             'traffic_share':float(s.b/F(17,10)),'compute_share':float(s.compute/30)}
            for i,s in enumerate(p.services)]


def all_populations():
    for n,count in COUNTS.items():
        for rep in range(count):yield population(n,rep)
