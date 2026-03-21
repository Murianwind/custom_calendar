"""The Custom Calendar integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 지원하는 플랫폼 리스트 (본 컴포넌트는 calendar 플랫폼을 사용함)
PLATFORMS = ["calendar"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """UI(Config Entry)를 통해 통합 구성요소가 설정될 때 호출됩니다."""
    hass.data.setdefault(DOMAIN, {})
    
    # 설정된 플랫폼(calendar.py)을 로드합니다.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합 구성요소가 제거될 때 호출됩니다."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
