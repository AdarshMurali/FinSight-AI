# ChromaDB Vector Database — Data Inventory

**Last Updated**: 2026-06-19  
**ChromaDB Host**: `localhost:8001`  
**Embedding Model**: `text-embedding-3-small` (OpenAI, 1536 dimensions)  
**Distance Metric**: Cosine Similarity  
**Total Documents**: **24,072** (+ `market_news` growing continuously via Flink)

---

## Collection Summary

| Collection | Documents | Status | Data Source |
|-----------|----------:|--------|-------------|
| `earnings_filings` | 10,189 | ✅ Loaded | SEC EDGAR (XBRL) |
| `macro_indicators` | 3,471 | ✅ Loaded | FRED API |
| `ohlcv_data` | 3,050 | ✅ Loaded | yfinance |
| `analyst_research` | 3,621 | ✅ Loaded | Finnhub (recommendation trends) + yfinance (price targets, upgrades, EPS) |
| `market_news` | 1,966+ | ✅ Live | Yahoo Finance (historical) + Finnhub via Flink (real-time) |
| `dividends_data` | 792 | ✅ Loaded | yfinance |
| `fed_communications` | 721 | ✅ Loaded | FRED API |
| `earnings_data` | 200 | ✅ Loaded | yfinance |
| `analyst_recommendations` | 50 | ✅ Loaded | yfinance |
| `splits_data` | 12 | ✅ Loaded | yfinance |
| `volatility_events` | 0 | ⏳ Pending | Flink detector (needs market hours — Mon Jun 22) |
| `reddit_sentiment` | 0 | ⏳ Skipped | Reddit PRAW — low priority for hedge fund use case |

---

## Collection 1 — `ohlcv_data` (3,050 documents)

**Description**: Monthly OHLCV (Open-High-Low-Close-Volume) price summaries for 50 S&P 500 stocks over 5 years (2021–2026).

**Data Source**: `yfinance` (free, no API key required)  
**Time Range**: June 2021 – June 2026  
**Granularity**: Monthly (last trading day of each month)

**Document Example**:
```
AAPL monthly OHLCV: Open $127.01, High $133.94, Low $125.95, Close $133.50,
Volume 544,084,600 shares in June 2021
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `date` | string | `"2021-06-30"` |
| `open` | float | `127.01` |
| `high` | float | `133.94` |
| `low` | float | `125.95` |
| `close` | float | `133.50` |
| `volume` | int | `544084600` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"ohlcv"` |

**Companies Covered (50)**:

| Sector | Tickers |
|--------|---------|
| Technology | AAPL, MSFT, GOOGL, META, NVDA, INTC, AMD, DELL, ORCL, AVGO, ADBE, INTU, CSCO, IBM |
| Consumer Discretionary | AMZN, NFLX, MCD, DIS |
| Consumer Staples | WMT, KO, PEP, PG |
| Financials | JPM, V, MA, AXP, PYPL, BRK-B |
| Healthcare | JNJ, ABT, TMO, MRK |
| Industrials | BA, CAT, HON, UNP, F, GM |
| Energy | XOM, CVX, COP, MPC, PSX, VLO |
| Telecom | VZ, T, TMUS |
| Real Estate | SPG, EQR |
| Consumer / EV | TSLA |

> **Note**: BRK-B (Berkshire Hathaway) was initially attempted as `BRK.B` (failed) — corrected to `BRK-B`.

---

## Collection 2 — `macro_indicators` (3,471 documents)

**Description**: 43 FRED economic time series from 2019–2026, resampled to monthly frequency. Each document includes the raw value, month-over-month change, year-over-year change, and contextual interpretation.

**Data Source**: FRED (Federal Reserve Bank of St. Louis — free API key)  
**Time Range**: January 2019 – June 2026  
**Granularity**: Monthly

**Document Example**:
```
Core PCE Price Index (Fed's Preferred Inflation Gauge) was 3.48 in January 2024.
This is down 0.09% from the prior month (3.57). Year-over-year it is down 12.33%
from 3.97. Inflation is above the Federal Reserve's 2% target.
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `series_id` | string | `"PCEPILFE"` |
| `series_name` | string | `"Core PCE Price Index..."` |
| `date` | string | `"2024-01-31"` |
| `value` | float | `3.48` |
| `macro_category` | string | `"inflation"` |
| `unit` | string | `"%"` |
| `source` | string | `"fred"` |
| `data_type` | string | `"macro_indicator"` |
| `event_type` | string | `"macro_data"` |

**Series Loaded (43 total)**:

### Interest Rates & Treasury Yields (12 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| FEDFUNDS | Effective Federal Funds Rate | 89 |
| DGS1MO | 1-Month Treasury Yield | 90 |
| DGS3MO | 3-Month Treasury Yield | 90 |
| DGS6MO | 6-Month Treasury Yield | 90 |
| DGS1 | 1-Year Treasury Yield | 90 |
| DGS2 | 2-Year Treasury Yield | 90 |
| DGS5 | 5-Year Treasury Yield | 90 |
| DGS10 | 10-Year Treasury Yield | 90 |
| DGS30 | 30-Year Treasury Yield | 90 |
| T10Y2Y | Yield Curve Spread (10Y − 2Y) | 90 |
| T10Y3M | Yield Curve Spread (10Y − 3M) | 90 |
| T10YIE | 10-Year Breakeven Inflation Rate | 90 |

### Inflation (5 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| CPIAUCSL | Consumer Price Index (All Items) | 88 |
| CPILFESL | Core CPI (Ex Food & Energy) | 88 |
| PCEPI | PCE Price Index | 88 |
| PCEPILFE | Core PCE — Fed's Preferred Gauge | 88 |
| PPIFIS | Producer Price Index (Final Demand) | 89 |

### Employment (7 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| UNRATE | Unemployment Rate | 88 |
| U6RATE | U-6 Underemployment Rate (Broadest Measure) | 88 |
| PAYEMS | Total Nonfarm Payrolls | 89 |
| ICSA | Initial Jobless Claims (Weekly) | 90 |
| CIVPART | Labor Force Participation Rate | 88 |
| EMRATIO | Employment-Population Ratio | 88 |
| JTSJOL | Job Openings (JOLTS) | 88 |

### GDP & Growth (3 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| GDP | US Nominal GDP (Quarterly) | 29 |
| GDPC1 | US Real GDP, Inflation-Adjusted (Quarterly) | 29 |
| GDPCA | Real GDP Growth Rate, Annual | 7 |

### Consumer & Spending (3 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| UMCSENT | University of Michigan Consumer Sentiment | 88 |
| RSAFS | US Retail Sales (Advance) | 89 |
| PSAVERT | Personal Saving Rate | 88 |

### Housing (4 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| CSUSHPISA | Case-Shiller US Home Price Index | 87 |
| MORTGAGE30US | 30-Year Fixed Mortgage Rate | 90 |
| HOUST | US Housing Starts | 89 |
| PERMIT | US Building Permits | 89 |

### Money Supply (2 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| M2SL | M2 Money Supply | 88 |
| BOGMBASE | Monetary Base | 88 |

### Volatility & Credit Spreads (4 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| VIXCLS | CBOE VIX Volatility Index | 90 |
| BAMLH0A0HYM2 | US High Yield Corporate Bond Spread (OAS) | 37 |
| BAMLC0A0CM | US Investment Grade Corporate Bond Spread (OAS) | 37 |
| TEDRATE | TED Spread (LIBOR − T-Bill) | 37 |

> Note: BAML credit spreads and TEDRATE return 37 records — these series have limited history on FRED as LIBOR was discontinued in 2023.

### Commodities & FX (3 series)
| Series ID | Description | Records |
|-----------|-------------|---------|
| DCOILWTICO | WTI Crude Oil Price | 90 |
| DEXUSEU | USD to EUR Exchange Rate | 90 |
| DEXJPUS | Japanese Yen per USD | 90 |

---

## Collection 3 — `market_news` (1,719 documents)

**Description**: Company news articles for all 50 covered stocks from two sources: a historical batch load from Yahoo Finance (533 docs) and a continuously growing real-time stream via Flink + Finnhub (1,186+ docs as of 2026-06-19). The collection is live — document count increases every 2 minutes while the Flink pipeline is running.

**Data Sources**:
| Source | Loader | Documents | `source` value | Distinguishing fields |
|--------|--------|----------:|----------------|-----------------------|
| Yahoo Finance (historical) | `historical_loader.py` batch | 533 | `yahoo_finance_news` | No sentiment fields |
| Finnhub REST API (real-time) | Flink `news_sentiment_job.py` | 1,186+ | `finnhub` | `ingested_via`, `sentiment_*` fields |

**Coverage**: 50 S&P 500 tickers (full list in Collection 1)  
**Recency**: Historical batch loaded June 2026; real-time stream active continuously

**Document Example (Flink / Finnhub)**:
```
NVDA announces major AI partnership with cloud provider: NVIDIA Corporation signed
a multi-year deal to supply H100 GPUs to a major hyperscaler.
```

**Metadata Fields**:
| Field | Type | Source | Example |
|-------|------|--------|---------|
| `ticker` | string | Both | `"NVDA"` |
| `title` | string | Both | `"NVDA announces..."` |
| `publisher` | string | Both | `"Reuters"` |
| `published_at` | string | Both | `"2026-06-19T10:30:00+00:00"` |
| `url` | string | Both | `"https://..."` |
| `source` | string | Both | `"finnhub"` or `"yahoo_finance_news"` |
| `data_type` | string | Both | `"news"` |
| `event_type` | string | Both | `"news"` |
| `category` | string | Flink only | `"company news"` |
| `ingested_via` | string | Flink only | `"flink_stream"` |
| `sentiment_label` | string | Flink only | `"Bullish"` / `"Bearish"` / `"Neutral"` |
| `sentiment_score` | float | Flink only | `0.813` |
| `sentiment_pos` | float | Flink only | `0.142` |
| `sentiment_neg` | float | Flink only | `0.021` |

**ID Format**:
- Historical: `news_{ticker}_{index}_{date}` (e.g. `news_AAPL_0_2026-06-18`)
- Flink: `fn_news_{ticker}_{md5[:12]}` (e.g. `fn_news_NVDA_a3f9c2d1b4e8`)

**To query only Flink-loaded docs**:
```python
col.get(where={"ingested_via": {"$eq": "flink_stream"}})
```

**To query only historical docs**:
```python
col.get(where={"source": {"$eq": "yahoo_finance_news"}})
```

---

## Collection 4 — `fed_communications` (721 documents)

**Description**: Federal Reserve monetary policy series — rate targets, balance sheet components, and reserve data. Tracks QE/QT cycles, rate hike/cut decisions, and balance sheet expansion/contraction.

**Data Source**: FRED API (free)  
**Time Range**: January 2019 – June 2026  
**Granularity**: Monthly

**Document Example**:
```
Federal Reserve Federal Funds Rate Upper Target was 5.50% in January 2024.
The Fed raised this by 0.00% from the prior month. The Fed balance sheet is
historically elevated, reflecting quantitative easing.
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `series_id` | string | `"DFEDTARU"` |
| `series_name` | string | `"Federal Funds Rate Upper Target"` |
| `date` | string | `"2024-01-31"` |
| `value` | float | `5.50` |
| `fed_category` | string | `"rate_decision"` |
| `unit` | string | `"%"` |
| `source` | string | `"fred"` |
| `data_type` | string | `"fed_communication"` |
| `event_type` | string | `"monetary_policy"` |

**Series Loaded (9 total)**:

| Series ID | Description | Records | Category |
|-----------|-------------|---------|----------|
| DFEDTARU | Fed Funds Rate Upper Target | 90 | rate_decision |
| DFEDTARL | Fed Funds Rate Lower Target | 90 | rate_decision |
| EFFR | Effective Federal Funds Rate (monthly avg) | 90 | rate_decision |
| IOER | Interest on Excess Reserves (retired Jul 2021) | 31 | rate_decision |
| IORB | Interest on Reserve Balances (replaced IOER) | 60 | rate_decision |
| WALCL | Fed Balance Sheet Total Assets | 90 | balance_sheet |
| WRESBAL | Reserve Balances at Federal Reserve Banks | 90 | balance_sheet |
| TREAST | US Treasury Securities Held by the Fed | 90 | balance_sheet |
| WSHOMCB | Mortgage-Backed Securities Held by the Fed | 90 | balance_sheet |

> Note: IOER (31 records) + IORB (60 records) together cover the full period — IOER was replaced by IORB in July 2021.

---

## Collection 5 — `dividends_data` (792 documents)

**Description**: Historical dividend payment records for covered stocks over the past 5 years.

**Data Source**: `yfinance` (free)  
**Time Range**: June 2021 – June 2026

**Document Example**:
```
AAPL paid dividend of $0.22 per share on August 06, 2021
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `date` | string | `"2021-08-06"` |
| `amount` | float | `0.22` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"dividend"` |
| `event_type` | string | `"dividend"` |

**Dividend Records by Ticker (selected)**:
| Ticker | Records | Note |
|--------|---------|------|
| AAPL | 20 | Quarterly payer |
| MSFT | 20 | Quarterly payer |
| KO | 20 | Quarterly payer |
| COP | 28 | Variable dividend payer |
| SPG | 21 | REIT — quarterly |
| DIS | 5 | Reinstated dividend |
| TMUS | 11 | Initiated dividends recently |
| AMZN | 0 | Does not pay dividends |
| TSLA | 0 | Does not pay dividends |
| NFLX | 0 | Does not pay dividends |
| AMD | 0 | Does not pay dividends |

---

## Collection 6 — `earnings_data` (200 documents)

**Description**: Quarterly financial report dates and earnings summaries for covered stocks.

**Data Source**: `yfinance` (free)  
**Coverage**: ~4 most recent quarters per ticker

**Document Example**:
```
AAPL reported quarterly financials for March 2026
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `date` | string | `"2026-03-31"` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"quarterly_financials"` |
| `event_type` | string | `"earnings_report"` |

---

## Collection 7 — `analyst_recommendations` (50 documents)

**Description**: Current analyst consensus ratings and price targets for all 50 covered stocks.

**Data Source**: `yfinance` (free)  
**Coverage**: 1 document per ticker — current snapshot as of load date (June 2026)

**Document Example**:
```
AAPL: Analyst consensus is BUY with a target price of $312.72 based on 43 analyst opinions
MSFT: Analyst consensus is STRONG_BUY with a target price of $561.39 based on 55 analyst opinions
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `recommendation` | string | `"BUY"` |
| `target_price` | float | `312.72` |
| `num_analysts` | int | `43` |
| `date` | string | `"2026-06-18"` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"analyst_recommendation"` |
| `event_type` | string | `"analyst_rating"` |

---

## Collection 8 — `splits_data` (12 documents)

**Description**: Stock split events for covered tickers in the 5-year window.

**Data Source**: `yfinance` (free)  
**Coverage**: Only tickers that had a split between 2021–2026

**Document Example**:
```
GOOGL underwent a 20.0 stock split on July 18, 2022
AMZN underwent a 20.0 stock split on June 06, 2022
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"GOOGL"` |
| `date` | string | `"2022-07-18"` |
| `split_ratio` | float | `20.0` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"split"` |
| `event_type` | string | `"stock_split"` |

**Known splits in window**:
| Ticker | Ratio | Date |
|--------|-------|------|
| GOOGL | 20:1 | July 18, 2022 |
| AMZN | 20:1 | June 6, 2022 |
| NVDA | 10:1 | June 10, 2024 |
| AVGO | 10:1 | July 15, 2024 |
| WMT | 3:1 | February 26, 2024 |
| TSLA | various | within window |

---

## Collection 9 — `earnings_filings` (10,189 documents)

**Description**: Quarterly and annual XBRL financial facts for all 50 covered companies, sourced directly from SEC EDGAR filings (10-K and 10-Q). Covers income statement and balance sheet metrics over 5 years.

**Data Source**: SEC EDGAR public REST API (completely free, no API key required)  
**API Base URL**: `https://data.sec.gov/api/xbrl/companyfacts/`  
**Time Range**: June 2021 – June 2026  
**Granularity**: Per filing (quarterly + annual)

**Document Examples**:
```
Apple Inc. (AAPL) quarterly Revenue was $94.84B$ for Q4 2021
(period ending September 2021, filed 2021-10-29).

Tesla, Inc. (TSLA) quarterly Net Income was $3.32B$ for Q3 2022
(period ending September 2022, filed 2022-10-24).

NVIDIA Corporation (NVDA) Total Assets was $65.73B$ as of January 2024
(annual filing, filed 2024-02-21).
```

**Metadata Fields**:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `company_name` | string | `"Apple Inc."` |
| `cik` | string | `"0000320193"` |
| `metric` | string | `"Revenue"` |
| `concept` | string | `"Revenues"` |
| `value` | float | `94.84` |
| `unit` | string | `"B$"` |
| `period_end` | string | `"2021-09-25"` |
| `filed_date` | string | `"2021-10-29"` |
| `form_type` | string | `"10-Q"` |
| `fiscal_period` | string | `"Q4 2021"` |
| `report_type` | string | `"quarterly"` |
| `source` | string | `"sec_edgar"` |
| `data_type` | string | `"financial_filing"` |
| `event_type` | string | `"earnings_report"` or `"balance_sheet"` |

**Metrics Extracted**:

| Category | Metric | US-GAAP Concept |
|----------|--------|-----------------|
| Income Statement | Revenue | `Revenues` / `RevenueFromContractWithCustomerExcludingAssessedTax` |
| Income Statement | Gross Profit | `GrossProfit` |
| Income Statement | Operating Income | `OperatingIncomeLoss` |
| Income Statement | Net Income | `NetIncomeLoss` |
| Income Statement | EPS Diluted | `EarningsPerShareDiluted` |
| Income Statement | R&D Expense | `ResearchAndDevelopmentExpense` |
| Income Statement | SG&A Expense | `SellingGeneralAndAdministrativeExpense` |
| Cash Flow | Operating Cash Flow | `NetCashProvidedByUsedInOperatingActivities` |
| Cash Flow | CapEx | `PaymentsToAcquirePropertyPlantAndEquipment` |
| Balance Sheet | Total Assets | `Assets` |
| Balance Sheet | Total Liabilities | `Liabilities` |
| Balance Sheet | Stockholders Equity | `StockholdersEquity` |
| Balance Sheet | Cash & Equivalents | `CashAndCashEquivalentsAtCarryingValue` |
| Balance Sheet | Long-Term Debt | `LongTermDebt` |
| Balance Sheet | Shares Outstanding | `CommonStockSharesOutstanding` |

**Records per Company**:
| Ticker | Records | Ticker | Records | Ticker | Records |
|--------|---------|--------|---------|--------|---------|
| DELL | 292 | TSLA | 281 | MSFT | 280 |
| AAPL | 279 | HON | 251 | BA | 245 |
| AMD | 241 | NFLX | 242 | ADBE | 240 |
| AMZN | 230 | AVGO | 229 | NVDA | 255 |
| TMUS | 227 | IBM | 225 | INTC | 228 |
| CSCO | 260 | INTU | 219 | GOOGL | 216 |
| JNJ | 211 | KO | 212 | PEP | 210 |
| META | 208 | TMO | 209 | ABT | 205 |
| XOM | 205 | MPC | 200 | GM | 201 |
| PYPL | 201 | CAT | 199 | MCD | 197 |
| DIS | 190 | UNP | 186 | AXP | 186 |
| WMT | 185 | SPG | 185 | F | 179 |
| MRK | 178 | COP | 177 | ORCL | 176 |
| PSX | 175 | CVX | 169 | EQR | 166 |
| PG | 165 | T | 161 | MA | 160 |
| VZ | 150 | VLO | 135 | V | 133 |
| BRK-B | 115 | JPM | 120 | | |

> Note: Banks (JPM, BRK-B) and financial holding companies report fewer matching metrics because they use different GAAP concepts (e.g. `InterestAndFeeIncomeLoansAndLeases` instead of `Revenues`).

---

## Collection 10 — `analyst_research` (3,621 documents)

**Description**: Four types of analyst research data across all 50 covered stocks — monthly consensus trends, current price targets with implied upside, firm-level rating changes, and forward EPS estimates.

**Data Sources**:
| Type | Source | Documents | Endpoint |
|------|--------|----------:|----------|
| Recommendation trends | Finnhub (free) | 200 | `/stock/recommendation` |
| Price targets | yfinance (free) | 50 | `ticker.analyst_price_targets` |
| Upgrade/downgrades | yfinance (free) | 3,171 | `ticker.upgrades_downgrades` |
| EPS estimates | yfinance (free) | 200 | `ticker.earnings_estimate` |

**Coverage**: All 50 tickers — recommendation trends up to 18 months history, upgrades/downgrades past 12 months, EPS estimates for next 2 quarters  
**Loaded**: 2026-06-19 via `backend/rag/analyst_research_loader.py`

**Document Examples**:
```
AAPL analyst consensus in June 2026: 14 Strong Buy, 24 Buy, 15 Hold, 2 Sell, 0 Strong Sell
(55 analysts total). Bullish: 69.1%, Bearish: 3.6%. Overall sentiment: moderately bullish.

AAPL analyst price targets (as of 2026-06-19): Mean target $314.42, Bull case $400.00,
Bear case $215.00. Current price $298.01 — implied upside to mean: +5.5%.

B of A Securities reiterated Buy on AAPL on 2026-06-18.

AAPL EPS estimate for 0q: consensus $1.89 from 31 analysts (range: $1.83 to $1.99).
Year-over-year change: +20.7% vs $1.57 last year.
```

**Metadata Fields by Type**:

*recommendation_trend*:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `period` | string | `"2026-06"` |
| `strong_buy`, `buy`, `hold`, `sell`, `strong_sell` | int | `14, 24, 15, 2, 0` |
| `total_analysts` | int | `55` |
| `bull_pct`, `bear_pct` | float | `69.1, 3.6` |
| `consensus` | string | `"moderately bullish"` |
| `source` | string | `"finnhub"` |
| `data_type` | string | `"recommendation_trend"` |

*price_target*:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `current_price` | float | `298.01` |
| `target_mean`, `target_high`, `target_low` | float | `314.42, 400.00, 215.00` |
| `upside_pct` | float | `5.5` |
| `spread_pct` | float | `62.2` |
| `as_of` | string | `"2026-06-19"` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"price_target"` |

*upgrade_downgrade*:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `firm` | string | `"B of A Securities"` |
| `action` | string | `"reiterate"` / `"upgrade"` / `"downgrade"` / `"init"` |
| `from_grade`, `to_grade` | string | `"Neutral", "Buy"` |
| `date` | string | `"2026-06-18"` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"upgrade_downgrade"` |

*eps_estimate*:
| Field | Type | Example |
|-------|------|---------|
| `ticker` | string | `"AAPL"` |
| `period` | string | `"0q"` (current quarter) |
| `eps_estimate`, `eps_high`, `eps_low` | float | `1.89, 1.99, 1.83` |
| `year_ago_eps` | float | `1.57` |
| `n_analysts` | int | `31` |
| `source` | string | `"yfinance"` |
| `data_type` | string | `"eps_estimate"` |

> Note: Finnhub free tier only provides `/stock/recommendation`. The other 3 endpoints (`/price-target`, `/upgrade-downgrade`, `/eps-estimate`) require a paid plan — yfinance provides equivalent data free.

---

## Pending Collections

| Collection | Planned Source | Planned Volume | Status |
|-----------|---------------|----------------|--------|
| `volatility_events` | Flink `volatility_detector_job.py` (trade price spikes) | ~1,000–5,000 docs | Flink ready — needs market hours (Mon Jun 22) |
| `reddit_sentiment` | Reddit PRAW (r/investing, r/wsb) | ~20,000–100,000 docs | Skipped — low priority for hedge fund use case |

> To populate `volatility_events`, start `finnhub_trade_producer.py` (WebSocket trade stream) and submit `volatility_detector_job.py` to Flink during market hours.

---

## Data Loading Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `backend/rag/load_financial_data.py` | Load all 50 stocks (OHLCV, dividends, splits, earnings, analysts, news) | `python backend/rag/load_financial_data.py` |
| `backend/rag/historical_loader.py` | Load specific tickers or data types | `python backend/rag/historical_loader.py --tickers AAPL MSFT --macro --fed` |
| `backend/rag/validate_data.py` | Inspect collection counts and sample docs | `python backend/rag/validate_data.py` |
| `backend/flink/finnhub_news_producer.py` | Poll Finnhub REST API → Kafka `market.news` (run in venv) | `python backend/flink/finnhub_news_producer.py` |
| `backend/flink/finnhub_trade_producer.py` | Finnhub WebSocket trades → Kafka `market.trades` (run in venv) | `python backend/flink/finnhub_trade_producer.py` |
| `backend/flink/news_sentiment_job.py` | PyFlink: Kafka → VADER sentiment → ChromaDB `market_news` | `docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/news_sentiment_job.py` |
| `backend/flink/volatility_detector_job.py` | PyFlink: Kafka trades → 5-min windows → ChromaDB `volatility_events` | `docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/volatility_detector_job.py` |
| `backend/flink/check_sources.py` | Query ChromaDB to show historical vs Flink doc counts in `market_news` | `python backend/flink/check_sources.py` |
| `backend/rag/analyst_research_loader.py` | Load analyst research (recommendation trends, price targets, upgrades, EPS) | `python backend/rag/analyst_research_loader.py` |
| `backend/rag/check_analyst.py` | Inspect `analyst_research` collection counts by type and show sample docs | `python backend/rag/check_analyst.py` |

### Load Only FRED Data
```bash
python backend/rag/historical_loader.py --tickers AAPL --macro --fed
# Skip --ohlcv --dividends --splits --earnings --analysts --news to avoid reloading stock data
```

### Load SEC EDGAR for All 50 Tickers
```bash
cd backend/rag
python -c "
from chromadb_setup import get_chroma_client, initialize_collections
from historical_loader import load_sec_edgar
client = get_chroma_client()
cols = initialize_collections(client)
load_sec_edgar(['AAPL','MSFT','GOOGL',...], cols['earnings_filings'], years=5)
"
```

### Load a New Ticker
```bash
python backend/rag/historical_loader.py --tickers NEW_TICKER --years 5
```

### Reload a Specific Collection
```bash
# Delete and reload just macro indicators
python -c "
from backend.rag.chromadb_setup import get_chroma_client
client = get_chroma_client()
client.delete_collection('macro_indicators')
"
python backend/rag/historical_loader.py --tickers AAPL --macro
```

---

## Environment Variables Required

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | Embeddings via `text-embedding-3-small` |
| `FRED_API_KEY` | Yes (for macro/fed) | FRED economic time series |
| `FINNHUB_API_KEY` | Yes (for Flink stream) | Finnhub news + trade producers |

> SEC EDGAR requires no API key — only a `User-Agent` header with name and email per SEC guidelines.

All keys stored in `backend/.env`.

---

## Infrastructure

| Component | Details |
|-----------|---------|
| **ChromaDB** | Docker container `FinSight_AI_chromadb` — HTTP server on `localhost:8001`, volume `chroma_data` (240 MB on disk) |
| **Embedding Model** | `text-embedding-3-small` (OpenAI) — 1536 dimensions |
| **Distance Metric** | Cosine similarity (`hnsw:space = cosine`) |
| **Storage** | Docker named volume `chroma_data` — persists across container restarts |
| **Batch Loader** | Python scripts (`yfinance`, `fredapi`, `sec_edgar`) — `backend/rag/` |
| **Kafka** | Docker container `finsight-kafka` — broker on `localhost:9092` (external) / `kafka:29092` (internal) |
| **Zookeeper** | Docker container `finsight-zookeeper` — port `2181` |
| **Kafka UI** | Docker container `finsight-kafka-ui` — browser dashboard at `http://localhost:8080` |
| **Flink JobManager** | Docker container `finsight-flink-jobmanager` — Web UI at `http://localhost:8082` |
| **Flink TaskManager** | Docker container `finsight-flink-taskmanager` — 4 task slots, 1728 MB memory |
| **Flink Version** | 1.18.1 (PyFlink) |
| **Streaming Stack** | `docker-compose-streaming.yml` — started with `docker compose -f docker-compose-streaming.yml up -d` |

### Active Flink Jobs (as of 2026-06-19)

| Job | Status | Kafka Topic | ChromaDB Target | Started |
|-----|--------|-------------|-----------------|---------|
| `FinSight News Sentiment Stream` | RUNNING | `market.news` | `market_news` | 2026-06-19 00:58 |

---

## Query Interface

```python
from backend.rag.query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Semantic search across all collections
results = engine.retrieve_context(
    query="Federal Reserve rate hikes impact on tech stocks",
    n_results=10
)

# Build full RAG prompt for LLM
prompt = engine.build_context_prompt(
    query="Why did the yield curve invert in 2022 and how did markets react?"
)
```

---

## Load History

| Date | Action | Documents Added | Total |
|------|--------|----------------|-------|
| 2026-06-18 | Initial load — 49 stocks OHLCV, dividends, splits, earnings, analysts, news | 4,561 | 4,561 |
| 2026-06-18 | Added BRK-B (corrected ticker from BRK.B) | 76 | 4,637 |
| 2026-06-18 | FRED macro indicators — 43 series | 3,471 | 8,108 |
| 2026-06-18 | Fed communications — 9 balance sheet / rate series | 721 | 8,829 |
| 2026-06-18 | SEC EDGAR XBRL financial facts — all 50 tickers, 15 metrics, 5 years | 10,189 | 19,018 |
| 2026-06-19 | Flink streaming pipeline launched — `news_sentiment_job.py` consuming `market.news` Kafka topic | — | — |
| 2026-06-19 | Flink real-time news: Finnhub articles with VADER sentiment → `market_news` collection (ongoing) | 1,433+ | 20,451+ |
| 2026-06-19 | Analyst research batch load — recommendation trends (Finnhub) + price targets, upgrades, EPS estimates (yfinance) | 3,621 | 24,072+ |

**Current Total: 24,072+ documents** (growing continuously via Flink `market_news` pipeline)

> `market_news` is a live collection — count increases every ~2 minutes while `finnhub_news_producer.py` is running.  
> `analyst_research` captures a point-in-time snapshot; re-run `analyst_research_loader.py` periodically to refresh upgrade/downgrade history and EPS estimates.
