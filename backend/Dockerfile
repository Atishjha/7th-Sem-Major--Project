FROM python:3.11-slim

WORKDIR /app

# Keep Python output unbuffered so `docker compose logs` is live, and don't
# write .pyc files into the bind-mounted source tree.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# First-run bootstrap, then serve. `python -m app.bootstrap`:
#   - waits for PostgreSQL to accept connections
#   - applies Alembic migrations (or safely adopts a pre-existing database)
#   - creates the demo accounts when SEED_DEMO_USERS=true
# If it fails the container exits (and says why) instead of serving a
# half-initialised app.
CMD ["sh", "-c", "python -m app.bootstrap && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
