import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.config import MAX_TOOL_CALL_ITERATIONS, PROMPT_VERSION, SYSTEM_PROMPT_TEMPLATE
from app.ai.guardrails import is_tool_allowed, scan_response, wrap_tool_result_as_untrusted
from app.ai.provider import GeminiProvider, LLMProvider, Message
from app.ai.retrieval import retrieve_methodology_context
from app.ai.tools import TOOL_REGISTRY, TOOL_SPECS
from app.config import get_settings
from app.db.models import AnalysisSnapshot, Instrument

_ALLOWED_TOOL_NAMES = frozenset(TOOL_REGISTRY.keys())


class AIAnalystService:
    """Orchestrates the bounded tool-calling loop between a provider and
    the typed-tool registry, then persists an AnalysisSnapshot with every
    field MASTER-PRD §21 requires for an important AI analysis (model,
    provider, prompt version, tool inputs, structured data snapshot,
    response, timestamp)."""

    def __init__(self, session: Session):
        self.session = session

    def _default_provider(self) -> LLMProvider:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError(
                "no LLM provider configured — set GEMINI_API_KEY, or pass an explicit "
                "provider (e.g. FixtureLLMProvider in tests)"
            )
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)

    def analyze(
        self,
        question: str,
        symbol: str | None = None,
        provider: LLMProvider | None = None,
    ) -> AnalysisSnapshot:
        provider = provider or self._default_provider()

        instrument_id: uuid.UUID | None = None
        if symbol:
            instrument = self.session.scalar(
                select(Instrument).where(Instrument.symbol == symbol.upper())
            )
            instrument_id = instrument.id if instrument else None

        methodology_chunks = retrieve_methodology_context(question)
        methodology_context = (
            "\n\n".join(f"[{c.source}] {c.text}" for c in methodology_chunks)
            if methodology_chunks
            else "(no relevant methodology context retrieved)"
        )
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(methodology_context=methodology_context)

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=question),
        ]
        tool_calls_log: list[dict[str, object]] = []
        structured_data: list[dict[str, object]] = []
        final_text = (
            "Analysis stopped: exceeded the maximum number of tool-call iterations "
            "without producing a final answer."
        )

        for _ in range(MAX_TOOL_CALL_ITERATIONS):
            response = provider.generate(messages, TOOL_SPECS)
            if not response.tool_calls:
                final_text = response.text or ""
                break

            for call in response.tool_calls:
                if not is_tool_allowed(call.tool_name, _ALLOWED_TOOL_NAMES):
                    result: dict[str, object] = {
                        "status": "REFUSED",
                        "reason": f"tool not permitted: {call.tool_name!r}",
                    }
                else:
                    tool_fn = TOOL_REGISTRY[call.tool_name]
                    try:
                        result = tool_fn(self.session, **call.arguments)
                    except TypeError as exc:
                        # a provider (especially a real LLM) can return
                        # tool-call arguments that don't match the tool's
                        # signature (missing/extra/mistyped) — treat that
                        # as a recorded failure, never an unhandled crash
                        # that would also skip persisting the snapshot.
                        result = {
                            "status": "ERROR",
                            "reason": f"invalid arguments for {call.tool_name!r}: {exc}",
                        }

                tool_calls_log.append(
                    {"tool_name": call.tool_name, "arguments": call.arguments, "result": result}
                )
                # a list, not a dict keyed by tool_name — the same tool can
                # legitimately be called more than once in one analysis
                # (e.g. comparing two symbols), and keying by name would
                # silently drop every call but the last from the
                # persisted grounding record.
                structured_data.append(
                    {"tool_name": call.tool_name, "arguments": call.arguments, "result": result}
                )

                messages.append(
                    Message(role="assistant", content=f"[requested tool: {call.tool_name}]")
                )
                messages.append(
                    Message(
                        role="tool",
                        content=wrap_tool_result_as_untrusted(call.tool_name, json.dumps(result)),
                        tool_call_id=call.call_id,
                        tool_name=call.tool_name,
                    )
                )

        guardrail_flags = scan_response(final_text)

        snapshot = AnalysisSnapshot(
            instrument_id=instrument_id,
            provider=provider.name,
            model=provider.model,
            prompt_version=PROMPT_VERSION,
            question=question,
            tool_calls=tool_calls_log,
            structured_data_snapshot=structured_data,
            response=final_text,
            guardrail_flags=guardrail_flags,
        )
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot
