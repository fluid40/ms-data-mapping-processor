import logging

from aas_http_client import encoder, sdk_tools
from aas_standard_parser import submodel_parser
from basyx.aas import model
from fastapi import APIRouter, HTTPException, Request

from ms_data_mapping_processor.models.process_models import ServiceStates

router = APIRouter()
_logger = logging.getLogger(__name__)


# GET /submodels/{submodelIdentifier}
@router.get(
    "/submodels/{submodelIdentifier}",
    tags=["submodels"],
    response_model=dict,
    responses={
        "200": {"model": dict},
        "404": {"description": "Submodel not found"},
        "500": {"description": "Server error"},
    },
    name="getSubmodel",
    description="Get a specific submodel by its identifier",
    summary="Get a submodel",
)
async def get_submodel(request: Request, submodelIdentifier: str):
    """Returns a specific Submodel."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        sm_id = encoder.decode_base_64(submodelIdentifier)

        if sm_id not in service_states.dynamic_submodel_cache:
            raise HTTPException(status_code=404, detail=f"Submodel with id '{sm_id}' not found.")

        sm = service_states.dynamic_submodel_cache[sm_id]
        return sdk_tools.convert_to_dict(sm)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


# GET /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}
@router.get(
    "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}",
    tags=["submodels"],
    response_model=dict,
    responses={
        "200": {"model": dict},
        "404": {"description": "Submodel not found"},
        "500": {"description": "Server error"},
    },
    name="GetSubmodelElementByPath_SubmodelRepo",
    description="Returns a specific submodel element from the Submodel at a specified path",
    summary="Returns a specific submodel element from the Submodel at a specified path",
)
async def get_submodel_element_by_path_submodel_repo(request: Request, submodelIdentifier: str, idShortPath: str):
    """Returns a specific submodel element from the Submodel at a specified path."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        sm_id = encoder.decode_base_64(submodelIdentifier)

        if sm_id not in service_states.dynamic_submodel_cache:
            raise HTTPException(status_code=404, detail=f"Submodel with id '{sm_id}' not found.")

        sm = service_states.dynamic_submodel_cache[sm_id]
        sme = submodel_parser.get_submodel_element_by_id_short_path(sm, idShortPath)

        if sme is None:
            raise HTTPException(status_code=404, detail=f"SubmodelElement with path '{idShortPath}' not found in Submodel '{sm_id}'.")

        return sdk_tools.convert_to_dict(sme)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


# GET /submodels
@router.get(
    "/submodels",
    tags=["submodels"],
    response_model=dict,
    responses={
        "200": {"model": dict},
        "404": {"description": "Submodel not found"},
        "500": {"description": "Server error"},
    },
    name="GetAllSubmodels",
    description="Returns all Submodels",
    summary="Returns all Submodels",
)
async def get_all_submodels(request: Request):
    """Returns all Submodels."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        submodels = [sdk_tools.convert_to_dict(sm) for sm in service_states.dynamic_submodel_cache.values()]
        return {"paging_metadata": {}, "results": submodels}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


# GET /submodels/{submodelIdentifier}/submodel-elements
@router.get(
    "/submodels/{submodelIdentifier}/submodel-elements",
    tags=["submodels"],
    response_model=dict,
    responses={
        "200": {"model": dict},
        "404": {"description": "Submodel not found"},
        "500": {"description": "Server error"},
    },
    name="GetAllSubmodelElements_SubmodelRepository",
    description="Returns all submodel elements including their hierarchy",
    summary="Returns all submodel elements including their hierarchy",
)
async def get_all_submodel_elements_submodel_repository(request: Request, submodelIdentifier: str):
    """Returns a specific submodel element from the Submodel at a specified path."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        sm_id = encoder.decode_base_64(submodelIdentifier)

        if sm_id not in service_states.dynamic_submodel_cache:
            raise HTTPException(status_code=404, detail=f"Submodel with id '{sm_id}' not found.")

        sm = service_states.dynamic_submodel_cache[sm_id]
        sme = [sdk_tools.convert_to_dict(se) for se in sm.submodel_element]
        return {"paging_metadata": {}, "results": sme}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


# GET /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value
@router.get(
    "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value",
    tags=["submodels"],
    response_model=dict | str | list,
    responses={
        "200": {"model": dict | str | list},
        "404": {"description": "Submodel or submodel element not found"},
        "500": {"description": "Server error"},
    },
    name="GetSubmodelElementByPath-ValueOnly_SubmodelRepo",
    description="Returns the value of a specific submodel element from the Submodel at a specified path",
    summary="Returns the value of a specific submodel element from the Submodel at a specified path",
)
async def get_submodel_element_by_path_value_only_submodel_repo(request: Request, submodelIdentifier: str, idShortPath: str):
    """Returns a specific submodel element from the Submodel at a specified path."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        sm_id = encoder.decode_base_64(submodelIdentifier)

        if sm_id not in service_states.dynamic_submodel_cache:
            raise HTTPException(status_code=404, detail=f"Submodel with id '{sm_id}' not found.")

        sm = service_states.dynamic_submodel_cache[sm_id]
        sme = submodel_parser.get_submodel_element_by_id_short_path(sm, idShortPath)

        if sme is None:
            raise HTTPException(status_code=404, detail=f"SubmodelElement with path '{idShortPath}' not found in Submodel '{sm_id}'.")

        return _get_sme_value(sme)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


# GET /submodels/{submodelIdentifier}/$value
@router.get(
    "/submodels/{submodelIdentifier}/$value",
    tags=["submodels"],
    response_model=dict,
    responses={
        "200": {"model": dict},
        "404": {"description": "Submodel not found"},
        "500": {"description": "Server error"},
    },
    name="GetSubmodelById-ValueOnly",
    description="Returns a specific Submodel in the ValueOnly representation",
    summary="Returns a specific Submodel in the ValueOnly representation",
)
async def get_submodel_by_id_value_only(request: Request, submodelIdentifier: str):
    """Returns the values of all submodel elements within a Submodel."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        sm_id = encoder.decode_base_64(submodelIdentifier)

        if sm_id not in service_states.dynamic_submodel_cache:
            raise HTTPException(status_code=404, detail=f"Submodel with id '{sm_id}' not found.")

        sm = service_states.dynamic_submodel_cache[sm_id]
        sme_values = {}

        for sme in sm.submodel_element:
            sme_values.update({sme.id_short: _get_sme_value(sme)})

        return sme_values

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


# GET /submodels/{submodelIdentifier}/$metadata
@router.get(
    "/submodels/{submodelIdentifier}/$metadata",
    tags=["submodels"],
    response_model=dict,
    responses={
        "200": {"model": dict},
        "404": {"description": "Submodel not found"},
        "500": {"description": "Server error"},
    },
    name="GetSubmodelById-Metadata",
    description="Returns the metadata attributes of a specific Submodel",
    summary="Returns the metadata attributes of a specific Submodel",
)
async def get_submodel_by_id_metadata(request: Request, submodelIdentifier: str):
    """Returns the metadata attributes of a specific Submodel."""
    service_states: ServiceStates = request.app.state.service_states

    try:
        sm_id = encoder.decode_base_64(submodelIdentifier)

        if sm_id not in service_states.dynamic_submodel_cache:
            raise HTTPException(status_code=404, detail=f"Submodel with id '{sm_id}' not found.")

        sm = service_states.dynamic_submodel_cache[sm_id]

        metadata_dict = sdk_tools.convert_to_dict(sm)
        metadata_dict.pop("submodelElements", None)  # Remove submodel elements from metadata response
        kind_value = sm.kind.name[0].upper() + sm.kind.name[1:].lower()
        metadata_dict.update({"kind": kind_value})  # Ensure 'kind' is included in the metadata response
        return metadata_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}") from e


def _get_sme_value(sme) -> dict | str | list:
    if not hasattr(sme, "value"):
        raise ValueError("SubmodelElement does not have a value attribute.")

    if isinstance(sme, model.Property):
        return str(sme.value)

    if isinstance(sme, (model.SubmodelElementCollection, model.SubmodelElementList)):
        values = {}

        for element in sme.value:
            values.update({element.id_short: _get_sme_value(element)})

        return values

    _logger.debug("Unsupported SubmodelElement type for value retrieval '%s'.", type(sme).__name__)
    return {}
