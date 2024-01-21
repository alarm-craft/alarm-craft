from typing import Mapping, Sequence

import pytest
from pytest_mock import MockerFixture

from alarm_craft.models import AlarmProps, MetricAlarmParam, TargetResource
from alarm_craft.monitoring_targets.target_metrics_provider_rgta import (
    ResourceGroupsTaggingAPITargetMetricsProviderBase,
)


class MyTestMetricsProvider(ResourceGroupsTaggingAPITargetMetricsProviderBase):
    """MetricsProvider for test

    Args:
        ResourceGroupsTaggingAPITargetMetricsProviderBase: base class
    """

    def dimensions(self, metric_name: str, arn: str) -> Sequence[Mapping[str, str]]:
        """Returns dimensions

        Args:
            metric_name (str): metric name
            arn (str): ARN

        Returns:
            Sequence[Mapping[str, str]]: dimension
        """
        name = self.get_resource_name(arn)
        return [{"Name": "MyTestName", "Value": name}]


def test_base_provider(mocker: MockerFixture):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase

    Args:
        mocker (MockerFixture): mocker
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    alarm_namespace = "AWS/MyService"
    alarm_metric_name = "NumOfTestFailure"
    resource_name1 = "my-test-1"
    resource_name2 = "my-test-2"
    config = _config(alarm_namespace=alarm_namespace, alarm_metrics=[alarm_metric_name])

    mock_get_resources.return_value = {
        "ResourceTagMappingList": [
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name1},
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name2},
        ]
    }

    target = MyTestMetricsProvider(config, "myservice")
    alarms = list(target.get_metric_alarms())

    assert alarms == [
        MetricAlarmParam(
            TargetResource=TargetResource(ResourceName=resource_name1),
            AlarmProps=AlarmProps(
                MetricName=alarm_metric_name,
                Namespace=alarm_namespace,
                Dimensions=[{"Name": "MyTestName", "Value": resource_name1}],
            ),
        ),
        MetricAlarmParam(
            TargetResource=TargetResource(ResourceName=resource_name2),
            AlarmProps=AlarmProps(
                MetricName=alarm_metric_name,
                Namespace=alarm_namespace,
                Dimensions=[{"Name": "MyTestName", "Value": resource_name2}],
            ),
        ),
    ]


def _resource_tags_api_test_param():
    resource_types = ["myservice1:myresource1", "myservice2:myresource2"]
    tags = [
        {"mytag1": "value1"},
        {
            "mytag1": "value1",
            "mytag2": "value2",
        },
    ]
    filter_tag_expression = [
        [
            {"Key": "mytag1", "Values": ["value1"]},
        ],
        [{"Key": "mytag1", "Values": ["value1"]}, {"Key": "mytag2", "Values": ["value2"]}],
    ]

    return zip(resource_types, tags, filter_tag_expression)


@pytest.mark.parametrize("resource_type, resource_tags, converted_tag_expression", _resource_tags_api_test_param())
def test_base_provider_call_api(mocker: MockerFixture, resource_type: str, resource_tags, converted_tag_expression):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase at calling resourcegroupstaggingapi

    Args:
        mocker (MockerFixture): mocker
        resource_type (str): _description_
        resource_tags (_type_): _description_
        converted_tag_expression (_type_): _description_
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    config = _config(target_resource_type=resource_type, target_resource_tags=resource_tags)

    mock_get_resources.return_value = {"ResourceTagMappingList": []}

    target = MyTestMetricsProvider(config, "myservice")
    assert len(list(target.get_metric_alarms())) == 0

    mock_get_resources.assert_called_once_with(
        PaginationToken="", ResourceTypeFilters=[resource_type], TagFilters=converted_tag_expression
    )


def test_base_provider_with_resource_name_pattern(mocker: MockerFixture):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase with reource_name_pattern

    Args:
        mocker (MockerFixture): mocker
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    alarm_namespace = "AWS/MyService"
    alarm_metric_name = "NumOfTestFailure"
    pattern = "^test-(red|blue)-(bird|cat)"

    config = _config(alarm_namespace=alarm_namespace, alarm_metrics=[alarm_metric_name])
    config["target_resource_name_pattern"] = pattern

    resource_name1 = "test-red-dog-0001"
    resource_name2 = "test-blue-cat-0002"  # this is only the one match the pattern
    resource_name3 = "test-green-bird-0003"
    resource_name4 = "test-red-lion-0004"
    resource_name5 = "test-blue-monkey-0005"
    resource_name6 = "1test-red-bird-0001"
    mock_get_resources.return_value = {
        "ResourceTagMappingList": [
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name1},
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name2},
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name3},
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name4},
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name5},
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name6},
        ]
    }

    target = MyTestMetricsProvider(config, "myservice")
    result = list(target.get_metric_alarms())
    assert len(result) == 1
    assert resource_name2 in result[0]["TargetResource"]["ResourceName"]


def test_base_provider_multiple_metrics(mocker: MockerFixture):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase with multiple metrics

    Args:
        mocker (MockerFixture): mocker
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    alarm_metric_name1 = "NumOfTestFailure"
    alarm_metric_name2 = "NumOfTests"
    resource_name1 = "my-test-1"
    config = _config(alarm_metrics=[alarm_metric_name1, alarm_metric_name2])

    mock_get_resources.return_value = {
        "ResourceTagMappingList": [
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name1},
        ]
    }

    target = MyTestMetricsProvider(config, "myservice")
    alarms = list(target.get_metric_alarms())
    assert len(alarms) == 2
    assert [
        (resource_name1, alarm_metric_name1),
        (resource_name1, alarm_metric_name2),
    ] == [(a["TargetResource"]["ResourceName"], a["AlarmProps"]["MetricName"]) for a in alarms]


def test_base_provider_optional_config_key(mocker: MockerFixture):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase with some optional config keys not given

    Args:
        mocker (MockerFixture): mocker
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    target_resource_type = "type1"
    config = {
        "target_resource_type": target_resource_type,
        "alarm": {
            "namespace": "",
            "metrics": [],
        },
    }

    mock_get_resources.return_value = {"ResourceTagMappingList": []}

    target = MyTestMetricsProvider(config, "test")  # type: ignore
    assert len(list(target.get_metric_alarms())) == 0

    mock_get_resources.assert_called_once_with(PaginationToken="", ResourceTypeFilters=[target_resource_type])


def test_param_overrides(mocker: MockerFixture):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase with alarm param overrides

    Args:
        mocker (MockerFixture): mocker
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    alarm_metric_name1 = "NumOfTestFailure"
    alarm_metric_name2 = "NumOfTests"
    alarm_metric_name3 = "TestsThrottled"  # not overridden metric

    resource_name1 = "my-test-1"
    config = _config(alarm_metrics=[alarm_metric_name1, alarm_metric_name2, alarm_metric_name3])
    overrides = {
        "NumOfTestFailure": {
            "Threshold": 3600,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        },
        "NumOfTests": {
            "Statistic": "Average",
            "Period": 24,
            "EvaluationPeriods": 3,
            "TreatMissingData": "ignore",
        },
        "NoSuchMetric": {
            "Threshold": 500,
            "ComparisonOperator": "GreaterThanUpperThreshold",
        },
    }
    config["alarm"]["alarm_param_overrides"] = overrides

    mock_get_resources.return_value = {
        "ResourceTagMappingList": [
            {"ResourceARN": "arn:aws:myservice:ap-northeast-1:123456789012:myresource:" + resource_name1},
        ]
    }

    target = MyTestMetricsProvider(config, "myservice")
    alarms = list(target.get_metric_alarms())
    num_of_results = 3
    assert len(alarms) == num_of_results

    expects: list[dict] = [
        {
            "TargetResource": {
                "ResourceName": resource_name1,
            },
            "AlarmProps": {
                "MetricName": alarm_metric_name1,
                "Threshold": 3600,
                "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            },
        },
        {
            "TargetResource": {
                "ResourceName": resource_name1,
            },
            "AlarmProps": {
                "MetricName": alarm_metric_name2,
                "Statistic": "Average",
                "Period": 24,
                "EvaluationPeriods": 3,
                "TreatMissingData": "ignore",
            },
        },
        {
            "TargetResource": {
                "ResourceName": resource_name1,
            },
            "AlarmProps": {
                "MetricName": alarm_metric_name3,
            },
        },
    ]

    for i in range(num_of_results):
        assert expects[i]["TargetResource"] == alarms[i]["TargetResource"]
        for k, v in expects[i]["AlarmProps"].items():
            assert alarms[i]["AlarmProps"].get(k) == v


def test_api_pagenation(mocker: MockerFixture):
    """Test for ResourceGroupsTaggingAPITargetMetricsProviderBase on pagenation

    Args:
        mocker (MockerFixture): mocker
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    # todo:
    num_calls = 3
    next_token = ""

    def _mock_do_get_resources(*args, **kwargs):
        nonlocal num_calls, next_token
        assert num_calls > 0
        assert kwargs["PaginationToken"] == next_token

        arns = [f"arn:aws:myservice:ap-northeast-1:123456789012:myresource:name-{i}" for i in range(50)]
        resp = {"ResourceTagMappingList": [{"ResourceARN": arn} for arn in arns]}
        next_token = f"token-qwertyuiop-{num_calls}"

        if num_calls > 1:
            # more results
            resp["PaginationToken"] = next_token

        num_calls = num_calls - 1
        return resp

    mock_get_resources.side_effect = _mock_do_get_resources

    target = MyTestMetricsProvider(_config(), "myservice")
    alarms = list(target.get_metric_alarms())
    num_of_results = 50 * 3
    assert len(alarms) == num_of_results
    assert num_calls == 0


def _config(
    target_resource_type: str = "",
    target_resource_tags: dict[str, str] = {},
    alarm_namespace: str = "AWS/MyService",
    alarm_metrics: list[str] = ["NumOfTestFailures"],
):
    return {
        "target_resource_type": target_resource_type,
        "target_resource_tags": target_resource_tags,
        "alarm": {
            "namespace": alarm_namespace,
            "metrics": alarm_metrics,
        },
    }
