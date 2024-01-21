from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, Mapping, Optional, Protocol, Sequence, TypeVar

from alarm_craft.models import MetricAlarmParam, ResourceConfig


class TargetMetricsProvider(Protocol):
    """Target Metrics Provider

    Args:
        Protocol (_type_): protocol
    """

    def get_metric_alarms(self) -> Iterable[MetricAlarmParam]:
        """Gets metric alarms

        Returns:
            Iterable[MetricAlarmParam]: list of metric alarms
        """
        pass


T = TypeVar("T")


class TargetMetricsProviderBase(ABC, Generic[T]):
    """Target Metrics Provider Base

    Args:
        ABC (_type_): abstract class
        Generic (_type_): type
    """

    def __init__(self, resource_config: ResourceConfig, resource_config_name: str):
        """Constructor

        Args:
            resource_config (ResourceAlarmConfig): resource config dict
            resource_config_name (str): key of the resource config
        """
        self.resource_config = resource_config
        self.resource_config_name = resource_config_name

    def get_metric_alarms(self) -> Iterable[MetricAlarmParam]:
        """Gets metric alarms

        Yields:
            Iterator[Iterable[MetricAlarmParam]]: list of metric alarm params
        """
        for resource in self.get_monitoring_target_resources():
            for metric in self.metric_names(resource):
                param: MetricAlarmParam = {
                    "TargetResource": {
                        "ResourceName": self.get_resource_name(resource),
                    },
                    "AlarmProps": {
                        "MetricName": metric,
                        "Namespace": self.namespace(),
                        "Dimensions": self.dimensions(metric, resource),
                    },
                }

                param_overrides = self.param_overrides(metric, resource)
                if param_overrides:
                    # param_overrides is a AlarmProps ensured by jsonschema checking
                    param["AlarmProps"].update(param_overrides)  # type: ignore

                yield param

    @abstractmethod
    def get_monitoring_target_resources(self) -> Iterable[T]:
        """Gets monitoring target resources

        Returns:
            Iterable[T]: target resources
        """
        pass

    def namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return str(self.resource_config["alarm"]["namespace"])

    def metric_names(self, resource: T) -> Sequence[str]:
        """Gets metric names

        Args:
            resource (T): resource

        Returns:
            list[str]: list of metric names
        """
        metrics = self.resource_config["alarm"]["metrics"]
        return metrics

    @abstractmethod
    def dimensions(self, metric_name: str, resource: T) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            resource (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        pass

    def param_overrides(self, metric_name: str, resource: T) -> Optional[Mapping[str, Any]]:
        """Gets alarm overrides

        Args:
            metric_name (str): metric name
            resource (T): resource

        Returns:
            Mapping[str, Any]: alarm param overrides
        """
        param_overrides = self.resource_config["alarm"].get("alarm_param_overrides")
        if param_overrides:
            return param_overrides.get(metric_name)

        return None

    @abstractmethod
    def get_resource_name(self, resource: T) -> str:
        """Gets resource name

        Args:
            resource (T): resource

        Returns:
            str: resource name
        """
        pass