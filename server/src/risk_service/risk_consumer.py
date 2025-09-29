# Kafka consumer that persists risk state to Redis
from typing import Dict, Any, Optional
import json

from messaging_enhanced.kafka.consumers import risk_event_consumer
from messaging_enhanced.kafka import kafka_manager, topic_manager
from caching_service.redis_manager import get_redis_manager

class RiskConsumer:
    def __init__(self, *, cache_key_prefix: str = "risk", client=None):
        self._client = client
        if self._client is None:
            self._client = get_redis_manager().get_sync_client()
        self._closed = False
        self._rates_key = "{prefix}:rates".format(prefix=cache_key_prefix)
        self._positions_key = "{prefix}:positions".format(prefix=cache_key_prefix)
        self._isolated_key = "{prefix}:isolated".format(prefix=cache_key_prefix)
        self._topic = topic_manager.get_topic_name("RISK_EVENT")
        # Subscribe via Kafka
        risk_event_consumer.subscribe([self._topic], callback=self.handle_msg)

    def close(self):
        self._closed = True

    def handle_msg(self, msg_raw):
        """Process RISK_EVENT messages and persist rate/position state to Redis."""
        # Parse Kafka message to event payload (simplified)
        if isinstance(msg_raw.value, str):
            msg = json.loads(msg_raw.value)
        else:
            msg = msg_raw.value
        assert isinstance(msg, dict)

        event_type = msg.get("type")
        payload = msg.get("payload", {})
        assert isinstance(payload, dict)

        try:
            if event_type == "POSITION_UPDATE" and "positions" in payload:
                self._merge_day_wise_positions(payload["positions"])
            elif event_type == "RATE_BREACH" and "rates" in payload:
                self._write_rates(payload["rates"])
        except Exception as e:
            print(f"RiskConsumer.handle_msg failed: {e}", flush=True)

    def _write_rates(self, rates_dict):
        assert isinstance(rates_dict, dict)
        self._client.set(self._rates_key, json.dumps(rates_dict), ex=86400)

    def _merge_day_wise_positions(self, positions_list):
        assert isinstance(positions_list, list)
        # Merge isolated symbols: if symbol in isolated list, strip from positions dataset
        isolated_bytes = self._client.get(self._isolated_key)
        isolated = json.loads(isolated_bytes or "{}")
        assert isinstance(isolated, dict)
        isolated_symbols = set(str(k) for k, v in isolated.items() if v is True)

        # Compute unique day-wise symbol set not in isolation
        symbols_by_day: Dict[str, Dict[str, Any]] = {}
        existing_bytes = self._client.get(self._positions_key)
        existing = json.loads(existing_bytes or "{}")
        assert isinstance(existing, dict)
        if existing and isinstance(existing.get("positions"), list):
            for pos in existing["positions"]:
                if isinstance(pos, dict) and "symboltoken" in pos:
                    key = str(pos["symboltoken"])
                    if key not in isolated_symbols:
                        symbols_by_day[key] = pos

        # Merge incoming positions, but skip if symbol is isolated
        for pos in positions_list:
            if isinstance(pos, dict) and "symboltoken" in pos:
                key = str(pos["symboltoken"])
                if key not in isolated_symbols:
                    symbols_by_day[key] = pos

        # Persist aggregated list
        payload_dict = {"positions": list(symbols_by_day.values())}
        self._client.set(self._positions_key, json.dumps(payload_dict), ex=86400)

