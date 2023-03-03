"""Support for TPMS devices."""
from __future__ import annotations

from .tpms_parser import DeviceKey

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothEntityKey,
)


def device_key_to_bluetooth_entity_key(
    device_key: DeviceKey,
) -> PassiveBluetoothEntityKey:
    """Convert a device key to an entity key."""
    return PassiveBluetoothEntityKey(device_key.key, device_key.device_id)
