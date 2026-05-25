FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BUZZWIRE_DB=/data/buzzwire.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY buzzwire ./buzzwire
COPY config ./config

RUN mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn buzzwire.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
