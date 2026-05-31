FROM python:3.12-slim

WORKDIR /app

RUN adduser --uid 1000 --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser

CMD ["uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "1"]
