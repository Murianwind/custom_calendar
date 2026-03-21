import logging
from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, CONF_UNIQUE_ID, MAX_DAYS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    # Data와 Options를 통합하여 최신값 반영
    config = {**config_entry.data, **config_entry.options}
    async_add_entities([FilteredCalendar(hass, config, config_entry.entry_id)], True)

class FilteredCalendar(CalendarEntity):
    def __init__(self, hass, data, entry_id):
        self.hass = hass
        self._parent_id = data[CONF_CAL_ID]
        self._attr_name = data["name"]
        self._search = data.get(CONF_SEARCH, "").lower()
        self._offset_char = data.get(CONF_OFFSET, "!!")
        self._days = min(data.get(CONF_DAYS, 30), MAX_DAYS)
        self._attr_unique_id = data[CONF_UNIQUE_ID] # 수동 입력한 Unique ID 사용
        
        self._event: CalendarEvent | None = None
        self._offset_reached = False

        # 기기 정보 설정 (모든 엔티티를 하나의 'Custom Calendar' 기기로 묶음)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "custom_calendar_device")}, # 고정 식별자
            name="Custom Calendar",
            manufacturer="My Home Assistant",
            model="Multi-Filter Calendar",
        )

    @property
    def unique_id(self): return self._attr_unique_id

    @property
    def event(self) -> CalendarEvent | None: return self._event

    @property
    def extra_state_attributes(self):
        if not self._event: return {"offset_reached": False, "friendly_name": self._attr_name}
        
        start, end = self._event.start, self._event.end
        start_str = start.strftime("%Y-%m-%d %H:%M:%S") if isinstance(start, datetime) else f"{start.isoformat()} 00:00:00"
        end_str = end.strftime("%Y-%m-%d %H:%M:%S") if isinstance(end, datetime) else f"{end.isoformat()} 00:00:00"

        return {
            "message": self._event.summary,
            "all_day": self._event.all_day,
            "start_time": start_str,
            "end_time": end_str,
            "location": self._event.location or "",
            "description": self._event.description or "",
            "offset_reached": self._offset_reached,
            "friendly_name": self._event.summary
        }

    def _parse_event_time(self, raw_time_str):
        if not raw_time_str: return None
        if len(raw_time_str) == 10: return dt_util.parse_date(raw_time_str)
        parsed_dt = dt_util.parse_datetime(raw_time_str)
        if parsed_dt and parsed_dt.tzinfo is None: parsed_dt = dt_util.as_local(parsed_dt)
        return parsed_dt

    async def async_get_events(self, hass, start_date, end_date):
        try:
            response = await self.hass.services.async_call(
                "calendar", "get_events",
                {"start_date_time": start_date.isoformat(), "end_date_time": end_date.isoformat()},
                target={"entity_id": self._parent_id}, blocking=True, return_response=True,
            )
            raw_events = response.get(self._parent_id, {}).get("events", [])
            matching_events = []
            for e in raw_events:
                summary = e.get("summary", "")
                if not self._search or self._search in summary.lower():
                    e_start, e_end = self._parse_event_time(e.get("start")), self._parse_event_time(e.get("end"))
                    if e_start and e_end:
                        matching_events.append(CalendarEvent(summary=summary, start=e_start, end=e_end, location=e.get("location"), description=e.get("description")))
            return matching_events
        except: return []

    async def async_update(self):
        start, end = dt_util.now(), dt_util.now() + timedelta(days=self._days)
        try:
            response = await self.hass.services.async_call(
                "calendar", "get_events",
                {"start_date_time": start.isoformat(), "end_date_time": end.isoformat()},
                target={"entity_id": self._parent_id}, blocking=True, return_response=True,
            )
            raw_events = response.get(self._parent_id, {}).get("events", [])
            matching_events = []
            for e in raw_events:
                summary = e.get("summary", "")
                if not self._search or self._search in summary.lower():
                    e_start, e_end = self._parse_event_time(e.get("start")), self._parse_event_time(e.get("end"))
                    if e_start and e_end:
                        matching_events.append(CalendarEvent(summary=summary, start=e_start, end=e_end, location=e.get("location"), description=e.get("description")))
            if not matching_events:
                self._event, self._offset_reached = None, False
            else:
                def get_sort_key(ev): return ev.start if isinstance(ev.start, datetime) else dt_util.as_local(datetime.combine(ev.start, datetime.min.time()))
                matching_events.sort(key=get_sort_key)
                self._event = matching_events[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)
        except: pass

    def _check_offset(self, summary, start_time):
        if self._offset_char not in summary: return False
        try:
            digits = "".join(filter(str.isdigit, summary.split(self._offset_char)[-1]))
            if not digits: return False
            start_dt = start_time if isinstance(start_time, datetime) else dt_util.as_local(datetime.combine(start_time, datetime.min.time()))
            return dt_util.now() >= (start_dt - timedelta(minutes=int(digits)))
        except: return False
