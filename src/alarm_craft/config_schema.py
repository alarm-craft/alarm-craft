import json
from pathlib import Path


def get_schema() -> dict:
    """Get config schema"""
    curr_dir = Path(__file__).parent
    with open(curr_dir / "config_schema.json", "r") as f:
        schema = json.load(f)
        assert isinstance(schema, dict)
        return schema
