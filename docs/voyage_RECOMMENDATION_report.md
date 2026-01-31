# Voyage Recommendation Report
## Cargill Ocean Transportation - Datathon 2026

**Prepared for:** Freight Trading Manager
**Date:** January 2026
**Authors:** Sidarth Rajesh & Makendra Prasad

---

## Executive Summary

This report presents our optimized vessel-cargo allocation strategy for Cargill's Capesize fleet, maximizing portfolio profit while ensuring all committed cargo obligations are fulfilled. Our analysis leverages dual-speed optimization, joint portfolio optimization with market vessels, and machine learning-based port congestion predictions.

**Key Recommendation:** Deploy all four Cargill vessels on high-margin market cargoes while hiring market vessels to cover committed Cargill cargoes. This arbitrage strategy yields a **total portfolio profit of $5.8 million**, significantly outperforming a conventional assignment approach.

---

## 1. Fleet & Cargo Overview

### 1.1 Cargill Fleet (4 Vessels)

| Vessel | DWT | Hire Rate | Current Port | ETD |
|--------|-----|-----------|--------------|-----|
| ANN BELL | 180,803 | $11,750/day | Qingdao | 25 Feb 2026 |
| OCEAN HORIZON | 181,550 | $15,750/day | Map Ta Phut | 1 Mar 2026 |
| PACIFIC GLORY | 182,320 | $14,800/day | Gwangyang | 10 Mar 2026 |
| GOLDEN ASCENT | 179,965 | $13,950/day | Fangcheng | 8 Mar 2026 |

### 1.2 Committed Cargill Cargoes (3 Obligations)

| Cargo | Customer | Quantity | Laycan | Freight Rate | Route |
|-------|----------|----------|--------|--------------|-------|
| EGA Bauxite | EGA | 180,000 MT | 2-10 Apr 2026 | $23.00/MT | Guinea → Qingdao |
| BHP Iron Ore | BHP | 160,000 MT | 7-11 Mar 2026 | $9.00/MT | Port Hedland → Lianyungang |
| CSN Iron Ore | CSN | 180,000 MT | 1-8 Apr 2026 | $22.30/MT | Itaguai → Qingdao |

---

## 2. Recommended Vessel-Cargo Allocation

### 2.1 Optimal Assignment Strategy

Our joint optimization algorithm recommends an **arbitrage strategy**: redirect Cargill vessels to higher-margin market cargoes while hiring market vessels at FFA rates to fulfill committed obligations.

#### Cargill Vessel Assignments (Market Cargoes)

| Vessel | Cargo | Profit | TCE |
|--------|-------|--------|-----|
| ANN BELL | Vale Malaysia Iron Ore (Brazil-Malaysia) | $915,509 | $22,614/day |
| OCEAN HORIZON | BHP Iron Ore (Australia-S.Korea) | $350,978 | $27,036/day |
| PACIFIC GLORY | Teck Coking Coal (Canada-China) | $708,408 | $29,426/day |
| GOLDEN ASCENT | Adaro Coal (Indonesia-India) | $1,169,745 | $35,181/day |

#### Market Vessel Hires (Committed Cargoes)

| Vessel | Cargo | Duration | Hire Rate |
|--------|-------|----------|-----------|
| IRON CENTURY | EGA Bauxite (Guinea-China) | 78 days | ~$20,784/day |
| ATLANTIC FORTUNE | BHP Iron Ore (Australia-China) | 30 days | ~$18,000/day |
| CORAL EMPEROR | CSN Iron Ore (Brazil-China) | 78 days | ~$13,376/day |

### 2.2 Rationale

1. **Laycan Constraints:** At eco speed, only 2 of 4 Cargill vessels (ANN BELL, OCEAN HORIZON) can make any committed cargo laycans. PACIFIC GLORY cannot reach any cargo in time.

2. **Dual-Speed Optimization:** Warranted speed unlocks 3 additional feasible voyages (GOLDEN ASCENT → EGA/CSN, OCEAN HORIZON → CSN), but at higher fuel costs.

3. **Arbitrage Opportunity:** Market cargoes offer higher TCE ($22,000-$35,000/day) compared to committed cargoes ($17,000-$27,000/day). Hiring market vessels at FFA rates (~$18,000/day) allows us to capture this spread.

4. **Total Portfolio Profit:** **$5,803,558**

---

## 3. Key Assumptions

| Assumption | Value | Source |
|------------|-------|--------|
| Bunker Price (VLSFO) | $490-$560/MT | Regional pricing (Singapore, Fujairah, Rotterdam) |
| Bunker Price (MGO) | $650/MT | Used for port operations per Cargill FAQ |
| FFA Market Rate | $18,000/day | 5TC March 2026 benchmark |
| Target TCE | $18,000/day | Based on FFA market rate |
| Port Fuel | MGO only | Per Cargill FAQ Q5/Q17 |
| Speed Options | Eco & Warranted | Dual-speed mode enabled |
| Commission | 1.25% - 3.75% | Per cargo terms |

**Fuel Consumption Rates:**
- Sea (Laden/Ballast): VLSFO
- Port Operations: MGO (as per Cargill FAQ)

---

## 4. Scenario Analysis Results

### 4.1 Bunker Price Sensitivity

We analyzed portfolio performance across bunker price variations from -20% to +50% of current levels.

| Bunker Change | Total Profit | Avg TCE | Assignment Change |
|---------------|--------------|---------|-------------------|
| -20% | $6.8M | $30,500/day | No change |
| -10% | $6.3M | $29,200/day | No change |
| Baseline | $5.8M | $28,924/day | Baseline |
| +10% | $5.3M | $27,600/day | No change |
| +20% | $4.8M | $26,300/day | No change |
| +30% | $4.3M | $25,000/day | No change |

**Key Finding:** Portfolio remains stable across bunker price variations. At **+31% bunker price increase**, the portfolio reaches a tipping point where alternative strategies become more profitable.

### 4.2 Port Delay Sensitivity (China Ports)

We analyzed the impact of additional port delays at Chinese discharge ports (Qingdao, Lianyungang, Caofeidian, etc.).

| Additional Delay | Baseline @ Delay | Re-optimized @ Delay | Switching Advantage |
|------------------|------------------|----------------------|---------------------|
| 0 days           | $5,803,558      | $5,803,558          | $0                  |
| 10 days          | $5,099,225      | $5,037,369          | -$61,857 (stick with baseline) |
| 20 days          | $4,333,036      | $4,271,180          | -$61,857 (stick with baseline) |
| 30 days          | $3,566,847      | $3,298,993          | -$267,854 (stick with baseline) |
| 40 days          | $2,800,658      | $2,700,274          | -$100,384 (stick with baseline) |
| 45 days          | $2,417,564      | $2,400,915          | -$16,649 (stick with baseline) |
| **46 days**      | **$2,340,945**  | **$2,341,043**      | **+$98 (TIPPING POINT!)** |
| 50 days          | $2,034,469      | $2,101,555          | +$67,086 (re-optimize) |
| 60 days          | $1,268,280      | $1,502,836          | +$234,556 (re-optimize) |

**Key Finding:** The baseline portfolio remains optimal up to **45 days of additional delays**. At **46 days**, re-optimizing provides a marginal advantage of $98. This demonstrates exceptional resilience of the optimal portfolio.

### 4.3 ML-Predicted Port Congestion (March 2026)

Our machine learning model predicts the following port delays:

| Port | Predicted Delay | Confidence Interval | Congestion Level |
|------|-----------------|---------------------|------------------|
| Qingdao | 3.2 days | 1.8 - 4.6 days | Medium |
| Lianyungang | 3.8 days | 2.4 - 5.2 days | Medium |
| Caofeidian | 4.5 days | 3.1 - 5.9 days | High |
| Rizhao | 2.1 days | 1.2 - 3.0 days | Low |

---

## 5. Threshold Insights (Tipping Points)

### 5.1 Bunker Price Tipping Point

**Threshold: +31% bunker price increase (1.31x multiplier)**

At a 31% bunker price increase:
- Baseline portfolio profit degrades from $5,803,558 to approximately $3,983,546
- Optimal strategy shifts to reduce ballast distances and focus on shorter routes
- Alternative portfolio becomes more profitable than baseline
- High-speed voyages become uneconomical

**Recommendation:** If bunker prices increase beyond 31% above current levels, reassess vessel assignments to prioritize fuel-efficient routes and shorter voyages.

### 5.2 Port Delay Tipping Point (China)

**Threshold: +46 days additional delay at Chinese ports**

Key findings:
- Baseline portfolio remains optimal up to +45 days of additional delays
- At +46 days, re-optimizing with delays provides a marginally more profitable portfolio (+$98 advantage)
- Profit degradation at tipping point: 59.7% (from $5,803,558 to $2,340,945)
- This indicates the baseline portfolio is highly resilient to port delays

**Recommendation:** Monitor Chinese port congestion. If delays exceed 45 days, consider:
1. Re-optimizing the portfolio to account for extended disruptions
2. Switching to warranted speed for time-critical cargoes
3. Adjusting laycan negotiations with customers
4. Exploring alternative discharge ports

Below 45 days, the baseline portfolio remains optimal despite delays.

---

## 6. Risk Considerations

| Risk Factor | Probability | Impact | Mitigation |
|-------------|-------------|--------|------------|
| Bunker price spike (+31%) | Medium | $1.8M profit loss | Lock in bunker purchases, consider fuel hedging |
| China port congestion (+46 days) | Low | $3.5M profit loss (59.7%) | Build buffer in voyage planning, monitor ML predictions |
| Market vessel unavailability | Low | High | Maintain relationships with multiple charter brokers |
| Laycan miss | Low | Very High | Dual-speed backup, warranted speed when needed |

---

## 7. Conclusion

Our recommended strategy delivers **$5.8 million in total portfolio profit** by:

1. **Optimizing vessel deployment** through joint optimization across committed and market cargoes
2. **Leveraging arbitrage** by redirecting Cargill vessels to high-margin market opportunities
3. **Ensuring obligation coverage** through strategic market vessel hires at competitive FFA rates
4. **Building resilience** with dual-speed optimization and comprehensive scenario analysis

The recommendation is robust to moderate bunker price fluctuations (up to +31%) and substantial port delays (up to +45 days). We recommend continuous monitoring of Chinese port congestion using our ML prediction model and proactive reassessment if conditions approach identified tipping points.

---

**Prepared by:**
Sidarth Rajesh & Makendra Prasad
Cargill Datathon 2026 Team