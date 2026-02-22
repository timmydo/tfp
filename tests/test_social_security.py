from tfp.schema import SocialSecurity
from tfp.social_security import monthly_social_security_income


def test_social_security_benefit_starts_after_claim_age():
    entry = SocialSecurity(
        owner="primary",
        pia_at_fra=3000.0,
        fra_age_years=67,
        fra_age_months=0,
        claiming_age_years=70,
        claiming_age_months=0,
        cola_assumption="fixed",
        cola_rate=0.0,
    )

    before_total, _ = monthly_social_security_income(
        entries=[entry],
        owner_ages={"primary": 69.0},
        inflation_rate=0.03,
    )
    after_total, by_owner = monthly_social_security_income(
        entries=[entry],
        owner_ages={"primary": 70.0},
        inflation_rate=0.03,
    )

    assert before_total == 0.0
    assert after_total > 3000.0
    assert by_owner["primary"] == after_total


def test_spousal_top_up_applies_when_own_pia_below_half_spouse_pia():
    primary = SocialSecurity(
        owner="primary",
        pia_at_fra=1000.0,
        fra_age_years=67,
        fra_age_months=0,
        claiming_age_years=67,
        claiming_age_months=0,
        cola_assumption="fixed",
        cola_rate=0.0,
    )
    spouse = SocialSecurity(
        owner="spouse",
        pia_at_fra=3200.0,
        fra_age_years=67,
        fra_age_months=0,
        claiming_age_years=67,
        claiming_age_months=0,
        cola_assumption="fixed",
        cola_rate=0.0,
    )

    _, by_owner = monthly_social_security_income(
        entries=[primary, spouse],
        owner_ages={"primary": 67.0, "spouse": 67.0},
        inflation_rate=0.03,
    )

    assert by_owner["primary"] == 1600.0
