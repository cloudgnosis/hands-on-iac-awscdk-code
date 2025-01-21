import os
import aws_cdk as cdk
from aws_cdk import (
    aws_apprunner_alpha as apprunner,
    aws_ec2 as ec2,
    aws_iam as iam,
)

app = cdk.App()
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)
my_stack_name = "my-app-stack"
stack = cdk.Stack(app, "app-runner-stack", stack_name=my_stack_name, env=env)

vpc = ec2.Vpc.from_lookup(stack, "my-vpc", is_default=True)

app_source = apprunner.Source.from_ecr_public(
    image_configuration=apprunner.ImageConfiguration(
        port=8000,
    ),
    image_identifier="public.ecr.aws/aws-containers/hello-app-runner:latest",
)

auto_scaling_config = apprunner.AutoScalingConfiguration(
    stack,
    "autoscaling-configuration",
    min_size=1,
    max_size=10,
    max_concurrency=40,
)

vpc_connector = apprunner.VpcConnector(
    stack,
    "vpc-connector",
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
)

service = apprunner.Service(
    stack,
    "app-runner-service",
    source=app_source,
    cpu=apprunner.Cpu.QUARTER_VCPU,
    memory=apprunner.Memory.ONE_GB,
    auto_scaling_configuration=auto_scaling_config,
    vpc_connector=vpc_connector,
)

read_s3_policy = iam.PolicyStatement(actions=["s3:GetObject"], resources=["*"])
service.add_to_role_policy(read_s3_policy)

cdk.CfnOutput(stack, "app-runner-service-url", value=service.service_url)
app.synth()
