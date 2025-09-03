# Use Python slim image for Apple Silicon or Apple Intel - whichever your platform supports
# Docker will automatically detect your systems architecture
FROM python:3.11-slim

# Show platform 
ARG TARGETPLATFORM
RUN echo "Building for: ${TARGETPLATFORM}"

# Set working directory
WORKDIR /app

# Install git to clone the repository and clean up in same layer
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Clone GTFOBins repository
RUN git clone https://github.com/GTFOBins/GTFOBins.github.io.git gtfobins-data

# Copy our MCP server files
COPY server.py .

# Set unbuffered Python output
ENV PYTHONUNBUFFERED=1

#Create logs dir with proper permissions
RUN mkdir -p /app/logs && chmod 755 /app/logs

#Mountable volume for logs
VOLUME /app/logs

# Default command for MCP server
CMD ["python", "/app/server.py"]
