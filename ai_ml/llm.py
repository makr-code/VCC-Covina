"""
VCC-Covina LLM Service
Self-hosted LLM integration with vLLM (Llama 3.1, Mistral)
On-premise, no vendor dependencies

Usage:
    from ai_ml.llm import LLMService, LLMConfig
    
    config = LLMConfig(
        model_endpoint="http://vllm-llama-service.covina-llm:8000",
        model_name="meta-llama/Meta-Llama-3.1-8B-Instruct"
    )
    llm = LLMService(config)
    
    response = await llm.generate("Explain document compliance requirements")
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Available LLM models (all self-hosted)"""
    LLAMA_3_1_8B = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    LLAMA_3_1_70B = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    MISTRAL_7B = "mistralai/Mistral-7B-Instruct-v0.2"
    DEEPSEEK_CODER = "deepseek-ai/deepseek-coder-6.7b-instruct"


@dataclass
class LLMConfig:
    """Configuration for LLM service"""
    # Service endpoints (on-premise)
    model_endpoint: str = "http://vllm-llama-service.covina-llm:8000"
    backup_endpoint: str = "http://vllm-mistral-service.covina-llm:8000"
    
    # Model settings
    model_name: str = ModelType.LLAMA_3_1_8B.value
    
    # Generation parameters
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    
    # Request settings
    timeout: float = 120.0  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # API key (on-premise)
    api_key: str = "vcc-covina-llm-secret-key"
    
    # System prompt for Covina
    default_system_prompt: str = """Du bist ein KI-Assistent für das VCC-Covina Dokumenten-Management-System.
Deine Aufgaben umfassen:
- Dokumentenanalyse und -klassifikation
- Compliance-Prüfung (DSGVO, Handelsregister)
- Rechtliche Recherche und Zusammenfassung
- Unterstützung bei der Dokumentenverarbeitung

Antworte präzise, sachlich und in der Sprache der Anfrage (Deutsch oder Englisch).
Bei rechtlichen Themen weise auf die Notwendigkeit professioneller Rechtsberatung hin."""


@dataclass
class LLMResponse:
    """Response from LLM service"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Chat message"""
    role: str  # "system", "user", "assistant"
    content: str


class LLMService:
    """
    Self-hosted LLM Service using vLLM
    
    Features:
    - Multiple model support (Llama 3.1, Mistral)
    - Streaming responses
    - Automatic failover
    - Rate limiting
    - Metrics collection
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0
        self._total_tokens = 0
    
    async def __aenter__(self) -> "LLMService":
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if self._session is None or self._session.closed:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}"
            }
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from prompt
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt override
            **kwargs: Override generation parameters
            
        Returns:
            LLMResponse with generated content
        """
        messages = [
            Message(role="system", content=system_prompt or self.config.default_system_prompt),
            Message(role="user", content=prompt)
        ]
        return await self.chat(messages, **kwargs)
    
    async def chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> LLMResponse:
        """
        Chat completion with message history
        
        Args:
            messages: List of chat messages
            **kwargs: Override generation parameters
            
        Returns:
            LLMResponse with generated content
        """
        await self._ensure_session()
        
        # Build request
        request_body = self._build_request(messages, **kwargs)
        
        # Try primary endpoint, fallback to backup
        endpoints = [self.config.model_endpoint, self.config.backup_endpoint]
        last_error = None
        
        for endpoint in endpoints:
            for attempt in range(self.config.max_retries):
                try:
                    import time
                    start_time = time.time()
                    
                    async with self._session.post(
                        f"{endpoint}/v1/chat/completions",
                        json=request_body
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            latency_ms = (time.time() - start_time) * 1000
                            
                            self._request_count += 1
                            usage = data.get("usage", {})
                            self._total_tokens += usage.get("total_tokens", 0)
                            
                            return LLMResponse(
                                content=data["choices"][0]["message"]["content"],
                                model=data.get("model", self.config.model_name),
                                usage=usage,
                                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                                latency_ms=latency_ms,
                                metadata={
                                    "endpoint": endpoint,
                                    "attempt": attempt + 1
                                }
                            )
                        else:
                            error_text = await response.text()
                            last_error = f"HTTP {response.status}: {error_text}"
                            logger.warning(f"LLM request failed: {last_error}")
                            
                except aiohttp.ClientError as e:
                    last_error = str(e)
                    logger.warning(f"LLM connection error: {e}")
                
                # Wait before retry
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        raise LLMServiceError(f"All LLM endpoints failed: {last_error}")
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate text with streaming response
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt override
            **kwargs: Override generation parameters
            
        Yields:
            Text chunks as they are generated
        """
        messages = [
            Message(role="system", content=system_prompt or self.config.default_system_prompt),
            Message(role="user", content=prompt)
        ]
        
        async for chunk in self.chat_stream(messages, **kwargs):
            yield chunk
    
    async def chat_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Chat completion with streaming response
        
        Args:
            messages: List of chat messages
            **kwargs: Override generation parameters
            
        Yields:
            Text chunks as they are generated
        """
        await self._ensure_session()
        
        request_body = self._build_request(messages, stream=True, **kwargs)
        
        async with self._session.post(
            f"{self.config.model_endpoint}/v1/chat/completions",
            json=request_body
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise LLMServiceError(f"Streaming request failed: HTTP {response.status}: {error_text}")
            
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    def _build_request(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Build API request body"""
        return {
            "model": kwargs.get("model", self.config.model_name),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.config.presence_penalty),
            "stop": kwargs.get("stop", self.config.stop_sequences) or None,
            "stream": stream
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check LLM service health"""
        await self._ensure_session()
        
        results = {}
        for name, endpoint in [
            ("primary", self.config.model_endpoint),
            ("backup", self.config.backup_endpoint)
        ]:
            try:
                async with self._session.get(f"{endpoint}/health") as response:
                    results[name] = {
                        "status": "healthy" if response.status == 200 else "unhealthy",
                        "endpoint": endpoint,
                        "status_code": response.status
                    }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "endpoint": endpoint,
                    "error": str(e)
                }
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "model": self.config.model_name,
            "primary_endpoint": self.config.model_endpoint,
            "backup_endpoint": self.config.backup_endpoint
        }


class LLMServiceError(Exception):
    """LLM service error"""
    pass


# Prompt templates for common Covina tasks
class CovinaPrompts:
    """Pre-defined prompts for Covina document processing"""
    
    DOCUMENT_CLASSIFICATION = """Klassifiziere das folgende Dokument in eine der Kategorien:
- Vertrag (contract)
- Rechnung (invoice)
- Angebot (offer)
- Handelsregisterauszug (commercial_register)
- DSGVO-Dokument (gdpr)
- Korrespondenz (correspondence)
- Sonstiges (other)

Dokument:
{document_text}

Antworte im JSON-Format:
{{"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}}"""
    
    COMPLIANCE_CHECK = """Prüfe das folgende Dokument auf Compliance-Anforderungen:

Dokument:
{document_text}

Prüfe auf:
1. DSGVO-Konformität (personenbezogene Daten, Einwilligungen)
2. Handelsrechtliche Anforderungen
3. Aufbewahrungspflichten
4. Potenzielle Risiken

Antworte im JSON-Format:
{{
    "gdpr_compliant": true/false,
    "issues": ["..."],
    "recommendations": ["..."],
    "risk_level": "low/medium/high"
}}"""
    
    DOCUMENT_SUMMARY = """Erstelle eine strukturierte Zusammenfassung des folgenden Dokuments:

Dokument:
{document_text}

Struktur:
1. Hauptthema (1 Satz)
2. Wichtigste Punkte (max. 5)
3. Beteiligte Parteien
4. Relevante Daten/Fristen
5. Handlungsbedarf"""
    
    ENTITY_EXTRACTION = """Extrahiere alle relevanten Entitäten aus dem folgenden Dokument:

Dokument:
{document_text}

Extrahiere:
- Personen (Namen, Rollen)
- Organisationen (Firmen, Behörden)
- Adressen
- Daten und Fristen
- Geldbeträge
- Referenznummern

Antworte im JSON-Format:
{{
    "persons": [{"name": "...", "role": "..."}],
    "organizations": ["..."],
    "addresses": ["..."],
    "dates": ["..."],
    "amounts": ["..."],
    "references": ["..."]
}}"""
    
    LEGAL_ANALYSIS = """Analysiere das folgende Dokument aus rechtlicher Sicht:

Dokument:
{document_text}

Jurisdiction: {jurisdiction}

Analysiere:
1. Relevante Rechtsgebiete
2. Anwendbare Gesetze und Verordnungen
3. Rechtliche Risiken
4. Handlungsempfehlungen

Hinweis: Diese Analyse ersetzt keine professionelle Rechtsberatung."""
