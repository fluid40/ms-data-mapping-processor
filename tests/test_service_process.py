import datetime
import pytest
from ms_data_mapping_processor.core.service_process import _convert_value
from basyx.aas import model


@pytest.mark.parametrize(
    "input_value,target_type,expected",
    [
        ("true", model.datatypes.Boolean, True),
        ("false", model.datatypes.Boolean, False),
        ("test", model.datatypes.String, "test"),
        ("123", model.datatypes.Integer, 123),
        ("123", model.datatypes.Short, 123),
        ("3.14", model.datatypes.Double, 3.14),
        ("2024-06-01T12:34:56", model.datatypes.DateTime, datetime.datetime(2024, 6, 1, 12, 34, 56)),
    ]
)
def test_convert_value(input_value, target_type, expected):
    value = _convert_value(input_value, target_type)
    assert value == expected
