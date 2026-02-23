"""Tax bracket and threshold reference data for TFP."""

from __future__ import annotations

from typing import Final

BASE_TAX_YEAR: Final[int] = 2026
DEFAULT_BRACKET_INFLATION: Final[float] = 0.025

FILING_STATUSES: Final[set[str]] = {
    "single",
    "married_filing_jointly",
    "married_filing_separately",
    "head_of_household",
    "qualifying_surviving_spouse",
}

# Brackets are (upper_bound, marginal_rate). Upper bound None means infinity.
FEDERAL_BRACKETS: Final[dict[int, dict[str, list[tuple[float | None, float]]]]] = {
    2026: {
        "single": [
            (12_400.0, 0.10),
            (50_400.0, 0.12),
            (105_700.0, 0.22),
            (201_775.0, 0.24),
            (256_225.0, 0.32),
            (640_600.0, 0.35),
            (None, 0.37),
        ],
        "married_filing_jointly": [
            (24_800.0, 0.10),
            (100_800.0, 0.12),
            (211_400.0, 0.22),
            (403_550.0, 0.24),
            (512_450.0, 0.32),
            (768_700.0, 0.35),
            (None, 0.37),
        ],
        "married_filing_separately": [
            (12_400.0, 0.10),
            (50_400.0, 0.12),
            (105_700.0, 0.22),
            (201_775.0, 0.24),
            (256_225.0, 0.32),
            (384_350.0, 0.35),
            (None, 0.37),
        ],
        "head_of_household": [
            (17_700.0, 0.10),
            (67_450.0, 0.12),
            (105_700.0, 0.22),
            (201_750.0, 0.24),
            (256_200.0, 0.32),
            (640_600.0, 0.35),
            (None, 0.37),
        ],
        "qualifying_surviving_spouse": [
            (24_800.0, 0.10),
            (100_800.0, 0.12),
            (211_400.0, 0.22),
            (403_550.0, 0.24),
            (512_450.0, 0.32),
            (768_700.0, 0.35),
            (None, 0.37),
        ],
    }
}

# Long-term capital gains brackets are (upper_bound, marginal_rate).
CAPITAL_GAINS_BRACKETS: Final[dict[int, dict[str, list[tuple[float | None, float]]]]] = {
    2026: {
        "single": [(50_800.0, 0.00), (557_000.0, 0.15), (None, 0.20)],
        "married_filing_jointly": [(101_600.0, 0.00), (626_350.0, 0.15), (None, 0.20)],
        "married_filing_separately": [(50_800.0, 0.00), (313_175.0, 0.15), (None, 0.20)],
        "head_of_household": [(68_050.0, 0.00), (595_350.0, 0.15), (None, 0.20)],
        "qualifying_surviving_spouse": [(101_600.0, 0.00), (626_350.0, 0.15), (None, 0.20)],
    }
}

STANDARD_DEDUCTIONS: Final[dict[int, dict[str, float]]] = {
    2026: {
        "single": 16_100.0,
        "married_filing_jointly": 32_200.0,
        "married_filing_separately": 16_100.0,
        "head_of_household": 24_150.0,
        "qualifying_surviving_spouse": 32_200.0,
    }
}

NIIT_THRESHOLDS: Final[dict[str, float]] = {
    "single": 200_000.0,
    "married_filing_jointly": 250_000.0,
    "married_filing_separately": 125_000.0,
    "head_of_household": 200_000.0,
    "qualifying_surviving_spouse": 250_000.0,
}

AMT_EXEMPTIONS: Final[dict[str, tuple[float, float]]] = {
    "single": (88_100.0, 626_350.0),
    "married_filing_jointly": (137_000.0, 1_252_700.0),
    "married_filing_separately": (68_500.0, 626_350.0),
    "head_of_household": (88_100.0, 626_350.0),
    "qualifying_surviving_spouse": (137_000.0, 1_252_700.0),
}

AMT_BRACKETS: Final[list[tuple[float | None, float]]] = [
    (220_700.0, 0.26),
    (None, 0.28),
]

IRMAA_BRACKETS: Final[dict[int, dict[str, list[tuple[float | None, tuple[float, float]]]]]] = {
    2026: {
        "single": [
            (106_000.0, (0.0, 0.0)),
            (133_000.0, (74.0, 13.0)),
            (167_000.0, (185.0, 33.0)),
            (200_000.0, (296.0, 52.0)),
            (500_000.0, (407.0, 71.0)),
            (None, (444.0, 82.0)),
        ],
        "married_filing_jointly": [
            (212_000.0, (0.0, 0.0)),
            (266_000.0, (74.0, 13.0)),
            (334_000.0, (185.0, 33.0)),
            (400_000.0, (296.0, 52.0)),
            (750_000.0, (407.0, 71.0)),
            (None, (444.0, 82.0)),
        ],
        "married_filing_separately": [
            (106_000.0, (0.0, 0.0)),
            (133_000.0, (407.0, 71.0)),
            (None, (444.0, 82.0)),
        ],
        "head_of_household": [
            (106_000.0, (0.0, 0.0)),
            (133_000.0, (74.0, 13.0)),
            (167_000.0, (185.0, 33.0)),
            (200_000.0, (296.0, 52.0)),
            (500_000.0, (407.0, 71.0)),
            (None, (444.0, 82.0)),
        ],
        "qualifying_surviving_spouse": [
            (212_000.0, (0.0, 0.0)),
            (266_000.0, (74.0, 13.0)),
            (334_000.0, (185.0, 33.0)),
            (400_000.0, (296.0, 52.0)),
            (750_000.0, (407.0, 71.0)),
            (None, (444.0, 82.0)),
        ],
    }
}

FICA_RATES: Final[dict[int, dict[str, float]]] = {
    2026: {
        "social_security_rate": 0.062,
        "social_security_wage_base": 184_500.0,
        "medicare_rate": 0.0145,
        "additional_medicare_rate": 0.009,
        "additional_medicare_single_threshold": 200_000.0,
        "additional_medicare_joint_threshold": 250_000.0,
    }
}

STATE_BASE_RATES: Final[dict[str, float]] = {
    "AL": 0.0500,
    "AK": 0.0000,
    "AZ": 0.0250,
    "AR": 0.0390,
    "CA": 0.0930,
    "CO": 0.0440,
    "CT": 0.0500,
    "DE": 0.0520,
    "FL": 0.0000,
    "GA": 0.0530,
    "HI": 0.0800,
    "ID": 0.0580,
    "IL": 0.0495,
    "IN": 0.0300,
    "IA": 0.0570,
    "KS": 0.0520,
    "KY": 0.0450,
    "LA": 0.0300,
    "ME": 0.0710,
    "MD": 0.0575,
    "MA": 0.0500,
    "MI": 0.0425,
    "MN": 0.0680,
    "MS": 0.0470,
    "MO": 0.0470,
    "MT": 0.0590,
    "NE": 0.0560,
    "NV": 0.0000,
    "NH": 0.0000,
    "NJ": 0.0630,
    "NM": 0.0490,
    "NY": 0.0650,
    "NC": 0.0475,
    "ND": 0.0250,
    "OH": 0.0350,
    "OK": 0.0475,
    "OR": 0.0870,
    "PA": 0.0307,
    "RI": 0.0550,
    "SC": 0.0640,
    "SD": 0.0000,
    "TN": 0.0000,
    "TX": 0.0000,
    "UT": 0.0480,
    "VT": 0.0660,
    "VA": 0.0575,
    "WA": 0.0000,
    "WV": 0.0510,
    "WI": 0.0530,
    "WY": 0.0000,
    "DC": 0.0850,
}


def _flat_state_brackets(rate: float) -> dict[str, list[tuple[float | None, float]]]:
    return {status: [(None, rate)] for status in FILING_STATUSES}


def _build_state_tax_brackets() -> dict[int, dict[str, dict[str, list[tuple[float | None, float]]]]]:
    by_state = {state: _flat_state_brackets(rate) for state, rate in STATE_BASE_RATES.items()}

    # Approximate progressive schedules for high-tax jurisdictions where filing status matters.
    by_state["CA"] = {
        "single": [
            (10_756.0, 0.01),
            (25_499.0, 0.02),
            (40_245.0, 0.04),
            (55_866.0, 0.06),
            (70_606.0, 0.08),
            (360_659.0, 0.093),
            (None, 0.103),
        ],
        "married_filing_jointly": [
            (21_512.0, 0.01),
            (50_998.0, 0.02),
            (80_490.0, 0.04),
            (111_732.0, 0.06),
            (141_212.0, 0.08),
            (721_318.0, 0.093),
            (None, 0.103),
        ],
        "married_filing_separately": [
            (10_756.0, 0.01),
            (25_499.0, 0.02),
            (40_245.0, 0.04),
            (55_866.0, 0.06),
            (70_606.0, 0.08),
            (360_659.0, 0.093),
            (None, 0.103),
        ],
        "head_of_household": [
            (21_527.0, 0.01),
            (51_001.0, 0.02),
            (65_747.0, 0.04),
            (81_368.0, 0.06),
            (96_108.0, 0.08),
            (490_493.0, 0.093),
            (None, 0.103),
        ],
        "qualifying_surviving_spouse": [
            (21_512.0, 0.01),
            (50_998.0, 0.02),
            (80_490.0, 0.04),
            (111_732.0, 0.06),
            (141_212.0, 0.08),
            (721_318.0, 0.093),
            (None, 0.103),
        ],
    }

    by_state["NY"] = {
        "single": [
            (8_500.0, 0.04),
            (11_700.0, 0.045),
            (13_900.0, 0.0525),
            (21_400.0, 0.055),
            (80_650.0, 0.06),
            (215_400.0, 0.0685),
            (1_077_550.0, 0.0965),
            (5_000_000.0, 0.103),
            (25_000_000.0, 0.109),
            (None, 0.109),
        ],
        "married_filing_jointly": [
            (17_150.0, 0.04),
            (23_600.0, 0.045),
            (27_900.0, 0.0525),
            (43_000.0, 0.055),
            (161_550.0, 0.06),
            (323_200.0, 0.0685),
            (2_155_350.0, 0.0965),
            (5_000_000.0, 0.103),
            (25_000_000.0, 0.109),
            (None, 0.109),
        ],
        "married_filing_separately": [
            (8_500.0, 0.04),
            (11_700.0, 0.045),
            (13_900.0, 0.0525),
            (21_400.0, 0.055),
            (80_650.0, 0.06),
            (161_550.0, 0.0685),
            (1_077_550.0, 0.0965),
            (5_000_000.0, 0.103),
            (25_000_000.0, 0.109),
            (None, 0.109),
        ],
        "head_of_household": [
            (12_800.0, 0.04),
            (17_650.0, 0.045),
            (20_900.0, 0.0525),
            (32_200.0, 0.055),
            (107_650.0, 0.06),
            (269_300.0, 0.0685),
            (1_616_450.0, 0.0965),
            (5_000_000.0, 0.103),
            (25_000_000.0, 0.109),
            (None, 0.109),
        ],
        "qualifying_surviving_spouse": [
            (17_150.0, 0.04),
            (23_600.0, 0.045),
            (27_900.0, 0.0525),
            (43_000.0, 0.055),
            (161_550.0, 0.06),
            (323_200.0, 0.0685),
            (2_155_350.0, 0.0965),
            (5_000_000.0, 0.103),
            (25_000_000.0, 0.109),
            (None, 0.109),
        ],
    }

    by_state["NJ"] = {
        "single": [
            (20_000.0, 0.014),
            (35_000.0, 0.0175),
            (40_000.0, 0.035),
            (75_000.0, 0.05525),
            (500_000.0, 0.0637),
            (1_000_000.0, 0.0897),
            (None, 0.1075),
        ],
        "married_filing_jointly": [
            (20_000.0, 0.014),
            (50_000.0, 0.0175),
            (70_000.0, 0.0245),
            (80_000.0, 0.035),
            (150_000.0, 0.05525),
            (500_000.0, 0.0637),
            (1_000_000.0, 0.0897),
            (None, 0.1075),
        ],
        "married_filing_separately": [
            (20_000.0, 0.014),
            (35_000.0, 0.0175),
            (40_000.0, 0.035),
            (75_000.0, 0.05525),
            (500_000.0, 0.0637),
            (1_000_000.0, 0.0897),
            (None, 0.1075),
        ],
        "head_of_household": [
            (20_000.0, 0.014),
            (50_000.0, 0.0175),
            (70_000.0, 0.0245),
            (80_000.0, 0.035),
            (150_000.0, 0.05525),
            (500_000.0, 0.0637),
            (1_000_000.0, 0.0897),
            (None, 0.1075),
        ],
        "qualifying_surviving_spouse": [
            (20_000.0, 0.014),
            (50_000.0, 0.0175),
            (70_000.0, 0.0245),
            (80_000.0, 0.035),
            (150_000.0, 0.05525),
            (500_000.0, 0.0637),
            (1_000_000.0, 0.0897),
            (None, 0.1075),
        ],
    }

    return {2026: by_state}


STATE_TAX_BRACKETS: Final[dict[int, dict[str, dict[str, list[tuple[float | None, float]]]]]] = _build_state_tax_brackets()

# Retained for compatibility with existing expectations and tests.
STATE_EFFECTIVE_RATES: Final[dict[int, dict[str, float]]] = {
    2026: {
        **STATE_BASE_RATES,
    }
}
