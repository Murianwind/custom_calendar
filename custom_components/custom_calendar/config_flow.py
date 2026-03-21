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

        # [수정 1] 번역 파일의 {max_days} 변수를 위해 description_placeholders 추가
        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={"max_days": MAX_DAYS}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """설정 수정(Options) 화면으로 연결."""
        return CustomCalendarOptionsFlowHandler(config_entry)


class CustomCalendarOptionsFlowHandler(config_entries.OptionsFlow):
    """설치 후 '구성(Configure)' 버튼을 눌렀을 때의 흐름."""

    def __init__(self, config_entry):
        # [수정 2] HA 최신 버전 충돌 방지: self.config_entry 대신 self._entry 사용
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # 수정된 내용을 저장
            return self.async_create_entry(title="", data=user_input)

        # 기존 설정값(data)과 수정값(options) 병합 (self._entry 사용)
        options = {**self._entry.data, **self._entry.options}

        data_schema = vol.Schema({
            vol.Required(CONF_CAL_ID, default=options.get(CONF_CAL_ID)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar")
            ),
            vol.Optional(CONF_SEARCH, default=options.get(CONF_SEARCH, "")): str,
            vol.Optional(CONF_OFFSET, default=options.get(CONF_OFFSET, "!!")): str,
            vol.Optional(CONF_DAYS, default=options.get(CONF_DAYS, DEFAULT_DAYS)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=MAX_DAYS)
            ),
        })

        # [수정 1] 구성 화면에서도 {max_days} 변수 전달
        return self.async_show_form(
            step_id="init", 
            data_schema=data_schema,
            description_placeholders={"max_days": MAX_DAYS}
        )
