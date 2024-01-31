# create ecr repositories on pulumi python code
import pulumi
import pulumi_aws as aws
import json


def get_repo_name(repo):
    try:
        return repo["github_repo"]
    except KeyError:
        return repo["name"]
    except Exception as e:
        pulumi.log.error(f"Error: {e}")


def get_repo_tags(repo):
    try:
        return repo["tags"]
    except KeyError:
        return {}
    except Exception as e:
        pulumi.log.error(f"Error: {e}")


def create_ecr():
    config = pulumi.Config("ecr")
    ecr_data = config.require_object("config")
    generic_tags = pulumi.Config("tags").require_object("config")
    for repo in ecr_data["repositories"]:
        s_tags = generic_tags | get_repo_tags(repo) | {"Name": repo["name"]}
        aws.ecr.Repository(resource_name=repo["name"], name=repo["name"], tags=s_tags)
    # pulumi.export('repo_name', repo.repository_url)


def create_iam_gh_integration():
    config = pulumi.Config("ecr")
    ecr_data = config.require_object("config")
    github_repositories = []
    generic_tags = pulumi.Config("tags").require_object("config")
    for repo in ecr_data["repositories"]:
        github_repositories.append(get_repo_name(repo))
    for github_repo in list(set(github_repositories)):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": f"arn:aws:iam::{aws.get_caller_identity().account_id}:oidc-provider/token.actions.githubusercontent.com"
                    },
                    "Action": "sts:AssumeRoleWithWebIdentity",
                    "Condition": {
                        "StringLike": {
                            "token.actions.githubusercontent.com:sub": f"repo:{pulumi.Config('artifacts').get_object('config')['org_name']}/{github_repo}:*"
                        },
                        "StringEquals": {
                            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                        },
                    },
                }
            ],
        }
        s_tags = generic_tags | {"Name": github_repo}
        ecr_role = aws.iam.Role(
            resource_name=f"{github_repo}-ecr-role",
            assume_role_policy=json.dumps(policy),
            tags=s_tags,
        )
        ecr_policy = aws.iam.RolePolicyAttachment(
            resource_name=f"{github_repo}-ecr-policy",
            role=ecr_role.name,
            policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess",
        )
