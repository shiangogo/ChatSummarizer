FROM python:3.11.3

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py migrate

EXPOSE 8000

VOLUME /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
