import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    DOMAIN, CONF_ROOM_NAME, CONF_INDOOR_TEMP_SENSORS, CONF_INDOOR_HUMIDITY_SENSORS,
    CONF_AGGREGATION_METHOD, AGGREGATION_METHODS, CONF_OUTDOOR_SOURCE_TYPE,
    SOURCE_WEATHER, SOURCE_SENSORS, CONF_OUTDOOR_TEMP_SENSOR,
    CONF_OUTDOOR_HUMIDITY_SENSOR, CONF_WEATHER_ENTITY, CONF_PC_SENSOR, CONF_PC_THRESHOLD
)

class SmartClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.data = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_outdoor()

        schema = vol.Schema({
            vol.Required(CONF_ROOM_NAME): str,
            vol.Required(CONF_INDOOR_TEMP_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Optional(CONF_INDOOR_HUMIDITY_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Required(CONF_AGGREGATION_METHOD, default="Average"): vol.In(AGGREGATION_METHODS)
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_outdoor(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_pc_monitor()

        schema = vol.Schema({
            vol.Required(CONF_OUTDOOR_SOURCE_TYPE, default=SOURCE_WEATHER): vol.In([SOURCE_WEATHER, SOURCE_SENSORS]),
            vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_OUTDOOR_TEMP_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_OUTDOOR_HUMIDITY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
        })
        return self.async_show_form(step_id="outdoor", data_schema=schema)

    async def async_step_pc_monitor(self, user_input=None):
        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(title=self.data[CONF_ROOM_NAME], data=self.data)

        schema = vol.Schema({
            vol.Optional(CONF_PC_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_PC_THRESHOLD, default=25.0): vol.Coerce(float)
        })
        return self.async_show_form(step_id="pc_monitor", data_schema=schema)