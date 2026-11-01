"""Fixtures for the Whirlpool Air Conditioners tests."""

from types import ModuleType
from unittest.mock import MagicMock

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
from homeassistant.helpers.entity import Entity

from custom_components.whirlpool_air_conditioners.const import CONF_BRAND

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


async def setup_platform(platform: ModuleType, aircons: list[MagicMock]) -> list[Entity]:
    """Run a platform's async_setup_entry and return the entities it adds."""
    config_entry = MagicMock()
    config_entry.runtime_data.aircons = aircons
    entities: list[Entity] = []
    await platform.async_setup_entry(MagicMock(), config_entry, entities.extend)
    return entities
