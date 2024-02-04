import boto3
import pytest
from moto import mock_apigateway

from alarm_craft.models import AlarmProps, MetricAlarmParam, TargetResource

default_alarm_namespace = "AWS/ApiGateway"


@pytest.fixture()
def restapi():
    """Create three rest apis for tests

    Yields:
        ApiGatewayClient : mocked by moto
    """
    with mock_apigateway():
        apigateway_client = boto3.client("apigateway")
        apigateway_client.create_rest_api(
            name="restapi-1",
            tags={
                "tagkey1": "tagvalue1",
            },
        )
        apigateway_client.create_rest_api(
            name="restapi-2",
            tags={
                "tagkey1": "tagvalue1",
                "tagkey2": "tagvalue2",
            },
        )
        apigateway_client.create_rest_api(
            name="restapi-3",
            tags={
                "tagkey1": "tagvalue1",
                "tagkey2": "tagvalue2",
                "tagkey3": "tagvalue3",
            },
        )
        yield apigateway_client


@pytest.mark.usefixtures("restapi")
def test_apigateway_provider_basic():
    """Test for ApiGatewayMetricsProvider

    Args:
        mocker (MockerFixture): mocker
    """
    from alarm_craft.monitoring_targets.target_metrics_provider_apigw import ApiGatewayMetricsProvider

    alarm_metric_name = "TestsCount"
    resource_name1 = "restapi-1"
    resource_name2 = "restapi-2"
    resource_name3 = "restapi-3"
    config = _config(
        alarm_metrics=[alarm_metric_name],
    )

    target = ApiGatewayMetricsProvider(config, "apigateway")
    alarms = list(target.get_metric_alarms())

    assert alarms == [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=resource_name1,
            ),
            AlarmProps=AlarmProps(
                MetricName=alarm_metric_name,
                Namespace=default_alarm_namespace,
                Dimensions=[{"Name": "ApiName", "Value": resource_name1}],
            ),
        ),
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=resource_name2,
            ),
            AlarmProps=AlarmProps(
                MetricName=alarm_metric_name,
                Namespace=default_alarm_namespace,
                Dimensions=[{"Name": "ApiName", "Value": resource_name2}],
            ),
        ),
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=resource_name3,
            ),
            AlarmProps=AlarmProps(
                MetricName=alarm_metric_name,
                Namespace=default_alarm_namespace,
                Dimensions=[{"Name": "ApiName", "Value": resource_name3}],
            ),
        ),
    ]


def _resource_tags_api_test_param():
    tags = [
        {"tagkey1": "tagvalue1"},
        {"tagkey2": "tagvalue2"},
        {"tagkey3": "tagvalue3"},
        {
            "tagkey1": "tagvalue1",
            "tagkey2": "tagvalue2",
        },
        {
            "tagkey1": "tagvalue1",
            "tagkey2": "tagvalue2",
            "tagkey3": "tagvalue3",
        },
        {
            "tagkey1": "tagvalue1",
            "tagkey3": "tagvalue3",
        },
        {
            "tagkey1": "tagvalue2",
        },
        {
            "tagkey2": "tagvalue1",
        },
        {},  # no filter to retrieve all
    ]
    resources = [
        ["restapi-1", "restapi-2", "restapi-3"],
        ["restapi-2", "restapi-3"],
        ["restapi-3"],
        ["restapi-2", "restapi-3"],
        ["restapi-3"],
        ["restapi-3"],
        [],
        [],
        ["restapi-1", "restapi-2", "restapi-3"],
    ]

    return zip(tags, resources)


@pytest.mark.usefixtures("restapi")
@pytest.mark.parametrize("tags, resource_names", _resource_tags_api_test_param())
def test_apigateway_provider_tag_filter(tags, resource_names):
    """Test for ApiGatewayMetricsProvider tag filters

    Args:
        tags (dict): tags
        resource_names (list[str]): list of resource names
    """
    from alarm_craft.monitoring_targets.target_metrics_provider_apigw import ApiGatewayMetricsProvider

    alarm_metric_name = "TestsCount"
    config = _config(
        target_resource_tags=tags,
        alarm_metrics=[alarm_metric_name],
    )

    target = ApiGatewayMetricsProvider(config, "apigateway")
    alarms = list(target.get_metric_alarms())

    assert resource_names == [a["TargetResource"]["ResourceName"] for a in alarms]


@pytest.mark.usefixtures("restapi")
def test_apigateway_provider_through_get_target_metrics():
    """Test for ApiGatewayMetricsProvider through get_target_metrics()"""
    from alarm_craft.monitoring_targets import get_target_metrics

    config = {
        "resources": {
            "apigateway": _config(
                target_resource_type="apigateway:restapi",
                alarm_metrics=["MyMetric"],
            )
        }
    }

    alarm_params = list(get_target_metrics(config))

    expects = [
        ("restapi-1", "MyMetric"),
        ("restapi-2", "MyMetric"),
        ("restapi-3", "MyMetric"),
    ]
    actuals = [(a["TargetResource"]["ResourceName"], a["AlarmProps"]["MetricName"]) for a in alarm_params]
    assert expects == actuals


def _config(
    target_resource_type: str = "",
    target_resource_tags: dict[str, str] = {},
    alarm_metrics: list[str] = ["NumOfTestFailures"],
):
    return {
        "target_resource_type": target_resource_type,
        "target_resource_tags": target_resource_tags,
        "alarm": {
            "metrics": alarm_metrics,
        },
    }
