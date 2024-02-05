import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

config = pulumi.Config()
stack = pulumi.get_stack()
org = config.require("org")

vpc = pulumi.StackReference(f"{org}/vpc/{stack}")
app_security_group = pulumi.StackReference(f"{org}/app-security-group/{stack}")
ssl_cert = pulumi.StackReference(f"{org}/ssl-cert/{stack}")
data = pulumi.StackReference(f"{org}/data/{stack}")

route53_zone_id = data.get_output("route53_zone_id").apply(lambda zone_id: f"{zone_id}")
route53_record_name = data.get_output("route53_zone_name").apply(
    lambda zone_name: f"{config.require('hostname')}.{zone_name}"
)

# Allow traffic to the ALB from the internet
security_group_alb = aws.ec2.SecurityGroup(
    f"{pulumi.get_project()}-alb-security-group",
    vpc_id=vpc.get_output("vpc_id"),
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="Allow HTTP traffic",
            from_port="80",
            to_port="80",
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="Allow HTTPS traffic",
            from_port="443",
            to_port="443",
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            description="Allow all traffic",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            ipv6_cidr_blocks=["::/0"],
        )
    ],
)


# create s3 bucket for alb logs
aws_s3_bucket = aws.s3.Bucket(
    f"{pulumi.get_project()}-s3-alb-logs",
    acl="private",
    force_destroy=True,
)


# grant the ALB access to write logs to the S3 bucket
aws.s3.BucketPolicy(
    f"{pulumi.get_project()}-alb-logs-policy",
    bucket=aws_s3_bucket.id,
    policy=aws_s3_bucket.arn.apply(
        lambda arn: f"""
{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Principal": {{
                "AWS": "arn:aws:iam::127311923021:root"
            }},
            "Action": "s3:PutObject",
            "Resource": "{arn}/{pulumi.get_project()}-alb-logs/AWSLogs/{aws.get_caller_identity().account_id}/*"
        }},
        {{
            "Effect": "Allow",
            "Principal": {{
                "Service": "delivery.logs.amazonaws.com"
            }},
            "Action": "s3:PutObject",
            "Resource": "{arn}/{pulumi.get_project()}-alb-logs/AWSLogs/{aws.get_caller_identity().account_id}/*",
            "Condition": {{
                "StringEquals": {{
                    "s3:x-amz-acl": "bucket-owner-full-control"
                }}
            }}
        }},
        {{
            "Effect": "Allow",
            "Principal": {{
                "Service": "delivery.logs.amazonaws.com"
            }},
            "Action": "s3:GetBucketAcl",
            "Resource": "{arn}"
        }}
    ]
}}
"""
    ),
)

alb = aws.lb.LoadBalancer(
    f"{pulumi.get_project()}-alb",
    internal=False,
    load_balancer_type="application",
    security_groups=[
        security_group_alb.id,
        app_security_group.get_output("lb_security_group_id"),
    ],
    subnets=vpc.get_output("public_subnet_ids"),
    enable_deletion_protection=False,
    access_logs=aws.lb.LoadBalancerAccessLogsArgs(
        bucket=aws_s3_bucket.id,
        prefix=f"{pulumi.get_project()}-alb-logs",
        enabled=True,
    ),
)

alb_target_group = aws.lb.TargetGroup(
    f"{pulumi.get_project()}-tg",
    port=8080,
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc.get_output("vpc_id"),
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        path="/healthz",
        port="8080",
        protocol="HTTP",
    ),
)


# Create an HTTPS listener and an HTTP listener that redirects to HTTPS
https_listener = aws.alb.Listener(
    f"{pulumi.get_project()}-https-listener",
    load_balancer_arn=alb.arn,
    port=443,
    protocol="HTTPS",
    ssl_policy="ELBSecurityPolicy-2016-08",
    certificate_arn=ssl_cert.get_output("arn"),
    default_actions=[
        aws.alb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=alb_target_group.arn,
        )
    ],
)

http_listener = aws.alb.Listener(
    f"{pulumi.get_project()}-http-listener",
    load_balancer_arn=alb.arn,
    port=80,
    default_actions=[
        aws.alb.ListenerDefaultActionArgs(
            type="redirect",
            redirect=aws.alb.ListenerDefaultActionRedirectArgs(
                port="443", protocol="HTTPS", status_code="HTTP_301"
            ),
        )
    ],
)


# Exclude the "/healthz" path from the load balancer external access by adding a rule to the listener
health_check_rule = aws.alb.ListenerRule(
    f"{pulumi.get_project()}-health-check-rule",
    listener_arn=https_listener.arn,
    priority=100,
    actions=[
        aws.alb.ListenerRuleActionArgs(
            type="fixed-response",
            fixed_response=aws.alb.ListenerRuleActionFixedResponseArgs(
                status_code="418",
                content_type="text/plain",
                message_body="I'm a teapot",
            ),
        ),
    ],
    conditions=[
        aws.alb.ListenerRuleConditionArgs(
            path_pattern=aws.alb.ListenerRuleConditionPathPatternArgs(
                values=["/healthz"],
            ),
        ),
    ],
)

# Create DNS A-Record in Route53 pointing to the ALB
dns_record = aws.route53.Record(
    f"{pulumi.get_project()}-dns-record",
    zone_id=route53_zone_id,
    name=route53_record_name,
    type="A",
    aliases=[
        aws.route53.RecordAliasArgs(
            name=alb.dns_name,
            zone_id=alb.zone_id,
            evaluate_target_health=True,
        ),
    ],
)

pulumi.export("target_group_arn", alb_target_group.arn)
