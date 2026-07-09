# Lambda container image for price_update_job.py
# Build context must be backend/  (docker build -f lambda_price_update/Dockerfile .)
#
# Uses AWS's documented "alternative base image" pattern (plain Debian + the
# Lambda Runtime Interface Client via pip) instead of the official Lambda
# Python base image -- the official image is Amazon Linux 2, whose bundled
# openssl-snapsafe-libs conflicts with the openssl-libs that msodbcsql18
# needs, and removing it breaks yum itself. Debian's Microsoft ODBC driver
# install has no such conflict.
FROM python:3.11-slim-bookworm

# Microsoft ODBC Driver 18 for SQL Server (Debian 12 / bookworm)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg2 unixodbc unixodbc-dev \
    && mkdir -p /usr/share/keyrings \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Lambda Runtime Interface Client -- lets a non-Lambda-base image run as a
# Lambda function (AWS's documented pattern for custom base images)
RUN pip install --no-cache-dir awslambdaric

WORKDIR /var/task

COPY lambda_price_update/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY database.py models.py config.py ./
COPY scripts/price_update_job.py ./scripts/price_update_job.py
COPY lambda_price_update/lambda_handler.py ./

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["lambda_handler.handler"]
