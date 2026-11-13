"""Check every exported primary trajectory independently of controller/Step.

Recomputes costs, Hamming penalties, the normal-set-empty emergency condition,
minimum repair distance, SLO slots, and aggregate metrics from RLE archives.
"""
import csv
import gzip
import json
from collections import defaultdict
import numpy as np
from m1_general import Model
from populations import population
from run_experiments import DATA,dump


def main():
    summaries=list(csv.DictReader((DATA/'primary_summary.csv').open()))
    key=lambda r:(r['id'],r['trace'],int(r['budget']),r['controller'])
    summary={key(r):r for r in summaries};traces=defaultdict(list)
    for r in csv.DictReader((DATA/'primary_traces.csv').open()):traces[r['id'],r['trace']].append(float(r['H']))
    current=None;cached={};count=slots=0;max_error=0.;seen=set()
    with gzip.open(DATA/'controller_paths.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line);row=summary[key(r)];seen.add(key(r))
            if current!=r['id']:
                current=r['id'];_,par=population(r['n'],r['replicate']);m=Model(par);cached={}
            name=r['trace']
            if name not in cached:cached[name]=m.table(traces[r['id'],name])
            table=cached[name]
            path=[m.index[s] for s,length in r['rle'] for _ in range(length)]
            assert len(path)==len(table)==int(row['T'])
            previous=m.index[r['initial']];op=sw=0.;moves=overrides=violations=0
            for c,j in zip(table,path):
                assert np.isfinite(c[j])
                d=int(m.distance[previous,j]);finite=np.isfinite(c)
                normal=finite & (m.distance[previous]<=r['budget'])
                if not normal.any():
                    assert d==int(min(m.distance[previous,finite]));overrides+=1
                else:assert normal[j]
                op+=float(c[j]);sw+=d*.0025;moves+=d;violations+=int(c[j]>1+1e-12)
                previous=j;slots+=1
            for field,actual in [('operating_cost',op),('switching_cost',sw),('total_cost',op+sw)]:
                error=abs(actual-float(row[field]));max_error=max(max_error,error);assert error<1e-8
            assert moves==int(row['service_moves'])
            assert overrides==int(row['overrides'])
            assert violations==int(row['slo_violation_slots'])
            count+=1
    assert len(seen)==len(summaries)
    out={'trajectories_verified':count,'slots_verified':slots,'max_cost_error':max_error,'status':'passed'}
    dump('archive_validation.json',out);print(json.dumps(out,indent=2))


if __name__=='__main__':main()
