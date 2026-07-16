# Shared image for both the `backend` and `mcp` services (aws/ec2-backend/docker-compose.yml) --
# same codebase and dependencies, only the entrypoint command differs. Sharing one image
# instead of building two matters on the backend EC2's limited disk budget.
FROM python:3.11-slim

# Unbuffered stdout -- without this, `docker logs`/`docker compose logs` showed
# almost nothing during startup (all the wait_for_db()/secrets-loading print()
# output sat in Python's buffer), which made debugging the ODBC issue below
# harder than it needed to be. Matches the `python -u` convention already used
# for the Flink EC2's background producer scripts.
ENV PYTHONUNBUFFERED=1

# Microsoft ODBC Driver 18 for SQL Server (replicates what's installed natively on the
# backend EC2 -- confirmed via `odbcinst -q -d` before writing this).
#
# NOTE: do not `apt-get purge`/`autoremove` curl/gnupg2 after this -- a first attempt
# at that (2026-07-16) swept away libgssapi-krb5-2, a runtime dependency the ODBC
# driver's .so dlopen()s rather than links against normally, so apt's dependency
# tracking doesn't protect it the way a purge step assumes. Caught via `ldd` showing
# "libgssapi_krb5.so.2 => not found" before it reached production. Disk isn't tight
# enough on this box (post-resize) to be worth re-risking that for a few MB.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 apt-transport-https ca-certificates libgssapi-krb5-2 \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list \
        | sed 's/\[arch=amd64\]/[arch=amd64 signed-by=\/usr\/share\/keyrings\/microsoft-prod.gpg]/' \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

CMD ["python", "main.py"]
