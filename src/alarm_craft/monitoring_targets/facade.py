import logging
import os
import pkgutil
from typing import Any, Iterable, Mapping

from alarm_craft.models import MetricAlarmParam

from .target_metrics_provider import TargetMetricsProvider, provider_class_name_postfix, provider_module_name_prefix

logger = logging.getLogger(__name__)


def get_target_metrics(config: Mapping[str, Any]) -> Iterable[MetricAlarmParam]:
    """Gets target metrics

    Args:
        config (dict[str, Any]): config dict

    Yields:
        Iterator[Iterable[MetricAlarmParam]]: metric alarm params
    """
    for provider in _get_target_metrics_providers(config):
        yield from provider.get_metric_alarms()


# implementations


def _get_provider_dict() -> dict[str, type[TargetMetricsProvider]]:
    """Gets a dict mapping resource_type and Provider classes

    Searches Provider classes and dynamically loads them

    Returns:
        dict[str, type[TargetMetricsProvider]]: mapping for resource_type and provider
    """
    repository = {}
    pkg = __package__
    curr_dir = os.path.dirname(__file__)
    logger.debug("package:%s, current dir:%s", pkg, curr_dir)
    for _, module_name, ispkg in pkgutil.iter_modules([curr_dir], pkg + "."):
        logger.debug("module_name: %s, ispkg: %s", module_name, ispkg)
        if module_name.startswith(provider_module_name_prefix):
            # import *_metrics_provider_* module
            module = __import__(name=module_name, fromlist=[""])
            for member in dir(module):
                if member.endswith(provider_class_name_postfix):
                    # Load *MetricsProvider class
                    cls = getattr(module, member)
                    if hasattr(cls, "resource_type"):
                        repository[cls.resource_type] = cls
                    else:
                        logger.warning(
                            "The class: %s is not registered, because it has no `@metric_provider('xxxxx')` decorator",
                            cls,
                        )
                        logger.debug("member of %s: %s", cls.__name__, dir(cls))

    return repository


def _get_target_metrics_providers(config: Mapping[str, Any]) -> Iterable[TargetMetricsProvider]:
    providers = _get_provider_dict()
    for resource_config_name, resource_config in config["resources"].items():
        resource_type = resource_config["target_resource_type"]
        provider = providers.get(resource_type)
        if provider:
            yield provider(resource_config, resource_config_name)
        else:
            raise ValueError(f"no such resource type: ${resource_type}")
