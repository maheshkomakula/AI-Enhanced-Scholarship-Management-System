FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps for building some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libmariadb-dev-compat \
    libmariadb-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "Backend.app:app", "--bind", "0.0.0.0:5000", "--workers", "4"]
