# Base image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port for Flask health check
EXPOSE 8080

# Command to run both Flask + Bot (single main.py with threading)
CMD ["python", "main.py"]
