import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from . import config_loader
from .alarm import AlarmHandler
from .monitoring_targets import MetricAlarmParam, get_target_metrics

logger = logging.getLogger(__name__)


@dataclass
class CommandOpts:
    """Command Options"""

    confirm_changeset: bool
    config_file: Optional[str]
    notification_topic_arn: list[str]
    update_existing_alarms: bool


def main(opts: CommandOpts) -> None:
    """The main function

    Args:
        opts (CommandOpts): command options
    """
    config = config_loader.load(opts.config_file)
    target_metrics = list(get_target_metrics(config))

    alarm_handler = AlarmHandler(config)
    (create, keep, delete) = alarm_handler.get_alarms_change_set(target_metrics)
    _print_chagne_set(create, keep, delete, opts.update_existing_alarms)

    if create or delete or (keep and opts.update_existing_alarms):
        force_update = not opts.confirm_changeset
        if force_update or _prompt_update():
            _print("!!! UPDATE ALARMS !!!")
            if opts.update_existing_alarms:
                alarm_handler.update_alarms(target_metrics, delete, opts.notification_topic_arn)
            else:
                alarm_handler.update_alarms(create, delete, opts.notification_topic_arn)
        else:
            _print("no updates executed..")
    else:
        _print("all required alarms already exist. no updates executed")


def _print_chagne_set(
    to_create: Iterable[MetricAlarmParam], no_update: list[str], to_delete: list[str], anyway_update: bool
) -> None:
    adding_label = "+ "
    exists_label = "  " if not anyway_update else "U "
    delete_label = "- "

    for a in to_create:
        _print(adding_label + a["AlarmName"])
    for s in no_update:
        _print(exists_label + s)
    for s in to_delete:
        _print(delete_label + s)


def _print(text: str) -> None:
    print(text)  # noqa: T201


def _prompt_update() -> bool:
    ans = input("execute updating above alarms ? [y/n]:") == "y"
    return ans
