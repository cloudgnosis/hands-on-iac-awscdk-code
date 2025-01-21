from typing import Literal, TypedDict  # noqa
import constructs as cons
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
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

    image = ecs.ContainerImage.from_registry(container_config["image"])
    image_id = f"container-{_extract_image_name(container_config['image'])}"
    taskdef.add_container(image_id, image=image)

    return taskdef


def add_cluster(scope: cons.Construct, id: str, vpc: ec2.IVpc) -> ecs.Cluster:
    return ecs.Cluster(scope, id, vpc=vpc)


def _extract_image_name(image_ref):
    name_with_tag = image_ref.split("/")[-1]
    name = name_with_tag.split(":")[0]
    return name
