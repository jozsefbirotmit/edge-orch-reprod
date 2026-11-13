"""Scientific figures generated only from the archived experiment outputs."""
import csv
import json
from fractions import Fraction as F
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,Normalize
from matplotlib.patches import Patch
from m1_general import Model
from populations import population
from run_experiments import ROOT,DATA,DURATIONS,KAPPAS

FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
read=lambda name:list(csv.DictReader((DATA/name).open()))
selected=json.loads((DATA/'selected_witnesses.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.titleweight':'bold','savefig.dpi':190,
                     'figure.dpi':120,'pdf.fonttype':42})
COLOR={'myopic':'#B94D42','MPC8':'#A36DA7','RAR8':'#219578','MPC64':'#9A7B39',
       'RAR-A64':'#237DA3','offline':'#172F48','MPC129':'#A36DA7','RAR129':'#219578'}
TIER_COLORS=['#256C8C','#E5AB48','#9BA7AE']


def save(fig,name):
    for ext in ['png','pdf']:fig.savefig(FIG/(name+'.'+ext),bbox_inches='tight',facecolor='white')
    plt.close(fig)


def static():
    nm=read('nonmonotone_witnesses.csv');static=read('static_envelopes.csv');cert=[]
    fig,axes=plt.subplots(2,3,figsize=(10.4,5.1),layout='constrained',sharex='col',
                           gridspec_kw={'height_ratios':[1.1,1.]})
    for col,n in enumerate([3,4,5]):
        # Pick the largest strict sampled gap for a readable illustration.
        w=max((r for r in nm if int(r['n'])==n),key=lambda r:float(r['min_uniqueness_gap']))
        meta,p=population(n,int(w['replicate']));m=Model(p)
        rows=[r for r in static if r['id']==w['id']];H=np.array([float(r['H']) for r in rows])
        J=np.array([float(r['cost']) for r in rows]);states=[r['placement'] for r in rows]
        hs=[float(w[f'H{i}']) for i in [1,2,3]]
        for h in hs:
            exact=sorted((m.snapshot(s,F(str(h)))['cost'],s) for s in m.states)
            cert.append({**meta,'H':str(h),'placement':exact[0][1],
                         'J_exact':str(exact[0][0]),'strict_gap_exact':str(exact[1][0]-exact[0][0])})
            assert exact[1][0]>exact[0][0]
        ax=axes[0,col]
        ax.plot(H[1:],J[1:],color='#172F48',lw=1.7)
        for h in hs:ax.axvline(h,color='#9DA9AE',lw=.7,ls=':')
        ax.set(xscale='log',title=f'n = {n} | {w["id"]}',ylim=(min(J)*.97,min(max(J),min(J)*1.8)))
        if col==0:ax.set_ylabel('Optimal SLO stress J*')
        tiers=np.array([[m.tiers[m.index[s],i] for s in states[1:]] for i in range(n)])
        ax=axes[1,col]
        # Edges of logarithmic sample bins; all nonzero samples retained.
        hh=H[1:];edges=np.r_[hh[0]/np.sqrt(hh[1]/hh[0]),np.sqrt(hh[:-1]*hh[1:]),hh[-1]*np.sqrt(hh[-1]/hh[-2])]
        ax.pcolormesh(edges,np.arange(n+1),tiers,cmap=ListedColormap(TIER_COLORS),vmin=-.5,vmax=2.5,
                      shading='flat',edgecolors='face',linewidth=0,rasterized=True)
        ax.set(xscale='log',xlabel='RAN headroom H',yticks=np.arange(n)+.5,
               yticklabels=[f'S{i+1}'+(' *' if i+1==int(w['service']) else '') for i in range(n)])
        ax.invert_yaxis()
        for h in hs:ax.axvline(h,color='white',lw=1.2,ls=':')
        if col==0:ax.set_ylabel('Service placement')
    handles=[Patch(color=c,label=k) for c,k in zip(TIER_COLORS,['RAN','MEC','Core'])]
    fig.legend(handles=handles,loc='outside lower center',ncol=3,frameon=False)
    save(fig,'fig01_static_nonmonotonicity')
    (DATA/'static_fraction_certificates.json').write_text(json.dumps(cert,indent=2)+'\n')


def exchange_geometry():
    pb=read('witness_paybacks.csv')
    fig,axes=plt.subplots(1,3,figsize=(10.4,3.4),layout='constrained')
    for ax,w in zip(axes,selected):
        _,p=population(w['n'],w['replicate']);m=Model(p)
        row=next(r for r in pb if r['id']==w['id'] and r['budget']=='1' and r['closed']=='0')
        path=[w['initial']]+[s for s,count in json.loads(row['path_rle'])]
        base=float(m.snapshot(w['initial'],w['high'])['cost'])
        y=[float(m.snapshot(s,w['high'])['cost'])-base for s in path]
        x=np.arange(len(path))
        ax.axhline(0,color='#9AA5AA',lw=1.)
        ax.plot(x,y,'o-',color='#237DA3',lw=1.8,ms=5)
        for xx,yy,s in zip(x,y,path):
            ax.annotate(s,(xx,yy),xytext=(0,8 if yy>=0 else -15),textcoords='offset points',ha='center',fontsize=9.5)
        span=max(y)-min(y)
        ax.set(title=f'n = {w["n"]} | H = {w["high"]}',xlabel='Single-service move',
               xticks=x,ylim=(min(y)-span*.36,max(y)+span*.43))
        if ax is axes[0]:ax.set_ylabel('Operating stress minus initial stress')
        ax.text(.03,.03,f'First gain: {row["horizon"]} slots',transform=ax.transAxes,fontsize=9.5)
    save(fig,'fig02_exchange_geometry')


def trajectories():
    raw=read('witness_timeseries.csv')
    names=['myopic','MPC8','RAR8','MPC64','RAR-A64','offline']
    fig,axes=plt.subplots(2,3,figsize=(10.4,5.3),sharex='col',layout='constrained',
                           gridspec_kw={'height_ratios':[.8,1.8]})
    for col,w in enumerate(selected):
        select=lambda name:[r for r in raw if r['id']==w['id'] and r['trace']=='pulse' and r['controller']==name]
        rows=select('myopic');slots=np.array([int(r['slot']) for r in rows]);H=[float(r['H']) for r in rows]
        axes[0,col].plot(slots,H,color='#172F48',lw=1.7)
        axes[0,col].set(title=f'n = {w["n"]} | {w["id"]}')
        if col==0:axes[0,col].set_ylabel('Headroom H')
        base=np.cumsum([float(r['operating_cost'])+float(r['switching_cost']) for r in rows])
        for name in names:
            rows=select(name)
            cost=np.cumsum([float(r['operating_cost'])+float(r['switching_cost']) for r in rows])
            axes[1,col].plot(slots,cost-base,color=COLOR[name],label=name,lw=1.6,ls=':' if name in ['MPC8','MPC64'] else '-')
        axes[1,col].axhline(0,color='#999',lw=.7)
        axes[1,col].set_xlabel('Slot')
        if col==0:axes[1,col].set_ylabel('Cumulative cost difference\nfrom myopic')
    handles,labels=axes[1,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=6,frameon=False,fontsize=8)
    save(fig,'fig03_pulse_trajectories')


def parameter_map():
    rows=read('pulse_map_summary.csv')
    fig,axes=plt.subplots(3,2,figsize=(8.4,7.7),layout='constrained',sharex=True,sharey=True)
    cmap=plt.get_cmap('YlGnBu').copy();cmap.set_bad('#D9DFE3')
    for row,w in enumerate(selected):
        subset=[r for r in rows if r['id']==w['id'] and r['budget']=='1']
        get=lambda c,k,d:next(r for r in subset if r['controller']==c and float(r['kappa_per_service'])==k and int(r['duration'])==d)
        for col,c in enumerate(['RAR8','RAR-A64']):
            recovery=np.full((len(KAPPAS),len(DURATIONS)),np.nan)
            for i,k in enumerate(KAPPAS):
                for j,d in enumerate(DURATIONS):
                    oracle=float(get('offline',k,d)['saving_vs_myopic'])
                    actual=float(get(c,k,d)['saving_vs_myopic'])
                    if oracle>1e-9:recovery[i,j]=np.clip(actual/oracle,0,1)
            ax=axes[row,col];im=ax.imshow(recovery,cmap=cmap,vmin=0,vmax=1,aspect='auto',interpolation='nearest')
            ax.set_title(f'{c} | n = {w["n"]} | {w["low"]} → {w["high"]} → {w["low"]}',fontsize=10)
            if col==0:
                for i,k in enumerate(KAPPAS):
                    for j,d in enumerate(DURATIONS):
                        if float(get('MPC8',k,d)['saving_vs_myopic'])< -1e-9:ax.plot(j,i,'x',color='#B63527',ms=5,mew=1.1)
            shown=list(range(0,len(DURATIONS),2))
            ax.set(xticks=shown,xticklabels=[DURATIONS[i] for i in shown],
                   yticks=range(len(KAPPAS)),yticklabels=[f'{k:g}' for k in KAPPAS])
            ax.tick_params(axis='x',labelrotation=35,labelsize=9)
            if col==0:ax.set_ylabel('Migration cost / service')
            if row==2:ax.set_xlabel('High-headroom duration (slots)')
    fig.colorbar(im,ax=axes,location='right',shrink=.83,pad=.02,label='Fraction of offline gain recovered')
    fig.legend(handles=[Patch(color='#D9DFE3',label='Myopic is optimal for this pulse')],
               loc='outside lower center',frameon=False,fontsize=8)
    save(fig,'fig04_return_parameter_map')


def gaps():
    rows=read('aggregate_primary.csv');names=['myopic','MPC3','MPC8','RAR8','MPC64','RAR-A64']
    fig,axes=plt.subplots(1,3,figsize=(10.4,3.7),layout='constrained')
    for ax,n in zip(axes,[3,4,5]):
        r=[next(r for r in rows if int(r['n'])==n and r['controller']==c) for c in names]
        ax.bar(range(len(names)),[float(x['mean_gap_pct']) for x in r],color=[COLOR.get(c,'#B898BF') for c in names])
        ax.set(title=f'n = {n}',xticks=range(len(names)),xticklabels=names)
        ax.tick_params(axis='x',rotation=55,labelsize=8)
        if n==3:ax.set_ylabel('Mean gap to offline (%)')
    save(fig,'fig05_population_gaps')


if __name__=='__main__':
    static();exchange_geometry();trajectories();parameter_map();gaps()
