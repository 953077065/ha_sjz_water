"""数据更新协调器。

通过 DataUpdateCoordinator 周期性调用 api client 拉取数据,
缓存全部月度账单列表, 供实体读取当前值与历史回填。
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiAuthError, ApiConnectionError, ApiParseError, CustomApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CustomApiCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """负责周期性拉取并暴露 API 数据。"""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CustomApiClient,
        update_interval: timedelta | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval or timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._client = client

    @property
    def current_data(self) -> dict[str, Any]:
        """返回最新一期账单(列表第一个元素)。"""
        data = self.data
        if data and len(data) > 0:
            return data[0]
        return {}

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """被调度器周期调用, 失败时抛 UpdateFailed 使实体进入 unavailable。"""
        try:
            data = await self._client.async_fetch_data()
        except ApiAuthError as err:
            raise UpdateFailed(f"接口鉴权或业务错误: {err}") from err
        except (ApiConnectionError, ApiParseError) as err:
            raise UpdateFailed(f"接口数据获取失败: {err}") from err
        return data
