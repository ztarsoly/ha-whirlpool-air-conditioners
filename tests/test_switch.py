"""Tests for the switch platform."""

from unittest.mock import MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.whirlpool_air_conditioners import switch
from custom_components.whirlpool_air_conditioners.switch import (
    WhirlpoolDisplaySwitch,
    WhirlpoolJetSwitch,
    WhirlpoolPowerSaveSwitch,
    WhirlpoolSuperSilentSwitch,
)

from .conftest import MOCK_SAID, setup_platform

SWITCHES = [
    (WhirlpoolDisplaySwitch, "display", "get_display_on", "set_display_on"),
    (WhirlpoolJetSwitch, "jet", "get_turbo_mode", "set_turbo_mode"),
    (WhirlpoolPowerSaveSwitch, "power_save", "get_eco_mode", "set_eco_mode"),
    (WhirlpoolSuperSilentSwitch, "super_silent", "get_quiet_mode", "set_quiet_mode"),
]


async def test_setup_entry(mock_aircon: MagicMock) -> None:
    """Test the four switches are added for each air conditioner."""
    entities = await setup_platform(switch, [mock_aircon])

    assert sorted(type(entity).__name__ for entity in entities) == sorted(
        cls.__name__ for cls, *_ in SWITCHES
    )


@pytest.mark.parametrize(("cls", "key", "getter", "setter"), SWITCHES)
async def test_switch(
    mock_aircon: MagicMock, cls: type, key: str, getter: str, setter: str
) -> None:
    """Test each switch shows and changes its setting."""
    entity = cls(mock_aircon)
    assert entity.unique_id == f"{MOCK_SAID}-{key}"
    assert entity.translation_key == key

    getattr(mock_aircon, getter).return_value = False
    assert entity.is_on is False
    getattr(mock_aircon, getter).return_value = True
    assert entity.is_on is True

    await entity.async_turn_off()
    getattr(mock_aircon, setter).assert_awaited_once_with(False)

    getattr(mock_aircon, setter).reset_mock()
    await entity.async_turn_on()
    getattr(mock_aircon, setter).assert_awaited_once_with(True)


@pytest.mark.parametrize(("cls", "key", "getter", "setter"), SWITCHES)
@pytest.mark.parametrize("method", ["async_turn_on", "async_turn_off"])
async def test_request_failed(
    mock_aircon: MagicMock, cls: type, key: str, getter: str, setter: str, method: str
) -> None:
    """Test a rejected command raises an error for the user."""
    getattr(mock_aircon, setter).return_value = False

    with pytest.raises(HomeAssistantError):
        await getattr(cls(mock_aircon), method)()
