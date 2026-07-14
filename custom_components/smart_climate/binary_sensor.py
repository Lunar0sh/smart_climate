import math
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN, CONF_ROOM_NAME, CONF_OUTDOOR_SOURCE_TYPE, SOURCE_WEATHER,
    CONF_OUTDOOR_TEMP_SENSOR, CONF_OUTDOOR_HUMIDITY_SENSOR, CONF_WEATHER_ENTITY,
    CONF_INDOOR_HUMIDITY_SENSORS, CONF_PC_SENSOR, CONF_PC_THRESHOLD
)


def calc_absolute_humidity(temp, rh):
    # Calculate absolute humidity (g/m^3)
    # Mass density formula utilizing standard constants
    return (13.2471 * math.pow(math.e, 17.67 * temp / (temp + 243.5)) * rh) / (273.15 + temp)


async def async_setup_entry(hass, entry, async_add_entities):
    room_name = entry.data[CONF_ROOM_NAME]

    entities = []
    # Note: For strict implementation, we track the aggregated virtual room sensor generated in sensor.py
    agg_room_temp_id = f"sensor.{room_name.lower().replace(' ', '_')}_aggregated_temperature"

    vent_sensor = VentilationRecommendationSensor(entry.data, agg_room_temp_id, hass)
    entities.append(vent_sensor)

    if entry.data.get(CONF_PC_SENSOR):
        entities.append(PCHeatWarningSensor(entry.data, agg_room_temp_id, hass))

    async_add_entities(entities)


class VentilationRecommendationSensor(BinarySensorEntity):
    def __init__(self, config_data, room_temp_id, hass):
        self.hass = hass
        self._config = config_data
        self._room_temp_id = room_temp_id
        self._attr_name = f"{config_data[CONF_ROOM_NAME]} Ventilation Recommendation"
        self._attr_unique_id = f"{config_data[CONF_ROOM_NAME]}_vent_rec"
        self._attr_device_class = BinarySensorDeviceClass.WINDOW
        self._attr_is_on = False

    async def async_added_to_hass(self):
        track_entities = [self._room_temp_id]

        if self._config.get(CONF_INDOOR_HUMIDITY_SENSORS):
            track_entities.extend(self._config[CONF_INDOOR_HUMIDITY_SENSORS])

        if self._config.get(CONF_OUTDOOR_SOURCE_TYPE) == SOURCE_WEATHER:
            track_entities.append(self._config[CONF_WEATHER_ENTITY])
        else:
            if self._config.get(CONF_OUTDOOR_TEMP_SENSOR):
                track_entities.append(self._config[CONF_OUTDOOR_TEMP_SENSOR])
            if self._config.get(CONF_OUTDOOR_HUMIDITY_SENSOR):
                track_entities.append(self._config[CONF_OUTDOOR_HUMIDITY_SENSOR])

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, track_entities, self._async_update_state
            )
        )

    async def _async_update_state(self, event):
        # Gather states
        in_temp_state = self.hass.states.get(self._room_temp_id)
        if not in_temp_state or in_temp_state.state in ['unknown', 'unavailable']:
            return
        in_temp = float(in_temp_state.state)

        out_temp = None
        out_hum = None

        # Get Outdoor Data
        if self._config.get(CONF_OUTDOOR_SOURCE_TYPE) == SOURCE_WEATHER:
            weather_state = self.hass.states.get(self._config[CONF_WEATHER_ENTITY])
            if weather_state:
                out_temp = weather_state.attributes.get("temperature")
                out_hum = weather_state.attributes.get("humidity")
        else:
            out_temp_state = self.hass.states.get(self._config.get(CONF_OUTDOOR_TEMP_SENSOR))
            if out_temp_state:
                out_temp = float(out_temp_state.state)

            out_hum_id = self._config.get(CONF_OUTDOOR_HUMIDITY_SENSOR)
            if out_hum_id:
                out_hum_state = self.hass.states.get(out_hum_id)
                if out_hum_state:
                    out_hum = float(out_hum_state.state)

        if out_temp is None:
            return

        # Get Indoor Humidity (Average if multiple)
        in_hum = None
        if self._config.get(CONF_INDOOR_HUMIDITY_SENSORS):
            hum_values = []
            for h_id in self._config[CONF_INDOOR_HUMIDITY_SENSORS]:
                h_state = self.hass.states.get(h_id)
                if h_state and h_state.state not in ['unknown', 'unavailable']:
                    hum_values.append(float(h_state.state))
            if hum_values:
                in_hum = sum(hum_values) / len(hum_values)

        # Logic
        recommendation = False

        # Feature 6 & 5 logic
        if in_hum is not None and out_hum is not None:
            # We have humidity on both sides, calculate absolute humidity
            in_ah = calc_absolute_humidity(in_temp, in_hum)
            out_ah = calc_absolute_humidity(out_temp, out_hum)

            if out_temp < in_temp and out_ah < in_ah:
                recommendation = True
        else:
            # Fallback to pure temperature
            if out_temp < in_temp:
                recommendation = True

        self._attr_is_on = recommendation
        self.async_write_ha_state()


class PCHeatWarningSensor(BinarySensorEntity):
    def __init__(self, config_data, room_temp_id, hass):
        self.hass = hass
        self._pc_sensor_id = config_data[CONF_PC_SENSOR]
        self._threshold = config_data[CONF_PC_THRESHOLD]
        self._room_temp_id = room_temp_id
        self._attr_name = f"{config_data[CONF_ROOM_NAME]} PC Heat Warning"
        self._attr_unique_id = f"{config_data[CONF_ROOM_NAME]}_pc_heat_warn"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_is_on = False

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._pc_sensor_id, self._room_temp_id], self._async_update_state
            )
        )

    async def _async_update_state(self, event):
        room_temp_state = self.hass.states.get(self._room_temp_id)
        pc_state = self.hass.states.get(self._pc_sensor_id)

        if not room_temp_state or not pc_state:
            return

        if room_temp_state.state in ['unknown', 'unavailable'] or pc_state.state in ['unknown', 'unavailable']:
            return

        room_temp = float(room_temp_state.state)

        # Assuming the PC sensor is either numeric (temp/load) or binary (on/off)
        pc_active = False
        try:
            pc_val = float(pc_state.state)
            if pc_val > 50.0:  # Arbitrary load/temp threshold for activity
                pc_active = True
        except ValueError:
            if pc_state.state.lower() in ['on', 'playing', 'active']:
                pc_active = True

        # Issue warning if room is hot and PC is active
        self._attr_is_on = bool(pc_active and (room_temp >= self._threshold))
        self.async_write_ha_state()