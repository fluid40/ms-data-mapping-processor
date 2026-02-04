"""Service setup module for initializing service states and connecting to AAS server."""

import json
import logging
import os

import basyx
import basyx.aas.adapter.json
from aas_http_client import AasHttpClient, SdkWrapper, create_wrapper_by_dict
from aas_standard_parser import aimc_parser
from aas_standard_parser.classes.aimc_parser_classes import MappingConfigurations
from basyx.aas import model
from fastapi import HTTPException

from ms_data_mapping_processor.core import aas_parser
from ms_data_mapping_processor.interfaces.asset_connector_interface import AssetConnectorClient, create_client
from ms_data_mapping_processor.models.configuration_models import ServiceConfiguration
from ms_data_mapping_processor.models.process_models import ProcessData, ServiceStates
from ms_data_mapping_processor.models.status_codes import StatusCode

logger = logging.getLogger(__name__)


def setup_service(configuration: ServiceConfiguration) -> ServiceStates:
    """Setup the service states with the given configuration.

    :param configuration: The service configuration to use.
    :return: An instance of ServiceStates with the provided configuration.
    """
    if configuration is None:
        logger.error("No configuration provided for service setup.")
        raise HTTPException(status_code=StatusCode.CONFIGURATION_ERROR.value, detail="No configuration provided for service setup.")

    # connect to AAS registry
    aas_registry_client: AasHttpClient = _create_aas_registry_client(configuration)

    # connect to all AAS server
    aas_server_wrapper_list: dict[str, SdkWrapper] = _create_aas_server_wrapper(configuration)

    # get the AAS from server
    shell: model.AssetAdministrationShell = _get_shell(aas_registry_client, aas_server_wrapper_list, configuration.aas_id)

    # get the AIMC submodel from server
    aimc_submodel: model.Submodel = _get_aimc_submodel(aas_server_wrapper_list, shell)

    # parse the AIMC submodel to get mapping configurations
    mapping_configurations: MappingConfigurations = _get_mapping_configurations(aimc_submodel)

    # get the AID submodels from the AAS
    aid_submodels: list[model.Submodel] = _get_aid_submodels(aas_server_wrapper_list, mapping_configurations.aid_submodel_ids)

    # connect to Asset Connector
    asset_connector_client = _connect_to_asset_connector(configuration)

    # configure Asset Connector with AID submodels
    _configure_asset_connector(asset_connector_client, aid_submodels)

    # create process data
    process_data = ProcessData(id=shell.id, id_short=shell.id_short, display_name=str(shell.display_name))

    # create service states
    service_states = ServiceStates(process_data)
    service_states.service_configuration = configuration
    service_states.aas_registry_client = aas_registry_client
    service_states.aas_server_wrapper_list = aas_server_wrapper_list
    service_states.asset_connector_client = asset_connector_client
    service_states.mapping_configurations = mapping_configurations

    return service_states


def _create_aas_registry_client(configuration: ServiceConfiguration) -> AasHttpClient:
    """Create AAS registry client using the provided configuration.

    :param configuration: The service configuration
    :raises HTTPException: If the connection to the AAS registry could not be established
    :return: The AAS registry client
    """
    logger.info("Create AAS registry wrapper.")
    registry_wrapper = _connect_to_aas_server(configuration.aas_registry_configuration, "AAS_REGISTRY_SECRET")

    if registry_wrapper is None:
        logger.error("Failed to create AAS registry client.")
        raise HTTPException(
            status_code=StatusCode.AAS_REGISTRY_CONNECTION_ERROR.value, detail="Could not connect to AAS Registry. Client not created."
        )

    return registry_wrapper.get_client()


def _create_aas_server_wrapper(configuration: ServiceConfiguration) -> dict[str, SdkWrapper]:
    """Create AAS server wrappers for all configured AAS servers.

    :param configuration: The service configuration
    :return: A dictionary of AAS server wrappers keyed by their base URL
    """
    logger.info(f"Create AAS server wrappers for {len(configuration.aas_server_configurations)} configured AAS servers.")
    aas_wrapper: dict[str, SdkWrapper] = {}

    for aas_server_configuration in configuration.aas_server_configurations:
        wrapper = _connect_to_aas_server(aas_server_configuration.server_configuration, aas_server_configuration.secret_var_name)

        if wrapper is not None and wrapper.base_url not in aas_wrapper:
            logger.info(f"AAS server wrapper for base URL '{wrapper.base_url}' created.")
            aas_wrapper[wrapper.base_url] = wrapper

    return aas_wrapper


def _connect_to_aas_server(server_configuration: dict, secret_var_name: str) -> SdkWrapper | None:
    """Connect to the AAS server and create a server wrapper by a given configuration file.

    :param server_configuration: The AAS server configuration
    :param secret_var_name: The name of the environment variable that contains the AAS authentication secret.
    :return: The created server wrapper or None
    """
    logger.info("Connect to AAS server.")

    logger.info(f"Get AAS server sec from environment variable '{secret_var_name}'.")
    server_secret: str = os.getenv(secret_var_name, "")

    try:
        wrapper: SdkWrapper | None = create_wrapper_by_dict(server_configuration, server_secret, server_secret, server_secret)
    except Exception as ve:
        logger.error(f"Could not create AAS server wrapper: {ve}")
        return None

    if wrapper is None:
        logger.error("Could not connect to AAS server. Client not created.")
        return None

    return wrapper


def _get_shell(aas_registry_client: AasHttpClient, aas_server_wrapper_list: dict[str, SdkWrapper], shell_id: str) -> model.AssetAdministrationShell:
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
    shell_desriptor: dict = AasHttpClient.shell_registry.get_submodel_descriptor_by_id_through_superpath(shell_id)

    shell = None

    if shell is None:
        logger.error(f"Asset Administration Shell with ID '{shell_id}' not found on server.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value, detail=f"Asset Administration Shell with ID '{shell_id}' not found on server."
        )

    logger.debug(f"Asset Administration Shell with ID '{shell_id}' found on server.")
    return shell


def _get_aimc_submodel(aas_server_wrapper: SdkWrapper, shell: model.AssetAdministrationShell) -> model.Submodel:
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
