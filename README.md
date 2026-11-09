# Farmer Brown – Corn Hedging Strategy

Monte Carlo analysis of a hedging strategy for an Illinois corn farmer, covering production, drought, basis and margin risk. Write-up: https://claude.ai/artifact/1sWsuveudkU52vWcTUWzrf

## Recommendation
Hedge about 80% of expected output (E[Q] = 85,950 bu):
- **Puts:** buy 10 December $4.40 puts (about 60% of expected output).
- **Futures:** sell 3 December futures on the exchange (about 20%).

Compared with no hedge, profit SD falls from $92k to $74k. The average loss in a price crash falls from $87k to $15k. In a drought year the hedge costs about $35k, against about $105k for a 100% futures hedge. At a 20% futures hedge, exchange margin calls never exceeded the $100k cash reserve in the simulation, so the OTC credit line isn't worth its fee.

## Files
- `hedge_sim.py`: the simulation. It runs 20,000 paths of 126 trading days each and compares hedging strategies, exchange futures vs OTC, and a grid of futures/put mixes. Run it with `python3 hedge_sim.py`; it needs `numpy`.
- `data/il_pdsi_jul.csv`, `data/il_pdsi_aug.csv`: Illinois Palmer Drought Index for July and August, 1895–2026, from NOAA NCEI.
- `data/il_dsci.json`: Illinois weekly Drought Severity and Coverage Index (DSCI), 2000–2026, from the US Drought Monitor.

## Drought estimate (Illinois)
- **Definition:** a drought year has an average July–August PDSI of −2 or lower.
- **Frequency:** 8 of 76 years from 1950 to 2025, about 10%. The drought years are 1953, 1954, 1963, 1964, 1988, 1991, 2005 and 2012.
- **DSCI check:** the July–August average peaks in 2012 (342), 2005 (261) and 2023 (147).
- **Correlation:** DSCI and PDSI move together closely (−0.77).

## Still to do
- Download Illinois corn yields from NASS Quick Stats.
- Remove the long-term upward trend and estimate the yield loss in drought years. The model currently assumes a 45% cut.
- Fit yield loss against DSCI, then rerun the simulation with the estimates.
