import os
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
)
import containers

app = cdk.App()
env = cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"),
                      region=os.getenv("CDK_DEFAULT_REGION"))
stack = cdk.Stack(app, "my-container-infra", env=env)

vpc = ec2.Vpc.from_lookup(stack, "vpc", is_default=True)

containers.add_cluster(stack, "my-test-cluster", vpc)

app.synth()

