"""Service setup module for initializing service states and connecting to AAS server."""

import json
import logging

import basyx
import basyx.aas.adapter.json
from aas_standard_parser import aas_parser, aimc_parser, submodel_parser
from aas_standard_parser.classes.aimc_parser_classes import MappingConfigurations
from basyx.aas import model
from fastapi import HTTPException

from ms_data_mapping_processor.core.aas_env_processor import get_shell, get_submodel
from ms_data_mapping_processor.core.server_handler import ServerHandler
from ms_data_mapping_processor.interfaces.asset_connector_interface import AssetConnectorClient, create_client
from ms_data_mapping_processor.models.configuration_models import ServerConfiguration, ServerConfigurationsHandler, ServiceConfiguration
from ms_data_mapping_processor.models.constants import StatusCode
from ms_data_mapping_processor.models.process_models import ProcessData, ServiceStates

_logger = logging.getLogger(__name__)


def setup_service(configuration: ServiceConfiguration) -> ServiceStates:
    """Setup the service states with the given configuration.

    :param configuration: The service configuration to use.
    :return: An instance of ServiceStates with the provided configuration.
    """
    if configuration is None:
        _logger.error("No configuration provided for service setup.")
        raise HTTPException(status_code=StatusCode.CONFIGURATION_ERROR.value, detail="No configuration provided for service setup.")

    server_configurations = ServerConfigurationsHandler()

    server_handler = ServerHandler()
    server_handler.connect_to_server(server_configurations)

    # get the AAS from server
    shell: model.AssetAdministrationShell = get_shell(server_handler, configuration.aas_id)

    # get the AIMC submodel from server
    aimc_submodel: model.Submodel = _get_aimc_submodel(server_handler, shell)

    # parse the AIMC submodel to get mapping configurations
    mapping_configurations: MappingConfigurations = _get_mapping_configurations(aimc_submodel)

    # get the AID submodels from the AAS
    aid_submodels: list[model.Submodel] = _get_aid_submodels(server_handler, mapping_configurations.aid_submodel_ids)

    # connect to Asset Connector
    asset_connector_client = _connect_to_asset_connector(server_configurations.asset_connector_configuration)

    # configure Asset Connector with AID submodels
    _configure_asset_connector(asset_connector_client, aid_submodels)

    # create process data
    process_data = ProcessData(id=shell.id, id_short=shell.id_short, display_name=str(shell.display_name))

    # create service states
    service_states = ServiceStates(process_data)
    service_states.service_configuration = configuration
    service_states.server_handler = server_handler
    service_states.asset_connector_client = asset_connector_client
    service_states.mapping_configurations = mapping_configurations

    return service_states


def _get_aimc_submodel(server_handler: ServerHandler, shell: model.AssetAdministrationShell) -> model.Submodel:
    """Get the Asset Interface Mapping Configuration (AIMC) submodel from the AAS.

    :param aas_server_wrapper: The SDK wrapper for the AAS server
    :param shell: The AAS to get the submodel from
    :raises HTTPException: If the AIMC submodel could not be found
    :return: The AIMC submodel
    """
    _logger.info("Get AIMC submodel from Shell.")
    submodel_ids = aas_parser.get_submodel_ids(shell)

    for submodel_id in submodel_ids:
        submodel = get_submodel(server_handler, submodel_id)

        semantic_id_value = submodel_parser.get_semantic_id_value(submodel)

        if semantic_id_value and "/idta/AssetInterfacesMappingConfiguration" in semantic_id_value:
            _logger.info(f"AIMC submodel with ID '{submodel_id}' found on server.")
            return submodel

    _logger.error("No Submodel with semantic ID '/idta/AssetInterfacesMappingConfiguration' not found on server.")
    raise HTTPException(
        status_code=StatusCode.AIMC_NOT_FOUND.value,
        detail="No Submodel with semantic ID '/idta/AssetInterfacesMappingConfiguration' not found on server.",
    )


def _get_mapping_configurations(aimc_submodel: model.Submodel) -> MappingConfigurations:
    """Get the mapping configurations from the AIMC submodel.

    :param aimc_submodel: The AIMC submodel
    :return: The mapping configurations
    """
    mapping_configurations = aimc_parser.parse_mapping_configurations(aimc_submodel)

    if mapping_configurations is None or len(mapping_configurations.configurations) == 0:
        _logger.error("No mapping configurations found in AIMC submodel.")
        raise HTTPException(
            status_code=StatusCode.MAPPING_PROCESSOR_ERROR.value,
            detail="No mapping configurations found in AIMC submodel.",
        )

    return mapping_configurations


def _get_aid_submodels(server_handler: ServerHandler, aid_submodel_ids: list[str]) -> list[model.Submodel]:
    _logger.info("Get AID submodels from Shell.")
    submodels: list[model.Submodel] = []
    for submodel_id in aid_submodel_ids:
        _logger.debug(f"Get submodel with ID '{submodel_id}' from server.")
        submodel = get_submodel(server_handler, submodel_id)

        semantic_id_value = submodel_parser.get_semantic_id_value(submodel)

        if semantic_id_value and "/idta/AssetInterfacesDescription" in semantic_id_value:
            _logger.info(f"AID submodel with ID '{submodel_id}' found on server.")
            submodels.append(submodel)

    if len(submodels) == 0:
        _logger.error("No Submodels with semantic ID '/idta/AssetInterfacesDescription' not found on server.")
        raise HTTPException(
            status_code=StatusCode.AID_NOT_FOUND.value,
            detail="No Submodels with semantic ID '/idta/AssetInterfacesDescription' not found on server.",
        )

    return submodels


def _connect_to_asset_connector(configuration: ServerConfiguration) -> AssetConnectorClient:
    """Connect to the Asset Connector using the provided configuration.

    :param configuration: The service configuration
    :raises HTTPException: If the connection to the Asset Connector could not be established
    :return: The Asset Connector client
    """
    _logger.info("Connect to Asset connector.")
    try:
        client = create_client(configuration.server_configuration)
    except Exception as ve:
        _logger.error(f"Could not create Asset Connector client: {ve}")
        raise HTTPException(
            status_code=StatusCode.ASSET_CONNECTOR_CONNECTION_ERROR.value, detail="Could not connect to Asset Connector. Client not created."
        ) from ve

    if client is None:
        _logger.error("Could not connect to Asset Connector. Client not created.")
        raise HTTPException(
            status_code=StatusCode.ASSET_CONNECTOR_CONNECTION_ERROR.value, detail="Could not connect to Asset Connector. Client not created."
        )

    return client


def _configure_asset_connector(asset_connector_client: AssetConnectorClient, aid_submodels: list[model.Submodel]):
    """Configure the Asset Connector with the provided AID submodels.

    :param client: The Asset Connector client
    :param aid_submodels: The list of AID submodels
    """
    _logger.info(f"Add {len(aid_submodels)} AID submodel configurations to Asset Connector.")
    for aid_submodel in aid_submodels:
        data_string = json.dumps(aid_submodel, cls=basyx.aas.adapter.json.AASToJsonEncoder)
        mqtt_config = {"Aid": json.loads(data_string)}

        _logger.info(f"Add AID submodel '{aid_submodel.id_short}' configuration to Asset Connector.")

        result = asset_connector_client.add_config(mqtt_config)

        if result is None or result.get_success() is False:
            _logger.error(f"Could not add AID submodel '{aid_submodel.id_short}' configuration to Asset Connector.")
            raise HTTPException(
                status_code=StatusCode.AID_CONFIGURATION_ERROR.value,
                detail=f"Could not add AID submodel '{aid_submodel.id_short}' configuration to Asset Connector.",
            )
