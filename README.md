# binance-futures-trading-challenges

一个面向 Binance Futures 的自动交易执行与监控服务骨架项目，基于 Python 3.11+、FastAPI、Typer、Pydantic、YAML 和 `.env` 配置方式构建，适合作为后续接入 Binance API 与交易模块的工程化起点。

## 项目特点

- 面向实战项目组织目录，优先保证结构清晰和后续扩展性
- 提供最小可运行 FastAPI 服务
- 提供最小 CLI 管理入口
- 使用 `.env` 管理敏感环境变量
- 使用 YAML 承载业务配置
- 使用标准库 `logging` 完成日志初始化

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

查看当前加载的配置：

```bash
python -m app.cli show-config
```

## 配置说明

- `.env` 用于保存敏感信息和环境级配置
- `config/config.yaml` 用于保存业务配置
- 如果 `config/config.yaml` 不存在，程序会自动回退到 `config/config.example.yaml`

## 当前已完成

- FastAPI 应用入口与生命周期管理
- Typer CLI 入口
- `.env` + Pydantic Settings 配置加载
- YAML 业务配置加载
- 基础日志初始化
- 健康检查接口

## 下一步建议

优先补齐以下模块：

1. Binance Futures REST / WebSocket 客户端封装
2. 账户、订单、持仓查询服务层
3. 下单执行器与统一异常处理
4. 风控开关、暂停机制与状态持久化
5. 行情与账户监控任务调度
