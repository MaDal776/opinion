# Opinion Spread Trading Strategy

本项目实现了在 Opinion 交易所上的价差交易策略，核心功能包括：

- 获取全部激活市场并计算流动性、价差与中间价，用于筛选 Top N Token；
- 根据策略与风控参数生成买单候选，满足条件后下限价单；
- 独立的卖单管理模块，周期性检查仓位与挂单，按阈值触发卖单；
- 风控模块覆盖总持仓上限、单市场持仓上限、账户余额、重复下单等约束；
- 统一的日志与监控指标，输出关键流程、账户状态与执行结果；
- 可通过 YAML 与环境变量配置参数；
- 采用同步轮询调度，流程清晰易维护。

## 文件结构

```
opinion_spread/
├── opinion_spread/
│   ├── clients/           # Opinion SDK 封装
│   ├── config/            # 配置结构与加载逻辑
│   ├── executors/         # 下单与卖单管理
│   ├── logging_utils/     # 日志工具
│   ├── models/            # 数据模型
│   ├── monitoring/        # 简单指标记录
│   ├── risk/              # 风控模块
│   ├── scheduler/         # 主调度循环
│   ├── state/             # 账户状态缓存
│   └── strategy/          # 策略分析与候选生成
├── config.yaml.example    # 配置示例
├── .env.example           # 环境变量示例
└── README.md
```

## 快速开始

1. **准备环境**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 请使用 .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **复制配置文件**
   ```bash
   cp config.yaml.example config.yaml
   cp .env.example .env
   ```
   - 在 `config.yaml` 或 `.env` 中填写正确的 Opinion API host、API Key、私钥等信息。
   - `.env` 中的参数优先级高于 YAML，同名字段将覆盖。

3. **运行策略**
   ```bash
   python -m opinion_spread.scheduler.runner --config config.yaml
   ```
   - 如果未传入 `--config`，默认从当前目录读取 `config.yaml`。
   - 根据风控需要，确保账户余额、仓位等符合策略要求。

4. **日志与监控**
   - 日志默认输出到控制台，可在配置中开启文件或 JSON 输出。
   - `MetricsRecorder` 会记录买卖执行数量、循环耗时、异常次数等指标，可在日志中查看。

## 测试

项目包含基础单元测试，可运行：
```bash
pytest
```

主要测试覆盖：
- 风控模块的额度校验与重复下单限制；
- 策略筛选与候选生成逻辑。

## 注意事项

- 所有价格与数量均使用 `Decimal` 处理，避免浮点误差。
- Opinion API 限速请参考官方文档，合理设置轮询周期。
- 风控与策略参数请根据实际账户规模调整。
- 私钥、API Key 等敏感信息切勿提交至版本库。
