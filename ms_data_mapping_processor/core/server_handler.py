"""Module to handle connections to AAS repo and registry servers."""

import logging
import os
from pathlib import Path

from aas_http_client import AasHttpClient, SdkWrapper, create_wrapper_by_dict
from fastapi import HTTPException
from pydantic import ValidationError

from ms_data_mapping_processor.models.configuration_models import AasServerConfiguration, ServiceConfiguration
from ms_data_mapping_processor.models.constants import CONFIG_BASE_PATH, StatusCode

logger = logging.getLogger(__name__)


class ServerHandler:
    """Class to handle connections to AAS servers and the AAS registry."""

    aas_registry_client: AasHttpClient
    sm_registry_client: AasHttpClient
    aas_server_wrappers: dict[str, SdkWrapper]
    _aas_registry_configuration: AasServerConfiguration
    _sm_registry_configuration: AasServerConfiguration
    _repo_server_configurations: list[AasServerConfiguration]

    def __init__(self):
        """Initialize ServerHandler with default values."""
        self.aas_registry_client = None
        self.sm_registry_client = None
        self.aas_server_wrappers = {}
        self._aas_registry_configuration = None
        self._sm_registry_configuration = None
        self._repo_server_configurations = []
        self._get_config_files()

    def _get_config_files(self):
        config_base_path = Path(CONFIG_BASE_PATH)

        if not config_base_path.exists() or not config_base_path.is_dir():
            logger.error(f"Configuration base path '{config_base_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"Configuration base path '{config_base_path}' not found.",
            )

        self._get_aas_registry_config()
        self._get_sm_registry_config()
        self._get_repos_configs()

    def _get_aas_registry_config(self):
        config_path = Path(f"{CONFIG_BASE_PATH}/aas_registry")

        if not config_path.exists() or not config_path.is_dir():
            logger.error(f"AAS registry configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"AAS registry configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            logger.error(f"No AAS registry configuration files found in folder '{config_path}'.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"No AAS registry configuration files found in folder '{config_path}'.",
            )

        logger.debug(f"Found {len(json_files)} AAS registry configuration files in folder '{config_path}'.")

        if len(json_files) > 1:
            logger.warning(f"Multiple AAS registry configuration files found. Using the first one: '{json_files[0]}'.")

        try:
            self._aas_registry_configuration = AasServerConfiguration.model_validate_json(json_files[0].read_text())
        except ValidationError as ve:
            logger.error(f"Invalid Submodel registry connection file: {ve}")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail="Invalid Submodel registry connection file.",
            ) from ve

    def _get_sm_registry_config(self):
        config_path = Path(f"{CONFIG_BASE_PATH}/submodel_registry")

        if not config_path.exists() or not config_path.is_dir():
            logger.error(f"Submodel registry configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"Submodel registry configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            logger.error(f"No Submodel registry configuration files found in folder '{config_path}'.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"No Submodel registry configuration files found in folder '{config_path}'.",
            )

        logger.debug(f"Found {len(json_files)} Submodel registry configuration files in folder '{config_path}'.")

        if len(json_files) > 1:
            logger.warning(f"Multiple Submodel registry configuration files found. Using the first one: '{json_files[0]}'.")

        try:
            self._sm_registry_configuration = AasServerConfiguration.model_validate_json(json_files[0].read_text())
        except ValidationError as ve:
            logger.error(f"Invalid Submodel registry connection file: {ve}")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail="Invalid Submodel registry connection file.",
            ) from ve

    def _get_repos_configs(self):
        """Get the AAS server configurations from the service configuration.

        :param configuration: The service configuration
        :return: List of AAS server configurations
        """
        config_path = Path(f"{CONFIG_BASE_PATH}/repo_server")

        if not config_path.exists() or not config_path.is_dir():
            logger.error(f"AAS repository configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"AAS repository configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            logger.info(f"No AAS repository configuration files found in folder '{config_path}'.")
            return

        for json_file in json_files:
            try:
                aas_server_configuration = AasServerConfiguration.model_validate_json(json_file.read_text())
                self._repo_server_configurations.append(aas_server_configuration)
            except ValidationError as ve:
                logger.error(f"Invalid AAS repository connection file '{json_file}': {ve}")

        logger.debug(f"Found {len(self._repo_server_configurations)} AAS repository configuration files in folder '{config_path}'.")

    def connect_to_server(self):
        """Create AAS server clients for all configured AAS servers and the AAS registry."""
        self._connect_to_aas_registry()
        self._connect_to_sm_registry()
        self._connect_to_repo_server()

    def _connect_to_aas_registry(self) -> AasHttpClient:
        """Create AAS registry client using the provided configuration.

        :param configuration: The service configuration
        :raises HTTPException: If the connection to the AAS registry could not be established
        """
        configuration = self._aas_registry_configuration
        logger.info("Create AAS registry client.")
        registry_wrapper = _connect_to_aas_server(configuration.server_configuration, configuration.secret_var_name)

        if registry_wrapper is None:
            logger.error("Failed to create AAS registry client.")
            raise HTTPException(
                status_code=StatusCode.AAS_REGISTRY_CONNECTION_ERROR.value, detail="Could not connect to AAS Registry. Client not created."
            )

        self.aas_registry_client = registry_wrapper.get_client()

    def _connect_to_sm_registry(self) -> AasHttpClient:
        """Create Submodel registry client using the provided configuration.

        :param configuration: The service configuration
        :raises HTTPException: If the connection to the AAS registry could not be established
        """
        configuration = self._sm_registry_configuration
        logger.info("Create Submodel registry client.")
        registry_wrapper = _connect_to_aas_server(configuration.server_configuration, configuration.secret_var_name)

        if registry_wrapper is None:
            logger.error("Failed to create Submodel registry client.")
            raise HTTPException(
                status_code=StatusCode.AAS_REGISTRY_CONNECTION_ERROR.value, detail="Could not connect to Submodel Registry. Client not created."
            )

        self.sm_registry_client = registry_wrapper.get_client()

    def _connect_to_repo_server(self):
        """Create AAS server wrappers for all configured AAS servers.

        :param configuration: The service configuration
        """
        configurations = self._repo_server_configurations
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
            logger.info(f"AAS server wrapper for base URL '{base_url}' found in cache.")
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
