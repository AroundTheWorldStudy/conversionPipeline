# Start from a slim Python image
FROM python:3.11-slim

# Install ffmpeg via apt
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY run.py .
COPY app/ app/

# Expose port and run
EXPOSE 8080
CMD ["python3", "run.py"]
