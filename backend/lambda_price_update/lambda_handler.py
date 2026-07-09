"""
AWS Lambda entry point for price_update_job.py.

Thin wrapper only — reuses scripts/price_update_job.py unchanged (the exact
version already verified locally against production Azure SQL). Keeping the
job logic identical across local/EC2/Lambda avoids drift between environments.
"""
from scripts.price_update_job import run


def handler(event, context):
    run()
    return {"statusCode": 200}
