FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8080

CMD ["gunicorn", "app.main:app", "-w", "2", "-b", "0.0.0.0:8080"]
