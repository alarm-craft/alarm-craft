import json
from typing import Dict, List, Optional, Union

import jsonschema

from . import config_schema

ConfigElement = Union[str, int, bool, "ConfigList", "ConfigValue"]
ConfigList = List[ConfigElement]
ConfigValue = Dict[str, ConfigElement]


def load(file_path: Optional[str]) -> ConfigValue:
    """Loads configuration from specified file path

    Args:
        file_path (str): file path, or None if use the default config

    Returns:
        ConfigValue: config dict
    """
    if file_path:
        with open(file_path, "r") as f:
            config = json.load(f)
        jsonschema.validate(config, config_schema.get_schema())
    else:
        # todo: consider how to handle this case
        raise ValueError("")

    return _merge_configs(config)


def _merge_configs(config: ConfigValue) -> ConfigValue:
    default_glo = default_global_config()
    glo = config.get("globals")
    if glo:
        assert isinstance(glo, dict)
        glo = _merge_dicts(default_glo, glo)
    else:
        glo = default_glo

    merged = {}
    glo_resource_filter = glo["resource_filter"]
    resources = config["resources"]
    for key in resources:  # type: ignore
        resource_config = _merge_dicts(glo_resource_filter, resources[key])  # type: ignore

        merged[key] = resource_config

    return dict(config, **{"globals": glo, "resources": merged})


def default_global_config() -> ConfigValue:
    """Gets default configuration of `global` key

    Returns:
        ConfigValue: default global config dict
    """
    return {
        "alarm": {
            "alarm_name_prefix": "alarm-craft-autogen-",
            "alarm_actions": [],
            "default_alarm_params": {
                "Statistic": "Sum",
                "Period": 60,
                "EvaluationPeriods": 1,
                "Threshold": 1,
                "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                "TreatMissingData": "notBreaching",
            },
        },
        "resource_filter": {},
        "api_call_intervals_in_millis": 334,
    }


def _merge_dicts(conf1: dict, conf2: dict) -> ConfigValue:
    ret = conf1.copy()
    for k, v2 in conf2.items():
        v1 = ret.get(k)
        if v1:
            if isinstance(v1, dict) and isinstance(v2, dict):
                ret[k] = _merge_dicts(v1, v2)
            elif isinstance(v1, list) and isinstance(v2, list):
                ret[k] = v1 + v2
            else:
                ret[k] = v2  # overwrite
        else:
            ret[k] = v2

    return ret
