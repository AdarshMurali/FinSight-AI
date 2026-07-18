"""
AWS Secrets Manager + SSM Parameter Store loader for the Flink jobs/producers.
Mirrors backend/services/secrets_loader.py exactly -- same opt-in flag, same
fail-loud-on-error behavior (if USE_AWS_SECRETS=true and AWS is unreachable,
refuse to start with a clear traceback rather than silently run with missing
credentials). boto3 is only imported when the flag is on, so it's not a hard
dependency for local development.

Reuses the SAME finsight/prod secret and the SAME /finsight/chroma_host SSM
param the backend already reads -- Flink doesn't get its own copies, since
that would just be two sources of truth for the same values.
"""
import json
import os

SECRET_ID = "finsight/prod"

SSM_PARAM_TO_ENV = {
    "/finsight/chroma_host": "CHROMA_HOST",
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
    for param_name, env_key in SSM_PARAM_TO_ENV.items():
        value = ssm.get_parameter(Name=param_name)["Parameter"]["Value"]
        os.environ[env_key] = value

    print(
        f"[OK]   Loaded {len(secret)} secrets from Secrets Manager "
        f"({SECRET_ID}) + {len(SSM_PARAM_TO_ENV)} params from SSM Parameter Store"
    )
