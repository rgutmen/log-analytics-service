# slim variant keeps the image small without needing build tools
FROM python:3.13-slim

WORKDIR /app

# install dependencies before copying app code so this layer is cached across code-only changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8080

# --access-logfile - writes request logs to stdout so CloudWatch picks them up
CMD ["gunicorn", "app.main:app", "-w", "2", "-b", "0.0.0.0:8080", "--access-logfile", "-"]
