import re
from typing import Callable, Iterable, Mapping, Optional, Sequence

import boto3

from .target_metrics_provider import TargetMetricsProviderBase, metric_provider


class ResourceGroupsTaggingAPITargetMetricsProviderBase(TargetMetricsProviderBase[str]):
    """ResourceGroupsTaggingAPI target metrics provider base"""

    default_arn_pattern = re.compile("^arn:aws:[^:]*:[^:]*:[0-9]*:[^:]*:")
    arn_pattern_no_restype = re.compile("^arn:aws:[^:]*:[^:]*:[0-9]*:")
    arn_pattern_name_by_slash = re.compile("^arn:aws:[^:]*:[^:]*:[0-9]*:[^:]*/")

    def get_monitoring_target_resources(self) -> Iterable[str]:
        """Gets monitoring target resources

        Returns:
            Iterable[str]: monitoring target resources
        """
        resource_client = boto3.client("resourcegroupstaggingapi")
        try:
            tags = self.resource_config.get("target_resource_tags")
            pattern = self.resource_config.get("target_resource_name_pattern")
            resource_type = self.resource_config["target_resource_type"]
            request_param: dict = {
                "ResourceTypeFilters": [resource_type],
                "PaginationToken": "",
            }

            # tags condition
            if tags:
                tag_filters = [{"Key": k, "Values": [v]} for k, v in tags.items()]
                request_param["TagFilters"] = tag_filters

            filter_func = self.create_resource_filter(pattern)

            while True:
                resp = resource_client.get_resources(**request_param)

                yield from filter(filter_func, [r["ResourceARN"] for r in resp["ResourceTagMappingList"]])

                next_token = resp.get("PaginationToken")
                if next_token and next_token != "":
                    request_param["PaginationToken"] = next_token
                else:
                    # no more results
                    break

        finally:
            pass
            # resource_client.close()

    def get_resource_name(self, arn: str) -> str:
        """Gets resource name

        Args:
            arn (T): resource

        Returns:
            str: resource name
        """
        return self.default_arn_pattern.sub("", arn, 1)

    def create_resource_filter(self, pattern: Optional[str]) -> Callable[[str], bool]:
        """Gets resource filter function

        Args:
            pattern (str): filter condition for resource name

        Returns:
            Callable[[str], bool]: function of predicate for resource name matches
        """
        if pattern:
            return self._get_filter_by_resource_name_pattern(pattern)
        else:
            return ResourceGroupsTaggingAPITargetMetricsProviderBase._nofilter

    def _get_filter_by_resource_name_pattern(self, pattern: str) -> Callable[[str], bool]:
        regex = re.compile(pattern)

        def _filter_by_resource_name_pattern(arn: str) -> bool:
            return regex.match(self.get_resource_name(arn)) is not None

        return _filter_by_resource_name_pattern

    @classmethod
    def _nofilter(cls, _: str) -> bool:
        return True


#
# Implementations
#


@metric_provider("lambda:function")
class LambdaMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """Lambda Metric Provider"""

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        name = self.get_resource_name(arn)
        return [{"Name": "FunctionName", "Value": name}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/Lambda"


@metric_provider("states:stateMachine")
class SfnMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """StepFunctions Metrics Provider"""

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        return [{"Name": "StateMachineArn", "Value": arn}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/States"


@metric_provider("sns:topic")
class SnsMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """SNS Metrics Provider"""

    def get_resource_name(self, arn: str) -> str:
        """Gets resource name

        Args:
            arn (T): resource

        Returns:
            str: resource name
        """
        return self.arn_pattern_no_restype.sub("", arn, 1)

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        name = self.get_resource_name(arn)
        return [{"Name": "TopicName", "Value": name}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/SNS"


@metric_provider("sqs:queue")
class SqsMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """SQS Metric Provider"""

    def get_resource_name(self, arn: str) -> str:
        """Gets resource name

        Args:
            arn (T): resource

        Returns:
            str: resource name
        """
        return self.arn_pattern_no_restype.sub("", arn, 1)

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        name = self.get_resource_name(arn)
        return [{"Name": "QueueName", "Value": name}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/SQS"


@metric_provider("events:rule")
class EventBridgeMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """EventBridge Metrics Provider"""

    def get_resource_name(self, arn: str) -> str:
        """Gets resource name

        Args:
            arn (T): resource

        Returns:
            str: resource name
        """
        return self.arn_pattern_name_by_slash.sub("", arn, 1)

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        name = self.get_resource_name(arn)
        return [{"Name": "RuleName", "Value": name}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/Events"


@metric_provider("apigateway:apis")
class ApiGatewayV2MetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """API Gateway V2(HttpApi) Metrics Provider"""

    # api stage ARN is like below
    # "arn:aws:apigateway:ap-northeast-1::/apis/abcd1234fg/stages/$default"
    arn_api_stage = re.compile("^arn:aws:apigateway:[^:]*::/apis/[^/]*/stages/.*")

    def create_resource_filter(self, pattern: Optional[str]) -> Callable[[str], bool]:
        """Creates filter with default one and filter stage ARNs"""
        original_filter = super().create_resource_filter(pattern)

        def composed_filter(arn: str) -> bool:
            return original_filter(arn) and self.arn_api_stage.match(arn) is None

        return composed_filter

    def get_resource_name(self, arn: str) -> str:
        """Gets resource name

        Args:
            arn (T): resource

        Returns:
            str: resource name
        """
        return self.arn_pattern_name_by_slash.sub("", arn, 1)

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        api_id = self.get_resource_name(arn)
        return [{"Name": "ApiId", "Value": api_id}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/ApiGateway"


@metric_provider("scheduler:schedule-group")
class EventBridgeSchedulerMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """EventBridge Scheduler Metrics Provider"""

    def get_resource_name(self, arn: str) -> str:
        """Gets resource name

        Args:
            arn (T): resource

        Returns:
            str: resource name
        """
        # "arn:aws:scheduler:ap-northeast-1:123456789012:schedule-group/name-of-schedulegroup"
        return self.arn_pattern_name_by_slash.sub("", arn, 1)

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Gets alarm dimensions

        Args:
            metric_name (str): metric name
            arn (T): resource

        Returns:
            Sequence[Mapping[str, str]]: alarm dimensions
        """
        name = self.get_resource_name(arn)
        return [{"Name": "ScheduleGroup", "Value": name}]

    def get_default_namespace(self) -> str:
        """Gets alarm namespace

        Returns:
            str: alarm namespace
        """
        return "AWS/Scheduler"
