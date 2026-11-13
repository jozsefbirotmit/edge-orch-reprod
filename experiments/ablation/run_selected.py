"""Selected M0 two-service and M1 five-service one-factor ablations."""
from ablation_study import *
import numpy as np

def main():
    selected=[];per_distance=[];witnesses=[]
    headrooms=np.r_[0,np.geomspace(2,400,481)]
    for mode in MODES:
        m2=make_model(Parameters(),mode)
        reversals,phases=strict_reversals(m2,headrooms)
        for H in (40,100,400):
            c=m2.costs(H);best=int(np.argmin(c))
            witnesses.append({'variant':mode,'H':H,'optimal_placement':m2.states[best],
                              'optimal_stress':float(c[best]),
                              'strict_reversal_on_grid':int(bool(reversals))})
        _,p=population(5,14)
        m5=make_model(p,mode)
        dist,strict_neighbor,better,depth=costs_per_distance(m5,30,'MCCMR')
        c_lo=m5.costs(10);c_hi=m5.costs(30);start=m5.index['MCCMR']
        selected.append({'variant':mode,'start_optimal_at_H10':int(start==np.argmin(c_lo)),
                         'start_cost_H30':float(c_hi[start]),
                         'global_state_H30':m5.states[int(np.argmin(c_hi))],
                         'global_cost_H30':float(np.min(c_hi)),
                         'strict_exchange_trap':int(strict_neighbor and better),
                         'shortest_escape_moves':int(depth)})
        per_distance.extend([{'variant':mode,**r} for r in dist])
    for filename,items in [('n2_witnesses.csv',witnesses),('n5_selected_cases.csv',selected),('n5_distance_profiles.csv',per_distance)]:
        with (HERE/filename).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    assert next(r for r in selected if r['variant']=='full')['shortest_escape_moves']==4
    assert next(r for r in witnesses if r['variant']=='full' and r['H']==40)['optimal_placement']=='MR'
    assert next(r for r in witnesses if r['variant']=='full' and r['H']==100)['optimal_placement']=='RM'
    assert next(r for r in witnesses if r['variant']=='full' and r['H']==400)['optimal_placement']=='RR'
    print('n5 selected:',selected)

if __name__=='__main__':main()
