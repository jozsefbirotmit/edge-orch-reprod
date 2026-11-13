from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np
P=Path(__file__).parent
rows=list(csv.DictReader((P/'population_outcomes.csv').open()))
variants=['full','no_transform','no_transport_congestion','no_compute_congestion']
labels=['Full M0/M1 model','No traffic reduction','Constant transport delay','No compute congestion']
rev=[sum(r['has_reversal']=='1' for r in rows if r['variant']==v) for v in variants]
trap=[sum(r['has_inherited_strict_trap']=='1' for r in rows if r['variant']==v) for v in variants]
y=np.arange(len(variants))
fig,ax=plt.subplots(figsize=(7.5,3.5))
barh=.35
c1,c2=plt.rcParams['axes.prop_cycle'].by_key()['color'][:2]
ax.barh(y-barh/2,rev,barh,label='RAN–MEC–RAN reversal',color=c1)
ax.barh(y+barh/2,trap,barh,label='Inherited strict exchange trap',color=c2)
for ys,counts in [(y-barh/2,rev),(y+barh/2,trap)]:
 for yy,v in zip(ys,counts):
  ax.text(v+.9,yy,str(v),va='center',fontsize=9)
ax.set_yticks(y,labels)
ax.invert_yaxis()
ax.set_xlim(0,80)
ax.set_xlabel('Number of affected populations (out of 72)')
ax.legend(loc='lower center',bbox_to_anchor=(.55,-.46),ncol=2,frameon=False,fontsize=9)
ax.grid(axis='x',alpha=.2)
ax.set_axisbelow(True)
fig.subplots_adjust(left=.31,bottom=.25,right=.94,top=.96)
for ext in ('png','svg','pdf'):fig.savefig(P/f'ablation_population_counts.{ext}',dpi=220)
plt.close(fig)

# Same fixed initial state, model-dependent 'cost relative to start' for selected n5_14.
d=list(csv.DictReader((P/'n5_distance_profiles.csv').open()))
fig,ax=plt.subplots(figsize=(7.1,3.35))
for v,label in zip(variants,labels):
 dd=sorted([r for r in d if r['variant']==v],key=lambda r:int(r['distance']))
 ax.plot([int(r['distance']) for r in dd],[float(r['minus_start']) for r in dd],
  marker='o',linewidth=1.7,label=label)
ax.axhline(0,linestyle='--',color='.4',linewidth=1)
ax.set_xlabel('Hamming distance from MCCMR (n=5, H=30)')
ax.set_ylabel('Minimum operating cost relative to MCCMR')
ax.set_xticks(range(6))
ax.grid(alpha=.2)
ax.legend(loc='upper left',fontsize=8,frameon=False)
fig.tight_layout()
for ext in ('png','svg','pdf'):fig.savefig(P/f'ablation_n5_distance_profile.{ext}',dpi=220)
plt.close(fig)
