import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_plan_dict() -> dict:
    return json.loads(Path("sample_plan.json").read_text(encoding="utf-8"))
