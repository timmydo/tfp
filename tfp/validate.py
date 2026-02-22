"""Semantic and cross-reference validation for plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Iterable

from .schema import Plan

DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
SPECIAL_DATES = {"start", "end"}

ACCOUNT_TYPES = {
    "cash",
    "taxable_brokerage",
    "401k",
    "traditional_ira",
    "roth_ira",
    "hsa",
    "529",
    "other",
}

FILING_STATUS = {
    "single",
    "married_filing_jointly",
    "married_filing_separately",
    "head_of_household",
    "qualifying_surviving_spouse",
}

CHANGE_OVER_TIME = {
    "fixed",
    "increase",
    "decrease",
    "match_inflation",
    "inflation_plus",
    "inflation_minus",
}

REQUIRES_CHANGE_RATE = {"increase", "decrease", "inflation_plus", "inflation_minus"}

FREQUENCY_BASIC = {"monthly", "annual"}
FREQUENCY_EXTENDED = {"monthly", "annual", "one_time"}

DIVIDEND_TAX_TREATMENT = {"tax_free", "income", "capital_gains", "plan_settings"}
INCOME_TAX_HANDLING = {"withhold", "tax_exempt"}
SPENDING_TYPE = {"essential", "discretionary"}
OWNER_PRIMARY_SPOUSE = {"primary", "spouse"}
OWNER_WITH_JOINT = {"primary", "spouse", "joint"}
COLA_ASSUMPTION = {"fixed", "match_inflation", "inflation_plus", "inflation_minus"}
TRANSACTION_TYPE = {"sell_asset", "buy_asset", "transfer", "other"}
TAX_TREATMENT = {"capital_gains", "income", "tax_free"}
SIM_MODES = {"deterministic", "monte_carlo", "historical"}


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _is_date_token(value: str | None) -> bool:
    if value is None:
        return False
    return value in SPECIAL_DATES or bool(DATE_RE.match(value))


def _date_to_ordinal(value: str, plan_start: str, plan_end: str) -> int:
    token = value
    if token == "start":
        token = plan_start
    elif token == "end":
        token = plan_end
    dt = datetime.strptime(token, "%Y-%m")
    return dt.year * 12 + dt.month


def _check_enum(result: ValidationResult, path: str, value: str, allowed: Iterable[str]) -> None:
    allowed_set = set(allowed)
    if value not in allowed_set:
        expected = ", ".join(sorted(allowed_set))
        result.errors.append(f"{path}: '{value}' is not valid; expected one of [{expected}]")


def _check_owner(result: ValidationResult, path: str, value: str, spouse_exists: bool, allow_joint: bool) -> None:
    allowed = OWNER_WITH_JOINT if allow_joint else OWNER_PRIMARY_SPOUSE
    if value not in allowed:
        expected = ", ".join(sorted(allowed))
        result.errors.append(f"{path}: '{value}' is not valid; expected one of [{expected}]")
    elif value == "spouse" and not spouse_exists:
        result.errors.append(f"{path}: references spouse, but people.spouse is missing")


def _check_date(result: ValidationResult, path: str, value: str | None, allow_null: bool = False) -> None:
    if value is None:
        if not allow_null:
            result.errors.append(f"{path}: date is required")
        return
    if not _is_date_token(value):
        result.errors.append(f"{path}: '{value}' is not valid; expected YYYY-MM or start/end")


def _check_date_range(result: ValidationResult, start_path: str, start: str, end_path: str, end: str, plan_start: str, plan_end: str) -> None:
    if not _is_date_token(start) or not _is_date_token(end):
        return
    if _date_to_ordinal(start, plan_start, plan_end) > _date_to_ordinal(end, plan_start, plan_end):
        result.errors.append(f"{start_path}/{end_path}: start_date must be <= end_date")


def validate_plan(plan: Plan) -> ValidationResult:
    result = ValidationResult()
    spouse_exists = plan.people.spouse is not None

    _check_enum(result, "filing_status", plan.filing_status, FILING_STATUS)
    if plan.filing_status in {
        "married_filing_jointly",
        "married_filing_separately",
        "qualifying_surviving_spouse",
    } and not spouse_exists:
        result.errors.append(f"filing_status: '{plan.filing_status}' requires people.spouse")
    if plan.filing_status in {"single", "head_of_household"} and spouse_exists:
        result.warnings.append(
            f"filing_status: '{plan.filing_status}' with people.spouse present is unusual but allowed"
        )

    _check_date(result, "plan_settings.plan_start", plan.plan_settings.plan_start)
    _check_date(result, "plan_settings.plan_end", plan.plan_settings.plan_end)
    if _is_date_token(plan.plan_settings.plan_start) and _is_date_token(plan.plan_settings.plan_end):
        if _date_to_ordinal(plan.plan_settings.plan_start, plan.plan_settings.plan_start, plan.plan_settings.plan_end) > _date_to_ordinal(plan.plan_settings.plan_end, plan.plan_settings.plan_start, plan.plan_settings.plan_end):
            result.errors.append("plan_settings.plan_start/plan_settings.plan_end: plan_start must be <= plan_end")

    account_names: set[str] = set()
    asset_names: set[str] = set()

    for idx, account in enumerate(plan.accounts):
        base = f"accounts[{idx}]"
        if account.name in account_names:
            result.errors.append(f"{base}.name: duplicate account name '{account.name}'")
        account_names.add(account.name)

        _check_enum(result, f"{base}.type", account.type, ACCOUNT_TYPES)
        _check_owner(result, f"{base}.owner", account.owner, spouse_exists, allow_joint=False)
        _check_enum(result, f"{base}.dividend_tax_treatment", account.dividend_tax_treatment, DIVIDEND_TAX_TREATMENT)
        if account.type == "taxable_brokerage" and account.cost_basis is None:
            result.errors.append(f"{base}.cost_basis: required for taxable_brokerage accounts")

    if not any(a.type == "cash" for a in plan.accounts):
        result.errors.append("accounts: at least one cash account is required")

    for idx, item in enumerate(plan.contributions):
        base = f"contributions[{idx}]"
        if item.source_account != "income" and item.source_account not in account_names:
            result.errors.append(f"{base}.source_account: '{item.source_account}' does not match any account name")
        if item.destination_account not in account_names:
            result.errors.append(f"{base}.destination_account: '{item.destination_account}' does not match any account name")
        _check_enum(result, f"{base}.frequency", item.frequency, FREQUENCY_BASIC)
        _check_enum(result, f"{base}.change_over_time", item.change_over_time, CHANGE_OVER_TIME)
        if item.change_over_time in REQUIRES_CHANGE_RATE and item.change_rate is None:
            result.errors.append(f"{base}.change_rate: required when change_over_time is '{item.change_over_time}'")
        _check_date(result, f"{base}.start_date", item.start_date)
        _check_date(result, f"{base}.end_date", item.end_date)
        _check_date_range(
            result,
            f"{base}.start_date",
            item.start_date,
            f"{base}.end_date",
            item.end_date,
            plan.plan_settings.plan_start,
            plan.plan_settings.plan_end,
        )
        if item.employer_match and not any(i.name == item.employer_match.salary_reference for i in plan.income):
            result.errors.append(
                f"{base}.employer_match.salary_reference: '{item.employer_match.salary_reference}' does not match any income name"
            )

    for idx, item in enumerate(plan.income):
        base = f"income[{idx}]"
        _check_owner(result, f"{base}.owner", item.owner, spouse_exists, allow_joint=False)
        _check_enum(result, f"{base}.frequency", item.frequency, FREQUENCY_EXTENDED)
        _check_enum(result, f"{base}.change_over_time", item.change_over_time, CHANGE_OVER_TIME)
        _check_enum(result, f"{base}.tax_handling", item.tax_handling, INCOME_TAX_HANDLING)
        if item.tax_handling == "withhold" and item.withhold_percent is None:
            result.errors.append(f"{base}.withhold_percent: required when tax_handling is 'withhold'")
        if item.change_over_time in REQUIRES_CHANGE_RATE and item.change_rate is None:
            result.errors.append(f"{base}.change_rate: required when change_over_time is '{item.change_over_time}'")
        _check_date(result, f"{base}.start_date", item.start_date)
        _check_date(result, f"{base}.end_date", item.end_date)
        _check_date_range(
            result,
            f"{base}.start_date",
            item.start_date,
            f"{base}.end_date",
            item.end_date,
            plan.plan_settings.plan_start,
            plan.plan_settings.plan_end,
        )

    for idx, item in enumerate(plan.expenses):
        base = f"expenses[{idx}]"
        _check_owner(result, f"{base}.owner", item.owner, spouse_exists, allow_joint=True)
        _check_enum(result, f"{base}.frequency", item.frequency, FREQUENCY_EXTENDED)
        _check_enum(result, f"{base}.change_over_time", item.change_over_time, CHANGE_OVER_TIME)
        _check_enum(result, f"{base}.spending_type", item.spending_type, SPENDING_TYPE)
        if item.change_over_time in REQUIRES_CHANGE_RATE and item.change_rate is None:
            result.errors.append(f"{base}.change_rate: required when change_over_time is '{item.change_over_time}'")
        _check_date(result, f"{base}.start_date", item.start_date)
        _check_date(result, f"{base}.end_date", item.end_date)
        _check_date_range(
            result,
            f"{base}.start_date",
            item.start_date,
            f"{base}.end_date",
            item.end_date,
            plan.plan_settings.plan_start,
            plan.plan_settings.plan_end,
        )

    for idx, item in enumerate(plan.social_security):
        base = f"social_security[{idx}]"
        _check_owner(result, f"{base}.owner", item.owner, spouse_exists, allow_joint=False)
        _check_enum(result, f"{base}.cola_assumption", item.cola_assumption, COLA_ASSUMPTION)
        if item.cola_assumption in {"inflation_plus", "inflation_minus"} and item.cola_rate is None:
            result.errors.append(f"{base}.cola_rate: required when cola_assumption is '{item.cola_assumption}'")

    for idx, item in enumerate(plan.healthcare.pre_medicare):
        base = f"healthcare.pre_medicare[{idx}]"
        _check_owner(result, f"{base}.owner", item.owner, spouse_exists, allow_joint=False)
        _check_enum(result, f"{base}.change_over_time", item.change_over_time, CHANGE_OVER_TIME)
        if item.change_over_time in REQUIRES_CHANGE_RATE and item.change_rate is None:
            result.errors.append(f"{base}.change_rate: required when change_over_time is '{item.change_over_time}'")
        _check_date(result, f"{base}.start_date", item.start_date, allow_null=True)
        _check_date(result, f"{base}.end_date", item.end_date, allow_null=True)

    for idx, item in enumerate(plan.healthcare.post_medicare):
        base = f"healthcare.post_medicare[{idx}]"
        _check_owner(result, f"{base}.owner", item.owner, spouse_exists, allow_joint=False)
        _check_enum(result, f"{base}.change_over_time", item.change_over_time, CHANGE_OVER_TIME)
        if item.change_over_time in REQUIRES_CHANGE_RATE and item.change_rate is None:
            result.errors.append(f"{base}.change_rate: required when change_over_time is '{item.change_over_time}'")
        _check_date(result, f"{base}.medicare_start_date", item.medicare_start_date, allow_null=True)

    for idx, asset in enumerate(plan.real_assets):
        base = f"real_assets[{idx}]"
        if asset.name in asset_names:
            result.errors.append(f"{base}.name: duplicate real asset name '{asset.name}'")
        asset_names.add(asset.name)
        _check_enum(result, f"{base}.change_over_time", asset.change_over_time, CHANGE_OVER_TIME)
        if asset.change_over_time in REQUIRES_CHANGE_RATE and asset.change_rate is None:
            result.errors.append(f"{base}.change_rate: required when change_over_time is '{asset.change_over_time}'")
        for midx, mexp in enumerate(asset.maintenance_expenses):
            _check_enum(result, f"{base}.maintenance_expenses[{midx}].frequency", mexp.frequency, FREQUENCY_BASIC)

    for idx, txn in enumerate(plan.transactions):
        base = f"transactions[{idx}]"
        _check_date(result, f"{base}.date", txn.date)
        _check_enum(result, f"{base}.type", txn.type, TRANSACTION_TYPE)
        _check_enum(result, f"{base}.tax_treatment", txn.tax_treatment, TAX_TREATMENT)
        if txn.linked_asset and txn.linked_asset not in asset_names:
            result.errors.append(f"{base}.linked_asset: '{txn.linked_asset}' does not match any real asset name")
        if txn.deposit_to_account and txn.deposit_to_account not in account_names:
            result.errors.append(f"{base}.deposit_to_account: '{txn.deposit_to_account}' does not match any account name")
        if txn.type == "sell_asset" and txn.linked_asset:
            referenced = next((a for a in plan.real_assets if a.name == txn.linked_asset), None)
            if referenced is not None and referenced.purchase_price is None:
                result.errors.append(
                    f"real_assets[{idx}].purchase_price: required for assets referenced by sell_asset transactions"
                )

    for idx, transfer in enumerate(plan.transfers):
        base = f"transfers[{idx}]"
        if transfer.from_account not in account_names:
            result.errors.append(f"{base}.from_account: '{transfer.from_account}' does not match any account name")
        if transfer.to_account not in account_names:
            result.errors.append(f"{base}.to_account: '{transfer.to_account}' does not match any account name")
        _check_enum(result, f"{base}.frequency", transfer.frequency, FREQUENCY_EXTENDED)
        _check_enum(result, f"{base}.tax_treatment", transfer.tax_treatment, TAX_TREATMENT)
        _check_date(result, f"{base}.start_date", transfer.start_date)
        _check_date(result, f"{base}.end_date", transfer.end_date)
        _check_date_range(
            result,
            f"{base}.start_date",
            transfer.start_date,
            f"{base}.end_date",
            transfer.end_date,
            plan.plan_settings.plan_start,
            plan.plan_settings.plan_end,
        )

    for idx, conversion in enumerate(plan.roth_conversions):
        base = f"roth_conversions[{idx}]"
        _check_date(result, f"{base}.start_date", conversion.start_date)
        _check_date(result, f"{base}.end_date", conversion.end_date)
        _check_date_range(
            result,
            f"{base}.start_date",
            conversion.start_date,
            f"{base}.end_date",
            conversion.end_date,
            plan.plan_settings.plan_start,
            plan.plan_settings.plan_end,
        )
        src = next((a for a in plan.accounts if a.name == conversion.from_account), None)
        dst = next((a for a in plan.accounts if a.name == conversion.to_account), None)
        if src is None:
            result.errors.append(f"{base}.from_account: '{conversion.from_account}' does not match any account name")
        elif src.type not in {"traditional_ira", "401k"}:
            result.errors.append(f"{base}.from_account: must be traditional_ira or 401k")
        if dst is None:
            result.errors.append(f"{base}.to_account: '{conversion.to_account}' does not match any account name")
        elif dst.type != "roth_ira":
            result.errors.append(f"{base}.to_account: must be roth_ira")

    if plan.withdrawal_strategy.use_account_specific:
        for idx, name in enumerate(plan.withdrawal_strategy.account_specific_order):
            if name not in account_names:
                result.errors.append(
                    f"withdrawal_strategy.account_specific_order[{idx}]: '{name}' does not match any account name"
                )
    else:
        for idx, kind in enumerate(plan.withdrawal_strategy.order):
            _check_enum(result, f"withdrawal_strategy.order[{idx}]", kind, ACCOUNT_TYPES)

    _check_enum(result, "simulation_settings.mode", plan.simulation_settings.mode, SIM_MODES)

    if plan.rmds.enabled:
        for idx, name in enumerate(plan.rmds.accounts):
            account = next((a for a in plan.accounts if a.name == name), None)
            if account is None:
                result.errors.append(f"rmds.accounts[{idx}]: '{name}' does not match any account name")
            elif account.type not in {"traditional_ira", "401k"}:
                result.errors.append(f"rmds.accounts[{idx}]: account must be 401k or traditional_ira")
        if plan.rmds.destination_account not in account_names:
            result.errors.append(
                f"rmds.destination_account: '{plan.rmds.destination_account}' does not match any account name"
            )

    return result
