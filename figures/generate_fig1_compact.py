import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import rcParams
from pathlib import Path
rcParams.update({'font.family':'serif','mathtext.fontset':'dejavuserif','pdf.fonttype':42,'axes.linewidth':0.8,'font.size':8})
fig=plt.figure(figsize=(3.50, 2.01))
axnet=fig.add_axes([.035,.753,.93,.237]);axnet.set_xlim(0,1);axnet.set_ylim(0,1);axnet.axis('off')
centers=[0.12,0.5,0.88]; labs=['RAN (R)','MEC (M)','Core (C)'];heads=[r'$H(t)$',r'$H_M$',r'$H_C$']
for center,lab,head in zip(centers,labs,heads):
 x=center-0.115
 rect=FancyBboxPatch((x,.22),.23,.71,boxstyle='round,pad=0.008,rounding_size=0.035',edgecolor='#1b2c40',facecolor='#f0f5fa',linewidth=.85)
 axnet.add_patch(rect);axnet.text(center,.67,lab,ha='center',va='center',fontsize=8.4)
 axnet.text(center,.37,head,ha='center',va='center',fontsize=7.9)
for x1,x2,txt in [(0.245,0.37,r'$B_1,L_1$'),(0.625,0.75,r'$B_2,L_2$')]:
 axnet.annotate('',xy=(x2,.53),xytext=(x1,.53),arrowprops={'arrowstyle':'->','lw':.95,'color':'#18212b','shrinkA':0,'shrinkB':0,'mutation_scale':9})
 axnet.text((x1+x2)/2,.79,txt,ha='center',va='center',fontsize=8)
ax=fig.add_axes([.17,.17,.79,.58])
H=np.geomspace(8,500,1800)
jMC=np.full_like(H,1133/2100)
jMR=np.full_like(H,np.inf);m=H>12;jMR[m]=np.maximum(263/540,(1241/210+2*H[m]/(H[m]-12))/20)
jRM=np.full_like(H,np.inf);m=H>18;jRM[m]=(331/60+2.5*H[m]/(H[m]-18))/18
jRR=np.full_like(H,np.inf);m=H>30;jRR[m]=(2099/390+2.5*H[m]/(H[m]-30))/18
j=np.minimum.reduce([jMC,jMR,jRM,jRR])
for h in [2460/121,78,268.84858]:ax.axvline(h,color='#59626f',ls=':',lw=.68,zorder=0)
for c in [jMR,jRM,jRR]:
 vals=np.where(np.isfinite(c),c,np.nan)
 ax.plot(H, np.where((vals>=.446)&(vals<=.562),vals,np.nan),':',color='#b4c1cf',lw=.7,zorder=0)
for lo,hi,color in [(8,2460/121,'#243448'),(2460/121,78,'#217c9b'),(78,268.84858,'#a36a0a'),(268.84858,500,'#168058')]:
 mask=(H>=lo)&(H<=hi)
 ax.plot(H[mask],j[mask],color=color,lw=2.25,solid_capstyle='round')
ax.set_xscale('log');ax.set_xlim(8,500);ax.set_ylim(.443,.559)
ax.set_xticks([10,20,78,269,500]);ax.set_xticklabels(['10','20','78','269','500'])
ax.minorticks_off()
ax.set_yticks([.45,.5,.55]);ax.set_yticklabels(['0.45','0.50','0.55'])
ax.set_xlabel(r'RAN compute headroom $H$',labelpad=1,fontsize=8)
ax.set_ylabel(r'Optimal stress $J^\star$',labelpad=2,fontsize=8)
ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
ax.tick_params(axis='both',which='major',length=2.5,pad=2,labelsize=7.5)
for x,lab,c in [(12.9,'MC','#243448'),(35,'MR','#217c9b'),(138,'RM','#a36a0a'),(372,'RR','#168058')]:
 ax.text(x,.550,lab,color=c,ha='center',va='center',fontsize=8.8)
out = Path(__file__).with_name('fig1_model_reversal.pdf')
fig.savefig(out)
# Optional preview: fig.savefig(out.with_suffix('.png'), dpi=200)
print('made compact plot')
