"""配置流程 — 石家庄供水水费。

允许用户在 HA 集成界面通过 UI 添加集成。
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import callback

from .const import (
    CONF_BASE_URL,
    CONF_CARD_ID,
    CONF_COOKIE,
    CONF_FANS_ID,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class CustomApiConfigFlow(ConfigFlow, domain=DOMAIN):
    """处理用户驱动的配置流程。"""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """用户首次添加集成。"""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = user_input[CONF_CARD_ID]
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"石家庄供水 {user_input[CONF_CARD_ID]}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BASE_URL, default=DEFAULT_BASE_URL
                    ): str,
                    vol.Required(CONF_CARD_ID): str,
                    vol.Required(CONF_FANS_ID): str,
                    vol.Required(CONF_VERIFY): str,
                    vol.Optional(CONF_COOKIE): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(int, vol.Range(min=10)),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: "CustomApiConfigEntry",
    ) -> "CustomApiOptionsFlow":
        return CustomApiOptionsFlow(config_entry)


class CustomApiOptionsFlow:
    """选项流程: 允许修改鉴权参数与轮询间隔。"""

    def __init__(self, config_entry: "CustomApiConfigEntry") -> None:
        self._config_entry = config_entry

    def _current(self, key: str, default: Any = None) -> Any:
        """优先取 options, 其次 data, 最后 default。"""
        return self._config_entry.options.get(
            key, self._config_entry.data.get(key, default)
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """选项首步。"""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_VERIFY, default=self._current(CONF_VERIFY, "")
                    ): str,
                    vol.Required(
                        CONF_FANS_ID, default=self._current(CONF_FANS_ID, "")
                    ): str,
                    vol.Required(
                        CONF_CARD_ID, default=self._current(CONF_CARD_ID, "")
                    ): str,
                    vol.Optional(
                        CONF_COOKIE, default=self._current(CONF_COOKIE, "")
                    ): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._current(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=10)),
                }
            ),
        )
