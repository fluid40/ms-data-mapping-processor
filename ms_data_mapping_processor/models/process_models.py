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


class DescriptorMapping:
    """Class representing a mapping between master and slave descriptors."""

    def __init__(self, master_descriptor: dict, slave_descriptor: dict, submodel_id: str):
        """Initialize DescriptorMapping with given parameters.

        :param master_descriptor: The master descriptor.
        :param slave_descriptor: The slave descriptor.
        :param submodel_id: The unique identifier for the asset.
        """
        self.master_descriptor = master_descriptor
        self.slave_descriptor = slave_descriptor
        self.submodel_id = submodel_id


class ServiceStates:
    """Class representing the service states."""

    process_data: ProcessData
    service_configuration: ServiceConfiguration
    asset_connector_client: AssetConnectorClient
    server_handler: ServerHandler
    dynamic_submodel_cache: dict[str, model.Submodel]
    mapping_configurations: MappingConfigurations
    descriptor_mapping: list[DescriptorMapping]

    def __init__(self, process_data: ProcessData):
        """Initialize ServiceStates with default values."""
        self.process_data: ProcessData = process_data
        self.dynamic_submodel_cache: dict[str, model.Submodel] = {}
        self.descriptor_mapping: list[DescriptorMapping] = []


class AasServerWrapper:
    """Class representing an AAS server wrapper with its base URL."""

    def __init__(self, base_url: str, wrapper: SdkWrapper):
        """Initialize AasServerWrapper with given parameters.

        :param base_url: The base URL of the AAS server.
        :param wrapper: The SDK wrapper for the AAS server.
        """
        self.base_url = base_url
        self.wrapper = wrapper
