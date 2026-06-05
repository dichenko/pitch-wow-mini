FROM python:3.12-slim

WORKDIR /app

# Copy shared package first
COPY packages/ /app/packages/

# Copy admin and bot services
COPY apps/bot/ /app/apps/bot/
COPY apps/admin/ /app/apps/admin/

# Install dependencies
RUN pip install --no-cache-dir -r apps/admin/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["python", "-m", "apps.admin.app.main"]
