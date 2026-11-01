"""Tests for the shared entity base class."""

import logging
from unittest.mock import MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.whirlpool_air_conditioners.const import DOMAIN
from custom_components.whirlpool_air_conditioners.entity import WhirlpoolEntity

from .conftest import MOCK_SAID


def make_entity(aircon: MagicMock) -> WhirlpoolEntity:
    """Return an entity with state writing stubbed out."""
    entity = WhirlpoolEntity(aircon, unique_id_suffix="-test")
    entity.entity_id = "climate.living_room"
    entity.async_write_ha_state = MagicMock()
    return entity


def test_device_info_and_unique_id(mock_aircon: MagicMock) -> None:
    """Test the entity belongs to the air conditioner's device."""
    entity = WhirlpoolEntity(mock_aircon, unique_id_suffix="-display")

    assert entity.unique_id == f"{MOCK_SAID}-display"
    assert entity.device_info == {
        "identifiers": {(DOMAIN, MOCK_SAID)},
        "name": "Living room",
        "manufacturer": "Whirlpool",
        "model_id": "SPIW309A2WF",
    }


def test_device_name_falls_back_to_said(mock_aircon: MagicMock) -> None:
    """Test an appliance without a name is named after its SAID."""
    mock_aircon.name = ""

    assert WhirlpoolEntity(mock_aircon).device_info["name"] == MOCK_SAID


async def test_registers_for_updates(mock_aircon: MagicMock) -> None:
    """Test the entity listens for pushed updates while it exists."""
    entity = make_entity(mock_aircon)

    await entity.async_added_to_hass()
    callback = mock_aircon.register_attr_callback.call_args.args[0]

    await entity.async_will_remove_from_hass()
    mock_aircon.unregister_attr_callback.assert_called_once_with(callback)


async def test_update_sets_availability(
    mock_aircon: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test pushed updates set availability and log changes only once."""
    entity = make_entity(mock_aircon)
    await entity.async_added_to_hass()
    callback = mock_aircon.register_attr_callback.call_args.args[0]
    caplog.set_level(logging.INFO)

    mock_aircon.get_online.return_value = False
    callback()
    callback()
    assert entity.available is False
    assert caplog.text.count("is unavailable") == 1

    mock_aircon.get_online.return_value = True
    callback()
    callback()
    assert entity.available is True
    assert caplog.text.count("is back online") == 1

    assert entity.async_write_ha_state.call_count == 4


def test_check_service_request() -> None:
    """Test a rejected request raises a translated error."""
    WhirlpoolEntity._check_service_request(True)  # pylint: disable=protected-access

    with pytest.raises(HomeAssistantError) as err:
        WhirlpoolEntity._check_service_request(False)  # pylint: disable=protected-access
    assert err.value.translation_domain == DOMAIN
    assert err.value.translation_key == "request_failed"
