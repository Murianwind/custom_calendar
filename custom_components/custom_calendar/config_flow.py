import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, CONF_UNIQUE_ID, MAX_DAYS, DEFAULT_DAYS

class CustomCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        calendar_entities = self.hass.states.async_entity_ids("calendar")
        
        if user_input is not None:
            # Unique ID 중복 체크
            await self.async_set_unique_id(user_input[CONF_UNIQUE_ID])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(title=user_input["name"], data=user_input)

        entity_list = {eid: f"{self.hass.states.get(eid).attributes.get('friendly_name', eid)} ({eid})" 
                       for eid in calendar_entities}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_UNIQUE_ID): str, # 수동 입력 ID
                vol.Required(CONF_CAL_ID): vol.In(entity_list),
                vol.Required("name"): str,
                vol.Optional(CONF_SEARCH, default=""): str,
                vol.Optional(CONF_OFFSET, default="!!"): str,
                vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=MAX_DAYS)
                ),
            }),
            errors=errors,
            description_placeholders={"max_days": str(MAX_DAYS)}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CustomCalendarOptionsFlowHandler(config_entry)

class CustomCalendarOptionsFlowHandler(config_entries.OptionsFlow):
    """설정된 센서를 수정하는 로직"""
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # 기존 값들을 기본값으로 불러옴
        options = self.config_entry.options
        data = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_SEARCH, default=options.get(CONF_SEARCH, data.get(CONF_SEARCH))): str,
                vol.Optional(CONF_OFFSET, default=options.get(CONF_OFFSET, data.get(CONF_OFFSET))): str,
                vol.Optional(CONF_DAYS, default=options.get(CONF_DAYS, data.get(CONF_DAYS))): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=MAX_DAYS)
                ),
            })
        )
