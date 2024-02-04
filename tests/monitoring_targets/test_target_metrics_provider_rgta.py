import pytest
from pytest_mock import MockerFixture

from alarm_craft.monitoring_targets import get_target_metrics


def _test_params(name1: str = "test1"):
    target_resource_type = [
        "lambda:function",
        "sns:topic",
        "sqs:queue",
        "states:stateMachine",
        "events:rule",
    ]
    service_name = [
        "lambda",
        "sns",
        "sqs",
        "stepfunctions",
        "event",
    ]
    resource_type = [
        ":function",
        "",  # topic
        "",  # queue
        ":statemachine",
        ":rule",
    ]
    name_sep = [
        ":",
        ":",
        ":",
        ":",
        "/",
    ]

    arn = [
        f"arn:aws:{s}:ap-northeast-1:123456789012{resource_type[i]}{name_sep[i]}{name1}"
        for i, s in enumerate(service_name)
    ]

    index_for_sfn = 3  # take care for this magic number in case you add a param
    dimensions = [
        [{"Name": "FunctionName", "Value": name1}],
        [{"Name": "TopicName", "Value": name1}],
        [{"Name": "QueueName", "Value": name1}],
        [{"Name": "StateMachineArn", "Value": arn[index_for_sfn]}],
        [{"Name": "RuleName", "Value": name1}],
    ]
    return zip(target_resource_type, service_name, arn, dimensions)


@pytest.mark.parametrize("target_resource_type, service_name, arn, dimensions", _test_params())
def test_inherit_metrics_provider(mocker: MockerFixture, target_resource_type, service_name, arn, dimensions):
    """Test provider classes inherited from ResourceGroupsTaggingAPITargetMetricsProviderBase

    Args:
        mocker (MockerFixture): mocker
        provider_type (ResourceGroupsTaggingAPITargetMetricsProviderBase): provider class
        service_name (str): service name
        arn (str): arn
        dimensions (list): alarm dimensions
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    resource_name = "test1"
    alarm_metric_name = "NumOfTestFailure"
    config = {
        "resources": {
            service_name: {
                "target_resource_type": target_resource_type,
                "target_resource_name_pattern": "^test1$",
                "alarm": {
                    "metrics": [alarm_metric_name],
                },
            },
        },
    }

    mock_get_resources.return_value = {
        "ResourceTagMappingList": [
            {"ResourceARN": arn},
        ]
    }

    alarms = list(get_target_metrics(config))
    assert len(alarms) == 1
    assert alarms[0]["TargetResource"]["ResourceName"] == resource_name
    assert alarms[0]["AlarmProps"]["MetricName"] == alarm_metric_name
    assert alarms[0]["AlarmProps"]["Dimensions"] == dimensions


@pytest.mark.parametrize("target_resource_type, service_name, arn, dimensions", _test_params())
def test_inherit_metrics_provider_no_match_pattern(
    mocker: MockerFixture, target_resource_type, service_name, arn, dimensions
):
    """Test provider classes inherited from ResourceGroupsTaggingAPITargetMetricsProviderBase

    Args:
        mocker (MockerFixture): mocker
        provider_type (ResourceGroupsTaggingAPITargetMetricsProviderBase): provider class
        service_name (str): service name
        arn (str): arn
        dimensions (list): alarm dimensions
    """
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    alarm_metric_name = "NumOfTestFailure"
    config = {
        "resources": {
            service_name: {
                "target_resource_type": target_resource_type,
                "target_resource_name_pattern": "test2",
                "alarm": {
                    "metrics": [alarm_metric_name],
                },
            },
        },
    }

    mock_get_resources.return_value = {
        "ResourceTagMappingList": [
            {"ResourceARN": arn},
        ]
    }

    alarms = list(get_target_metrics(config))
    assert len(alarms) == 0


def test_get_target_metrics(mocker: MockerFixture):
    """Test get_target_metrics()

    Test with config specifying provider classes inherited
    from ResourceGroupsTaggingAPITargetMetricsProviderBase

    Args:
        mocker (MockerFixture): mocker
    """
    resource_name = "test-225"
    resource_configs = {}
    mock_result = {}
    expects: list[dict] = []
    for target_resource_type, service_name, arn, dimensions in _test_params(resource_name):
        namespace = "AWS/" + service_name
        metric_name = "TestMetric"
        resource_configs[service_name] = {
            "target_resource_type": target_resource_type,
            "alarm": {
                "namespace": namespace,
                "metrics": [metric_name],
            },
        }
        mock_result[target_resource_type] = [
            {"ResourceARN": arn},
        ]
        expects.append(
            {
                "TargetResource": {
                    "ResourceName": resource_name,
                },
                "AlarmProps": {
                    "Namespace": namespace,
                    "MetricName": metric_name,
                    "Dimensions": dimensions,
                },
            }
        )

    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources

    def _mock_do_get_resources(*args, **kwargs):
        res_types = kwargs["ResourceTypeFilters"]
        return {"ResourceTagMappingList": mock_result[res_types[0]]}

    mock_get_resources.side_effect = _mock_do_get_resources

    config = {
        "resources": resource_configs,
    }

    alarm_params = list(get_target_metrics(config))
    for i, expected_param in enumerate(expects):
        assert expected_param["TargetResource"] == alarm_params[i]["TargetResource"]
        for k, v in expected_param["AlarmProps"].items():
            assert alarm_params[i]["AlarmProps"][k] == v  # type: ignore
