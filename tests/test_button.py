"""Tests for the button platform."""

from collections.abc import Callable
from unittest.mock import MagicMock

from whirlpool.aircon import SETTING_REBOOT_WIFI

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

ENTITY_ID = "button.living_room_restart_wi_fi_module"


async def test_press(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable,
    mock_aircon: MagicMock,
) -> None:
    """Test pressing the button sends the Wi-Fi reboot command."""
    await setup_integration()
    assert entity_registry.async_get(ENTITY_ID).entity_category is EntityCategory.CONFIG

    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )

    mock_aircon.send_attributes.assert_awaited_once_with({SETTING_REBOOT_WIFI: "1"})


async def test_not_created_when_unsupported(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test no reboot button for units without that setting."""
    mock_aircon.has_attribute.side_effect = lambda attr: attr != SETTING_REBOOT_WIFI
    await setup_integration()

    assert hass.states.get(ENTITY_ID) is None
