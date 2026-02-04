"""Module defining the configuration model classes."""

import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class AasServerConfiguration(BaseModel):
    """Represents the AAS server configuration.

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
    aas_server_configurations: list[AasServerConfiguration] = Field(default=[], alias="AasServer", description="Configuration for the AAS server.")
    aas_registry_configuration: dict = Field(..., alias="AasRegistry", description="Configuration for the AAS registry.")
    asset_connector_configuration: dict = Field(..., alias="AssetConnector", description="Configuration for the asset connector.")


def load_configuration_file(config_file_path: str) -> ServiceConfiguration | None:
    """Load the runtime configuration from a JSON file."""
    if not config_file_path:
        logger.error("No configuration file provided.")
        return None

    config_file = Path(config_file_path)

    config_file = config_file.resolve()
    logger.info(f"Load configuration file '{config_file}'.")

    if not config_file.exists() or not config_file.is_file():
        logger.error(f"Configuration file '{config_file}' not found or inaccessible. ")
        return None

    config_string = config_file.read_text(encoding="utf-8")
    logger.debug(f"Configuration  file '{config_file}' found.")

    try:
        return ServiceConfiguration.model_validate_json(config_string)
    except ValidationError as ve:
        logger.error(f"Invalid BaSyx server connection file: {ve}")
        return None
