import argparse
import logging
import os

from . import core

def run() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    logger = logging.getLogger(__name__)

    opts = core.CommandOpts(True, None, [], False)

    argparser = argparse.ArgumentParser(description="AWS CloudWatch Alarm Craft")
    argparser.add_argument("-f", "--no-confirm-changeset", action="store_false", dest="confirm_changeset")
    argparser.add_argument("-n", "--notification-topic-arn", type=str, dest="notification_topic_arn", nargs="*", default=[])
    argparser.add_argument("-c", "--config-file")
    argparser.add_argument("-u", "--update-existing-alarms", action="store_true", dest="update_existing_alarms")
    args = argparser.parse_args(namespace=opts)

    logger.debug("commandline opts:%s", opts)

    core.main(args)

if __name__ == "__main__":
    run()
