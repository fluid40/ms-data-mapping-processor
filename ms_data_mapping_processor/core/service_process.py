import datetime
import logging

from aas_http_client import SdkWrapper
from aas_standard_parser import submodel_parser
from basyx.aas import model
from basyx.aas.model.base import DataTypeDefXsd

from ms_data_mapping_processor.models.process_models import ServiceStates
from ms_data_mapping_processor.models.value_data_models import PayloadValue

logger = logging.getLogger(__name__)

# Global counter for runtime process executions
counter = 1


def get_asset_values(states: ServiceStates):
    """Get the values from mapping configurations relations from broker.

    :param mapping_configurations: The mapping configurations.
    :param asset_connector: The asset connector client.
    :param influx_client: The InfluxDB client.
    """
    logger.info("Get asset values from asset connector based on mapping configurations.")
    for configuration in states.mapping_configurations.configurations:
        asset_values: list[PayloadValue] = []

        # Process each source-sink relation from aimc mapping configuration
        for relation in configuration.source_sink_relations:
            logger.debug(f"Get value for submodel element: {relation.source_properties.property_name}")

            # Prepare source reference data for asset connector
            source_references_data = {"Reference": relation.source_reference_as_dict()}
            # Get value from asset connector
            value = states.asset_connector_client.get_value(source_references_data)

            if value is None or value.payload is None:
                logger.warning(f"No value received for '{relation.source_properties.property_name}'")
                continue

            logger.info(f"Received value '{relation.source_properties.property_name}': {value.payload}")
            payload_value = PayloadValue(
                value.payload,
                relation.source_properties.property_name,
                relation.source_properties.parent_path,
                relation.sink_properties.submodel_id,
                relation.sink_properties.parent_path,
                relation.sink_properties.property_name,
            )

            # Update target property in submodel with received payload value
            _update_target_property_with_payload(payload_value, states.aas_server_wrapper_list, states.dynamic_submodel_cache)

            asset_values.append(payload_value)


def _update_target_property_with_payload(payload_value: PayloadValue, wrapper: SdkWrapper, submodel_cache: dict[str, model.Submodel]):
    """Write payload value to target property in submodel.

    :param payload_values: payload value to write as property value.
    :param wrapper: The SDK wrapper.
    :param submodel_cache: The submodel cache.
    :param measurement: The measurement name.
    """
    logger.info(
        f"Write payload value '{payload_value.value}' to element '{payload_value.target_element_path}' in submodel '{payload_value.target_submodel_id}'"
    )
    # get target submodel
    target_submodel = _get_submodel_from_cache(payload_value.target_submodel_id, wrapper, submodel_cache)

    if target_submodel is None:
        logger.error(f"Target submodel with ID '{payload_value.target_submodel_id}' not found.")
        return

    target_element = submodel_parser.get_submodel_element_by_id_short_path(target_submodel, payload_value.target_element_path)

    if target_element is None:
        logger.error(f"Target element with path '{payload_value.target_element_path}' not found in submodel: {payload_value.target_submodel_id}")
        return

    if not isinstance(target_element, model.Property):
        logger.error(f"Target element with path '{payload_value.target_element_path}' is not a property.")
        return

    target_property: model.Property = target_element
    target_property.value = _convert_value(payload_value.value, target_property.value_type)


def _get_submodel_from_cache(submodel_id: str, wrapper: SdkWrapper, submodel_cache: dict[str, model.Submodel]) -> model.Submodel | None:
    """Get a submodel from the cache.

    :param submodel_id: The ID of the submodel.
    :param wrapper: The SDK wrapper.
    :return: The submodel if found, None otherwise.
    """
    # Check if submodel is already in cache
    if submodel_id in submodel_cache:
        # Return cached submodel
        return submodel_cache[submodel_id]

    # Fetch submodel from AAS server
    submodel = wrapper.get_submodel_by_id(submodel_id)
    if submodel is None:
        logger.warning(f"Submodel with ID '{submodel_id}' not found on server.")
        return None

    # Cache the fetched submodel
    submodel_cache[submodel_id] = submodel
    # Return the fetched submodel
    return submodel


def _convert_value(value: str, value_type: DataTypeDefXsd) -> any:
    """Convert a string value to an expected value type.

    :param value: string value
    :param expected_type: expected value type
    :raises ValueError: if the value cannot be converted to the expected type
    :return: converted value
    """
    return_value: any = value

    match value_type:
        case model.datatypes.Boolean:
            v = value.strip().lower()
            if v == "true":
                return_value = True
            elif v == "false":
                return_value = False
            else:
                raise ValueError(f"Cannot convert '{value}' to boolean.")
        case model.datatypes.Integer | model.datatypes.Short:
            return_value = int(value)
        case model.datatypes.Double | model.datatypes.Float:
            return_value = float(value)
        case model.datatypes.DateTime:
            return_value = datetime.datetime.fromisoformat(value)

    return return_value
