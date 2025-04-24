import pytest
import aws_cdk as cdk
from aws_cdk import (
    assertions,
    aws_ec2 as ec2,
    aws_sns as sns,
)
import monitoring as mon


def test_init_monitoring_of_stack_with_defaults():
    stack = cdk.Stack()

    config = mon.MonitoringConfig(dashboard_name="test-monitoring")
    mon.init_monitoring(stack, config)
    template = assertions.Template.from_stack(stack)
    print(template)
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)
    template.has_resource_properties(
        "AWS::CloudWatch::Dashboard", {"DashboardName": config["dashboard_name"]}
    )

def test_init_monitoring_of_stack_with_sns_alarm_topic():
    stack = cdk.Stack()
    ec2.Vpc(stack, 'vpc')
    alarm_topic = sns.Topic(stack, 'alarm-topic')

    monitoring_config = mon.MonitoringConfig(
        dashboard_name='test-monitoring',
        default_alarm_topic=alarm_topic  # type: ignore
    )

    monitoring = mon.init_monitoring(stack, config=monitoring_config)
    assert(monitoring.get("default_alarm_topic") == monitoring_config.get("default_alarm_topic"))
    assert(monitoring.get("default_alarm_name_prefix") == monitoring_config.get("dashboard_name"))
