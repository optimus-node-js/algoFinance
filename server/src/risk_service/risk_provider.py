# Angel One helpers and risk state publishing into Kafka
from typing import Dict, Any, List
import os
import asyncio
import json
import uuid
from enum import Enum

from core.connections import ConnectionManager
from messaging_enhanced.kafka.producers import order_producer
from caching_service import redis_manager

class RiskEventType(str, Enum):
    ORDER_CHECK = "ORDER_CHECK"
    POSITION_UPDATE = "POSITION_UPDATE"
    RATE_BREACH = "RATE_BREACH"
    KILL_SWITCH_TOGGLE = "KILL_SWITCH_TOGGLE"

# Publisher helpers
async def publish_rms_limits(angel_one_client) -> Dict[str, Any]:
    resp = await angel_one_client.getRMS()
    assert isinstance(resp, dict)
    if not resp or resp.get("status") is not True:
        raise ValueError("invalid RMS response")
    data = resp.get("data", {})
    product_map = data.get("product_wise", {})
    reason_map = data.get("reason_wise", {})
    combined = {**product_map, **reason_map}
    assert isinstance(combined, dict)
    return {"rates": combined}

async def publish_day_wise_positions(angel_one_client) -> List[Dict[str, Any]]:
    resp = await angel_one_client.getPositionsDayWise()
    assert isinstance(resp, dict)
    if not resp or not isinstance(resp.get("data"), list):
        raise ValueError("invalid positions response")
    return {"positions": resp["data"]}

# RiskProvider publishes to Kafka RISK_EVENT
class RiskProvider:
    def __init__(self, *, periodic_ms: int = 60000):
        self._kafka_producer = order_producer
        self._periodic_ms = periodic_ms
        self._closed = False

    async def _publish_rms_rates(self, angel_one_client, source: str = "risk_provider", error_count: int = 0):
        try:
            rates = await publish_rms_limits(angel_one_client)
            payload = {"type": "rates", **rates}
            await self._publish_risk_event(
                topic="RISK_EVENT",
                event_type=RiskEventType.RATE_BREACH,
                source=source,
                payload=payload,
            )
        except Exception as e:
            error_count = error_count + 1
            print(f"RiskProvider._publish_rms_rates failed (count={error_count}): {e}", flush=True)

    async def _publish_positions(self, angel_one_client, source: str = "risk_provider", error_count: int = 0):
        try:
            positions = await publish_day_wise_positions(angel_one_client)
            payload = {"type": "positions", **positions}
            await self._publish_risk_event(
                topic="RISK_EVENT",
                event_type=RiskEventType.POSITION_UPDATE,
                source=source,
                payload=payload,
            )
        except Exception as e:
            error_count = error_count + 1
            print(f"RiskProvider._publish_positions failed (count={error_count}): {e}", flush=True)

    async def _publish_risk_event(self, topic: str, event_type: RiskEventType, source: str, payload: Dict[str, Any]):
        event_timestamp_ms = int(asyncio.get_event_loop().time() * 1000)
        event_id = str(uuid.uuid4())
        risk_event = {
            "source": source,
            "type": event_type.value,
            "payload": payload,
            "timestamp": event_timestamp_ms,
            "id": event_id,
        }
        self._kafka_producer.publish(topic, risk_event, schema_name="risk_event.avsc")

    def close(self):
        self._closed = True

