# Use the lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 5001

# Run the app (host 0.0.0.0 required for Docker)
CMD ["python", "app.py"]