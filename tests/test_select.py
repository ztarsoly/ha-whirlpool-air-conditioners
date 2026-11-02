"""Tests for the select platform."""

from unittest.mock import MagicMock

import pytest
from whirlpool.httpapi.aircon import SETTING_SLEEP_MODE, Aircon as HttpAircon

from homeassistant.exceptions import HomeAssistantError

from custom_components.whirlpool_air_conditioners import select
from custom_components.whirlpool_air_conditioners.select import (
    WhirlpoolSleepModeSelect,
)

from .conftest import MOCK_SAID, setup_platform


async def test_setup_entry(
    mock_aircon: MagicMock, mock_aws_aircon: MagicMock
) -> None:
    """Test the sleep mode select is only added for units that support it."""
    unsupported = MagicMock(spec=HttpAircon)
    unsupported.has_attribute.side_effect = lambda attr: attr != SETTING_SLEEP_MODE

    entities = await setup_platform(
        select, [mock_aircon, unsupported, mock_aws_aircon]
    )

    assert len(entities) == 1
    assert entities[0].unique_id == f"{MOCK_SAID}-sleep_mode"
    assert entities[0].translation_key == "sleep_mode"
    assert entities[0].options == ["off", "adults", "elderly", "teens", "children"]


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("0", "off"),
        ("1", "adults"),
        ("2", "elderly"),
        ("3", "teens"),
        ("4", "children"),
        ("9", None),
        (None, None),
    ],
)
def test_current_option(
    mock_aircon: MagicMock, raw_value: str | None, expected: str | None
) -> None:
    """Test the sleep mode is read from the appliance setting."""
    # pylint: disable-next=protected-access
    mock_aircon._get_attribute.side_effect = {SETTING_SLEEP_MODE: raw_value}.get

    assert WhirlpoolSleepModeSelect(mock_aircon).current_option == expected


@pytest.mark.parametrize(
    ("option", "raw_value"),
    [("off", "0"), ("adults", "1"), ("elderly", "2"), ("teens", "3"), ("children", "4")],
)
async def test_select_option(
    mock_aircon: MagicMock, option: str, raw_value: str
) -> None:
    """Test choosing a sleep mode sends its setting value."""
    await WhirlpoolSleepModeSelect(mock_aircon).async_select_option(option)

    mock_aircon.send_attributes.assert_awaited_once_with(
        {SETTING_SLEEP_MODE: raw_value}
    )


async def test_select_option_failed(mock_aircon: MagicMock) -> None:
    """Test a rejected command raises an error for the user."""
    mock_aircon.send_attributes.return_value = False

    with pytest.raises(HomeAssistantError):
        await WhirlpoolSleepModeSelect(mock_aircon).async_select_option("adults")
