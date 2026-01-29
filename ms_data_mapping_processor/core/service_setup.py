"""Service setup module for initializing service states and connecting to AAS server."""

import logging
import os

from aas_http_client import SdkWrapper, create_wrapper_by_dict
from aas_standard_parser import aimc_parser
from aas_standard_parser.classes.aimc_parser_classes import MappingConfigurations
from basyx.aas import model
from fastapi import HTTPException

from ms_data_mapping_processor.core import aas_parser
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

    # connect to AAS server
    aas_wrapper: SdkWrapper = _connect_to_aas_server(configuration)

    # get the AAS from server
    shell: model.AssetAdministrationShell = _get_shell(aas_wrapper, configuration)

    # get the AIMC submodel from server
    aimc_submodel: model.Submodel = _get_aimc_submodel(aas_wrapper, shell)

    # parse the AIMC submodel to get mapping configurations
    mapping_configurations: MappingConfigurations = _get_mapping_configurations(aimc_submodel)

    # get the AID submodels from the AAS
    aid_submodels: list[model.Submodel] = _get_aid_submodels(aas_wrapper, mapping_configurations.aid_submodel_ids())

    # create process data
    process_data = ProcessData(id=shell.id, id_short=shell.id_short, display_name=shell.display_name)

    # create service states
    service_states = ServiceStates(process_data)
    service_states.service_configuration = configuration
    service_states.aas_wrapper = aas_wrapper
    return service_states


def _connect_to_aas_server(configuration: ServiceConfiguration) -> SdkWrapper | None:
    """Connect to the AAS server and create a server wrapper by a given configuration file.

    :param config_file: Path to the configuration file
    :raises HTTPException: If the server wrapper could not be created
    :return: The created server wrapper or None
    """
    logger.info("Connect to AAS server.")

    logger.info("Get AAS server password from environment variable 'RUNTIME_AAS_PW'.")
    password: str = os.getenv("RUNTIME_BASIC_AUTH_PW", "")
    o_auth_secret: str = os.getenv("RUNTIME_OAUTH_SECRET", "")
    token: str = os.getenv("RUNTIME_BEARER_TOKEN", "")

    try:
        wrapper: SdkWrapper | None = create_wrapper_by_dict(configuration.aas_server_configuration, password, o_auth_secret, token)
    except Exception as ve:
        logger.error(f"Could not create AAS server wrapper: {ve}")
        raise HTTPException(status_code=StatusCode.AAS_CONNECTION_ERROR.value, detail="Could not connect to AAS server. Client not created.") from ve

    if wrapper is None:
        logger.error("Could not connect to AAS server. Client not created.")
        raise HTTPException(status_code=StatusCode.AAS_CONNECTION_ERROR.value, detail="Could not connect to AAS server. Client not created.")
    return wrapper


def _get_shell(aas_wrapper: SdkWrapper, configuration: ServiceConfiguration) -> model.AssetAdministrationShell:
    """Get the AAS from the AAS server using Asset Administration Shell ID from configuration file.

    :param aas_wrapper: The SDK wrapper for the AAS server
    :raises HTTPException: If the AAS could not be found
    :return: The AAS
    """
    if configuration.aas_id is None:
        logger.error("No Asset Administration Shell ID provided in configuration file.")
        raise HTTPException(
            status_code=StatusCode.CONFIGURATION_ERROR.value, detail="No Asset Administration Shell ID provided in configuration file."
        )

    shell_id: str = configuration.aas_id

    logger.info(f"Get Asset Administration Shell with ID '{shell_id}' from server.")
    shell: model.AssetAdministrationShell = aas_wrapper.get_asset_administration_shell_by_id(shell_id)

    if shell is None:
        logger.error(f"Asset Administration Shell with ID '{shell_id}' not found on server.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value, detail=f"Asset Administration Shell with ID '{shell_id}' not found on server."
        )

    logger.debug(f"Asset Administration Shell with ID '{shell_id}' found on server.")
    return shell


def _get_aimc_submodel(wrapper: SdkWrapper, shell: model.AssetAdministrationShell) -> model.Submodel:
    """Get the Asset Interface Mapping Configuration (AIMC) submodel from the AAS.

    :param wrapper: The SDK wrapper for the AAS server
    :param shell: The AAS to get the submodel from
    :raises HTTPException: If the AIMC submodel could not be found
    :return: The AIMC submodel
    """
    logger.info("Get AIMC submodel from Shell.")
    submodels: list[model.Submodel] = aas_parser.get_submodels_by_semantic_id(wrapper, shell, "/idta/AssetInterfacesMappingConfiguration")

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
    logger.info("Parse mapping configurations from AIMC submodel.")
    mapping_configurations = aimc_parser.parse_mapping_configurations(aimc_submodel)

    if mapping_configurations is None or len(mapping_configurations) == 0:
        logger.error("No mapping configurations found in AIMC submodel.")
        raise HTTPException(
            status_code=StatusCode.MAPPING_PROCESSOR_ERROR.value,
            detail="No mapping configurations found in AIMC submodel.",
        )

    return mapping_configurations


def _get_aid_submodels(aas_wrapper: SdkWrapper, aid_submodel_ids: list[str]) -> list[model.Submodel]:
    """Get the Asset Interface Description (AID) submodel from the AAS.

    :param wrapper: The SDK wrapper for the AAS server
    :param aas: The AAS to get the submodel from
    :raises HTTPException: If the AID submodel could not be found
    :return: The AID submodel
    """
    logger.info("Get AID submodels from Shell.")
    submodels: list[model.Submodel] = aas_parser.get_submodels_by_id(aas_wrapper, aid_submodel_ids)

    if len(submodels) == 0:
        logger.error("No Submodels with semantic ID '/idta/AssetInterfacesDescription' not found on server.")
        raise HTTPException(
            status_code=StatusCode.AID_NOT_FOUND.value,
            detail="No Submodels with semantic ID '/idta/AssetInterfacesDescription' not found on server.",
        )

    return submodels
