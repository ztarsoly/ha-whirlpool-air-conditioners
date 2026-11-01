"""Tests for setting up and unloading the integration."""

from collections.abc import Callable
from unittest.mock import MagicMock

from aiohttp import ClientError
import pytest
from whirlpool.auth import AccountLockedError

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.whirlpool_air_conditioners.const import DOMAIN

from .conftest import MOCK_SAID


async def test_setup_and_unload(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_appliances_manager: MagicMock,
) -> None:
    """Test the entry loads, connects, and disconnects on unload."""
    entry = await setup_integration()
    assert entry.state is ConfigEntryState.LOADED
    mock_appliances_manager.connect.assert_awaited_once()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_appliances_manager.disconnect.assert_awaited_once()


async def test_device_info(
    device_registry: dr.DeviceRegistry,
    setup_integration: Callable,
) -> None:
    """Test the air conditioner is registered as a device."""
    entry = await setup_integration()

    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, MOCK_SAID)}
    assert device.name == "Living room"
    assert device.manufacturer == "Whirlpool"
    assert device.model_id == "SPIW309A2WF"


@pytest.mark.parametrize(
    ("auth_error", "token_valid", "expected_state"),
    [
        (ClientError, True, ConfigEntryState.SETUP_RETRY),
        (TimeoutError, True, ConfigEntryState.SETUP_RETRY),
        (AccountLockedError, True, ConfigEntryState.SETUP_ERROR),
        (None, False, ConfigEntryState.SETUP_ERROR),
    ],
)
async def test_setup_auth_errors(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_auth: MagicMock,
    auth_error: type[Exception] | None,
    token_valid: bool,
    expected_state: ConfigEntryState,
) -> None:
    """Test connection errors retry setup and login errors start re-auth."""
    mock_auth.do_auth.side_effect = auth_error
    mock_auth.is_access_token_valid.return_value = token_valid

    entry = await setup_integration()

    assert entry.state is expected_state
    reauth_started = any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )
    assert reauth_started is (expected_state is ConfigEntryState.SETUP_ERROR)


async def test_setup_fetch_appliances_failed(
    setup_integration: Callable, mock_appliances_manager: MagicMock
) -> None:
    """Test setup is retried when the appliance list can't be fetched."""
    mock_appliances_manager.fetch_appliances.return_value = False

    entry = await setup_integration()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    mock_appliances_manager.connect.assert_not_awaited()
