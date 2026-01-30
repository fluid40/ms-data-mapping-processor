"""Data models for value data processing."""


class PayloadValue:
    """Represents a payload value for a submodel element."""

    value: str
    property_name: str
    parent_name: str
    target_submodel_id: str

    def __init__(
        self,
        value: str,
        property_name: str,
        source_parent_path: list[str],
        target_submodel_id: str,
        target_parent_path: list[str],
        target_property_name: str,
    ):
        """Initializes a PayloadValue instance.

        :param value: The value of the payload.
        :param property_name: The name of the property.
        :param parent_name: The name of the parent element.
        :param target_submodel_id: The ID of the target submodel.
        """
        self.value = value
        self.property_name = property_name
        self.parent_name = self._get_source_parent_property_group_name(source_parent_path)
        self.target_submodel_id = target_submodel_id
        self.target_element_path = self._get_source_element_path(target_parent_path, target_property_name)

    def _get_source_parent_property_group_name(self, source_parent_path: list[str]) -> str:
        """Get the name of the parent property group from the source. Ignore 'properties' entries from the path."""
        if len(source_parent_path) == 0:
            return ""

        return next((n for n in reversed(source_parent_path) if n != "properties"), "")

    def _get_source_element_path(self, target_parent_path: list[str], target_property_name: str) -> str:
        """Get the element path from the target parent path and property name."""
        if not target_parent_path or not target_property_name:
            return ""

        return f"{'.'.join(target_parent_path)}.{target_property_name}"
