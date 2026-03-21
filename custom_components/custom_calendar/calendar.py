import logging
from datetime import timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util
from .const import CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, MAX_DAYS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([FilteredCalendar(hass, config_entry.data, config_entry.entry_id)], True)

class FilteredCalendar(CalendarEntity):
    def __init__(self, hass, data, entry_id):
        self.hass = hass
        self._parent_id = data[CONF_CAL_ID]
        self._attr_name = data["name"]
        self._search = data.get(CONF_SEARCH, "").lower()
        self._offset_char = data.get(CONF_OFFSET, "!!")
        self._days = min(data.get(CONF_DAYS, 30), MAX_DAYS)
        self._attr_unique_id = entry_id
        self._event = None
        self._offset_reached = False

    @property
    def name(self): return self._attr_name

    @property
    def event(self) -> CalendarEvent | None: return self._event

    @property
    def extra_state_attributes(self):
        if not self._event: return {"offset_reached": False}
        return {
            "message": self._event.summary,
            "all_day": self._event.all_day,
            "start_time": self._event.start,
            "end_time": self._event.end,
            "location": self._event.location or "",
            "description": self._event.description or "",
            "offset_reached": self._offset_reached,
        }

    async def async_get_events(self, hass, start_date, end_date):
        events = await self.hass.components.calendar.async_get_events(self._parent_id, start_date, end_date)
        return [e for e in events if not self._search or self._search in e.summary.lower()]

    async def async_update(self):
        start = dt_util.now()
        end = start + timedelta(days=self._days)
        try:
            events = await self.hass.components.calendar.async_get_events(self._parent_id, start, end)
            matching = [e for e in events if not self._search or self._search in e.summary.lower()]
            if not matching:
                self._event = None
                self._offset_reached = False
            else:
                self._event = matching[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)
        except Exception as e:
            _LOGGER.error("Update failed: %s", e)

    def _check_offset(self, summary, start_time):
        if self._offset_char not in summary: return False
        try:
            offset_val = int("".join(filter(str.isdigit, summary.split(self._offset_char)[1])))
            return dt_util.now() >= (start_time - timedelta(minutes=offset_val))
        except: return False
