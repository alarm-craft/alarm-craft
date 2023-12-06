import itertools
import time
from typing import Union

import boto3
import pytest
from moto import mock_cloudwatch
from mypy_boto3_cloudwatch.client import CloudWatchClient

from alarm_craft.alarm import AlarmHandler
from alarm_craft.monitoring_targets import MetricAlarmParam


@pytest.fixture()
def cloudwatch_client():
    """Create mock cloudwatch client for tests

    Yields:
        CloudWatchClient : mocked by moto
    """
    with mock_cloudwatch():
        cloudwatch_client = boto3.client("cloudwatch")
        yield cloudwatch_client


def _alarm_test_params():
    return [
        (
            "alarm-test-resource-1",
            "12345678901234567890",
            "TestsCount",
            "AWS/MyService",
            [{"Name": "MyResourceName", "Value": "myresource-1"}],
        ),
        (
            "alarm-test-resource-2",
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

    alarm = MetricAlarmParam(
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
    assert curr_alarm["Statistic"] == "Sum"
    assert curr_alarm["Period"] == 60
    assert curr_alarm["EvaluationPeriods"] == 1
    assert curr_alarm["Threshold"] == 1
    assert curr_alarm["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
    assert curr_alarm["TreatMissingData"] == "notBreaching"


def test_create_alarm_param_overrides(cloudwatch_client: CloudWatchClient):
    """Tests creating an alarm with param overrides

    Args:
        cloudwatch_client (CloudWatchClient): CloudWatchClient
    """
    handler = AlarmHandler(_config())

    alarm_param = MetricAlarmParam(
        AlarmName="alarm-name-0001",
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
    api_resp = cloudwatch_client.describe_alarms(AlarmNamePrefix=alarm_param["AlarmName"], AlarmTypes=["MetricAlarm"])

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
                "EvaluationPeriods": 95,
                "ComparisonOperator": "GreaterThanThreshold",
            },
            {
                "Statistic": "Average",
                "Period": 60,
                "EvaluationPeriods": 95,
                "Threshold": 1,
                "ComparisonOperator": "GreaterThanThreshold",
                "TreatMissingData": "notBreaching",
            },
        ),
        (
            {
                "Period": 78,
                "Threshold": 9,
                "TreatMissingData": "ignore",
            },
            {
                "Statistic": "Sum",
                "Period": 78,
                "EvaluationPeriods": 1,
                "Threshold": 9,
                "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                "TreatMissingData": "ignore",
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
    config["alarm_config"]["default_alarm_params"] = default_alarm_params

    alarm_param = MetricAlarmParam(
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

    alarm = MetricAlarmParam(
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
    config["alarm_config"]["alarm_tagging"] = tag_config

    handler = AlarmHandler(config)

    alarm = MetricAlarmParam(
        AlarmName="alarm-name-0001111",
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
    config["alarm_config"]["api_call_intervals_in_millis"] = interval

    handler = AlarmHandler(config)

    alarms = [
        MetricAlarmParam(
            AlarmName=f"alarm-name-{i}",
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
        AlarmNamePrefix="alarm-name-",
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
    config["alarm_config"]["api_call_intervals_in_millis"] = interval

    handler = AlarmHandler(config)

    num_alarms = (num_api_calls - 1) * 100 + 1  # ex.) 201 makes three calls of 100, 100 and 1.
    alarm_names = [f"alarm-name-{i}" for i in range(num_alarms)]

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
        AlarmNamePrefix="alarm-name-",
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
        MetricAlarmParam(
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
            AlarmName=f"{alarm_name_prefix}{i}{j}",
            MetricName="dummy",
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
    create_alarm_names = [f"{alarm_name_prefix}{i}{j}" for i, j in itertools.product(range(1, 3), range(0, 2))]
    alarm_params = [
        MetricAlarmParam(
            AlarmName=alarm_name,
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for alarm_name in create_alarm_names
    ]

    handler = AlarmHandler(_config(alarm_name_prefix=alarm_name_prefix))
    to_create, no_update, to_delete = handler.get_alarms_change_set(alarm_params)

    assert {a["AlarmName"] for a in to_create} == {
        f"{alarm_name_prefix}20",
        f"{alarm_name_prefix}21",
    }
    assert (
        alarm_with_different_prefix not in no_update
    ), "only alarms having the prefix in config are calclated as changesets"
    assert {a for a in no_update} == {
        f"{alarm_name_prefix}10",
        f"{alarm_name_prefix}11",
    }
    assert (
        alarm_with_different_prefix not in to_delete
    ), "only alarms having the prefix in config are calclated as changesets"
    assert {a for a in to_delete} == {
        f"{alarm_name_prefix}00",
        f"{alarm_name_prefix}01",
    }


def test_describe_alarm_api_more_than_100(cloudwatch_client: CloudWatchClient):
    """Test on calling describe_alarm() with token

    describe_alarm() allows up to 100 records to return in an invocation.
    test verifies the module retrieves all current alarms in the case there're
    more than 100

    Args:
        cloudwatch_client (CloudWatchClient): cloudwatch client
    """
    alarm_name_prefix = "alarm-test"
    num_current_alarms = 2022
    offset = 1511  # must be < num_current_alarms

    for i in range(num_current_alarms):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{alarm_name_prefix}-{i}",
            MetricName="dummy",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    alarm_params = [
        MetricAlarmParam(
            AlarmName=f"{alarm_name_prefix}-{i}",
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for i in range(offset, num_current_alarms + offset)
    ]

    handler = AlarmHandler(_config(alarm_name_prefix=alarm_name_prefix))
    to_create, no_update, to_delete = handler.get_alarms_change_set(alarm_params)
    assert len(list(to_create)) == offset
    assert len(no_update) == num_current_alarms - offset
    assert len(to_delete) == offset


def _config(alarm_name_prefix: str = "", alarm_actions: list[str] = []):
    return {
        "alarm_config": {
            "alarm_name_prefix": alarm_name_prefix,
            "alarm_actions": alarm_actions,
        },
    }
