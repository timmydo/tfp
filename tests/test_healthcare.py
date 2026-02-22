from tfp.healthcare import compute_monthly_healthcare_cost
from tfp.schema import load_plan


def test_irmaa_increases_post_medicare_costs_when_enabled():
    plan = load_plan("sample_plan.json")

    owner_ages = {"primary": 66.0, "spouse": 66.0}
    base_cost, base_irmaa = compute_monthly_healthcare_cost(
        healthcare=plan.healthcare,
        owner_ages=owner_ages,
        current_year=2028,
        current_index=2028 * 12 + 1,
        plan_start=plan.plan_settings.plan_start,
        plan_end=plan.plan_settings.plan_end,
        inflation_rate=plan.plan_settings.inflation_rate,
        filing_status=plan.filing_status,
        irmaa_magi_history={2026: 0.0},
    )

    high_cost, high_irmaa = compute_monthly_healthcare_cost(
        healthcare=plan.healthcare,
        owner_ages=owner_ages,
        current_year=2028,
        current_index=2028 * 12 + 1,
        plan_start=plan.plan_settings.plan_start,
        plan_end=plan.plan_settings.plan_end,
        inflation_rate=plan.plan_settings.inflation_rate,
        filing_status=plan.filing_status,
        irmaa_magi_history={2026: 1_000_000.0},
    )

    assert high_irmaa > base_irmaa
    assert high_cost > base_cost
