"""Tests for the config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
import pytest
from whirlpool.auth import AccountLockedError

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.whirlpool_air_conditioners.const import CONF_BRAND, DOMAIN

from .conftest import INTEGRATION, MOCK_USER_INPUT, MOCK_USERNAME


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip setting up the integration once the flow creates an entry."""
    with patch(f"{INTEGRATION}.async_setup_entry", return_value=True) as mock:
        yield mock


@pytest.mark.usefixtures("mock_auth", "mock_appliances_manager")
async def test_user_flow(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test a successful setup from the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"] == MOCK_USER_INPUT
    assert result["result"].unique_id == MOCK_USERNAME
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("auth_error", "token_valid", "expected_error"),
    [
        (AccountLockedError, True, "account_locked"),
        (ClientError, True, "cannot_connect"),
        (TimeoutError, True, "cannot_connect"),
        (Exception, True, "unknown"),
        (None, False, "invalid_auth"),
    ],
)
async def test_user_flow_auth_errors(
    hass: HomeAssistant,
    mock_auth: MagicMock,
    mock_appliances_manager: MagicMock,
    auth_error: type[Exception] | None,
    token_valid: bool,
    expected_error: str,
) -> None:
    """Test login errors are shown and the user can retry."""
    mock_auth.do_auth.side_effect = auth_error
    mock_auth.is_access_token_valid.return_value = token_valid

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    mock_auth.do_auth.side_effect = None
    mock_auth.is_access_token_valid.return_value = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_auth")
async def test_user_flow_no_aircons(
    hass: HomeAssistant, mock_appliances_manager: MagicMock
) -> None:
    """Test setup is refused when the account has no air conditioner."""
    mock_appliances_manager.aircons = []

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=MOCK_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_appliances"}


@pytest.mark.usefixtures("mock_auth", "mock_appliances_manager")
async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the same account can't be added twice, ignoring username case."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={**MOCK_USER_INPUT, CONF_USERNAME: MOCK_USERNAME.upper()},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_appliances_manager")
async def test_reauth_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_auth: MagicMock
) -> None:
    """Test re-entering the password, with a failed attempt first."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    mock_auth.is_access_token_valid.return_value = False
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "wrong", CONF_BRAND: "Whirlpool"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_auth.is_access_token_valid.return_value = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-secret", CONF_BRAND: "Maytag"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {
        **MOCK_USER_INPUT,
        CONF_PASSWORD: "new-secret",
        CONF_BRAND: "Maytag",
    }
