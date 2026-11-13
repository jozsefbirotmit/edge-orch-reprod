from pathlib import Path
import csv
P=Path(__file__).parent
rows=list(csv.DictReader((P/'population_outcomes.csv').open()))
expected={'full':(55,70),'no_transform':(0,4),'no_transport_congestion':(1,5),'no_compute_congestion':(53,10)}
assert len(rows)==72*4
for mode,(rev,trap) in expected.items():
    s=[r for r in rows if r['variant']==mode]
    assert len(s)==72
    assert sum(int(r['has_reversal']) for r in s)==rev
    assert sum(int(r['has_inherited_strict_trap']) for r in s)==trap
n2=list(csv.DictReader((P/'n2_witnesses.csv').open()))
assert [(r['H'],r['optimal_placement']) for r in n2 if r['variant']=='full']==[('40','MR'),('100','RM'),('400','RR')]
sel=list(csv.DictReader((P/'n5_selected_cases.csv').open()))
assert next(r for r in sel if r['variant']=='full')['shortest_escape_moves']=='4'
assert all(r['strict_exchange_trap']=='0' for r in sel if r['variant']!='full')
print('PASS: 72 paired populations, witness placements, selected n=5 exchange barrier')
