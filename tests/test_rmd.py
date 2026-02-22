from tfp.rmd import compute_rmd_amount, execute_rmds
from tfp.schema import Account, RMDSettings


def test_compute_rmd_amount_for_age_73():
    assert round(compute_rmd_amount(265000, 73.0), 2) == 10000.00


def test_execute_rmds_deposits_to_destination_account():
    accounts = {
        "IRA": Account(
            name="IRA",
            type="traditional_ira",
            owner="primary",
            balance=100000,
            cost_basis=None,
            growth_rate=0.0,
            dividend_yield=0.0,
            dividend_tax_treatment="tax_free",
            reinvest_dividends=True,
            bond_allocation_percent=0.0,
            yearly_fees=0.0,
            allow_withdrawals=True,
        ),
        "Cash": Account(
            name="Cash",
            type="cash",
            owner="primary",
            balance=0.0,
            cost_basis=None,
            growth_rate=0.0,
            dividend_yield=0.0,
            dividend_tax_treatment="tax_free",
            reinvest_dividends=False,
            bond_allocation_percent=100.0,
            yearly_fees=0.0,
            allow_withdrawals=True,
        ),
    }
    balances = {"IRA": 100000.0, "Cash": 0.0}
    settings = RMDSettings(enabled=True, rmd_start_age=73, accounts=["IRA"], destination_account="Cash")

    withdrawn, ordinary = execute_rmds(
        settings=settings,
        accounts_by_name=accounts,
        balances=balances,
        prior_year_end_balances={"IRA": 100000.0, "Cash": 0.0},
        owner_ages={"primary": 73.0},
    )

    assert withdrawn > 0
    assert ordinary == withdrawn
    assert balances["Cash"] == withdrawn
    assert balances["IRA"] == 100000.0 - withdrawn
