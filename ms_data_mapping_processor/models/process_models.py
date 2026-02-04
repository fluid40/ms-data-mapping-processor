"""Module defining the process model classes."""

from aas_http_client import SdkWrapper
from aas_standard_parser.aimc_parser import MappingConfigurations
from basyx.aas import model

from ms_data_mapping_processor.core.server_handler import ServerHandler
from ms_data_mapping_processor.interfaces.asset_connector_interface import AssetConnectorClient
from ms_data_mapping_processor.models.configuration_models import ServiceConfiguration


class ProcessData:
    """Class representing process data for a model."""

    def __init__(self, id: str, id_short: str, display_name: str):
        """Initialize ProcessData with given parameters.

        :param id: The unique identifier of the shell.
        :param id_short: The short identifier of the shell.
        :param display_name: The display name of the shell.
        """
        self.id = id
        self.id_short = id_short
        self.display_name = display_name


class ServiceStates:
    """Class representing the service states."""

    process_data: ProcessData | None
    service_configuration: ServiceConfiguration | None
    asset_connector_client: AssetConnectorClient | None
    aas_registry_client: SdkWrapper | None
    server_handler: ServerHandler | None
    aas_server_wrapper_list: dict[str, SdkWrapper] | None
    dynamic_submodel_cache: dict[str, model.Submodel] | None
    mapping_configurations: MappingConfigurations | None

    def __init__(self, process_data: ProcessData):
        """Initialize ServiceStates with default values."""
        self.process_data: ProcessData = process_data
        self.service_configuration: ServiceConfiguration = None
        self.asset_connector_client: AssetConnectorClient = None
        self.aas_server_wrapper_list: dict[str, SdkWrapper] = None
        self.dynamic_submodel_cache: dict[str, model.Submodel] = {}
        self.mapping_configurations: MappingConfigurations = None
        self.server_handler: ServerHandler = None


class AasServerWrapper:
    """Class representing an AAS server wrapper with its base URL."""

    def __init__(self, base_url: str, wrapper: SdkWrapper):
        """Initialize AasServerWrapper with given parameters.

        :param base_url: The base URL of the AAS server.
        :param wrapper: The SDK wrapper for the AAS server.
        """
        self.base_url = base_url
        self.wrapper = wrapper
