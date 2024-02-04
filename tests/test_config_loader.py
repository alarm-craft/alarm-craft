import json
import os
from pathlib import Path
from typing import Dict

import pytest
import yaml

from alarm_craft import config_loader


def _missing_conf_message_data():
    conf = [
        {"globals": {}},
        {"resources": {}},
        {
            "resources": {
                "lambda": {
                    "alarm": {"metrics": [""]},
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
                    "alarm": {},  # invalid
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                    "target_resource_tags": {},  # invalid
                    "alarm": {"metrics": [""]},
                }
            }
        },
        {
            "resources": {
                "lambda": {
                    "target_resource_type": "lambda:function",
                    "alarm": {"metrics": []},  # invalid
                }
            }
        },
    ]
    # note: these portions of error messages may modified in a new version of libs.
    words = [
        "resources",
        "non-empty",  # `resources` must have 1 or more key(s)
        "target_resource_type",
        "alarm",
        "metrics",
        "non-empty",  # `target_resource_tags`` must have 1 or more key(s)
        "non-empty",  # `metrics` must have 1 or more str(s)
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
                    "metrics": [""],
                },
            },
            "myservice2": {
                "target_resource_type": "lambda:function",
                "alarm": {
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
                    "metrics": [""],
                },
            },
            "myservice2": {
                "target_resource_tags": {"tag2": "value2"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "metrics": [""],
                },
            },
            "myservice12": {
                "target_resource_tags": {"tag1": "value1", "tag2": "value2"},
                "target_resource_type": "lambda:function",
                "alarm": {
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


@pytest.mark.parametrize("config_file", ["config.yaml", "config.yml"])
def test_conf_in_yaml(tmp_path: Path, config_file: str):
    """Tests yaml config"""
    conf = {
        "globals": config_loader.default_global_config(),
        "resources": {
            "myservice1": {
                "target_resource_tags": {"tag1": "value1"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "metrics": [""],
                },
            },
            "myservice2": {
                "target_resource_tags": {"tag2": "value2"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "metrics": [""],
                },
            },
            "myservice12": {
                "target_resource_tags": {"tag1": "value1", "tag2": "value2"},
                "target_resource_type": "lambda:function",
                "alarm": {
                    "metrics": [""],
                },
            },
        },
    }

    config_path = tmp_path / config_file

    with open(config_path, "w") as f:
        yaml.safe_dump(conf, f)

    loaded_conf = config_loader.load(str(config_path))
    assert conf == loaded_conf


def test_default_conf_filename(tmp_path: Path):
    """Tests resolving default config filename"""

    def _conf(filename: str):
        return {
            "globals": config_loader.default_global_config(),
            "resources": {
                "myservice": {
                    "target_resource_type": "lambda:function",
                    "target_resource_tags": {"filename": filename},
                    "alarm": {
                        "metrics": [""],
                    },
                },
            },
        }

    prioritized_filenames: list[str] = [
        "alarm-config.yaml",
        "alarm-config.yml",
        "alarm-config.json",
    ]  # prioritized order

    os.chdir(tmp_path)

    for filename in prioritized_filenames:
        conf = _conf(filename)

        config_path = tmp_path / filename
        with open(config_path, "w") as f:
            if filename.endswith(".json"):
                json.dump(conf, f)
            else:
                yaml.safe_dump(conf, f)

    for filename in prioritized_filenames:
        # load without filename
        loaded_conf = config_loader.load(None)
        assert loaded_conf["resources"]["myservice"]["target_resource_tags"]["filename"] == filename  # type: ignore
        os.remove(tmp_path / filename)


def test_file_not_found():
    """Tests config file not found"""
    with pytest.raises(FileNotFoundError) as err:
        f = "no_such_config.json"
        config_loader.load(f)
        assert f in err.value

    with pytest.raises(ValueError) as err:
        config_loader.load(None)
        assert "-c" in err.value
