import os
import aws_cdk as cdk
from aws_cdk import (
    aws_cloudwatch as cw,
    aws_ec2 as ec2,
    aws_sns as sns,
    aws_sns_subscriptions as snssubs,
)
import cdk_monitoring_constructs as cdkmon
import containers
import monitoring

app = cdk.App()
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
)
stack = cdk.Stack(app, "my-container-infra", env=env)

vpcname = app.node.try_get_context("vpcname")
if vpcname:
    vpc = ec2.Vpc.from_lookup(stack, "vpc", vpc_name=vpcname)
else:
    vpc = ec2.Vpc(stack, "vpc", vpc_name="my-vpc", nat_gateways=1, max_azs=2)
config = containers.ClusterConfig(vpc=vpc)
cluster = containers.add_cluster(stack, "my-test-cluster", config)

taskconfig: containers.TaskConfig = {
    "cpu": 512,
    "memory_limit_mib": 1024,
    "family": "webapp",
}
containerconfig: containers.ContainerConfig = {
    "image": "public.ecr.aws/aws-containers/hello-app-runner:latest",
    "tcp_ports": [8000],
}
taskdef = containers.add_task_definition_with_container(
    stack, f"taskdef-{taskconfig['family']}", taskconfig, containerconfig
)

service = containers.add_service(
    stack, f"service-{taskconfig['family']}", cluster, taskdef, 8000, 2, True
)

containers.set_service_scaling(
    service=service.service,
    config=containers.ServiceScalingConfig(
        min_count=1,
        max_count=4,
        scale_cpu_target=containers.ScalingThreshold(percent=50),
        scale_memory_target=containers.ScalingThreshold(percent=70),
    ),
)


alarm_topic = sns.Topic(stack, 'alarm-topic', display_name='Alarm topic')

monitoring_config = monitoring.MonitoringConfig(dashboard_name='monitoring', default_alarm_topic=alarm_topic)
mon = monitoring.init_monitoring(stack, monitoring_config)

mon["handler"].add_medium_header("Test App monitoring")
mon["handler"].monitor_fargate_service(
    fargate_service=service,
    human_readable_name="My test service",
)

mon["handler"].monitor_fargate_service(
    fargate_service=service,
    human_readable_name='My test service',
    add_running_task_count_alarm={
        'alarm1': cdkmon.RunningTaskCountThreshold(
            max_running_tasks=2,
            comparison_operator_override=cw.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            period=cdk.Duration.minutes(5),
        )
    })

alarm_email = 'hello@example.com'
alarm_topic.add_subscription(snssubs.EmailSubscription(alarm_email))

app.synth()
