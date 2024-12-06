import os
import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

app = cdk.App()
environment = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
)
stack = cdk.Stack(app, "my-stack", env=environment)

vpc = ec2.Vpc.from_lookup(stack, "my-vpc", is_default=True)
instance = ec2.Instance(
    stack,
    "my-ec2",
    instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
    machine_image=ec2.MachineImage.latest_amazon_linux2023(),
    vpc=vpc,
)

app.synth()
