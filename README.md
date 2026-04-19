# binance-futures-trading-challenges

一个面向 Binance Futures 的自动交易执行与监控服务骨架项目，基于 Python 3.11+、FastAPI、Typer、Pydantic、YAML 和 `.env` 配置方式构建，适合作为后续接入 Binance REST、WebSocket、execution service 和 risk engine 的工程化起点。

## 项目特点

- 面向实战项目组织目录，优先保证结构清晰和后续扩展性
- 提供最小可运行 FastAPI 服务
- 提供最小 CLI 管理入口
- 使用 `.env` 管理敏感信息
- 使用 YAML 承载业务配置
- 启动时打印简洁配置摘要

## 项目结构

```text
.
├── app
│   ├── api
│   ├── core
│   ├── exchange
│   ├── execution
│   ├── monitoring
│   ├── risk
│   ├── schemas
│   ├── services
│   ├── strategy
│   ├── cli.py
│   └── main.py
├── config
│   └── config.example.yaml
├── .env.example
├── main.py
├── README.md
└── requirements.txt
```

## 环境要求

- Python 3.11 或更高版本

## 初始化

1. 创建虚拟环境

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 准备环境变量和业务配置

```bash
cp .env.example .env
cp config/config.example.yaml config/config.yaml
```

## 启动服务

方式一：直接使用 uvicorn

```bash
uvicorn main:app --reload
```

方式二：使用 CLI

```bash
python -m app.cli serve --reload
```

服务启动后可访问：

- `GET /health`
- Swagger UI: `http://127.0.0.1:8000/docs`

## CLI

查看完整加载后的配置：

```bash
python -m app.cli show-config
```

检查配置是否可用并输出摘要：

```bash
python -m app.cli check-config
```

## 配置说明

配置分为两层：

- `.env`：保存敏感信息与环境切换项
- `config/config.yaml`：保存业务参数与服务开关

### `.env`

当前只保留后续接 Binance API 立即需要的敏感项：

- `BINANCE_API_KEY`：Binance API Key
- `BINANCE_API_SECRET`：Binance API Secret
- `BINANCE_USE_TESTNET`：是否使用 Binance Futures Testnet
- `APP_CONFIG_FILE`：YAML 配置文件路径，默认是 `config/config.yaml`

### `config/config.yaml`

当前业务配置收敛为以下 6 个部分：

#### `app`

- `name`：服务名称
- `host`：FastAPI 绑定地址
- `port`：FastAPI 监听端口
- `log_level`：日志级别

#### `exchange`

- `symbol`：当前默认交易对
- `default_leverage`：默认杠杆
- `recv_window`：Binance REST 请求接收窗口
- `request_timeout_seconds`：HTTP 请求超时

#### `execution`

- `max_single_order_notional_usdt`：单笔订单最大名义金额
- `max_open_exposure_usdt`：最大总敞口
- `allow_market_order`：是否允许市价单
- `allow_limit_order`：是否允许限价单
- `dry_run`：是否使用模拟执行开关

#### `risk`

- `max_daily_loss_pct`：单日最大亏损百分比
- `max_consecutive_losses`：最大连续亏损次数
- `max_api_failures`：最大 API 连续失败次数

#### `monitoring`

- `kline_interval`：行情监控的 K 线周期
- `volatility_threshold_pct`：波动告警阈值
- `reconnect_delay_seconds`：WebSocket 或流服务重连等待时间

#### `service`

- `enable_api`：是否启用 HTTP API 服务
- `enable_market_monitor`：是否启用市场监控
- `enable_user_stream`：是否启用用户流监控

如果 `config/config.yaml` 不存在，程序会自动回退到 `config/config.example.yaml`。

## 当前已完成

- FastAPI 应用入口与生命周期管理
- Typer CLI 入口
- `.env` + YAML 合并配置加载
- 精简可扩展的配置模型
- 基础日志初始化
- 启动配置摘要输出
- 健康检查接口

## 下一步建议

优先补齐以下模块：

1. Binance Futures REST 客户端与签名请求
2. WebSocket 市场流与用户流连接管理
3. execution service 的下单参数校验与 dry-run 执行器
4. risk engine 的暂停条件与状态管理
