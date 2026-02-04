"""Enumeration of status codes for the data mapping processor."""

import enum

CONFIG_BASE_PATH = "configuration/"


class StatusCode(enum.Enum):
    """Enumeration of status codes for the data mapping processor."""

    SUCCESS = 200
    CONFIGURATION_ERROR = 300
    AAS_REGISTRY_CONNECTION_ERROR = 301
    SHELL_NOT_FOUND = 302
    AIMC_NOT_FOUND = 303
    AID_NOT_FOUND = 304
    MAPPING_PROCESSOR_ERROR = 305
    ASSET_CONNECTOR_CONNECTION_ERROR = 306
    AID_CONFIGURATION_ERROR = 307
    CREATE_REPO_CONNECTION_ERROR = 308
