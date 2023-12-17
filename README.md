# AWS CloudWatch Alarm Craft

A tool to create AWS CloudWatch Alarms for your resources with specified name and tags.

## Quick Start
1. Install python (>= 3.9), and install `alarm-craft`.
    ```bash
    pip install alarm-craft
    ```
1. Execute the tool.
    ```bash
    python -m alarm-craft -c config-min-sample.json
    ```
By this execution, the `alarm-craft` creates Cloudwatch Alarms for your Lambda functions tagged `division: alpha`. The following alarms would be created if your lambda function exists.
* myproj-cw-metric-alarm-autogen-_<name_of_funcion>_-Errors
* myproj-cw-metric-alarm-autogen-_<name_of_funcion>_-Throttled

The prefix of alarm name, target resource, its tags/names and others can be configured by json file. See [config-min-sample.json](config-min-sample.json) for above simple case or [config-sample.json](config-sample.json) for more complex case. For complete configuration file specification, refer [Wiki/Configuration](https://github.com/ryo-murai/alarm-craft/wiki/Configuration).


## Usage

See [Wiki](https://github.com/ryo-murai/alarm-craft/wiki).