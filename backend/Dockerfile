FROM python:3.12-slim

# ffmpeg is required for yt-dlp to merge separate audio/video streams
# into a single file — without it, high-quality formats that come as
# split streams (the norm on YouTube above 1080p) can't be muxed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Runs as a non-root user for defense in depth.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
