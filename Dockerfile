FROM apache/airflow:3.4.0

USER root
# Add any OS packages needed later (e.g., build tools) here if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY --chown=airflow:root pyproject.toml /opt/airflow/project/pyproject.toml
COPY --chown=airflow:root tracker /opt/airflow/project/tracker

# Install only the tracker package & runtime deps against Airflow's constraints
# so core Airflow / Task SDK packages are not downgraded or conflicted.
ARG AIRFLOW_VERSION=3.4.0
ARG PYTHON_VERSION=3.12
ARG CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

RUN pip install --no-cache-dir \
    --constraint "${CONSTRAINT_URL}" \
    -e /opt/airflow/project --no-deps \
    && pip install --no-cache-dir \
    --constraint "${CONSTRAINT_URL}" \
    httpx feedparser trafilatura sqlalchemy "psycopg[binary]" pgvector pydantic tenacity
