# Quantitative Trading Rules

## No Look-Ahead
At timestamp T, calculations may only use information available by T.

## Data Availability
For events and fundamentals distinguish:
- event date
- publication/announcement timestamp
- effective date

Backtests use publication availability, not future knowledge.

## Corporate Actions
Raw source data and adjusted/canonical representations must remain traceable.

## Costs
Backtests must model configured fees and slippage.

## Survivorship
Universe membership must be timestamp-aware when historical robustness is evaluated.

## Reproducibility
A backtest is reproducible from:
- strategy version
- dataset version
- parameters
- execution model
- cost model

## Interpretation
A score is a ranking heuristic, not a probability of profit.
Historical performance is not a guarantee of future returns.
