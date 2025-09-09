# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Install Python deps first (better caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Heroku provides PORT at runtime
# (EXPOSE not required by Heroku, but fine to keep)
EXPOSE 8000

# Start app on the Heroku-assigned port
CMD ["bash","-lc","uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
