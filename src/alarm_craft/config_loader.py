import json
from os import path
from typing import Dict, List, Literal, Optional, TypedDict, Union

import jsonschema
import yaml

from . import config_schema

# type declaration
ConfigElement = Union[str, int, bool, "ConfigList", "ConfigValue"]
ConfigList = List[ConfigElement]
ConfigValue = Dict[str, ConfigElement]

# constants
DEFAULT_CONFIG_FILES = [
    "alarm-config.yaml",
    "alarm-config.yml",
    "alarm-config.json",
]


class ConfigFile(TypedDict):
    """Config File

    Args:
        TypedDict (_type_): typed dict
    """

    FilePath: str
    Type: Literal["json", "yaml"]


def load(file_path: Optional[str]) -> ConfigValue:
    """Loads configuration from specified file path

    Args:
        file_path (str): file path, or None if use the default config

    Returns:
        ConfigValue: config dict
    """
    config_file = _resolve_file_path(file_path)
    with open(config_file["FilePath"], "r") as f:
        if config_file["Type"] == "json":
            config = json.load(f)
        else:
            config = yaml.safe_load(f)
    jsonschema.validate(config, config_schema.get_schema())

    return _merge_configs(config)


def _config_file(config_file_path: str) -> ConfigFile:
    conf: ConfigFile = {
        "FilePath": config_file_path,
        "Type": "json",  # default
    }
    if config_file_path.endswith("yaml") or config_file_path.endswith("yml"):
        conf["Type"] = "yaml"

    return conf


def _resolve_file_path(file_path: Optional[str]) -> ConfigFile:
    if file_path:
        if path.exists(file_path):
            return _config_file(file_path)
        else:
            raise FileNotFoundError(file_path)
    else:
        for file_name in DEFAULT_CONFIG_FILES:
            if path.exists(file_name):
                return _config_file(file_name)

        raise ValueError("config file not found. locate `alarm-config.yaml` or specify `-c your-config.yaml`")


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


DEFAULT_ALARM_NAME_PREFIX = "alarm-craft-autogen-"
DEFAULT_ALARM_PARAMS: ConfigValue = {
    "Statistic": "Sum",
    "Period": 60,
    "EvaluationPeriods": 1,
    "Threshold": 1,
    "ComparisonOperator": "GreaterThanOrEqualToThreshold",
    "TreatMissingData": "notBreaching",
}
DEFAULT_API_CALL_INTERVAL = 334


def default_global_config() -> ConfigValue:
    """Gets default configuration of `global` key

    Returns:
        ConfigValue: default global config dict
    """
    return {
        "alarm": {
            "alarm_name_prefix": DEFAULT_ALARM_NAME_PREFIX,
            "alarm_actions": [],
            "default_alarm_params": DEFAULT_ALARM_PARAMS,
        },
        "resource_filter": {},
        "api_call_intervals_in_millis": DEFAULT_API_CALL_INTERVAL,
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
