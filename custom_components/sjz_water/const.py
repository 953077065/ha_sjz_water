"""集成常量定义。

集中维护域名、平台名、配置字段 key、默认参数等常量。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "sjz_water"

PLATFORMS: Final[list[str]] = ["sensor"]

DEFAULT_SCAN_INTERVAL: Final[int] = 604800

CONF_BASE_URL: Final[str] = "base_url"
CONF_CARD_ID: Final[str] = "card_id"
CONF_FANS_ID: Final[str] = "fans_id"
CONF_VERIFY: Final[str] = "verify"
CONF_COOKIE: Final[str] = "cookie"
CONF_SCAN_INTERVAL: Final[str] = "scan_interval"

DEFAULT_BASE_URL: Final[str] = "http://www.sjzgsgs.com/preapi/wap/mcs/v1"

ATTR_RAW_DATA: Final[str] = "raw_data"
ATTR_UPDATED_AT: Final[str] = "updated_at"
