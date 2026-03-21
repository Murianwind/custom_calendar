import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, MAX_DAYS, DEFAULT_DAYS

class CustomCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            # 입력값 검증: 1일 미만이거나 365일 초과인 경우
            if user_input[CONF_DAYS] < 1 or user_input[CONF_DAYS] > MAX_DAYS:
                errors["base"] = "range_exceeded"
            else:
                return self.async_create_entry(title=user_input["name"], data=user_input)

        # UI 스키마 정의
        return self.show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CAL_ID): str,
                vol.Required("name"): str,
                vol.Optional(CONF_SEARCH, default=""): str,
                vol.Optional(CONF_OFFSET, default="!!"): str,
                vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=MAX_DAYS)
                ),
            }),
            errors=errors,
            description_placeholders={"max_days": str(MAX_DAYS)} # UI 메시지에 사용
        )
