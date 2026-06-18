FROM python:3.12-slim

# Install ffmpeg for voice audio normalization
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared package first
COPY packages/ /app/packages/

# Copy bot service and migrations
COPY apps/bot/ /app/apps/bot/
COPY migrations/ /app/migrations/

# Install dependencies
RUN pip install --no-cache-dir -r apps/bot/requirements.txt

# Create temp directory for voice processing
RUN mkdir -p /tmp/assistant-audio

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "apps.bot.app.main"]
