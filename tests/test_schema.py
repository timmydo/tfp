import pytest

from tests.helpers import clone_plan, write_plan
from tfp.schema import SchemaError, load_plan


def test_load_plan_rejects_non_object_root(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(SchemaError, match="plan: root must be a JSON object"):
        load_plan(path)


def test_load_plan_requires_people_primary_state(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    del data["people"]["primary"]["state"]
    path = write_plan(tmp_path, data)

    with pytest.raises(SchemaError, match=r"people\.primary\.state: missing required field"):
        load_plan(path)


def test_load_plan_requires_required_field(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    del data["plan_settings"]["plan_start"]
    path = write_plan(tmp_path, data)

    with pytest.raises(SchemaError, match=r"plan_settings\.plan_start: missing required field"):
        load_plan(path)


def test_load_plan_rejects_wrong_collection_types(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["accounts"] = {}
    path = write_plan(tmp_path, data)

    with pytest.raises(SchemaError, match=r"accounts: expected array"):
        load_plan(path)


def test_load_plan_rejects_invalid_nested_object_type(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["people"]["primary"] = "bad"
    path = write_plan(tmp_path, data)

    with pytest.raises(SchemaError, match=r"people\.primary: expected object"):
        load_plan(path)


def test_load_plan_allows_missing_purchase_price_for_unsold_asset(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["real_assets"][0].pop("purchase_price", None)
    path = write_plan(tmp_path, data)

    plan = load_plan(path)
    assert plan.real_assets[0].purchase_price is None
