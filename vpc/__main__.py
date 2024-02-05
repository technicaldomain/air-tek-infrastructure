import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

vpc = awsx.ec2.Vpc("vpc")

pulumi.export("vpc", vpc)
pulumi.export("vpc_id", vpc.vpc_id)
pulumi.export("private_subnet_ids", vpc.private_subnet_ids)
pulumi.export("public_subnet_ids", vpc.public_subnet_ids)
