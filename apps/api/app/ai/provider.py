"""Provider-agnostic LLM layer (MASTER-TDD §18: "Provider-agnostic LLM
layer with typed tools"). `LLMProvider` is the interface every adapter
implements; `FixtureLLMProvider` is deterministic and network-free —
every automated test uses it exclusively. `GeminiProvider` is the one
real adapter (MASTER-PRD §28 "AI provider/model" decision, recorded in
DECISION-LOG.md), constructed only when `settings.gemini_api_key` is
set; nothing in this package requires it to be installed or configured
to run the test suite.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Describes one callable tool to the model. `parameters_schema` is a
    plain JSON-schema-shaped dict (provider adapters translate it into
    whatever native format they need)."""

    name: str
    description: str
    parameters_schema: dict[str, object]


@dataclass(frozen=True, slots=True)
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None


@dataclass(frozen=True, slots=True)
class ToolCallRequest:
    call_id: str
    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Exactly one of tool_calls or text is meaningful: a non-empty
    tool_calls list means the model wants tool results before it can
    continue; otherwise text is the final answer."""

    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    text: str | None = None


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, messages: list[Message], tools: list[ToolSpec]) -> ProviderResponse: ...


class FixtureLLMProvider:
    """Deterministic, network-free provider used by every automated
    test. Returns a pre-scripted sequence of ProviderResponse objects,
    one per call to generate(), regardless of the actual message/tool
    content — the caller (test) controls the script, not this class."""

    name = "fixture"

    def __init__(self, script: list[ProviderResponse], model: str = "fixture-v1"):
        self._script = list(script)
        self._call_count = 0
        self.model = model

    def generate(self, messages: list[Message], tools: list[ToolSpec]) -> ProviderResponse:
        if self._call_count >= len(self._script):
            raise RuntimeError(
                f"FixtureLLMProvider script exhausted after {self._call_count} calls — "
                "the orchestrator asked for more turns than the test scripted"
            )
        response = self._script[self._call_count]
        self._call_count += 1
        return response


class GeminiProvider:
    """Real adapter over Google's Gemini API (google-genai SDK), the
    free-tier provider chosen for this phase (see DECISION-LOG.md). Never
    imported/constructed by the test suite — the `google-genai` import is
    local to __init__ so the rest of this package never requires network
    access or an API key just to be tested."""

    name = "gemini"

    def __init__(self, api_key: str, model: str):
        from google import genai  # local import: only the real adapter needs this

        self._client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, messages: list[Message], tools: list[ToolSpec]) -> ProviderResponse:
        from google.genai import types

        system_instruction = "\n\n".join(m.content for m in messages if m.role == "system")

        contents: list[types.Content] = []
        for message in messages:
            if message.role == "system":
                continue  # handled separately via system_instruction
            if message.role == "user":
                contents.append(
                    types.Content(role="user", parts=[types.Part(text=message.content)])
                )
            elif message.role == "assistant":
                contents.append(
                    types.Content(role="model", parts=[types.Part(text=message.content)])
                )
            elif message.role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=message.tool_name or "unknown_tool",
                                response={"result": message.content},
                            )
                        ],
                    )
                )

        genai_tools: list[types.Tool] | None = (
            [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters_json_schema=tool.parameters_schema,
                        )
                        for tool in tools
                    ]
                )
            ]
            if tools
            else None
        )
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            tools=genai_tools,  # type: ignore[arg-type]  # google-genai's union type is broader than needed here
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        response = self._client.models.generate_content(
            model=self.model, contents=contents, config=config
        )

        candidate = response.candidates[0] if response.candidates else None
        parts = candidate.content.parts if candidate and candidate.content else None

        tool_calls: list[ToolCallRequest] = []
        text_parts: list[str] = []
        for index, part in enumerate(parts or []):
            function_call = part.function_call
            if function_call is not None and function_call.name:
                tool_calls.append(
                    ToolCallRequest(
                        call_id=f"{function_call.name}-{index}",
                        tool_name=function_call.name,
                        arguments=dict(function_call.args or {}),
                    )
                )
            elif part.text:
                text_parts.append(part.text)

        if tool_calls:
            return ProviderResponse(tool_calls=tool_calls)
        return ProviderResponse(text="\n".join(text_parts))
