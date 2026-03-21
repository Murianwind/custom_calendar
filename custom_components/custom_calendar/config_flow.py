import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import (
    DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, 
    CONF_DAYS, CONF_UNIQUE_ID, DEFAULT_DAYS, MAX_DAYS
)

class CustomCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """최초 설치 시 설정 흐름."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_CAL_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar")
            ),
            vol.Required("name"): str,
            vol.Required(CONF_UNIQUE_ID): str,
            vol.Optional(CONF_SEARCH, default=""): str,
            vol.Optional(CONF_OFFSET, default="!!"): str,
            vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=MAX_DAYS)
            ),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """설정 수정(Options) 화면으로 연결."""
        return CustomCalendarOptionsFlowHandler(config_entry)


class CustomCalendarOptionsFlowHandler(config_entries.OptionsFlow):
    """설치 후 '구성(Configure)' 버튼을 눌렀을 때의 흐름."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # 수정된 내용을 저장 (이 순간 __init__.py의 update_listener가 작동함)
            return self.async_create_entry(title="", data=user_input)

        # 기존 설정값(data)과 수정값(options) 병합
        options = {**self.config_entry.data, **self.config_entry.options}

        data_schema = vol.Schema({
            # 원본 달력을 다시 선택할 수 있도록 추가됨
            vol.Required(CONF_CAL_ID, default=options.get(CONF_CAL_ID)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar")
            ),
            vol.Optional(CONF_SEARCH, default=options.get(CONF_SEARCH, "")): str,
            vol.Optional(CONF_OFFSET, default=options.get(CONF_OFFSET, "!!")): str,
            vol.Optional(CONF_DAYS, default=options.get(CONF_DAYS, DEFAULT_DAYS)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=MAX_DAYS)
            ),
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
