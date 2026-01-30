"""Support for TPMS sensors."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from .tpms_parser import TPMSSensor, SensorUpdate, TPMSBluetoothDeviceData

from homeassistant import config_entries
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothProcessorCoordinator,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.components.bluetooth.const import DOMAIN as BLUETOOTH_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.sensor import sensor_device_info_to_hass_device_info

from .const import DOMAIN
from .device import device_key_to_bluetooth_entity_key

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    TPMSSensor.PRESSURE: SensorEntityDescription(
        key=TPMSSensor.PRESSURE,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
    ),
    TPMSSensor.TEMPERATURE: SensorEntityDescription(
        key=TPMSSensor.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    TPMSSensor.BATTERY: SensorEntityDescription(
        key=TPMSSensor.BATTERY,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
    ),
    TPMSSensor.VOLTAGE: SensorEntityDescription(
        key=TPMSSensor.VOLTAGE,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    TPMSSensor.SIGNAL_STRENGTH: SensorEntityDescription(
        key=TPMSSensor.SIGNAL_STRENGTH,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    TPMSSensor.DATA_AGE: SensorEntityDescription(
        key=TPMSSensor.DATA_AGE,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:clock-outline",
    ),
}


def sensor_update_to_bluetooth_data_update(
    sensor_update: SensorUpdate,
) -> PassiveBluetoothDataUpdate:
    """Convert a sensor update to a bluetooth data update."""
    return PassiveBluetoothDataUpdate(
        devices={
            device_id: sensor_device_info_to_hass_device_info(device_info)
            for device_id, device_info in sensor_update.devices.items()
        },
        entity_descriptions={
            device_key_to_bluetooth_entity_key(device_key): SENSOR_DESCRIPTIONS[
                device_key.key
            ]
            for device_key in sensor_update.entity_descriptions
        },
        entity_data={
            device_key_to_bluetooth_entity_key(device_key): sensor_values.native_value
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
        entity_names={
            device_key_to_bluetooth_entity_key(device_key): sensor_values.name
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TPMS BLE sensors."""
    coordinator: PassiveBluetoothProcessorCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    device_data: TPMSBluetoothDeviceData = hass.data[DOMAIN][f"{entry.entry_id}_data"]

    processor = PassiveBluetoothDataProcessor(sensor_update_to_bluetooth_data_update)

    # Track whether data age sensor has been created
    data_age_sensor_created = False

    def _async_add_entities_with_data_age(entities: list) -> None:
        """Add entities and create data age sensor on first update."""
        nonlocal data_age_sensor_created
        # Add the regular TPMS entities
        async_add_entities(entities)
        # Create data age sensor once we have device info
        if not data_age_sensor_created and processor.devices:
            data_age_sensor_created = True

            # Get base device info from processor for manufacturer/model
            base_info = next(iter(processor.devices.values()), {})

            # Build device_info with identifiers/connections to link to the
            # same device as the other TPMS sensors
            device_info: DeviceInfo = {
                "identifiers": {(BLUETOOTH_DOMAIN, coordinator.address)},
                "connections": {(CONNECTION_BLUETOOTH, coordinator.address)},
            }
            if manufacturer := base_info.get("manufacturer"):
                device_info["manufacturer"] = manufacturer
            if model := base_info.get("model"):
                device_info["model"] = model

            # Get device name from registry - prefer user-customized name
            dev_reg = dr.async_get(hass)
            device = dev_reg.async_get_device(
                identifiers={(BLUETOOTH_DOMAIN, coordinator.address)}
            )
            if device:
                entity_device_name = device.name_by_user or device.name
            else:
                entity_device_name = base_info.get(
                    "name", f"TPMS {coordinator.address[-5:].replace(':', '')}"
                )

            data_age_sensor = TPMSDataAgeSensorEntity(
                hass, coordinator, device_data, device_info, entity_device_name
            )
            async_add_entities([data_age_sensor])

    entry.async_on_unload(
        processor.async_add_entities_listener(
            TPMSBluetoothSensorEntity, _async_add_entities_with_data_age
        )
    )
    entry.async_on_unload(
        coordinator.async_register_processor(processor, SensorEntityDescription)
    )


class TPMSBluetoothSensorEntity(
    PassiveBluetoothProcessorEntity,
    SensorEntity,
):
    """Representation of a TPMS sensor."""

    @property
    def native_value(self) -> str | int | None:
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        The sensor is only created when the device is seen.

        Since these are sleepy devices which stop broadcasting
        when not in use, we can't rely on the last update time
        so once we have seen the device we always return True.
        """
        return True

    @property
    def assumed_state(self) -> bool:
        """Return True if the device is no longer broadcasting."""
        return not self.processor.available


class TPMSDataAgeSensorEntity(SensorEntity):
    """Representation of a TPMS data age sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: PassiveBluetoothProcessorCoordinator,
        device_data: TPMSBluetoothDeviceData,
        device_info: DeviceInfo | None,
        device_name: str,
    ) -> None:
        """Initialize the data age sensor."""
        self.hass = hass
        self._coordinator = coordinator
        self._device_data = device_data
        self._attr_unique_id = f"{coordinator.address}_data_age_v2"
        self._attr_name = f"{device_name} Data Age"
        self._attr_device_info = device_info
        self._unsub_timer: Callable[[], None] | None = None

    @property
    def native_value(self) -> int | None:
        """Return the data age in minutes."""
        if self._device_data.last_update_time is None:
            return None

        age_seconds = (
            datetime.now(timezone.utc) - self._device_data.last_update_time
        ).total_seconds()

        return int(age_seconds // 60)

    @property
    def available(self) -> bool:
        """Return True if we have received at least one update."""
        return self._device_data.last_update_time is not None

    async def async_added_to_hass(self) -> None:
        """Register timer when entity is added."""
        await super().async_added_to_hass()

        async def _async_update_data_age(now: datetime) -> None:
            """Trigger state update for data age."""
            self.async_write_ha_state()

        self._unsub_timer = async_track_time_interval(
            self.hass,
            _async_update_data_age,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up timer when entity is removed."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        await super().async_will_remove_from_hass()
