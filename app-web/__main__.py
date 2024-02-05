import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

config = pulumi.Config("aws")
aws_region = config.require("region")

config = pulumi.Config()
stack = pulumi.get_stack()
org = config.require("org")

vpc = pulumi.StackReference(f"{org}/vpc/{stack}")
ecs = pulumi.StackReference(f"{org}/ecs/{stack}")
app_security_group = pulumi.StackReference(f"{org}/app-security-group/{stack}")
app_ingress = pulumi.StackReference(f"{org}/app-ingress/{stack}")
app_api = pulumi.StackReference(f"{org}/app-api/{stack}")
api_address = app_api.get_output("internal_name").apply(
    lambda v: f"http://{v}/{config.require('api_context_path')}"
)

service = awsx.ecs.FargateService(
    f"{pulumi.get_project()}-service",
    cluster=ecs.get_output("arn"),
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        subnets=vpc.get_output("private_subnet_ids"),
        security_groups=[
            app_security_group.get_output("security_group_id"),
            app_security_group.get_output("lb_security_group_id"),
        ],
    ),
    task_definition_args=awsx.ecs.FargateServiceTaskDefinitionArgs(
        container=awsx.ecs.TaskDefinitionContainerDefinitionArgs(
            name=f"{pulumi.get_project()}-service",
            image=f"{aws.get_caller_identity().account_id}.dkr.ecr.{aws_region}.amazonaws.com/{config.require('image')}:{config.require('tag')}",
            cpu=config.require_int("cpu"),
            memory=config.require_int("memory"),
            essential=True,
            health_check=awsx.ecs.TaskDefinitionHealthCheckArgs(
                command=[
                    "CMD-SHELL",
                    "curl -f http://localhost:8080/healthz || exit 1",
                ],
                interval=30,
                retries=3,
                start_period=60,
                timeout=5,
            ),
            port_mappings=[
                awsx.ecs.TaskDefinitionPortMappingArgs(
                    container_port=8080,
                    name="http",
                    app_protocol=awsx.ecs.TaskDefinitionPortMappingAppProtocol.HTTP,
                    target_group=app_ingress.get_output("target_group_arn"),
                )
            ],
            environment=[
                awsx.ecs.TaskDefinitionKeyValuePairArgs(
                    name="ApiAddress",
                    value=api_address,
                ),
            ],
        ),
    ),
    service_connect_configuration=aws.ecs.ServiceServiceConnectConfigurationArgs(
        enabled=True,
        namespace=ecs.get_output("http_namespace_name"),
        services=[
            aws.ecs.ServiceServiceConnectConfigurationServiceArgs(
                port_name="http",
                discovery_name=f"{pulumi.get_project()}",
                ingress_port_override=8888,
                client_alias=[
                    aws.ecs.ServiceServiceConnectConfigurationServiceClientAliasArgs(
                        port=80,
                        dns_name=f"{pulumi.get_project()}",
                    ),
                ],
            ),
        ],
    ),
    load_balancers=[
        aws.ecs.ServiceLoadBalancerArgs(
            target_group_arn=app_ingress.get_output("target_group_arn"),
            container_name=f"{pulumi.get_project()}-service",
            container_port=8080,
        )
    ],
)

execution_role_arn = service.task_definition.apply(
    lambda task_definition: task_definition.execution_role_arn
    if task_definition
    else None
)


execution_role_name = pulumi.Output.from_input(execution_role_arn).apply(
    lambda arn: arn.split("/")[-1] if arn else None
)

ecr_policy = aws.iam.RolePolicyAttachment(
    f"{pulumi.get_project()}-ecr-policy",
    role=execution_role_name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
)

app_autoscaling_target = aws.appautoscaling.Target(
    f"{pulumi.get_project()}-autoscaling-target",
    max_capacity=config.require("max_instances"),
    min_capacity=config.require("min_instances"),
    resource_id=pulumi.Output.concat(
        "service/", ecs.get_output("name"), "/", service.service.name
    ),
    scalable_dimension="ecs:service:DesiredCount",
    service_namespace="ecs",
)

app_autoscaling_policy = aws.appautoscaling.Policy(
    f"{pulumi.get_project()}-autoscaling-policy",
    policy_type="TargetTrackingScaling",
    resource_id=app_autoscaling_target.resource_id,
    scalable_dimension=app_autoscaling_target.scalable_dimension,
    service_namespace=app_autoscaling_target.service_namespace,
    target_tracking_scaling_policy_configuration={
        "target_value": 90.0,
        "predefined_metric_specification": {
            "predefined_metric_type": "ECSServiceAverageCPUUtilization",
        },
    },
)
