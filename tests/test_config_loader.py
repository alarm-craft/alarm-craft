import json
from pathlib import Path

import pytest

from alarm_craft import config_loader


def test_load_minimum_config(tmp_path: Path):
    """Tests loading a minimum config"""
    conf = {
        "alarm_config": {
            "alarm_name_prefix": "cw-metric-alarm-autogen-",
            "alarm_actions": [],
            "default_alarm_params": {},
        },
        "service_config": {},
    }
    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    assert conf == config_loader.load(str(config_path))


def test_load_default_config(tmp_path: Path):
    """Tests loading default config"""
    default_config_path = tmp_path / "default_config.json"
    config_loader.save_default_config(str(default_config_path))

    actual_config = config_loader.load(None)

    with open(default_config_path, "r") as f:
        merged_default_config = config_loader._merge_configs(json.load(f))
        assert actual_config == merged_default_config


def test_merge_global_name_conf(tmp_path: Path):
    """Tests merge globals to service_config"""
    conf = {
        "alarm_config": {
            "alarm_name_prefix": "aaa",
            "alarm_actions": [],
            "default_alarm_params": {},
        },
        "globals": {
            "target_resource_name_pattern": "globally_configured_pattern",
        },
        "service_config": {
            "myservice1": {
                "provider_class_name": "MyServiceProvider1",
                "resource_type_filter": "1234567890",
                "target_resource_name_pattern": "overridden_pattern_321",
                "namespace": "1234567890",
                "metrics": ["1234567890"],
            },
            "myservice2": {
                "provider_class_name": "MyServiceProvider2",
                "resource_type_filter": "1234567890",
                "namespace": "1234567890",
                "metrics": ["1234567890"],
            },
        },
    }

    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    loaded_conf = config_loader.load(str(config_path))

    key1, key2, key3 = ("service_config", "myservice", "target_resource_name_pattern")
    assert loaded_conf[key1][key2 + "1"][key3] == "overridden_pattern_321"  # type: ignore
    assert loaded_conf[key1][key2 + "2"][key3] == "globally_configured_pattern"  # type: ignore


def test_merge_global_tag_conf(tmp_path: Path):
    """Tests merge globals to service_config"""
    conf = {
        "alarm_config": {
            "alarm_name_prefix": "aaa",
            "alarm_actions": [],
            "default_alarm_params": {},
        },
        "globals": {
            "target_resource_tags": {"tag0": "value0"},
        },
        "service_config": {
            "myservice1": {
                "provider_class_name": "MyServiceProvider1",
                "target_resource_tags": {"tag1": "value1"},
                "resource_type_filter": "1234567890",
                "namespace": "1234567890",
                "metrics": ["1234567890"],
            },
            "myservice2": {
                "provider_class_name": "MyServiceProvider2",
                "target_resource_tags": {"tag2": "value2"},
                "resource_type_filter": "1234567890",
                "namespace": "1234567890",
                "metrics": ["1234567890"],
            },
            "myservice12": {
                "provider_class_name": "MyServiceProvider12",
                "target_resource_tags": {"tag1": "value1", "tag2": "value2"},
                "resource_type_filter": "1234567890",
                "namespace": "1234567890",
                "metrics": ["1234567890"],
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

    assert _type_safe_get(loaded_conf, ["service_config", "myservice1", "target_resource_tags"]) == {
        "tag0": "value0",
        "tag1": "value1",
    }

    assert _type_safe_get(loaded_conf, ["service_config", "myservice2", "target_resource_tags"]) == {
        "tag0": "value0",
        "tag2": "value2",
    }
    assert _type_safe_get(loaded_conf, ["service_config", "myservice12", "target_resource_tags"]) == {
        "tag0": "value0",
        "tag1": "value1",
        "tag2": "value2",
    }


def _conf_insufficient_keys_data():
    confs = [
        {
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "default_alarm_params": {},
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
        },
        {
            "alarm_config": {"alarm_name_prefix": "aaa", "alarm_actions": [], "default_alarm_params": {}},
            "service_config": {
                "myservice": {
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                }
            },
        },
        {
            "alarm_config": {"alarm_name_prefix": "aaa", "alarm_actions": [], "default_alarm_params": {}},
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "namespace": "",
                    "metrics": ["m"],
                }
            },
        },
        {
            "alarm_config": {"alarm_name_prefix": "aaa", "alarm_actions": [], "default_alarm_params": {}},
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "metrics": ["m"],
                }
            },
        },
        {
            "alarm_config": {"alarm_name_prefix": "aaa", "alarm_actions": [], "default_alarm_params": {}},
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                }
            },
        },
        {
            "alarm_config": {"alarm_name_prefix": "aaa", "alarm_actions": [], "default_alarm_params": {}},
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": [],  # at least one metric required
                }
            },
        },
        {
            "alarm_config": {"alarm_name_prefix": "aaa", "alarm_actions": [], "default_alarm_params": {}},
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                    "target_resource_tags": {},  # at least one tag required
                }
            },
        },
    ]
    words = [
        "alarm_config",
        "alarm_name_prefix",
        "alarm_actions",
        "default_alarm_params",
        "service_config",
        "provider_class_name",
        "resource_type_filter",
        "namespace",
        "metrics",
        "[]",  # is too short
        "{}",  # does not have enough properties
    ]

    return zip(confs, words)


@pytest.mark.parametrize("conf, word_in_message", _conf_insufficient_keys_data())
def test_invalid_config_required_keys(tmp_path: Path, conf, word_in_message):
    """Tests loading an invalid config with insufficient keys"""
    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    with pytest.raises(Exception) as e:
        config_loader.load(str(config_path))

    assert word_in_message in e.value.message  # type: ignore


def _conf_invalid_additional_keys_data():
    confs = [
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {},
            "invalid_in_root": "bar",
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                    "invalid_in_service_config": "bar",
                }
            },
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "globals": {
                "invalid_in_globals": "bar",
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
                "invalid_in_alarm_config": "bar",
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {
                    "invalid_in_default_alarm_params": "bar",
                },
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                    "alarm_param_overrides": {
                        "m": {
                            "invalid_in_alarm_param_overrides": 1,
                        }
                    },
                }
            },
        },
    ]
    words = [
        "invalid_in_root",
        "invalid_in_service_config",
        "invalid_in_globals",
        "invalid_in_alarm_config",
        "invalid_in_default_alarm_params",
        "invalid_in_alarm_param_overrides",
    ]

    return zip(confs, words)


@pytest.mark.parametrize("conf, word_in_message", _conf_invalid_additional_keys_data())
def test_invalid_additional_keys(tmp_path: Path, conf, word_in_message):
    """Tests loading a config with additional invalid key"""
    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    with pytest.raises(Exception) as e:
        config_loader.load(str(config_path))

    assert word_in_message in e.value.message  # type: ignore


def _conf_invalid_key_name_data():
    confs = [
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "globals": {
                "target_resource_tags": {
                    "inval;d": "value",
                },
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {
                "invalid$service": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                }
            },
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                    "target_resource_tags": {
                        "inva#ld": "value",
                    },
                }
            },
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {},
            },
            "service_config": {
                "myservice": {
                    "provider_class_name": "",
                    "resource_type_filter": "",
                    "namespace": "",
                    "metrics": ["m"],
                    "alarm_param_overrides": {
                        "inv@lid": {"Threshold": 1},
                    },
                },
            },
        },
    ]
    words = [
        "inval;d",
        "invalid$service",
        "inva#ld",
        "inv@lid",
    ]

    return zip(confs, words)


@pytest.mark.parametrize("conf, word_in_message", _conf_invalid_key_name_data())
def test_invalid_key_name(tmp_path: Path, conf, word_in_message):
    """Tests loading a config with additional invalid key"""
    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    with pytest.raises(Exception) as e:
        config_loader.load(str(config_path))

    assert word_in_message in e.value.message  # type: ignore


def _conf_invalid_value_type_data():
    confs = [
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {
                    "Period": "1",
                },
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {
                    "EvaluationPeriods": 1.25,
                },
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {
                    "Threshold": 0.9,
                },
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {
                    "ComparisonOperator": "LessThanUpperThreshold",
                },
            },
            "service_config": {},
        },
        {
            "alarm_config": {
                "alarm_name_prefix": "aaa",
                "alarm_actions": [],
                "default_alarm_params": {
                    "TreatMissingData": 10,
                },
            },
            "service_config": {},
        },
    ]
    words = [
        "1",
        "1.25",
        "0.9",
        "LessThanUpperThreshold",
        "10",
    ]

    return zip(confs, words)


@pytest.mark.parametrize("conf, word_in_message", _conf_invalid_value_type_data())
def test_invalid_value_type(tmp_path: Path, conf, word_in_message):
    """Tests loading a config with additional invalid key"""
    config_path = tmp_path / "config.json"

    with open(config_path, "w") as f:
        json.dump(conf, f)

    with pytest.raises(Exception) as e:
        config_loader.load(str(config_path))

    assert word_in_message in e.value.message  # type: ignore
