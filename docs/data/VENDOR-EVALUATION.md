# VENDOR-EVALUATION.md

## IDX Swing Trading Assistant — Vendor Evaluation

**Version:** 1.0  
**Evaluation date:** 2026-08-15

## 1. Objective

Select production-quality market data for IDX while optimizing:

1. data correctness
2. IDX coverage
3. historical quality
4. licensing
5. API reliability
6. integration effort
7. total cost

## 2. Official IDX Route

IDX's official data-services page lists IDX market-data products and registered redistributors. Local redistributors listed include Perum LKBN Antara (formerly IMQ), IQ Plus Prima, RTI Infokom, and IDX Solusi Teknologi Informasi. Foreign redistributors listed include Bloomberg, FactSet, FIS, ICE Data Services, Refinitiv, SIX, and others.

**Production research should start with this licensed-data ecosystem.**

Source: IDX Data Services. citeturn0search0

## 3. Candidate Categories

### A — IDX / Local Licensed Route
- IDX official data services
- Antara / IMQ
- IQ Plus Prima
- RTI Infokom
- IDX Solusi Teknologi Informasi

### B — Global Institutional
- Bloomberg
- FactSet
- LSEG / Refinitiv
- ICE Data Services
- FIS
- SIX
- Morningstar / Morningstar Real-Time Data

### C — Developer APIs
- Twelve Data
- other providers discovered during Phase 2

Twelve Data documents historical time series, latest prices, reference data, REST/WebSocket access, and technical-indicator APIs. Specific IDX coverage and production licensing must be verified. citeturn0search1turn0search2turn0search3

### D — Development / Research Only
Yahoo Finance lists Indonesia/IDX under `.JK` and documents a 10-minute delay, but explicitly prohibits redistribution. Therefore it should not be assumed suitable as a production/commercial feed. citeturn0search5

## 4. Scoring

| Criterion | Weight |
|---|---:|
| IDX coverage | 20% |
| Historical quality/depth | 20% |
| Accuracy/corporate actions | 15% |
| Licensing | 15% |
| API/integration | 10% |
| Reliability/SLA | 10% |
| Cost | 5% |
| Documentation/support | 5% |
| **Total** | **100%** |

Score each category 0–5.

```text
Weighted Score = Σ(score / 5 × weight)
```

Hard gates:
- Licensing >= 3/5
- IDX coverage >= 4/5
- Historical quality >= 4/5
- no critical unresolved data issue

Production target: >= 75/100.

## 5. Evaluation Matrix

| Provider | IDX | History | Corp Actions | Licensing | API | Reliability | Cost | Support | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| IDX official services | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Investigate |
| Antara / IMQ | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Investigate |
| IQ Plus Prima | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Investigate |
| RTI Infokom | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Investigate |
| IDX Solusi Teknologi Informasi | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Investigate |
| Bloomberg | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Enterprise |
| FactSet | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Enterprise |
| LSEG / Refinitiv | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Enterprise |
| ICE Data Services | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Enterprise |
| FIS | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Enterprise |
| SIX | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Enterprise |
| Twelve Data | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | POC |
| Yahoo Finance | TBD | TBD | N/A | Low for redistribution | Consumer-oriented | TBD | Low | Community | Research only |

## 6. Recommended Strategy

### Stage 1 — Prototype

Use:

```text
Mock Provider
+
one developer-friendly candidate
```

This validates the adapter and canonical data model without coupling the application to an expensive production contract.

Twelve Data is a candidate for technical evaluation because its API documentation supports historical time series, latest prices, reference data, and REST/WebSocket access. IDX coverage must be tested directly. citeturn0search1turn0search2

### Stage 2 — Production

Prioritize a licensed IDX route:

```text
IDX official data services
→ local registered redistributors
→ global institutional vendor if justified
```

## 7. Due-Diligence Questions

Ask every serious vendor:

### Coverage
1. How many IDX equities?
2. Suspended securities?
3. Delisted securities?
4. Newly listed securities?
5. Historical ticker changes?

### Historical
6. Years of daily OHLCV?
7. Point-in-time data?
8. Historical universe?
9. Delisted history?
10. Corporate actions?

### Corporate Actions
11. Split methodology?
12. Dividend representation?
13. Rights issues?
14. Raw and adjusted prices?
15. Adjustment methodology?

### Timing
16. Realtime/delayed/EOD?
17. Exact delay?
18. Timezone?
19. When is a daily bar final?
20. Can historical records be revised?

### API
21. REST?
22. WebSocket?
23. Bulk download?
24. Batch symbols?
25. Rate limits?
26. Pagination?
27. Sandbox?
28. SLA?

### Licensing
29. Can data be stored?
30. Can derived indicators be stored?
31. Can derived scores be displayed?
32. Can raw data be redistributed?
33. Commercial product allowed?
34. Per-user fees?
35. Exchange fees?

### Cost
36. Monthly cost?
37. Setup cost?
38. Historical-data cost?
39. Realtime entitlement?
40. Overage?
41. Minimum contract?
42. Cancellation terms?

## 8. Proof of Concept

Test at least two candidates using a representative fixture:

```text
BBCA
BBRI
BMRI
TLKM
ASII
ICBP
INDF
ANTM
PTBA
GOTO
```

These are only evaluation fixtures, not a permanent universe.

Compare:
- 5-year daily history
- 10-year history where available
- latest quote
- corporate actions
- metadata
- calendar
- row counts
- missing dates
- OHLC differences
- volume differences
- timestamp semantics
- latency
- API errors

## 9. Cross-Provider Reconciliation

```text
Provider A
Provider B
→ Normalize
→ Compare
→ Difference Report
```

Flag:
- price differences above tolerance
- volume differences above tolerance
- missing/extra candles
- timestamp mismatch
- corporate-action mismatch

## 10. Backtest Qualification

Before Phase 5 production backtests:

```text
Coverage
→ Completeness
→ Corporate Actions
→ Timestamp
→ Historical Universe
→ Reproducibility
→ Bias Audit
```

Unresolved material historical-data bias blocks production-grade backtesting.

## 11. Decision Record

Record in `DECISION-LOG.md`:

```text
Selected Provider:
Tier:
Plan/Contract:
Products:
IDX Coverage:
Historical Depth:
Raw/Adjusted:
Corporate Actions:
Latency:
API Limits:
Licensing:
Monthly Cost:
Fallback:
Known Limitations:
Decision Date:
```

## 12. Final Architecture Rule

The vendor can change.

The canonical market-data contract must remain stable.

Phase 2 owns the vendor adapter. Phases 3+ must not directly call a vendor API.
