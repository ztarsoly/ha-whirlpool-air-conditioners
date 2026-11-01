"""Tests for setting up and unloading the integration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
import pytest
from whirlpool.auth import AccountLockedError
from whirlpool.backendselector import Brand, Region

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from custom_components.whirlpool_air_conditioners import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)

from .conftest import INTEGRATION, MOCK_USER_INPUT


@pytest.fixture
def hass() -> MagicMock:
    """Return a mocked Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def config_entry() -> MagicMock:
    """Return a mocked config entry."""
    entry = MagicMock()
    entry.data = dict(MOCK_USER_INPUT)
    return entry


@pytest.fixture
def mock_auth() -> Generator[MagicMock]:
    """Mock the Whirlpool login."""
    auth = MagicMock()
    auth.do_auth = AsyncMock()
    auth.is_access_token_valid.return_value = True
    with (
        patch(f"{INTEGRATION}.Auth", return_value=auth) as auth_class,
        patch(f"{INTEGRATION}.async_get_clientsession"),
    ):
        auth.auth_class = auth_class
        yield auth


@pytest.fixture
def mock_manager() -> Generator[MagicMock]:
    """Mock the appliances manager."""
    manager = MagicMock()
    manager.fetch_appliances = AsyncMock(return_value=True)
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    with patch(f"{INTEGRATION}.AppliancesManager", return_value=manager):
        yield manager


def test_platforms() -> None:
    """Test the integration sets up only the air conditioner platforms."""
    assert PLATFORMS == [
        Platform.BUTTON,
        Platform.CLIMATE,
        Platform.SELECT,
        Platform.SWITCH,
    ]


async def test_setup_and_unload(
    hass: MagicMock,
    config_entry: MagicMock,
    mock_auth: MagicMock,
    mock_manager: MagicMock,
) -> None:
    """Test a successful setup connects, and unloading disconnects."""
    assert await async_setup_entry(hass, config_entry) is True

    mock_auth.do_auth.assert_awaited_once_with(store=False)
    args = mock_auth.auth_class.call_args.args
    assert (args[1], args[2]) == (
        MOCK_USER_INPUT[CONF_USERNAME],
        MOCK_USER_INPUT[CONF_PASSWORD],
    )
    mock_manager.connect.assert_awaited_once()
    assert config_entry.runtime_data is mock_manager
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        config_entry, PLATFORMS
    )

    assert await async_unload_entry(hass, config_entry) is True
    mock_manager.disconnect.assert_awaited_once()
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        config_entry, PLATFORMS
    )


@pytest.mark.usefixtures("mock_auth", "mock_manager")
async def test_setup_defaults_region_and_brand(
    hass: MagicMock, config_entry: MagicMock
) -> None:
    """Test older entries without region and brand use EU and Whirlpool."""
    config_entry.data = {
        CONF_USERNAME: MOCK_USER_INPUT[CONF_USERNAME],
        CONF_PASSWORD: MOCK_USER_INPUT[CONF_PASSWORD],
    }

    with patch(f"{INTEGRATION}.BackendSelector") as backend_selector:
        await async_setup_entry(hass, config_entry)

    backend_selector.assert_called_once_with(Brand.Whirlpool, Region.EU)


@pytest.mark.parametrize(
    ("auth_error", "token_valid", "expected_error", "translation_key"),
    [
        (ClientError, True, ConfigEntryNotReady, "cannot_connect"),
        (TimeoutError, True, ConfigEntryNotReady, "cannot_connect"),
        (AccountLockedError, True, ConfigEntryAuthFailed, "account_locked"),
        (None, False, ConfigEntryAuthFailed, "invalid_auth"),
    ],
)
async def test_setup_auth_errors(
    hass: MagicMock,
    config_entry: MagicMock,
    mock_auth: MagicMock,
    mock_manager: MagicMock,
    auth_error: type[Exception] | None,
    token_valid: bool,
    expected_error: type[Exception],
    translation_key: str,
) -> None:
    """Test connection errors retry setup and login errors ask for re-auth."""
    mock_auth.do_auth.side_effect = auth_error
    mock_auth.is_access_token_valid.return_value = token_valid

    with pytest.raises(expected_error) as err:
        await async_setup_entry(hass, config_entry)

    assert err.value.translation_key == translation_key
    mock_manager.connect.assert_not_awaited()


@pytest.mark.usefixtures("mock_auth")
async def test_setup_fetch_appliances_failed(
    hass: MagicMock, config_entry: MagicMock, mock_manager: MagicMock
) -> None:
    """Test setup is retried when the appliance list can't be fetched."""
    mock_manager.fetch_appliances.return_value = False

    with pytest.raises(ConfigEntryNotReady) as err:
        await async_setup_entry(hass, config_entry)

    assert err.value.translation_key == "appliances_fetch_failed"
    mock_manager.connect.assert_not_awaited()
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()
