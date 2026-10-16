"""Tests for the Ai TPMS (AI-8000) decoder, Type G.

The two load-bearing frames are REAL captured frames (2026-10-16, four
sensors): pressure field 0x0092 = no overpressure (ambient air) and
0x01AE = a mounted tyre, where the car's factory sensor on the same
wheel showed 1.944 bar. The remaining bytes of those two captures (status, battery,
temperature) are not documented, so the tests pin the FORMAT around
them: byte 0 status, byte 1 battery V×10, byte 2 temperature °C,
bytes 3-4 pressure big-endian 0.1 psi absolute.
"""
from __future__ import annotations

import importlib.util
import struct
from pathlib import Path

from home_assistant_bluetooth import BluetoothServiceInfo

# Load parser.py directly: the package __init__ pulls in homeassistant,
# which these tests don't need — the parser itself runs on the three
# bluetooth helper libraries only.
_PARSER_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components" / "tpms_ble" / "tpms_parser" / "parser.py"
)
_spec = importlib.util.spec_from_file_location("tpms_ble_parser", _PARSER_PATH)
_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parser)

TPMSSensor = _parser.TPMSSensor
TPMSBluetoothDeviceData = _parser.TPMSBluetoothDeviceData
battery_percentage = _parser.battery_percentage

AI_ADDRESS = "12:30:AF:11:22:33"


def ai_info(
    company_id: int,
    payload: bytes,
    address: str = AI_ADDRESS,
    name: str = "AI-8000",
) -> BluetoothServiceInfo:
    """The advertisement of an AI-8000: measurements inside the id."""
    return BluetoothServiceInfo(
        name=name,
        address=address,
        rssi=-60,
        manufacturer_data={company_id: payload},
        service_data={},
        service_uuids=[],
        source="local",
    )


def values_of(info: BluetoothServiceInfo) -> dict[str, object]:
    parser = TPMSBluetoothDeviceData()
    update = parser.update(info)
    return {
        key.key: value.native_value
        for key, value in update.entity_values.items()
    }


# The two captured frames: the 16-bit id is little-endian, so its low
# byte is frame byte 0 (status) and its high byte frame byte 1 (battery).
# id = status | battery << 8 → 0x2000 = status 0x00, battery 0x20 (3.2 V).
MOUNTED_TYRE = (0x2000, b"\x15\x01\xAE")  # pressure 0x01AE, 21 °C
AMBIENT = (0x2000, b"\x0F\x00\x92")  # pressure 0x0092, 15 °C


def test_mounted_tyre_real_frame() -> None:
    """0x01AE = 43.0 psi absolute − 14.696 ambient = 1.951 bar gauge."""
    values = values_of(ai_info(*MOUNTED_TYRE))
    assert values[TPMSSensor.PRESSURE] == 1.951
    assert values[TPMSSensor.TEMPERATURE] == 21
    assert values[TPMSSensor.VOLTAGE] == 3.2
    assert values[TPMSSensor.BATTERY] == battery_percentage(3.2)


def test_ambient_real_frame_is_zero_gauge() -> None:
    """0x0092 = 14.6 psi absolute — below ambient, gauge clamps to 0."""
    values = values_of(ai_info(*AMBIENT))
    assert values[TPMSSensor.PRESSURE] == 0.0


def test_status_bits_rotate_pressure_stays() -> None:
    """The status bits (0-3) rotate between messages — pressure must not."""
    status, payload = MOUNTED_TYRE
    for rotated_status in (0x2001, 0x2002, 0x2003):
        values = values_of(ai_info(rotated_status, payload))
        assert values[TPMSSensor.PRESSURE] == 1.951


def test_detection_by_name() -> None:
    """A sensor named AI-* is recognized regardless of its address."""
    values = values_of(ai_info(*MOUNTED_TYRE, address="00:11:22:33:44:55"))
    assert values[TPMSSensor.PRESSURE] == 1.951


def test_detection_by_address() -> None:
    """A 12:30:AF sensor is recognized regardless of its name."""
    values = values_of(ai_info(*MOUNTED_TYRE, name="something else"))
    assert values[TPMSSensor.PRESSURE] == 1.951


def test_wrong_payload_length_is_refused() -> None:
    """5 bytes total is the frame law: 2 id bytes + 3 payload bytes."""
    values = values_of(ai_info(0x0020, b"\x15\x01\xAE\xFF"))
    assert TPMSSensor.PRESSURE not in values
    parser = TPMSBluetoothDeviceData()
    assert not parser.supported(ai_info(0x0020, b"\x15\x01\xAE\xFF"))


def test_detection_does_not_hijack_existing_types() -> None:
    """TypeA (company 256, 16 bytes) still routes to its own parser."""
    type_a_payload = b"\x00" * 6 + struct.pack("=iib?", 250000, 2150, 85, False)
    values = values_of(
        BluetoothServiceInfo(
            name="TIRE",
            address="AA:BB:CC:DD:EE:FF",
            rssi=-60,
            manufacturer_data={256: type_a_payload},
            service_data={},
            service_uuids=[],
            source="local",
        )
    )
    assert values[TPMSSensor.PRESSURE] == 2.5
    assert values[TPMSSensor.TEMPERATURE] == 21.5
    assert values[TPMSSensor.BATTERY] == 85
