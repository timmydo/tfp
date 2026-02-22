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
            (11_925.0, 0.10),
            (48_475.0, 0.12),
            (103_350.0, 0.22),
            (197_300.0, 0.24),
            (250_525.0, 0.32),
            (626_350.0, 0.35),
            (None, 0.37),
        ],
        "married_filing_jointly": [
            (23_850.0, 0.10),
            (96_950.0, 0.12),
            (206_700.0, 0.22),
            (394_600.0, 0.24),
            (501_050.0, 0.32),
            (751_600.0, 0.35),
            (None, 0.37),
        ],
        "married_filing_separately": [
            (11_925.0, 0.10),
            (48_475.0, 0.12),
            (103_350.0, 0.22),
            (197_300.0, 0.24),
            (250_525.0, 0.32),
            (375_800.0, 0.35),
            (None, 0.37),
        ],
        "head_of_household": [
            (17_000.0, 0.10),
            (64_850.0, 0.12),
            (103_350.0, 0.22),
            (197_300.0, 0.24),
            (250_500.0, 0.32),
            (626_350.0, 0.35),
            (None, 0.37),
        ],
        "qualifying_surviving_spouse": [
            (23_850.0, 0.10),
            (96_950.0, 0.12),
            (206_700.0, 0.22),
            (394_600.0, 0.24),
            (501_050.0, 0.32),
            (751_600.0, 0.35),
            (None, 0.37),
        ],
    }
}

# Long-term capital gains brackets are (upper_bound, marginal_rate).
CAPITAL_GAINS_BRACKETS: Final[dict[int, dict[str, list[tuple[float | None, float]]]]] = {
    2026: {
        "single": [(48_350.0, 0.00), (533_400.0, 0.15), (None, 0.20)],
        "married_filing_jointly": [(96_700.0, 0.00), (600_050.0, 0.15), (None, 0.20)],
        "married_filing_separately": [(48_350.0, 0.00), (300_000.0, 0.15), (None, 0.20)],
        "head_of_household": [(64_750.0, 0.00), (566_700.0, 0.15), (None, 0.20)],
        "qualifying_surviving_spouse": [(96_700.0, 0.00), (600_050.0, 0.15), (None, 0.20)],
    }
}

STANDARD_DEDUCTIONS: Final[dict[int, dict[str, float]]] = {
    2026: {
        "single": 15_000.0,
        "married_filing_jointly": 30_000.0,
        "married_filing_separately": 15_000.0,
        "head_of_household": 22_500.0,
        "qualifying_surviving_spouse": 30_000.0,
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
        "social_security_wage_base": 180_000.0,
        "medicare_rate": 0.0145,
        "additional_medicare_rate": 0.009,
        "additional_medicare_single_threshold": 200_000.0,
        "additional_medicare_joint_threshold": 250_000.0,
    }
}

STATE_EFFECTIVE_RATES: Final[dict[int, dict[str, float]]] = {
    2026: {
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
}
