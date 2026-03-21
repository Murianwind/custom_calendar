import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, MAX_DAYS, DEFAULT_DAYS

class CustomCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        calendar_entities = self.hass.states.async_entity_ids("calendar")
        
        if not calendar_entities:
            errors["base"] = "no_calendars_found"

        if user_input is not None:
            if user_input[CONF_DAYS] < 1 or user_input[CONF_DAYS] > MAX_DAYS:
                errors["base"] = "range_exceeded"
            else:
                return self.async_create_entry(title=user_input["name"], data=user_input)

        entity_list = {eid: f"{self.hass.states.get(eid).attributes.get('friendly_name', eid)} ({eid})" 
                       for eid in calendar_entities}

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
