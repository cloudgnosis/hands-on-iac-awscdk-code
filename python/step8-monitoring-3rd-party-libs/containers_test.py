import pytest
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
    config = containers.ClusterConfig(vpc=vpc)
    cluster = containers.add_cluster(stack, "my-test-cluster", config)

    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::ECS::Cluster", 1)
    assert cluster.vpc is vpc


def test_check_that_container_insights_become_enabled():
    stack = cdk.Stack()
    vpc = ec2.Vpc(stack, "vpc")
    config = containers.ClusterConfig(vpc=vpc, enable_container_insights=True)
    containers.add_cluster(stack, "test-cluster", config)

    template = assertions.Template.from_stack(stack)

    template.has_resource_properties('AWS::ECS::Cluster', {
        'ClusterSettings': assertions.Match.array_with(
            pattern=[
                assertions.Match.object_equals(pattern={
                    'Name': 'containerInsights',
                    'Value': 'enabled'
                })
            ]
        )
    })

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
    containercfg: containers.ContainerConfig = {"image": image, "tcp_ports": [8000]}
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
    containercfg: containers.ContainerConfig = {
        "image": image_name,
        "tcp_ports": [8000],
    }

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


@pytest.fixture
def service_test_input_data():
    stack = cdk.Stack()
    vpc = ec2.Vpc(stack, "vpc")
    config=containers.ClusterConfig(vpc=vpc)
    cluster = containers.add_cluster(stack, "test-cluster", config)
    cpuval = 512
    memval = 1024
    familyval = "test"
    taskcfg: containers.TaskConfig = {
        "cpu": cpuval,
        "memory_limit_mib": memval,
        "family": familyval,
    }
    image_name = "public.ecr.aws/aws-containers/hello-app-runner:latest"
    containercfg: containers.ContainerConfig = {
        "image": image_name,
        "tcp_ports": [8000],
    }

    taskdef = containers.add_task_definition_with_container(
        stack, "test-taskdef", taskcfg, containercfg
    )
    return {"stack": stack, "cluster": cluster, "task_definition": taskdef}


def test_fargate_service_created_with_only_mandatory_properties(
    service_test_input_data,
):
    stack = service_test_input_data["stack"]
    cluster = service_test_input_data["cluster"]
    taskdef = service_test_input_data["task_definition"]

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

    template.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 1)
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
        {"Type": "application", "Scheme": "internet-facing"},
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


def test_fargate_service_created_without_public_access(service_test_input_data):
    stack = service_test_input_data["stack"]
    cluster = service_test_input_data["cluster"]
    taskdef = service_test_input_data["task_definition"]

    port = 80
    desired_count = 1
    containers.add_service(
        stack, "test-service", cluster, taskdef, port, desired_count, False
    )

    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 1)
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
        {"Type": "application", "Scheme": "internal"},
    )


def test_scaling_settings_for_service(service_test_input_data):
    stack = service_test_input_data["stack"]
    cluster = service_test_input_data["cluster"]
    taskdef = service_test_input_data["task_definition"]
    port = 80
    desired_count = 2

    service = containers.add_service(
        stack, "test-service", cluster, taskdef, port, desired_count, False
    )

    config = containers.ServiceScalingConfig(
        min_count=1,
        max_count=5,
        scale_cpu_target=containers.ScalingThreshold(percent=50),
        scale_memory_target=containers.ScalingThreshold(percent=50),
    )
    containers.set_service_scaling(service=service.service, config=config)

    scale_resource = assertions.Capture()
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::ApplicationAutoScaling::ScalableTarget", 1)
    template.has_resource_properties(
        "AWS::ApplicationAutoScaling::ScalableTarget",
        {
            "MaxCapacity": config["max_count"],
            "MinCapacity": config["min_count"],
            "ResourceId": scale_resource,
            "ScalableDimension": "ecs:service:DesiredCount",
            "ServiceNamespace": "ecs",
        },
    )

    template.resource_count_is("AWS::ApplicationAutoScaling::ScalingPolicy", 2)
    template.has_resource_properties(
        "AWS::ApplicationAutoScaling::ScalingPolicy",
        {
            "PolicyType": "TargetTrackingScaling",
            "TargetTrackingScalingPolicyConfiguration": assertions.Match.object_like(
                {
                    "PredefinedMetricSpecification": assertions.Match.object_equals(
                        {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"}
                    ),
                    "TargetValue": config["scale_cpu_target"]["percent"],
                }
            ),
        },
    )
    template.has_resource_properties(
        "AWS::ApplicationAutoScaling::ScalingPolicy",
        {
            "PolicyType": "TargetTrackingScaling",
            "TargetTrackingScalingPolicyConfiguration": assertions.Match.object_like(
                {
                    "PredefinedMetricSpecification": assertions.Match.object_equals(
                        {"PredefinedMetricType": "ECSServiceAverageMemoryUtilization"}
                    ),
                    "TargetValue": config["scale_memory_target"]["percent"],
                }
            ),
        },
    )
