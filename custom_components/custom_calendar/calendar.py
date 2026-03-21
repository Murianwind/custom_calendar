import logging
from datetime import timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util
from .const import CONF_CAL_ID, CONF_SEARCH, CONF_OFFSET, CONF_DAYS, MAX_DAYS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """설정 항목을 기반으로 엔티티를 추가합니다."""
    # 엔티티 추가 후 즉시 update를 실행하도록 두 번째 인자를 True로 설정합니다.
    async_add_entities([FilteredCalendar(hass, config_entry.data, config_entry.entry_id)], True)

class FilteredCalendar(CalendarEntity):
    """필터링된 기능을 가진 달력 엔티티입니다."""

    def __init__(self, hass, data, entry_id):
        self.hass = hass
        self._parent_id = data[CONF_CAL_ID]
        self._attr_name = data["name"]
        self._search = data.get(CONF_SEARCH, "").lower()
        self._offset_char = data.get(CONF_OFFSET, "!!")
        self._days = min(data.get(CONF_DAYS, 30), MAX_DAYS)
        self._attr_unique_id = entry_id
        
        self._event: CalendarEvent | None = None
        self._offset_reached = False

    @property
    def name(self):
        """엔티티 이름을 반환합니다."""
        return self._attr_name

    @property
    def event(self) -> CalendarEvent | None:
        """이 부분이 핵심입니다. HA 코어가 상태를 계산하기 위해 호출합니다."""
        return self._event

    @property
    def extra_state_attributes(self):
        """엔티티의 추가 속성을 정의합니다."""
        if not self._event:
            return {"offset_reached": False}
        
        return {
            "message": self._event.summary,
            "all_day": self._event.all_day,
            "start_time": self._event.start,
            "end_time": self._event.end,
            "location": self._event.location or "",
            "description": self._event.description or "",
            "offset_reached": self._offset_reached,
            "friendly_name": self._attr_name
        }

    async def async_get_events(self, hass, start_date, end_date):
        """달력 대시보드 화면에 일정을 뿌려줄 때 호출됩니다."""
        try:
            events = await self.hass.components.calendar.async_get_events(
                self._parent_id, start_date, end_date
            )
            return [e for e in events if not self._search or self._search in e.summary.lower()]
        except Exception as e:
            _LOGGER.error("Error getting events from %s: %s", self._parent_id, e)
            return []

    async def async_update(self):
        """주기적으로 부모 달력에서 데이터를 가져와 가공합니다."""
        start = dt_util.now()
        end = start + timedelta(days=self._days)

        try:
            events = await self.hass.components.calendar.async_get_events(
                self._parent_id, start, end
            )
            matching = [e for e in events if not self._search or self._search in e.summary.lower()]

            if not matching:
                self._event = None
                self._offset_reached = False
            else:
                self._event = matching[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)
        except Exception as e:
            _LOGGER.error("Custom Calendar update failed for %s: %s", self._attr_name, e)

    def _check_offset(self, summary, start_time):
        """오프셋 도달 여부를 계산합니다."""
        if self._offset_char not in summary:
            return False
        try:
            parts = summary.split(self._offset_char)
            digits = "".join(filter(str.isdigit, parts[1]))
            if not digits:
                return False
            offset_val = int(digits)
            return dt_util.now() >= (start_time - timedelta(minutes=offset_val))
        except Exception:
            return False
