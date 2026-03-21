import logging
from datetime import datetime, timedelta, date
from homeassistant.components.calendar import CalendarEntity, CalendarEvent, async_get_events
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    CONF_CAL_ID,
    CONF_SEARCH,
    CONF_OFFSET,
    CONF_DAYS,
    MAX_DAYS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """설정 항목을 기반으로 플랫폼을 설정합니다."""
    async_add_entities([FilteredCalendar(hass, config_entry.data, config_entry.entry_id)], True)

class FilteredCalendar(CalendarEntity):
    """원본 달력에서 이벤트를 필터링하여 보여주는 엔티티입니다."""

    def __init__(self, hass, data, entry_id):
        """초기화."""
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
        """엔티티의 이름을 반환합니다."""
        return self._attr_name

    @property
    def event(self) -> CalendarEvent | None:
        """현재 혹은 가장 가까운 미래의 일정을 반환합니다."""
        return self._event

    @property
    def extra_state_attributes(self):
        """요구사항에 맞춘 세부 속성을 반환합니다."""
        if not self._event:
            return {
                "offset_reached": False,
                "friendly_name": self._attr_name
            }
        
        # 시작/종료 시간을 YYYY-MM-DD HH:MM:SS 형식의 문자열로 가공
        start = self._event.start
        end = self._event.end
        
        # 종일 일정(date 객체)과 일반 일정(datetime 객체) 대응
        if isinstance(start, datetime):
            start_str = start.strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_str = f"{start.isoformat()} 00:00:00"

        if isinstance(end, datetime):
            end_str = end.strftime("%Y-%m-%d %H:%M:%S")
        else:
            end_str = f"{end.isoformat()} 00:00:00"

        return {
            "message": self._event.summary,
            "all_day": self._event.all_day,
            "start_time": start_str,
            "end_time": end_str,
            "location": self._event.location or "",
            "description": self._event.description or "",
            "offset_reached": self._offset_reached,
            "friendly_name": self._event.summary  # 일정 제목을 friendly_name으로 사용
        }

    async def async_get_events(self, hass, start_date, end_date):
        """달력 대시보드에서 요청한 일정 목록을 반환합니다."""
        try:
            # 헬퍼 함수를 사용하여 원본 달력의 데이터를 안전하게 가져옵니다.
            events = await async_get_events(self.hass, self._parent_id, start_date, end_date)
            return [e for e in events if not self._search or self._search in e.summary.lower()]
        except Exception as e:
            _LOGGER.error("Error fetching events for %s: %s", self._attr_name, e)
            return []

    async def async_update(self):
        """데이터를 갱신합니다."""
        start = dt_util.now()
        end = start + timedelta(days=self._days)

        try:
            events = await async_get_events(self.hass, self._parent_id, start, end)
            matching = [e for e in events if not self._search or self._search in e.summary.lower()]

            if not matching:
                self._event = None
                self._offset_reached = False
            else:
                self._event = matching[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)
        except Exception as e:
            _LOGGER.error("Update failed for %s: %s", self._attr_name, e)

    def _check_offset(self, summary, start_time):
        """오프셋 도달 여부를 시간대(Timezone)를 고려하여 계산합니다."""
        if self._offset_char not in summary:
            return False
        try:
            parts = summary.split(self._offset_char)
            if len(parts) < 2:
                return False
            
            digits = "".join(filter(str.isdigit, parts[1]))
            if not digits:
                return False
            
            offset_val = int(digits)
            
            # 종일 일정(date)인 경우 현지 시간의 시작 시간으로 변환하여 계산
            if isinstance(start_time, datetime):
                start_dt = start_time
            else:
                start_dt = dt_util.start_of_local_day(datetime.combine(start_time, datetime.min.time()))

            return dt_util.now() >= (start_dt - timedelta(minutes=offset_val))
        except Exception:
            return False
