"""Fixtures for the Whirlpool Air Conditioners tests."""

from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from whirlpool.aircon import (
    SETTING_SLEEP_MODE,
    SETVAL_SLEEP_MODE_OFF,
    Aircon,
    FanSpeed,
    Mode,
)
from whirlpool.types import ApplianceInfo

from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.whirlpool_air_conditioners.const import CONF_BRAND, DOMAIN

from . import init_integration

MOCK_USERNAME = "user@example.com"
MOCK_SAID = "WPR1XYZABC123"
MOCK_NAME = "living room"

MOCK_USER_INPUT = {
    CONF_USERNAME: MOCK_USERNAME,
    CONF_PASSWORD: "secret",
    CONF_REGION: "EU",
    CONF_BRAND: "Whirlpool",
}

INTEGRATION = "custom_components.whirlpool_air_conditioners"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the integration from custom_components."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_USERNAME,
        data=MOCK_USER_INPUT,
        unique_id=MOCK_USERNAME,
    )


def fire_update(aircon: MagicMock) -> None:
    """Simulate the cloud pushing new attribute values for an appliance."""
    for callback in list(aircon.attr_callbacks):
        callback()


@pytest.fixture
def mock_aircon() -> MagicMock:
    """Return a mocked air conditioner that is on, in cool mode."""
    aircon = MagicMock(spec=Aircon)
    aircon.said = MOCK_SAID
    aircon.name = MOCK_NAME
    aircon.appliance_info = ApplianceInfo(
        said=MOCK_SAID,
        name=MOCK_NAME,
        data_model="DDM_AIRCONDITIONER_V1",
        category="AirConditioner",
        model_number="SPIW309A2WF",
        serial_number="SN12345",
    )

    aircon.attr_callbacks = []
    aircon.register_attr_callback.side_effect = aircon.attr_callbacks.append
    aircon.unregister_attr_callback.side_effect = aircon.attr_callbacks.remove

    aircon.has_attribute.return_value = True
    aircon.bool_to_attr_value.side_effect = lambda value: "1" if value else "0"
    # pylint: disable-next=protected-access
    aircon._get_attribute.side_effect = {SETTING_SLEEP_MODE: SETVAL_SLEEP_MODE_OFF}.get

    aircon.get_online.return_value = True
    aircon.get_power_on.return_value = True
    aircon.get_mode.return_value = Mode.Cool
    aircon.get_sixthsense_mode.return_value = False
    aircon.get_current_temp.return_value = 24.5
    aircon.get_temp.return_value = 22.0
    aircon.get_current_humidity.return_value = 45
    aircon.get_humidity.return_value = 50
    aircon.get_fanspeed.return_value = FanSpeed.Auto
    aircon.get_h_louver_swing.return_value = False
    aircon.get_display_on.return_value = True
    aircon.get_turbo_mode.return_value = False
    aircon.get_eco_mode.return_value = False
    aircon.get_quiet_mode.return_value = False

    for setter in (
        "send_attributes",
        "set_power_on",
        "set_temp",
        "set_humidity",
        "set_mode",
        "set_fanspeed",
        "set_h_louver_swing",
        "set_turbo_mode",
        "set_eco_mode",
        "set_quiet_mode",
        "set_display_on",
    ):
        getattr(aircon, setter).return_value = True

    return aircon


@pytest.fixture
def mock_auth() -> Generator[MagicMock]:
    """Mock the Whirlpool login in both setup and the config flow."""
    auth = MagicMock()
    auth.do_auth = AsyncMock()
    auth.is_access_token_valid.return_value = True
    with (
        patch(f"{INTEGRATION}.Auth", return_value=auth),
        patch(f"{INTEGRATION}.config_flow.Auth", return_value=auth),
    ):
        yield auth


@pytest.fixture
def mock_appliances_manager(
    mock_aircon: MagicMock,
) -> Generator[MagicMock]:
    """Mock the appliances manager, owning one air conditioner."""
    manager = MagicMock()
    manager.fetch_appliances = AsyncMock(return_value=True)
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.aircons = [mock_aircon]
    with (
        patch(f"{INTEGRATION}.AppliancesManager", return_value=manager),
        patch(f"{INTEGRATION}.config_flow.AppliancesManager", return_value=manager),
    ):
        yield manager


@pytest.fixture
def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: MagicMock,
    mock_appliances_manager: MagicMock,
) -> Callable:
    """Return a coroutine function that sets up the integration."""

    async def _setup() -> MockConfigEntry:
        return await init_integration(hass, mock_config_entry)

    return _setup
