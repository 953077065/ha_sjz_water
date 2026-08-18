"""实体基类。

各平台实体(如 sensor)继承 CustomApiEntity, 自动绑定到对应 config_entry 的 coordinator,
并通过 _attr_unique_id / _attr_has_entity_name 等设置统一行为。
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CustomApiCoordinator


class CustomApiEntity(CoordinatorEntity[CustomApiCoordinator]):
    """所有平台实体的通用基类。"""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CustomApiCoordinator,
        config_entry: ConfigEntry,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.unique_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.unique_id or config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="石家庄供水",
            model="水费查询",
            sw_version="1.0.0",
        )

    @property
    def available(self) -> bool:
        """coordinator 上次更新成功才视为可用。"""
        return self.coordinator.last_update_success
