"""Additional paired/decomposed statistics; all scopes kept explicit."""
import csv
import json
import numpy as np
from run_experiments import DATA,write,dump


def main():
    raw=list(csv.DictReader((DATA/'primary_summary.csv').open()))
    primary=[r for r in raw if r['budget']=='1']
    lookup={(r['id'],r['trace'],r['controller']):r for r in primary}
    paired={};bytrace=[]
    for n in [3,4,5]:
        rr=[r for r in primary if int(r['n'])==n and r['controller']=='RAR8']
        delta=[float(r['total_cost'])-float(lookup[r['id'],r['trace'],'MPC8']['total_cost']) for r in rr]
        paired[n]={'RAR8_better_MPC8':sum(x< -1e-9 for x in delta),
                   'equal':sum(abs(x)<=1e-9 for x in delta),'RAR8_worse_MPC8':sum(x>1e-9 for x in delta),
                   'MPC64_matches_offline':sum(float(r['gap_to_offline'])<1e-9 for r in primary if int(r['n'])==n and r['controller']=='MPC64'),
                   'RAR_A64_matches_offline':sum(float(r['gap_to_offline'])<1e-9 for r in primary if int(r['n'])==n and r['controller']=='RAR-A64')}
        for trace in dict.fromkeys(r['trace'] for r in primary):
            for c in ['myopic','MPC8','RAR8','MPC64','RAR-A64']:
                rs=[r for r in primary if int(r['n'])==n and r['trace']==trace and r['controller']==c]
                bytrace.append({'n':n,'trace':trace,'controller':c,'cases':len(rs),
                                'mean_gap_pct':float(np.mean([float(r['gap_to_offline_pct']) for r in rs])),
                                'max_saving_pct':max(float(r['saving_vs_myopic_pct']) for r in rs),
                                'mean_operating_cost':float(np.mean([float(r['operating_cost']) for r in rs])),
                                'mean_migration_cost':float(np.mean([float(r['switching_cost']) for r in rs]))})
    local=list(csv.DictReader((DATA/'local_robustness.csv').open()))
    robustness={}
    for n in [3,4,5]:
        rs=[r for r in local if int(r['n'])==n];positive=[int(r['payback']) for r in rs if int(r['payback'])>0]
        robustness[n]={'probes':len(rs),'strict_traps':sum(int(r['strict_trap']) for r in rs),
                       'depth_at_least_three':sum(int(r['min_moves_to_better'])>=3 for r in rs),
                       'depth_four':sum(int(r['min_moves_to_better'])==4 for r in rs),
                       'same_initial':sum(int(r['same_initial']) for r in rs),
                       'payback_min':min(positive),'payback_max':max(positive)}
    worst=max((r for r in primary if r['controller']=='offline'),key=lambda r:float(r['saving_vs_myopic_pct']))
    # Larger move budgets enlarge the feasible trajectory set; verify on every trace.
    coordination=[]
    for r in primary:
        if r['controller']!='offline':continue
        n=int(r['n']);ctx=(r['id'],r['trace'])
        costs={int(x['budget']):float(x['total_cost']) for x in raw if (x['id'],x['trace'])==ctx and x['controller']=='offline'}
        assert costs[1]>=costs[2]-1e-8 and costs[2]>=costs[n]-1e-8
        coordination.append({'id':r['id'],'n':n,'trace':r['trace'],'offline_m1':costs[1],
                             'offline_m2':costs[2],'offline_mn':costs[n],
                             'gain_m2_vs_m1':costs[1]-costs[2],'gain_mn_vs_m1':costs[1]-costs[n]})
    dump('paired_and_robustness.json',{'paired':paired,'local_robustness':robustness,
                                      'largest_primary_saving':worst,
                                      'primary_slots_per_controller':sum(int(r['T']) for r in primary if r['controller']=='myopic')})
    write('aggregate_by_trace.csv',bytrace);write('coordination_comparison.csv',coordination)
    print(json.dumps({'paired':paired,'local_robustness':robustness,'worst_id':worst['id'],'worst_trace':worst['trace']},indent=2))


if __name__=='__main__':main()
