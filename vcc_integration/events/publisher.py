"""
VCC Event Publisher
Phase 2: Event-Driven Architecture

Kafka producer for publishing VCC ecosystem events.
On-premise deployment - connects to self-hosted Kafka cluster.
"""

import json
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from confluent_kafka import Producer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from .schemas import VCCEventBase

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Kafka Event Publisher for VCC Ecosystem
    
    Publishes events to the on-premise Kafka cluster for
    inter-service communication within the VCC ecosystem.
    
    Usage:
        publisher = EventPublisher(
            bootstrap_servers="kafka-service.covina.svc.cluster.local:9092"
        )
        await publisher.publish(document_ingested_event)
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "kafka-service.covina.svc.cluster.local:9092",
        client_id: str = "covina-publisher",
        schema_registry_url: Optional[str] = None,
        **kafka_config
    ):
        """
        Initialize the Event Publisher
        
        Args:
            bootstrap_servers: Kafka broker addresses (on-premise)
            client_id: Unique identifier for this producer
            schema_registry_url: Optional Schema Registry URL for Avro
            **kafka_config: Additional Kafka producer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.schema_registry_url = schema_registry_url
        
        # Default Kafka producer configuration (optimized for reliability)
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': client_id,
            'acks': 'all',  # Wait for all replicas
            'retries': 5,
            'retry.backoff.ms': 100,
            'delivery.timeout.ms': 30000,
            'enable.idempotence': True,  # Exactly-once semantics
            'compression.type': 'lz4',
            'batch.size': 16384,
            'linger.ms': 5,
            **kafka_config
        }
        
        self._producer: Optional[Producer] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._delivery_callbacks: Dict[str, Callable] = {}
        
    def connect(self) -> None:
        """Connect to Kafka cluster"""
        if self._producer is None:
            try:
                self._producer = Producer(self.config)
                logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
            except KafkaException as e:
                logger.error(f"Failed to connect to Kafka: {e}")
                raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka cluster"""
        if self._producer:
            # Flush any pending messages
            self._producer.flush(timeout=10)
            self._producer = None
            logger.info("Disconnected from Kafka")
    
    def _delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """Callback for message delivery confirmation"""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[partition={msg.partition()}] "
                f"[offset={msg.offset()}]"
            )
    
    def publish_sync(
        self,
        event: VCCEventBase,
        topic: Optional[str] = None,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Publish event synchronously
        
        Args:
            event: VCC event to publish
            topic: Override topic (uses event's default if not provided)
            key: Message key (uses event_id if not provided)
            headers: Additional headers
            
        Returns:
            True if message was queued successfully
        """
        self.connect()
        
        # Determine topic
        target_topic = topic or event.get_topic()
        
        # Prepare message
        message_key = key or event.event_id
        message_value = event.model_dump_json()
        
        # Prepare headers
        message_headers = {
            "event_type": event.event_type.value,
            "source": event.source_service,
            "correlation_id": event.correlation_id or "",
            "timestamp": datetime.utcnow().isoformat(),
            "version": event.version
        }
        if headers:
            message_headers.update(headers)
        
        # Convert headers to list of tuples
        header_list = [(k, v.encode('utf-8')) for k, v in message_headers.items()]
        
        try:
            self._producer.produce(
                topic=target_topic,
                key=message_key.encode('utf-8'),
                value=message_value.encode('utf-8'),
                headers=header_list,
                callback=self._delivery_callback
            )
            self._producer.poll(0)  # Trigger callbacks
            logger.info(f"Published event {event.event_type.value} to {target_topic}")
            return True
        except BufferError:
            logger.error("Kafka producer buffer full, waiting...")
            self._producer.poll(1)
            return False
        except KafkaException as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    async def publish(
        self,
        event: VCCEventBase,
        topic: Optional[str] = None,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Publish event asynchronously
        
        Args:
            event: VCC event to publish
            topic: Override topic (uses event's default if not provided)
            key: Message key (uses event_id if not provided)
            headers: Additional headers
            
        Returns:
            True if message was queued successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.publish_sync(event, topic, key, headers)
        )
    
    async def publish_batch(
        self,
        events: list[VCCEventBase],
        flush_after: bool = True
    ) -> int:
        """
        Publish multiple events as a batch
        
        Args:
            events: List of events to publish
            flush_after: Whether to flush after batch
            
        Returns:
            Number of successfully queued messages
        """
        self.connect()
        
        success_count = 0
        for event in events:
            if await self.publish(event):
                success_count += 1
        
        if flush_after:
            self.flush()
        
        return success_count
    
    def flush(self, timeout: float = 10.0) -> int:
        """
        Flush pending messages
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            Number of messages still in queue
        """
        if self._producer:
            return self._producer.flush(timeout)
        return 0
    
    def create_topics(
        self,
        topics: list[Dict[str, Any]],
        admin_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Create Kafka topics (admin operation)
        
        Args:
            topics: List of topic configurations
            admin_config: Admin client configuration
        """
        config = admin_config or {'bootstrap.servers': self.bootstrap_servers}
        admin_client = AdminClient(config)
        
        new_topics = [
            NewTopic(
                topic=t['name'],
                num_partitions=t.get('partitions', 3),
                replication_factor=t.get('replication_factor', 3),
                config=t.get('config', {})
            )
            for t in topics
        ]
        
        futures = admin_client.create_topics(new_topics)
        
        for topic, future in futures.items():
            try:
                future.result()
                logger.info(f"Created topic: {topic}")
            except KafkaException as e:
                if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                    logger.debug(f"Topic already exists: {topic}")
                else:
                    logger.error(f"Failed to create topic {topic}: {e}")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    async def __aenter__(self):
        self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
