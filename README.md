# Microservice: Data Mapping Processor

[![Docker Hub](https://img.shields.io/docker/v/engineeringmethodsag/ms-data-mapping-processor?label=Docker%20Hub)](https://hub.docker.com/repository/docker/engineeringmethodsag/ms-data-mapping-processor/general)
[![License: MIT](https://img.shields.io/badge/license-MIT-%23f8a602?label=License&labelColor=%23992b2e)](https://github.com/fluid40/aas-http-client/blob/dk/doxygen/LICENSE)
[![CI](https://github.com/fluid40/ms-data-mapping-processor/actions/workflows/CI.yml/badge.svg?branch=main&cache-bust=1)](https://github.com/fluid40/ms-data-mapping-processor/actions)

Microservice for easily connecting to physical machines via MQTT or OPC UA, reading operational data and providing it in a standardized submodel structure.

This microservice transforms incoming asset data into structured AAS-compatible payloads based on configurable mapping rules. It is designed to sit between asset connectors and AAS repositories, helping you standardize, enrich, and route data reliably within your digital twin pipeline. It uses AIMC submodels to read mapping definitions and AID submodels to establish the connection to an tool via MQTT or OPC UA. Mapping logic is driven by external configuration, so field assignments and transformations can be adapted without changing application code. The service exposes lightweight HTTP endpoints for processing requests and returning normalized response bodies, making it easy to integrate into automated ingestion pipelines and CI/CD-based deployment workflows.

**Table of Contents:**

* [Microservice: Data Mapping Processor](#microservice-data-mapping-processor)
  + [⚙️ Process](#️-process)
  + [🚀 Features](#-features)
  + [📋 Prerequisites](#-prerequisites)
  + [📚 Resources](#-resources)

---

## ⚙️ Process

The service runs as a continuous mapping pipeline:

1. On startup, it loads `service_config.json` and establishes connections to the AAS Registry, Submodel Registry, repository server(s), and Asset Connector.
2. It resolves the configured AAS and searches its referenced submodels for the AIMC submodel (`/idta/AssetInterfacesMappingConfiguration`).
3. It parses AIMC to get mapping definitions, including source value references and target AID submodel IDs.
4. It loads the referenced AID submodels and prepares an in-memory dynamic submodel cache that represents the target structure.
5. In a background worker loop (based on `PollingInterval`), it pulls live values from the Tool via the Asset Connector, applies the AIMC mapping rules, and updates the dynamic submodel content.
6. It updates the submodel descriptors on the registry server so endpoint hrefs point to this microservice endpoints. If service ends, original descriptor will be restored
7. Through HTTP endpoints, clients can read the current mapped result as full submodels, elements, metadata, or value-only responses.

In short, the service continuously transforms live connector data into AAS-compliant submodel data that can be consumed via API.

## 🚀 Features

* ✅ Configuration-driven mapping from incoming asset payloads to AAS-compatible structures
* ✅ Support for AIMC-based mapping definitions with linked AID target context resolution
* ✅ Automatic retrieval of required submodels through registry and repository integration
* ✅ Lightweight HTTP endpoints for processing, normalization, and integration into data pipelines
* ✅ Container-ready deployment via Docker image with CI-backed project workflow
* ✅ Provides Submodel-specification-compliant endpoints for straightforward system integration

---

## 📋 Prerequisites

Before running this service, make sure the following requirements are met:

* Python 3.13 or newer
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
