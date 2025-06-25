FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
 && pip install --upgrade pip \
 && pip install --retries=10 -r requirements.txt \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY . .

EXPOSE 5000

CMD ["python3", "app.py"]




