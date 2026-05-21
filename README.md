# Microservice: Data Mapping Processor

[![Docker Hub](https://img.shields.io/docker/v/engineeringmethodsag/ms-data-mapping-processor?label=Docker%20Hub)](https://hub.docker.com/repository/docker/engineeringmethodsag/ms-data-mapping-processor/general)
[![License: MIT](https://img.shields.io/badge/license-MIT-%23f8a602?label=License&labelColor=%23992b2e)](https://github.com/fluid40/aas-http-client/blob/dk/doxygen/LICENSE)
[![CI](https://github.com/fluid40/ms-data-mapping-processor/actions/workflows/CI.yml/badge.svg?branch=main&cache-bust=1)](https://github.com/fluid40/ms-data-mapping-processor/actions)

This microservice transforms incoming asset data into structured AAS-compatible payloads based on configurable mapping rules. It is designed to sit between asset connectors and AAS repositories, helping you standardize, enrich, and route data reliably within your digital twin pipeline. It uses AIMC submodels to read mapping definitions and AID submodels to resolve the target context for those mappings. Mapping logic is driven by external configuration, so field assignments and transformations can be adapted without changing application code. The service exposes lightweight HTTP endpoints for processing requests and returning normalized response bodies, making it easy to integrate into automated ingestion pipelines and CI/CD-based deployment workflows.

**Table of Contents:**

- [Microservice: Data Mapping Processor](#microservice-data-mapping-processor)
  - [🚀 Features](#-features)
    - [Using AID and AIMC Submodels](#using-aid-and-aimc-submodels)

## 🚀 Features

* ✅ Configuration-driven mapping from incoming asset payloads to AAS-compatible structures
* ✅ Support for AIMC-based mapping definitions with linked AID target context resolution
* ✅ Automatic retrieval of required submodels through registry and repository integration
* ✅ Lightweight HTTP endpoints for processing, normalization, and integration into data pipelines
* ✅ Container-ready deployment via Docker image with CI-backed project workflow

### Using AID and AIMC Submodels

This service relies on two core submodel types during startup and runtime processing:

* **AIMC (Asset Interface Mapping Configuration):** The service scans the shell for the submodel with semantic ID `/idta/AssetInterfacesMappingConfiguration`. It parses this submodel to extract mapping configurations, including which AID submodels are required and how incoming values should be transformed.
* **AID submodels:** The AID submodel IDs referenced by AIMC are resolved from the registry and loaded from the connected repository. These AID submodels are then used to configure the Asset Connector and to provide the structural context for mapping source data into target AAS elements.

In short, **AIMC defines the mapping rules**, and **AID provides the concrete target context** used to apply those rules consistently across requests.
