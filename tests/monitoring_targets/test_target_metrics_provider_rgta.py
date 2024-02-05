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
        "apigateway:apis",
        "scheduler:schedule-group",
    ]
    service_name = [
        "lambda",
        "sns",
        "sqs",
        "stepfunctions",
        "event",
        "apigateway",
        "scheduler",
    ]
    resource_type = [
        ":function",
        "",  # topic
        "",  # queue
        ":statemachine",
        ":rule",
        ":/apis",
        ":schedule-group",
    ]
    name_sep = [
        ":",
        ":",
        ":",
        ":",
        "/",
        "/",
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
        [{"Name": "ApiId", "Value": name1}],
        [{"Name": "ScheduleGroup", "Value": name1}],
    ]
    namespaces = [
        "AWS/Lambda",
        "AWS/SNS",
        "AWS/SQS",
        "AWS/States",
        "AWS/Events",
        "AWS/ApiGateway",
        "AWS/Scheduler",
    ]
    return zip(target_resource_type, service_name, arn, dimensions, namespaces)


@pytest.mark.parametrize("target_resource_type, service_name, arn, dimensions, namespace", _test_params())
def test_inherit_metrics_provider(
    mocker: MockerFixture, target_resource_type, service_name, arn, dimensions, namespace
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
    assert alarms[0]["AlarmProps"]["Namespace"] == namespace


@pytest.mark.parametrize("target_resource_type, service_name, arn, dimensions, namespace", _test_params())
def test_inherit_metrics_provider_no_match_pattern(
    mocker: MockerFixture, target_resource_type, service_name, arn, dimensions, namespace
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


def test_custom_namespaces(mocker: MockerFixture):
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
    for target_resource_type, service_name, arn, dimensions, _ in _test_params(resource_name):
        namespace = "Custom/" + service_name  # custom namespace
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


def test_apigateway_v2_metrics_provider_create_resource_filter(mocker: MockerFixture):
    """Test create_resource_filter() of ApiGatewayV2MetricsProvider

    Args:
        mocker (MockerFixture): mocker
    """
    config = {
        "resources": {
            "test": {
                "target_resource_type": "apigateway:apis",
                "alarm": {
                    "metrics": ["Test"],
                },
            },
        },
    }
    raw_arns = [
        "arn:aws:apigateway:ap-northeast-1::/apis/abcd1234AB",
        "arn:aws:apigateway:ap-northeast-1::/apis/abcd1234AB/stages/$default",
        "arn:aws:apigateway:ap-northeast-1::/apis/efgh5678CD",
        "arn:aws:apigateway:ap-northeast-1::/apis/efgh5678CD/stages/ProdCD",
        "arn:aws:apigateway:ap-northeast-1::/apis/ijkl9012CD",
        "arn:aws:apigateway:ap-northeast-1::/apis/ijkl9012CD/stages/StageAB",
    ]
    mock_resp = {"ResourceTagMappingList": [{"ResourceARN": arn} for arn in raw_arns]}
    mock_boto3 = mocker.patch("alarm_craft.monitoring_targets.target_metrics_provider_rgta.boto3")
    mock_get_resources = mock_boto3.client.return_value.get_resources
    mock_get_resources.return_value = mock_resp

    alarm_params = list(get_target_metrics(config))
    actual = [a["TargetResource"]["ResourceName"] for a in alarm_params]
    assert actual == [
        "abcd1234AB",
        "efgh5678CD",
        "ijkl9012CD",
    ]

    config["resources"]["test"]["target_resource_name_pattern"] = ".*CD$"
    alarm_params = list(get_target_metrics(config))
    actual = [a["TargetResource"]["ResourceName"] for a in alarm_params]
    assert actual == [
        "efgh5678CD",
        "ijkl9012CD",
    ]
