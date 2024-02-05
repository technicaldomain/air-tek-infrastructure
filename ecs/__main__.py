import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

config = pulumi.Config()
stack = pulumi.get_stack()
org = config.require("org")

vpc = pulumi.StackReference(f"{org}/vpc/{stack}")

http_namespace = aws.servicediscovery.HttpNamespace(
    f"{org}-{stack}", description=f"{org}-{stack}"
)
cluster = aws.ecs.Cluster(
    "cluster",
    service_connect_defaults=aws.ecs.ClusterServiceConnectDefaultsArgs(
        namespace=http_namespace.arn,
    ),
)
pulumi.export("arn", cluster.arn)
pulumi.export("name", cluster.name)
pulumi.export("http_namespace_id", http_namespace.id)
pulumi.export("http_namespace_name", http_namespace.name)
