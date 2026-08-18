"""API 客户端 — 石家庄供水水费查询接口。

返回完整月度账单数组, 供历史回填与当前值读取。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError

from .const import (
    CONF_BASE_URL,
    CONF_CARD_ID,
    CONF_COOKIE,
    CONF_END_BM,
    CONF_FANS_ID,
    CONF_START_BM,
    CONF_VERIFY,
)

_LOGGER = logging.getLogger(__name__)


class ApiAuthError(Exception):
    """鉴权失败(401/403/业务 code != 0)。"""


class ApiConnectionError(Exception):
    """网络或服务端不可达。"""


class ApiParseError(Exception):
    """响应解析失败。"""


class CustomApiClient:
    """石家庄供水水费 API 客户端。"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        card_id: str,
        fans_id: str,
        verify: str,
        cookie: str | None = None,
        start_bm: str = "202409",
        end_bm: str = "202609",
        timeout: int = 15,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._card_id = card_id
        self._fans_id = fans_id
        self._verify = verify
        self._cookie = cookie
        self._start_bm = start_bm
        self._end_bm = end_bm
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _url(self) -> str:
        return f"{self._base_url}/card/{self._card_id}/billingsSJZ"

    @property
    def _query_params(self) -> dict[str, str]:
        return {
            "startBM": self._start_bm,
            "endBM": self._end_bm,
            "fansId": self._fans_id,
            "isPayAgentCheck": "0",
        }

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Host": "www.sjzgsgs.com",
            "Accept": "application/json, text/plain, */*",
            "UserId": self._fans_id,
            "fansid": self._fans_id,
            "cardId": self._card_id,
            "verfiy": self._verify,
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 26_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                "MicroMessenger/8.0.75(0x18004b61) NetType/WIFI Language/zh_CN"
            ),
            "Referer": (
                "http://www.sjzgsgs.com/?v=09261531&code=021w8n0w3A4lB731WG0w3jWGZW2w8n0O"
                "&state=123,wechat_redirect"
            ),
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        if self._cookie:
            headers["Cookie"] = self._cookie
        return headers

    async def async_fetch_data(self) -> list[dict[str, Any]]:
        """拉取全部月度账单, 返回记录列表(最新在前)。

        :raises ApiAuthError: 业务 code != 0 或 HTTP 401/403
        :raises ApiConnectionError: 网络/超时
        :raises ApiParseError: 响应非 JSON 或结构异常
        """
        try:
            async with self._session.get(
                self._url,
                headers=self._build_headers(),
                params=self._query_params,
                timeout=self._timeout,
            ) as resp:
                if resp.status in (401, 403):
                    raise ApiAuthError(f"鉴权失败 status={resp.status}")
                if resp.status >= 400:
                    raise ApiConnectionError(f"接口返回错误 status={resp.status}")
                try:
                    body = await resp.json()
                except aiohttp.ContentTypeError as err:
                    text = await resp.text()
                    raise ApiParseError(f"响应非 JSON: {text[:200]}") from err
        except asyncio.TimeoutError as err:
            raise ApiConnectionError("请求超时") from err
        except ClientError as err:
            raise ApiConnectionError(f"网络异常: {err}") from err

        if not isinstance(body, dict):
            raise ApiParseError(f"响应非对象(dict): {type(body).__name__}")

        code = body.get("code")
        if code != 0:
            message = body.get("message") or f"业务错误 code={code}"
            raise ApiAuthError(message)

        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise ApiParseError("响应 data 为空数组")

        for i, record in enumerate(data):
            if not isinstance(record, dict):
                raise ApiParseError(f"data[{i}] 非对象: {type(record).__name__}")
        return data


async def async_build_client(
    session: aiohttp.ClientSession,
    config: dict[str, Any],
) -> CustomApiClient:
    """根据用户配置项构造客户端实例。"""
    return CustomApiClient(
        session=session,
        base_url=config[CONF_BASE_URL],
        card_id=config[CONF_CARD_ID],
        fans_id=config[CONF_FANS_ID],
        verify=config[CONF_VERIFY],
        cookie=config.get(CONF_COOKIE),
        start_bm=config.get(CONF_START_BM, "202409"),
        end_bm=config.get(CONF_END_BM, "202609"),
    )
