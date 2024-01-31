import pulumi
import pulumi_aws as aws


def configure_vpc():
    config = pulumi.Config("vpc")
    vpc_data = config.require_object("config")

    vpc = aws.ec2.Vpc(
        resource_name="vpc_" + vpc_data["region"] + "_" + vpc_data["cidr"],
        cidr_block=vpc_data["cidr"],
        tags={"Name": "vpc_" + vpc_data["region"] + "_" + vpc_data["cidr"]},
    )

    public_subnets = {}
    for subnet in vpc_data["subnets"]:
        if subnet["type"] == "public":
            name = "subnet_" + subnet["type"] + "_" + subnet["az"]
            public_subnets[name] = aws.ec2.Subnet(
                resource_name=name,
                cidr_block=subnet["cidr"],
                map_public_ip_on_launch=True,
                vpc_id=vpc.id,
                tags={"Name": name},
            )
    private_subnets = {}
    for subnet in vpc_data["subnets"]:
        if subnet["type"] == "private":
            name = "subnet_" + subnet["type"] + "_" + subnet["az"]
            private_subnets[name] = aws.ec2.Subnet(
                resource_name=name,
                cidr_block=subnet["cidr"],
                map_public_ip_on_launch=False,
                vpc_id=vpc.id,
                tags={"Name": name},
            )

    igw = aws.ec2.InternetGateway(
        resource_name="internet_gateway",
        vpc_id=vpc.id,
        tags={
            "Name": "internet_gateway",
        },
    )

    # TODO: add EIP?
    nat_gw = {}
    for subnet_name, subnet in private_subnets.items():
        name = "nat_gw_" + subnet_name
        nat_gw[name] = aws.ec2.NatGateway(
            resource_name=name,
            subnet_id=subnet.id,
            connectivity_type="private",
            tags={"Name": name},
        )
        # allocation_id=aws_eip["example"]["id"],

    public_routes = {}
    for subnet_name, subnet in public_subnets.items():
        name = "public_route_" + subnet_name
        public_routes[name] = aws.ec2.RouteTable(
            resource_name=name,
            vpc_id=vpc.id,
            routes=[
                aws.ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=igw.id),
            ],
            tags={
                "Name": name,
            },
        )
        aws.ec2.RouteTableAssociation(
            resource_name="rt_association_" + name,
            subnet_id=subnet.id,
            route_table_id=public_routes[name].id,
        )
    private_routes = {}
    for subnet_name, subnet in private_subnets.items():
        name = "private_route_" + subnet_name
        private_routes[name] = aws.ec2.RouteTable(
            resource_name=name,
            vpc_id=vpc.id,
            routes=[
                aws.ec2.RouteTableRouteArgs(
                    cidr_block="0.0.0.0/0",
                    nat_gateway_id=nat_gw["nat_gw_" + subnet_name].id,
                ),
            ],
            tags={
                "Name": name,
            },
        )
        aws.ec2.RouteTableAssociation(
            resource_name="rt_association_" + name,
            subnet_id=subnet.id,
            route_table_id=private_routes[name].id,
        )
