# 石家庄供水水费 Home Assistant 集成

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

从石家庄供水集团接口周期性拉取水费账单数据, 暴露为 Home Assistant 传感器实体, 并支持历史月度趋势曲线。

## 功能特性

- 周期性拉取水费账单(默认每周一次)
- 自动查询近 3 个月账单, 无需手动配置账期
- 自动回填历史月度账单数据到 HA Recorder, 支持历史面板绘制趋势曲线
- 暴露 14 个传感器: 水表读数、用水量、应缴金额、缴费状态等
- 鉴权参数可在「选项」中随时修改

## 安装

### 方法一: 通过 HACS 安装(推荐)

1. 在 HA 中安装 [HACS](https://hacs.xyz) (如未安装)
2. HACS → 集成 → 右上角菜单 → 自定义仓库
3. 添加本仓库地址: `https://github.com/953077065/ha_sjz_water`
4. 在「石家庄供水水费」集成点击「安装」
5. 重启 Home Assistant
6. 设置 → 设备与服务 → 添加集成 → 搜索「石家庄供水水费」

### 方法二: 手动安装

将 `custom_components/sjz_water` 整个文件夹复制到 HA 配置目录:

```
<config>/custom_components/sjz_water/
├── __init__.py
├── api.py
├── config_flow.py
├── const.py
├── coordinator.py
├── entity.py
├── manifest.json
├── sensor.py
├── services.yaml
├── strings.json
└── translations/
    ├── en.json
    └── zh-Hans.json
```

重启 Home Assistant, 在 设置 → 设备与服务 → 添加集成 中搜索「石家庄供水水费」。

## 配置参数

集成添加时需要填写:

| 字段 | 是否必填 | 默认值 | 说明 |
|------|---------|--------|------|
| `base_url` | 是 | `http://www.sjzgsgs.com/preapi/wap/mcs/v1` | 接口基础 URL |
| `card_id` | 是 | — | 卡号 |
| `fans_id` | 是 | — | 粉丝ID / UserId |
| `verify` | 是 | — | 验证码 (verfiy) |
| `cookie` | 否 | — | Cookie 字符串 |
| `scan_interval` | 否 | `604800` | 轮询间隔秒数 (默认 1 周, 最小 10) |

账期范围自动取近 3 个月, 无需手动配置。添加后可在「集成 → 配置」中随时修改除 `base_url` 外的所有参数。

## 如何获取鉴权参数

1. 在微信中打开「石家庄供水」小程序, 进入水费查询页面
2. 使用抓包工具(如 Stream、Charles、Fiddler)捕获 `billingsSJZ` 请求
3. 从请求头中提取 `cardId`、`fansid/UserId`、`verfiy` 字段
4. (可选)从请求头复制完整 Cookie 字符串

## 暴露的传感器

| 实体名称 | 字段 | 设备类 | 单位 |
|---------|------|--------|------|
| 本期水表读数 | `reading` | WATER | m³ |
| 上期水表读数 | `lastReading` | WATER | m³ |
| 本期用水量 | `readWater` | WATER | m³ |
| 本期应缴金额 | `amount` | MONETARY | CNY |
| 本期账单金额 | `checkMoney` | MONETARY | CNY |
| 滞纳金 | `lateFee` | MONETARY | CNY |
| 违约金 | `acLateFee` | MONETARY | CNY |
| 账期 | `billingMonth` | — | — |
| 抄表时间 | `readDate` | — | — |
| 下次抄表时间 | `nextReadDate` | — | — |
| 缴费状态 | `payState` | — | 未缴费/部分缴费/已缴费 |
| 缴费时间 | `payTime` | — | — |
| 用户姓名 | `cardName` | — | — |
| 用户地址 | `cardAddress` | — | — |

## 历史趋势查看

集成首次加载时会自动回填近 3 个月的历史数据到 HA Recorder, 之后在 **历史面板** 搜索 `本期用水量` 或 `本期应缴金额` 即可看到月度趋势曲线。

## 注意事项

- `scan_interval` 默认 1 周(604800 秒), 水费数据更新频率低, 无需频繁拉取
- 鉴权参数(`verify`、`cookie`)可能过期, 失效后请在集成「配置」中更新
- 本集成仅供个人查询自家水费使用, 请勿用于商业用途

## 许可证

MIT License - 详见 [LICENSE](LICENSE)
