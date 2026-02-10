# Ekumen - Ansible Web Interface
# Docker/Podman build

FROM python:3.12-slim

LABEL maintainer="Aydin Aslangoren"
LABEL description="Ekumen - A simple web interface for running Ansible playbooks"
LABEL version="1.7.5"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ansible \
    openssh-client \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and collections/roles directories
WORKDIR /opt/ekumen
RUN mkdir -p /opt/ekumen/collections /opt/ekumen/roles

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create directories for runtime data
RUN mkdir -p /opt/ekumen/playbooks /opt/ekumen/inventories

# Set environment variables
ENV ANSIBLE_SHUTTLE_HOST=0.0.0.0
ENV ANSIBLE_SHUTTLE_PORT=5000
ENV ANSIBLE_HOST_KEY_CHECKING=False
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run with gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000", "app:app"]
