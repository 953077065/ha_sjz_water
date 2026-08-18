"""石家庄供水水费集成入口。"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CustomApiClient, async_build_client
from .const import (
    CONF_BASE_URL,
    CONF_CARD_ID,
    CONF_COOKIE,
    CONF_FANS_ID,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import CustomApiCoordinator

_LOGGER = logging.getLogger(__name__)

type CustomApiConfigEntry = ConfigEntry[CustomApiCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CustomApiConfigEntry) -> bool:
    """设置 config entry。"""
    def _cfg(key: str, default: Any = None) -> Any:
        """优先取 options, 其次 data, 最后 default。"""
        return entry.options.get(key, entry.data.get(key, default))

    config: dict[str, Any] = {
        CONF_BASE_URL: _cfg(CONF_BASE_URL),
        CONF_CARD_ID: _cfg(CONF_CARD_ID),
        CONF_FANS_ID: _cfg(CONF_FANS_ID),
        CONF_VERIFY: _cfg(CONF_VERIFY),
        CONF_COOKIE: _cfg(CONF_COOKIE),
        CONF_SCAN_INTERVAL: _cfg(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    }

    session = async_get_clientsession(hass)
    client = await async_build_client(session, config)

    update_interval_seconds = int(
        config.get(CONF_SCAN_INTERVAL) or DEFAULT_SCAN_INTERVAL
    )
    coordinator = CustomApiCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=update_interval_seconds),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 等待实体注册完成后回填历史数据
    await hass.async_block_till_done()

    from .sensor import async_backfill_history
    await async_backfill_history(hass, coordinator)

    entry.async_on_unload(entry.add_update_listener(async_reload_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CustomApiConfigEntry) -> bool:
    """卸载 config entry。"""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """配置变更时重载。"""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """删除条目时清理。"""
    _LOGGER.debug("移除集成条目: %s", entry.entry_id)
