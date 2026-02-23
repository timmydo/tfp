"""Plan schema dataclasses and JSON loading."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


class SchemaError(ValueError):
    """Raised when raw JSON cannot be parsed into schema objects."""


def _expect_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaError(f"{path}: expected object")
    return value


def _expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise SchemaError(f"{path}: expected array")
    return value


def _require(data: dict[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise SchemaError(f"{path}.{key}: missing required field")
    return data[key]


def _optional(data: dict[str, Any], key: str, default: Any = None) -> Any:
    return data.get(key, default)


@dataclass(slots=True)
class Person:
    name: str
    birthday: str
    state: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str, require_state: bool) -> "Person":
        name = _require(data, "name", path)
        birthday = _require(data, "birthday", path)
        state = _optional(data, "state")
        if require_state and state is None:
            raise SchemaError(f"{path}.state: missing required field")
        return cls(name=name, birthday=birthday, state=state)


@dataclass(slots=True)
class People:
    primary: Person
    spouse: Person | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "people") -> "People":
        primary = Person.from_dict(_expect_dict(_require(data, "primary", path), f"{path}.primary"), f"{path}.primary", True)
        spouse_raw = _optional(data, "spouse")
        spouse = None
        if spouse_raw is not None:
            spouse = Person.from_dict(_expect_dict(spouse_raw, f"{path}.spouse"), f"{path}.spouse", False)
        return cls(primary=primary, spouse=spouse)


@dataclass(slots=True)
class Account:
    name: str
    type: str
    owner: str
    balance: float
    cost_basis: float | None
    growth_rate: float
    dividend_yield: float
    dividend_tax_treatment: str
    reinvest_dividends: bool
    bond_allocation_percent: float
    yearly_fees: float
    allow_withdrawals: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Account":
        return cls(
            name=_require(data, "name", path),
            type=_require(data, "type", path),
            owner=_require(data, "owner", path),
            balance=float(_require(data, "balance", path)),
            cost_basis=_optional(data, "cost_basis"),
            growth_rate=float(_require(data, "growth_rate", path)),
            dividend_yield=float(_require(data, "dividend_yield", path)),
            dividend_tax_treatment=_require(data, "dividend_tax_treatment", path),
            reinvest_dividends=bool(_require(data, "reinvest_dividends", path)),
            bond_allocation_percent=float(_require(data, "bond_allocation_percent", path)),
            yearly_fees=float(_require(data, "yearly_fees", path)),
            allow_withdrawals=bool(_require(data, "allow_withdrawals", path)),
        )


@dataclass(slots=True)
class EmployerMatch:
    match_percent: float
    up_to_percent_of_salary: float
    salary_reference: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "EmployerMatch":
        return cls(
            match_percent=float(_require(data, "match_percent", path)),
            up_to_percent_of_salary=float(_require(data, "up_to_percent_of_salary", path)),
            salary_reference=_require(data, "salary_reference", path),
        )


@dataclass(slots=True)
class Contribution:
    name: str
    source_account: str
    destination_account: str
    amount: float
    frequency: str
    start_date: str
    end_date: str
    change_over_time: str
    change_rate: float | None
    employer_match: EmployerMatch | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Contribution":
        employer_match_raw = _optional(data, "employer_match")
        employer_match = None
        if employer_match_raw is not None:
            employer_match = EmployerMatch.from_dict(_expect_dict(employer_match_raw, f"{path}.employer_match"), f"{path}.employer_match")
        change_rate = _optional(data, "change_rate")
        return cls(
            name=_require(data, "name", path),
            source_account=_require(data, "source_account", path),
            destination_account=_require(data, "destination_account", path),
            amount=float(_require(data, "amount", path)),
            frequency=_require(data, "frequency", path),
            start_date=_require(data, "start_date", path),
            end_date=_require(data, "end_date", path),
            change_over_time=_require(data, "change_over_time", path),
            change_rate=float(change_rate) if change_rate is not None else None,
            employer_match=employer_match,
        )


@dataclass(slots=True)
class Income:
    name: str
    owner: str
    amount: float
    frequency: str
    start_date: str
    end_date: str
    change_over_time: str
    change_rate: float | None
    tax_handling: str
    withhold_percent: float | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Income":
        change_rate = _optional(data, "change_rate")
        withhold_percent = _optional(data, "withhold_percent")
        return cls(
            name=_require(data, "name", path),
            owner=_require(data, "owner", path),
            amount=float(_require(data, "amount", path)),
            frequency=_require(data, "frequency", path),
            start_date=_require(data, "start_date", path),
            end_date=_require(data, "end_date", path),
            change_over_time=_require(data, "change_over_time", path),
            change_rate=float(change_rate) if change_rate is not None else None,
            tax_handling=_require(data, "tax_handling", path),
            withhold_percent=float(withhold_percent) if withhold_percent is not None else None,
        )


@dataclass(slots=True)
class Expense:
    name: str
    owner: str
    amount: float
    frequency: str
    start_date: str
    end_date: str
    change_over_time: str
    change_rate: float | None
    spending_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Expense":
        change_rate = _optional(data, "change_rate")
        return cls(
            name=_require(data, "name", path),
            owner=_require(data, "owner", path),
            amount=float(_require(data, "amount", path)),
            frequency=_require(data, "frequency", path),
            start_date=_require(data, "start_date", path),
            end_date=_require(data, "end_date", path),
            change_over_time=_require(data, "change_over_time", path),
            change_rate=float(change_rate) if change_rate is not None else None,
            spending_type=_require(data, "spending_type", path),
        )


@dataclass(slots=True)
class SocialSecurity:
    owner: str
    pia_at_fra: float
    fra_age_years: int
    fra_age_months: int
    claiming_age_years: int
    claiming_age_months: int
    cola_assumption: str
    cola_rate: float | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "SocialSecurity":
        cola_rate = _optional(data, "cola_rate")
        return cls(
            owner=_require(data, "owner", path),
            pia_at_fra=float(_require(data, "pia_at_fra", path)),
            fra_age_years=int(_require(data, "fra_age_years", path)),
            fra_age_months=int(_require(data, "fra_age_months", path)),
            claiming_age_years=int(_require(data, "claiming_age_years", path)),
            claiming_age_months=int(_require(data, "claiming_age_months", path)),
            cola_assumption=_require(data, "cola_assumption", path),
            cola_rate=float(cola_rate) if cola_rate is not None else None,
        )


@dataclass(slots=True)
class HealthcarePreMedicare:
    owner: str
    monthly_premium: float
    annual_out_of_pocket: float
    start_date: str | None
    end_date: str | None
    change_over_time: str
    change_rate: float | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "HealthcarePreMedicare":
        change_rate = _optional(data, "change_rate")
        return cls(
            owner=_require(data, "owner", path),
            monthly_premium=float(_require(data, "monthly_premium", path)),
            annual_out_of_pocket=float(_require(data, "annual_out_of_pocket", path)),
            start_date=_optional(data, "start_date"),
            end_date=_optional(data, "end_date"),
            change_over_time=_require(data, "change_over_time", path),
            change_rate=float(change_rate) if change_rate is not None else None,
        )


@dataclass(slots=True)
class HealthcarePostMedicare:
    owner: str
    medicare_start_date: str | None
    part_b_monthly_premium: float
    supplement_monthly_premium: float
    part_d_monthly_premium: float
    annual_out_of_pocket: float
    change_over_time: str
    change_rate: float | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "HealthcarePostMedicare":
        change_rate = _optional(data, "change_rate")
        return cls(
            owner=_require(data, "owner", path),
            medicare_start_date=_optional(data, "medicare_start_date"),
            part_b_monthly_premium=float(_require(data, "part_b_monthly_premium", path)),
            supplement_monthly_premium=float(_require(data, "supplement_monthly_premium", path)),
            part_d_monthly_premium=float(_require(data, "part_d_monthly_premium", path)),
            annual_out_of_pocket=float(_require(data, "annual_out_of_pocket", path)),
            change_over_time=_require(data, "change_over_time", path),
            change_rate=float(change_rate) if change_rate is not None else None,
        )


@dataclass(slots=True)
class IRMAASettings:
    enabled: bool
    lookback_years: int

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "IRMAASettings":
        return cls(
            enabled=bool(_require(data, "enabled", path)),
            lookback_years=int(_require(data, "lookback_years", path)),
        )


@dataclass(slots=True)
class Healthcare:
    pre_medicare: list[HealthcarePreMedicare] = field(default_factory=list)
    post_medicare: list[HealthcarePostMedicare] = field(default_factory=list)
    irmaa: IRMAASettings = field(default_factory=lambda: IRMAASettings(enabled=True, lookback_years=2))

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "healthcare") -> "Healthcare":
        pre_medicare = [
            HealthcarePreMedicare.from_dict(_expect_dict(item, f"{path}.pre_medicare[{idx}]"), f"{path}.pre_medicare[{idx}]")
            for idx, item in enumerate(_expect_list(_optional(data, "pre_medicare", []), f"{path}.pre_medicare"))
        ]
        post_medicare = [
            HealthcarePostMedicare.from_dict(_expect_dict(item, f"{path}.post_medicare[{idx}]"), f"{path}.post_medicare[{idx}]")
            for idx, item in enumerate(_expect_list(_optional(data, "post_medicare", []), f"{path}.post_medicare"))
        ]
        irmaa_raw = _optional(data, "irmaa", {"enabled": True, "lookback_years": 2})
        irmaa = IRMAASettings.from_dict(_expect_dict(irmaa_raw, f"{path}.irmaa"), f"{path}.irmaa")
        return cls(pre_medicare=pre_medicare, post_medicare=post_medicare, irmaa=irmaa)


@dataclass(slots=True)
class Mortgage:
    payment: float
    remaining_balance: float
    interest_rate: float
    end_date: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Mortgage":
        return cls(
            payment=float(_require(data, "payment", path)),
            remaining_balance=float(_require(data, "remaining_balance", path)),
            interest_rate=float(_require(data, "interest_rate", path)),
            end_date=_require(data, "end_date", path),
        )


@dataclass(slots=True)
class MaintenanceExpense:
    name: str
    amount: float
    frequency: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "MaintenanceExpense":
        return cls(
            name=_require(data, "name", path),
            amount=float(_require(data, "amount", path)),
            frequency=_require(data, "frequency", path),
        )


@dataclass(slots=True)
class RealAsset:
    name: str
    current_value: float
    purchase_price: float | None
    primary_residence: bool
    change_over_time: str
    change_rate: float | None
    property_tax_rate: float
    mortgage: Mortgage | None
    maintenance_expenses: list[MaintenanceExpense]

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "RealAsset":
        mortgage_raw = _optional(data, "mortgage")
        mortgage = None
        if mortgage_raw is not None:
            mortgage = Mortgage.from_dict(_expect_dict(mortgage_raw, f"{path}.mortgage"), f"{path}.mortgage")
        change_rate = _optional(data, "change_rate")
        maintenance_expenses = [
            MaintenanceExpense.from_dict(_expect_dict(item, f"{path}.maintenance_expenses[{idx}]"), f"{path}.maintenance_expenses[{idx}]")
            for idx, item in enumerate(_expect_list(_optional(data, "maintenance_expenses", []), f"{path}.maintenance_expenses"))
        ]
        return cls(
            name=_require(data, "name", path),
            current_value=float(_require(data, "current_value", path)),
            purchase_price=float(_optional(data, "purchase_price")) if _optional(data, "purchase_price") is not None else None,
            primary_residence=bool(_require(data, "primary_residence", path)),
            change_over_time=_require(data, "change_over_time", path),
            change_rate=float(change_rate) if change_rate is not None else None,
            property_tax_rate=float(_require(data, "property_tax_rate", path)),
            mortgage=mortgage,
            maintenance_expenses=maintenance_expenses,
        )


@dataclass(slots=True)
class Transaction:
    name: str
    date: str
    type: str
    amount: float
    fees: float
    tax_treatment: str
    linked_asset: str | None
    deposit_to_account: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Transaction":
        return cls(
            name=_require(data, "name", path),
            date=_require(data, "date", path),
            type=_require(data, "type", path),
            amount=float(_require(data, "amount", path)),
            fees=float(_require(data, "fees", path)),
            tax_treatment=_require(data, "tax_treatment", path),
            linked_asset=_optional(data, "linked_asset"),
            deposit_to_account=_optional(data, "deposit_to_account"),
        )


@dataclass(slots=True)
class Transfer:
    name: str
    from_account: str
    to_account: str
    amount: float
    frequency: str
    start_date: str
    end_date: str
    tax_treatment: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "Transfer":
        return cls(
            name=_require(data, "name", path),
            from_account=_require(data, "from_account", path),
            to_account=_require(data, "to_account", path),
            amount=float(_require(data, "amount", path)),
            frequency=_require(data, "frequency", path),
            start_date=_require(data, "start_date", path),
            end_date=_require(data, "end_date", path),
            tax_treatment=_require(data, "tax_treatment", path),
        )


@dataclass(slots=True)
class WithdrawalStrategy:
    order: list[str]
    account_specific_order: list[str]
    use_account_specific: bool
    rmd_satisfied_first: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "withdrawal_strategy") -> "WithdrawalStrategy":
        return cls(
            order=list(_optional(data, "order", [])),
            account_specific_order=list(_optional(data, "account_specific_order", [])),
            use_account_specific=bool(_optional(data, "use_account_specific", False)),
            rmd_satisfied_first=bool(_optional(data, "rmd_satisfied_first", True)),
        )


@dataclass(slots=True)
class RothConversion:
    name: str
    from_account: str
    to_account: str
    annual_amount: float | None
    start_date: str
    end_date: str
    fill_to_bracket: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "RothConversion":
        annual_amount = _optional(data, "annual_amount")
        return cls(
            name=_require(data, "name", path),
            from_account=_require(data, "from_account", path),
            to_account=_require(data, "to_account", path),
            annual_amount=float(annual_amount) if annual_amount is not None else None,
            start_date=_require(data, "start_date", path),
            end_date=_require(data, "end_date", path),
            fill_to_bracket=_optional(data, "fill_to_bracket"),
        )


@dataclass(slots=True)
class RMDSettings:
    enabled: bool
    rmd_start_age: int
    accounts: list[str]
    destination_account: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "rmds") -> "RMDSettings":
        return cls(
            enabled=bool(_optional(data, "enabled", False)),
            rmd_start_age=int(_optional(data, "rmd_start_age", 73)),
            accounts=list(_optional(data, "accounts", [])),
            destination_account=_optional(data, "destination_account"),
        )


@dataclass(slots=True)
class ItemizedDeductions:
    salt_cap: float
    mortgage_interest_deductible: bool
    charitable_contributions: float

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "ItemizedDeductions":
        return cls(
            salt_cap=float(_optional(data, "salt_cap", 10000)),
            mortgage_interest_deductible=bool(_optional(data, "mortgage_interest_deductible", True)),
            charitable_contributions=float(_optional(data, "charitable_contributions", 0.0)),
        )


@dataclass(slots=True)
class TaxSettings:
    use_current_brackets: bool
    bracket_year: int
    federal_effective_rate_override: float | None
    state_effective_rate_override: float | None
    capital_gains_rate_override: float | None
    standard_deduction_override: float | None
    itemized_deductions: ItemizedDeductions
    niit_enabled: bool
    amt_enabled: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "tax_settings") -> "TaxSettings":
        itemized_raw = _optional(data, "itemized_deductions", {})
        return cls(
            use_current_brackets=bool(_optional(data, "use_current_brackets", True)),
            bracket_year=int(_optional(data, "bracket_year", 2026)),
            federal_effective_rate_override=_optional(data, "federal_effective_rate_override"),
            state_effective_rate_override=_optional(data, "state_effective_rate_override"),
            capital_gains_rate_override=_optional(data, "capital_gains_rate_override"),
            standard_deduction_override=_optional(data, "standard_deduction_override"),
            itemized_deductions=ItemizedDeductions.from_dict(_expect_dict(itemized_raw, f"{path}.itemized_deductions"), f"{path}.itemized_deductions"),
            niit_enabled=bool(_optional(data, "niit_enabled", True)),
            amt_enabled=bool(_optional(data, "amt_enabled", True)),
        )


@dataclass(slots=True)
class PlanSettings:
    plan_start: str
    plan_end: str
    inflation_rate: float
    default_dividend_tax_treatment: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "plan_settings") -> "PlanSettings":
        return cls(
            plan_start=_require(data, "plan_start", path),
            plan_end=_require(data, "plan_end", path),
            inflation_rate=float(_require(data, "inflation_rate", path)),
            default_dividend_tax_treatment=_require(data, "default_dividend_tax_treatment", path),
        )


@dataclass(slots=True)
class MonteCarloSettings:
    num_simulations: int
    stock_mean_return: float
    stock_std_dev: float
    bond_mean_return: float
    bond_std_dev: float
    correlation: float

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "MonteCarloSettings":
        return cls(
            num_simulations=int(_optional(data, "num_simulations", 1000)),
            stock_mean_return=float(_optional(data, "stock_mean_return", 0.1)),
            stock_std_dev=float(_optional(data, "stock_std_dev", 0.18)),
            bond_mean_return=float(_optional(data, "bond_mean_return", 0.04)),
            bond_std_dev=float(_optional(data, "bond_std_dev", 0.06)),
            correlation=float(_optional(data, "correlation", 0.2)),
        )


@dataclass(slots=True)
class HistoricalSettings:
    start_year: int
    end_year: int
    use_rolling_periods: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str) -> "HistoricalSettings":
        return cls(
            start_year=int(_optional(data, "start_year", 1926)),
            end_year=int(_optional(data, "end_year", 2024)),
            use_rolling_periods=bool(_optional(data, "use_rolling_periods", True)),
        )


@dataclass(slots=True)
class SimulationSettings:
    mode: str
    monte_carlo: MonteCarloSettings
    historical: HistoricalSettings

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str = "simulation_settings") -> "SimulationSettings":
        mc = MonteCarloSettings.from_dict(
            _expect_dict(_optional(data, "monte_carlo", {}), f"{path}.monte_carlo"),
            f"{path}.monte_carlo",
        )
        hist = HistoricalSettings.from_dict(
            _expect_dict(_optional(data, "historical", {}), f"{path}.historical"),
            f"{path}.historical",
        )
        return cls(mode=_optional(data, "mode", "deterministic"), monte_carlo=mc, historical=hist)


@dataclass(slots=True)
class Plan:
    people: People
    filing_status: str
    accounts: list[Account]
    contributions: list[Contribution]
    income: list[Income]
    expenses: list[Expense]
    social_security: list[SocialSecurity]
    healthcare: Healthcare
    real_assets: list[RealAsset]
    transactions: list[Transaction]
    transfers: list[Transfer]
    withdrawal_strategy: WithdrawalStrategy
    roth_conversions: list[RothConversion]
    rmds: RMDSettings
    tax_settings: TaxSettings
    plan_settings: PlanSettings
    simulation_settings: SimulationSettings

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            people=People.from_dict(_expect_dict(_require(data, "people", "plan"), "people")),
            filing_status=_require(data, "filing_status", "plan"),
            accounts=[
                Account.from_dict(_expect_dict(item, f"accounts[{idx}]"), f"accounts[{idx}]")
                for idx, item in enumerate(_expect_list(_require(data, "accounts", "plan"), "accounts"))
            ],
            contributions=[
                Contribution.from_dict(_expect_dict(item, f"contributions[{idx}]"), f"contributions[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "contributions", []), "contributions"))
            ],
            income=[
                Income.from_dict(_expect_dict(item, f"income[{idx}]"), f"income[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "income", []), "income"))
            ],
            expenses=[
                Expense.from_dict(_expect_dict(item, f"expenses[{idx}]"), f"expenses[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "expenses", []), "expenses"))
            ],
            social_security=[
                SocialSecurity.from_dict(_expect_dict(item, f"social_security[{idx}]"), f"social_security[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "social_security", []), "social_security"))
            ],
            healthcare=Healthcare.from_dict(_expect_dict(_optional(data, "healthcare", {}), "healthcare")),
            real_assets=[
                RealAsset.from_dict(_expect_dict(item, f"real_assets[{idx}]"), f"real_assets[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "real_assets", []), "real_assets"))
            ],
            transactions=[
                Transaction.from_dict(_expect_dict(item, f"transactions[{idx}]"), f"transactions[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "transactions", []), "transactions"))
            ],
            transfers=[
                Transfer.from_dict(_expect_dict(item, f"transfers[{idx}]"), f"transfers[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "transfers", []), "transfers"))
            ],
            withdrawal_strategy=WithdrawalStrategy.from_dict(
                _expect_dict(_optional(data, "withdrawal_strategy", {}), "withdrawal_strategy")
            ),
            roth_conversions=[
                RothConversion.from_dict(_expect_dict(item, f"roth_conversions[{idx}]"), f"roth_conversions[{idx}]")
                for idx, item in enumerate(_expect_list(_optional(data, "roth_conversions", []), "roth_conversions"))
            ],
            rmds=RMDSettings.from_dict(_expect_dict(_optional(data, "rmds", {}), "rmds")),
            tax_settings=TaxSettings.from_dict(_expect_dict(_optional(data, "tax_settings", {}), "tax_settings")),
            plan_settings=PlanSettings.from_dict(_expect_dict(_require(data, "plan_settings", "plan"), "plan_settings")),
            simulation_settings=SimulationSettings.from_dict(
                _expect_dict(_optional(data, "simulation_settings", {}), "simulation_settings")
            ),
        )


def load_plan(path: str | Path) -> Plan:
    """Load plan JSON into strongly-typed dataclasses."""
    source = Path(path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SchemaError("plan: root must be a JSON object")
    return Plan.from_dict(raw)
