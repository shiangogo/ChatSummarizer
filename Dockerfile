FROM python:3.11.3

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/ufoscout/docker-compose-wait:latest /wait /wait
RUN chmod +x /wait

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN apt-get update -qq && apt-get install -y postgresql-client
