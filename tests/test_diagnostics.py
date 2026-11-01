"""Tests for diagnostics."""

from collections.abc import Callable

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from .conftest import MOCK_NAME


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    setup_integration: Callable,
) -> None:
    """Test diagnostics list the air conditioner and hide credentials."""
    entry = await setup_integration()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["config_entry"]["data"]["username"] == REDACTED
    assert result["config_entry"]["data"]["password"] == REDACTED
    assert result["config_entry"]["unique_id"] == REDACTED
    assert result["appliances"] == {
        "aircons": {
            MOCK_NAME: {
                "data_model": "DDM_AIRCONDITIONER_V1",
                "category": "AirConditioner",
                "model_number": "SPIW309A2WF",
            }
        }
    }
