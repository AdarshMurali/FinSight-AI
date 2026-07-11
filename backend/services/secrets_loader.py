"""
AWS Secrets Manager + SSM Parameter Store loader — Task 7.2
=============================================================
Populates os.environ from AWS before config.py's Settings() reads them.
Opt-in via USE_AWS_SECRETS=true — local dev keeps using the plain .env
file untouched. boto3 is only imported when the flag is on, so it's not
a hard dependency for local development.

Fails loudly on error (no try/except swallowing): if USE_AWS_SECRETS=true
and AWS is unreachable, the app should refuse to start with a clear
traceback rather than silently boot with missing DB/API credentials.
"""
import json
import os

SECRET_ID = "finsight/prod"

SSM_PARAM_TO_ENV = {
    "/finsight/chroma_host": "CHROMA_HOST",
    "/finsight/chroma_port": "CHROMA_PORT",
    "/finsight/kafka_bootstrap_servers": "KAFKA_BOOTSTRAP_SERVERS",
}


def load_aws_secrets() -> None:
    if os.environ.get("USE_AWS_SECRETS", "").lower() != "true":
        return

    import boto3

    region = os.environ.get("AWS_REGION", "ap-south-1")

    sm = boto3.client("secretsmanager", region_name=region)
    secret = json.loads(sm.get_secret_value(SecretId=SECRET_ID)["SecretString"])
    for key, value in secret.items():
        os.environ[key] = str(value)

    ssm = boto3.client("ssm", region_name=region)
    response = ssm.get_parameters(Names=list(SSM_PARAM_TO_ENV.keys()))
    for param in response["Parameters"]:
        os.environ[SSM_PARAM_TO_ENV[param["Name"]]] = param["Value"]

    missing = set(SSM_PARAM_TO_ENV) - {p["Name"] for p in response["Parameters"]}
    if missing:
        raise RuntimeError(f"SSM parameters not found: {missing}")

    print(
        f"[OK]   Loaded {len(secret)} secrets from Secrets Manager "
        f"({SECRET_ID}) + {len(response['Parameters'])} params from SSM Parameter Store"
    )
