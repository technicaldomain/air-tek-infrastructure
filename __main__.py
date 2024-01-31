import pulumi
import network
import ecr


def check4config(config, key="config"):
    if pulumi.Config(config).get_object(key) is None:
        return False
    return True


if check4config("ecr"):
    ecr.create_ecr()
    ecr.create_iam_gh_integration()

# if check4config("vpc"):
#     network.configure_vpc()
