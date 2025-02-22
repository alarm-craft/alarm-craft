---
name: Support for New Resource Type
about: Design for supporting new resource type
title: "[Feature] "
labels: enhancement
assignees: ryo-murai

---

# Target resource type and alarm dimension
|Service|Resource|[target_resource_type](Configuration#definitions%2Fresource_config)|Namespace|Dimensions|
|-|-|-|-|-|
|EventBridge Scheduler|Schedule Group|`"scheduler:schedule-group"`|AWS/Scheduler|[`ScheduleGroup`](https://docs.aws.amazon.com/scheduler/latest/UserGuide/monitoring-cloudwatch.html#monitoring-cloudwatch-dimensions)|

# API to retrieve target resources
* resourcegroupstaggingapi

# TODO
- [] Add Provider class
- [] Add test data in `_test_params()` of `test_target_metrics_provider_rgta.py`
- [] Add enum value in target_resource_type in config_schema.json, then generate docs
- [] Add sample for this resource_type in config-sample.yaml
- [] Add doc

# Notes
* None
