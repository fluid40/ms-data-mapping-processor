# Microservice: Data Mapping Processor

[![Docker Hub](https://img.shields.io/docker/v/engineeringmethodsag/ms-data-mapping-processor?label=Docker%20Hub)](https://hub.docker.com/repository/docker/engineeringmethodsag/ms-data-mapping-processor/general)
[![License: MIT](https://img.shields.io/badge/license-MIT-%23f8a602?label=License&labelColor=%23992b2e)](https://github.com/fluid40/aas-http-client/blob/dk/doxygen/LICENSE)
[![CI](https://github.com/fluid40/ms-data-mapping-processor/actions/workflows/CI.yml/badge.svg?branch=main&cache-bust=1)](https://github.com/fluid40/ms-data-mapping-processor/actions)

This microservice transforms incoming asset data into structured AAS-compatible payloads based on configurable mapping rules. It is designed to sit between asset connectors and AAS repositories, helping you standardize, enrich, and route data reliably within your digital twin pipeline. It uses AIMC submodels to read mapping definitions and AID submodels to establish the connection to an tool via MQTT or OPC UA. Mapping logic is driven by external configuration, so field assignments and transformations can be adapted without changing application code. The service exposes lightweight HTTP endpoints for processing requests and returning normalized response bodies, making it easy to integrate into automated ingestion pipelines and CI/CD-based deployment workflows.

**Table of Contents:**

- [Microservice: Data Mapping Processor](#microservice-data-mapping-processor)
  - [🚀 Features](#-features)
  - [📋 Prerequisites](#-prerequisites)
  - [📚 Resources](#-resources)

---

## 🚀 Features

* ✅ Configuration-driven mapping from incoming asset payloads to AAS-compatible structures
* ✅ Support for AIMC-based mapping definitions with linked AID target context resolution
* ✅ Automatic retrieval of required submodels through registry and repository integration
* ✅ Lightweight HTTP endpoints for processing, normalization, and integration into data pipelines
* ✅ Container-ready deployment via Docker image with CI-backed project workflow

---

## 📋 Prerequisites

Before running this service, make sure the following requirements are met:

* Python 3.11 or newer
* Reachable AAS infrastructure services (AAS Registry, Submodel Registry, and at least one Repository server)
* A reachable [Asset Connector](https://github.com/fluid40/ms-asset-connector) endpoint (for MQTT/OPC UA-backed data retrieval)
* Valid JSON configuration files under the `configuration/` folder, including:
  + `configuration/service_config.json`
  + `configuration/aas_registry/*.json`
  + `configuration/submodel_registry/*.json`
  + `configuration/asset_connector/*.json`
* An AAS containing an AIMC submodel (`/idta/AssetInterfacesMappingConfiguration`) and referenced AID submodels
* Optional for containerized deployment: Docker engine with network access to the required backend services

---

## 📚 Resources

📘 [Documentation](https://fluid40.github.io/ms-data-mapping-processor/)

📝 [Changelog](docs/CHANGELOG.md)

🤖 [GitHub Releases](https://github.com/fluid40/ms-data-mapping-processor/releases)

📦 [Docker Image](https://hub.docker.com/repository/docker/engineeringmethodsag/ms-data-mapping-processor/general)

📜 [MIT License](https://github.com/fluid40/ms-data-mapping-processor/blob/main/LICENSE)
