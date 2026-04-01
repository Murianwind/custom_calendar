import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["calendar"]
SIGNAL_REFRESH = f"{DOMAIN}_refresh"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config entry 설정 및 서비스 등록."""
    hass.data.setdefault(DOMAIN, {})

    # [추가] 모든 엔티티를 한 번에 갱신하는 서비스 등록
    async def handle_refresh(call: ServiceCall):
        _LOGGER.debug("Custom Calendar: 모든 엔티티 갱신 신호를 보냅니다.")
        async_dispatcher_send(hass, SIGNAL_REFRESH)

    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """언로드 처리."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """설정 변경 시 리로드."""
    await hass.config_entries.async_reload(entry.entry_id)
