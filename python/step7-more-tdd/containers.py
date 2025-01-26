from typing import Literal, TypedDict  # noqa
import constructs as cons
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_logs as logs,
)


class TaskConfig(TypedDict):
    cpu: Literal[256, 512, 1024, 2048, 4096]
    memory_limit_mib: int
    family: str


class ContainerConfig(TypedDict):
    image: str


def add_task_definition_with_container(
    scope: cons.Construct,
    id: str,
    task_config: TaskConfig,
    container_config: ContainerConfig,
) -> ecs.FargateTaskDefinition:
    taskdef = ecs.FargateTaskDefinition(
        scope,
        id,
        cpu=task_config["cpu"],
        memory_limit_mib=task_config["memory_limit_mib"],
        family=task_config["family"],
    )

    logdriver = ecs.LogDrivers.aws_logs(
        stream_prefix=taskdef.family,
        log_retention=logs.RetentionDays.ONE_DAY,
    )
    image = ecs.ContainerImage.from_registry(container_config["image"])
    image_id = f"container-{_extract_image_name(container_config['image'])}"
    taskdef.add_container(image_id, image=image, logging=logdriver)

    return taskdef


def add_service(
    scope: cons.Construct,
    id: str,
    cluster: ecs.Cluster,
    taskdef: ecs.FargateTaskDefinition,
    port: int,
    desired_count: int,
    assign_public_ip: bool = False,
    service_name: str = None,
) -> ecs.FargateService:
    name = service_name if service_name else ""
    sg = ec2.SecurityGroup(
        scope,
        f"{id}-security-group",
        description=f"security group for service {name}",
        vpc=cluster.vpc,
    )
    sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(port))

    service = ecs.FargateService(
        scope,
        id,
        cluster=cluster,
        task_definition=taskdef,
        desired_count=desired_count,
        service_name=service_name,
        security_groups=[sg],
        circuit_breaker=ecs.DeploymentCircuitBreaker(
            rollback=True,
        ),
        assign_public_ip=assign_public_ip,
    )
    return service


def add_cluster(scope: cons.Construct, id: str, vpc: ec2.IVpc) -> ecs.Cluster:
    return ecs.Cluster(scope, id, vpc=vpc)


def _extract_image_name(image_ref):
    name_with_tag = image_ref.split("/")[-1]
    name = name_with_tag.split(":")[0]
    return name
