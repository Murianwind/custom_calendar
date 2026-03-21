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
        """현재 진행 중이거나 가장 가까운 미래의 일정을 반환합니다."""
        return self._event

    @property
    def extra_state_attributes(self):
        """사용자가 요청한 세부 속성을 반환합니다."""
        if not self._event:
            return {
                "offset_reached": False,
                "friendly_name": self._attr_name
            }
        
        # 시작/종료 시간 문자열 가공 (YYYY-MM-DD HH:MM:SS)
        start = self._event.start
        end = self._event.end
        
        if isinstance(start, datetime):
            start_str = start.strftime("%Y-%m-%d %H:%M:%S")
        else: # 종일 일정(date 객체) 처리
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
            "friendly_name": self._event.summary # 일정 제목을 friendly_name으로 설정
        }

    async def async_update(self):
        """서비스 호출을 통해 원본 달력의 데이터를 가져오고 갱신합니다."""
        start = dt_util.now()
        end = start + timedelta(days=self._days)

        try:
            # 임포트 에러를 방지하기 위해 서비스 호출(get_events) 방식으로 변경
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": self._parent_id,
                    "start_date_time": start.isoformat(),
                    "end_date_time": end.isoformat(),
                },
                blocking=True,
                return_response=True,
            )

            # 응답 데이터에서 이벤트 목록 추출
            raw_events = response.get(self._parent_id, {}).get("events", [])
            
            # CalendarEvent 객체로 변환 및 필터링
            matching_events = []
            for e in raw_events:
                summary = e.get("summary", "")
                if not self._search or self._search in summary.lower():
                    # 시간 데이터 파싱
                    e_start = dt_util.parse_datetime(e["start"]) or dt_util.parse_date(e["start"])
                    e_end = dt_util.parse_datetime(e["end"]) or dt_util.parse_date(e["end"])
                    
                    matching_events.append(CalendarEvent(
                        summary=summary,
                        start=e_start,
                        end=e_end,
                        location=e.get("location"),
                        description=e.get("description"),
                    ))

            if not matching_events:
                self._event = None
                self._offset_reached = False
            else:
                # 시간순 정렬 후 가장 가까운 일정 선택
                matching_events.sort(key=lambda x: x.start if isinstance(x.start, datetime) 
                                     else datetime.combine(x.start, datetime.min.time()))
                self._event = matching_events[0]
                self._offset_reached = self._check_offset(self._event.summary, self._event.start)

        except Exception as e:
            _LOGGER.error("Update failed for Custom Calendar '%s': %s", self._attr_name, e)

    def _check_offset(self, summary, start_time):
        """일정 제목의 !! 뒤 숫자를 파싱하여 오프셋 도달 여부를 계산합니다."""
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
                start_dt = dt_util.start_of_local_day(datetime.combine(start_time, datetime.min.time()))

            return dt_util.now() >= (start_dt - timedelta(minutes=offset_val))
        except Exception:
            return False
