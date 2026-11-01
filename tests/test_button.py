"""Tests for the button platform."""

from unittest.mock import MagicMock

import pytest
from whirlpool.aircon import SETTING_REBOOT_WIFI, Aircon

from homeassistant.components.button import ButtonDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.whirlpool_air_conditioners import button
from custom_components.whirlpool_air_conditioners.button import (
    WhirlpoolWifiRebootButton,
)

from .conftest import MOCK_SAID, setup_platform


async def test_setup_entry(mock_aircon: MagicMock) -> None:
    """Test the reboot button is only added for units that support it."""
    unsupported = MagicMock(spec=Aircon)
    unsupported.has_attribute.side_effect = lambda attr: attr != SETTING_REBOOT_WIFI

    entities = await setup_platform(button, [mock_aircon, unsupported])

    assert len(entities) == 1
    entity = entities[0]
    assert entity.unique_id == f"{MOCK_SAID}-wifi_reboot"
    assert entity.translation_key == "wifi_reboot"
    assert entity.device_class is ButtonDeviceClass.RESTART
    assert entity.entity_category is EntityCategory.CONFIG


async def test_press(mock_aircon: MagicMock) -> None:
    """Test pressing the button sends the Wi-Fi reboot command."""
    await WhirlpoolWifiRebootButton(mock_aircon).async_press()

    mock_aircon.send_attributes.assert_awaited_once_with({SETTING_REBOOT_WIFI: "1"})


async def test_press_failed(mock_aircon: MagicMock) -> None:
    """Test a rejected command raises an error for the user."""
    mock_aircon.send_attributes.return_value = False

    with pytest.raises(HomeAssistantError):
        await WhirlpoolWifiRebootButton(mock_aircon).async_press()
