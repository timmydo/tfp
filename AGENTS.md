# TFP - Timmy's Financial Planner

A command-line Python application with minimal dependencies. TFP reads a single JSON file describing a household's complete financial picture and produces a self-contained HTML file with interactive charts, graphs, and tables. The JSON file is intended to be created and modified by an AI agent conversing with the user; the Python script is a read-only consumer of that JSON.

## Architecture

```
User <-> AI Agent <-> plan.json -> tfp.py -> report.html
```

- **plan.json**: All financial data (created/edited by AI agent or by hand)
- **tfp.py**: Reads JSON, runs simulation, writes HTML
- **report.html**: Self-contained interactive output (inline CSS/JS, no external dependencies)

## Commit Policy

- Agent-created commits must include a `Co-Authored-By:` trailer.
- Run `python3 -m pytest -q` before committing.
- Do not commit if tests are failing.

## JSON File Specification

All dates use `YYYY-MM` format throughout.

---

### `people`

```json
{
  "people": {
    "primary": {
      "name": "string",
      "birthday": "YYYY-MM",
      "state": "XX"
    },
    "spouse": {
      "name": "string",
      "birthday": "YYYY-MM"
    }
  }
}
```

- **primary** (required): name, birthday (for age calculations), US state (for state tax)
- **spouse** (optional): name and birthday

---

### `filing_status`

```json
{
  "filing_status": "married_filing_jointly"
}
```

One of: `single`, `married_filing_jointly`, `married_filing_separately`, `head_of_household`, `qualifying_surviving_spouse`

---

### `accounts`

A list of financial accounts.

```json
{
  "accounts": [
    {
      "name": "Fidelity 401k",
      "type": "401k",
      "owner": "primary",
      "balance": 500000,
      "cost_basis": null,
      "growth_rate": 0.07,
      "dividend_yield": 0.02,
      "dividend_tax_treatment": "plan_settings",
      "reinvest_dividends": true,
      "bond_allocation_percent": 20,
      "yearly_fees": 0.001,
      "allow_withdrawals": true
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `type` | enum | `cash`, `taxable_brokerage`, `401k`, `traditional_ira`, `roth_ira`, `hsa`, `529`, `other` |
| `owner` | string | `"primary"` or `"spouse"` |
| `balance` | number | Current balance in dollars |
| `cost_basis` | number/null | Cost basis for taxable accounts; null for tax-advantaged |
| `growth_rate` | number | Expected annual growth (e.g. 0.07 = 7%) |
| `dividend_yield` | number | Expected annual dividend yield |
| `dividend_tax_treatment` | enum | `tax_free`, `income`, `capital_gains`, `plan_settings` |
| `reinvest_dividends` | boolean | Reinvest or pay out to cash |
| `bond_allocation_percent` | number | 0-100, percentage in bonds |
| `yearly_fees` | number | Annual fee percentage (e.g. 0.001 = 0.1%) |
| `allow_withdrawals` | boolean | Whether the plan can withdraw from this account |

---

### `contributions`

Ongoing contributions to accounts (e.g., 401k payroll deductions, IRA contributions).

```json
{
  "contributions": [
    {
      "name": "401k payroll contribution",
      "source_account": "checking",
      "destination_account": "Fidelity 401k",
      "amount": 23000,
      "frequency": "annual",
      "start_date": "start",
      "end_date": "2030-12",
      "change_over_time": "match_inflation",
      "change_rate": null,
      "employer_match": {
        "match_percent": 0.50,
        "up_to_percent_of_salary": 0.06,
        "salary_reference": "Salary"
      }
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `source_account` | string | Account name to draw from (or `"income"` for payroll deductions) |
| `destination_account` | string | Account name to deposit into |
| `amount` | number | Contribution amount in dollars |
| `frequency` | enum | `monthly`, `annual` |
| `start_date` | string | `YYYY-MM` or `"start"` |
| `end_date` | string | `YYYY-MM` or `"end"` |
| `change_over_time` | enum | `fixed`, `increase`, `decrease`, `match_inflation`, `inflation_plus`, `inflation_minus` |
| `change_rate` | number/null | Custom percentage for applicable change types |
| `employer_match` | object/null | Optional employer match details |

---

### `income`

```json
{
  "income": [
    {
      "name": "Salary",
      "owner": "primary",
      "amount": 150000,
      "frequency": "annual",
      "start_date": "start",
      "end_date": "2035-06",
      "change_over_time": "inflation_plus",
      "change_rate": 0.01,
      "tax_handling": "withhold",
      "withhold_percent": 0.25
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `owner` | string | `"primary"` or `"spouse"` |
| `amount` | number | Starting amount in dollars |
| `frequency` | enum | `monthly`, `annual`, `one_time` |
| `start_date` | string | `YYYY-MM` or `"start"` |
| `end_date` | string | `YYYY-MM` or `"end"` |
| `change_over_time` | enum | `fixed`, `increase`, `decrease`, `match_inflation`, `inflation_plus`, `inflation_minus` |
| `change_rate` | number/null | Custom percentage for applicable change types |
| `tax_handling` | enum | `withhold`, `tax_exempt` |
| `withhold_percent` | number/null | Withholding percentage (when `tax_handling` is `withhold`) |

---

### `expenses`

```json
{
  "expenses": [
    {
      "name": "Groceries",
      "owner": "joint",
      "amount": 800,
      "frequency": "monthly",
      "start_date": "start",
      "end_date": "end",
      "change_over_time": "match_inflation",
      "change_rate": null,
      "spending_type": "essential"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `owner` | string | `"primary"`, `"spouse"`, or `"joint"` |
| `amount` | number | Starting amount in dollars |
| `frequency` | enum | `monthly`, `annual`, `one_time` |
| `start_date` | string | `YYYY-MM` or `"start"` |
| `end_date` | string | `YYYY-MM` or `"end"` |
| `change_over_time` | enum | `fixed`, `increase`, `decrease`, `match_inflation`, `inflation_plus`, `inflation_minus` |
| `change_rate` | number/null | Custom percentage for applicable change types |
| `spending_type` | enum | `essential`, `discretionary` |

---

### `social_security`

Social Security benefit details for each person.

```json
{
  "social_security": [
    {
      "owner": "primary",
      "pia_at_fra": 3200,
      "fra_age_years": 67,
      "fra_age_months": 0,
      "claiming_age_years": 70,
      "claiming_age_months": 0,
      "cola_assumption": "match_inflation"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | `"primary"` or `"spouse"` |
| `pia_at_fra` | number | Primary Insurance Amount at Full Retirement Age (monthly) |
| `fra_age_years` | number | Full retirement age (years component) |
| `fra_age_months` | number | Full retirement age (months component, 0-11) |
| `claiming_age_years` | number | Planned claiming age (years component) |
| `claiming_age_months` | number | Planned claiming age (months component, 0-11) |
| `cola_assumption` | enum | `fixed`, `match_inflation`, `inflation_plus`, `inflation_minus` |
| `cola_rate` | number/null | Custom rate for applicable COLA types |

The simulator calculates actual benefits based on early/late claiming adjustments relative to FRA.

Spousal benefits are modeled with a simplified dual-entitlement rule: if a person's own benefit is lower than 50% of the spouse's PIA baseline, they receive the larger of their own benefit and the simplified spousal amount. This is an explicit approximation.

---

### `healthcare`

Healthcare cost modeling with distinct phases for pre-Medicare and post-Medicare.

```json
{
  "healthcare": {
    "pre_medicare": [
      {
        "owner": "primary",
        "monthly_premium": 600,
        "annual_out_of_pocket": 3000,
        "start_date": "start",
        "end_date": null,
        "change_over_time": "inflation_plus",
        "change_rate": 0.02
      }
    ],
    "post_medicare": [
      {
        "owner": "primary",
        "medicare_start_date": null,
        "part_b_monthly_premium": 175,
        "supplement_monthly_premium": 200,
        "part_d_monthly_premium": 40,
        "annual_out_of_pocket": 2000,
        "change_over_time": "inflation_plus",
        "change_rate": 0.02
      }
    ],
    "irmaa": {
      "enabled": true,
      "lookback_years": 2
    }
  }
}
```

**Pre-Medicare** (per person):

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | `"primary"` or `"spouse"` |
| `monthly_premium` | number | Monthly insurance premium |
| `annual_out_of_pocket` | number | Expected annual out-of-pocket costs |
| `start_date` | string/null | `YYYY-MM`, `"start"`, or null (auto from plan start) |
| `end_date` | string/null | `YYYY-MM` or null (auto-ends at Medicare eligibility age 65) |
| `change_over_time` | enum | How costs change annually |
| `change_rate` | number/null | Custom percentage |

**Post-Medicare** (per person):

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | `"primary"` or `"spouse"` |
| `medicare_start_date` | string/null | `YYYY-MM` or null (auto-calculated from birthday at age 65) |
| `part_b_monthly_premium` | number | Part B base premium |
| `supplement_monthly_premium` | number | Medigap or Medicare Advantage premium |
| `part_d_monthly_premium` | number | Part D premium |
| `annual_out_of_pocket` | number | Expected annual out-of-pocket |
| `change_over_time` | enum | How costs change annually |
| `change_rate` | number/null | Custom percentage |

**IRMAA** (Income-Related Monthly Adjustment Amount):

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether to model IRMAA surcharges |
| `lookback_years` | number | Years of income lookback for IRMAA (typically 2) |

The simulator uses MAGI from the lookback period to determine IRMAA surcharges on Part B and Part D premiums using current bracket thresholds.

---

### `real_assets`

```json
{
  "real_assets": [
    {
      "name": "Primary Home",
      "current_value": 500000,
      "purchase_price": 320000,
      "primary_residence": true,
      "change_over_time": "match_inflation",
      "change_rate": null,
      "property_tax_rate": 0.012,
      "mortgage": {
        "payment": 2500,
        "remaining_balance": 300000,
        "interest_rate": 0.035,
        "end_date": "2045-06"
      },
      "maintenance_expenses": [
        {
          "name": "General maintenance",
          "amount": 5000,
          "frequency": "annual"
        }
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `current_value` | number | Current market value |
| `purchase_price` | number | Original cost basis for gain calculations on sale |
| `primary_residence` | boolean | Whether this asset is eligible for primary residence gain exclusion |
| `change_over_time` | enum | `fixed`, `increase`, `match_inflation`, `inflation_plus`, `inflation_minus` |
| `change_rate` | number/null | Custom percentage |
| `property_tax_rate` | number | Annual tax rate as decimal |
| `mortgage` | object/null | Mortgage details (see sub-fields) |
| `maintenance_expenses` | array | Recurring maintenance costs |

Mortgage sub-fields: `payment` (monthly), `remaining_balance`, `interest_rate`, `end_date` (`YYYY-MM`).

Maintenance: `name`, `amount`, `frequency` (`monthly` or `annual`).

---

### `transactions`

Planned one-time transactions (sell an asset, large purchase, etc.).

```json
{
  "transactions": [
    {
      "name": "Sell rental property",
      "date": "2030-06",
      "type": "sell_asset",
      "amount": 400000,
      "fees": 24000,
      "tax_treatment": "capital_gains",
      "linked_asset": "Rental Property",
      "deposit_to_account": "Vanguard Taxable"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `date` | string | `YYYY-MM` |
| `type` | enum | `sell_asset`, `buy_asset`, `transfer`, `other` |
| `amount` | number | Gross dollar amount |
| `fees` | number | Fees in dollars |
| `tax_treatment` | enum | `capital_gains`, `income`, `tax_free` |
| `linked_asset` | string/null | Reference to a real asset name |
| `deposit_to_account` | string/null | Account name to deposit proceeds |

---

### `transfers`

Recurring transfers between accounts (e.g., rebalancing, Roth conversions).

```json
{
  "transfers": [
    {
      "name": "Annual Roth conversion",
      "from_account": "Traditional IRA",
      "to_account": "Roth IRA",
      "amount": 50000,
      "frequency": "annual",
      "start_date": "2026-01",
      "end_date": "2034-12",
      "tax_treatment": "income"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `from_account` | string | Source account name |
| `to_account` | string | Destination account name |
| `amount` | number | Transfer amount in dollars |
| `frequency` | enum | `monthly`, `annual`, `one_time` |
| `start_date` | string | `YYYY-MM` or `"start"` |
| `end_date` | string | `YYYY-MM` or `"end"` |
| `tax_treatment` | enum | `income` (e.g. Roth conversion), `capital_gains`, `tax_free` (e.g. Roth-to-Roth) |

---

### `withdrawal_strategy`

Specifies how the simulator draws down accounts to cover expenses when income is insufficient.

```json
{
  "withdrawal_strategy": {
    "order": [
      "cash",
      "taxable_brokerage",
      "traditional_ira",
      "401k",
      "roth_ira",
      "hsa"
    ],
    "account_specific_order": [
      "Ally Savings",
      "Vanguard Taxable",
      "Fidelity 401k",
      "Schwab Roth"
    ],
    "use_account_specific": true,
    "rmd_satisfied_first": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `order` | string[] | Default withdrawal order by account type |
| `account_specific_order` | string[] | Explicit account-by-account withdrawal order |
| `use_account_specific` | boolean | If true, use `account_specific_order` instead of `order` |
| `rmd_satisfied_first` | boolean | If true, RMD amounts are withdrawn before following the order |

---

### `roth_conversions`

Planned Roth conversion ladder strategy.

```json
{
  "roth_conversions": [
    {
      "name": "Bridge conversion",
      "from_account": "Traditional IRA",
      "to_account": "Roth IRA",
      "annual_amount": 50000,
      "start_date": "2030-01",
      "end_date": "2037-12",
      "fill_to_bracket": "22%"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Descriptive name |
| `from_account` | string | Traditional IRA or 401k account name |
| `to_account` | string | Roth IRA account name |
| `annual_amount` | number/null | Fixed annual conversion amount, or null if using `fill_to_bracket` |
| `start_date` | string | `YYYY-MM` |
| `end_date` | string | `YYYY-MM` |
| `fill_to_bracket` | string/null | Fill up to this marginal federal tax bracket (e.g. `"22%"`, `"24%"`), or null to use fixed amount |

---

### `rmds`

Required Minimum Distribution settings.

```json
{
  "rmds": {
    "enabled": true,
    "rmd_start_age": 73,
    "accounts": ["Fidelity 401k", "Traditional IRA"],
    "destination_account": "Ally Savings"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether to model RMDs |
| `rmd_start_age` | number | Age at which RMDs begin (currently 73, rising to 75) |
| `accounts` | string[] | Account names subject to RMDs |
| `destination_account` | string | Account where RMD proceeds are deposited |

The simulator uses IRS Uniform Lifetime Table divisors to calculate annual RMD amounts.
In v1, first-year RMD deferral to April 1 is not modeled; RMD is taken in December of the first required year.

---

### `tax_settings`

Detailed tax modeling configuration.

```json
{
  "tax_settings": {
    "use_current_brackets": true,
    "bracket_year": 2026,
    "federal_effective_rate_override": null,
    "state_effective_rate_override": null,
    "capital_gains_rate_override": null,
    "standard_deduction_override": null,
    "itemized_deductions": {
      "salt_cap": 10000,
      "mortgage_interest_deductible": true,
      "charitable_contributions": 5000
    },
    "niit_enabled": true,
    "amt_enabled": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `use_current_brackets` | boolean | Use built-in federal/state tax brackets |
| `bracket_year` | number | Which year's brackets to use as baseline |
| `federal_effective_rate_override` | number/null | Override with flat federal rate |
| `state_effective_rate_override` | number/null | Override with flat state rate |
| `capital_gains_rate_override` | number/null | Override capital gains rate |
| `standard_deduction_override` | number/null | Override standard deduction amount |
| `itemized_deductions` | object | Itemized deduction details |
| `niit_enabled` | boolean | Model Net Investment Income Tax (3.8%) |
| `amt_enabled` | boolean | Model Alternative Minimum Tax |

The simulator computes taxes using:
- Federal income tax brackets (ordinary income)
- Long-term capital gains brackets (0%, 15%, 20%)
- NIIT (3.8% on investment income above threshold)
- AMT (if enabled)
- State income tax (bracket-based per state, or flat override)
- FICA/self-employment tax where applicable
- Standard vs. itemized deduction (whichever is greater)

---

### `plan_settings`

```json
{
  "plan_settings": {
    "plan_start": "2026-01",
    "plan_end": "2065-12",
    "inflation_rate": 0.03,
    "default_dividend_tax_treatment": "capital_gains"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `plan_start` | string | Projection start date (`YYYY-MM`) |
| `plan_end` | string | Projection end date (`YYYY-MM`) |
| `inflation_rate` | number | Assumed annual inflation (e.g. 0.03 = 3%) |
| `default_dividend_tax_treatment` | enum | Default for accounts using `plan_settings` |

---

### `simulation_settings`

```json
{
  "simulation_settings": {
    "mode": "monte_carlo",
    "monte_carlo": {
      "num_simulations": 1000,
      "stock_mean_return": 0.10,
      "stock_std_dev": 0.18,
      "bond_mean_return": 0.04,
      "bond_std_dev": 0.06,
      "correlation": 0.2
    },
    "historical": {
      "start_year": 1926,
      "end_year": 2024,
      "use_rolling_periods": true
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mode` | enum | `deterministic`, `monte_carlo`, `historical` |

**Monte Carlo sub-fields:**

| Field | Type | Description |
|-------|------|-------------|
| `num_simulations` | number | Number of simulation runs |
| `stock_mean_return` | number | Mean annual stock return |
| `stock_std_dev` | number | Standard deviation of stock returns |
| `bond_mean_return` | number | Mean annual bond return |
| `bond_std_dev` | number | Standard deviation of bond returns |
| `correlation` | number | Stock-bond return correlation |

**Historical sub-fields:**

| Field | Type | Description |
|-------|------|-------------|
| `start_year` | number | Earliest year in historical dataset |
| `end_year` | number | Latest year in historical dataset |
| `use_rolling_periods` | boolean | Test all rolling N-year periods from the dataset |

---

## Simulation Semantics (Normative)

### Monthly Event Ordering

Each simulated month executes in this order:

1. Age calculation
2. Income collection (including Social Security after claiming starts)
3. FICA/self-employment tax withholding on employment income
4. Income tax withholding per `withhold_percent`
5. Payroll deductions (income-sourced contributions)
6. Employer match deposits
7. Other contributions
8. Recurring transfers
9. Roth conversions (fixed amount monthly; fill-to-bracket in December)
10. RMD processing (December only in applicable years)
11. Account growth (monthly geometric conversion from annual rates)
12. Dividends (reinvest or pay to cash)
13. Fees
14. Real asset updates (appreciation, mortgage amortization, maintenance)
15. One-time transactions (`sell_asset`, `buy_asset`, etc.)
16. Healthcare costs (pre/post-Medicare plus IRMAA surcharges)
17. Non-healthcare expenses
18. Shortfall detection and withdrawals by strategy
19. Expense payment from cash
20. Cost basis updates
21. Monthly flow recording

### Annual Events (December)

1. Full-year tax computation (federal, state, capital gains, NIIT, AMT, early withdrawal penalties)
2. Tax settlement versus cumulative withholding (refund or shortfall payment)
3. IRMAA MAGI capture for lookback application
4. Annual aggregation and notes

### Return Conversion Rules

- Deterministic mode converts annual growth/dividend/fee assumptions to monthly geometric rates.
- Monte Carlo and historical modes generate annual returns and apply equal geometric monthly rates within each year.

### Cash and Insolvency Rules

- At least one `cash` account is required.
- Income deposits, expense payments, and tax settlements route through cash.
- If cash is insufficient, withdrawal strategy is applied.
- If all eligible accounts are exhausted, insolvency is recorded and shown in output.

### Real Asset Sale Gain Rules

- For `sell_asset`, gain basis uses `purchase_price`.
- If `primary_residence` is true, primary residence gain exclusion is applied ($250K single / $500K MFJ).
- Depreciation modeling is out of scope in v1.

---

## Validation Rules (Normative)

Validation runs before simulation:

- Owner fields must be valid (`primary`/`spouse`; spouse must exist if referenced).
- All cross-references must resolve (accounts, assets, transaction links, transfer targets, RMD accounts).
- Date ranges must satisfy `start_date <= end_date`; `plan_start <= plan_end`.
- `cost_basis` must be non-null for `taxable_brokerage`.
- `withhold_percent` is required when `tax_handling == "withhold"`.
- `change_rate` is required for `increase`, `decrease`, `inflation_plus`, and `inflation_minus`.
- Filing status checks:
  - `married_filing_jointly`, `married_filing_separately`, and `qualifying_surviving_spouse` require spouse data.
  - `single` and `head_of_household` with spouse data emit a warning (not hard error).
- At least one `cash` account must exist.
- `rmds.accounts` must be tax-deferred accounts (`traditional_ira`, `401k`).
- Roth conversion `from_account` must be tax-deferred and `to_account` must be Roth.
- No duplicate account names or duplicate real asset names.
- Enum values must be from allowed sets.
- `purchase_price` is required on real assets referenced by `sell_asset` transactions.
- Errors must include actionable JSON-path context.

---

## Stated Simplifications

1. Taxable account holdings are treated as long-term capital gains.
2. Average cost basis is used (no lot-specific accounting).
3. No depreciation modeling for real assets.
4. First RMD is taken in December of first required year (no April 1 deferral).
5. Social Security spousal benefit uses a simplified dual-entitlement approximation.
6. AMT is modeled as a simplified approximation.
7. Monte Carlo/historical annual returns are spread uniformly across each month's geometric rate for that year.

---

## HTML Output

The generated HTML file is fully self-contained (inline CSS, inline JS, no external dependencies) and includes:

### Tabs and Views

1. **Overview** — key plan inputs (household, plan/simulation settings, accounts, income, expenses, additional settings) plus expandable normalized JSON.
2. **Annual Financials** — year-by-year consolidated table (income, expenses, taxes, withdrawals, contributions, transfers, net worth, notes) with inline per-cell breakdowns.
3. **Account Details** — single year-by-account matrix where each account cell shows ending balance with inline breakdown (start, growth, dividends, contributions, withdrawals, fees) when non-zero.
4. **Account Balance View** — monthly end-of-month balances for each account.
5. **Account Activity View** — monthly per-account balance deltas with inline per-cell reason breakdowns.
6. **Taxes** — monthly tax cash-flow table (FICA withheld, income tax withheld, estimated payments, settlement, net tax cash flow) with inline breakdowns.
7. **Calculation Log** — verbose month-by-month ledger of computed values and withdrawal sources.
8. **Plan Validation** — schema validation results and non-blocking sanity-check warnings.

## Tech Stack

- **Language**: Python 3.10+
- **Dependencies**: Minimal — standard library only where possible
- **Data format**: JSON input
- **Output**: Self-contained HTML file
