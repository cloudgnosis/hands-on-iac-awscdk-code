from typing import Literal, TypedDict, List  # noqa
import constructs as cons
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecspat,
    aws_logs as logs,
)


class TaskConfig(TypedDict):
    cpu: Literal[256, 512, 1024, 2048, 4096]
    memory_limit_mib: int
    family: str


class ContainerConfig(TypedDict):
    image: str
    tcp_ports: List[int]


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
    containerdef = taskdef.add_container(image_id, image=image, logging=logdriver)

    for port in container_config["tcp_ports"]:
        containerdef.add_port_mappings(ecs.PortMapping(container_port=port, protocol=ecs.Protocol.TCP))

    return taskdef


def add_service(
    scope: cons.Construct,
    id: str,
    cluster: ecs.Cluster,
    taskdef: ecs.FargateTaskDefinition,
    port: int,
    desired_count: int,
    use_public_endpoint: bool = True,
    service_name: str | None = None,
) -> ecspat.ApplicationLoadBalancedFargateService:
    service = ecspat.ApplicationLoadBalancedFargateService(
        scope,
        id,
        cluster=cluster,
        task_definition=taskdef,
        listener_port=port,
        desired_count=desired_count,
        service_name=service_name,
        circuit_breaker=ecs.DeploymentCircuitBreaker(
            rollback=True,
        ),
        public_load_balancer=use_public_endpoint,
    )
    return service


def add_cluster(scope: cons.Construct, id: str, vpc: ec2.IVpc) -> ecs.Cluster:
    return ecs.Cluster(scope, id, vpc=vpc)


def _extract_image_name(image_ref):
    name_with_tag = image_ref.split("/")[-1]
    name = name_with_tag.split(":")[0]
    return name

class ScalingThreshold(TypedDict):
    percent: float

class ServiceScalingConfig(TypedDict):
    min_count: int
    max_count: int
    scale_cpu_target: ScalingThreshold
    scale_memory_target: ScalingThreshold

def set_service_scaling(service: ecs.FargateService, config: ServiceScalingConfig):
    scaling = service.auto_scale_task_count(max_capacity=config["max_count"], min_capacity=config["min_count"])
    scaling.scale_on_cpu_utilization('CpuScaling', target_utilization_percent=config["scale_cpu_target"]["percent"])
    scaling.scale_on_memory_utilization('MemoryScaling', target_utilization_percent=config["scale_memory_target"]["percent"])
    
