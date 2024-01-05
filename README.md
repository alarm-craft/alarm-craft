# AWS CloudWatch Alarm Craft

[![Python - Version](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg?logo=python&style=flat)](https://www.python.org/downloads/)
[![PyPI - Version](https://img.shields.io/pypi/v/alarm-craft)](https://pypi.org/project/alarm-craft/)
[![PyPI - License](https://img.shields.io/pypi/l/alarm-craft)](https://pypi.org/project/alarm-craft/)
![aws](https://img.shields.io/badge/-Amazon%20Web%20Services-232F3E.svg?logo=amazon-aws&style=flat)

---

In modern architectures such as serverless and microservices, the number of cloud-managed resources tends to grow, making monitoring a challenging task. `alarm-craft` is a tool designed to address this issue.

## Features

- **Bulk Generation**: Generates the necessary monitoring alarms in bulk with a single command.
- **Declarative Config**: Provides a [declarative config](https://github.com/ryo-murai/alarm-craft/wiki/Configuration) to specify monitoring targets using resource names or tags.
- **Flexible Condition Definition**: Allows flexible definition of alarm conditions, including metrics and thresholds.
- **Integration with Your Deployment Pipeline**: A CLI tool written in Python that [integrates](https://github.com/ryo-murai/alarm-craft/wiki/Automation) seamlessly into your deployment pipeline.

## Quick Start

1. Install python (>= 3.9), and install `alarm-craft`.
   ```bash
   pip install alarm-craft
   ```
1. Create a json file like below and save it as `config.json`
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
   ```bash
   alarm-craft -c config.json
   ```
   By this execution, the `alarm-craft` creates Cloudwatch Alarms to detect `Errors` in all Lambda functions.

## Documentation

For detailed instructions and information on configuring the tool, refer to the [Wiki](https://github.com/ryo-murai/alarm-craft/wiki).
