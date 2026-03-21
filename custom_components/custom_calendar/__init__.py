from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

PLATFORMS = ["calendar"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # 옵션 업데이트 감시 리스너 등록
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """옵션이 수정되면 플랫폼을 다시 로드합니다."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
