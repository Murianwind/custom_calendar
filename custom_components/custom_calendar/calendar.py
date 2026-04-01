import logging
from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util, slugify
from .const import (
    DOMAIN, CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, 
    CONF_DAYS, CONF_UNIQUE_ID, MAX_DAYS
)

_LOGGER = logging.getLogger(__name__)
SIGNAL_REFRESH = f"{DOMAIN}_refresh"

async def async_setup_entry(hass, config_entry, async_add_entities):
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
        self._attr_unique_id = data.get(CONF_UNIQUE_ID, entry_id)
        self.entity_id = f"calendar.{slugify(self._attr_unique_id)}"
        
        self._event: CalendarEvent | None = None
        self._offset_reached = False

    async def async_added_to_hass(self):
        """엔티티가 HA에 추가될 때 실행."""
        # 1. 자동 감지: 원본 달력의 상태가 변할 때 감시 (부활 감지)
        @callback
        def _async_state_changed(event):
            new_state = event.data.get("new_state")
            if new_state and new_state.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                _LOGGER.debug("%s: 원본 달력 활성화 감지, 업데이트 시작", self.entity_id)
                self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._parent_id], _async_state_changed)
        )

        # 2. 수동 서비스 대응: custom_calendar.refresh 서비스 호출 시 작동
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_REFRESH, self._force_refresh)
        )

    async def _force_refresh(self):
        """서비스 신호를 받았을 때 강제 업데이트 수행."""
        _LOGGER.debug("%s: 강제 갱신 신호를 수신했습니다.", self.entity_id)
        await self.async_update_ha_state(True)

    @property
    def name(self): return self._attr_name

    @property
    def unique_id(self): return self._attr_unique_id

    @property
    def event(self) -> CalendarEvent | None: return self._event

    @property
    def extra_state_attributes(self):
        if not self._event:
            return {"offset_reached": False, "friendly_name": self._attr_name}
        start = self._event.start
        end = self._event.end
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
        if parsed_dt and parsed_dt.tzinfo is None:
            parsed_dt = dt_util.as_local(parsed_dt)
        return parsed_dt

    async def async_get_events(self, hass, start_date, end_date):
        if self.hass.states.get(self._parent_id) is None: return []
        try:
            response = await self.hass.services.async_call(
                "calendar", "get_events",
                {"start_date_time": start_date.isoformat(), "end_date_time": end_date.isoformat()},
                target={"entity_id": self._parent_id},
                blocking=True, return_response=True,
            )
            raw_events = response.get(self._parent_id, {}).get("events", [])
            matching_events = []
            for e in raw_events:
                summary = e.get("summary", "")
                if not self._search or self._search in summary.lower():
                    e_start = self._parse_event_time(e.get("start"))
                    e_end = self._parse_event_time(e.get("end"))
                    if e_start and e_end:
                        matching_events.append(CalendarEvent(
                            summary=summary, start=e_start, end=e_end,
                            location=e.get("location"), description=e.get("description"),
                        ))
            return matching_events
        except Exception: return []

    async def async_update(self):
        if self.hass.states.get(self._parent_id) is None: return
        start = dt_util.now()
        end = start + timedelta(days=self._days)
        try:
            response = await self.hass.services.async_call(
                "calendar", "get_events",
                {"start_date_time": start.isoformat(), "end_date_time": end.isoformat()},
                target={"entity_id": self._parent_id},
                blocking=True, return_response=True,
            )
            raw_events = response.get(self._parent_id, {}).get("events", [])
            matching_events = []
            for e in raw_events:
                summary = e.get("summary", "")
                if not self._search or self._search in summary.lower():
                    e_start = self._parse_event_time(e.get("start"))
                    e_end = self._parse_event_time(e.get("end"))
                    if e_start and e_end:
                        matching_events.append(CalendarEvent(
                            summary=summary, start=e_start, end=e_end,
                            location=e.get("location"), description=e.get("description"),
                        ))
            if not matching_events:
                self._event, self._offset_reached = None, False
            else:
                def get_sort_key(ev):
                    if isinstance(ev.start, datetime): return ev.start
                    return dt_util.as_local(datetime.combine(ev.start, datetime.min.time()))
                matching_events.sort(key=get_sort_key)
                self._event = matching_events[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)
        except Exception as e:
            _LOGGER.error("Update failed: %s", e)

    def _check_offset(self, summary, start_time):
        if self._offset_char not in summary: return False
        try:
            digits = "".join(filter(str.isdigit, summary.split(self._offset_char)[-1]))
            if not digits: return False
            start_dt = start_time if isinstance(start_time, datetime) else dt_util.as_local(datetime.combine(start_time, datetime.min.time()))
            return dt_util.now() >= (start_dt - timedelta(minutes=int(digits)))
        except Exception: return False
