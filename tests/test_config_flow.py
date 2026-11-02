"""Tests for the config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
import pytest
from whirlpool.auth import AccountLockedError

from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.whirlpool_air_conditioners.config_flow import (
    WhirlpoolConfigFlow,
    authenticate,
)
from custom_components.whirlpool_air_conditioners.const import CONF_BRAND, DOMAIN

from .conftest import INTEGRATION, MOCK_USER_INPUT, MOCK_USERNAME

FLOW = f"{INTEGRATION}.config_flow"


@pytest.fixture
def hass_mock() -> MagicMock:
    """Return a mocked Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_auth() -> Generator[MagicMock]:
    """Mock the Whirlpool login."""
    auth = MagicMock()
    auth.do_auth = AsyncMock()
    auth.is_access_token_valid.return_value = True
    with (
        patch(f"{FLOW}.Auth", return_value=auth),
        patch(f"{FLOW}.async_get_clientsession"),
    ):
        yield auth


@pytest.fixture
def mock_manager(mock_aircon: MagicMock) -> Generator[MagicMock]:
    """Mock the appliances manager, owning one air conditioner."""
    manager = MagicMock()
    manager.connect = AsyncMock(return_value=True)
    manager.disconnect = AsyncMock()
    manager.aircons = [mock_aircon]
    with patch(f"{FLOW}.AppliancesManager", return_value=manager):
        yield manager


def make_flow(source: str, existing_entry: MagicMock | None = None) -> WhirlpoolConfigFlow:
    """Return a config flow attached to a mocked Home Assistant."""
    flow = WhirlpoolConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entry_for_domain_unique_id.return_value = (
        existing_entry
    )
    flow.hass.config_entries.flow.async_progress_by_handler.return_value = []
    flow.handler = DOMAIN
    flow.flow_id = "test-flow"
    flow.context = {"source": source}
    return flow


@pytest.mark.usefixtures("mock_auth")
async def test_authenticate_success(
    hass_mock: MagicMock, mock_manager: MagicMock
) -> None:
    """Test a valid login with an air conditioner returns no error."""
    assert await authenticate(hass_mock, MOCK_USER_INPUT, True) is None

    # The check only lists the appliances; it must not stay connected.
    mock_manager.connect.assert_awaited_once()
    mock_manager.disconnect.assert_awaited_once()


@pytest.mark.usefixtures("mock_auth")
async def test_authenticate_connect_failed(
    hass_mock: MagicMock, mock_manager: MagicMock
) -> None:
    """Test a failure to load the appliance list is a connection error."""
    mock_manager.connect.return_value = False

    assert await authenticate(hass_mock, MOCK_USER_INPUT, True) == "cannot_connect"
    mock_manager.disconnect.assert_not_awaited()


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
@pytest.mark.usefixtures("mock_manager")
async def test_authenticate_errors(
    hass_mock: MagicMock,
    mock_auth: MagicMock,
    auth_error: type[Exception] | None,
    token_valid: bool,
    expected_error: str,
) -> None:
    """Test each login problem maps to its error message."""
    mock_auth.do_auth.side_effect = auth_error
    mock_auth.is_access_token_valid.return_value = token_valid

    assert await authenticate(hass_mock, MOCK_USER_INPUT, True) == expected_error


@pytest.mark.usefixtures("mock_auth")
async def test_authenticate_no_aircons(
    hass_mock: MagicMock, mock_manager: MagicMock
) -> None:
    """Test an account without an air conditioner is refused."""
    mock_manager.aircons = []

    assert await authenticate(hass_mock, MOCK_USER_INPUT, True) == "no_appliances"


@pytest.mark.usefixtures("mock_auth")
async def test_authenticate_skips_appliance_check(
    hass_mock: MagicMock, mock_manager: MagicMock
) -> None:
    """Test re-authentication doesn't fetch the appliance list."""
    assert await authenticate(hass_mock, MOCK_USER_INPUT, False) is None

    mock_manager.connect.assert_not_awaited()


async def test_user_step_shows_form() -> None:
    """Test the first step shows the login form."""
    result = await make_flow(SOURCE_USER).async_step_user()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]


@pytest.mark.usefixtures("mock_auth", "mock_manager")
async def test_user_step_creates_entry() -> None:
    """Test a valid login creates an entry named after the username."""
    flow = make_flow(SOURCE_USER)

    result = await flow.async_step_user(dict(MOCK_USER_INPUT))

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"] == MOCK_USER_INPUT
    assert flow.unique_id == MOCK_USERNAME


@pytest.mark.usefixtures("mock_manager")
async def test_user_step_shows_error(mock_auth: MagicMock) -> None:
    """Test a failed login shows the form again with the error."""
    mock_auth.is_access_token_valid.return_value = False

    result = await make_flow(SOURCE_USER).async_step_user(dict(MOCK_USER_INPUT))

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.usefixtures("mock_auth", "mock_manager")
async def test_user_step_already_configured() -> None:
    """Test the same account can't be added twice, ignoring username case."""
    existing_entry = MagicMock()
    existing_entry.data = dict(MOCK_USER_INPUT)
    flow = make_flow(SOURCE_USER, existing_entry=existing_entry)

    # Home Assistant's flow manager turns this exception into an abort result.
    with pytest.raises(AbortFlow) as err:
        await flow.async_step_user(
            {**MOCK_USER_INPUT, CONF_USERNAME: MOCK_USERNAME.upper()}
        )

    assert err.value.reason == "already_configured"
    flow.hass.config_entries.async_entry_for_domain_unique_id.assert_called_with(
        DOMAIN, MOCK_USERNAME
    )


def make_reauth_flow() -> tuple[WhirlpoolConfigFlow, MagicMock]:
    """Return a re-auth flow and the entry it re-authenticates."""
    entry = MagicMock()
    entry.entry_id = "entry-id"
    entry.data = dict(MOCK_USER_INPUT)
    entry.update_listeners = []
    flow = make_flow(SOURCE_REAUTH)
    flow.context["entry_id"] = "entry-id"
    flow.hass.config_entries.async_get_known_entry.return_value = entry
    return flow, entry


async def test_reauth_shows_form() -> None:
    """Test re-authentication asks for the password and brand."""
    flow, _ = make_reauth_flow()

    result = await flow.async_step_reauth(dict(MOCK_USER_INPUT))

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert set(result["data_schema"].schema) == {CONF_PASSWORD, CONF_BRAND}


@pytest.mark.usefixtures("mock_manager")
async def test_reauth_error(mock_auth: MagicMock) -> None:
    """Test a wrong password shows the form again with the error."""
    mock_auth.is_access_token_valid.return_value = False
    flow, _ = make_reauth_flow()

    result = await flow.async_step_reauth_confirm(
        {CONF_PASSWORD: "wrong", CONF_BRAND: "Whirlpool"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    flow.hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.usefixtures("mock_auth", "mock_manager")
async def test_reauth_success() -> None:
    """Test a new password and brand are saved to the entry."""
    flow, entry = make_reauth_flow()

    result = await flow.async_step_reauth_confirm(
        {CONF_PASSWORD: "new-secret", CONF_BRAND: "Maytag"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    update = flow.hass.config_entries.async_update_entry.call_args
    assert update.kwargs["entry"] is entry
    assert update.kwargs["data"] == {
        **MOCK_USER_INPUT,
        CONF_PASSWORD: "new-secret",
        CONF_BRAND: "Maytag",
    }
    flow.hass.config_entries.async_schedule_reload.assert_called_once_with("entry-id")
