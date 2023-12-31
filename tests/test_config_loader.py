import json
from pathlib import Path
from typing import Dict

import pytest

from alarm_craft import config_loader


def _missing_conf_message_data():
    conf = [
        {"globals": {}},
        {"resources": {}},
        {
            "resources": {
                "lambda": {
                    "alarm": {"namespace": "", "metrics": [""]},
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                    "alarm": {"metrics": [""]},  # invalid
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                    "alarm": {"namespace": ""},  # invalid
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                    "target_resource_tags": {},  # invalid
                    "alarm": {"namespace": "", "metrics": [""]},
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                    "alarm": {"namespace": "", "metrics": []},  # invalid
                }
            }
        },
    ]
    words = [
        "resources",
        "enough",  # `resources` must have 1 or more key(s)
        "target_resource_type",
        "alarm",
        "namespace",
        "metrics",
        "enough",  # `target_resource_tags`` must have 1 or more key(s)
        "too short",  # `metrics` must have 1 or more str(s)
    ]

    return zip(conf, words)


@pytest.mark.parametrize("conf, word_in_message", _missing_conf_message_data())
def test_insufficient_config(tmp_path: Path, conf: Dict, word_in_message: str):
    """Tests missing keys"""
    config_path = tmp_path / "config_missing_key.json"
    with open(config_path, "w") as f:
        json.dump(conf, f)

    with pytest.raises(Exception) as e:
        # execute test
        config_loader.load(str(config_path))

    assert word_in_message in e.value.message  # type: ignore


def test_load_global_default_config(tmp_path: Path):
    """Tests loading no global config"""
    given_conf = {
        "resources": {
            "1": {
                "target_resource_type": "lambda:function",
                "alarm": {
                    "namespace": "",
                    "metrics": [""],
                },
            },
        },
    }
    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(given_conf, f)

    default_glo = config_loader.default_global_config()
    defaulted_conf = {
        "globals": default_glo,
        "resources": given_conf["resources"],
    }

    assert defaulted_conf == config_loader.load(str(config_path))


def test_merge_global_name_conf(tmp_path: Path):
    """Tests merge globals to resources"""
    conf = {
        "globals": {
            "resource_filter": {
                "target_resource_name_pattern": "globally_configured_pattern",
            },
        },
        "resources": {
            "myservice1": {
                "target_resource_type": "lambda:function",
                "target_resource_name_pattern": "overridden_pattern_321",
                "alarm": {
                    "namespace": "",
                    "metrics": [""],
                },
            },
            "myservice2": {
                "target_resource_type": "lambda:function",
                "alarm": {
                    "namespace": "",
                    "metrics": [""],
                },
            },
        },
    }

    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    loaded_conf = config_loader.load(str(config_path))

    key1, key2, key3 = ("resources", "myservice", "target_resource_name_pattern")
    assert loaded_conf[key1][key2 + "1"][key3] == "overridden_pattern_321"  # type: ignore
    assert loaded_conf[key1][key2 + "2"][key3] == "globally_configured_pattern"  # type: ignore


def test_merge_global_tag_conf(tmp_path: Path):
    """Tests merge globals to resources"""
    conf = {
        "globals": {
            "resource_filter": {
                "target_resource_tags": {"tag0": "value0"},
            },
        },
        "resources": {
            "myservice1": {
                "target_resource_tags": {"tag1": "value1"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "namespace": "",
                    "metrics": [""],
                },
            },
            "myservice2": {
                "target_resource_tags": {"tag2": "value2"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "namespace": "",
                    "metrics": [""],
                },
            },
            "myservice12": {
                "target_resource_tags": {"tag1": "value1", "tag2": "value2"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "namespace": "",
                    "metrics": [""],
                },
            },
        },
    }

    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    loaded_conf = config_loader.load(str(config_path))

    def _type_safe_get(conf: dict, keys: list[str]):
        if len(keys) == 0:
            return None

        val = conf[keys[0]]
        if len(keys) == 1:
            return val
        else:
            assert isinstance(val, dict)
            return _type_safe_get(val, keys[1:])

    assert _type_safe_get(loaded_conf, ["resources", "myservice1", "target_resource_tags"]) == {
        "tag0": "value0",
        "tag1": "value1",
    }

    assert _type_safe_get(loaded_conf, ["resources", "myservice2", "target_resource_tags"]) == {
        "tag0": "value0",
        "tag2": "value2",
    }
    assert _type_safe_get(loaded_conf, ["resources", "myservice12", "target_resource_tags"]) == {
        "tag0": "value0",
        "tag1": "value1",
        "tag2": "value2",
    }
