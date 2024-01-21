import itertools
import json
from io import StringIO
from pathlib import Path

import boto3
import pytest
from moto import mock_cloudwatch
from mypy_boto3_cloudwatch import CloudWatchClient
from pytest_mock import MockerFixture

from alarm_craft.config_loader import DEFAULT_ALARM_NAME_PREFIX
from alarm_craft.models import AlarmProps, TargetResource
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

    metric = "dummy"
    # 10, 11, 20, 21, 30, 31
    resource_names = [f"{i}{j}" for i, j in itertools.product(range(0, 4), range(0, 2))]
    alarm_params = [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=resource_name,
            ),
            AlarmProps=AlarmProps(
                MetricName=metric,
            ),
        )
        for resource_name in resource_names
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
            AlarmName=f"{DEFAULT_ALARM_NAME_PREFIX}{i}{j}-{metric}",
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
    actual_result_alarms = cloudwatch_client.describe_alarms(
        AlarmNamePrefix=DEFAULT_ALARM_NAME_PREFIX, AlarmTypes=["MetricAlarm"]
    )
    actual_alarm_names = {a["AlarmName"] for a in actual_result_alarms["MetricAlarms"]}
    assert actual_alarm_names == {f"{DEFAULT_ALARM_NAME_PREFIX}{r}-{metric}" for r in resource_names}

    out, _ = capfd.readouterr()
    expected_changeset_output_lines = [
        f"+ {DEFAULT_ALARM_NAME_PREFIX}10-{metric}",
        f"+ {DEFAULT_ALARM_NAME_PREFIX}20-{metric}",
        f"+ {DEFAULT_ALARM_NAME_PREFIX}30-{metric}",
        f"  {DEFAULT_ALARM_NAME_PREFIX}21-{metric}",
        f"  {DEFAULT_ALARM_NAME_PREFIX}11-{metric}",
        f"  {DEFAULT_ALARM_NAME_PREFIX}31-{metric}",
        f"- {DEFAULT_ALARM_NAME_PREFIX}12-{metric}",
        f"- {DEFAULT_ALARM_NAME_PREFIX}22-{metric}",
        f"- {DEFAULT_ALARM_NAME_PREFIX}32-{metric}",
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
    alarm_name_prefix = DEFAULT_ALARM_NAME_PREFIX
    metric = "dummy"
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")

    alarm_params = [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=f"{i}",
            ),
            AlarmProps=AlarmProps(
                MetricName=metric,
            ),
        )
        for i in range(10)
    ]
    mock_get_target_metrics.return_value = alarm_params

    required_alarm_names = [
        f"{alarm_name_prefix}{almparam['TargetResource']['ResourceName']}-{metric}" for almparam in alarm_params
    ]
    existing_alarm_names = [f"{alarm_name_prefix}{i}-{metric}" for i in range(5, 15)]

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
    alarm_name_prefix = DEFAULT_ALARM_NAME_PREFIX
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")

    metric = "dummy"
    alarm_params = [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=f"{i}",
            ),
            AlarmProps=AlarmProps(
                MetricName=metric,
            ),
        )
        for i in range(10)
    ]
    mock_get_target_metrics.return_value = alarm_params

    required_alarm_names = [
        f"{alarm_name_prefix}{almparam['TargetResource']['ResourceName']}-{metric}" for almparam in alarm_params
    ]

    # create config
    config_path = tmp_path / "config.json"
    conf = _config(alarm_name_prefix)
    with open(config_path, "w") as f:
        json.dump(conf, f)

    # existing alarms
    for name in required_alarm_names:
        cloudwatch_client.put_metric_alarm(
            AlarmName=name,
            MetricName=metric,
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
    assert actual_alarm_names == set(required_alarm_names), "must the same"

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
    alarm_name_prefix = DEFAULT_ALARM_NAME_PREFIX
    mock_get_target_metrics = mocker.patch("alarm_craft.core.get_target_metrics")

    metric = "dummy"
    alarm_params = [
        MetricAlarmParam(
            TargetResource=TargetResource(
                ResourceName=f"{i}",
            ),
            AlarmProps=AlarmProps(
                MetricName=metric,
            ),
        )
        for i in range(100)
    ]
    mock_get_target_metrics.return_value = alarm_params
    required_alarm_names = [f"{alarm_name_prefix}{p['TargetResource']['ResourceName']}-{metric}" for p in alarm_params]

    # create config
    alarm_topic_arn = "arn:aws:sns:ap-northeast-1:123456789012:alarming0001"
    config_path = tmp_path / "config.json"
    conf = _config(alarm_name_prefix, [alarm_topic_arn])
    with open(config_path, "w") as f:
        json.dump(conf, f)

    # existing alarms
    for i in range(50, 150):
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{alarm_name_prefix}{i}-{metric}",
            MetricName=metric,
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
    assert actual_alarm_names == set(required_alarm_names)
    for a in actual_result_alarms:
        assert a["AlarmActions"] == [alarm_topic_arn]
        assert a["OKActions"] == [alarm_topic_arn]
        assert a["InsufficientDataActions"] == [alarm_topic_arn]

    out, _ = capfd.readouterr()
    for i in range(50):
        assert f"+ {alarm_name_prefix}{i}-{metric}" in out
    for i in range(50, 100):
        assert f"U {alarm_name_prefix}{i}-{metric}" in out


def _config(alarm_name_prefix: str = DEFAULT_ALARM_NAME_PREFIX, alarm_actions: list[str] = None) -> dict:
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
