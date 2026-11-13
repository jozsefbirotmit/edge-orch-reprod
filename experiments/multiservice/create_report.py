"""Generate English technical report and Hungarian findings from measured data."""
import csv
import json
from pathlib import Path
from run_experiments import ROOT,DATA

read=lambda name:list(csv.DictReader((DATA/name).open()))
facts=json.loads((DATA/'findings.json').read_text())
extra=json.loads((DATA/'paired_and_robustness.json').read_text())
validation=json.loads((DATA/'archive_validation.json').read_text())
primary=read('primary_summary.csv');ws=read('witness_summary.csv')
thresholds=read('pulse_thresholds.csv');pb=read('witness_paybacks.csv')
params=read('populations.csv')


def num(x,d=3):return f'{float(x):.{d}f}'
def tex(s):return str(s).replace('_',r'\_')
def wr(n,trace,c):return next(r for r in ws if int(r['n'])==n and r['trace']==trace and r['controller']==c)


population_table=[];gap_table=[];cost_table=[];robust_table=[];budget_table=[];map_table=[]
for n in [3,4,5]:
    p=facts['populations'][str(n)]
    population_table.append(f"{n} & {3**n} & {p['count']} & {p['nonmonotone']}/{p['count']} & {p['with_inherited_strict_trap']}/{p['count']} & "+
                            num(100*p['min_traffic_share'],2)+' / '+num(100*p['min_compute_share'],2)+r' \\')
    for c in ['myopic','offline']:
        rs=[r for r in primary if int(r['n'])==n and r['budget']=='1' and r['controller']==c]
        cost_table.append(f'{n} & {c} & '+num(sum(float(r['operating_cost']) for r in rs)/len(rs),6)+' & '+
                          num(sum(float(r['switching_cost']) for r in rs)/len(rs),6)+' & '+
                          str(sum(int(r['slo_violation_slots']) for r in rs))+r' \\')
    r=extra['local_robustness'][str(n)]
    robust_table.append(f"{n} & {r['strict_traps']}/50 & {r['depth_at_least_three']}/50 & {r['depth_four']}/50 & {r['payback_min']}--{r['payback_max']}"+r' \\')
    getpb=lambda closed,b:next(r['horizon'] for r in pb if int(r['n'])==n and int(r['closed'])==closed and int(r['budget'])==b)
    getD=lambda b:next(r['first_high_duration'] for r in thresholds if int(r['n'])==n and int(r['budget'])==b and float(r['kappa_per_service'])==.0025)
    trip=lambda fn:' / '.join(fn(b) for b in [1,2,n])
    budget_table.append(f'{n} & {trip(lambda b:getpb(0,b))} & {trip(lambda b:getpb(1,b))} & {trip(getD)}'+r' \\')
for c in ['myopic','MPC3','MPC5','MPC8','RAR8','MPC64','RAR-A64']:
    means=[facts['primary'][str(n)][c]['mean_gap_pct'] for n in [3,4,5]]
    maxima=[facts['primary'][str(n)][c]['max_gap_pct'] for n in [3,4,5]]
    gap_table.append(c+' & '+' & '.join(num(x,5) for x in means)+' & '+' & '.join(num(x,3) for x in maxima)+r' \\')
for c in ['myopic','MPC8','RAR8','MPC64','RAR-A64']:
    rs=[facts['map'][str(n)][c] for n in [3,4,5]]
    map_table.append(c+' & '+str(sum(r['harmful'] for r in rs))+' & '+str(sum(r['missed_all_gain'] for r in rs))+' & '+str(sum(r['matches_offline'] for r in rs))+r' \\')

pulse_table=[]
for n,c in [(3,'myopic'),(3,'offline'),(4,'myopic'),(4,'offline'),(5,'myopic'),(5,'MPC64')]:
    r=wr(n,'pulse',c)
    pulse_table.append(f'{n} & {c} & '+ ' & '.join(num(r[k],6) for k in ['operating_cost','switching_cost','total_cost','saving_vs_myopic'])+r' \\')
service_table=[]
for w in facts['witnesses']:
    for r in params:
        if r['id']!=w['id']:continue
        service_table.append(f"{r['n']} & {r['service']} & "+' & '.join(num(r[k],4) for k in ['b','compute','eta','slo','p_R','p_M','p_C'])+r' \\')

source=r'''\documentclass[10pt,a4paper]{article}
\usepackage[T1]{fontenc}\usepackage[utf8]{inputenc}\usepackage{lmodern,microtype}
\usepackage[left=19mm,right=19mm,top=18mm,bottom=18mm,headheight=14pt]{geometry}
\usepackage{amsmath,amssymb,booktabs,array,enumitem,graphicx,xcolor,fancyhdr,float}
\usepackage[hidelinks,pdftitle={M1: Heterogeneous Three-to-Five-Service Experiments}]{hyperref}
\definecolor{inkblue}{HTML}{183B56}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small\color{inkblue}Communication--compute orchestration}
\fancyhead[R]{\small M1 experiments / v0.3}\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{.35pt}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\renewcommand{\arraystretch}{1.13}\setlength{\tabcolsep}{5pt}
\setlength{\abovedisplayskip}{5pt}\setlength{\belowdisplayskip}{5pt}
\setlist[itemize]{leftmargin=*,itemsep=3pt,topsep=3pt}
\setlist[enumerate]{leftmargin=*,itemsep=3pt,topsep=3pt}
\newcommand{\C}{\mathcal C}\newcommand{\ind}{\mathbf1}
\begin{document}
\begin{center}
{\small\color{inkblue}KURUC G\'ABOR PhD RESEARCH PROJECT \hfill 17 October 2026}\par\vspace{7pt}
{\LARGE\bfseries\color{inkblue}M1: Heterogeneous Service Experiments}\par\vspace{4pt}
{\large Exact finite-state control for $n=3,4,5$ services}
\end{center}

\textbf{Completed result.} The existing M1 framework has been generalized to 27, 81 and 243
placements, preserving the physical equations, reconfiguration rules, emergency override and
free final placement. The study evaluates 72 balanced heterogeneous populations, 432 common
controller traces, and 7,692 new controller runs. A further 108 runs reproduce the original
two-service costs \emph{and complete placement sequences}.

\textbf{What generalizes.} A strict RAN--MEC--RAN reversal appears in 55/72 populations on
the sampled static envelope. A strict myopic trap inherited from a lower-headroom static
optimum occurs in 70/72 populations on the specified headroom-pair grid. Selected examples
require three or four single-service moves before \emph{any} lower operating-cost placement
can be reached. These are substantial, interacting services, rather than negligible additions
to the original two-service construction.

\textbf{What the controllers show.} Lookahead materially reduces myopic cost in this finite
test suite. Ordinary MPC64 matches offline DP on all 432 primary traces. Return-aware rollout
(RAR) never exceeds its myopic baseline in the 1,518 measured RAR runs, but short return
windows are conservative and can miss gains that ordinary MPC captures. On a selected
five-service pulse, MPC64 makes a losing exchange while RAR-A64 avoids it. The evidence supports
operating-range characterization, not uniform RAR superiority or a new literature novelty claim.

\section{The physical M0/M1 model is preserved}
Each service is placed once at RAN ($R$), MEC ($M$), or Core ($C$) along the fixed two-link
route. All services traverse both links, carrying transformed output after processing. For
placement $p\in\{R,M,C\}^n$, tier load $q_k=\sum_{i:p_i=k}c_i$ and link loads are
\[
 L_1=\sum_i b_i\bigl(\eta_i\ind_{p_i=R}+\ind_{p_i\ne R}\bigr),\quad
 L_2=\sum_i b_i\bigl(\eta_i\ind_{p_i\ne C}+\ind_{p_i=C}\bigr).
\]
With $h=(H_R(t),60,120)$, latency and operating objective remain
\[
 D_i(p,H)=r_i+\sum_{e=1}^2\left(\delta_e+a_e\frac{L_e}{B_e-L_e}\right)
       +p^0_{i,p_i}\frac{h_{p_i}}{h_{p_i}-q_{p_i}},\qquad
 J_p(H)=\max_i D_i(p,H)/\tau_i.
\]
Bandwidths $(B_1,B_2)=(2.4,1.8)$, base delays $(1,2)$, coefficients $(0.5,0.8)$ and radio
delay $r_i=2$ are unchanged. Physical feasibility requires $L_e<B_e$ and $q_k<h_k$ at every
occupied tier. Empty RAN is allowed at $H=0$. Stress $J>1$ is recorded, not forbidden.

Per-slot cost is $J_p(H_t)+\sum_i\kappa_i\ind_{s_i\ne p_i}$. Normally at most $m$ services
move per slot. Only when \emph{no} normal feasible action exists, minimum-move feasible repairs
are admitted; they pay ordinary migration cost. Each intermediate placement incurs a full
slot of stress. All actual traces have zero terminal value and a free final placement.
Slots and migration weights are dimensionless; there is no new transient or workload model.

\newpage
\section{Experimental protocol and comparable populations}
\textbf{Fixed totals, heterogeneous shares.} Every population has $\sum b_i=1.7$ and
$\sum c_i=30$, the original aggregate demands. Tier/link capacities stay fixed. Both resource
shares use $w_i=0.5/n+0.5z_i/\sum_jz_j$, separately for traffic and compute, followed by
$10^{-4}$ rounding with total correction. Thus every service has at least approximately half
an equal share of both demands. Observed minima are reported below; even the smallest
five-service compute share is 11.80\%.

\begin{center}\small
\begin{tabular}{rrrrrl}\toprule
$n$ & States & Populations & R--M--R & Inherited strict trap & Min. shares: $b$ / $c$ (\%)\\\midrule
@@POPULATION_TABLE@@
\bottomrule\end{tabular}
\end{center}

Half the populations independently sample compression, compute/traffic shares, nominal
delays and SLOs. The other half sample a heterogeneous compression--compute trade-off inspired
by the original witness, with independent perturbations. No population is dropped based on
its result. Seeds are $104729+1000n+\mathrm{replicate}$; the full generation law and every
service parameter are included in code and CSV. The discovery examples on later pages are
selected \emph{after} this ensemble scan and do not define the frequency denominator.

\textbf{Primary traces.} Each population runs all six traces below with the same inputs for
all controllers. Initial placement is a static optimum at the first headroom sample.
\begin{center}\small
\begin{tabular}{p{30mm}rp{112mm}}\toprule
Trace & Slots & Headroom construction\\\midrule
Pulse & 64 & $20^{16},80^{12},20^{36}$\\
Exchange ramp & 128 & 64 linear samples $10\to120$, then 64 back to 10\\
Oscillation & 128 & $40+30\sin[2\pi(t-8)/32]$, $t=0,\ldots,127$\\
All-phase ramp & 128 & 64 geometric samples $5\to400$, then 64 back to 5\\
Withdrawal & 64 & $400^{16},10^8,100^{16},0^8,400^{16}$\\
Seeded blocks & 128 & Headrooms from $\{0,5,10,15,20,30,40,60,80,100,200,400\}$;
blocks of 2--10 slots, seed increased by 900000\\\bottomrule
\end{tabular}\end{center}
Superscripts denote repetitions. This spans both the exchange region and broader capacity
changes. It is a synthetic parameter study, not a measured telecom workload distribution.

For $m=1$, controllers are myopic, MPC3/5/8/16/64, RAR8, adaptive RAR-A64 and offline DP.
All have $\kappa_i=0.0025$ per moved service, so a coordinated $d$-service change costs
$0.0025d$. At $m=2,n$, myopic and offline are repeated on all 432 traces to isolate the
migration budget. That gives $432(9+2+2)=5616$ primary runs. Targeted pulse maps contribute
1,980 runs and detailed examples contribute 96. Local robustness uses 150 additional parameter
probes. Counts are evaluations, not independent real-world samples.

\textbf{Information and exactness.} MPC$K$ and RAR$K$ use the same maximum $K$-slot exact
headroom preview, including the current slot. RAR-A64 tries $3,5,8,16,32,64$ and stops at
the first improving complete plan. The true trace end is known. Offline has the entire trace.
DP enumerates every physical placement and admissible edge; sparse storage only omits
forbidden edges. Sweeps use float64, ties within $10^{-12}$ and improvement tolerance
$10^{-11}$. Selected payback thresholds and static examples have independent Fraction checks.

\newpage
\section{The M0/M1 mechanisms survive genuine multi-service competition}
The static envelope is sampled at $H=0$ and 481 geometric values from 2 to 400. A reversal
requires three increasing headrooms with the same service at $R,M,R$, each with a unique
global optimum separated from the runner-up by more than $10^{-8}$. The resulting population
counts are 23/32, 18/24 and 14/16 for $n=3,4,5$. This is numerical envelope coverage, not an
analytical enumeration of every phase boundary.

\begin{figure}[H]\centering
\includegraphics[width=\linewidth]{figures/fig01_static_nonmonotonicity.pdf}
\caption{Representative static envelopes, selected for a visible strict gap. An asterisk
marks a service with an R--M--R reversal. Dotted headrooms are independently checked with
rational arithmetic: the winning whole placement is strictly unique at all nine marked
points. Different service populations and the fixed aggregate demands produce the reversals.}
\end{figure}

The effect is present in both generation families. For independent populations the reversal
counts are $9/16$, $6/12$, $6/8$; for the coupled family they are $14/16$, $12/12$, $8/8$.
The latter family intentionally concentrates on the compression--compute trade-off, so these
ratios must not be interpreted as operational prevalence.

\textbf{Strict operating-cost trap.} At fixed $H$, an inherited feasible placement $s$ is
called a strict trap when some placement has $J_p<J_s$ but \emph{every} feasible one-service
neighbor has $J_p>J_s$. Any nonnegative migration penalty then leaves the myopic controller
at $s$ indefinitely, including the zero-penalty case. This distinguishes a physical exchange
barrier from a switch blocked only by its penalty or an exactly flat minimax plateau.

The all-state scan uses 12 headrooms between 20 and 300; the full list is in
\texttt{config.json}. It records strict, flat and penalty-only traps separately. For
inherited traps, low headrooms are 10, 15, 20, 25, 30, 40, 50 and 60. High headrooms are
20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120 and 150, retaining only strict increases.
Starting at a static optimum for the low value, a strict trap is found in 32/32, 22/24 and
16/16 populations. Maximum all-state escape distances are 3, 4 and 4 moves, respectively;
the inherited examples next have distances 3, 3 and 4.

\newpage
\section{Longer exchanges and the price of a complete return}
Let $d_{\rm esc}$ be the fewest feasible single-service moves required to reach \emph{any}
placement with lower operating cost than the initial state. It is a spatial graph distance.
The first profitable horizon $K_{\rm out}$ instead minimizes total operating plus migration
cost, against staying, with a free endpoint. $K_{\rm closed}$ prices the same constant-$H$
window but requires the initial placement at its end, including that final slot and migration.
This return constraint is a diagnostic and controller-window rule, not a change to the
actual free-terminal M1 problem.

\begin{center}\small
\begin{tabular}{llrrrrr}\toprule
Case & Initial & $H_{\rm low}$ & $H$ & $d_{\rm esc}$ & $K_{\rm out}$ & $K_{\rm closed}$\\\midrule
$n=2$ reference & MR & 60 & 100 & 2 & 3 & 6\\
$n=3$: n3\_21 & RMC & 20 & 50 & 3 & 4 & 8\\
$n=4$: n4\_11 & RCMR & 40 & 70 & 3 & 12 & 25\\
$n=5$: n5\_14 & MCCMR & 10 & 30 & 4 & 64 & 129\\\bottomrule
\end{tabular}\end{center}
All three new $m=1$ payback pairs are certified by a separate all-state rational DP: every
earlier horizon has zero gain over staying; the listed first horizon has a strictly positive
exact rational gain. Full numerators/denominators are archived. These examples were selected
by maximum inherited escape distance, then number of services in the first profitable plan,
then operating gap. They illustrate mechanisms and do not imply growth monotonic in $n$.

\begin{figure}[H]\centering
\includegraphics[width=\linewidth]{figures/fig02_exchange_geometry.pdf}
\caption{Operating cost along the migration actions in the first profitable constant-$H$
plan. Repeated dwell slots are omitted from the horizontal axis. Temporary worsening can
extend across several migrations; elapsed payback includes dwell time and all move penalties.}
\end{figure}

\textbf{Four-service obstruction in the five-service population.} At $H=30$,
$J_{MCCMR}=0.524661793$, while $J_{RMMCR}=0.524003655$. Exact rational comparison over all
243 placements gives the following minima at each Hamming distance from MCCMR:
\begin{center}\small
\begin{tabular}{rllr}\toprule
Distance & Best placement at distance & Minimum $J$ & Difference from initial\\\midrule
1 & MCCCR & 0.529733676 & $+0.005071883$\\
2 & RMCMR & 0.525597434 & $+0.000935641$\\
3 & RMMMR & 0.536651860 & $+0.011990067$\\
4 & RMMCR & 0.524003655 & $-0.000658138$\\\bottomrule
\end{tabular}\end{center}
Thus no lower-cost state exists within three moves, even with zero migration penalty.
The profitable path changes four distinct services. In the four-service case, a cheaper
state exists after three moves, but the first total-cost-optimal profitable plan changes
all four services. Spatial distance, number of moves, and payback time are distinct measures.

\newpage
\section{Primary controller comparison: 432 matched traces}
The table reports the arithmetic mean of per-trace percentages
$100(\C_{\rm policy}-\C_{\rm offline})/\C_{\rm offline}$ for $m=1$, separately for each $n$.
These percentages are not ratios of pooled sums. Trace counts are 192, 144 and 96.
\begin{center}\small
\begin{tabular}{lrrrrrr}\toprule
& \multicolumn{3}{c}{Mean gap to offline (\%)} & \multicolumn{3}{c}{Maximum gap (\%)}\\
Controller & $n=3$ & $n=4$ & $n=5$ & $n=3$ & $n=4$ & $n=5$\\\midrule
@@GAP_TABLE@@
\bottomrule\end{tabular}\end{center}

MPC64 equals the offline value to $10^{-9}$ absolute total cost in all 432 primary cases.
RAR-A64 matches it in 428/432 cases. This is an outcome of these finite traces, not a bound
on the preview needed in other instances. Myopic is strictly suboptimal in 380/432 cases.
Mean myopic gaps are 1.452\%, 0.689\% and 1.642\%; the heterogeneous populations do not support
a monotone dependence on service count.

\textbf{Matched short preview matters.} RAR8 beats MPC8 in 18 cases, ties in 198, and loses
in 216. MPC8 exceeds myopic total cost in four primary cases; RAR8 does so in none. Return
awareness trades some opportunities for a completed-plan safeguard. It is not uniformly
better than ordinary MPC at equal preview.

\textbf{Operating stress and migration are separated.} The table below gives mean sums per
trace, retaining dimensionless slot cost. Violation counts sum slots with $J>1$ over the
entire primary set at the given $n$; they are not hard feasibility failures.
\begin{center}\small
\begin{tabular}{rlrrr}\toprule
$n$ & Controller & Mean $\sum J$ & Mean migration cost & $J>1$ slots\\\midrule
@@COST_TABLE@@
\bottomrule\end{tabular}\end{center}

There are 46,080 slots per controller across the 432 primary traces. Myopic accumulates 50
violation slots; MPC3/5/8/16/64, RAR8, RAR-A64 and offline have zero in this primary suite.
This empirical result does not turn the total-cost RAR bound into a separate SLO guarantee.
Migration cost is often higher for lookahead policies because useful repositioning is paid
explicitly. Overrides are also recorded separately in the raw summaries.

The largest primary saving over myopic is 28.313\% for offline on n5\_09's seeded block
trace. It includes abrupt capacity changes and anticipation of future stress. It must not be
attributed solely to exchange barriers. The selected constant-headroom exchange examples
save 3.720\%, 0.617\% and 0.094\% over myopic during a 256-slot plateau; the four-move example
demonstrates a horizon obstruction, not a large percentage gain.

\newpage
\section{Same-trace trajectories: profitable and losing excursions}
For each selected population, use 64 low-headroom slots, a high-headroom pulse, then 64 low
slots. High durations here are 12, 24 and 96. All departure, intermediate, dwell and return
costs are included, as are any prepositioning actions before the pulse.
\begin{figure}[H]\centering
\includegraphics[width=\linewidth]{figures/fig03_pulse_trajectories.pdf}
\caption{Every curve uses the same headroom trace within its panel. A negative final
difference means lower total cost than myopic. Coincident curves overlap. In the five-service
case MPC64 temporarily benefits during the pulse but finishes worse after return.}
\end{figure}

\begin{center}\small
\begin{tabular}{rlrrrr}\toprule
$n$ & Controller & $\sum J$ & Migration & Total & Net saving vs myopic\\\midrule
@@PULSE_TABLE@@
\bottomrule\end{tabular}\end{center}
In the three-service pulse, the displayed offline value is also attained by MPC8, RAR8,
MPC64 and RAR-A64. In the four-service pulse, MPC8/RAR8 stay with myopic; MPC64/RAR-A64 attain
offline. In the five-service pulse, staying is offline optimal and both RAR policies stay.
MPC64's eight service moves cost 0.020000; its operating sum is also 0.000550 higher, giving
a total loss of 0.020550. Seeing a profitable one-way exchange is insufficient to price the
eventual return when the pulse end is outside the current preview.

Complete placement sequences for every primary run are in the RLE trajectory archive, and
the detailed examples include per-slot placement, per-service stress, move cost and emergency
flags in CSV. Here and throughout, offline is the exact \emph{finite-trace} optimum with full
preview, while online controller sequences are generated by their respective information rule.

\newpage
\section{When is myopic sufficient, and when is more preview useful?}
The maps use the three discovered examples, $m=1$, six per-service migration weights and
15 pulse durations. Each episode has 64 low slots before and after the pulse. Grey means
myopic already attains the offline total; coloured cells show the fraction of offline gain
recovered by RAR. This is a conditional mechanism map, not a population-frequency estimate.
\begin{figure}[H]\centering
\includegraphics[width=.98\linewidth]{figures/fig04_return_parameter_map.pdf}
\caption{Return-aware operating ranges. Blue is full recovery; pale yellow is a missed
profitable excursion. Red crosses in the left column mark losing MPC8 excursions. All
15 duration categories are present, with a subset of ticks labelled. κ is the cost of one
moved service, not the cost of a whole exchange. The actual final placement remains free.}
\end{figure}

\newpage
\section{Pulse thresholds, migration coordination and the preview cap}
Of the 270 $m=1$ map cases, offline improves on myopic in 94; in 176 cases myopic is sufficient
for the specified episode. At the chosen three high headrooms, those profitable counts are
60/90, 31/90 and 3/90. A larger $n$ or a longer escape path alone does not imply a larger
or more frequent gain.
\begin{center}\small
\begin{tabular}{lrrr}\toprule
Controller & Worse than myopic & Misses all profitable gain & Equals offline / 270\\\midrule
@@MAP_TABLE@@
\bottomrule\end{tabular}\end{center}
``Misses all'' is counted only among the 94 profitable cases, and includes any losing
attempt. MPC64 loses on six five-service pulses despite matching offline in every primary
trace. RAR-A64 is harmless here but misses six profitable excursions: three four-service
cases and all three profitable five-service cases. Equal counts of offline matches do not
mean the controllers win on the same cases.

\textbf{How long must favourable headroom last?} In addition to the sparse duration map,
every integer pulse duration is checked in ascending order until first gain (cap 512).
The table distinguishes constant-$H$ diagnostics from actual low--high--low episodes.
Each cell lists budgets $m=1\,/\,2\,/\,n$; all use $\kappa_i=0.0025$.
\begin{center}\small
\begin{tabular}{rccc}\toprule
$n$ & Constant $K_{\rm out}$ & Constant $K_{\rm closed}$ & First profitable high duration $D$\\\midrule
@@BUDGET_TABLE@@
\bottomrule\end{tabular}\end{center}
The $m=1$ constant thresholds have exact rational certificates. Other entries use full
float64 DP. Pulse thresholds include prepositioning in the low prefix and repair/return in
the low suffix, so they must not be substituted for $K_{\rm closed}$. At $m=1$, actual pulse
durations are 5, 22 and 128. In the first two examples an optimal plan begins one move before
the pulse; in the last it waits for the high interval. No favourable duration was omitted
below these thresholds.

Increasing the budget reduces bridge cost and travel time. It does not necessarily eliminate
trapping: two simultaneous moves still cannot reach any better operating state in the
five-service witness. With all five moves allowed, a direct four-service change remains worth
doing only after 16 constant-high slots because its operating advantage is small. On all 432
primary traces, offline costs are verified nonincreasing as $m$ increases from 1 to 2 to $n$.

\textbf{A 64-slot return window can be too short.} At constant $H=30$ over 256 slots,
MPC64 and offline save 0.126618 relative to myopic. RAR-A64 saves only 0.000255: its first
accepted deviation occurs at slot 193, when the window reaches the true free terminal.
Its pre-terminal return window cannot cover the 129-slot closed payback. RAR129 begins at
slot 1 and attains offline, as does matched-preview MPC129. This is a diagnostic cap selected
from the discovered witness, not an automatic universal tuning rule. The retained complete
plan and its return price are unchanged from the earlier RAR construction.

\newpage
\section{Robustness, limits and the defensible research statement}
Around each discovered witness, 50 unfiltered probes perturb service traffic, compute,
compression, nominal delays and SLOs multiplicatively by up to $\pm2\%$. Aggregate traffic
and compute are renormalized to 1.7 and 30. Low/high headrooms stay fixed; the low-headroom
static optimum is recomputed. Thus this is robustness of the local mechanism, including
possible changes in the inherited initial state, rather than a test that freezes that state.
\begin{center}\small
\begin{tabular}{rrrrr}\toprule
$n$ & Strict trap & Escape $\ge3$ moves & Escape 4 moves & Positive $K_{\rm out}$ range\\\midrule
@@ROBUST_TABLE@@
\bottomrule\end{tabular}\end{center}
The four-move obstruction persists in 11/50 probes around the five-service witness, while
strict trapping persists in 25/50. Some probes admit easier switches. Five four-service
probes also have four-move escape distance. This supports a non-isolated mechanism but does
not show uniform parameter robustness or stability of a particular payback threshold.

\textbf{Return-aware bound and its scope.} RAR uses a shadow myopic trajectory, retains an
unexecuted incumbent, and accepts a cheaper replacement only when its window covers that
incumbent and rejoins the same reference endpoint. At the true end, the endpoint is free.
The earlier finite-state argument is independent of service count:
\[
 \C_{\rm offline}\le\C_{\rm RAR}\le\C_{\rm myopic},\qquad
 \C_{\rm myopic}-\C_{\rm RAR}=\sum_t\delta_t.
\]
It assumes a feasible baseline and correct forecasts within every queried window. The
largest ledger residual over 1,518 RAR runs is $1.55\times10^{-12}$. It does not guarantee
fewer migrations, lower prefix cost, better individual SLOs, or dominance over matched MPC.
Forecast errors are not part of this study.

\textbf{Supported contribution candidate.} In the unchanged communication--compute placement
model, substantial heterogeneous services can create strict barriers involving three or four
service changes. Complete-return payback can be much longer than the path itself. Exact
enumeration identifies when ordinary short MPC fails, when completed-return control avoids
a losing excursion, and when its own finite preview is too conservative. The added value is
a reproducible engineering characterization beyond a dummy-service embedding of $n=2$.
This is computational validation of these instances and controller ranges; literature novelty
and a general law of exchange length versus $n$ remain open.

\textbf{Limits that affect interpretation.} The 72 populations are bounded synthetic ensembles,
with the same aggregate loads and original resource regime; they do not cover all possible
service distributions. MEC/Core remain physically feasible because their capacities exceed
the total compute demand, while their shared compute delays still interact. Link loads stay
below capacity in this ensemble. Only RAN headroom varies. Static frequency counts depend on
the sample grid and generation families. The finite horizon, ideal previews and additive
instantaneous migration costs are inherited M1 assumptions. Exponential state growth is
still present; 243 states are not a scalability claim for large service populations.

The appropriate paper-level next step is to frame these measured operating ranges and the
certified multi-service witnesses, keeping the return-aware safeguard distinct from cost
optimality at equal preview. Predictive robustness would require a separate experiment.

\newpage
\section{Reproduction, verification and reference parameters}
\textbf{Independent checks.} Thirteen unit/regression tests pass, including scalar--vector
physics equality over all placements, strict subset-capacity boundaries, dense versus sparse
DP, three-service exhaustive paths, Fraction DP, emergency repair, forecast-prefix invariance
and the four-move witness. Another 108 legacy controller runs match original costs and full
placement paths. The exported archive is decoded independently of the controllers and checks
5,616 trajectories and 599,040 slots, including every ordinary/emergency edge. Its maximum
cost reconstruction error is $2.28\times10^{-13}$.

\textbf{Re-run from the extracted project directory.} Python, NumPy and Matplotlib suffice
for experiments; PDF generation additionally uses pdfLaTeX. Package versions are pinned and
runtime details are recorded. Full run commands are:
\begin{verbatim}
python3 -m unittest discover -s tests -v
python3 run_experiments.py
python3 local_robustness.py
python3 pulse_thresholds.py
python3 analyze_results.py
python3 validate_archive.py
python3 create_figures.py
python3 create_report.py
pdflatex M1_Multiservice_Experiments.tex
\end{verbatim}
Run pdfLaTeX again for references. The runner also supports section-by-section execution.
Controller timing columns describe this run and are not hardware-normalized benchmarks.

\textbf{The three discovered populations.} Service order in every placement string follows
the rows below. Fixed $r_i=2$ and $\kappa_i=0.0025$ apply to all. The other 69 populations and
their seeds are in the same parameter CSV.
\begin{center}\small
\begin{tabular}{rrrrrrrrr}\toprule
$n$ & $i$ & $b_i$ & $c_i$ & $\eta_i$ & $\tau_i$ & $p^0_R$ & $p^0_M$ & $p^0_C$\\\midrule
@@SERVICE_TABLE@@
\bottomrule\end{tabular}\end{center}

\textbf{Audit trail.} The package contains source code, all measured summaries, static/trap
tables, every primary trace, RLE placement trajectories, detailed per-service witness stress,
plan ledgers, rational certificates, source report files and vector/raster figures. A manifest
records hashes of the delivered files. The readable Hungarian findings summarize these same
measurements.

\textbf{Model sources retained in the package.} [1] Working Technical Note M0, v1.0,
13 October 2026, supplied communication--compute note. [2] M1: Minimal Dynamic Model and
Research Questions, supplied original technical source. [3] M1: Return-Aware Rollout Controller,
v0.2, earlier completed experimental report. The original two-service implementations and
reference trace/results CSV are retained unmodified for regression; the new generalized code
is a separate release. No additional topology, service chain or AI-RAN workload was introduced.
\end{document}
'''

replacements={'POPULATION_TABLE':population_table,'GAP_TABLE':gap_table,'COST_TABLE':cost_table,
              'PULSE_TABLE':pulse_table,'MAP_TABLE':map_table,'BUDGET_TABLE':budget_table,
              'ROBUST_TABLE':robust_table,'SERVICE_TABLE':service_table}
for key,value in replacements.items():source=source.replace('@@'+key+'@@','\n'.join(value))
# pdfLaTeX-compatible symbol in text, kept out of the numerical calculation.
source=source.replace('κ',r'$\kappa$')
(ROOT/'M1_Multiservice_Experiments.tex').write_text(source)

hu='''# M1 – heterogén, 3–5 szolgáltatásos kísérletek

**Elkészült vizsgálat, v0.3 – 2026. október 17.**

A meglévő M1 keretrendszer 27, 81 és 243 placementre általánosítva fut. A topológia,
a két link késleltetési modellje, a minimax SLO-stressz, a migrációs költség,
a migrációs keret és az emergency override szabálya változatlan. A teljes idősor
végén továbbra is szabad a végső placement, nulla terminális költséggel.

72 heterogén konfigurációt és 432 közös trace-t vizsgáltam. A teljes forgalmi igény
mindenütt 1,7, a compute-igény 30; a kapacitások az eredetiek. Egyetlen új szolgáltatás
sem elhanyagolható: az n=5 populációkban a legkisebb tényleges forgalmi részesedés
12,91%, a legkisebb compute-részesedés 11,80%. Az eredmények 7692 új vezérlőfutásból
származnak; további 108 n=2 regresszió a teljes korábbi placement-sorozatot is reprodukálta.

## Mi általánosult?

| Szolgáltatások | Populációk | RAN→MEC→RAN visszafordulás | Alacsonyabb headroom optimumából örökölt szigorú csereakadály |
|---|---:|---:|---:|
| 3 | 32 | 23/32 | 32/32 |
| 4 | 24 | 18/24 | 22/24 |
| 5 | 16 | 14/16 | 16/16 |

A visszafordulásnál mindhárom mintapontban szigorúan egyedi globális optimumot kértem.
A csereakadálynál minden egyszolgáltatásos szomszéd működési költsége nagyobb, miközben
létezik olcsóbb távoli placement. Ezért a beragadás nulla migrációs költségnél is fennáll.
A fenti arányok a rögzített, szintetikus populációhalmazra és headroomrácsra vonatkoznak;
nem valós workloadok gyakorisági becslései.

## Hosszabb cserék és a teljes visszatérés ára

Az alábbi három példát az állapottér-vizsgálat után, szemléltetésre választottam ki.
A költség szolgáltatásonként és áthelyezésenként 0,0025, a migrációs keret m=1.

| Példa | Kezdeti placement | Magas H | Legkevesebb lépés bármely jobb működési állapotig | Első megtérülő egyirányú horizont | Első megtérülő zárt, visszatérő horizont | Első megtérülő magas-H impulzus |
|---|---|---:|---:|---:|---:|---:|
| n3_21 | RMC | 50 | 3 | 4 | 8 | 5 |
| n4_11 | RCMR | 70 | 3 | 12 | 25 | 22 |
| n5_14 | MCCMR | 30 | 4 | 64 | 129 | 128 |

Az egyirányú és zárt horizontok állandó magas headroomra vonatkoznak; első szigorúan
nyereséges értéküket független, egzakt racionális DP is igazolja. Az impulzusok előtt és után
64 alacsony-H slot van, ezért ott az előkészítés és visszatérés más headroomnál történhet.
Az impulzushosszt minden egész értéken végigvizsgáltam az első nyereségig.

Az n=5 példa útvonala:

`MCCMR → RCCMR → RMCMR → RMMMR → RMMCR`.

Négy különböző szolgáltatás mozog. A kezdeti állapottól 1, 2 vagy 3 szolgáltatásnyi
távolságban egyetlen placement működési költsége sem jobb. A négyservice-es példában
három lépés után már létezik jobb állapot, de az első megtérülő optimális terv négy
szolgáltatást mozgat. Az úthossz és a megtérülési idő külön mennyiség.

## Vezérlők azonos trace-en és azonos előretekintési kerettel

Az alábbi átlag a trace-enként számolt, offline optimumhoz viszonyított költségtöbblet:

| Vezérlő | n=3 | n=4 | n=5 |
|---|---:|---:|---:|
'''
for c in ['myopic','MPC3','MPC8','RAR8','MPC64','RAR-A64']:
    hu+='| '+c+' | '+' | '.join(num(facts['primary'][str(n)][c]['mean_gap_pct'],5)+'%' for n in [3,4,5])+' |\n'
hu+='''
Az MPC64 mind a 432 fő trace-en elérte az offline költséget, a RAR-A64 428 esetben.
Ez az adott teszthalmaz eredménye, nem általános horizontkorlát. Azonos 8 lépéses
előretekintésnél a RAR8 az MPC8-nál 18 esetben jobb, 198-ban azonos, 216-ban rosszabb.
A return-aware vezérlés fő előnye itt az alapmegoldáshoz viszonyított összköltség
védelme: mind az 1518 RAR-futásban teljesült, legfeljebb 1,55×10⁻¹² ledgerhibával.
Rövid horizonton ennek ára kihagyott nyereség; nincs általános RAR-fölény az MPC-vel szemben.

A fő tesztekben a myopic összesen 50 SLO-sértő slotot adott 46 080 vizsgált slotból;
a felsorolt előretekintő vezérlők és az offline 0-t. Ez megfigyelés, nem külön SLO-garancia.
A tárolt eredmények az összegzett SLO-stresszt, a migrációs költséget, a migrációk és
override-ok számát külön tartalmazzák.

Az n=5 példában a 96 slot hosszú magas-H impulzuson az MPC64 nyolc áthelyezéssel
0,020550 többletköltséget termelt: 0,020000 migráció és 0,000550 működési többlet.
A myopic, a RAR és az offline itt helyben marad. Állandó magas H mellett ugyanakkor
az MPC64 már hasznos: 256 sloton 0,09427%-ot takarít meg. A RAR64 a 129 slotos zárt
megtérülés miatt késlekedik; RAR129-cel a nyereség az első slottól elérhető.

## Paramétertérkép, koordináció, robusztusság

A három példán 270 m=1 impulzus/migrációs költség kombinációból 94-ben éri meg eltérni
a myopictól. RAR8 61 ilyen eset összes nyereségét kihagyja, RAR-A64 hatét. Az MPC64
hat esetben a myopicnál rosszabb impulzusváltást hajt végre. A térkép jelöli, mikor
elegendő a myopic/hiszterézises működés, mikor segít a hosszabb előretekintés és mikor
marad a return-aware horizont is túl rövid. Ez három kiválasztott mechanizmus térképe.

A koordinált migráció csökkenti az akadályt. Az n=5 példa egyirányú megtérülése
m=1/2/5 esetén 64/18/16 slot, zárt megtérülése 129/37/32 slot. Két egyidejű migráció
tehát még nem szünteti meg a csereakadályt. A teljes koordináció mellett is meg kell
fizetni a migrációt, ezért a kis működési előny hosszabb fennmaradást kívánhat.

A kiválasztott példák körüli 50–50, ±2%-os lokális paraméterpróbából 48, 33 és 25
esetben maradt meg szigorú beragadás. Az n=5 környezetében 11/50 esetben fennmaradt
a négylépéses akadály. A mechanizmus nem egyetlen pontos paraméterpontra szorul,
de a megtérülési küszöbök érzékenyek a populációra; nem állítható egyenletes robusztusság.

## Átadott eredmények és ellenőrzés

- Futtatható, általánosított Python-referenciamodell és az eredeti n=2 regressziós források.
- Az összes paraméter, trace, költségösszesítő és placement-sorozat; a fő útvonalak RLE/GZIP
  formátumban, a részletes példák per-service stresszel és RAR-tervnaplóval CSV-ben.
- Egzakt racionális küszöbbizonyítványok, statikus és exchange-ábrák, impulzustérkép.
- 13 sikeres ellenőrző teszt, 108 azonos n=2 regresszió és 5616 exportált pálya,
  összesen 599 040 slot független újraértékelése. Maximális exportált költségeltérés: 2,28×10⁻¹³.

**Kutatási értelmezés:** a nem elhanyagolható heterogén szolgáltatásokkal megmaradó,
több szolgáltatást érintő csereakadály és annak időhorizontigénye erősebb M1 mérnöki
alátámasztást ad a kétservice-es beágyazásnál. Az előny nagysága és a megfelelő vezérlő
paraméterfüggő. Ez reprodukálható numerikus igazolás az adott modellben, nem újdonsági
elsőbbség vagy általános optimalitási tétel az online vezérlőre. A headroom-előrejelzések
minden felhasznált ablakban tökéletesek; hibás előrejelzést és valódi AI-RAN workloadot
ez a vizsgálat nem modellezett.
'''
(ROOT/'RESULTS_HU.md').write_text(hu)
