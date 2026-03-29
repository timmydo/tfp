from tfp.tax_data import BASE_TAX_YEAR
from tfp.utils import change_multiplier, date_index, is_active, year_factor


def test_date_index_resolves_start_and_end_keywords():
    assert date_index("start", "2026-01", "2030-12") == 2026 * 12 + 1
    assert date_index("end", "2026-01", "2030-12") == 2030 * 12 + 12


def test_is_active_uses_inclusive_bounds():
    current_index = 2026 * 12 + 6
    assert is_active("2026-06", "2026-06", current_index, "2026-01", "2030-12")
    assert not is_active("2026-07", "2026-12", current_index, "2026-01", "2030-12")


def test_change_multiplier_supports_decrease_mode():
    assert round(
        change_multiplier(
            change_over_time="decrease",
            change_rate=0.10,
            inflation_rate=0.03,
            years_elapsed=2,
        ),
        6,
    ) == 0.81


def test_year_factor_can_optionally_clamp_to_base_year():
    prior_year = BASE_TAX_YEAR - 2
    unclamped = year_factor(prior_year, 0.03)
    clamped = year_factor(prior_year, 0.03, clamp_at_base_year=True)

    assert unclamped < 1.0
    assert clamped == 1.0
