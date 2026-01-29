"""Enumeration of status codes for the data mapping processor."""

import enum


class StatusCode(enum.Enum):
    """Enumeration of status codes for the data mapping processor."""

    SUCCESS = 200
    CONFIGURATION_ERROR = 300
    AAS_CONNECTION_ERROR = 301
    SHELL_NOT_FOUND = 302
    AIMC_NOT_FOUND = 303
    AID_NOT_FOUND = 304
    MAPPING_PROCESSOR_ERROR = 400
