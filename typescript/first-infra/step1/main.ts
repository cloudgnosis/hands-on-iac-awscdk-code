import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as process from 'node:process';

const app = new cdk.App();
const stack = new cdk.Stack(app, 'my-stack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

const vpc = ec2.Vpc.fromLookup(stack, 'my-vpc', {
  isDefault: true,
});

const instance = new ec2.Instance(stack, 'my-ec2', {
  instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
  machineImage: ec2.MachineImage.latestAmazonLinux2023(),
  vpc,
});
