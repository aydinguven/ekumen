# Docker / Podman Deployment

Ekumen can be run in a container using Docker or Podman.

## Quick Start with Docker Compose

```bash
cd docker
docker-compose up -d
```

## Build and Run Manually

```bash
# Build the image
docker build -t ekumen -f docker/Dockerfile .

# Run the container
docker run -d \
  --name ekumen \
  -p 5000:5000 \
  -v ekumen-playbooks:/opt/ekumen/playbooks \
  -v ekumen-collections:/opt/ekumen/collections \
  ekumen
```

## Podman (rootless)

```bash
# Build the image
podman build -t ekumen -f docker/Dockerfile .

# Run with persistent volumes
podman run -d \
  --name ekumen \
  -p 5000:5000 \
  -v ekumen-playbooks:/opt/ekumen/playbooks:Z \
  -v ekumen-collections:/opt/ekumen/collections:Z \
  -v ekumen-roles:/opt/ekumen/roles:Z \
  ekumen
```

Access the interface at http://localhost:5000
