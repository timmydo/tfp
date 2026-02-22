import copy
import json
from pathlib import Path


def write_plan(tmp_path: Path, data: dict, filename: str = "plan.json") -> Path:
    path = tmp_path / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def clone_plan(data: dict) -> dict:
    return copy.deepcopy(data)
