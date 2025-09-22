"""
Schema Registry for HFT Kafka Messages
======================================

Manages Avro schemas for all Kafka message types with:
- Schema validation
- Schema evolution
- Serialization/deserialization
- Performance optimization
"""

import json
import os
import logging
from typing import Dict, Any, Optional, Type
from pathlib import Path
import avro.schema
import avro.io
import io
from datetime import datetime

logger = logging.getLogger(__name__)

class SchemaRegistry:
    """
    Avro schema registry for HFT messaging.
    
    Features:
    - Automatic schema loading from .avsc files
    - Schema validation
    - Fast serialization/deserialization
    - Schema evolution tracking
    """
    
    def __init__(self, schema_dir: Optional[str] = None):
        """
        Initialize schema registry.
        
        Args:
            schema_dir: Directory containing .avsc schema files
        """
        if schema_dir is None:
            schema_dir = Path(__file__).parent / "schemas"
        
        self.schema_dir = Path(schema_dir)
        self.schemas: Dict[str, avro.schema.Schema] = {}
        self.serializers: Dict[str, Any] = {}
        self.deserializers: Dict[str, Any] = {}
        
        # Performance tracking
        self.serialization_counts = {}
        self.deserialization_counts = {}
        self.error_counts = {}
        
        # Load all schemas
        self._load_schemas()
        logger.info(f"SchemaRegistry initialized with {len(self.schemas)} schemas")
    
    def _load_schemas(self):
        """Load all .avsc schema files from the schema directory."""
        if not self.schema_dir.exists():
            logger.warning(f"Schema directory not found: {self.schema_dir}")
            return
        
        for schema_file in self.schema_dir.glob("*.avsc"):
            try:
                with open(schema_file, 'r') as f:
                    schema_dict = json.load(f)
                
                schema = avro.schema.parse(json.dumps(schema_dict))
                schema_name = schema_file.stem
                
                self.schemas[schema_name] = schema
                self.serialization_counts[schema_name] = 0
                self.deserialization_counts[schema_name] = 0
                self.error_counts[schema_name] = 0
                
                logger.info(f"Loaded schema: {schema_name} from {schema_file}")
                
            except Exception as e:
                logger.error(f"Failed to load schema from {schema_file}: {e}")
    
    def get_schema(self, schema_name: str) -> Optional[avro.schema.Schema]:
        """
        Get schema by name.
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            Avro schema object or None if not found
        """
        return self.schemas.get(schema_name)
    
    def list_schemas(self) -> list:
        """Get list of available schema names."""
        return list(self.schemas.keys())
    
    def validate_message(self, schema_name: str, message: Dict[str, Any]) -> bool:
        """
        Validate a message against its schema.
        
        Args:
            schema_name: Name of the schema to validate against
            message: Message data to validate
            
        Returns:
            True if valid, False otherwise
        """
        schema = self.get_schema(schema_name)
        if not schema:
            logger.error(f"Schema not found: {schema_name}")
            return False
        
        try:
            # Create a dummy serialization to validate
            writer = avro.io.DatumWriter(schema)
            bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)
            writer.write(message, encoder)
            return True
            
        except Exception as e:
            logger.error(f"Message validation failed for {schema_name}: {e}")
            self.error_counts[schema_name] += 1
            return False
    
    def serialize(self, schema_name: str, message: Dict[str, Any]) -> Optional[bytes]:
        """
        Serialize a message using Avro schema.
        
        Args:
            schema_name: Name of the schema to use
            message: Message data to serialize
            
        Returns:
            Serialized bytes or None if error
        """
        schema = self.get_schema(schema_name)
        if not schema:
            logger.error(f"Schema not found: {schema_name}")
            return None
        
        try:
            # Add timestamp if not present
            if 'timestamp' in [field.name for field in schema.fields]:
                if 'timestamp' not in message:
                    message['timestamp'] = int(datetime.now().timestamp() * 1_000_000_000)
            
            writer = avro.io.DatumWriter(schema)
            bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)
            writer.write(message, encoder)
            
            self.serialization_counts[schema_name] += 1
            return bytes_writer.getvalue()
            
        except Exception as e:
            logger.error(f"Serialization failed for {schema_name}: {e}")
            self.error_counts[schema_name] += 1
            return None
    
    def deserialize(self, schema_name: str, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Deserialize bytes using Avro schema.
        
        Args:
            schema_name: Name of the schema to use
            data: Serialized bytes to deserialize
            
        Returns:
            Deserialized message dict or None if error
        """
        schema = self.get_schema(schema_name)
        if not schema:
            logger.error(f"Schema not found: {schema_name}")
            return None
        
        try:
            reader = avro.io.DatumReader(schema)
            bytes_reader = io.BytesIO(data)
            decoder = avro.io.BinaryDecoder(bytes_reader)
            message = reader.read(decoder)
            
            self.deserialization_counts[schema_name] += 1
            return message
            
        except Exception as e:
            logger.error(f"Deserialization failed for {schema_name}: {e}")
            self.error_counts[schema_name] += 1
            return None
    
    def create_market_tick(
        self,
        symbol: str,
        exchange: str,
        price: float,
        volume: int,
        bid: float,
        ask: float,
        bid_size: int = 0,
        ask_size: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a market tick message with proper defaults.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange identifier
            price: Last traded price
            volume: Trade volume
            bid: Best bid price
            ask: Best ask price
            bid_size: Best bid quantity
            ask_size: Best ask quantity
            **kwargs: Additional optional fields
            
        Returns:
            Market tick message dict
        """
        now_ns = int(datetime.now().timestamp() * 1_000_000_000)
        
        message = {
            'symbol': symbol,
            'exchange': exchange,
            'timestamp': now_ns,
            'system_timestamp': now_ns,
            'price': price,
            'volume': volume,
            'bid': bid,
            'ask': ask,
            'bid_size': bid_size,
            'ask_size': ask_size,
            'feed_latency_ns': 0,
            'sequence_number': kwargs.get('sequence_number', 0),
            'source': kwargs.get('source', 'angel_one')
        }
        
        # Add optional fields
        optional_fields = [
            'open', 'high', 'low', 'close', 'change', 'change_percent', 'total_volume'
        ]
        for field in optional_fields:
            if field in kwargs:
                message[field] = kwargs[field]
        
        return message
    
    def create_trade_order(
        self,
        order_id: str,
        strategy_id: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        order_type: str,
        product_type: str = "INTRADAY",
        price: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a trade order message with proper defaults.
        
        Args:
            order_id: Unique order identifier
            strategy_id: Strategy that generated the order
            symbol: Trading symbol
            exchange: Exchange identifier
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            product_type: Product type
            price: Order price (for limit orders)
            **kwargs: Additional optional fields
            
        Returns:
            Trade order message dict
        """
        now_ns = int(datetime.now().timestamp() * 1_000_000_000)
        
        message = {
            'order_id': order_id,
            'strategy_id': strategy_id,
            'symbol': symbol,
            'exchange': exchange,
            'side': side.upper(),
            'quantity': quantity,
            'order_type': order_type.upper(),
            'product_type': product_type.upper(),
            'timestamp': now_ns,
            'risk_approved': False,
            'execution_venue': kwargs.get('execution_venue', 'angel_one'),
            'order_status': kwargs.get('order_status', 'PENDING'),
            'filled_quantity': kwargs.get('filled_quantity', 0),
            'tags': kwargs.get('tags', {})
        }
        
        if price is not None:
            message['price'] = price
        
        # Add optional fields
        optional_fields = [
            'parent_order_id', 'risk_check_timestamp', 'average_price',
            'commission', 'slippage', 'execution_latency_ns', 'broker_order_id'
        ]
        for field in optional_fields:
            if field in kwargs:
                message[field] = kwargs[field]
        
        return message
    
    def create_sentiment_signal(
        self,
        signal_id: str,
        symbol: str,
        sentiment_score: float,
        confidence: float,
        source: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a sentiment signal message.
        
        Args:
            signal_id: Unique signal identifier
            symbol: Trading symbol
            sentiment_score: Sentiment score (-1.0 to +1.0)
            confidence: Confidence score (0.0 to 1.0)
            source: Data source
            **kwargs: Additional optional fields
            
        Returns:
            Sentiment signal message dict
        """
        now_ns = int(datetime.now().timestamp() * 1_000_000_000)
        
        # Determine strength based on score and confidence
        abs_score = abs(sentiment_score)
        if abs_score >= 0.8 and confidence >= 0.8:
            strength = "VERY_STRONG"
        elif abs_score >= 0.6 and confidence >= 0.6:
            strength = "STRONG"
        elif abs_score >= 0.3 and confidence >= 0.4:
            strength = "MODERATE"
        else:
            strength = "WEAK"
        
        message = {
            'signal_id': signal_id,
            'symbol': symbol,
            'sentiment_score': sentiment_score,
            'confidence': confidence,
            'strength': strength,
            'source': source,
            'timestamp': now_ns,
            'social_mentions': kwargs.get('social_mentions', 0),
            'keywords': kwargs.get('keywords', []),
            'entities': kwargs.get('entities', []),
            'provenance': kwargs.get('provenance', f"processed_by_hft_system"),
            'model_version': kwargs.get('model_version', "1.0"),
            'processing_latency_ms': kwargs.get('processing_latency_ms', 0),
            'market_hours': kwargs.get('market_hours', True),
            'metadata': kwargs.get('metadata', {})
        }
        
        # Add optional fields
        optional_fields = [
            'source_url', 'content_timestamp', 'news_headline', 'news_summary',
            'volume_trend', 'expiry_timestamp'
        ]
        for field in optional_fields:
            if field in kwargs:
                message[field] = kwargs[field]
        
        return message
    
    def get_stats(self) -> Dict[str, Any]:
        """Get schema registry statistics."""
        return {
            'schemas_loaded': len(self.schemas),
            'schema_names': list(self.schemas.keys()),
            'serialization_counts': self.serialization_counts.copy(),
            'deserialization_counts': self.deserialization_counts.copy(),
            'error_counts': self.error_counts.copy(),
            'schema_dir': str(self.schema_dir)
        }


# Global schema registry instance
_schema_registry: Optional[SchemaRegistry] = None

def get_schema_registry(schema_dir: Optional[str] = None) -> SchemaRegistry:
    """Get or create global schema registry instance."""
    global _schema_registry
    
    if _schema_registry is None:
        _schema_registry = SchemaRegistry(schema_dir)
    
    return _schema_registry
