import json
import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Literal
import logging
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 配置日志记录
import datetime
# 为了让其他项目好追踪，记录到项目根目录的 hibt_order.log
logger = logging.getLogger("HiBTApiLogger")
logger.setLevel(logging.INFO)
logger.propagate = False
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler("hibt_order.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler) # 可选，是否输出到运行终端

# 引入原有逻辑
import main

# 读取配置
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Missing {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

configs = load_config()
API_KEY = configs.get("api_key", "YOUR_SECURE_API_KEY_HERE")

def load_token():
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# 鉴权设定
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key"
    )

# 后台任务：每 6 小时刷新 Token
def refresh_token_task():
    logger.info("[Task] Starting background token refresh...")
    try:
        # headless=True 以静默模式更新
        main.get_token(reset=True, headless=True)
        logger.info("[Task] Token refresh completed successfully.")
    except Exception as e:
        logger.error(f"[Task] Error fetching token: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化首次 Token（如果不存在的话）
    if not load_token():
        logger.info("未找到 token.json，正在进行初次 Token 获取...")
        # 为了不阻塞主线程太久，也可以在此开启一个子线程去做，但为了确保服务可用，这里阻塞获取一次也可以
        # 若需要无阻塞，可将其作为线程启动
        threading.Thread(target=refresh_token_task, daemon=True).start()

    # 启动定时任务
    scheduler = BackgroundScheduler()
    # 每间隔 6 小时触发一次 Token 重新获取
    scheduler.add_job(
        refresh_token_task,
        trigger=IntervalTrigger(hours=6),
        id="refresh_token_job",
        name="Refresh token automatically",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started.")
    yield
    # 停止定时任务
    scheduler.shutdown()

app = FastAPI(title="HiBT Event Contract API", version="1.0.0", lifespan=lifespan)

# 请求数据模型
class OrderRequest(BaseModel):
    amount: float = Field(..., ge=3, le=2000, description="交易金额，限制范围：3~2000")
    direction: int = Field(..., description="交易方向：1 可能是看涨，取决于实际平台配置")
    symbol: Literal["btcusdt", "ethusdt", "btc_usdt", "eth_usdt"] = Field(..., description="交易对，推荐带下划线格式")
    time_unit: Literal[5, 10, 15, 30, 60] = Field(..., description="时间周期单元（分钟）")

@app.post("/api/v1/order", dependencies=[Depends(get_api_key)])
async def place_order(order: OrderRequest):
    token_dict = load_token()
    if not token_dict:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token is not available yet. Background task is likely still fetching the token."
        )

    # 兼容 symbol 格式（将没有下划线的转化为带下划线的，这主要是为了适配平台可能的要求，如果有误可回滚）
    # 目前 main.py 用的是 `btc_usdt`，如果用户传入 btcusdt，这里可以帮忙格式化
    safe_symbol = order.symbol
    if "_" not in safe_symbol:
        safe_symbol = safe_symbol.replace("usd", "_usd")

    v = token_dict.get("v")
    authorization = token_dict.get("Authorization")
    x_auth_token = token_dict.get("x-auth-token")

    if not all([v, authorization, x_auth_token]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token file is corrupted or incomplete."
        )

    try:
        logger.info(f">>> Sending order: Amount={order.amount}, Direction=({'Call' if order.direction == 1 else 'Put'}), Symbol={safe_symbol}, Time={order.time_unit}m")
        result = main.place_order_web(
            v=v,
            authorization=authorization,
            x_auth_token=x_auth_token,
            amount=order.amount,
            direction=order.direction,
            symbol=safe_symbol,
            time_unit=order.time_unit
        )
        
        # 判断 HiBT 是否真正成功（通过返回的 code 字段等来断定）
        # HiBT 成功下单通常包含 {"code": 0, "msg": "success"} 或者在 data 里包含有效字段
        is_success = False
        hibt_msg = "Unknown reason"
        response_code = -1
        
        if isinstance(result, dict):
            response_code = result.get("code", -1)
            hibt_msg = result.get("msg", str(result))
            if response_code == 0:
                is_success = True
                
        if is_success:
            logger.info(f"<<< Order Success: {result}")
            return {
                "status": "success",
                "message": "Order placed successfully",
                "hibt_msg": hibt_msg,
                "data": result,
                "params_used": {
                    "amount": order.amount,
                    "direction": order.direction,
                    "symbol": safe_symbol,
                    "time_unit": order.time_unit
                }
            }
        else:
            logger.warning(f"<<< Order Failed by Platform: {result}")
            # 返回 400 Bad Request 或者 200 带 false 状态给其他项目。为了明确区分业务没挂但下单不成功的情况：
            return {
                "status": "failed",
                "message": "Order rejected by platform",
                "hibt_msg": hibt_msg,
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Order placement Exception: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order placement failed: {str(e)}"
        )

@app.post("/api/v1/refresh_token", dependencies=[Depends(get_api_key)])
async def force_refresh_token():
    """手动强制触发刷新 token 逻辑（非阻塞后台运行）"""
    logger.info("Manual token refresh triggered.")
    threading.Thread(target=refresh_token_task, daemon=True).start()
    return {"message": "Token refresh task started in the background."}

if __name__ == "__main__":
    import uvicorn
    # 为了防止因为 uvicorn 的 multiprocess 机制导致浏览器被启动多份，我们将默认 workers 设置为 1
    uvicorn.run("api:app", host="0.0.0.0", port=29471, reload=False, workers=1)
