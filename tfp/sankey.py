"""Money-flow payload generation for Sankey rendering."""

from __future__ import annotations

from .engine import EngineResult


def build_sankey_payload(engine_result: EngineResult) -> dict[str, object]:
    flows: dict[int, dict[str, object]] = {}
    for annual in engine_result.annual:
        expenses = annual.healthcare_expenses + annual.other_expenses + annual.real_asset_expenses
        taxes = annual.tax_total if annual.tax_total > 0 else annual.tax_withheld
        sources = {
            "Income": annual.income,
            "Withdrawals": annual.withdrawals,
            "Tax Refund": annual.tax_refund,
            "Other": max(0.0, annual.transfers),
        }
        destinations = {
            "Living + Healthcare": expenses,
            "Taxes": taxes,
            "Contributions": annual.contributions,
            "Transfers": annual.transfers,
            "Fees": annual.fees,
            "Savings Δ": max(
                0.0,
                (annual.income + annual.withdrawals + annual.tax_refund + max(0.0, annual.transfers))
                - (expenses + taxes + annual.contributions + annual.transfers + annual.fees),
            ),
        }
        flows[annual.year] = {
            "sources": sources,
            "destinations": destinations,
        }
    return {
        "years": [row.year for row in engine_result.annual],
        "flows": flows,
    }
