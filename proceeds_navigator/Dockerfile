FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/snapshots /app/data/exports

ENV DATABASE_URL=sqlite:////app/data/proceeds_navigator.db
ENV DATA_DIR=/app/data
ENV SNAPSHOTS_DIR=/app/data/snapshots
ENV EXPORTS_DIR=/app/data/exports
ENV LOG_LEVEL=info

EXPOSE 8000

CMD ["uvicorn", "proceeds_navigator.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
