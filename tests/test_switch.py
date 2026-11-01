"""Tests for the switch platform."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from .conftest import fire_update

SWITCHES = [
    ("switch.living_room_display", "get_display_on", "set_display_on"),
    ("switch.living_room_jet", "get_turbo_mode", "set_turbo_mode"),
    ("switch.living_room_power_save", "get_eco_mode", "set_eco_mode"),
    ("switch.living_room_super_silent", "get_quiet_mode", "set_quiet_mode"),
]


@pytest.mark.parametrize(("entity_id", "getter", "setter"), SWITCHES)
async def test_switch(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_aircon: MagicMock,
    entity_id: str,
    getter: str,
    setter: str,
) -> None:
    """Test each switch shows and changes its setting."""
    getattr(mock_aircon, getter).return_value = False
    await setup_integration()
    assert hass.states.get(entity_id).state == STATE_OFF

    getattr(mock_aircon, getter).return_value = True
    fire_update(mock_aircon)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    getattr(mock_aircon, setter).assert_awaited_once_with(False)

    getattr(mock_aircon, setter).reset_mock()
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    getattr(mock_aircon, setter).assert_awaited_once_with(True)
