# AWS CloudWatch Alarm Craft

A tool to create AWS CloudWatch Alarms for your resources with specified name and tags.

## Quick Start

1. Install python (>= 3.9), and install `alarm-craft`.
   ```bash
   pip install alarm-craft
   ```
1. Create a json file like below and save it `config.json`
   ```json
   {
     "resources": {
       "lambda": {
         "target_resource_type": "lambda:function",
         "alarm": {
           "namespace": "AWS/Lambda",
           "metrics": ["Errors"]
         }
       }
     }
   }
   ```
1. Execute the tool.
   `bash
 python alarm-craft -c config.json
 `
   By this execution, the `alarm-craft` creates Cloudwatch Alarms to detect `Error` for your Lambda functions.

### Supported resources

The following resources are supported by the `alarm-craft`.

- Lambda Function
- StepFunctions State Machine
- APIGateway REST API
- SNS Topic
- SQS Queue
- EventBridge Rule

### Filtering resources

- The alarming target can be filtered by name and/or tags.
  ```json
     "lambda": {
          "target_resource_name_pattern": "^myproj-(dev|prod)-",
          "target_resource_tags": {
              "Owner": "mydivision"
          },
          ... (omit)
     }
  ```

### Configure more

See [config-min-sample.json](config-min-sample.json) for above simple case or [config-sample.json](config-sample.json) for more complex case. For complete configuration specification, refer [Wiki/Configuration](https://github.com/ryo-murai/alarm-craft/wiki/Configuration).

## Usage

See [Wiki](https://github.com/ryo-murai/alarm-craft/wiki).
