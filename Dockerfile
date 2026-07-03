FROM python:3.12-slim

WORKDIR /app

# Системные зависимости для lxml и Playwright
RUN apt-get update && apt-get install -y \
    gcc libxml2-dev libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright chromium (для JS-источников)
RUN pip install playwright && playwright install chromium --with-deps

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]
