"""Service setup module for initializing service states and connecting to AAS server."""

import json
import logging
import os

import basyx
import basyx.aas.adapter.json
from aas_http_client import AasHttpClient, SdkWrapper, create_wrapper_by_dict
from aas_standard_parser import aimc_parser, descriptor_json_helper
from aas_standard_parser.classes.aimc_parser_classes import MappingConfigurations
from basyx.aas import model
from fastapi import HTTPException

from ms_data_mapping_processor.core import aas_parser
from ms_data_mapping_processor.core.server_handler import ServerHandler
from ms_data_mapping_processor.interfaces.asset_connector_interface import AssetConnectorClient, create_client
from ms_data_mapping_processor.models.configuration_models import ServiceConfiguration
from ms_data_mapping_processor.models.constants import StatusCode
from ms_data_mapping_processor.models.process_models import ProcessData, ServiceStates

logger = logging.getLogger(__name__)


def setup_service(configuration: ServiceConfiguration) -> ServiceStates:
    """Setup the service states with the given configuration.

    :param configuration: The service configuration to use.
    :return: An instance of ServiceStates with the provided configuration.
    """
    if configuration is None:
        logger.error("No configuration provided for service setup.")
        raise HTTPException(status_code=StatusCode.CONFIGURATION_ERROR.value, detail="No configuration provided for service setup.")

    server_handler = ServerHandler()
    server_handler.connect_to_server()

    # get the AAS from server
    shell: model.AssetAdministrationShell = _get_shell(server_handler, configuration.aas_id)

    # get the AIMC submodel from server
    aimc_submodel: model.Submodel = _get_aimc_submodel(server_handler, shell)

    # parse the AIMC submodel to get mapping configurations
    mapping_configurations: MappingConfigurations = _get_mapping_configurations(aimc_submodel)

    # get the AID submodels from the AAS
    aid_submodels: list[model.Submodel] = _get_aid_submodels(server_handler, mapping_configurations.aid_submodel_ids)

    # connect to Asset Connector
    asset_connector_client = _connect_to_asset_connector(configuration)

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


def _get_shell(server_handler: ServerHandler, shell_id: str) -> model.AssetAdministrationShell:
    """Get the AAS from the AAS server using Asset Administration Shell ID from configuration file.

    :raises HTTPException: If the AAS could not be found
    :return: The AAS
    """
    if shell_id is None:
        logger.error("No Asset Administration Shell ID provided in configuration file.")
        raise HTTPException(
            status_code=StatusCode.CONFIGURATION_ERROR.value, detail="No Asset Administration Shell ID provided in configuration file."
        )

    logger.info(f"Get Asset Administration Shell with ID '{shell_id}' from server.")
    shell_descriptor: dict = server_handler.aas_registry_client.shell_registry.get_asset_administration_shell_descriptor_by_id(shell_id)

    if shell_descriptor is None:
        logger.error(f"Asset Administration Shell descriptor with ID '{shell_id}' not found in AAS registry.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value,
            detail=f"Asset Administration Shell descriptor with ID '{shell_id}' not found in AAS registry.",
        )

    shell_href = get_endpoint_href(shell_descriptor, 0)
    shell_href_data = descriptor_json_helper.parse_endpoint_href(shell_href)

    shell_repo_wrapper = server_handler.get_or_create_repo_wrapper(shell_href_data.base_url)

    shell: model.AssetAdministrationShell = shell_repo_wrapper.get_asset_administration_shell_by_id(shell_id)

    if shell is None:
        logger.error(f"Asset Administration Shell with ID '{shell_id}' not found on server.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value, detail=f"Asset Administration Shell with ID '{shell_id}' not found on server."
        )

    logger.debug(f"Asset Administration Shell with ID '{shell_id}' found on server.")
    return shell


def _get_aimc_submodel(server_handler: ServerHandler, shell: model.AssetAdministrationShell) -> model.Submodel:
    """Get the Asset Interface Mapping Configuration (AIMC) submodel from the AAS.

    :param aas_server_wrapper: The SDK wrapper for the AAS server
    :param shell: The AAS to get the submodel from
    :raises HTTPException: If the AIMC submodel could not be found
    :return: The AIMC submodel
    """
    logger.info("Get AIMC submodel from Shell.")
    submodels: list[model.Submodel] = aas_parser.get_submodels_by_semantic_id(aas_server_wrapper, shell, "/idta/AssetInterfacesMappingConfiguration")

    if len(submodels) == 0:
        logger.error("Submodel with semantic ID '/idta/AssetInterfacesMappingConfiguration' not found on server.")
        raise HTTPException(
            status_code=StatusCode.AIMC_NOT_FOUND.value,
            detail="Submodel with semantic ID '/idta/AssetInterfacesMappingConfiguration' not found on server.",
        )

    return submodels[0]


def _get_mapping_configurations(aimc_submodel: model.Submodel) -> MappingConfigurations:
    """Get the mapping configurations from the AIMC submodel.

    :param aimc_submodel: The AIMC submodel
    :return: The mapping configurations
    """
    mapping_configurations = aimc_parser.parse_mapping_configurations(aimc_submodel)

    if mapping_configurations is None or len(mapping_configurations.configurations) == 0:
        logger.error("No mapping configurations found in AIMC submodel.")
        raise HTTPException(
            status_code=StatusCode.MAPPING_PROCESSOR_ERROR.value,
            detail="No mapping configurations found in AIMC submodel.",
        )

    return mapping_configurations


def _get_aid_submodels(aas_server_wrapper: SdkWrapper, aid_submodel_ids: list[str]) -> list[model.Submodel]:
    """Get the Asset Interface Description (AID) submodel from the AAS.

    :param aas_server_wrapper: The SDK wrapper for the AAS server
    :param aas: The AAS to get the submodel from
    :raises HTTPException: If the AID submodel could not be found
    :return: The AID submodel
    """
    logger.info("Get AID submodels from Shell.")
    submodels: list[model.Submodel] = aas_parser.get_submodels_by_id(aas_server_wrapper, aid_submodel_ids)

    if len(submodels) == 0:
        logger.error("No Submodels with semantic ID '/idta/AssetInterfacesDescription' not found on server.")
        raise HTTPException(
            status_code=StatusCode.AID_NOT_FOUND.value,
            detail="No Submodels with semantic ID '/idta/AssetInterfacesDescription' not found on server.",
        )

    return submodels


def _connect_to_asset_connector(configuration: ServiceConfiguration) -> AssetConnectorClient:
    """Connect to the Asset Connector using the provided configuration.

    :param configuration: The service configuration
    :raises HTTPException: If the connection to the Asset Connector could not be established
    :return: The Asset Connector client
    """
    logger.info("Connect to Asset connector.")

    try:
        client = create_client(configuration.asset_connector_configuration)
    except Exception as ve:
        logger.error(f"Could not create Asset Connector client: {ve}")
        raise HTTPException(
            status_code=StatusCode.ASSET_CONNECTOR_CONNECTION_ERROR.value, detail="Could not connect to Asset Connector. Client not created."
        ) from ve

    if client is None:
        logger.error("Could not connect to Asset Connector. Client not created.")
        raise HTTPException(
            status_code=StatusCode.ASSET_CONNECTOR_CONNECTION_ERROR.value, detail="Could not connect to Asset Connector. Client not created."
        )

    return client


def _configure_asset_connector(asset_connector_client: AssetConnectorClient, aid_submodels: list[model.Submodel]):
    """Configure the Asset Connector with the provided AID submodels.

    :param client: The Asset Connector client
    :param aid_submodels: The list of AID submodels
    """
    logger.info(f"Add {len(aid_submodels)} AID submodel configurations to Asset Connector.")
    for aid_submodel in aid_submodels:
        data_string = json.dumps(aid_submodel, cls=basyx.aas.adapter.json.AASToJsonEncoder)
        mqtt_config = {"Aid": json.loads(data_string)}

        logger.info(f"Add AID submodel '{aid_submodel.id_short}' configuration to Asset Connector.")

        result = asset_connector_client.add_config(mqtt_config)

        if result is None or result.get_success() is False:
            logger.error(f"Could not add AID submodel '{aid_submodel.id_short}' configuration to Asset Connector.")
            raise HTTPException(
                status_code=StatusCode.AID_CONFIGURATION_ERROR.value,
                detail=f"Could not add AID submodel '{aid_submodel.id_short}' configuration to Asset Connector.",
            )


def get_endpoint_href(descriptor_data: dict, endpoint_index: int = 0) -> str | None:
    """Get the href from a descriptor's endpoints.

    :param descriptor_data: The descriptor data containing endpoints.
    :param endpoint_index: The index of the endpoint to extract the href from.
    :return: The href string if found, otherwise None.
    """
    endpoints = get_endpoint_hrefs(descriptor_data)

    if not endpoints or len(endpoints) == 0:
        logger.warning(f"No endpoints found in descriptor {descriptor_data}")
        return None

    if endpoint_index >= len(endpoints):
        logger.warning(f"Endpoint index {endpoint_index} out of range for descriptor {descriptor_data}")
        return None

    return endpoints[endpoint_index]


def get_endpoint_hrefs(descriptor_data: dict) -> list[str]:
    """Get all hrefs from a descriptor's endpoints.

    :param descriptor_data: The descriptor data containing endpoints.
    :return: A list of href strings extracted from the endpoints.
    """
    return [endpoint.get("protocolInformation", {}).get("href", "") for endpoint in descriptor_data.get("endpoints", [])]
