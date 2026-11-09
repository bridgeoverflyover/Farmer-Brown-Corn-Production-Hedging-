import numpy as np
from math import log, sqrt, exp
from statistics import NormalDist; norm=NormalDist()
rng=np.random.default_rng(42)
N=20000; T=0.5; D=126
F0=4.50; vol=0.25
acres=500; mu_y=180; sd_y=18
p_dr=0.10; dr_cut=0.45; dr_jump=0.30
cost_acre=650; fixed_cost=acres*cost_acre
basis_mu=-0.35; basis_sd=0.12
rho=-0.30
cash=100000; distress=15000; init_m=0.25  # $/bu initial margin
otc_fee=0.04  # $/bu on hedged volume (credit line fee)
fut_comm=0.01
K=4.40; r=0.04
EQ=acres*mu_y*(1-p_dr*dr_cut)
def b76(F,K,s,T):
    d1=(log(F/K)+0.5*s*s*T)/(s*sqrt(T)); d2=d1-s*sqrt(T)
    return exp(-r*T)*(K*norm.cdf(-d2)-F*norm.cdf(-d1))
prem=b76(F0,K,vol,T)
# shocks
z1=rng.standard_normal(N); z2=rho*z1+sqrt(1-rho**2)*rng.standard_normal(N)
dr=rng.random(N)<p_dr
yld=np.clip(mu_y+sd_y*z1,100,None)*np.where(dr,1-dr_cut,1)
Q=acres*yld
# daily price paths; terminal correlated with -yield shock via z2 used as path endpoint driver
dt=T/D
eps=rng.standard_normal((N,D))
# force path sum to match z2 (Brownian bridge style): adjust
eps=eps-eps.mean(1,keepdims=True)+ (-z2/sqrt(D))[:,None]  # -z2: low yield -> high price
logp=np.cumsum(-0.5*vol**2*dt+vol*sqrt(dt)*eps,1)
# drought: price jump spreading in over summer (days 60-100)
ramp=np.clip((np.arange(D)-60)/40,0,1)
logp=logp+np.where(dr,log(1+dr_jump),0)[:,None]*ramp[None,:]
P=F0*np.exp(logp); P=P/P.mean(0,keepdims=True)*F0; FT=P[:,-1]
basis=basis_mu+basis_sd*rng.standard_normal(N)+np.where(dr,0.15,0)  # basis strengthens in drought
cashrev=Q*(FT+basis); prem=1.05*np.maximum(K-FT,0).mean()*exp(-r*T); print("fair put prem",round(prem,3))
def run(hf,hp,venue):
    hf_bu=hf*EQ; hp_bu=hp*EQ
    putpay=hp_bu*np.maximum(K-FT,0)-hp_bu*prem*exp(r*T)
    if venue=='OTC':
        futpnl=hf_bu*(F0-FT)-hf_bu*otc_fee
        forced=np.zeros(N,bool)
    else:
        # cumulative variation margin needed = hf_bu*(P-F0)+initial; forced liquidation if > cash
        need=hf_bu*(P-F0)+hf_bu*init_m
        breach=need>cash
        forced=breach.any(1)
        idx=np.where(forced,breach.argmax(1),D-1)
        Pexit=P[np.arange(N),idx]
        futpnl=hf_bu*(F0-Pexit)-hf_bu*fut_comm
    prof=cashrev+futpnl+putpay-fixed_cost-np.where(forced,distress,0) if venue=='EX' else cashrev+futpnl+putpay-fixed_cost
    return prof,forced
strats=[('Unhedged',0,0,'OTC'),('100% futures (exch)',1,0,'EX'),('100% futures (OTC)',1,0,'OTC'),
        ('70% futures (exch)',0.7,0,'EX'),('70% futures (OTC)',0.7,0,'OTC'),('80% puts',0,0.8,'OTC'),
        ('50% OTC fut + 30% puts',0.5,0.3,'OTC'),('50% exch fut + 30% puts',0.5,0.3,'EX')]
res={}
print(f"E[Q]={EQ:,.0f} bu, put prem={prem:.3f}, cost/bu={fixed_cost/EQ:.2f}")
for n,a,b,v in strats:
    p,f=run(a,b,v); q=np.quantile(p,0.05); cv=p[p<=q].mean()
    res[n]=p
    print(f"{n:28s} mean {p.mean()/1e3:7.1f}k sd {p.std()/1e3:6.1f}k P(loss) {np.mean(p<0):5.1%} VaR5 {q/1e3:7.1f}k CVaR5 {cv/1e3:7.1f}k forced {f.mean():5.1%}  drought-mean {p[dr].mean()/1e3:7.1f}k")
# frontier: futures ratio 0..1.2 with OTC, and puts overlay
print('frontier')
fr=[]
for h in np.arange(0,1.21,0.1):
    p,_=run(h,0,'OTC'); q=np.quantile(p,0.05); fr.append((round(h,1),p.mean(),p.std(),p[p<=q].mean()))
    print(round(h,1),round(p.mean()/1e3,1),round(p.std()/1e3,1),round(p[p<=q].mean()/1e3,1))

print('grid OTC: rows futures, cols puts -> CVaR5 / mean')
best=[]
for a in np.arange(0,0.81,0.1):
  line=[]
  for b in np.arange(0,0.81,0.1):
    if a+b>1.0001: line.append('   -   '); continue
    p,_=run(a,b,'OTC'); q=np.quantile(p,0.05); cv=p[p<=q].mean(); line.append(f"{cv/1e3:6.0f}/{p.mean()/1e3:3.0f}"); best.append((cv,a,b,p.mean(),p.std(),np.mean(p<0)))
  print(round(a,1),' '.join(line))
best.sort(reverse=True); print(best[:5])
import json
bins=np.arange(-250,451,25)
H={}
for n,a,b,v in [('Unhedged',0,0,'OTC'),('100% futures',1,0,'OTC'),('Recommended',0.3,0.4,'OTC')]:
    p,_=run(a,b,v); H[n]=np.histogram(np.clip(p/1e3,-249,449),bins)[0].tolist()
fr=[]
for h in np.arange(0,1.01,0.1):
    p,_=run(h,0,'OTC'); q=np.quantile(p,0.05); p2,_=run(h,0.4,'OTC') if h<=0.6 else (None,None)
    fr.append({'h':round(h,1),'cv':round(p[p<=q].mean()/1e3,1)})
json.dump({'bins':bins.tolist(),'H':H,'fr':fr},open('out.json','w'))
for v in ['EX','OTC']:
    for a,b in [(0.3,0.4),(0.7,0)]:
        p,f=run(a,b,v); q=np.quantile(p,0.05); print(v,a,b,'mean',round(p.mean()/1e3,1),'CVaR',round(p[p<=q].mean()/1e3,1),'forced',f.mean())
need=EQ*(P-F0).max(1)
print('max adverse $/bu pctiles',np.quantile((P-F0).max(1),[.5,.9,.95,.99]))
