from typing import NotRequired, TypedDict
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_sns as sns,
)
import cdk_monitoring_constructs as cdkmon


class MonitoringConfig(TypedDict):
    dashboard_name: str
    default_alarm_topic: NotRequired[sns.ITopic]
    default_alarm_name_prefix: NotRequired[str]


class MonitoringContext(TypedDict):
    handler: cdkmon.MonitoringFacade
    default_alarm_topic: NotRequired[sns.ITopic]
    default_alarm_name_prefix: NotRequired[str]



def init_monitoring(scope: Construct, config: MonitoringConfig) -> MonitoringContext:
    sns_alarm_strategy = cdkmon.NoopAlarmActionStrategy()
    if config.get("default_alarm_topic"):
        sns_alarm_strategy = cdkmon.SnsAlarmActionStrategy(on_alarm_topic=config.get("default_alarm_topic"))
    default_alarm_name_prefix = config.get("default_alarm_name_prefix")
    if default_alarm_name_prefix is None:
        default_alarm_name_prefix = config["dashboard_name"]
    return MonitoringContext(
        handler=cdkmon.MonitoringFacade(
            scope,
            config["dashboard_name"],
            alarm_factory_defaults=cdkmon.AlarmFactoryDefaults(
                actions_enabled=True,
                action=sns_alarm_strategy,
                alarm_name_prefix=default_alarm_name_prefix
            )),
            default_alarm_topic=config.get("default_alarm_topic"),
            default_alarm_name_prefix=default_alarm_name_prefix)
