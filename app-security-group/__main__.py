import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

config = pulumi.Config()
stack = pulumi.get_stack()
org = config.require("org")

vpc = pulumi.StackReference(f"{org}/vpc/{stack}")

security_group = aws.ec2.SecurityGroup(
    f"{pulumi.get_project()}-security-group",
    vpc_id=vpc.get_output("vpc_id"),
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port="8080",
            to_port="8080",
            self=True,
            description="Allow port 8080 within security group",
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port="80",
            to_port="80",
            self=True,
            description="Allow port 80 within security group",
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port="8888",
            to_port="8888",
            self=True,
            description="Allow port 8888 within security group to communicate with Service Connect proxy",
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        )
    ],
)
lb_security_group = aws.ec2.SecurityGroup(
    f"{pulumi.get_project()}-lb-security-group",
    vpc_id=vpc.get_output("vpc_id"),
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port="8080",
            to_port="8080",
            self=True,
            description="Allow port 8080 within security group",
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        )
    ],
)
pulumi.export("security_group_id", security_group.id)
pulumi.export("security_group_name", security_group.name)
pulumi.export("security_group_arn", security_group.arn)
pulumi.export("lb_security_group_id", lb_security_group.id)
pulumi.export("lb_security_group_name", lb_security_group.name)
pulumi.export("lb_security_group_arn", lb_security_group.arn)
