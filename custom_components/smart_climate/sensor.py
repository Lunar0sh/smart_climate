import statistics
import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.const import UnitOfTemperature
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, CONF_ROOM_NAME, CONF_INDOOR_TEMP_SENSORS, CONF_AGGREGATION_METHOD,
    CONF_WEATHER_ENTITY, CONF_OUTDOOR_SOURCE_TYPE, SOURCE_WEATHER
)


async def async_setup_entry(hass, entry, async_add_entities):
    room_name = entry.data[CONF_ROOM_NAME]
    temp_sensors = entry.data[CONF_INDOOR_TEMP_SENSORS]
    agg_method = entry.data[CONF_AGGREGATION_METHOD]

    entities = []

    # Feature 3: Virtual Aggregated Room Sensor
    agg_sensor = VirtualAggregatedSensor(room_name, temp_sensors, agg_method, hass)
    entities.append(agg_sensor)

    # Feature 4: Daily Min/Max Sensor
    entities.append(DailyMinMaxSensor(room_name, agg_sensor.entity_id, "min", hass))
    entities.append(DailyMinMaxSensor(room_name, agg_sensor.entity_id, "max", hass))

    # Feature 7: Forecast Ventilation Curve (if weather entity is used)
    if entry.data.get(CONF_OUTDOOR_SOURCE_TYPE) == SOURCE_WEATHER and entry.data.get(CONF_WEATHER_ENTITY):
        entities.append(
            OptimalVentilationWindowSensor(room_name, entry.data[CONF_WEATHER_ENTITY], agg_sensor.entity_id, hass))

    async_add_entities(entities)


class VirtualAggregatedSensor(SensorEntity):
    def __init__(self, room_name, sensors, method, hass):
        self.hass = hass
        self._attr_name = f"{room_name} Aggregated Temperature"
        self._attr_unique_id = f"{room_name}_agg_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._sensors = sensors
        self._method = method
        self._state = None

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._sensors, self._async_update_state
            )
        )

    async def _async_update_state(self, event):
        values = []
        for entity_id in self._sensors:
            state = self.hass.states.get(entity_id)
            if state and state.state not in ['unknown', 'unavailable']:
                try:
                    values.append(float(state.state))
                except ValueError:
                    pass

        if not values:
            return

        if self._method == "Average":
            self._state = round(statistics.mean(values), 1)
        elif self._method == "Median":
            self._state = round(statistics.median(values), 1)
        elif self._method == "Min":
            self._state = min(values)
        elif self._method == "Max":
            self._state = max(values)

        self._attr_native_value = self._state
        self.async_write_ha_state()


class DailyMinMaxSensor(SensorEntity):
    def __init__(self, room_name, source_entity_id, mode, hass):
        self.hass = hass
        self._source_entity_id = source_entity_id
        self._mode = mode
        self._attr_name = f"{room_name} Daily {mode.capitalize()} Temperature"
        self._attr_unique_id = f"{room_name}_daily_{mode}_temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._state = None
        self._last_reset = dt_util.now().date()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity_id], self._async_update_state
            )
        )

    async def _async_update_state(self, event):
        current_date = dt_util.now().date()
        if current_date > self._last_reset:
            self._state = None
            self._last_reset = current_date

        new_state = event.data.get("new_state")
        if new_state and new_state.state not in ['unknown', 'unavailable']:
            try:
                val = float(new_state.state)
                if self._state is None:
                    self._state = val
                else:
                    if self._mode == "min" and val < self._state:
                        self._state = val
                    elif self._mode == "max" and val > self._state:
                        self._state = val
            except ValueError:
                pass

        self._attr_native_value = self._state
        self.async_write_ha_state()


class OptimalVentilationWindowSensor(SensorEntity):
    def __init__(self, room_name, weather_entity, room_temp_entity, hass):
        self.hass = hass
        self._weather_entity = weather_entity
        self._room_temp_entity = room_temp_entity
        self._attr_name = f"{room_name} Optimal Ventilation Window"
        self._attr_unique_id = f"{room_name}_vent_window"
        self._attr_native_value = "Calculating..."

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_time_interval(self.hass, self._update_forecast, datetime.timedelta(minutes=30))
        )

    async def _update_forecast(self, _):
        # Using modern HA weather.get_forecasts service
        try:
            response = await self.hass.services.async_call(
                "weather", "get_forecasts",
                {"entity_id": self._weather_entity, "type": "hourly"},
                blocking=True, return_response=True
            )
            forecast_data = response.get(self._weather_entity, {}).get("forecast", [])

            room_state = self.hass.states.get(self._room_temp_entity)
            if not room_state or room_state.state in ['unknown', 'unavailable']:
                return

            room_temp = float(room_state.state)

            # Find continuous blocks where outdoor < indoor
            good_times = [f for f in forecast_data if float(f.get("temperature", 99)) < room_temp]

            if good_times:
                start_time = dt_util.parse_datetime(good_times[0]["datetime"]).strftime("%H:%M")
                end_time = dt_util.parse_datetime(good_times[-1]["datetime"]).strftime("%H:%M")
                self._attr_native_value = f"Open {start_time}, Close {end_time}"
            else:
                self._attr_native_value = "No optimal window"

            self.async_write_ha_state()
        except Exception as e:
            pass  # Keep previous state if service fails