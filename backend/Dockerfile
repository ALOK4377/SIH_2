# Samanvay backend image.
# Build context is the REPO ROOT (see docker-compose.yml) so the bundled
# data/ (synthetic dataset + reference dictionaries) is available at runtime.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first for better layer caching.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the repo (backend code + data/ reference & synthetic files).
COPY . /app

WORKDIR /app/backend
EXPOSE 8000

# Seed the DB (load synthetic + run pipeline) on first boot, then serve.
CMD ["sh", "-c", "python /app/scripts/seed_db.py || true; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
