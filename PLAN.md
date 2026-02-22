# TFP Implementation Plan

## Context

TFP is a greenfield Python CLI that reads a financial plan JSON file and produces a self-contained HTML report with interactive charts, tables, and a Sankey money-flow diagram. No existing code. Full JSON spec in `AGENTS.md`.

## Package Structure

```
tfp/
  __init__.py
  __main__.py          # CLI entry point (argparse)
  schema.py            # Dataclasses + JSON parsing
  validate.py          # Cross-reference + semantic validation
  engine.py            # Core month-by-month simulation step
  tax.py               # Federal/state/cap gains/NIIT/AMT/FICA computation
  tax_data.py          # All 50 states + federal brackets, versioned by year
  social_security.py   # PIA adjustment + benefit calculation
  healthcare.py        # Pre-Medicare, post-Medicare, IRMAA brackets
  rmd.py               # IRS Uniform Lifetime Table + RMD calc
  withdrawals.py       # Account drain ordering
  roth.py              # Roth conversion logic (fixed + fill-to-bracket)
  cost_basis.py        # Cost basis tracking + gains computation on withdrawals/sales
  real_assets.py       # Asset appreciation, mortgage amortization, property tax, maintenance
  simulation.py        # Orchestrator: deterministic, Monte Carlo, historical
  historical_data.py   # Bundled annual stock/bond returns 1926-2024
  report.py            # HTML generation orchestrator
  charts.py            # Chart.js configuration generation
  sankey.py            # Sankey flow data generation
  templates.py         # HTML/CSS/JS template strings + embedded Chart.js
sample_plan.json       # Realistic test fixture
tests/
  test_tax.py
  test_engine.py
  test_social_security.py
  test_rmd.py
  test_healthcare.py
  test_withdrawals.py
  test_cost_basis.py
  test_real_assets.py
  test_validation.py
  test_simulation.py
  test_golden.py       # End-to-end golden file tests
  golden/              # Normalized expected output snapshots
  conftest.py          # Shared fixtures
pyproject.toml
```

## Key Design Decisions

- **Monthly engine**: Core simulation runs month-by-month. Charts/tables aggregate to annual. Correctly handles monthly frequencies, SS claiming at specific months, Medicare start dates, mid-year transactions, and mortgage amortization.
- **Annual-to-monthly return conversion**: All annual rates (growth, dividends, fees) are converted to monthly via geometric split: `monthly_rate = (1 + annual_rate)^(1/12) - 1`. Monte Carlo and historical modes generate annual returns, which are converted to monthly using the same formula and applied uniformly across the 12 months of each simulated year.
- **Charting**: Embed Chart.js v4 minified inline in `templates.py`. Sankey uses custom vanilla JS canvas renderer with year slider.
- **State taxes**: Ship all 50 states + DC from day 1. Missing/incomplete state data causes a hard validation error.
- **Cost basis**: Average cost basis method. Track basis updates on every contribution, reinvestment, withdrawal, and sale.
- **Real asset sale basis**: `real_assets` gains a `purchase_price` field (added to AGENTS.md schema). On `sell_asset` transaction, gain = `amount - purchase_price - improvements`. Simplification: no depreciation modeling (stated explicitly).
- **Monte Carlo reproducibility**: `--seed` CLI flag. Seed stored in report metadata. Default: random seed printed to stdout.
- **HTML safety**: All user-provided strings escaped via `html.escape()`. Data embedded via `json.dumps()`.
- **Tax year versioning**: Brackets keyed by `(year, filing_status)`. Years beyond data: inflate brackets using plan inflation rate.
- **No external dependencies**: Python 3.10+ stdlib only. `pytest` dev-only.
- **Filing status + spouse**: Spouse presence is independent of filing status. MFJ/MFS require spouse (hard error). Single/HoH with spouse present: emit warning but allow (valid scenario — unmarried partner, separated, etc.).

## Phase 0: Simulation Semantics

### Monthly Event Ordering

Each simulated month executes in this strict order:

1. **Age calculation** — determine each person's age in years+months
2. **Income** — collect all active income for this month (salary, etc.; SS added here if claiming has started)
3. **FICA/self-employment tax** — compute and withhold FICA (6.2% SS up to wage base + 1.45% Medicare + 0.9% Additional Medicare Tax above $200K/$250K) on employment income; self-employment tax on SE income
4. **Income tax withholding** — withhold estimated income taxes per `withhold_percent`
5. **Payroll deductions** — apply contributions sourced from income (401k payroll)
6. **Employer match** — calculate and deposit employer match
7. **Other contributions** — non-payroll contributions (IRA, HSA, etc.)
8. **Transfers** — process recurring inter-account transfers
9. **Roth conversions** — execute scheduled conversions (fixed: monthly pro-rata; fill-to-bracket: lump in December)
10. **RMDs** — in December of applicable years, calculate and withdraw RMD for the year (see RMD rules below)
11. **Account growth** — apply monthly growth rate to all accounts
12. **Dividends** — apply monthly dividend yield; reinvest or pay to cash per account settings
13. **Fees** — deduct monthly fees from accounts
14. **Real asset updates** — appreciate/depreciate assets, compute monthly mortgage payment (principal/interest split), deduct maintenance
15. **Transactions** — execute one-time transactions scheduled for this month (sell/buy assets, with basis and tax handling)
16. **Healthcare costs** — compute healthcare for this month (pre-Medicare premiums+OOP or post-Medicare Part B/D/supplement/OOP + IRMAA surcharges). This produces a dollar amount added to total monthly expenses.
17. **Expenses** — total all active non-healthcare expenses for this month. Combined with healthcare from step 16 to get total monthly outflow.
18. **Shortfall detection + withdrawals** — if cash account balance < total expenses, execute withdrawal strategy to cover shortfall. Each withdrawal records: account, amount, gain (from cost basis tracker), tax treatment. Early withdrawal penalty (10%) applied for pre-59.5 withdrawals from 401k/IRA and tracked separately.
19. **Pay expenses** — deduct total expenses from cash account
20. **Cost basis update** — adjust basis for all withdrawals, sales, contributions, and reinvestments that occurred this month
21. **Monthly recording** — capture all flows (sources, destinations, amounts) for this month

### Annual Events (December of each year)

1. **Tax computation** — calculate actual taxes for the full year:
   - Federal income tax on ordinary income (wages, IRA/401k withdrawals, Roth conversion amounts, SS taxable portion)
   - Long-term capital gains tax on realized gains from taxable accounts
   - NIIT (3.8% on investment income above threshold)
   - AMT (simplified: 26%/28% with exemption phaseout)
   - State income tax
   - FICA already withheld monthly (step 3); no annual settlement needed for FICA
   - Early withdrawal penalties (10%) on applicable withdrawals
2. **Tax settlement** — compare actual tax to cumulative withholdings:
   - Overpayment: refund deposited to cash account
   - Underpayment: deducted from cash account. If cash insufficient, trigger withdrawal strategy to cover tax shortfall. If all accounts exhausted, record as unpaid tax liability (insolvency flag set).
3. **IRMAA determination** — compute MAGI for this year and store for lookback (applied 2 years later to healthcare costs)
4. **Annual recording** — aggregate 12 months into annual summary

### Cash Account / Insolvency Rules

- The plan must have at least one `cash` type account (validated). This is the operating account for income deposits, expense payments, and tax settlement.
- If cash goes negative after exhausting all withdrawable accounts, the simulation sets an `insolvent` flag for that month/year. Simulation continues (to show the trajectory) but the report highlights insolvency clearly.
- If no cash account exists, validation emits a hard error.

### Cost Basis Rules

- **Method**: Average cost basis (total basis / total balance)
- **On contribution/reinvestment**: basis increases by amount contributed
- **On withdrawal/sale**: basis decreases proportionally: `basis_reduction = withdrawal_amount * (total_basis / total_balance)`
- **Gain on withdrawal**: `gain = withdrawal_amount - basis_reduction`
- **Tax-advantaged accounts** (401k, traditional IRA): no basis tracking — withdrawals taxed as ordinary income
- **Roth IRA, HSA**: no basis tracking — qualified withdrawals are tax-free
- **Taxable accounts**: gains classified as long-term capital gains (simplification: all holdings assumed long-term, stated explicitly)

### Real Asset Sale Rules

- `real_assets` schema extended with `purchase_price` field (original cost basis of the asset)
- On `sell_asset` transaction linked to a real asset: `gain = sale_amount - purchase_price`
- Primary residence exclusion: if asset is flagged as primary residence, up to $250K ($500K MFJ) of gain is excluded
- Gain taxed per transaction's `tax_treatment` field
- Asset removed from real_assets list after sale; mortgage payments cease

### RMD Rules

- RMDs begin in the year the account owner turns `rmd_start_age` (default 73; will be 75 for those born 1960+)
- **Simplification**: First-year RMD is taken in December of the year the owner turns `rmd_start_age`. The real-world option to delay first RMD to April 1 of the following year is not modeled (stated explicitly as simplification).
- RMD amount = prior year-end balance / Uniform Lifetime Table divisor for current age
- RMDs are taken proportionally from all accounts listed in `rmds.accounts`
- RMD amounts count as ordinary income for tax purposes
- If an account is subject to both RMD and Roth conversion, RMD is satisfied first

### Social Security — Spousal Benefits

- The JSON schema for `social_security` remains as-is (per-person PIA + claiming age)
- **Simplification**: Spousal benefit is modeled as: if a person's own PIA < 50% of the other person's PIA, they receive the greater of (own benefit, 50% of spouse's PIA adjusted for their own claiming age). This is a simplification of the full dual-entitlement rules (stated explicitly).
- Both persons must have a `social_security` entry; if one has no work history, set `pia_at_fra: 0` and they'll receive spousal benefit only.

### Early Withdrawal Penalty Integration

- 10% penalty on pre-age-59.5 withdrawals from `401k` and `traditional_ira` account types
- Penalty is tracked as a separate line item in `MonthResult` and `AnnualResult`
- Penalty is added to the annual tax bill in the December tax settlement step
- Reported as a distinct category in tax burden chart and annual summary table
- Roth IRA: earnings portion of early withdrawals penalized (simplification: since we use average basis, any withdrawal amount exceeding total contributions is considered earnings and penalized)

### Validation Rules (validate.py)

Cross-reference checks run before simulation starts:

- All `owner` fields reference `"primary"` or `"spouse"` (spouse must exist if referenced)
- All account name references resolve to existing account/asset names
- `start_date <= end_date` for all date ranges; `plan_start <= plan_end`
- `cost_basis` required and non-null for `taxable_brokerage` accounts
- `withhold_percent` required when `tax_handling == "withhold"`
- `change_rate` required when `change_over_time` is `increase`, `decrease`, `inflation_plus`, or `inflation_minus`
- Filing status: MFJ/MFS/QSS require spouse (hard error). Single/HoH with spouse present: warning (not error).
- At least one `cash` type account must exist (hard error)
- Account types in `rmd.accounts` must be tax-deferred (`traditional_ira`, `401k`)
- Roth conversion `from_account` must be tax-deferred, `to_account` must be Roth
- No duplicate account names
- Enum values validated against allowed sets
- Real assets referenced by transactions must exist
- `purchase_price` required on real assets that have linked `sell_asset` transactions
- Actionable error messages with JSON path (e.g., `"accounts[2].owner: 'partner' is not valid, must be 'primary' or 'spouse'"`)

## Implementation Phases

### Phase 1: Data Model + Validation + CLI
**Files**: `schema.py`, `validate.py`, `__main__.py`, `__init__.py`, `sample_plan.json`

- Define all dataclasses matching JSON spec (including `purchase_price` on real assets)
- JSON loading with defaults for optional fields
- `validate.py`: all cross-reference and semantic checks listed above
- CLI argument parsing: `plan.json`, `-o`, `--mode`, `--runs`, `--seed`, `--validate`, `--summary`
- Create `sample_plan.json`: married couple (ages 45/43), two salaries, 401k + IRA + Roth + taxable + HSA + savings, primary home with mortgage, Social Security for both, Roth conversion ladder, healthcare, RMDs, 40-year plan

### Phase 2: Core Monthly Engine (Deterministic)
**Files**: `engine.py`, `simulation.py`, `cost_basis.py`, `real_assets.py`

- `MonthState`: mutable simulation state (all account balances, cost basis trackers, ages, YTD totals, MAGI history, insolvency flag)
- `MonthResult`: all computed values for one month
- `AnnualResult`: aggregated from 12 months, plus tax settlement results
- `simulate_month()`: implements the 21-step monthly ordering
- `cost_basis.py`: `CostBasisTracker` class
- `real_assets.py`: `appreciate_asset()`, `amortize_mortgage()` (standard amortization formula), `compute_property_tax()`, `compute_maintenance()`
- Transaction handling: `sell_asset` computes gain using `purchase_price`, removes asset; `buy_asset` adds to real assets or deposits to account
- `simulation.py`: `run_deterministic(plan) -> SimulationResult`
- Cash/insolvency handling per rules above

### Phase 3: Tax Engine
**Files**: `tax.py`, `tax_data.py`

- `tax_data.py`: All 50 states + DC + federal brackets, keyed by `(year, filing_status)`:
  - `FEDERAL_BRACKETS`, `STATE_TAX`, `CAPITAL_GAINS_BRACKETS`, `STANDARD_DEDUCTIONS`
  - `NIIT_THRESHOLDS`, `AMT_EXEMPTIONS`, `IRMAA_BRACKETS`
  - `FICA_RATES` (SS wage base, SS rate, Medicare rate, Additional Medicare threshold+rate)
- `tax.py` functions:
  - `compute_federal_income_tax(taxable_income, filing_status, year)`
  - `compute_capital_gains_tax(gains, other_income, filing_status, year)`
  - `compute_niit(investment_income, agi, filing_status, year)`
  - `compute_amt(income, deductions, filing_status, year)`
  - `compute_state_tax(taxable_income, state, filing_status, year)`
  - `compute_fica(wages, ytd_wages, year)` — monthly FICA with SS wage base cap tracking
  - `compute_self_employment_tax(se_income, year)` — if applicable
  - `compute_standard_vs_itemized(filing_status, year, itemized_details)`
  - `compute_total_tax(year_income_summary) -> TaxResult` — orchestrates all, includes early withdrawal penalties
  - Inflation adjustment for years beyond bracket data

### Phase 4: Retirement Features
**Files**: `social_security.py`, `rmd.py`, `healthcare.py`, `withdrawals.py`, `roth.py`

- **social_security.py**:
  - Early claiming reduction (5/9% per month for first 36 months before FRA, 5/12% beyond)
  - Delayed retirement credits (2/3% per month past FRA to age 70)
  - COLA applied annually
  - Spousal benefit: max(own_benefit, 50% of spouse PIA adjusted for claiming age)
  - SS taxable portion: up to 85% taxable based on combined income thresholds

- **rmd.py**:
  - Uniform Lifetime Table divisors (ages 72-120+)
  - First RMD in December of `rmd_start_age` year (simplified — no April 1 delay)
  - RMDs satisfied before Roth conversions and before withdrawal strategy

- **healthcare.py**:
  - Pre-Medicare: premiums + OOP, with inflation adjustment
  - Post-Medicare: Part B + supplement + Part D + OOP, with inflation adjustment
  - IRMAA: surcharge brackets looked up from MAGI 2 years prior
  - Auto-transition at age 65

- **withdrawals.py**:
  - Configurable drain order (by type or by specific account names)
  - RMD-first option
  - Early withdrawal penalty tracking (pre-59.5)
  - Handles account exhaustion gracefully

- **roth.py**:
  - Fixed amount: annual_amount / 12 monthly
  - Fill-to-bracket: compute in December based on YTD taxable income
  - Converted amount added to taxable income

### Phase 5: Monte Carlo + Historical Simulation
**Files**: `simulation.py` (extend), `historical_data.py`

- **historical_data.py**: `{year: {"stocks": float, "bonds": float}}` for 1926-2024

- **Monte Carlo**:
  - Correlated returns via Cholesky: `stock = mean_s + std_s * z1`, `bond = mean_b + std_b * (corr*z1 + sqrt(1-corr²)*z2)`
  - Annual returns → monthly via `(1 + annual)^(1/12) - 1`, applied uniformly across 12 months
  - Per-account blended return using `bond_allocation_percent`
  - Percentile bands (10th, 25th, 50th, 75th, 90th) for net worth, income, etc.
  - Success rate = % of runs with balance > 0 at plan_end
  - Seed stored in metadata; `random.seed(seed)` at start

- **Historical**:
  - Rolling N-year windows over historical dataset
  - Same return application and metrics as MC

### Phase 6: HTML Report
**Files**: `report.py`, `charts.py`, `sankey.py`, `templates.py`

- Embed Chart.js v4 minified in `templates.py`
- Charts: net worth stacked area, income vs expenses, account balances, tax burden stacked bar (federal/state/cap gains/NIIT/IRMAA/penalties), asset allocation, withdrawal sources, success probability
- Sankey: custom canvas JS, year slider, sources on left → destinations on right
- Tables: annual summary, money flow, per-account detail
- Tabs: Dashboard | Charts | Money Flows | Tables | Account Details
- Insolvency years highlighted in red
- Report metadata: seed, mode, timestamp, plan file hash

## CLI Interface

```
python -m tfp plan.json                    # writes report.html (deterministic)
python -m tfp plan.json -o my_report.html  # custom output path
python -m tfp plan.json --mode monte_carlo # override simulation mode
python -m tfp plan.json --runs 5000        # override MC run count
python -m tfp plan.json --seed 42          # reproducible MC/historical run
python -m tfp plan.json --validate         # validate JSON only, no simulation
python -m tfp plan.json --summary          # print text summary to stdout
```

## Schema Changes to AGENTS.md

- Add `purchase_price` field to `real_assets` (original cost basis, for capital gains on sale)
- Add `primary_residence` boolean to `real_assets` (for $250K/$500K exclusion)
- These are the only schema additions needed.

## Verification

1. **Unit tests** (`pytest`):
   - `test_tax.py`: Known scenarios verified against IRS tables (including FICA)
   - `test_social_security.py`: Claiming at 62/67/70 with known PIA; spousal benefit scenarios
   - `test_rmd.py`: Known balance at age 73 → specific RMD
   - `test_healthcare.py`: IRMAA at specific MAGI levels
   - `test_withdrawals.py`: Drain order, account exhaustion, early withdrawal penalties
   - `test_cost_basis.py`: Sequence of buys/sells → correct gains
   - `test_real_assets.py`: Mortgage amortization matches standard amortization schedule; asset sale gain computation
   - `test_validation.py`: Each validation rule triggers on bad input with correct error message + JSON path

2. **Golden file tests** (`test_golden.py`):
   - Run deterministic simulation on `sample_plan.json`
   - Compare **normalized snapshots**: key annual summary values (net worth, income, expenses, taxes) rounded to nearest dollar, plus targeted assertions on specific interactions (RMD year + Roth conversion + IRMAA + tax settlement)
   - Boundary tests: SS claiming month, Medicare start month, RMD start year, mortgage payoff month
   - Not full SimulationResult serialization (too brittle) — instead, extract specific stable metrics

3. **Integration tests**:
   - MC with seed=42 produces identical results on re-run (reproducibility)
   - Single filer (no spouse) runs without errors
   - Insolvency scenario: plan runs out of money, report shows $0 and insolvency markers
   - Generated HTML parseable (basic tag matching check)

4. **Manual verification**:
   - Open `report.html` in browser, verify charts render, tables populate, Sankey slider works
   - Compare 5-year simple scenario against hand-calculated spreadsheet

## Stated Simplifications

These are deliberate simplifications documented in the codebase:

1. All taxable account holdings assumed long-term for capital gains purposes
2. Average cost basis method (not specific lot identification)
3. No depreciation modeling for real assets
4. First-year RMD taken in December (no April 1 delay option)
5. Spousal SS benefit: simplified dual-entitlement (max of own vs. 50% of spouse's PIA)
6. No qualified vs. ordinary dividend distinction beyond the account-level `dividend_tax_treatment` setting
7. AMT is simplified (26%/28% with exemption phaseout, no preference item tracking)
8. Monte Carlo/historical annual returns applied uniformly across 12 months (no intra-year volatility)
