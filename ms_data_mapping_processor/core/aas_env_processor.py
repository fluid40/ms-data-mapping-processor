import logging

from aas_standard_parser import descriptor_json_helper
from basyx.aas import model
from fastapi import HTTPException

from ms_data_mapping_processor.core.server_handler import ServerHandler
from ms_data_mapping_processor.models.constants import StatusCode

logger = logging.getLogger(__name__)


def get_shell(server_handler: ServerHandler, shell_id: str) -> model.AssetAdministrationShell:
    """Get a Asset Administration Shell from a AAS server environment.

    :param server_handler: Server handler
    :param shell_id: ID of the Asset Administration Shell to get
    :raises HTTPException: If no Asset Administration Shell ID is provided in the configuration file.
    :raises HTTPException: If the Asset Administration Shell descriptor with the provided ID could not be found in the AAS registry.
    :raises HTTPException: If a repository wrapper for the AAS server could not be created.
    :raises HTTPException: If the Asset Administration Shell with the provided ID could not be found on the AAS server.
    :return: Asset Administration Shell with the provided ID from the AAS server
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

    shell_href = _get_endpoint_href(shell_descriptor, 0)
    shell_href_data = descriptor_json_helper.parse_endpoint_href(shell_href)

    shell_repo_wrapper = server_handler.get_or_create_repo_wrapper(shell_href_data.base_url)

    if shell_repo_wrapper is None:
        logger.error(f"Could not create repository wrapper for base URL '{shell_href_data.base_url}'.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value,
            detail=f"Could not connect to Repository server at '{shell_href_data.base_url}'. Repository wrapper not created.",
        )

    shell: model.AssetAdministrationShell = shell_repo_wrapper.get_asset_administration_shell_by_id(shell_id)

    if shell is None:
        logger.error(f"Asset Administration Shell with ID '{shell_id}' not found on server.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value, detail=f"Asset Administration Shell with ID '{shell_id}' not found on server."
        )

    shell_name = shell.display_name if shell.display_name else shell.id_short
    logger.info(f"Asset Administration Shell '{shell_name}' with ID '{shell_id}' found on server.")
    return shell


def get_submodel(server_handler: ServerHandler, submodel_id: str) -> model.Submodel:
    """Get a Submodel from a AAS server environment.

    :param server_handler: Server handler
    :param submodel_id: ID of the Submodel to get
    :raises HTTPException: If no Submodel ID is provided in the configuration file.
    :raises HTTPException: If the Submodel descriptor with the provided ID could not be found in the AAS registry.
    :raises HTTPException: If a repository wrapper for the AAS server could not be created.
    :raises HTTPException: If the Submodel with the provided ID could not be found on the AAS server.
    :return: Submodel with the provided ID from the AAS server
    """
    if submodel_id is None:
        logger.error("No Submodel ID provided in configuration file.")
        raise HTTPException(status_code=StatusCode.CONFIGURATION_ERROR.value, detail="No Submodel ID provided in configuration file.")

    logger.info(f"Get Submodel with ID '{submodel_id}' from server.")
    submodel_descriptor: dict = server_handler.sm_registry_client.submodel_registry.get_submodel_descriptor_by_id(submodel_id)

    if submodel_descriptor is None:
        logger.error(f"Submodel descriptor with ID '{submodel_id}' not found in AAS registry.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value,
            detail=f"Submodel descriptor with ID '{submodel_id}' not found in AAS registry.",
        )

    submodel_href = _get_endpoint_href(submodel_descriptor, 0)
    submodel_href_data = descriptor_json_helper.parse_endpoint_href(submodel_href)

    submodel_repo_wrapper = server_handler.get_or_create_repo_wrapper(submodel_href_data.base_url)

    if submodel_repo_wrapper is None:
        logger.error(f"Could not create repository wrapper for base URL '{submodel_href_data.base_url}'.")
        raise HTTPException(
            status_code=StatusCode.SHELL_NOT_FOUND.value,
            detail=f"Could not connect to Repository server at '{submodel_href_data.base_url}'. Repository wrapper not created.",
        )

    submodel: model.Submodel = submodel_repo_wrapper.get_submodel_by_id(submodel_id)

    if submodel is None:
        logger.error(f"Submodel with ID '{submodel_id}' not found on server.")
        raise HTTPException(status_code=StatusCode.SHELL_NOT_FOUND.value, detail=f"Submodel with ID '{submodel_id}' not found on server.")

    logger.debug(f"Submodel with ID '{submodel_id}' found on server.")
    return submodel


def _get_endpoint_href(descriptor_data: dict, endpoint_index: int = 0) -> str | None:
    """Get the href from a descriptor's endpoints.

    :param descriptor_data: The descriptor data containing endpoints.
    :param endpoint_index: The index of the endpoint to extract the href from.
    :return: The href string if found, otherwise None.
    """
    endpoints = _get_endpoint_hrefs(descriptor_data)

    if not endpoints or len(endpoints) == 0:
        logger.warning(f"No endpoints found in descriptor {descriptor_data}")
        return None

    if endpoint_index >= len(endpoints):
        logger.warning(f"Endpoint index {endpoint_index} out of range for descriptor {descriptor_data}")
        return None

    return endpoints[endpoint_index]


def _get_endpoint_hrefs(descriptor_data: dict) -> list[str]:
    """Get all hrefs from a descriptor's endpoints.

    :param descriptor_data: The descriptor data containing endpoints.
    :return: A list of href strings extracted from the endpoints.
    """
    return [endpoint.get("protocolInformation", {}).get("href", "") for endpoint in descriptor_data.get("endpoints", [])]
