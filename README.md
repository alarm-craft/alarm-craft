# `alarm-craft` for AWS CloudWatch Alarms

[![Python - Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fryo-murai%2Falarm-craft%2Fmain%2Fpyproject.toml&logo=python)](https://www.python.org/downloads/)
[![PyPI - Version](https://img.shields.io/pypi/v/alarm-craft)](https://pypi.org/project/alarm-craft/)
[![PyPI - License](https://img.shields.io/pypi/l/alarm-craft)](https://pypi.org/project/alarm-craft/)
[![CI for alarm-craft](https://github.com/ryo-murai/alarm-craft/actions/workflows/ci.yml/badge.svg)](https://github.com/ryo-murai/alarm-craft/actions/workflows/ci.yml)
![aws](https://img.shields.io/badge/-Amazon%20Web%20Services-232F3E.svg?logo=amazon-aws&style=flat)
![cloudwatch](https://img.shields.io/badge/Made%20for-Amazon%20CloudWatch%20Alarms-FF4F8B.svg?logo=amazon-cloudwatch&style=flat)

---

With modern architectures such as serverless and microservices, the number of resources managed in the cloud tends to increase, making monitoring a challenging task. `alarm-craft` is a tool designed to address this problem.

## Features

- **Bulk Generation**: Generates the necessary monitoring alarms in bulk with a single command.
- **Flexible Alarm Definition**: Allows flexible definition of alarm conditions, including metrics and thresholds.
- **Declarative Config**: Provides [declarative configurations](https://github.com/ryo-murai/alarm-craft/wiki/ConfigurationByExample) for monitoring targets using resource name or tag.
- **Integration with Your Deployment Pipeline**: A CLI tool written in Python that can be seamlessly [integrated](https://github.com/ryo-murai/alarm-craft/wiki/Automation) into the deployment pipeline.
- **DevOps**: By leveraging declarative configurations based on the tag strategy and integrating `alarm-craft` with the deployment pipeline, DevOps teams can automatically monitor newly deployed resources.

## Quick Start

1. Install python (>= 3.9), and install `alarm-craft`.
   ```bash
   pip install alarm-craft
   ```
1. Create a json file like below and save it as `alarm-config.yaml`
   ```yaml
   resources:
     lambda:
       target_resource_type: "lambda:function"
       alarm:
         namespace: "AWS/Lambda"
         metrics:
           - Errors
   ```
1. Execute the tool.
   ```bash
   alarm-craft
   ```
   By this execution, the `alarm-craft` creates Cloudwatch Alarms to detect `Errors` in all Lambda functions.

## Documentation

For detailed instructions and information on configuring the tool, refer to the [Wiki](https://github.com/ryo-murai/alarm-craft/wiki/Home#toc).
