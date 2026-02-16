"""Module to handle connections to AAS repo and registry servers."""

import logging
import os

from aas_http_client import AasHttpClient, SdkWrapper, create_wrapper_by_dict
from fastapi import HTTPException

from ms_data_mapping_processor.models.configuration_models import ServerConfiguration, ServerConfigurationsHandler
from ms_data_mapping_processor.models.constants import StatusCode

logger = logging.getLogger(__name__)


class ServerHandler:
    """Class to handle connections to AAS servers and the AAS registry."""

    aas_registry_client: AasHttpClient
    sm_registry_client: AasHttpClient
    aas_server_wrappers: dict[str, SdkWrapper]

    def __init__(self):
        """Initialize ServerHandler with default values."""
        self.aas_registry_client = None
        self.sm_registry_client = None
        self.aas_server_wrappers = {}

    def connect_to_server(self, configuration_files_handler: ServerConfigurationsHandler):
        """Create AAS server clients for all configured AAS servers and the AAS registry."""
        self._connect_to_aas_registry(configuration_files_handler.aas_registry_configuration)
        self._connect_to_sm_registry(configuration_files_handler.sm_registry_configuration)
        self._connect_to_repo_server(configuration_files_handler.repo_server_configurations)

    def _connect_to_aas_registry(self, configuration: ServerConfiguration) -> AasHttpClient:
        """Create AAS registry client using the provided configuration.

        :param configuration: The server configuration
        :raises HTTPException: If the connection to the AAS registry could not be established
        """
        logger.info("Create AAS registry client.")
        registry_wrapper = _connect_to_aas_server(configuration.server_configuration, configuration.secret_var_name)

        if registry_wrapper is None:
            logger.error("Failed to create AAS registry client.")
            raise HTTPException(
                status_code=StatusCode.AAS_REGISTRY_CONNECTION_ERROR.value, detail="Could not connect to AAS Registry. Client not created."
            )

        self.aas_registry_client = registry_wrapper.get_client()

    def _connect_to_sm_registry(self, configuration: ServerConfiguration) -> AasHttpClient:
        """Create Submodel registry client using the provided configuration.

        :param configuration: The server configuration
        :raises HTTPException: If the connection to the AAS registry could not be established
        """
        logger.info("Create Submodel registry client.")
        registry_wrapper = _connect_to_aas_server(configuration.server_configuration, configuration.secret_var_name)

        if registry_wrapper is None:
            logger.error("Failed to create Submodel registry client.")
            raise HTTPException(
                status_code=StatusCode.AAS_REGISTRY_CONNECTION_ERROR.value, detail="Could not connect to Submodel Registry. Client not created."
            )

        self.sm_registry_client = registry_wrapper.get_client()

    def _connect_to_repo_server(self, configurations: list[ServerConfiguration]):
        """Create AAS server wrappers for all configured AAS servers.

        :param configuration: The server configuration
        """
        logger.info(f"Create AAS server wrappers for {len(configurations)} configured AAS servers.")

        for configuration in configurations:
            wrapper = _connect_to_aas_server(configuration.server_configuration, configuration.secret_var_name)

            if wrapper is not None and wrapper.base_url not in self.aas_server_wrappers:
                logger.info(f"AAS server wrapper for base URL '{wrapper.base_url}' created.")
                self.aas_server_wrappers[wrapper.base_url] = wrapper

    def get_or_create_repo_wrapper(self, base_url: str) -> SdkWrapper:
        """Get or create an AAS server wrapper for the given base URL.

        :param base_url: The base URL of the AAS server
        :return: The AAS server wrapper or None
        """
        if base_url in self.aas_server_wrappers:
            logger.debug(f"AAS server wrapper for base URL '{base_url}' found in cache.")
            return self.aas_server_wrappers[base_url]

        logger.info(f"AAS server wrapper for base URL '{base_url}' not found in cache. Create new wrapper.")

        wrapper = _connect_to_aas_server({"BaseUrl": base_url, "EncodedIds": False}, "")

        if wrapper is not None:
            logger.info(f"AAS server wrapper for base URL '{base_url}' created.")
            self.aas_server_wrappers[base_url] = wrapper
            return wrapper

        logger.error(f"Could not create AAS server wrapper for base URL '{base_url}'.")
        raise HTTPException(
            status_code=StatusCode.CREATE_REPO_CONNECTION_ERROR.value, detail="Could not create AAS server wrapper for base URL '{base_url}'."
        )


def _connect_to_aas_server(server_configuration: dict, secret_var_name: str) -> SdkWrapper | None:
    """Connect to the AAS server and create a server wrapper by a given configuration file.

    :param server_configuration: The AAS server configuration
    :param secret_var_name: The name of the environment variable that contains the AAS authentication secret.
    :return: The created server wrapper or None
    """
    logger.info("Connect to AAS server.")

    logger.debug(f"Get AAS server secret from environment variable '{secret_var_name}'.")
    server_secret: str = os.getenv(secret_var_name, "")

    # Ensure EncodedIds is set to False
    server_configuration["EncodedIds"] = False

    try:
        wrapper: SdkWrapper | None = create_wrapper_by_dict(server_configuration, server_secret, server_secret, server_secret)
    except Exception as ve:
        logger.error(f"Could not create AAS server wrapper: {ve}")
        return None

    if wrapper is None:
        logger.error("Could not connect to AAS server. Client not created.")
        return None

    return wrapper
