"""
VCC Event Consumer
Phase 2: Event-Driven Architecture

Kafka consumer for receiving VCC ecosystem events.
On-premise deployment - connects to self-hosted Kafka cluster.
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition

from .schemas import (
    VCCEventBase,
    DocumentIngestedEvent,
    DocumentProcessedEvent,
    ComplianceEvent,
    AuditLogEvent,
    VeritasRequestEvent,
    VeritasResponseEvent,
    ThemisSyncEvent
)

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    Kafka Event Consumer for VCC Ecosystem
    
    Consumes events from the on-premise Kafka cluster for
    inter-service communication within the VCC ecosystem.
    
    Usage:
        consumer = EventConsumer(
            bootstrap_servers="kafka-service.covina.svc.cluster.local:9092",
            group_id="covina-main-backend"
        )
        
        @consumer.handler("vcc.documents.processed")
        async def handle_processed(event):
            print(f"Document processed: {event.document_id}")
        
        await consumer.start()
    """
    
    # Event type to class mapping
    EVENT_CLASSES = {
        "document.ingested": DocumentIngestedEvent,
        "document.processed": DocumentProcessedEvent,
        "compliance.check": ComplianceEvent,
        "compliance.result": ComplianceEvent,
        "audit.log": AuditLogEvent,
        "veritas.request": VeritasRequestEvent,
        "veritas.response": VeritasResponseEvent,
        "themis.sync": ThemisSyncEvent,
    }
    
    def __init__(
        self,
        bootstrap_servers: str = "kafka-service.covina.svc.cluster.local:9092",
        group_id: str = "covina-consumer",
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        **kafka_config
    ):
        """
        Initialize the Event Consumer
        
        Args:
            bootstrap_servers: Kafka broker addresses (on-premise)
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading (earliest/latest)
            enable_auto_commit: Auto-commit offsets
            **kafka_config: Additional Kafka consumer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        
        # Default Kafka consumer configuration
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': enable_auto_commit,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000,
            'max.poll.interval.ms': 300000,
            **kafka_config
        }
        
        self._consumer: Optional[Consumer] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._consume_thread: Optional[threading.Thread] = None
        
    def connect(self) -> None:
        """Connect to Kafka cluster"""
        if self._consumer is None:
            try:
                self._consumer = Consumer(self.config)
                logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
            except KafkaException as e:
                logger.error(f"Failed to connect to Kafka: {e}")
                raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka cluster"""
        self._running = False
        if self._consume_thread:
            self._consume_thread.join(timeout=5)
        if self._consumer:
            self._consumer.close()
            self._consumer = None
            logger.info("Disconnected from Kafka")
    
    def handler(self, topic: str):
        """
        Decorator to register an event handler
        
        Args:
            topic: Kafka topic to subscribe to
            
        Usage:
            @consumer.handler("vcc.documents.processed")
            async def handle_processed(event):
                print(f"Processing: {event.document_id}")
        """
        def decorator(func: Callable):
            if topic not in self._handlers:
                self._handlers[topic] = []
            self._handlers[topic].append(func)
            logger.debug(f"Registered handler for topic: {topic}")
            return func
        return decorator
    
    def add_handler(self, topic: str, handler: Callable) -> None:
        """
        Add an event handler programmatically
        
        Args:
            topic: Kafka topic to subscribe to
            handler: Async function to handle events
        """
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)
        logger.debug(f"Added handler for topic: {topic}")
    
    def _parse_event(self, message) -> Optional[VCCEventBase]:
        """Parse Kafka message to event object"""
        try:
            # Get event type from headers
            headers = dict(message.headers() or [])
            event_type = headers.get(b'event_type', b'').decode('utf-8')
            
            # Parse JSON value
            value = json.loads(message.value().decode('utf-8'))
            
            # Get appropriate event class
            event_class = self.EVENT_CLASSES.get(event_type, VCCEventBase)
            
            return event_class(**value)
        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None
    
    async def _invoke_handlers(self, topic: str, event: VCCEventBase) -> None:
        """Invoke all handlers for a topic"""
        handlers = self._handlers.get(topic, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    # Run sync handler in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self._executor, handler, event)
            except Exception as e:
                logger.error(f"Handler error for {topic}: {e}")
    
    def _consume_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Main consume loop (runs in separate thread)"""
        while self._running:
            try:
                message = self._consumer.poll(timeout=1.0)
                
                if message is None:
                    continue
                
                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(
                            f"End of partition: {message.topic()} "
                            f"[{message.partition()}] @ {message.offset()}"
                        )
                    else:
                        logger.error(f"Consumer error: {message.error()}")
                    continue
                
                # Parse event
                event = self._parse_event(message)
                if event:
                    # Schedule handler invocation
                    asyncio.run_coroutine_threadsafe(
                        self._invoke_handlers(message.topic(), event),
                        loop
                    )
                    logger.debug(
                        f"Processed event from {message.topic()} "
                        f"[{message.partition()}] @ {message.offset()}"
                    )
                
            except Exception as e:
                logger.error(f"Consume loop error: {e}")
    
    async def start(self) -> None:
        """Start consuming events"""
        self.connect()
        
        # Subscribe to topics with handlers
        topics = list(self._handlers.keys())
        if not topics:
            logger.warning("No handlers registered, nothing to consume")
            return
        
        self._consumer.subscribe(topics)
        logger.info(f"Subscribed to topics: {topics}")
        
        self._running = True
        loop = asyncio.get_event_loop()
        
        # Start consume loop in separate thread
        self._consume_thread = threading.Thread(
            target=self._consume_loop,
            args=(loop,),
            daemon=True
        )
        self._consume_thread.start()
        logger.info("Started event consumer")
    
    async def stop(self) -> None:
        """Stop consuming events"""
        self._running = False
        if self._consume_thread:
            self._consume_thread.join(timeout=5)
        self.disconnect()
        logger.info("Stopped event consumer")
    
    def consume_one(self, timeout: float = 10.0) -> Optional[VCCEventBase]:
        """
        Consume a single message (synchronous)
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            Parsed event or None
        """
        self.connect()
        
        topics = list(self._handlers.keys())
        if topics:
            self._consumer.subscribe(topics)
        
        message = self._consumer.poll(timeout=timeout)
        
        if message is None or message.error():
            return None
        
        return self._parse_event(message)
    
    def commit(self) -> None:
        """Manually commit offsets"""
        if self._consumer:
            self._consumer.commit()
    
    def seek_to_beginning(self, topic: str, partition: int = 0) -> None:
        """Seek to beginning of partition"""
        if self._consumer:
            tp = TopicPartition(topic, partition, 0)
            self._consumer.seek(tp)
    
    def seek_to_end(self, topic: str, partition: int = 0) -> None:
        """Seek to end of partition"""
        if self._consumer:
            # Get high watermark
            low, high = self._consumer.get_watermark_offsets(
                TopicPartition(topic, partition)
            )
            tp = TopicPartition(topic, partition, high)
            self._consumer.seek(tp)
    
    def get_committed_offsets(self, topics: List[str]) -> Dict[str, int]:
        """Get committed offsets for topics"""
        if not self._consumer:
            return {}
        
        result = {}
        for topic in topics:
            for partition in range(3):  # Assuming 3 partitions
                tp = TopicPartition(topic, partition)
                committed = self._consumer.committed([tp])
                if committed and committed[0].offset >= 0:
                    result[f"{topic}[{partition}]"] = committed[0].offset
        
        return result
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    async def __aenter__(self):
        self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
