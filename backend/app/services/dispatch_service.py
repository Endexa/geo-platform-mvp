"""
Dispatch Service — Parallel AI Engine Query Dispatch

Orchestrates sending audit queries to all three AI engines (OpenAI, Anthropic,
Perplexity) in parallel using ThreadPoolExecutor. Integrates with the existing
cache, rate limiter, and cost tracking infrastructure from Phase 1.

Key design choices:
- Each ThreadPoolExecutor thread creates its OWN SQLAlchemy Session (thread-safe)
- Each thread creates its own asyncio event loop for async cache/limiter calls
- Rate limiter acquire() is async, release() is sync
- Engine failures are isolated: one engine failing does not affect others
- Budget is checked before each query dispatch batch
"""

import asyncio
import concurrent.futures
import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import litellm
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.outbound_limiter import get_provider_limiter
from app.models.audit_query import AuditQuery
from app.models.engine_response import EngineResponse
from app.services.cache_service import AICacheService
from app.services.cost_service import CostTrackingService

# ---------------------------------------------------------------------------
# Engine configuration — model names read from settings at runtime
# ---------------------------------------------------------------------------

ENGINE_CONFIG = {
    "openai": {
        "model_setting": "DISPATCH_MODEL_OPENAI",
        "provider": "openai",
        "api_key_setting": "OPENAI_API_KEY",
    },
    "anthropic": {
        "model_setting": "DISPATCH_MODEL_ANTHROPIC",
        "provider": "anthropic",
        "api_key_setting": "ANTHROPIC_API_KEY",
    },
    "perplexity": {
        "model_setting": "DISPATCH_MODEL_PERPLEXITY",
        "provider": "perplexity",
        "api_key_setting": "PERPLEXITYAI_API_KEY",
    },
    "gemini": {
        "model_setting": "DISPATCH_MODEL_GEMINI",
        "provider": "gemini",
        "api_key_setting": "GEMINI_API_KEY",
    },
    "mistral": {
        "model_setting": "DISPATCH_MODEL_MISTRAL",
        "provider": "mistral",
        "api_key_setting": "MISTRAL_API_KEY",
    },
}


@dataclass
class DispatchResult:
    """Summary of a dispatch_all_queries run."""

    total_queries: int
    total_responses: int
    total_failures: int
    budget_exceeded: bool


class DispatchService:
    """Dispatches audit queries to all AI engines in parallel."""

    def __init__(self, db: Session):
        self.db = db
        # Pre-compute which engines have valid API keys (once, not per-query)
        self._active_engines = {}
        for name, config in ENGINE_CONFIG.items():
            api_key = getattr(settings, config["api_key_setting"], "")
            if api_key:
                self._active_engines[name] = config
            else:
                logger.info(f"Engine {name} skipped: no API key configured")
        if not self._active_engines:
            logger.warning("No AI engines have API keys configured!")

    def dispatch_all_queries(
        self, audit_id: UUID, queries: list[AuditQuery]
    ) -> DispatchResult:
        """Dispatch all queries to engines that have valid API keys.

        Iterates through queries, dispatching each to active engines in parallel.
        Checks budget before each query. Stops if budget is exceeded.
        """
        total_responses = 0
        total_failures = 0
        budget_exceeded = False

        if not self._active_engines:
            logger.warning(f"No active engines for audit {audit_id}, skipping dispatch")
            return DispatchResult(
                total_queries=len(queries),
                total_responses=0,
                total_failures=0,
                budget_exceeded=False,
            )

        for idx, query in enumerate(queries):
            # Budget check before each query dispatch
            if not CostTrackingService(self.db).check_budget(audit_id):
                logger.warning(
                    f"Budget exceeded for audit {audit_id} at query {idx + 1}/{len(queries)}. "
                    "Stopping dispatch."
                )
                budget_exceeded = True
                break

            logger.info(
                f"Dispatching query {idx + 1}/{len(queries)} "
                f"(audit={audit_id}, query={query.id})"
            )
            responses = self._dispatch_query_to_engines(audit_id, query)

            for resp in responses:
                if resp.error_message:
                    total_failures += 1
                else:
                    total_responses += 1

        result = DispatchResult(
            total_queries=len(queries),
            total_responses=total_responses,
            total_failures=total_failures,
            budget_exceeded=budget_exceeded,
        )
        logger.info(
            f"Dispatch complete for audit {audit_id}: "
            f"{result.total_responses} responses, {result.total_failures} failures, "
            f"budget_exceeded={result.budget_exceeded}"
        )
        return result

    def _dispatch_query_to_engines(
        self, audit_id: UUID, query: AuditQuery
    ) -> list[EngineResponse]:
        """Dispatch a single query to all three engines in parallel.

        Uses ThreadPoolExecutor for parallel execution. Each engine failure is
        isolated — one engine failing does not affect the others.
        """
        responses: list[EngineResponse] = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=settings.DISPATCH_MAX_WORKERS
        ) as executor:
            futures = {
                executor.submit(
                    self._call_engine, engine_name, audit_id, query
                ): engine_name
                for engine_name in self._active_engines
            }

            # Collect results with a generous timeout above per-engine timeout
            for future in concurrent.futures.as_completed(
                futures, timeout=settings.DISPATCH_TIMEOUT_SECONDS + 10
            ):
                engine_name = futures[future]
                try:
                    response = future.result()
                    responses.append(response)
                except Exception as exc:
                    logger.error(
                        f"Engine {engine_name} failed for query {query.id}: {exc}"
                    )
                    # Create error EngineResponse and persist in a thread-safe session
                    error_resp = self._create_error_response(
                        engine_name, audit_id, query, str(exc)
                    )
                    responses.append(error_resp)

        return responses

    def _call_engine(
        self, engine_name: str, audit_id: UUID, query: AuditQuery
    ) -> EngineResponse:
        """Call a single AI engine for a query.

        Runs in a ThreadPoolExecutor thread. Creates its own DB session and
        asyncio event loop for thread safety.
        """
        config = ENGINE_CONFIG[engine_name]
        model = getattr(settings, config["model_setting"])
        api_key = getattr(settings, config["api_key_setting"])

        # Validate API key before attempting call
        if not api_key:
            logger.warning(f"API key not configured for {engine_name}, skipping")
            return self._create_error_response(
                engine_name,
                audit_id,
                query,
                f"API key not configured for {engine_name}",
            )

        messages = [{"role": "user", "content": query.query_text}]

        # Each thread gets its own event loop and DB session
        loop = asyncio.new_event_loop()
        thread_db = SessionLocal()
        cache = AICacheService()
        limiter = get_provider_limiter(config["provider"])

        try:
            # --- Cache check ---
            cached_data = loop.run_until_complete(
                cache.get(engine_name, model, messages, settings.DISPATCH_TEMPERATURE)
            )

            if cached_data is not None:
                logger.info(f"Cache hit for {engine_name}/{model} query={query.id}")
                response_obj = EngineResponse(
                    audit_query_id=query.id,
                    engine=engine_name,
                    model_version=cached_data.get("model_version", model),
                    response_text=cached_data.get("response_text", ""),
                    prompt_tokens=cached_data.get("prompt_tokens", 0),
                    completion_tokens=cached_data.get("completion_tokens", 0),
                    cost_usd=Decimal("0"),
                    cached=True,
                    citations=cached_data.get("citations"),
                )
                thread_db.add(response_obj)
                thread_db.commit()
                thread_db.refresh(response_obj)

                # Record zero-cost entry
                CostTrackingService(thread_db).record_cost(
                    audit_id=audit_id,
                    engine=engine_name,
                    model=cached_data.get("model_version", model),
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost_usd=Decimal("0"),
                    cached=True,
                )
                logger.info(f"Cached response recorded for {engine_name} query={query.id}")
                return response_obj

            # --- Cache miss: call the engine ---
            logger.info(f"Cache miss for {engine_name}/{model} query={query.id}")

            # Acquire rate limiter
            loop.run_until_complete(limiter.acquire())
            logger.debug(f"Rate limiter acquired for {engine_name}")

            try:
                # LLM call via LiteLLM
                logger.info(f"Calling {engine_name}/{model} for query={query.id}")
                try:
                    response = litellm.completion(
                        model=model,
                        messages=messages,
                        temperature=settings.DISPATCH_TEMPERATURE,
                        timeout=settings.DISPATCH_TIMEOUT_SECONDS,
                        api_key=api_key,
                    )
                except litellm.AuthenticationError as auth_err:
                    logger.warning(f"Engine {engine_name} auth failed (invalid/expired key): {auth_err}")
                    error_resp = EngineResponse(
                        audit_query_id=query.id,
                        engine=engine_name,
                        model_version=model,
                        response_text="",
                        prompt_tokens=0,
                        completion_tokens=0,
                        cost_usd=Decimal("0"),
                        error_message=f"Authentication failed: invalid or expired API key for {engine_name}",
                    )
                    thread_db.add(error_resp)
                    thread_db.commit()
                    thread_db.refresh(error_resp)
                    # Remove this engine from active engines so we don't retry on next query
                    self._active_engines.pop(engine_name, None)
                    return error_resp

                # Extract metadata
                response_text = response.choices[0].message.content or ""
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                cost = response._hidden_params.get("response_cost", 0.0)
                model_version = response.model or model

                # Extract Perplexity citations from API response
                citations_list = None
                if engine_name == "perplexity":
                    citations_list = getattr(response, "citations", None)
                    if citations_list is None:
                        citations_list = response._hidden_params.get("citations", None)
                    if citations_list:
                        logger.info(
                            f"Captured {len(citations_list)} citations from Perplexity "
                            f"for query={query.id}"
                        )

                # For non-Perplexity engines, extract inline URLs as citations
                if engine_name != "perplexity" and response_text:
                    url_pattern = re.compile(
                        r'https?://[^\s\)\]\},\"\']+', re.IGNORECASE
                    )
                    inline_urls = url_pattern.findall(response_text)
                    if inline_urls:
                        citations_list = sorted(set(inline_urls))

                # Perplexity surcharge
                if engine_name == "perplexity":
                    cost += settings.PERPLEXITY_REQUEST_SURCHARGE
                    logger.debug(
                        f"Added Perplexity surcharge: +${settings.PERPLEXITY_REQUEST_SURCHARGE}"
                    )

                # Cache the response (include citations)
                cache_payload = {
                    "response_text": response_text,
                    "model_version": model_version,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "citations": citations_list,
                }
                loop.run_until_complete(
                    cache.set(
                        engine_name,
                        model,
                        messages,
                        settings.DISPATCH_TEMPERATURE,
                        cache_payload,
                    )
                )
                logger.debug(f"Response cached for {engine_name}/{model}")

                # Record cost
                cost_decimal = Decimal(str(cost))
                CostTrackingService(thread_db).record_cost(
                    audit_id=audit_id,
                    engine=engine_name,
                    model=model_version,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_decimal,
                )
                logger.info(
                    f"Cost recorded for {engine_name}: ${cost_decimal} "
                    f"(tokens: {prompt_tokens}+{completion_tokens})"
                )

                # Create and persist EngineResponse
                response_obj = EngineResponse(
                    audit_query_id=query.id,
                    engine=engine_name,
                    model_version=model_version,
                    response_text=response_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_decimal,
                    cached=False,
                    citations=citations_list,
                )
                thread_db.add(response_obj)
                thread_db.commit()
                thread_db.refresh(response_obj)

                logger.info(
                    f"Engine {engine_name} completed for query={query.id}: "
                    f"{len(response_text)} chars, ${cost_decimal}"
                )
                return response_obj

            finally:
                # Release rate limiter (sync)
                limiter.release()
                logger.debug(f"Rate limiter released for {engine_name}")

        except Exception as exc:
            logger.error(
                f"Engine {engine_name} error for query={query.id}: {exc}"
            )
            # Create error response
            error_resp = EngineResponse(
                audit_query_id=query.id,
                engine=engine_name,
                model_version=model,
                response_text="",
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=Decimal("0"),
                error_message=str(exc),
            )
            thread_db.add(error_resp)
            thread_db.commit()
            thread_db.refresh(error_resp)
            return error_resp

        finally:
            thread_db.close()
            loop.close()

    def _create_error_response(
        self,
        engine_name: str,
        audit_id: UUID,
        query: AuditQuery,
        error_message: str,
    ) -> EngineResponse:
        """Create and persist an error EngineResponse using a thread-safe session."""
        config = ENGINE_CONFIG[engine_name]
        model = getattr(settings, config["model_setting"])

        thread_db = SessionLocal()
        try:
            error_resp = EngineResponse(
                audit_query_id=query.id,
                engine=engine_name,
                model_version=model,
                response_text="",
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=Decimal("0"),
                error_message=error_message,
            )
            thread_db.add(error_resp)
            thread_db.commit()
            thread_db.refresh(error_resp)
            return error_resp
        finally:
            thread_db.close()
