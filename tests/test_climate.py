"""Tests for the climate platform."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from whirlpool.aircon import SETTING_HUMIDITY, FanSpeed, Mode

from homeassistant.components.climate import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_SWING_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_AUTO,
    FAN_HIGH,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    SWING_HORIZONTAL,
    SWING_OFF,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import fire_update

ENTITY_ID = "climate.living_room"


async def test_state(hass: HomeAssistant, setup_integration: Callable) -> None:
    """Test the climate entity reflects the air conditioner."""
    await setup_integration()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 24.5
    assert state.attributes[ATTR_TEMPERATURE] == 22.0
    assert state.attributes[ATTR_CURRENT_HUMIDITY] == 45
    assert state.attributes[ATTR_HUMIDITY] == 50
    assert state.attributes[ATTR_FAN_MODE] == FAN_AUTO
    assert state.attributes[ATTR_SWING_MODE] == SWING_OFF
    assert state.attributes[ATTR_MIN_TEMP] == 16
    assert state.attributes[ATTR_MAX_TEMP] == 30
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
    assert state.attributes[ATTR_FAN_MODES] == ["off", "auto", "low", "medium", "high"]
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        & ClimateEntityFeature.TARGET_HUMIDITY
    )


async def test_no_target_humidity(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test target humidity is left out for units without that setting."""
    mock_aircon.has_attribute.side_effect = lambda attr: attr != SETTING_HUMIDITY
    await setup_integration()

    state = hass.states.get(ENTITY_ID)
    assert not (
        state.attributes[ATTR_SUPPORTED_FEATURES]
        & ClimateEntityFeature.TARGET_HUMIDITY
    )
    assert ATTR_HUMIDITY not in state.attributes


@pytest.mark.parametrize(
    ("power_on", "sixth_sense", "mode", "expected"),
    [
        (False, False, Mode.Cool, HVACMode.OFF),
        (False, True, Mode.Cool, HVACMode.OFF),
        (True, False, Mode.Cool, HVACMode.COOL),
        (True, False, Mode.Heat, HVACMode.HEAT),
        (True, False, Mode.Fan, HVACMode.FAN_ONLY),
        # In 6th Sense the unit reports the step it picked, but the user chose auto.
        (True, True, Mode.Cool, HVACMode.AUTO),
        (True, True, Mode.Heat, HVACMode.AUTO),
    ],
)
async def test_hvac_mode_state(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_aircon: MagicMock,
    power_on: bool,
    sixth_sense: bool,
    mode: Mode,
    expected: HVACMode,
) -> None:
    """Test the HVAC mode shown for each appliance state."""
    mock_aircon.get_power_on.return_value = power_on
    mock_aircon.get_sixthsense_mode.return_value = sixth_sense
    mock_aircon.get_mode.return_value = mode
    await setup_integration()

    assert hass.states.get(ENTITY_ID).state == expected


async def test_push_updates(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test pushed updates change the state and availability."""
    await setup_integration()

    mock_aircon.get_temp.return_value = 19.0
    fire_update(mock_aircon)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).attributes[ATTR_TEMPERATURE] == 19.0

    mock_aircon.get_online.return_value = False
    fire_update(mock_aircon)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE

    mock_aircon.get_online.return_value = True
    fire_update(mock_aircon)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == HVACMode.COOL


async def test_set_temperature(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test setting the target temperature."""
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 25},
        blocking=True,
    )

    mock_aircon.set_temp.assert_awaited_once_with(25)


async def test_set_humidity(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test setting the target humidity."""
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HUMIDITY: 55},
        blocking=True,
    )

    mock_aircon.set_humidity.assert_awaited_once_with(55)


async def test_set_hvac_mode_off(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test turning the unit off through the HVAC mode."""
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )

    mock_aircon.set_power_on.assert_awaited_once_with(False)
    mock_aircon.set_mode.assert_not_awaited()


@pytest.mark.parametrize(
    ("hvac_mode", "expected_mode"),
    [
        (HVACMode.COOL, Mode.Cool),
        (HVACMode.HEAT, Mode.Heat),
        (HVACMode.FAN_ONLY, Mode.Fan),
        (HVACMode.AUTO, Mode.SixthSense),
    ],
)
@pytest.mark.parametrize("power_on", [True, False])
async def test_set_hvac_mode(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_aircon: MagicMock,
    hvac_mode: HVACMode,
    expected_mode: Mode,
    power_on: bool,
) -> None:
    """Test each HVAC mode is sent, and an off unit is turned on."""
    mock_aircon.get_power_on.return_value = power_on
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: hvac_mode},
        blocking=True,
    )

    mock_aircon.set_mode.assert_awaited_once_with(expected_mode)
    if power_on:
        mock_aircon.set_power_on.assert_not_awaited()
    else:
        mock_aircon.set_power_on.assert_awaited_once_with(True)


async def test_set_fan_mode(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test setting the fan speed."""
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_FAN_MODE: FAN_HIGH},
        blocking=True,
    )

    mock_aircon.set_fanspeed.assert_awaited_once_with(FanSpeed.High)


@pytest.mark.parametrize(
    ("swing_mode", "expected"), [(SWING_HORIZONTAL, True), (SWING_OFF, False)]
)
async def test_set_swing_mode(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_aircon: MagicMock,
    swing_mode: str,
    expected: bool,
) -> None:
    """Test turning the horizontal louver swing on and off."""
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_SWING_MODE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_SWING_MODE: swing_mode},
        blocking=True,
    )

    mock_aircon.set_h_louver_swing.assert_awaited_once_with(expected)


@pytest.mark.parametrize(
    ("service", "expected"), [(SERVICE_TURN_ON, True), (SERVICE_TURN_OFF, False)]
)
async def test_turn_on_off(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_aircon: MagicMock,
    service: str,
    expected: bool,
) -> None:
    """Test the turn on and turn off actions."""
    await setup_integration()

    await hass.services.async_call(
        CLIMATE_DOMAIN, service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )

    mock_aircon.set_power_on.assert_awaited_once_with(expected)


async def test_request_failed(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test a rejected command is reported to the user."""
    await setup_integration()
    mock_aircon.set_temp.return_value = False

    with pytest.raises(HomeAssistantError, match="Request failed"):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 25},
            blocking=True,
        )
