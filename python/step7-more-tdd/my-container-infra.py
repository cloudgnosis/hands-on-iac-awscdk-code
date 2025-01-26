import os
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
)
import containers

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

cluster = containers.add_cluster(stack, "my-test-cluster", vpc)

taskconfig: containers.TaskConfig = {
    "cpu": 512,
    "memory_limit_mib": 1024,
    "family": "webapp",
}
containerconfig: containers.ContainerConfig = {
    "image": "public.ecr.aws/aws-containers/hello-app-runner:latest",
}
taskdef = containers.add_task_definition_with_container(
    stack, f"taskdef-{taskconfig['family']}", taskconfig, containerconfig
)

containers.add_service(
    stack, f"service-{taskconfig['family']}", cluster, taskdef, 8000, 0, True
)

app.synth()
