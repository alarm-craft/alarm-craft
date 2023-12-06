import boto3
import pytest
from moto import mock_apigateway


@pytest.fixture()
def restapi():
    """Create three rest apis for tests

    Yields:
        ApiGatewayClient : mocked by moto
    """
    with mock_apigateway():
        apigateway_client = boto3.client("apigateway")
        apigateway_client.create_rest_api(name="restapi-1", tags={"tagkey1": "tagvalue1"})
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
    from alarm_craft.monitoring_targets import ApiGatewayMetricsProvider, MetricAlarmParam

    alarm_name_prefix = "test_monitoring_targets_apigateway-"
    alarm_namespace = "AWS/APIGateway"
    alarm_metric_name = "TestsCount"
    resource_name = "restapi-3"
    config = _config(
        target_resource_tags={"tagkey3": "tagvalue3"},
        alarm_name_prefix=alarm_name_prefix,
        alarm_namespace=alarm_namespace,
        alarm_metrics=[alarm_metric_name],
    )

    target = ApiGatewayMetricsProvider(config, "apigateway")
    alarms = list(target.get_metric_alarms())

    assert alarms == [
        MetricAlarmParam(
            AlarmName=f"{alarm_name_prefix}{resource_name}-{alarm_metric_name}",
            AlarmDescription=f"Metric Alarm for `{alarm_metric_name}` of {resource_name}",
            MetricName=alarm_metric_name,
            Namespace=alarm_namespace,
            Dimensions=[{"Name": "ApiName", "Value": resource_name}],
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
    from alarm_craft.monitoring_targets import ApiGatewayMetricsProvider

    alarm_metric_name = "TestsCount"
    config = _config(
        target_resource_tags=tags,
        alarm_metrics=[alarm_metric_name],
    )

    target = ApiGatewayMetricsProvider(config, "apigateway")
    alarms = list(target.get_metric_alarms())

    assert [f"{r}-{alarm_metric_name}" for r in resource_names] == [a["AlarmName"] for a in alarms]


@pytest.mark.usefixtures("restapi")
def test_apigateway_provider_through_get_target_metrics():
    """Test for ApiGatewayMetricsProvider through get_target_metrics()"""
    from alarm_craft.monitoring_targets import get_target_metrics

    config = _config(alarm_metrics=["MyMetric"])
    alarm_params = list(get_target_metrics(config))

    expects = [
        ("restapi-1-MyMetric", "MyMetric"),
        ("restapi-2-MyMetric", "MyMetric"),
        ("restapi-3-MyMetric", "MyMetric"),
    ]
    actuals = [(a["AlarmName"], a["MetricName"]) for a in alarm_params]
    assert expects == actuals


def _config(
    alarm_name_prefix: str = "",
    resource_type_filter: str = "",
    target_resource_tags: dict[str, str] = {},
    alarm_namespace: str = "AWS/MyService",
    alarm_metrics: list[str] = ["NumOfTestFailures"],
):
    return {
        "alarm_config": {
            "alarm_name_prefix": alarm_name_prefix,
            "alarm_actions": [],
            "default_alarm_params": {},
        },
        "service_config": {
            "apigateway": {
                "provider_class_name": "ApiGatewayMetricsProvider",
                "resource_type_filter": resource_type_filter,
                "target_resource_tags": target_resource_tags,
                "namespace": alarm_namespace,
                "metrics": alarm_metrics,
            },
        },
    }
