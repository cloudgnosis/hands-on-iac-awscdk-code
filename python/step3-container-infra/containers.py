import constructs as cons
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
)

def add_cluster(scope: cons.Construct, id: str, vpc: ec2.IVpc) -> ecs.Cluster:
   return ecs.Cluster(scope, id, vpc=vpc) 
