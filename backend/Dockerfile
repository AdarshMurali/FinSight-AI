# Shared image for both the `backend` and `mcp` services (aws/ec2-backend/docker-compose.yml) --
# same codebase and dependencies, only the entrypoint command differs. Sharing one image
# instead of building two matters on the backend EC2's limited disk budget.
FROM python:3.11-slim

# Microsoft ODBC Driver 18 for SQL Server (replicates what's installed natively on the
# backend EC2 -- confirmed via `odbcinst -q -d` before writing this).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 apt-transport-https ca-certificates \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list \
        | sed 's/\[arch=amd64\]/[arch=amd64 signed-by=\/usr\/share\/keyrings\/microsoft-prod.gpg]/' \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev \
    && apt-get purge -y curl gnupg2 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

CMD ["python", "main.py"]
