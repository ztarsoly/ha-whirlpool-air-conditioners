"""Tests for the select platform."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from whirlpool.aircon import SETTING_SLEEP_MODE

from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

ENTITY_ID = "select.living_room_sleep_mode"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("0", "off"),
        ("1", "adults"),
        ("2", "elderly"),
        ("3", "teens"),
        ("4", "children"),
        ("9", STATE_UNKNOWN),
    ],
)
async def test_state(
    hass: HomeAssistant,
    setup_integration: Callable,
    mock_aircon: MagicMock,
    raw_value: str,
    expected: str,
) -> None:
    """Test the sleep mode is read from the appliance setting."""
    # pylint: disable-next=protected-access
    mock_aircon._get_attribute.side_effect = {SETTING_SLEEP_MODE: raw_value}.get
    await setup_integration()

    state = hass.states.get(ENTITY_ID)
    assert state.state == expected
    assert state.attributes[ATTR_OPTIONS] == [
        "off",
        "adults",
        "elderly",
        "teens",
        "children",
    ]


async def test_select_option(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test choosing a sleep mode sends its setting value."""
    await setup_integration()

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "children"},
        blocking=True,
    )

    mock_aircon.send_attributes.assert_awaited_once_with({SETTING_SLEEP_MODE: "4"})


async def test_not_created_when_unsupported(
    hass: HomeAssistant, setup_integration: Callable, mock_aircon: MagicMock
) -> None:
    """Test no sleep mode entity for units without that setting."""
    mock_aircon.has_attribute.side_effect = lambda attr: attr != SETTING_SLEEP_MODE
    await setup_integration()

    assert hass.states.get(ENTITY_ID) is None
