# Use official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies required by OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirement files first to leverage Docker cache
COPY requirements* ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Run the model download script to fetch the large MediaPipe task files
RUN python download_models.py

# Expose port (Hugging Face Spaces automatically route port 7860)
EXPOSE 7860

# Command to run the Flask app via gunicorn
# Note: we bind to 0.0.0.0 and port 7860 for Hugging Face Spaces
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:7860", "--workers", "2", "--timeout", "120"]
