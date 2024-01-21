from typing import Any, Iterable, Mapping

from alarm_craft.models import MetricAlarmParam

from .target_metrics_provider import TargetMetricsProvider
from .target_metrics_provider_apigw import ApiGatewayMetricsProvider
from .target_metrics_provider_rgta import (
    EventBridgeMetricsProvider,
    LambdaMetricsProvider,
    SfnMetricsProvider,
    SnsMetricsProvider,
    SqsMetricsProvider,
)


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


def _get_target_metrics_providers(config: Mapping[str, Any]) -> Iterable[TargetMetricsProvider]:
    for resource_config_name, resource_config in config["resources"].items():
        resource_type = resource_config["target_resource_type"]

        if resource_type == "lambda:function":
            yield LambdaMetricsProvider(resource_config, resource_config_name)
        elif resource_type == "states:stateMachine":
            yield SfnMetricsProvider(resource_config, resource_config_name)
        elif resource_type == "apigateway:restapi":
            yield ApiGatewayMetricsProvider(resource_config, resource_config_name)
        elif resource_type == "sns:topic":
            yield SnsMetricsProvider(resource_config, resource_config_name)
        elif resource_type == "sqs:queue":
            yield SqsMetricsProvider(resource_config, resource_config_name)
        elif resource_type == "events:rule":
            yield EventBridgeMetricsProvider(resource_config, resource_config_name)
        else:
            raise ValueError(f"no such resource type: ${resource_type}")
