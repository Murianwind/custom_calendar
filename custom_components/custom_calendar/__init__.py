import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["calendar"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config entry에서 Custom Calendar를 설정합니다."""
    hass.data.setdefault(DOMAIN, {})
    
    # 캘린더 플랫폼 설정 로드
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # [핵심] '구성(Configure)'에서 설정이 변경될 때 즉시 다시 로드하도록 리스너 등록
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config entry를 언로드합니다 (삭제 시)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """옵션이 변경되면 통합 구성요소를 다시 로드합니다."""
    await hass.config_entries.async_reload(entry.entry_id)
