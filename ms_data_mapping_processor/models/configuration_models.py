"""Module defining the configuration model classes."""

import logging
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

from ms_data_mapping_processor.models.constants import CONFIG_BASE_PATH, StatusCode

_logger = logging.getLogger(__name__)


class ServerConfiguration(BaseModel):
    """Represents the HTTP server configuration.

    :param BaseModel: Base model class for Pydantic
    """

    secret_var_name: str = Field(
        default="",
        alias="SecretVarName",
        description="The name of the environment variable that contains the AAS authentication secret.",
    )
    server_configuration: dict = Field(
        default={},
        alias="ServerConfiguration",
        description="The configuration parameters for connecting to the AAS server.",
    )


class ServiceConfiguration(BaseModel):
    """Represents the runtime configuration for the application.

    :param BaseModel: Base model class for Pydantic
    """

    aas_id: str = Field(..., alias="AasId", description="The ID of the AAS used by the microservice.")
    polling_interval: int = Field(
        default=5, alias="PollingInterval", description="Polling interval in seconds for retrieving values from the broker."
    )
    external_url: str = Field(
        default="http://127.0.0.1",
        alias="ExternalUrl",
        description="The external URL for the server.",
    )
    external_port: str = Field(
        default="3088",
        alias="ExternalPort",
        description="The external port for the server.",
    )


def load_configuration_file(config_file: Path) -> ServiceConfiguration | None:
    """Load the runtime configuration from a JSON file.

    :param config_file_path: Path to the configuration file
    :return: ServiceConfiguration object if successful, None otherwise
    """
    if config_file is None:
        _logger.error("No configuration file provided.")
        return None

    config_file = config_file.resolve()
    _logger.info(f"Load configuration file '{config_file}'.")

    if not config_file.exists() or not config_file.is_file():
        _logger.error(f"Configuration file '{config_file}' not found or inaccessible. ")
        return None

    config_string = config_file.read_text(encoding="utf-8")
    _logger.debug(f"Configuration  file '{config_file}' found.")

    try:
        return ServiceConfiguration.model_validate_json(config_string)
    except ValidationError as ve:
        _logger.error(f"Invalid BaSyx server connection file: {ve}")
        return None


class ServerConfigurationsHandler:
    """Handler for loading and managing server configurations."""

    aas_registry_configuration: ServerConfiguration
    sm_registry_configuration: ServerConfiguration
    repo_server_configurations: list[ServerConfiguration]
    asset_connector_configuration: ServerConfiguration

    def __init__(self):
        """Initialize ConfigHandler with default values."""
        self.repo_server_configurations = []
        self._get_config_files()

    def _get_config_files(self):
        config_base_path = Path(CONFIG_BASE_PATH)

        if not config_base_path.exists() or not config_base_path.is_dir():
            _logger.error(f"Configuration base path '{config_base_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"Configuration base path '{config_base_path}' not found.",
            )

        self._get_aas_registry_config()
        self._get_sm_registry_config()
        self._get_repos_configs()
        self._get_asset_connector_configs()

    def _get_aas_registry_config(self):
        config_path = Path(f"{CONFIG_BASE_PATH}/aas_registry")

        if not config_path.exists() or not config_path.is_dir():
            _logger.error(f"AAS registry configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"AAS registry configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            _logger.error(f"No AAS registry configuration files found in folder '{config_path}'.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"No AAS registry configuration files found in folder '{config_path}'.",
            )

        _logger.debug(f"Found {len(json_files)} AAS registry configuration files in folder '{config_path}'.")

        if len(json_files) > 1:
            _logger.warning(f"Multiple AAS registry configuration files found. Using the first one: '{json_files[0]}'.")

        try:
            self.aas_registry_configuration = ServerConfiguration.model_validate_json(json_files[0].read_text())
        except ValidationError as ve:
            _logger.error(f"Invalid Submodel registry connection file: {ve}")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail="Invalid Submodel registry connection file.",
            ) from ve

    def _get_sm_registry_config(self):
        config_path = Path(f"{CONFIG_BASE_PATH}/submodel_registry")

        if not config_path.exists() or not config_path.is_dir():
            _logger.error(f"Submodel registry configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"Submodel registry configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            _logger.error(f"No Submodel registry configuration files found in folder '{config_path}'.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"No Submodel registry configuration files found in folder '{config_path}'.",
            )

        _logger.debug(f"Found {len(json_files)} Submodel registry configuration files in folder '{config_path}'.")

        if len(json_files) > 1:
            _logger.warning(f"Multiple Submodel registry configuration files found. Using the first one: '{json_files[0]}'.")

        try:
            self.sm_registry_configuration = ServerConfiguration.model_validate_json(json_files[0].read_text())
        except ValidationError as ve:
            _logger.error(f"Invalid Submodel registry connection file: {ve}")
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
            _logger.error(f"AAS repository configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"AAS repository configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            _logger.info(f"No AAS repository configuration files found in folder '{config_path}'.")
            return

        try:
            for json_file in json_files:
                aas_server_configuration = ServerConfiguration.model_validate_json(json_file.read_text())
                self.repo_server_configurations.append(aas_server_configuration)
        except ValidationError as ve:
            _logger.error(f"Invalid AAS repository connection file '{json_file}': {ve}")

        _logger.debug(f"Found {len(self.repo_server_configurations)} AAS repository configuration files in folder '{config_path}'.")

    def _get_asset_connector_configs(self):
        config_path = Path(f"{CONFIG_BASE_PATH}/asset_connector")

        if not config_path.exists() or not config_path.is_dir():
            _logger.error(f"Asset Connector configuration path '{config_path}' not found or inaccessible.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"Asset Connector configuration path '{config_path}' not found.",
            )

        json_files = list(config_path.rglob("*.json"))

        if not json_files or len(json_files) == 0:
            _logger.error(f"No Asset Connector configuration files found in folder '{config_path}'.")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail=f"No Asset Connector configuration files found in folder '{config_path}'.",
            )

        _logger.debug(f"Found {len(json_files)} Asset Connector configuration files in folder '{config_path}'.")

        if len(json_files) > 1:
            _logger.warning(f"Multiple Asset Connector configuration files found. Using the first one: '{json_files[0]}'.")

        try:
            self.asset_connector_configuration = ServerConfiguration.model_validate_json(json_files[0].read_text())
        except ValidationError as ve:
            _logger.error(f"Invalid Asset Connector connection file: {ve}")
            raise HTTPException(
                status_code=StatusCode.CONFIGURATION_ERROR.value,
                detail="Invalid Asset Connector connection file.",
            ) from ve
