import itertools
import time
from typing import Union

import boto3
import pytest
from moto import mock_cloudwatch
from mypy_boto3_cloudwatch.client import CloudWatchClient

from alarm_craft.alarm import AlarmHandler
from alarm_craft.config_loader import DEFAULT_ALARM_NAME_PREFIX, DEFAULT_ALARM_PARAMS
from alarm_craft.models import AlarmProps, MetricAlarmParam, TargetResource


@pytest.fixture()
def cloudwatch_client():
    """Create mock cloudwatch client for tests

    Yields:
        CloudWatchClient : mocked by moto
    """
    with mock_cloudwatch():
        cloudwatch_client = boto3.client("cloudwatch")
        yield cloudwatch_client


def _alarm_name_creation_param():
    prefix = ["alarm-craft-gen-", "abdcefg-"]
    resources = ["res1", "res2"]
    metrics = ["met1", "met2", "met3"]
    return list(itertools.product(prefix, resources, metrics))


@pytest.mark.parametrize("prefix, resource_name, alarm_metric", _alarm_name_creation_param())
def test_alarm_props_from_metric_alarm_params(cloudwatch_client: CloudWatchClient, prefix, resource_name, alarm_metric):
    """Tests creating an alarm with proper name / description

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        resource_name (str): resource name
        alarm_metric (str): alarm metric name
    """
    params: MetricAlarmParam = {
        "TargetResource": {
            "ResourceName": resource_name,
        },
        "AlarmProps": {
            "MetricName": alarm_metric,
        },
    }
    handler = AlarmHandler(_config(alarm_name_prefix=prefix))
    create_alarms, _, _ = handler.get_alarms_change_set([params])
    for alm in create_alarms:
        assert f"{prefix}{resource_name}-{alarm_metric}" == alm["AlarmName"]


def _alarm_test_params():
    return [
        (
            f"{DEFAULT_ALARM_NAME_PREFIX}resource-1",
            "12345678901234567890",
            "TestsCount",
            "AWS/MyService",
            [{"Name": "MyResourceName", "Value": "myresource-1"}],
        ),
        (
            f"{DEFAULT_ALARM_NAME_PREFIX}resource-2",
            "qwertyuiop",
            "NumOfTests",
            "AWS/XService",
            [{"Name": "TargetName", "Value": "myresource-800"}],
        ),
    ]


@pytest.mark.parametrize("alarm_name, alarm_desc, alarm_metric, alarm_namespace, alarm_dimension", _alarm_test_params())
def test_create_alarm_basic(
    cloudwatch_client: CloudWatchClient, alarm_name, alarm_desc, alarm_metric, alarm_namespace, alarm_dimension
):
    """Tests creating an alarm with proper attributes

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        alarm_name (str): alarm name
        alarm_desc (str): alarm description
        alarm_metric (str): alarm metric name
        alarm_namespace (str): alarm namespace
        alarm_dimension (list): alarm dimensions
    """
    handler = AlarmHandler(_config())

    alarm = AlarmProps(
        AlarmName=alarm_name,
        AlarmDescription=alarm_desc,
        MetricName=alarm_metric,
        Namespace=alarm_namespace,
        Dimensions=alarm_dimension,
    )

    handler.update_alarms([alarm], [], [])

    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm_name, AlarmTypes=["MetricAlarm"])

    curr_alarms = api_resp["MetricAlarms"]
    assert len(curr_alarms) == 1
    curr_alarm = curr_alarms[0]
    assert curr_alarm["AlarmName"] == alarm_name
    assert curr_alarm["AlarmDescription"] == alarm_desc
    assert curr_alarm["MetricName"] == alarm_metric
    assert curr_alarm["Namespace"] == alarm_namespace
    assert curr_alarm["Dimensions"] == alarm_dimension

    assert curr_alarm["AlarmActions"] == []

    # other properties are set as default
    for k, v in DEFAULT_ALARM_PARAMS.items():
        assert curr_alarm[k] == v  # type: ignore


def test_create_alarm_param_overrides(cloudwatch_client: CloudWatchClient):
    """Tests creating an alarm with param overrides

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
    """
    handler = AlarmHandler(_config())

    alarm_param = AlarmProps(
        AlarmName=f"{DEFAULT_ALARM_NAME_PREFIX}0001",
        AlarmDescription="",
        MetricName="dummy",
        Namespace="dummy",
        Dimensions=[],
        Statistic="Max",
        Period=86,
        EvaluationPeriods=512,
        Threshold=73,
        ComparisonOperator="LessThanThreshold",
        TreatMissingData="ignore",
    )

    handler.update_alarms([alarm_param], [], [])
    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=DEFAULT_ALARM_NAME_PREFIX, AlarmTypes=["MetricAlarm"])

    curr_alarms = api_resp["MetricAlarms"]
    assert len(curr_alarms) == 1
    curr_alarm = curr_alarms[0]

    for k, v in alarm_param.items():
        assert curr_alarm.get(k) == v


def _alarm_test_default_alarm_param():
    return [
        (
            {
                "Statistic": "Average",
                "Period": 95,
                "EvaluationPeriods": 95,
                "Threshold": 2,
                "ComparisonOperator": "GreaterThanThreshold",
                "TreatMissingData": "breaching",
            },
            {
                "Statistic": "Average",
                "Period": 95,
                "EvaluationPeriods": 95,
                "Threshold": 2,
                "ComparisonOperator": "GreaterThanThreshold",
                "TreatMissingData": "breaching",
            },
        ),
        (
            {
                "Statistic": "Maximum",
                "Period": 123,
                "EvaluationPeriods": 4,
                "Threshold": 1024,
                "ComparisonOperator": "LessThanOrEqualToThreshold",
                "TreatMissingData": "missing",
            },
            {
                "Statistic": "Maximum",
                "Period": 123,
                "EvaluationPeriods": 4,
                "Threshold": 1024,
                "ComparisonOperator": "LessThanOrEqualToThreshold",
                "TreatMissingData": "missing",
            },
        ),
    ]


@pytest.mark.parametrize("default_alarm_params, expects", _alarm_test_default_alarm_param())
def test_default_alarm_params(
    cloudwatch_client: CloudWatchClient,
    default_alarm_params: dict[str, Union[str, int]],
    expects: dict[str, Union[str, int]],
):
    """Tests creating an alarm with default alarm param

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        default_alarm_params (dict[str, Union[str, int]]): config value of `default_alarm_params`
        expects (dict[str, Union[str, int]]): expected alarm properties
    """
    config = _config()
    config["globals"]["alarm"]["default_alarm_params"] = default_alarm_params

    alarm_param = AlarmProps(
        AlarmName="alarm-name-0001",
        AlarmDescription="",
        MetricName="dummy",
        Namespace="dummy",
        Dimensions=[],
    )

    handler = AlarmHandler(config)
    handler.update_alarms([alarm_param], [], [])
    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm_param["AlarmName"], AlarmTypes=["MetricAlarm"])

    curr_alarms = api_resp["MetricAlarms"]
    assert len(curr_alarms) == 1
    curr_alarm = curr_alarms[0]

    for k, v in expects.items():
        assert curr_alarm.get(k) == v


def _alarm_test_actions():
    return [
        (
            "alarm1",
            ["action1"],
            [],
            ["action1"],
        ),
        (
            "alarm2",
            [],
            ["action2"],
            ["action2"],
        ),
        (
            "alarm3",
            ["action1", "action11"],
            ["action2", "action22"],
            ["action1", "action11", "action2", "action22"],
        ),
    ]


@pytest.mark.parametrize("alarm_name, alarm_action_config, additional_alarm_actions, expects", _alarm_test_actions())
def test_create_alarm_with_action(
    cloudwatch_client: CloudWatchClient, alarm_name, alarm_action_config, additional_alarm_actions, expects
):
    """Tests creating an alarm with alarm actions

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        alarm_name (str): alarm name
        alarm_action_config (list): alarm actions specified in config
        additional_alarm_actions (list): alarm actions additionally given
        expects (list): alarm actions which is expectedly set in the created alarm
    """
    handler = AlarmHandler(_config(alarm_actions=alarm_action_config))

    alarm = AlarmProps(
        AlarmName=alarm_name,
        AlarmDescription="",
        MetricName="dummy",
        Namespace="dummy",
        Dimensions=[],
    )

    handler.update_alarms([alarm], [], additional_alarm_actions)

    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm_name, AlarmTypes=["MetricAlarm"])

    curr_alarms = api_resp["MetricAlarms"]
    assert len(curr_alarms) == 1
    curr_alarm = curr_alarms[0]
    assert curr_alarm["AlarmName"] == alarm_name
    assert curr_alarm["AlarmActions"] == expects
    assert curr_alarm["OKActions"] == expects
    assert curr_alarm["InsufficientDataActions"] == expects


def _alarm_test_tagging():
    return [
        (
            {
                "tagkey1": "value1",
            },
            [
                {
                    "Key": "tagkey1",
                    "Value": "value1",
                },
            ],
        ),
        (
            {
                "tagkey1": "value1",
                "tagkey2": "value2",
            },
            [
                {
                    "Key": "tagkey1",
                    "Value": "value1",
                },
                {
                    "Key": "tagkey2",
                    "Value": "value2",
                },
            ],
        ),
    ]


@pytest.mark.parametrize("tag_config, alarm_tag_expects", _alarm_test_tagging())
def test_create_alarm_with_tags(
    cloudwatch_client: CloudWatchClient, tag_config: dict[str, str], alarm_tag_expects: list[dict[str, str]]
):
    """Tests creating an alarm with alarm tags

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        tag_config (dict[str, str]): config for alarm tag
        alarm_tag_expects (list[dict[str, str]]): expected tags of created alarm
    """
    config = _config()
    config["globals"]["alarm"]["alarm_tagging"] = tag_config

    handler = AlarmHandler(config)

    alarm = AlarmProps(
        AlarmName=f"{DEFAULT_ALARM_NAME_PREFIX}0001111",
        AlarmDescription="",
        MetricName="dummy",
        Namespace="dummy",
        Dimensions=[],
    )

    handler.update_alarms([alarm], [], [])

    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm["AlarmName"], AlarmTypes=["MetricAlarm"])
    curr_alarms = api_resp["MetricAlarms"]
    assert len(curr_alarms) == 1
    tag_api_resp = cloudwatch_client.list_tags_for_resource(ResourceARN=curr_alarms[0]["AlarmArn"])
    assert tag_api_resp["Tags"] == alarm_tag_expects


@pytest.mark.parametrize("interval", [99, 334, 512])
def test_update_with_interval(cloudwatch_client: CloudWatchClient, interval: int):
    """Tests creating alarms with specified interval

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        interval (int): interval in millis
    """
    num_api_calls = 3
    config = _config()
    config["globals"]["api_call_intervals_in_millis"] = interval

    handler = AlarmHandler(config)

    alarms = [
        AlarmProps(
            AlarmName=f"{DEFAULT_ALARM_NAME_PREFIX}{i}",
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for i in range(num_api_calls)
    ]

    before = time.time()
    handler.update_alarms(alarms, [], [])
    after = time.time()

    curr_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=DEFAULT_ALARM_NAME_PREFIX,
        AlarmTypes=["MetricAlarm"],
    )["MetricAlarms"]

    assert len(curr_alarms) == num_api_calls
    assert (after - before) >= (interval / 1000 * num_api_calls)


@pytest.mark.parametrize("interval", [99, 334, 512])
def test_delete_with_interval(cloudwatch_client: CloudWatchClient, interval: int):
    """Tests deleting alarms with specified interval

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
        interval (int): interval in millis
    """
    num_api_calls = 3
    config = _config()
    config["globals"]["api_call_intervals_in_millis"] = interval

    handler = AlarmHandler(config)

    num_alarms = (num_api_calls - 1) * 100 + 1  # ex.) 201 makes three calls of 100, 100 and 1.
    alarm_names = [f"{DEFAULT_ALARM_NAME_PREFIX}{i}" for i in range(num_alarms)]

    for name in alarm_names:
        cloudwatch_client.put_metric_alarm(
            AlarmName=name,
            MetricName="dummy",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    before = time.time()
    handler.update_alarms([], alarm_names, [])
    after = time.time()

    curr_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=DEFAULT_ALARM_NAME_PREFIX,
        AlarmTypes=["MetricAlarm"],
    )["MetricAlarms"]

    assert len(curr_alarms) == 0
    assert (after - before) >= (interval / 1000 * num_api_calls)


def test_create_and_delete_alarms(cloudwatch_client: CloudWatchClient):
    """Tests creating and deleting alarms

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
    """
    alarm_name_prefix = "test-"
    handler = AlarmHandler(_config(alarm_name_prefix=alarm_name_prefix))

    for i, j in itertools.product(range(0, 2), range(0, 2)):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{alarm_name_prefix}alarm-{i}{j}",
            MetricName="dummy",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    create_alarm_names = [f"{alarm_name_prefix}alarm-1{i}" for i in range(2, 4)]
    create_alarms = [
        AlarmProps(
            AlarmName=alarm_name,
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for alarm_name in create_alarm_names
    ]

    delete_alarm_names = [f"{alarm_name_prefix}alarm-{i}1" for i in range(0, 2)]

    handler.update_alarms(create_alarms, delete_alarm_names, [])

    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm_name_prefix, AlarmTypes=["MetricAlarm"])
    actual_alarm_names = {a["AlarmName"] for a in api_resp["MetricAlarms"]}

    assert actual_alarm_names == {
        "test-alarm-00",
        # "test-alarm-01",     # expected be deleted
        "test-alarm-10",
        # "test-alarm-11",     # expected be deleted
        "test-alarm-12",
        "test-alarm-13",
    }


def test_create_changeset(cloudwatch_client: CloudWatchClient):
    """Tests creating changeset

    Args:
        cloudwatch_client (CloudWatchClient): cloudwatch client
    """
    alarm_name_prefix = "test-changeset-alarm-"

    # create previously existing alarms
    # 00, 01, 10, 11
    for i, j in itertools.product(range(0, 2), range(0, 2)):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{alarm_name_prefix}{i}{j}-m1",
            MetricName="m1",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )
    # create existing alarm with different name prefix
    alarm_with_different_prefix = "different_alarm_name_prefix-11"
    cloudwatch_client.put_metric_alarm(
        AlarmName=alarm_with_different_prefix,
        MetricName="dummy",
        Namespace="dummy",
        EvaluationPeriods=1,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
    )

    # create required alarm params
    # 10, 11, 20, 21
    alarm_params = [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=f"{i}{j}",
            ),
            AlarmProps=AlarmProps(
                MetricName="m1",
            ),
        )
        for i, j in itertools.product(range(1, 3), range(0, 2))
    ]

    handler = AlarmHandler(_config(alarm_name_prefix=alarm_name_prefix))
    to_create, no_update, to_delete = handler.get_alarms_change_set(alarm_params)
    no_update_alarm_names = {a["AlarmName"] for a in no_update}

    assert {a["AlarmName"] for a in to_create} == {
        f"{alarm_name_prefix}20-m1",
        f"{alarm_name_prefix}21-m1",
    }
    assert (
        alarm_with_different_prefix not in no_update_alarm_names
    ), "only alarms having the prefix in config are calclated as changesets"
    assert no_update_alarm_names == {
        f"{alarm_name_prefix}10-m1",
        f"{alarm_name_prefix}11-m1",
    }
    assert (
        alarm_with_different_prefix not in to_delete
    ), "only alarms having the prefix in config are calclated as changesets"
    assert {a for a in to_delete} == {
        f"{alarm_name_prefix}00-m1",
        f"{alarm_name_prefix}01-m1",
    }


def test_describe_alarm_api_more_than_100(cloudwatch_client: CloudWatchClient):
    """Test on calling describe_alarm() with token

    describe_alarm() allows up to 100 records to return in an invocation.
    test verifies the module retrieves all current alarms in the case there're
    more than 100

    Args:
        cloudwatch_client (CloudWatchClient): cloudwatch client
    """
    alarm_name_prefix = DEFAULT_ALARM_NAME_PREFIX
    num_current_alarms = 2024
    offset = 1511  # must be < num_current_alarms
    addition = 3

    for i in range(num_current_alarms):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{alarm_name_prefix}{i}-m1",
            MetricName="m1",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    alarm_params = [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=f"{i}",
            ),
            AlarmProps=AlarmProps(
                MetricName="m1",
            ),
        )
        for i in range(offset, num_current_alarms + offset + addition)
    ]

    handler = AlarmHandler(_config())
    to_create, no_update, to_delete = handler.get_alarms_change_set(alarm_params)
    assert len(list(to_create)) == offset + addition
    assert len(list(no_update)) == num_current_alarms - offset
    assert len(to_delete) == offset


def _config(alarm_name_prefix: str = DEFAULT_ALARM_NAME_PREFIX, alarm_actions: list[str] = []):
    return {
        "globals": {
            "alarm": {
                "alarm_name_prefix": alarm_name_prefix,
                "alarm_actions": alarm_actions,
                "default_alarm_params": DEFAULT_ALARM_PARAMS,
            },
            "api_call_intervals_in_millis": 0,
        },
    }
