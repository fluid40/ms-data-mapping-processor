import copy
import datetime
import logging

from aas_standard_parser import descriptor_json_helper, submodel_parser
from basyx.aas import model
from basyx.aas.model.base import DataTypeDefXsd

from ms_data_mapping_processor.core.aas_env_processor import get_submodel
from ms_data_mapping_processor.core.server_handler import ServerHandler
from ms_data_mapping_processor.models.constants import get_external_port, get_external_url
from ms_data_mapping_processor.models.process_models import DescriptorMapping, ServiceStates
from ms_data_mapping_processor.models.value_data_models import PayloadValue

_logger = logging.getLogger(__name__)


def get_asset_values(states: ServiceStates):
    """Get the values from mapping configurations relations from broker.

    :param mapping_configurations: The mapping configurations.
    :param asset_connector: The asset connector client.
    :param influx_client: The InfluxDB client.
    """
    _logger.info("Get asset values from asset connector based on mapping configurations.")
    for configuration in states.mapping_configurations.configurations:
        asset_values: list[PayloadValue] = []

        # Process each source-sink relation from aimc mapping configuration
        for relation in configuration.source_sink_relations:
            _logger.debug(f"Get value for submodel element: {relation.source_properties.property_name}")

            # Prepare source reference data for asset connector
            source_references_data = {"Reference": relation.source_reference_as_dict()}
            # Get value from asset connector
            value = states.asset_connector_client.get_value(source_references_data)

            if value is None or value.payload is None:
                _logger.warning(f"No value received for '{relation.source_properties.property_name}'")
                continue

            _logger.info(f"Received value '{relation.source_properties.property_name}': {value.payload}")
            payload_value = PayloadValue(
                value.payload,
                relation.source_properties.property_name,
                relation.source_properties.parent_path,
                relation.sink_properties.submodel_id,
                relation.sink_properties.parent_path,
                relation.sink_properties.property_name,
            )

            # Update target property in submodel with received payload value
            _update_target_property_with_payload(payload_value, states.server_handler, states.dynamic_submodel_cache, states.descriptor_mapping)

            asset_values.append(payload_value)


def _update_target_property_with_payload(
    payload_value: PayloadValue, server_handler: ServerHandler, submodel_cache: dict[str, model.Submodel], descriptor_mapping: list[DescriptorMapping]
) -> model.Submodel | None:
    """Write payload value to target property in submodel.

    :param payload_values: payload value to write as property value.
    :param server_handler: The server handler.
    :param submodel_cache: The submodel cache.
    :param measurement: The measurement name.
    """
    _logger.info(
        f"Write value '{payload_value.value}' to element '{payload_value.target_element_path}' in submodel '{payload_value.target_submodel_id}'"
    )

    # get target submodel
    target_submodel = _get_submodel_from_cache(payload_value.target_submodel_id, server_handler, submodel_cache, descriptor_mapping)

    if target_submodel is None:
        _logger.error(f"Target submodel with ID '{payload_value.target_submodel_id}' not found.")
        return None

    target_element = submodel_parser.get_submodel_element_by_id_short_path(target_submodel, payload_value.target_element_path)

    if target_element is None:
        _logger.error(f"Target element with path '{payload_value.target_element_path}' not found in submodel: {payload_value.target_submodel_id}")
        return None

    if not isinstance(target_element, model.Property):
        _logger.error(f"Target element with path '{payload_value.target_element_path}' is not a property.")
        return None

    target_property: model.Property = target_element
    target_property.value = _convert_value(payload_value.value, target_property.value_type)

    return target_submodel


def _get_submodel_from_cache(
    submodel_id: str, server_handler: ServerHandler, submodel_cache: dict[str, model.Submodel], descriptor_mapping: list[DescriptorMapping]
) -> model.Submodel | None:
    """Get a submodel from the cache.

    :param submodel_id: The ID of the submodel.
    :param server_handler: The server handler.
    :param submodel_cache: The submodel cache.
    :return: The submodel if found, None otherwise.
    """
    # Check if submodel is already in cache
    if submodel_id in submodel_cache:
        # Return cached submodel
        return submodel_cache[submodel_id]

    # Fetch submodel from AAS server
    submodel = get_submodel(server_handler, submodel_id)
    if submodel is None:
        _logger.warning(f"Submodel with ID '{submodel_id}' not found on server.")
        return None
    # rewrite descriptor of submodel on submodel registry server
    _rewrite_registry_descriptor(submodel_id, server_handler, descriptor_mapping)

    # Cache the fetched submodel
    submodel_cache[submodel_id] = submodel
    # Return the fetched submodel
    return submodel


def _rewrite_registry_descriptor(submodel_id: str, server_handler: ServerHandler, descriptor_mapping: list[DescriptorMapping]):
    # get current descriptor from registry as 'master'
    master_descriptor = server_handler.sm_registry_client.submodel_registry.get_submodel_descriptor_by_id(submodel_id)

    if master_descriptor is None:
        _logger.warning(f"Submodel descriptor with ID '{submodel_id}' not found in AAS registry. Cannot rewrite descriptor.")
        return

    # parse 'master' descriptor to get endpoint href and protocol information
    master_href = descriptor_json_helper.get_endpoint_href_by_index(master_descriptor)
    master_href_data = descriptor_json_helper.parse_endpoint_href(master_href)

    # copy 'master' descriptor to 'slave' descriptor which will be rewritten and updated in registry
    slave_descriptor = copy.deepcopy(master_descriptor)

    # get the protocol information from the 'slave'
    slave_protocol_info = descriptor_json_helper.get_endpoint_protocol_information_by_index(slave_descriptor)
    # create new href with external URL and port and parsed tag and identifier
    slave_href = f"{_get_base_url()}/{master_href_data.tag}/{master_href_data.identifier}"
    slave_protocol_info["href"] = slave_href

    # update descriptor with new href on registry server
    _logger.info(f"Update descriptor for submodel '{submodel_id}' with new href '{slave_href}' on registry server")
    server_handler.sm_registry_client.submodel_registry.put_submodel_descriptor_by_id(submodel_id, slave_descriptor)

    # save 'master' and 'slave' descriptor as a mapping for later use when submodels are fetched and descriptors need to be rewritten
    mapping = DescriptorMapping(master_descriptor, slave_descriptor, submodel_id)
    descriptor_mapping.append(mapping)


def _get_base_url() -> str:
    external_url = get_external_url()
    port = get_external_port()

    if port:
        return f"{external_url}:{port}"

    return external_url


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
