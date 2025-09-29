from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import os
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import grpc

from core.connections import ConnectionManager
from messaging_enhanced.kafka.producers import OrderProducer as OrderProducerClass
from messaging_enhanced.kafka.consumers import RiskEventConsumer as RiskEventConsumerClass
from caching_service import redis_manager

# Bring in logging scope (if module exists)
try:
    from angel_one_api.logger.scope_loggers import get_scope_logger
    log = get_scope_logger("risk_service")
except Exception:
    log = lambda s: None

# Producer/Consumer instances
kafka_order_producer = OrderProducerClass()
kafka_risk_consumer = RiskEventConsumerClass()

# Default helper for publishing (simplified: we'll reuse the order producer schema path temporarily)
async def publish_risk_event(topic: str, risk_event_dict: Dict[str, Any], schema_name: str = "risk_event.avsc"):
    await kafka_order_producer.publish(topic, risk_event_dict, schema_name)

# Import RiskProvider/Consumer from separate files
from risk_service.risk_provider import RiskProvider, publish_rms_limits, publish_day_wise_positions
from risk_service.risk_consumer import RiskConsumer

# Global state
manager: Optional[ConnectionManager] = None
redis_client = None
_kill_switch: Optional[bool] = None
_kill_switch_cache_key = "risk:kill_switch"

class RiskEventType(str, Enum):
    ORDER_CHECK = "ORDER_CHECK"
    POSITION_UPDATE = "POSITION_UPDATE"
    RATE_BREACH = "RATE_BREACH"
    KILL_SWITCH_TOGGLE = "KILL_SWITCH_TOGGLE"

@dataclass
class RiskEvent:
    source: str
    type: RiskEventType
    payload: Dict[str, Any]
    timestamp: int
    id: Optional[str] = None

@dataclass
class OrderRiskCheckRequest:
    client_id: int
    product_type: str
    exchange: str
    symbol: str
    symbol_token: int
    side: str  # BUY|SELL
    quantity: int
    price: Optional[float] = None
    order_type: str = "MARKET"
    variety: str = "NORMAL"
    valid_till: str = "DAY"
    tag: Optional[str] = None

@dataclass
class OrderRiskCheckResult:
    allowed: bool
    reason: Optional[str] = None
    max_quantity: Optional[int] = None
    max_value: Optional[float] = None
    warnings: Optional[List[str]] = None

# FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    global manager, redis_client, _kill_switch
    try:
        manager = ConnectionManager()
        client = redis_manager.get_sync_client()
        redis_client = client
        # ConnectionManager handles SmartAPI client internally
    except Exception:
        pass
    try:
        if manager:
            rms_limits_json = await manager.rms_limits
            rms_limits = json.loads(rms_limits_json) if isinstance(rms_limits_json, bytes) else rms_limits_json
            assert isinstance(rms_limits, dict)
            if client:
                client.set(_kill_switch_cache_key, json.dumps(False), ex=86400)
    except Exception:
        pass
    # Initialize providers/consumers
    try:
        RiskProvider(_product_cache_key="risk:product:", _client=redis_client)
        RiskConsumer(_position_cache_key="risk:positions:", _client=redis_client, _manager=manager)
    except Exception as e:
        log(f"lifespan: provider/consumer init failed: {e}")
    yield
    try:
        if redis_client:
            redis_client.close()
    except Exception:
        pass

app = FastAPI(title="Risk Service", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_headers=["*"],
                   allow_methods=["*"])

@app.get("/health")
async def health():
    return {"status": "up", "kill_switch_on": _kill_switch or False}

@app.post("/risk/admin/kill-switch")
async def toggle_kill_switch(toggle: bool, background_tasks: BackgroundTasks):
    global _kill_switch
    _kill_switch = toggle
    client = redis_manager.get_sync_client()
    client.set(_kill_switch_cache_key, json.dumps(_kill_switch), ex=86400)
    # Publish event to topic (background)
    event = RiskEvent(source="risk_service", type=RiskEventType.KILL_SWITCH_TOGGLE, payload={"enabled": toggle}, timestamp=int(asyncio.get_event_loop().time() * 1000))
    await publish_risk_event("RISK_EVENT", event.__dict__, "risk_event.avsc")
    return {"enabled": _kill_switch}

@app.get("/risk/admin/rates")
async def get_rate_limits():
    assert manager
    angel_one_client = manager.get_smartapi_client()
    resp = await angel_one_client.getRMS()
    assert isinstance(resp, dict)
    if not resp or resp.get("status") is not True:
        raise HTTPException(status_code=502, detail="unable to fetch rate limits")
    data = resp.get("data", {})
    assert isinstance(data, dict)
    product_map = data.get("product_wise", {})
    assert isinstance(product_map, dict)
    reason_map = data.get("reason_wise", {})
    assert isinstance(reason_map, dict)
    combined_rms = {**product_map, **reason_map}
    return {"limits": combined_rms}

@app.get("/risk/admin/positions/daily")
async def get_daily_positions():
    assert manager
    angel_one_client = manager.get_smartapi_client()
    resp = await angel_one_client.getPositionsDayWise()
    assert isinstance(resp, dict)
    if not resp or not isinstance(resp.get("data"), list):
        raise HTTPException(status_code=502, detail="unable to fetch positions")
    return {"positions": resp["data"]}

@app.post("/risk/admin/positions/isolate", response_model=Dict[str, Any])
async def isolate_positions(symbols: List[str]) -> Dict[str, Any]:
    client = redis_manager.get_sync_client()
    isolated = json.loads(client.get("risk:isolated") or "{}")
    symbols_were = set(isolated.keys())
    symbols_now = set(symbols)
    isolated.clear()
    isolated.update({'symbol': True for symbol in symbols_now})
    client.set("risk:isolated", json.dumps(isolated), ex=86400)
    return {"isolated": list(symbols_now), "was": list(symbols_were)}

@app.get("/risk/admin/positions/isolate")
async def get_isolated_positions():
    client = redis_manager.get_sync_client()
    isolated = json.loads(client.get("risk:isolated") or "{}")
    return {"isolated": list(k for k, v in isolated.items() if v is True)}

@app.post("/risk/check/order", response_model=OrderRiskCheckResult)
async def check_order(req: OrderRiskCheckRequest) -> OrderRiskCheckResult:
    if _kill_switch:
        return OrderRiskCheckResult(allowed=False, reason="kill_switch_on")

    def _is_delivery(product_type: str) -> bool:
        return product_type.upper() in ["CNC", "DELIVERY"]

    def _is_buy(side: str) -> bool:
        return side.upper() in ["BUY", "B"]

    def _is_sell(side: str) -> bool:
        return side.upper() in ["SELL", "S"]

    assert manager
    angel_one_client = manager.get_smartapi_client()
    rms_resp = await angel_one_client.getRMS()
    assert isinstance(rms_resp, dict)
    if not rms_resp or rms_resp.get("status", False) is not True:
        return OrderRiskCheckResult(allowed=False, reason="rms_unavailable")
    limits = (rms_resp.get("data", {}) or {}).get("product_wise", {})
    key = f"{req.product_type}_{req.exchange}".upper()
    max_qty_raw = limits.get(key, {}).get("max_qty", "0")
    max_val_raw = limits.get(key, {}).get("max_val", "0")
    max_qty = float(max_qty_raw) if str(max_qty_raw).replace(".", "").isdigit() else 0.
    max_val = float(max_val_raw) if str(max_val_raw).replace(".", "").isdigit() else 0.
    warnings = []

    if max_qty > 0 and req.quantity > max_qty:
        return OrderRiskCheckResult(allowed=False, allowed_for_partial=True,
                                    max_quantity=max_qty, max_value=max_val)

    value = float(req.price) * req.quantity if req.price else 0.
    if value > max_val:
        return OrderRiskCheckResult(allowed=False, reason=f"order_value_exceeds_max_value")

    if _is_delivery(req.product_type) and _is_buy(req.side):
        warnings.append("Ensure sufficient margin for DELIVERY")

    return OrderRiskCheckResult(allowed=True, max_quantity=max_qty, max_value=max_val, warnings=warnings if warnings else None)

# RiskService class for external imports
class RiskService:
    """Main Risk Service class."""
    def __init__(self):
        self.app = app
        self.manager = manager
        self.redis_client = redis_client
