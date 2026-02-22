from tests.helpers import clone_plan, write_plan
from tfp.__main__ import main


def test_validate_mode_exits_zero():
    code = main(["sample_plan.json", "--validate"])
    assert code == 0


def test_invalid_plan_returns_one(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["accounts"] = [a for a in data["accounts"] if a["type"] != "cash"]
    path = write_plan(tmp_path, data)

    code = main([str(path), "--validate"])
    assert code == 1


def test_missing_plan_file_returns_two(tmp_path):
    missing = tmp_path / "nope.json"
    code = main([str(missing), "--validate"])
    assert code == 2


def test_summary_mode_writes_output(tmp_path, sample_plan_dict):
    plan_path = write_plan(tmp_path, sample_plan_dict)
    output_path = tmp_path / "out.html"
    code = main([str(plan_path), "--summary", "-o", str(output_path)])

    assert code == 0
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "TFP Report" in text
