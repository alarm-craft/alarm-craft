from typing import Mapping, Optional, Sequence, TypedDict


class AlarmProps(TypedDict, total=False):
    """Metric Alarm Properties

    Args:
        TypedDict (_type_): typed dict
    """

    AlarmName: str
    AlarmDescription: str
    Statistic: str
    Period: int
    EvaluationPeriods: int
    Threshold: int
    ComparisonOperator: str
    TreatMissingData: str
    Namespace: str
    MetricName: str
    Dimensions: Sequence[Mapping[str, str]]


class TargetResource(TypedDict):
    """Target Resource

    Args:
        TypedDict (_type_): typed dict
    """

    ResourceName: str


class MetricAlarmParam(TypedDict):
    """Metric Alarm Parameter

    Args:
        TypedDict (_type_): typed dict
    """

    TargetResource: TargetResource
    AlarmProps: AlarmProps


class MetricAlarmParamRequired(TypedDict):
    """Metric Alarm Parameter with required keys

    Args:
        TypedDict (_type_): typed dict
    """

    ResourceName: str
    MetricName: str
    Namespace: str
    Dimensions: Sequence[Mapping[str, str]]


class MetricAlarmParam2(MetricAlarmParamRequired, total=False):
    """Metric Alarm Parameter

    Args:
        MetricAlarmParamRequired (_type_): MetricAlarmParamRequired
    """

    AlarmName: str
    AlarmDescription: str
    Statistic: str
    Period: int
    EvaluationPeriods: int
    Threshold: int
    ComparisonOperator: str
    TreatMissingData: str


class ResourceAlarmConfig(TypedDict):
    """Alarm Config in Resource Config

    Args:
        TypedDict (_type_): typed dict
    """

    namespace: str
    metrics: Sequence[str]
    alarm_param_overrides: Optional[Mapping[str, MetricAlarmParam]]


class ResourceConfig(TypedDict):
    """Resource Config

    Args:
        TypedDict (_type_): typed dict
    """

    target_resource_type: str
    target_resource_name_pattern: Optional[str]
    target_resource_tags: Optional[Mapping[str, str]]
    alarm: ResourceAlarmConfig
