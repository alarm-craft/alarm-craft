import itertools
import json
from io import StringIO
from pathlib import Path

import boto3
import pytest
from moto import mock_cloudwatch
from mypy_boto3_cloudwatch import CloudWatchClient
from pytest_mock import MockerFixture

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


def test_end_to_end_exec(
    mocker: MockerFixture, tmp_path: Path, capfd: pytest.CaptureFixture[str], cloudwatch_client: CloudWatchClient
):
    """Tests end-to-end functionality

    Args:
        mocker (MockerFixture): mocker
        tmp_path (Path): temporary directory path
        capfd (CaptureFixture): capture
        cloudwatch_client (CloudWatchClient): cloudwatch client
    """
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")

    alarm_names = [
        "alarm-test-10",
        "alarm-test-11",
        "alarm-test-20",
        "alarm-test-21",
        "alarm-test-30",
        "alarm-test-31",
    ]
    alarm_params = [
        MetricAlarmParam(
            AlarmName=name,
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for name in alarm_names
    ]

    mock_get_target_metrics.return_value = alarm_params

    # create config
    config_path = tmp_path / "config.json"
    conf = _config()
    with open(config_path, "w") as f:
        json.dump(conf, f)

    # create existing alarms before execute
    # 11, 12, 21, 22, 31, 32
    for i, j in itertools.product(range(1, 4), range(1, 3)):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"alarm-test-{i}{j}",
            MetricName="dummy",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    from alarm_craft import core

    command_opts = core.CommandOpts(
        config_file=str(config_path),
        confirm_changeset=False,
        notification_topic_arn=[],
        update_existing_alarms=False,
    )
    core.main(command_opts)

    # assert
    actual_result_alarms = cloudwatch_client.describe_alarms(AlarmNamePrefix="alarm-test-", AlarmTypes=["MetricAlarm"])
    actual_alarm_names = {a["AlarmName"] for a in actual_result_alarms["MetricAlarms"]}
    assert actual_alarm_names == set(alarm_names)

    out, _ = capfd.readouterr()
    expected_changeset_output_lines = [
        "+ alarm-test-10",
        "+ alarm-test-20",
        "+ alarm-test-30",
        "  alarm-test-21",
        "  alarm-test-11",
        "  alarm-test-31",
        "- alarm-test-12",
        "- alarm-test-22",
        "- alarm-test-32",
    ]
    for expected in expected_changeset_output_lines:
        assert expected in out


def test_end_to_end_confirm(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    cloudwatch_client: CloudWatchClient,
):
    """Test end-to-end execution with confirm changeset

    Args:
        mocker (MockerFixture): mocker
        monkeypatch (pytest.MonkeyPatch): monkeypatch
        tmp_path (Path): temporary path for test
        capfd (pytest.CaptureFixture[str]): capture for stdout
        cloudwatch_client (CloudWatchClient): CloudWatchClient
    """
    alarm_name_prefix = "alarm-test-"
    required_alarm_names = [f"{alarm_name_prefix}{i}" for i in range(10)]
    existing_alarm_names = [f"{alarm_name_prefix}{i}" for i in range(5, 15)]
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")
    alarm_params = [
        MetricAlarmParam(
            AlarmName=name,
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for name in required_alarm_names
    ]
    mock_get_target_metrics.return_value = alarm_params

    # create config
    config_path = tmp_path / "config.json"
    conf = _config(alarm_name_prefix)
    with open(config_path, "w") as f:
        json.dump(conf, f)

    # existing alarms
    for name in existing_alarm_names:
        cloudwatch_client.put_metric_alarm(
            AlarmName=name,
            MetricName="dummy",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    from alarm_craft import core

    command_opts = core.CommandOpts(
        config_file=str(config_path),
        confirm_changeset=True,
        notification_topic_arn=[],
        update_existing_alarms=False,
    )

    # answer 'n'
    monkeypatch.setattr("sys.stdin", StringIO("n"))
    core.main(command_opts)

    # assert the current alarms are not changed
    actual_result_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=alarm_name_prefix,
        AlarmTypes=["MetricAlarm"],
    )["MetricAlarms"]
    actual_alarm_names = {a["AlarmName"] for a in actual_result_alarms}
    assert actual_alarm_names == set(existing_alarm_names), "must not changed"

    # answer 'y'
    monkeypatch.setattr("sys.stdin", StringIO("y"))
    core.main(command_opts)

    # assert the current alarms are not changed
    actual_result_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=alarm_name_prefix,
        AlarmTypes=["MetricAlarm"],
    )["MetricAlarms"]
    actual_alarm_names = {a["AlarmName"] for a in actual_result_alarms}
    assert actual_alarm_names == set(required_alarm_names)


def test_end_to_end_no_updates(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    cloudwatch_client: CloudWatchClient,
):
    """Test end-to-end execution with confirm changeset

    Args:
        mocker (MockerFixture): mocker
        monkeypatch (pytest.MonkeyPatch): monkeypatch
        tmp_path (Path): temporary path for test
        capfd (pytest.CaptureFixture[str]): capture for stdout
        cloudwatch_client (CloudWatchClient): CloudWatchClient
    """
    alarm_name_prefix = "alarm-test-"
    alarm_names = [f"{alarm_name_prefix}{i}" for i in range(10)]
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")
    alarm_params = [
        MetricAlarmParam(
            AlarmName=name,
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for name in alarm_names
    ]
    mock_get_target_metrics.return_value = alarm_params

    # create config
    config_path = tmp_path / "config.json"
    conf = _config(alarm_name_prefix)
    with open(config_path, "w") as f:
        json.dump(conf, f)

    # existing alarms
    for name in alarm_names:
        cloudwatch_client.put_metric_alarm(
            AlarmName=name,
            MetricName="dummy",
            Namespace="dummy",
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    from alarm_craft import core

    command_opts = core.CommandOpts(
        config_file=str(config_path),
        confirm_changeset=True,
        notification_topic_arn=[],
        update_existing_alarms=False,
    )

    core.main(command_opts)

    # assert the current alarms are not changed
    actual_result_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=alarm_name_prefix,
        AlarmTypes=["MetricAlarm"],
    )["MetricAlarms"]
    actual_alarm_names = {a["AlarmName"] for a in actual_result_alarms}
    assert actual_alarm_names == set(alarm_names), "must the same"

    out, _ = capfd.readouterr()
    assert "no updates" in out


def test_end_to_end_update_existing(
    mocker: MockerFixture, tmp_path: Path, capfd: pytest.CaptureFixture[str], cloudwatch_client: CloudWatchClient
):
    """Tests end-to-end functionality with update option

    Args:
        mocker (MockerFixture): mocker
        tmp_path (Path): temporary directory path
        capfd (CaptureFixture): capture
        cloudwatch_client (CloudWatchClient): cloudwatch client
    """
    alarm_name_prefix = "alarm-test-"
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")

    alarm_params = [
        MetricAlarmParam(
            AlarmName=f"{alarm_name_prefix}{i}",
            AlarmDescription="",
            MetricName="dummy",
            Namespace="dummy",
            Dimensions=[],
        )
        for i in range(100)
    ]
    mock_get_target_metrics.return_value = alarm_params

    # create config
    alarm_topic_arn = "arn:aws:sns:ap-northeast-1:123456789012:alarming0001"
    config_path = tmp_path / "config.json"
    conf = _config(alarm_name_prefix, [alarm_topic_arn])
    with open(config_path, "w") as f:
        json.dump(conf, f)

    # existing alarms
    for i in range(50, 150):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{alarm_name_prefix}{i}",
            MetricName="dummy",
            Namespace="dummy",
            AlarmActions=[],  # empty
            EvaluationPeriods=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
        )

    from alarm_craft import core

    command_opts = core.CommandOpts(
        config_file=str(config_path),
        confirm_changeset=False,
        notification_topic_arn=[],
        update_existing_alarms=True,
    )
    core.main(command_opts)

    actual_result_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=alarm_name_prefix,
        AlarmTypes=["MetricAlarm"],
    )["MetricAlarms"]
    actual_alarm_names = {a["AlarmName"] for a in actual_result_alarms}
    assert actual_alarm_names == {a["AlarmName"] for a in alarm_params}
    for a in actual_result_alarms:
        assert a["AlarmActions"] == [alarm_topic_arn]
        assert a["OKActions"] == [alarm_topic_arn]
        assert a["InsufficientDataActions"] == [alarm_topic_arn]

    out, _ = capfd.readouterr()
    for i in range(50):
        assert f"+ {alarm_name_prefix}{i}" in out
    for i in range(50, 100):
        assert f"U {alarm_name_prefix}{i}" in out


def _config(alarm_name_prefix: str = "alarm-test-", alarm_actions: list[str] = None) -> dict:
    conf = {
        "globals": {
            "alarm": {
                "alarm_name_prefix": alarm_name_prefix,
            },
        },
        "resources": {
            "dummy": {
                "target_resource_type": "lambda:function",
                "alarm": {
                    "namespace": "dummy",
                    "metrics": ["dummy"],
                },
            },
        },
    }
    if alarm_actions:
        conf["globals"]["alarm"]["alarm_actions"] = alarm_actions  # type: ignore

    return conf
