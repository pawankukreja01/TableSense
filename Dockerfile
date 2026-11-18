FROM node:22-alpine AS client
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server server
COPY pilot pilot
COPY manage.py .
COPY --from=client /app/frontend/dist frontend/dist
RUN useradd --create-home service && chown -R service:service /app
USER service
CMD ["sh","-ec","python manage.py migrate --noinput; if [ \"$DEMO_MODE\" = 1 ]; then python manage.py seed_demo; fi; exec gunicorn server.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 24 --access-logfile -"]
