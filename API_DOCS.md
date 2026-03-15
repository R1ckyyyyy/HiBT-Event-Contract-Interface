# HiBT Event Contract API 接口文档

本文档描述了如何通过本项目提供的 FastAPI 服务与 HiBT 事件合约平台进行基于内部抓包分析的程序化交互。

## 基础信息
- **服务默认端口**: `29471`
- **基准 URL**: `http://127.0.0.1:29471/api/v1`
- **鉴权方式**: 在 HTTP Header 中添加 `X-API-Key`（请确保与您 `config.json` 中的 `api_key` 保持一致）
- **数据格式**: JSON (`application/json`)

---

## 快速运行
在配置好 `config.json` 后，您可以通过如下命令启动服务端接口：
```bash
python api.py
```
> **提示**：启动后，服务器将自动在后台进行首次 Web 端无头登录操作获取并缓存 `token.json`。此时终端会打印 `Background scheduler started.` 并在 Token 后台获取成功后额外提示。请务必等待获取完成后再执行下单动作（也可以观察根目录下是否有 `token.json` 生成）。

服务器同时启用了自动清理与定时刷新，每间隔 **6个小时** 会在隐式后台重启一次 Chrome 更新 Token 以防过期。

---

## 接口列表

### 1. 下单接口

- **路径**: `/order`
- **请求方法**: `POST`
- **说明**: 用于向平台发送具体的看涨、看跌事件合约订单。

#### 请求头 (Headers)
| 参数 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| `X-API-Key` | String | 是 | 您的专属 API Key，可在 `config.json` 中配置 |
| `Content-Type`| String | 是 | 必须为 `application/json` |

#### 请求体 (Body)
| 参数名 | 类型 | 必填 | 取值范围限制 | 描述 |
| --- | --- | --- | --- | --- |
| `amount` | Float/Int| 是 | `3` ~ `2000` | 交易金额 (USDT) |
| `direction` | Integer| 是 | 无严格限制 | 交易方向验证值（如 `1` 通常代表看涨，`-1/2` 视 HiBT 抓包规则定） |
| `symbol` | String | 是 | `btcusdt`, `ethusdt`, `btc_usdt`, `eth_usdt` | 交易对名称 |
| `time_unit` | Integer| 是 | `5`, `10`, `15`, `30`, `60` | 锁定或执行周期单位（时间单位：分钟） |

**请求示例**:
```bash
curl -X POST http://127.0.0.1:29471/api/v1/order \
  -H "X-API-Key: YOUR_SECURE_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10,
    "direction": 1,
    "symbol": "btc_usdt",
    "time_unit": 5
  }'
```

#### 响应结构 (Response)

**成功响应 (200 OK，平台返回下单成功)**:
```json
{
  "status": "success",
  "message": "Order placed successfully",
  "hibt_msg": "success",
  "data": {
    "code": 0,
    "msg": "success",
    "data": { ...HiBT的原始响应内容...}
  },
  "params_used": {
    "amount": 10.0,
    "direction": 1,
    "symbol": "btc_usdt",
    "time_unit": 5
  }
}
```

**被平台拒绝下单 (200 OK，但平台报业务错)**:
```json
{
  "status": "failed",
  "message": "Order rejected by platform",
  "hibt_msg": "余额不足 / 最小下单金额为...",
  "data": {
    ...原始失败返回...
  }
}
```

**失败响应 (示例)**:
```json
// 401 Unauthorized - 鉴权失败
{
  "detail": "Invalid API Key"
}

// 422 Unprocessable Entity - 参数校验报错（如金额过高或过低）
{
  "detail": [
    {
      "loc": ["body", "amount"],
      "msg": "ensure this value is greater than or equal to 3",
      "type": "value_error.number.not_ge"
    }
  ]
}

// 503 Service Unavailable - 服务器仍在开启后台浏览器获取初始 Token 阶段
{
  "detail": "Token is not available yet. Background task is likely still fetching the token."
}
```

---

### 2. 强制刷新 Token 接口

- **路径**: `/refresh_token`
- **请求方法**: `POST`
- **说明**: 手动触发后台 Chrome 更新 `token.json`（非阻塞，立刻返回）。

#### 请求头 (Headers)
| 参数 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| `X-API-Key` | String | 是 | 您的专属 API Key |

**请求示例**:
```bash
curl -X POST http://127.0.0.1:29471/api/v1/refresh_token \
  -H "X-API-Key: YOUR_SECURE_API_KEY_HERE"
```

**响应结构 (Response)**:
```json
{
  "message": "Token refresh task started in the background."
}
```

---

## Swagger UI
启动 `api.py` 服务器后，您可以在浏览器访问：`http://127.0.0.1:29471/docs`。 FastAPI 自带的交互式页面能帮助您直接在浏览器测试所有接口并自动组装 JSON 及 Headers 格式。
