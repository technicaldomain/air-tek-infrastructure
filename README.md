# Infrastructure provisioning

## Configure environment

### Install aws cli
[How to install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

[Login into account](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-prereqs.html)

### Install pulumi

See actual guide [here](https://www.pulumi.com/docs/get-started/install/)

### Configure Python virtual environments

```shell
python3 -m venv venv
source venv/bin/activate
```
### Install requirements

```shell
pip3 install -r requirements.txt
```

### Run preview

```shell
pulumi preview
```

### Apply changes

```shell
pulumi up
```
