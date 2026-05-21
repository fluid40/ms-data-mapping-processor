# 🛠️ Configuration Guide

This guide explains how to configure ms-data-mapping-processor for local and containerized deployments.

**Table of Contents:**

- [🛠️ Configuration Guide](#️-configuration-guide)
  - [Overview](#overview)
  - [Required Folder Structure](#required-folder-structure)
  - [Runtime Service Configuration](#runtime-service-configuration)
  - [Asset Connector Configuration](#asset-connector-configuration)
  - [AAS Registry Configuration](#aas-registry-configuration)
  - [Submodel Registry Configuration](#submodel-registry-configuration)
  - [Repository Server Configuration](#repository-server-configuration)
  - [Environment Variables](#environment-variables)
  - [How SecretVarName Works](#how-secretvarname-works)
  - [Validation Checklist](#validation-checklist)
  - [Typical Startup Errors](#typical-startup-errors)

## Overview

At startup, the service loads runtime settings and connection profiles from the configuration folder.

Default configuration base path:

* configuration/

Runtime config file selection:

* By default, the service loads service_config.json.
* You can override this with environment variable CONFIG_FILE_NAME.

## Required Folder Structure

The following structure is expected:

~~~text
configuration/

	service_config.json
	aas_registry/
		*.json
	submodel_registry/
		*.json
	asset_connector/
		*.json
	repo_server/
		*.json

~~~

Required at startup:

* service_config.json
* at least one file in aas_registry/
* at least one file in submodel_registry/
* at least one file in asset_connector/

Optional but recommended:

* one or more files in repo_server/

## Runtime Service Configuration

File:

* configuration/service_config.json

Example:

~~~json
{

	"AasId": "my-shell-id",
	"PollingInterval": 5,
	"ExternalUrl": "http://my-external-url",
	"ExternalPort": "3088"

}
~~~

Field reference:

* AasId: Target AAS identifier used by the service.
* PollingInterval: Poll cycle in seconds for dynamic value updates.
* ExternalUrl: Public base URL used by the service when exposing descriptor links.
* ExternalPort: Optional public port used together with ExternalUrl, if needed

## Asset Connector Configuration

Folder:

* configuration/asset_connector/

Example:

~~~json
{

	"ServerConfiguration": {
		"BaseUrl": "http://my-asset-connector/",
		"TimeOut": 60,
		"ConnectionTimeOut": 60,
		"TrustEnv": false
	}

}
~~~

Notes:

* This endpoint is used to retrieve live values (for example from MQTT or OPC UA integrations behind the connector).

---

Note:

* A detailed introduction to server configuration options is available in the aas-http-client documentation: https://fluid40.github.io/aas-http-client/md_docs_2configuration.html

## AAS Registry Configuration

Folder:

* configuration/aas_registry/

Example:

~~~json
{

	"ServerConfiguration": {
		"BaseUrl": "https://my-aas-registry/",
		"TimeOut": 60,
		"ConnectionTimeOut": 60,
		"TrustEnv": false,
		"EncodedIds": false
	},
	"SecretVarName": ""

}
~~~

Notes:

* If multiple files exist, the first discovered JSON file is used.
* SecretVarName is optional and can be empty when no auth secret is needed.

## Submodel Registry Configuration

Folder:

* configuration/submodel_registry/

Example:

~~~json
{

	"ServerConfiguration": {
		"BaseUrl": "https://my-sm-registry/",
		"TimeOut": 60,
		"ConnectionTimeOut": 60,
		"TrustEnv": false,
		"EncodedIds": false
	},
	"SecretVarName": ""

}
~~~

Notes:

* If multiple files exist, the first discovered JSON file is used.

## Repository Server Configuration

Folder:

* configuration/repo_server/

You can define multiple repository targets, for example different environments or providers.

Example with OAuth:

~~~json
{

	"ServerConfiguration": {
		"BaseUrl": "https://my-aas-repo/",
		"TimeOut": 60,
		"ConnectionTimeOut": 60,
		"TrustEnv": false,
		"EncodedIds": false,
		"AuthenticationSettings": {
			"OAuth": {
				"ClientId": "workstation-1",
				"TokenUrl": "https://.../token",
				"GrantType": "client_credentials"
			}
		}
	},
	"SecretVarName": "HACK_AAS_SERVER_SECRET"

}
~~~

Example with BasicAuth:

~~~json
{

	"ServerConfiguration": {
		"BaseUrl": "https://my-aas-repo/",
		"TimeOut": 60,
		"ConnectionTimeOut": 60,
		"TrustEnv": false,
		"EncodedIds": false,
		"AuthenticationSettings": {
			"BasicAuth": {
				"Username": "your-user"
			}
		}
	},
	"SecretVarName": "HACK_AAS_SERVER_SECRET"

}
~~~

Important:

* If SecretVarName is set, the environment variable with that exact name must be available at runtime.
* The secret value is read from environment and used as password/client secret depending on auth mode.

## Environment Variables

Common variables:

* CONFIG_FILE_NAME: Name of the runtime config file inside configuration/.
* APP_HOST: Host interface for the HTTP server. Default is 127.0.0.1.
* APP_PORT: HTTP server port. Default is 3088.
* RUN_SERVER: Set to 0 to disable starting the server in module execution contexts.

Authentication variables:

* Any variable referenced by SecretVarName in repository config files.
* Examples from current templates: IQSTRUCT_AAS_SERVER_SECRET, HACK_AAS_SERVER_SECRET.

## How SecretVarName Works

`SecretVarName` defines the name of an environment variable that contains a secret used for server authentication.

Short flow:

* The JSON file provides the variable name (for example `HACK_AAS_SERVER_SECRET`).
* At runtime, the service reads the value from the environment.
* The value is forwarded to the configured auth method (for example OAuth client secret or BasicAuth password).

If `SecretVarName` is empty, no secret variable lookup is performed for that config file.

## Validation Checklist

Before starting the service, verify:

* All required files exist and are valid JSON.
* BaseUrl values are reachable from the runtime network.
* AasId points to an existing shell.
* The target AAS provides AIMC and referenced AID submodels.
* Required secrets are present in environment variables.

## Typical Startup Errors

Configuration base path not found:

* Ensure configuration/ is present in the runtime working directory.
* In Docker, mount configuration/ to /app/configuration.

No registry or connector config found:

* Ensure at least one JSON file exists in each required subfolder.

Authentication failures:

* Ensure SecretVarName matches an exported environment variable.

Connection timeouts:

* Check container networking, DNS/service names, firewall rules, and BaseUrl scheme/port.
