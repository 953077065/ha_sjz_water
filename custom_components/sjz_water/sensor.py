"""传感器平台 — 石家庄供水水费。

从 coordinator 缓存的最新账单记录中提取字段并生成 sensor 实体。
首次加载时将历史月份数据回填到 HA Recorder, 供历史面板绘制趋势。
日期/时间类字段统一以字符串形式展示, 避免 HA 设备类的类型限制。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CustomApiCoordinator
from .entity import CustomApiEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SensorFieldDef:
    """单个 sensor 字段定义。"""

    key: str
    name: str
    icon: str | None = None
    device_class: SensorDeviceClass | None = None
    unit: str | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


FIELD_DEFINITIONS: tuple[SensorFieldDef, ...] = (
    SensorFieldDef(
        key="reading",
        name="本期水表读数",
        icon="mdi:water",
        device_class=SensorDeviceClass.WATER,
        unit=UnitOfVolume.CUBIC_METERS,
    ),
    SensorFieldDef(
        key="lastReading",
        name="上期水表读数",
        icon="mdi:water",
        device_class=SensorDeviceClass.WATER,
        unit=UnitOfVolume.CUBIC_METERS,
    ),
    SensorFieldDef(
        key="readWater",
        name="本期用水量",
        icon="mdi:water",
        device_class=SensorDeviceClass.WATER,
        unit=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorFieldDef(
        key="amount",
        name="本期应缴金额",
        icon="mdi:currency-cny",
        device_class=SensorDeviceClass.MONETARY,
        unit="CNY",
    ),
    SensorFieldDef(
        key="checkMoney",
        name="本期账单金额",
        icon="mdi:file-document",
        device_class=SensorDeviceClass.MONETARY,
        unit="CNY",
    ),
    SensorFieldDef(
        key="lateFee",
        name="滞纳金",
        icon="mdi:alert-circle",
        device_class=SensorDeviceClass.MONETARY,
        unit="CNY",
    ),
    SensorFieldDef(
        key="acLateFee",
        name="违约金",
        icon="mdi:alert-octagon",
        device_class=SensorDeviceClass.MONETARY,
        unit="CNY",
    ),
    SensorFieldDef(
        key="billingMonth",
        name="账期",
        icon="mdi:calendar",
        device_class=None,
        state_class=None,
    ),
    SensorFieldDef(
        key="readDate",
        name="抄表时间",
        icon="mdi:clock",
        device_class=None,
        state_class=None,
    ),
    SensorFieldDef(
        key="nextReadDate",
        name="下次抄表时间",
        icon="mdi:calendar-clock",
        device_class=None,
        state_class=None,
    ),
    SensorFieldDef(
        key="payState",
        name="缴费状态",
        icon="mdi:check-circle",
        device_class=None,
        state_class=None,
    ),
    SensorFieldDef(
        key="payTime",
        name="缴费时间",
        icon="mdi:cash-clock",
        device_class=None,
        state_class=None,
    ),
    SensorFieldDef(
        key="cardName",
        name="用户姓名",
        icon="mdi:account",
        device_class=None,
        state_class=None,
    ),
    SensorFieldDef(
        key="cardAddress",
        name="用户地址",
        icon="mdi:map-marker",
        device_class=None,
        state_class=None,
    ),
)

PAY_STATE_MAP = {
    0: "未缴费",
    1: "部分缴费",
    2: "已缴费",
}

_entities: list["CustomApiSensor"] = []


def _get_nested(data: dict[str, Any], dotted_key: str) -> Any:
    """按点号路径取嵌套值, 缺失返回 None。"""
    cur: Any = data
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _billing_month_to_dt(billing_month: int) -> datetime:
    """将 202608 格式转为 datetime(2026, 8, 1), 用于回填时间戳。"""
    year = billing_month // 100
    month = billing_month % 100
    return datetime(year, month, 1)


def _format_billing_month(value: Any) -> str | None:
    """将 int 202608 转为 "2026-08" 字符串。"""
    if not isinstance(value, int):
        return None
    year = value // 100
    month = value % 100
    try:
        return f"{year:04d}-{month:02d}"
    except (ValueError, TypeError):
        _LOGGER.warning("账期格式异常: %s", value)
        return None


def _format_iso_datetime(value: Any) -> str | None:
    """将 ISO 字符串 "2026-08-03T12:00:22" 格式化为 "2026-08-03 12:00:22"。

    解析失败或空值时返回 None。
    """
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        _LOGGER.warning("无法解析时间字符串: %s", value)
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _raw_value(record: dict[str, Any], field_key: str) -> Any:
    """从记录中提取字段值, 并做必要的格式转换。

    - billingMonth: int 202608 → "2026-08" 字符串
    - readDate/nextReadDate/payTime: ISO 字符串 → "YYYY-MM-DD HH:MM:SS"
    - payState: int → 中文文案
    - 其他: 原值
    """
    value = _get_nested(record, field_key)

    if field_key == "payState" and isinstance(value, int):
        return PAY_STATE_MAP.get(value, f"未知({value})")

    if value is None:
        return None

    if field_key == "billingMonth":
        return _format_billing_month(value)

    if field_key in ("readDate", "nextReadDate", "payTime"):
        return _format_iso_datetime(value)

    return value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """sensor 平台 setup。"""
    coordinator: CustomApiCoordinator = entry.runtime_data
    global _entities
    _entities = [
        CustomApiSensor(
            coordinator=coordinator,
            config_entry=entry,
            field=field,
        )
        for field in FIELD_DEFINITIONS
    ]
    async_add_entities(_entities)


async def async_backfill_history(
    hass: HomeAssistant,
    coordinator: CustomApiCoordinator,
) -> None:
    """将所有历史月份数据回填到 HA Recorder, 供历史面板绘制趋势。

    按账期从旧到新依次写入, 最终实体当前状态为最新一期。
    """
    global _entities
    if not _entities:
        return

    records = coordinator.data or []
    valid_records = [r for r in records if isinstance(r, dict) and r.get("billingMonth")]
    if not valid_records:
        return

    sorted_records = sorted(valid_records, key=lambda r: r["billingMonth"])
    _LOGGER.info("回填历史水费数据: %d 条记录", len(sorted_records))

    for record in sorted_records:
        billing_month = record["billingMonth"]
        timestamp = _billing_month_to_dt(billing_month)

        for entity in _entities:
            value = _raw_value(record, entity._field.key)
            if value is None:
                continue
            try:
                hass.states.async_set(
                    entity.entity_id,
                    value,
                    last_changed=timestamp,
                )
            except Exception:
                _LOGGER.exception("回填实体 %s 状态失败", entity.entity_id)


class CustomApiSensor(CustomApiEntity, SensorEntity):
    """单个 API 字段对应的 sensor 实体。"""

    def __init__(
        self,
        coordinator: CustomApiCoordinator,
        config_entry: ConfigEntry,
        field: SensorFieldDef,
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            unique_suffix=field.key,
        )
        self._field = field
        self._attr_name = field.name
        self._attr_icon = field.icon
        self._attr_device_class = field.device_class
        self._attr_native_unit_of_measurement = field.unit
        self._attr_state_class = field.state_class

    @property
    def native_value(self) -> Any:
        """从最新数据中按字段 key 提取数值, 并做格式转换。"""
        data = self.coordinator.current_data
        return _raw_value(data, self._field.key)
