# 🐳 Docker Setup

This guide explains how to run ms-data-mapping-processor in Docker.

**Table of Contents:**

- [🐳 Docker Setup](#-docker-setup)
  - [Prerequisites](#prerequisites)
  - [Prepare Configuration](#prepare-configuration)
  - [Option A: Pull Prebuilt Image](#option-a-pull-prebuilt-image)
  - [Option B: Build Image Locally](#option-b-build-image-locally)
  - [Run Container (docker run)](#run-container-docker-run)
  - [Run with Docker Compose](#run-with-docker-compose)
  - [Verify the Service](#verify-the-service)
  - [Troubleshooting](#troubleshooting)

## Prerequisites

* Docker Engine 24+ with Docker Compose plugin
* Network connectivity from the container to:
  + AAS Registry
  + Submodel Registry
  + At least one AAS repository
  + Asset Connector service
* Valid configuration files in the project `configuration/` directory

## Prepare Configuration

The container reads runtime configuration from the `configuration/` directory (default path inside the container).

Required files and folders:

* `configuration/service_config.json`
* `configuration/aas_registry/*.json`
* `configuration/submodel_registry/*.json`
* `configuration/asset_connector/*.json`
* `configuration/repo_server/*.json` (at least one recommended)

Notes:

* By default, startup reads `configuration/service_config.json`.
* Set `CONFIG_FILE_NAME` to use a different runtime config filename.
* If repository configs require secrets (`SecretVarName`), pass matching environment variables to the container.

## Option A: Pull Prebuilt Image

```bash
docker pull engineeringmethodsag/ms-data-mapping-processor:latest
```

## Option B: Build Image Locally

From the repository root:

```bash
docker build -t ms-data-mapping-processor:local .
```

## Run Container (docker run)

Example using the local build tag:

```bash
docker run --rm \
	--name ms-data-mapping-processor \
	-p 3088:3088 \
	-e APP_HOST=0.0.0.0 \
	-e APP_PORT=3088 \
	-e CONFIG_FILE_NAME=service_config.json \
	-e IQSTRUCT_AAS_SERVER_SECRET="<your-secret-if-needed>" \
	-e HACK_AAS_SERVER_SECRET="<your-secret-if-needed>" \
	-v "$(pwd)/configuration:/app/configuration:ro" \
	ms-data-mapping-processor:local
```

If you use the published image, replace the last line with:

```bash
engineeringmethodsag/ms-data-mapping-processor:latest
```

## Run with Docker Compose

Create `docker-compose.yml` :

```yaml
services:
  ms-data-mapping-processor:
    image: engineeringmethodsag/ms-data-mapping-processor:latest
    container_name: ms-data-mapping-processor
    ports:
      - "3088:3088"
    environment:
      APP_HOST: "0.0.0.0"
      APP_PORT: "3088"
      CONFIG_FILE_NAME: "service_config.json"
    volumes:
      - ./configuration:/app/configuration:ro
    restart: unless-stopped
```

Start:

```bash
docker compose up -d
```

Stop:

```bash
docker compose down
```

## Verify the Service

Check health endpoint:

```bash
curl -s http://localhost:3088/health
```

Check root endpoint:

```bash
curl -s http://localhost:3088/
```

Open API docs in browser:

* `http://localhost:3088/docs`

## Troubleshooting

* Startup fails with configuration errors:
  + Confirm `configuration/` is mounted to `/app/configuration`.
  + Confirm required JSON files exist and are valid JSON.
* Connection errors to registry/repository/asset connector:
  + Verify BaseUrl values in config files are reachable from inside the container.
  + If using Docker networks, ensure service names in BaseUrl are resolvable.
* Auth errors for repository servers:
  + Ensure all environment variables referenced by `SecretVarName` are provided.
