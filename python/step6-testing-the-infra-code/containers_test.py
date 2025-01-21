import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    assertions,
)
import containers


def test_ecs_cluster_defined_with_existing_vpc():
    stack = cdk.Stack()
    vpc = ec2.Vpc(stack, "vpc")
    cluster = containers.add_cluster(stack, "my-test-cluster", vpc=vpc)

    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::ECS::Cluster", 1)
    assert cluster.vpc is vpc


def test_ecs_fargate_task_definition_defined():
    stack = cdk.Stack()
    cpuval = 512
    memval = 1024
    familyval = "test"
    taskcfg: containers.TaskConfig = {
        "cpu": cpuval,
        "memory_limit_mib": memval,
        "family": familyval,
    }
    image = "public.ecr.aws/aws-containers/hello-app-runner:latest"
    containercfg: containers.ContainerConfig = {"image": image}
    taskdef = containers.add_task_definition_with_container(
        stack, f"taskdef-{taskcfg['family']}", taskcfg, containercfg
    )

    assert taskdef.is_fargate_compatible
    assert taskdef in stack.node.children

    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::ECS::TaskDefinition", 1)
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "RequiresCompatibilities": ["FARGATE"],
            "Cpu": str(cpuval),
            "Memory": str(memval),
            "Family": familyval,
        },
    )


def test_container_definition_added_to_task_definition():
    stack = cdk.Stack()
    cpuval = 512
    memval = 1024
    familyval = "test"
    taskcfg: containers.TaskConfig = {
        "cpu": cpuval,
        "memory_limit_mib": memval,
        "family": familyval,
    }
    image_name = "public.ecr.aws/aws-containers/hello-app-runner:latest"
    containercfg: containers.ContainerConfig = {"image": image_name}

    taskdef = containers.add_task_definition_with_container(
        stack, "test-taskdef", taskcfg, containercfg
    )

    template = assertions.Template.from_stack(stack)
    containerdef: ecs.ContainerDefinition = taskdef.default_container  # type: ignore

    assert containerdef is not None
    assert containerdef.image_name == image_name

    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": assertions.Match.array_with(
                [assertions.Match.object_like({"Image": image_name})]
            )
        },
    )


def test_fargate_service_created_with_only_mandatory_properties():
    stack = cdk.Stack()
    vpc = ec2.Vpc(stack, "vpc")
    cluster = containers.add_cluster(stack, "test-cluster", vpc=vpc)
    cpuval = 512
    memval = 1024
    familyval = "test"
    taskcfg: containers.TaskConfig = {
        "cpu": cpuval,
        "memory_limit_mib": memval,
        "family": familyval,
    }
    image_name = "public.ecr.aws/aws-containers/hello-app-runner:latest"
    containercfg: containers.ContainerConfig = {"image": image_name}

    taskdef = containers.add_task_definition_with_container(
        stack, "test-taskdef", taskcfg, containercfg
    )

    port = 80
    desired_count = 1

    service = containers.add_service(
        stack, "test-service", cluster, taskdef, port, desired_count
    )

    sg_capture = assertions.Capture()
    template = assertions.Template.from_stack(stack)

    assert service.cluster == cluster
    assert service.task_definition == taskdef

    template.resource_count_is("AWS::ECS::Service", 1)
    template.has_resource_properties(
        "AWS::ECS::Service",
        {
            "DesiredCount": desired_count,
            "LaunchType": "FARGATE",
            "NetworkConfiguration": assertions.Match.object_like(
                {
                    "AwsvpcConfiguration": assertions.Match.object_like(
                        {
                            "AssignPublicIp": "DISABLED",
                            "SecurityGroups": assertions.Match.array_with([sg_capture]),
                        }
                    )
                }
            ),
        },
    )

    template.has_resource_properties(
        "AWS::EC2::SecurityGroup",
        {
            "SecurityGroupIngress": assertions.Match.array_with(
                [
                    assertions.Match.object_like(
                        {"CidrIp": "0.0.0.0/0", "FromPort": port, "IpProtocol": "tcp"}
                    )
                ]
            )
        },
    )
