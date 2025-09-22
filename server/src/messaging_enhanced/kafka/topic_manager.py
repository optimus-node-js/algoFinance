"""
Kafka Topic Manager for HFT System
==================================

Manages Kafka topics with:
- Automatic topic creation
- Performance-optimized configurations
- Topic monitoring and management
"""

import logging
from typing import Dict, List, Any, Optional
from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource, ConfigSource
from confluent_kafka import KafkaException, KafkaError

logger = logging.getLogger(__name__)

class TopicManager:
    """
    Kafka topic management for HFT system.
    
    Features:
    - Automatic topic creation with optimized configs
    - Topic monitoring and health checks
    - Performance tuning for low-latency
    """
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize topic manager.
        
        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
        """
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = AdminClient({
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'hft-topic-manager'
        })
        
        # HFT-optimized topic configurations
        self.hft_topic_configs = {
            # Low-latency settings
            'min.insync.replicas': '1',
            'unclean.leader.election.enable': 'false',
            'compression.type': 'snappy',
            'message.timestamp.type': 'CreateTime',
            
            # Performance settings
            'segment.ms': '3600000',  # 1 hour segments
            'segment.bytes': '1073741824',  # 1GB segments
            'retention.ms': '86400000',  # 1 day retention
            'retention.bytes': '10737418240',  # 10GB retention
            
            # Cleanup and compaction
            'cleanup.policy': 'delete',
            'delete.retention.ms': '86400000',  # 1 day
            'file.delete.delay.ms': '60000',  # 1 minute
            
            # Replication settings
            'replica.lag.time.max.ms': '30000',  # 30 seconds
            'replica.fetch.max.bytes': '1048576',  # 1MB
        }
        
        logger.info(f"TopicManager initialized for brokers: {bootstrap_servers}")
    
    def get_hft_topics(self) -> List[Dict[str, Any]]:
        """
        Get list of HFT system topics with optimized configurations.
        
        Returns:
            List of topic configurations
        """
        return [
            {
                'name': 'hft-market-data',
                'partitions': 12,  # High partition count for throughput
                'replication': 1,  # Single replica for low latency
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '3600000',  # 1 hour for market data
                    'segment.ms': '600000',  # 10 minute segments
                }
            },
            {
                'name': 'hft-trade-orders',
                'partitions': 6,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '604800000',  # 7 days for orders
                    'cleanup.policy': 'compact,delete',  # Compact for deduplication
                }
            },
            {
                'name': 'hft-execution-events',
                'partitions': 6,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '2592000000',  # 30 days for executions
                }
            },
            {
                'name': 'hft-sentiment-signals',
                'partitions': 3,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '86400000',  # 1 day for sentiment
                    'segment.ms': '3600000',  # 1 hour segments
                }
            },
            {
                'name': 'hft-risk-events',
                'partitions': 3,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '2592000000',  # 30 days for risk events
                }
            },
            {
                'name': 'hft-strategy-signals',
                'partitions': 6,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '86400000',  # 1 day for strategy signals
                }
            },
            {
                'name': 'hft-portfolio-updates',
                'partitions': 3,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '604800000',  # 7 days for portfolio
                    'cleanup.policy': 'compact,delete',
                }
            },
            {
                'name': 'hft-system-events',
                'partitions': 1,
                'replication': 1,
                'config': {
                    **self.hft_topic_configs,
                    'retention.ms': '604800000',  # 7 days for system events
                }
            }
        ]
    
    def create_hft_topics(self) -> Dict[str, bool]:
        """
        Create all HFT system topics.
        
        Returns:
            Dict mapping topic names to creation success status
        """
        topics = self.get_hft_topics()
        return self.create_topics(topics)
    
    def create_topics(self, topics: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Create Kafka topics with specified configurations.
        
        Args:
            topics: List of topic configurations
            
        Returns:
            Dict mapping topic names to creation success status
        """
        new_topics = []
        
        for topic_config in topics:
            new_topic = NewTopic(
                topic=topic_config['name'],
                num_partitions=topic_config.get('partitions', 3),
                replication_factor=topic_config.get('replication', 1),
                config=topic_config.get('config', {})
            )
            new_topics.append(new_topic)
        
        # Create topics
        fs = self.admin_client.create_topics(new_topics, validate_only=False)
        
        results = {}
        for topic, f in fs.items():
            try:
                f.result(timeout=10)  # Wait up to 10 seconds
                results[topic] = True
                logger.info(f"✅ Topic created successfully: {topic}")
                
            except KafkaException as e:
                if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                    results[topic] = True
                    logger.info(f"✅ Topic already exists: {topic}")
                else:
                    results[topic] = False
                    logger.error(f"❌ Failed to create topic {topic}: {e}")
            except Exception as e:
                results[topic] = False
                logger.error(f"❌ Unexpected error creating topic {topic}: {e}")
        
        return results
    
    def list_topics(self) -> Dict[str, Any]:
        """
        List all topics in the Kafka cluster.
        
        Returns:
            Dict with topic metadata
        """
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            
            topics_info = {}
            for topic_name, topic_metadata in metadata.topics.items():
                if not topic_name.startswith('__'):  # Skip internal topics
                    topics_info[topic_name] = {
                        'partitions': len(topic_metadata.partitions),
                        'error': topic_metadata.error,
                        'partition_info': [
                            {
                                'partition': p.id,
                                'leader': p.leader,
                                'replicas': p.replicas,
                                'isrs': p.isrs,
                                'error': p.error
                            }
                            for p in topic_metadata.partitions.values()
                        ]
                    }
            
            return {
                'broker_count': len(metadata.brokers),
                'topics': topics_info,
                'total_topics': len(topics_info)
            }
            
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return {'error': str(e)}
    
    def get_topic_configs(self, topic_names: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Get configuration for specified topics.
        
        Args:
            topic_names: List of topic names
            
        Returns:
            Dict mapping topic names to their configurations
        """
        try:
            resources = [
                ConfigResource(ConfigResource.Type.TOPIC, topic_name) 
                for topic_name in topic_names
            ]
            
            fs = self.admin_client.describe_configs(resources)
            
            configs = {}
            for resource, f in fs.items():
                try:
                    config_result = f.result(timeout=10)
                    configs[resource.name] = {
                        config.name: config.value 
                        for config in config_result.values()
                    }
                except Exception as e:
                    logger.error(f"Failed to get config for {resource.name}: {e}")
                    configs[resource.name] = {'error': str(e)}
            
            return configs
            
        except Exception as e:
            logger.error(f"Failed to describe configs: {e}")
            return {'error': str(e)}
    
    def delete_topics(self, topic_names: List[str]) -> Dict[str, bool]:
        """
        Delete specified topics.
        
        Args:
            topic_names: List of topic names to delete
            
        Returns:
            Dict mapping topic names to deletion success status
        """
        try:
            fs = self.admin_client.delete_topics(topic_names, operation_timeout=30)
            
            results = {}
            for topic, f in fs.items():
                try:
                    f.result()
                    results[topic] = True
                    logger.info(f"✅ Topic deleted successfully: {topic}")
                except Exception as e:
                    results[topic] = False
                    logger.error(f"❌ Failed to delete topic {topic}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to delete topics: {e}")
            return {topic: False for topic in topic_names}
    
    def check_topic_health(self) -> Dict[str, Any]:
        """
        Check health of HFT topics.
        
        Returns:
            Health status for all HFT topics
        """
        hft_topic_names = [topic['name'] for topic in self.get_hft_topics()]
        topics_info = self.list_topics()
        
        health_status = {
            'healthy_topics': [],
            'missing_topics': [],
            'error_topics': [],
            'total_partitions': 0,
            'overall_health': 'UNKNOWN'
        }
        
        if 'error' in topics_info:
            health_status['overall_health'] = 'ERROR'
            health_status['error'] = topics_info['error']
            return health_status
        
        for topic_name in hft_topic_names:
            if topic_name in topics_info['topics']:
                topic_info = topics_info['topics'][topic_name]
                if topic_info.get('error') is None:
                    health_status['healthy_topics'].append(topic_name)
                    health_status['total_partitions'] += topic_info['partitions']
                else:
                    health_status['error_topics'].append({
                        'topic': topic_name,
                        'error': topic_info['error']
                    })
            else:
                health_status['missing_topics'].append(topic_name)
        
        # Determine overall health
        if health_status['missing_topics'] or health_status['error_topics']:
            health_status['overall_health'] = 'DEGRADED'
        else:
            health_status['overall_health'] = 'HEALTHY'
        
        return health_status
    
    def setup_hft_system(self) -> Dict[str, Any]:
        """
        Complete setup of HFT Kafka infrastructure.
        
        Returns:
            Setup results and status
        """
        logger.info("🚀 Setting up HFT Kafka infrastructure...")
        
        # Create all HFT topics
        creation_results = self.create_hft_topics()
        
        # Check health
        health_status = self.check_topic_health()
        
        # Get topic info
        topics_info = self.list_topics()
        
        setup_result = {
            'topic_creation': creation_results,
            'health_status': health_status,
            'topics_info': topics_info,
            'setup_successful': health_status['overall_health'] in ['HEALTHY', 'DEGRADED']
        }
        
        if setup_result['setup_successful']:
            logger.info("✅ HFT Kafka infrastructure setup completed successfully")
        else:
            logger.error("❌ HFT Kafka infrastructure setup failed")
        
        return setup_result


# Global topic manager instance
_topic_manager: Optional[TopicManager] = None

def get_topic_manager(bootstrap_servers: str = "localhost:9092") -> TopicManager:
    """Get or create global topic manager instance."""
    global _topic_manager
    
    if _topic_manager is None:
        _topic_manager = TopicManager(bootstrap_servers)
    
    return _topic_manager
