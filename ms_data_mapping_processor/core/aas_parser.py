import logging

from aas_http_client import SdkWrapper, sdk_tools
from aas_standard_parser import submodel_json_parser
from basyx.aas import model

logger = logging.getLogger(__name__)


def get_submodels_by_id(wrapper: SdkWrapper, submodel_ids: list[str]) -> list[model.Submodel]:
    """Get all submodels from the AAS.

    :param wrapper: The SDK wrapper for the AAS server
    :param aas: The AAS to get the submodels from
    :return: A list of all submodels in the AAS
    """
    submodels: list[model.Submodel] = []

    logger.info(f"Get {len(submodel_ids)} submodels by IDs from server.")

    for sm_id in submodel_ids:
        logger.debug(f"Get submodel with ID '{sm_id}'.")
        sm = wrapper.get_submodel_by_id(sm_id)

        if sm is None:
            logger.error(f"Submodel with ID '{sm_id}' not found on server.")
            continue

        submodels.append(sm)

    if len(submodels) == 0:
        logger.warning("No submodels found on server.")

    logger.debug(f"Found {len(submodels)} submodels on server.")

    return submodels


def get_aid_submodels(wrapper: SdkWrapper, aas: model.AssetAdministrationShell) -> list[model.Submodel]:
    """Get the Asset Interface Description (AID) submodel from the AAS.

    :param wrapper: The SDK wrapper for the AAS server
    :param aas: The AAS to get the submodel from
    :raises HTTPException: If the AID submodel could not be found
    :return: The AID submodel
    """
    submodels: list[model.Submodel] = get_submodels_by_semantic_id(wrapper, aas, "/idta/AssetInterfacesDescription")

    if len(submodels) == 0:
        logger.error("Submodel with semantic ID '/idta/AssetInterfacesDescription' not found on server.")

    return submodels


def get_aimc_submodel(wrapper: SdkWrapper, aas: model.AssetAdministrationShell) -> model.Submodel | None:
    """Get the Asset Interface Mapping Configuration (AIMC) submodel from the AAS.

    :param wrapper: The SDK wrapper for the AAS server
    :param aas: The AAS to get the submodel from
    :raises HTTPException: If the AIMC submodel could not be found
    :return: The AIMC submodel
    """
    submodels: list[model.Submodel] = get_submodels_by_semantic_id(wrapper, aas, "/idta/AssetInterfacesMappingConfiguration")

    if len(submodels) == 0:
        logger.error("Submodel with semantic ID '/idta/AssetInterfacesMappingConfiguration' not found on server.")
        return None

    return submodels[0]


def get_submodels_by_semantic_id(wrapper: SdkWrapper, aas: model.AssetAdministrationShell, semantic_id: str) -> list[model.Submodel]:
    """Get submodels from the AAS by semantic ID.

    :param wrapper: The SDK wrapper for the AAS server
    :param aas: The AAS to get the submodels from
    :param semantic_id: The semantic ID to search for
    :return: A list of submodels matching the semantic ID
    """
    submodels: list[model.Submodel] = []

    logger.debug(f"Get submodels with semantic ID '{semantic_id}' from server.")
    for ref in aas.submodel:
        # extract the submodel ID from the reference
        sm_id = ref.key[0].value
        logger.debug(f"Get submodel with ID '{sm_id}'")

        client = wrapper.get_client()

        # get the submodel data as dictionary from the server
        sm_data = client.submodels.get_submodel_by_id(sm_id)

        if sm_data is None:
            logger.error(f"Submodel with ID '{sm_id}' not found on server.")
            continue

        # extract the semantic ID from the submodel data
        sm_semantic_id = submodel_json_parser.get_value_from_semantic_id_by_index(sm_data)

        # check if the semantic ID matches. If not, continue to the next submodel
        if not sm_semantic_id or semantic_id not in sm_semantic_id:
            continue

        # convert the submodel data to a Submodel object
        sm: model.Submodel = sdk_tools.convert_to_object(sm_data)

        if sm is None:
            logger.error(f"Could not convert submodel data to Submodel object for submodel ID '{sm_id}'")
            continue

        logger.debug(f"Found submodel '{sm.id_short}' with semantic ID '{semantic_id}'")
        submodels.append(sm)

    if len(submodels) == 0:
        logger.error(f" No submodels with semantic ID '{semantic_id}' not found on server.")

    logger.debug(f"Found {len(submodels)} submodels with semantic ID '{semantic_id}' on server.")

    return submodels
