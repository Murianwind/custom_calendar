import logging
from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    """원본 달력에서 이벤트를 필터링하여 보여주는 가상 달력 엔티티."""

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
        return self._attr_name

    @property
    def event(self) -> CalendarEvent | None:
        return self._event

    @property
    def extra_state_attributes(self):
        if not self._event:
            return {
                "offset_reached": False,
                "friendly_name": self._attr_name
            }
        
        start = self._event.start
        end = self._event.end
        
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
            "friendly_name": self._event.summary
        }

    def _parse_event_time(self, raw_time_str):
        """문자열에서 시간대(Timezone)가 포함된 올바른 날짜 객체를 생성합니다."""
        if not raw_time_str:
            return None
        # 길이가 10이면 날짜(종일 일정)
        if len(raw_time_str) == 10:
            return dt_util.parse_date(raw_time_str)
        # 시간 정보가 포함된 경우
        parsed_dt = dt_util.parse_datetime(raw_time_str)
        # 시간대(timezone) 정보가 없다면 강제로 현재 시간대를 부여 (에러 방지 핵심)
        if parsed_dt and parsed_dt.tzinfo is None:
            parsed_dt = dt_util.as_local(parsed_dt)
        return parsed_dt

    async def async_get_events(self, hass, start_date, end_date):
        """달력 대시보드 화면 렌더링용"""
        try:
            # target을 명시적으로 분리하여 전달 (Entity Not Found 에러 해결)
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "start_date_time": start_date.isoformat(),
                    "end_date_time": end_date.isoformat(),
                },
                target={"entity_id": self._parent_id},
                blocking=True,
                return_response=True,
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
        except Exception as e:
            _LOGGER.error("Error fetching UI events: %s", e)
            return []

    async def async_update(self):
        """센서 상태 주기적 업데이트"""
        start = dt_util.now()
        end = start + timedelta(days=self._days)

        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "start_date_time": start.isoformat(),
                    "end_date_time": end.isoformat(),
                },
                target={"entity_id": self._parent_id},
                blocking=True,
                return_response=True,
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
                self._event = None
                self._offset_reached = False
            else:
                # 시간순 정렬 (종일 일정과 일반 일정 비교 시 타입 에러 방지)
                def get_sort_key(event_obj):
                    if isinstance(event_obj.start, datetime):
                        return event_obj.start
                    return dt_util.as_local(datetime.combine(event_obj.start, datetime.min.time()))

                matching_events.sort(key=get_sort_key)
                
                # 가장 가까운 미래 일정 선택
                self._event = matching_events[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)

        except Exception as e:
            _LOGGER.error("Update failed: %s", e)

    def _check_offset(self, summary, start_time):
        """오프셋 도달 여부 계산"""
        if self._offset_char not in summary:
            return False
        try:
            parts = summary.split(self._offset_char)
            digits = "".join(filter(str.isdigit, parts[-1]))
            if not digits:
                return False
            
            offset_val = int(digits)
            if isinstance(start_time, datetime):
                start_dt = start_time
            else:
                start_dt = dt_util.as_local(datetime.combine(start_time, datetime.min.time()))

            return dt_util.now() >= (start_dt - timedelta(minutes=offset_val))
        except Exception:
            return False
