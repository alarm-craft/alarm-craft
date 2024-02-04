from typing import Iterable, Mapping, Optional, Sequence

import boto3

from .target_metrics_provider import TargetMetricsProviderBase, metric_provider


@metric_provider("apigateway:restapi")
class ApiGatewayMetricsProvider(TargetMetricsProviderBase[str]):
    """API Gateway Metrics Provider"""

    def get_monitoring_target_resources(self) -> Iterable[str]:
        """Gets monitoring target resources

        Returns:
            Iterable[str]: monitoring target resources
        """
        target_tags = self.resource_config.get("target_resource_tags")

        client = boto3.client("apigateway")
        try:
            resources = client.get_rest_apis()["items"]
            return [res["name"] for res in resources if self._contains_tags(res["tags"], target_tags)]

        finally:
            pass
            # client.close()

    def _contains_tags(self, actual_tags: Mapping[str, str], expected_tags: Optional[Mapping[str, str]]) -> bool:
        if expected_tags:
            tags = actual_tags.items()
            contains_all_expected_tags = all(tag in tags for tag in expected_tags.items())
            return contains_all_expected_tags
        else:
            return True

    def get_resource_name(self, api_name: str) -> str:
        """Gets resource name

        Args:
            api_name (T): resource

        Returns:
            str: resource name
        """
        return api_name

    def dimensions(self, metric_name: str, api_name: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            api_name (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        return [{"Name": "ApiName", "Value": api_name}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/ApiGateway"
