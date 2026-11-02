"""Tests for the climate platform."""

from unittest.mock import MagicMock

import pytest
from whirlpool.aircon import FanSpeed, Mode
from whirlpool.httpapi.aircon import SETTING_HUMIDITY

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    SWING_HORIZONTAL,
    SWING_OFF,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from custom_components.whirlpool_air_conditioners import climate
from custom_components.whirlpool_air_conditioners.climate import AirConEntity

from .conftest import MOCK_SAID, setup_platform


async def test_setup_entry(
    mock_aircon: MagicMock, mock_aws_aircon: MagicMock
) -> None:
    """Test one climate entity is added per air conditioner, on either API."""
    entities = await setup_platform(climate, [mock_aircon, mock_aws_aircon])

    assert [type(entity) for entity in entities] == [AirConEntity, AirConEntity]
    assert [entity.unique_id for entity in entities] == [MOCK_SAID, "AWS_SAID"]


def test_attributes(mock_aircon: MagicMock) -> None:
    """Test the entity reflects the air conditioner."""
    entity = AirConEntity(mock_aircon)

    assert entity.name is None
    assert entity.current_temperature == 24.5
    assert entity.target_temperature == 22.0
    assert entity.current_humidity == 45
    assert entity.target_humidity == 50
    assert entity.fan_mode == FAN_AUTO
    assert entity.swing_mode == SWING_OFF
    assert entity.min_temp == 16
    assert entity.max_temp == 30
    assert entity.target_temperature_step == 1
    assert entity.temperature_unit == UnitOfTemperature.CELSIUS
    assert entity.hvac_modes == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
    assert entity.fan_modes == [FAN_OFF, FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    assert entity.swing_modes == [SWING_HORIZONTAL, SWING_OFF]


def test_supported_features(mock_aircon: MagicMock) -> None:
    """Test target humidity is only offered when the unit reports it."""
    with_humidity = AirConEntity(mock_aircon).supported_features
    mock_aircon.has_attribute.side_effect = lambda attr: attr != SETTING_HUMIDITY
    without_humidity = AirConEntity(mock_aircon).supported_features

    for feature in (
        ClimateEntityFeature.TARGET_TEMPERATURE,
        ClimateEntityFeature.FAN_MODE,
        ClimateEntityFeature.SWING_MODE,
        ClimateEntityFeature.TURN_ON,
        ClimateEntityFeature.TURN_OFF,
    ):
        assert feature in without_humidity
    assert ClimateEntityFeature.TARGET_HUMIDITY not in without_humidity
    assert with_humidity == without_humidity | ClimateEntityFeature.TARGET_HUMIDITY


def test_supported_features_aws(
    mock_aircon: MagicMock, mock_aws_aircon: MagicMock
) -> None:
    """Test AWS IoT units get the base features but no target humidity."""
    mock_aircon.has_attribute.side_effect = lambda attr: attr != SETTING_HUMIDITY

    assert (
        AirConEntity(mock_aws_aircon).supported_features
        == AirConEntity(mock_aircon).supported_features
    )


@pytest.mark.parametrize(
    ("power_on", "sixth_sense", "mode", "expected"),
    [
        (False, False, Mode.Cool, HVACMode.OFF),
        (False, True, Mode.Cool, HVACMode.OFF),
        (True, False, Mode.Cool, HVACMode.COOL),
        (True, False, Mode.Heat, HVACMode.HEAT),
        (True, False, Mode.Fan, HVACMode.FAN_ONLY),
        (True, False, None, None),
        # In 6th Sense the unit reports the step it picked, but the user chose auto.
        (True, True, Mode.Cool, HVACMode.AUTO),
        (True, True, Mode.Heat, HVACMode.AUTO),
    ],
)
def test_hvac_mode(
    mock_aircon: MagicMock,
    power_on: bool,
    sixth_sense: bool,
    mode: Mode | None,
    expected: HVACMode | None,
) -> None:
    """Test the HVAC mode shown for each appliance state."""
    mock_aircon.get_power_on.return_value = power_on
    mock_aircon.get_sixthsense_mode.return_value = sixth_sense
    mock_aircon.get_mode.return_value = mode

    assert AirConEntity(mock_aircon).hvac_mode == expected


@pytest.mark.parametrize(
    ("fanspeed", "expected"),
    [
        (FanSpeed.Off, FAN_OFF),
        (FanSpeed.Auto, FAN_AUTO),
        (FanSpeed.Low, FAN_LOW),
        (FanSpeed.Medium, FAN_MEDIUM),
        (FanSpeed.High, FAN_HIGH),
        (None, FAN_OFF),
    ],
)
def test_fan_mode(
    mock_aircon: MagicMock, fanspeed: FanSpeed | None, expected: str
) -> None:
    """Test each fan speed is shown, with unknown speeds shown as off."""
    mock_aircon.get_fanspeed.return_value = fanspeed

    assert AirConEntity(mock_aircon).fan_mode == expected


def test_swing_mode_on(mock_aircon: MagicMock) -> None:
    """Test horizontal swing is shown when the louver swings."""
    mock_aircon.get_h_louver_swing.return_value = True

    assert AirConEntity(mock_aircon).swing_mode == SWING_HORIZONTAL


async def test_set_temperature(mock_aircon: MagicMock) -> None:
    """Test setting the target temperature."""
    await AirConEntity(mock_aircon).async_set_temperature(**{ATTR_TEMPERATURE: 25})

    mock_aircon.set_temp.assert_awaited_once_with(25)


async def test_set_humidity(mock_aircon: MagicMock) -> None:
    """Test setting the target humidity."""
    await AirConEntity(mock_aircon).async_set_humidity(55)

    mock_aircon.set_humidity.assert_awaited_once_with(55)


async def test_set_hvac_mode_off(mock_aircon: MagicMock) -> None:
    """Test turning the unit off through the HVAC mode."""
    await AirConEntity(mock_aircon).async_set_hvac_mode(HVACMode.OFF)

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
    mock_aircon: MagicMock,
    hvac_mode: HVACMode,
    expected_mode: Mode,
    power_on: bool,
) -> None:
    """Test each HVAC mode is sent, and an off unit is turned on."""
    mock_aircon.get_power_on.return_value = power_on

    await AirConEntity(mock_aircon).async_set_hvac_mode(hvac_mode)

    mock_aircon.set_mode.assert_awaited_once_with(expected_mode)
    if power_on:
        mock_aircon.set_power_on.assert_not_awaited()
    else:
        mock_aircon.set_power_on.assert_awaited_once_with(True)


@pytest.mark.parametrize(
    ("fan_mode", "expected"),
    [
        (FAN_OFF, FanSpeed.Off),
        (FAN_AUTO, FanSpeed.Auto),
        (FAN_LOW, FanSpeed.Low),
        (FAN_MEDIUM, FanSpeed.Medium),
        (FAN_HIGH, FanSpeed.High),
    ],
)
async def test_set_fan_mode(
    mock_aircon: MagicMock, fan_mode: str, expected: FanSpeed
) -> None:
    """Test setting each fan speed."""
    await AirConEntity(mock_aircon).async_set_fan_mode(fan_mode)

    mock_aircon.set_fanspeed.assert_awaited_once_with(expected)


@pytest.mark.parametrize(
    ("swing_mode", "expected"), [(SWING_HORIZONTAL, True), (SWING_OFF, False)]
)
async def test_set_swing_mode(
    mock_aircon: MagicMock, swing_mode: str, expected: bool
) -> None:
    """Test turning the horizontal louver swing on and off."""
    await AirConEntity(mock_aircon).async_set_swing_mode(swing_mode)

    mock_aircon.set_h_louver_swing.assert_awaited_once_with(expected)


async def test_turn_on_off(mock_aircon: MagicMock) -> None:
    """Test the turn on and turn off actions."""
    entity = AirConEntity(mock_aircon)

    await entity.async_turn_on()
    mock_aircon.set_power_on.assert_awaited_once_with(True)

    mock_aircon.set_power_on.reset_mock()
    await entity.async_turn_off()
    mock_aircon.set_power_on.assert_awaited_once_with(False)


@pytest.mark.parametrize(
    ("method", "args", "setter"),
    [
        ("async_set_temperature", {ATTR_TEMPERATURE: 25}, "set_temp"),
        ("async_set_humidity", {"humidity": 55}, "set_humidity"),
        ("async_set_hvac_mode", {"hvac_mode": HVACMode.COOL}, "set_mode"),
        ("async_set_hvac_mode", {"hvac_mode": HVACMode.OFF}, "set_power_on"),
        ("async_set_fan_mode", {"fan_mode": FAN_HIGH}, "set_fanspeed"),
        ("async_set_swing_mode", {"swing_mode": SWING_OFF}, "set_h_louver_swing"),
        ("async_turn_on", {}, "set_power_on"),
        ("async_turn_off", {}, "set_power_on"),
    ],
)
async def test_request_failed(
    mock_aircon: MagicMock, method: str, args: dict, setter: str
) -> None:
    """Test a rejected command raises an error for the user."""
    getattr(mock_aircon, setter).return_value = False

    with pytest.raises(HomeAssistantError):
        await getattr(AirConEntity(mock_aircon), method)(**args)


async def test_turn_on_failed_after_mode_change(mock_aircon: MagicMock) -> None:
    """Test a failed power-on after a mode change is reported."""
    mock_aircon.get_power_on.return_value = False
    mock_aircon.set_power_on.return_value = False

    with pytest.raises(HomeAssistantError):
        await AirConEntity(mock_aircon).async_set_hvac_mode(HVACMode.HEAT)
    mock_aircon.set_mode.assert_awaited_once_with(Mode.Heat)
