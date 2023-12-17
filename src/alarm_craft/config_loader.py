import json
from typing import Optional, Union

import jsonschema

ConfigValue = Union[str, int, list["ConfigValue"], dict[str, "ConfigValue"]]  # type: ignore


def load(file_path: Optional[str]) -> dict[str, ConfigValue]:
    """Loads configuration from specified file path

    Args:
        file_path (str): file path, or None if use the default config

    Returns:
        dict[str, ConfigValue]: config dict
    """
    if file_path:
        with open(file_path, "r") as f:
            config = json.load(f)
        jsonschema.validate(config, _json_schema())
    else:
        config = _default_config()

    return _merge_configs(config)


def save_default_config(file_name: str = "config.json") -> None:
    """Save default config to file

    Args:
        file_name (str, optional): file to save. Defaults to "config.json".
    """
    with open(file_name, "w") as file:
        json.dump(_default_config(), file)


def _merge_configs(config: dict[str, ConfigValue]) -> dict[str, ConfigValue]:
    glo = config.get("globals")
    if not glo:
        return config

    assert isinstance(glo, dict)
    merged = {}
    service_configs = config["service_config"]
    assert isinstance(service_configs, dict)
    for key in service_configs:
        merged[key] = _merge_service_config(glo, service_configs[key])

    return dict(config, **{"service_config": merged})


def _merge_service_config(conf1: dict[str, ConfigValue], conf2: dict[str, ConfigValue]) -> dict[str, ConfigValue]:
    ret = conf1.copy()
    for k, v2 in conf2.items():
        v1 = ret.get(k)
        if v1:
            if isinstance(v1, dict) and isinstance(v2, dict):
                ret[k] = _merge_service_config(v1, v2)
            elif isinstance(v1, list) and isinstance(v2, list):
                ret[k] = v1 + v2
            else:
                ret[k] = v2  # overwrite
        else:
            ret[k] = v2

    return ret


def _default_config() -> dict[str, ConfigValue]:
    return {
        "alarm_config": {
            "alarm_name_prefix": "cw-metric-alarm-autogen-",
            "alarm_actions": [],
            "default_alarm_params": {},
        },
        "service_config": {},
    }


def _json_schema() -> dict[str, ConfigValue]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "aws_create_alarm config schema",
        "description": "json validation",
        "type": "object",
        "properties": {
            "alarm_config": {
                "type": "object",
                "properties": {
                    "alarm_name_prefix": {"type": "string"},
                    "alarm_actions": {"type": "array", "items": {"type": "string"}},
                    "default_alarm_params": {"$ref": "#/definitions/alarm_params"},
                    "alarm_tagging": {"$ref": "#/definitions/tags"},
                    "api_call_intervals_in_millis": {"type": "integer"},
                },
                "required": [
                    "alarm_name_prefix",
                    "alarm_actions",
                    "default_alarm_params",
                ],
                "additionalProperties": False,
            },
            "globals": {
                "type": "object",
                "properties": {
                    "target_resource_name_pattern": {"type": "string"},
                    "target_resource_tags": {"$ref": "#/definitions/tags"},
                },
                "additionalProperties": False,
            },
            "service_config": {
                "type": "object",
                "patternProperties": {"^[\\-0-9A-Za-z]*$": {"$ref": "#/definitions/service_config"}},
                "additionalProperties": False,
            },
        },
        "required": [
            "alarm_config",
            "service_config",
        ],
        "additionalProperties": False,
        "definitions": {
            "service_config": {
                "type": "object",
                "properties": {
                    "provider_class_name": {"type": "string"},
                    "resource_type_filter": {"type": "string"},
                    "target_resource_name_pattern": {"type": "string"},
                    "target_resource_tags": {"$ref": "#/definitions/tags"},
                    "namespace": {"type": "string"},
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "alarm_param_overrides": {
                        "type": "object",
                        "patternProperties": {"^[0-9A-Za-z]*$": {"$ref": "#/definitions/alarm_params"}},
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "provider_class_name",
                    "resource_type_filter",
                    "namespace",
                    "metrics",
                ],
                "additionalProperties": False,
            },
            "alarm_params": {
                "type": "object",
                "properties": {
                    "Statistic": {"type": "string"},
                    "Period": {"type": "integer"},
                    "EvaluationPeriods": {"type": "integer"},
                    "Threshold": {"type": "integer"},
                    "ComparisonOperator": {
                        "type": "string",
                        "enum": [
                            "GreaterThanOrEqualToThreshold",
                            "GreaterThanThreshold",
                            "GreaterThanUpperThreshold",
                            "LessThanLowerOrGreaterThanUpperThreshold",
                            "LessThanLowerThreshold",
                            "LessThanOrEqualToThreshold",
                            "LessThanThreshold",
                        ],
                    },
                    "TreatMissingData": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "tags": {
                "type": "object",
                "patternProperties": {"^[0-9A-Za-z.:+=@_/-]*$": {"type": "string"}},
                "minProperties": 1,
                "additionalProperties": False,
            },
        },
    }
