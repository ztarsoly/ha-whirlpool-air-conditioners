"""Tests for diagnostics."""

from unittest.mock import MagicMock

from homeassistant.components.diagnostics import REDACTED

from custom_components.whirlpool_air_conditioners.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import MOCK_NAME, MOCK_USER_INPUT, MOCK_USERNAME


async def test_diagnostics(mock_aircon: MagicMock) -> None:
    """Test diagnostics list the air conditioner and hide credentials."""
    config_entry = MagicMock()
    config_entry.as_dict.return_value = {
        "title": MOCK_USERNAME,
        "unique_id": MOCK_USERNAME,
        "data": dict(MOCK_USER_INPUT),
    }
    config_entry.runtime_data.aircons = [mock_aircon]

    result = await async_get_config_entry_diagnostics(MagicMock(), config_entry)

    assert result["config_entry"]["unique_id"] == REDACTED
    assert result["config_entry"]["data"] == {
        **MOCK_USER_INPUT,
        "username": REDACTED,
        "password": REDACTED,
    }
    assert result["appliances"] == {
        "aircons": {
            MOCK_NAME: {
                "data_model": "DDM_AIRCONDITIONER_V1",
                "category": "AirConditioner",
                "model_number": "SPIW309A2WF",
            }
        }
    }
