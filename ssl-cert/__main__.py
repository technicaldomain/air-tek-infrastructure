import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

config = pulumi.Config()
stack = pulumi.get_stack()
org = config.require("org")
data = pulumi.StackReference(f"{org}/data/{stack}")

route53_zone_id = data.get_output("route53_zone_id").apply(lambda zone_id: f"{zone_id}")
wildcard_san = data.get_output("route53_zone_name").apply(
    lambda zone_name: f"*.{zone_name}"
)


cert = aws.acm.Certificate(
    "certificate",
    domain_name=data.get_output("route53_zone_name"),
    subject_alternative_names=[wildcard_san],
    validation_method="DNS",
)

# Wait for the certificate to be validated
validation_record = aws.route53.Record(
    "validationRecord",
    zone_id=route53_zone_id,
    name=cert.domain_validation_options.apply(
        lambda options: options[0].resource_record_name
    ),
    type=cert.domain_validation_options.apply(
        lambda options: options[0].resource_record_type
    ),
    records=[
        cert.domain_validation_options.apply(
            lambda options: options[0].resource_record_value
        )
    ],
    ttl=600,
)
pulumi.export("arn", cert.arn)
