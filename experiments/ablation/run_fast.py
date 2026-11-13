"""Efficient matched-population static structural ablation."""
from ablation_study import *
from collections import defaultdict

Hs=np.r_[0,np.geomspace(2,400,481)]
LOW=[10,15,20,25,30,40,50,60]
HIGH=[20,25,30,40,50,60,70,80,90,100,120,150]
HALL=sorted(set(LOW+HIGH))

def has_reversal(model):
    tab=model.table(Hs)
    ix=np.argmin(tab,axis=1)
    part=np.partition(tab,1,axis=1)
    gap=part[:,1]-part[:,0]
    strict=np.flatnonzero(gap>1e-8)
    for i in range(model.n):
        phase=[]
        for t in strict:
            k=int(model.tiers[ix[t],i])
            if not phase or phase[-1]!=k:phase.append(k)
        first_r=False;found_m=False
        for k in phase:
            if k==0 and not first_r:first_r=True
            elif k==1 and first_r:found_m=True
            elif k==0 and found_m:return True
    return False

def inherited(model):
    cost={h:model.costs(h) for h in HALL}
    neigh=(model.distance==1)
    n=0;depth=0;examples=[]
    for lo in LOW:
        si=int(np.argmin(cost[lo]))
        for hi in HIGH:
            if hi<=lo:continue
            c=cost[hi]
            if not np.isfinite(c[si]):continue
            neighbor=c[neigh[si]&np.isfinite(c)]
            if len(neighbor) and np.min(neighbor)>c[si]+1e-8 and np.min(c)<c[si]-1e-8:
                n+=1
                if len(examples)<3:examples.append((lo,hi,model.states[si]))
    return n,examples


def main():
    allrows=[]
    for n,count in COUNTS.items():
        for replicate in range(count):
            meta,p=population(n,replicate)
            for mode in MODES:
                model=make_model(p,mode)
                rev=has_reversal(model)
                traps,examples=inherited(model)
                allrows.append({'variant':mode,**meta,
                                'has_reversal':int(rev),
                                'has_inherited_strict_trap':int(traps>0),
                                'inherited_trap_pairs':int(traps),
                                'example_pairs':str(examples)})
        print('n=',n,'done',flush=True)
    with (HERE/'population_outcomes.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
    summaries=[]
    for mode in MODES:
        for n in [3,4,5,'all']:
            rows=[r for r in allrows if r['variant']==mode and (n=='all' or r['n']==n)]
            entry={'variant':mode,'n':n,'N':len(rows),'reversal':sum(r['has_reversal'] for r in rows),
                   'inherited_trap':sum(r['has_inherited_strict_trap'] for r in rows)}
            summaries.append(entry)
            print(entry,flush=True)
    (HERE/'matched_population_summary.json').write_text(json.dumps(summaries,indent=2)+'\n')

if __name__=='__main__':main()
