import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, MAX_DAYS, DEFAULT_DAYS

class CustomCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Custom Calendar의 설정 흐름을 관리합니다."""

    async def async_step_user(self, user_input=None):
        errors = {}

        # 1. 시스템에서 모든 calendar 엔티티 목록 가져오기
        calendar_entities = self.hass.states.async_entity_ids("calendar")
        
        if not calendar_entities:
            errors["base"] = "no_calendars_found"

        if user_input is not None:
            # 입력값 검증 (날짜 범위)
            if user_input[CONF_DAYS] < 1 or user_input[CONF_DAYS] > MAX_DAYS:
                errors["base"] = "range_exceeded"
            else:
                return self.async_create_entry(title=user_input["name"], data=user_input)

        # 2. 드롭다운 구성을 위한 딕셔너리 생성 {엔티티_ID: "친숙한 이름 (엔티티_ID)"}
        entity_list = {}
        for entity_id in calendar_entities:
            state = self.hass.states.get(entity_id)
            friendly_name = state.attributes.get("friendly_name", entity_id) if state else entity_id
            entity_list[entity_id] = f"{friendly_name} ({entity_id})"

        # 3. UI 스키마 정의 (vol.In 사용으로 드롭다운 생성)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
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
