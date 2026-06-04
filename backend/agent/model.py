import os
from typing import Generator
import uuid
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)
from backend.agent.config import CATALOG_SCHEMA, MAX_TOKENS, MAX_ITERATIONS, LLM_MODEL_NAME


# Process-wide cache of guardrail detection, keyed by endpoint name. An endpoint's
# guardrail configuration is static for the app's lifetime, so we only pay for the
# serving_endpoints.get round-trip once instead of on every request (load_context runs
# per chat message).
_OUTPUT_GUARDRAIL_CACHE: dict[str, bool] = {}


def _has_output_guardrails(w, endpoint_name) -> bool:
    """Return True if the serving endpoint has AI Gateway output guardrails configured.

    AI Gateway routes with output guardrails buffer the full response to inspect it, so
    they cannot stream token-by-token. We use this to decide whether to stream.
    Any failure to introspect the endpoint is treated as "no guardrails" so we default
    to streaming (direct foundation model endpoints stream fine).

    The result is cached per process so this costs at most one API call per endpoint.
    """
    if endpoint_name in _OUTPUT_GUARDRAIL_CACHE:
        return _OUTPUT_GUARDRAIL_CACHE[endpoint_name]

    try:
        endpoint = w.serving_endpoints.get(endpoint_name)
        ai_gateway = getattr(endpoint, "ai_gateway", None)
        guardrails = getattr(ai_gateway, "guardrails", None) if ai_gateway else None
        output = getattr(guardrails, "output", None) if guardrails else None
        # output is AiGatewayGuardrailParameters; it is only "active" if at least one
        # guardrail dimension is actually configured.
        result = output is not None and any(
            getattr(output, attr, None)
            for attr in ("invalid_keywords", "pii", "safety", "valid_topics")
        )
    except Exception:
        result = False

    _OUTPUT_GUARDRAIL_CACHE[endpoint_name] = result
    return result


def _extract_text(message) -> str:
    """Extract plain answer text from a message or message chunk content."""
    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    text = ""
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in ("text", "output_text") and "text" in block:
                    text += block.get("text", "")
            elif isinstance(block, str):
                text += block
    return text


def _extract_reasoning(message) -> str:
    """Extract reasoning/thinking content (extended thinking) from a message/chunk."""
    parts = []
    content = getattr(message, "content", None)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type")
                if btype in ("reasoning", "thinking"):
                    parts.append(block.get("text") or block.get("thinking") or "")
                    summary = block.get("summary")
                    if isinstance(summary, list):
                        for s in summary:
                            if isinstance(s, dict):
                                parts.append(s.get("text", ""))
    additional = getattr(message, "additional_kwargs", None)
    if isinstance(additional, dict):
        rc = additional.get("reasoning_content")
        if isinstance(rc, str):
            parts.append(rc)
    return "".join(p for p in parts if p)


def _finish_reason(chunk) -> str:
    """Return the OpenAI-style finish_reason for a streamed chunk, if present.

    A turn that finishes with "tool_calls" is a reasoning/acting step, not the final
    answer. This is emitted on the last chunk of the turn and survives external-model
    proxies (which often drop incremental tool_call_chunks), so it is our most reliable
    early signal that a turn's text belongs in the thinking panel rather than the answer.
    """
    meta = getattr(chunk, "response_metadata", None)
    if isinstance(meta, dict) and meta.get("finish_reason"):
        return meta["finish_reason"]
    meta = getattr(chunk, "additional_kwargs", None)
    if isinstance(meta, dict) and meta.get("finish_reason"):
        return meta["finish_reason"]
    return ""


def _has_tool_calls(chunk) -> bool:
    """True if the chunk carries (even partial) tool calls."""
    return bool(getattr(chunk, "tool_calls", None)) or bool(
        getattr(chunk, "tool_call_chunks", None)
    )


def _clean_text(text: str) -> str:
    """Strip tool/skill XML scaffolding the model may leak into the visible answer."""
    import re
    if not text:
        return text
    if "<read_skill_result>" in text:
        text = re.sub(r'<read_skill_result>.*?</read_skill_result>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_response>.*?</tool_response>', '', text, flags=re.DOTALL)
    return text.replace('<tool_response>', '').strip()


# Some endpoints (notably external-model proxies) make the model narrate tool use as inline
# text — e.g. `<tool_call>{...}</tool_call> <tool_response>{...}</tool_response>` — instead of
# using native function calling. This scaffolding must never reach the visible answer.
_SCAFFOLD = {
    "<tool_call>": "</tool_call>",
    "<tool_response>": "</tool_response>",
    "<read_skill_result>": "</read_skill_result>",
}


class _AnswerSanitizer:
    """Incrementally strips text-based tool scaffolding out of the streamed answer.

    Complete ``<tool_call>`` blocks surface their tool name as reasoning; ``<tool_response>``
    and ``<read_skill_result>`` blocks are dropped (they're internal). Partial tags or
    unclosed blocks at the end of the buffer are held back until more text arrives, so a tag
    split across streaming chunks is never shown to the user.
    """

    def __init__(self):
        self._raw = ""
        self._consumed = 0  # prefix of _raw already turned into clean output
        self._tools = []  # tool names discovered, in order

    def feed(self, text: str):
        """Append streamed text; return (clean_answer_delta, new_tool_names)."""
        import re
        self._raw += text
        clean, new_names = [], []
        i, n = self._consumed, len(self._raw)
        while i < n:
            lt = self._raw.find("<", i)
            if lt == -1:
                clean.append(self._raw[i:])
                i = n
                break
            if lt > i:
                clean.append(self._raw[i:lt])
            opener = next((op for op in _SCAFFOLD if self._raw.startswith(op, lt)), None)
            if opener:
                close = _SCAFFOLD[opener]
                ce = self._raw.find(close, lt + len(opener))
                if ce == -1:
                    i = lt  # block not closed yet — hold back
                    break
                inner = self._raw[lt + len(opener):ce]
                if opener == "<tool_call>":
                    m = re.search(r'"name"\s*:\s*"([^"]+)"', inner)
                    if m and m.group(1) not in self._tools:
                        self._tools.append(m.group(1))
                        new_names.append(m.group(1))
                i = ce + len(close)
            else:
                tail = self._raw[lt:]
                boundaries = list(_SCAFFOLD) + list(_SCAFFOLD.values())
                if any(b.startswith(tail) for b in boundaries):
                    i = lt  # possible partial tag — hold back
                    break
                clean.append("<")
                i = lt + 1
        self._consumed = i
        return "".join(clean), new_names

    def flush(self) -> str:
        """At end of stream, return any held-back tail that wasn't real scaffolding."""
        rest = self._raw[self._consumed:]
        if rest.startswith("<") and any(op.startswith(rest) or rest.startswith(op) for op in _SCAFFOLD):
            return ""  # dangling/incomplete scaffold — drop it
        return rest

    @property
    def tools(self):
        return list(self._tools)


def _build_tool_error_middleware():
    """Middleware that turns any tool exception into an error ToolMessage.

    Without this, a tool that raises (e.g. a UC function called with a missing/None
    parameter, or a warehouse permission error) propagates out of the agent and crashes
    the whole stream with a 500. Returning the error as a ToolMessage instead lets the
    model see what went wrong and recover (retry with correct arguments, or explain the
    failure to the user). Returns a list so it can be spread into create_agent(middleware=).
    """
    try:
        from langchain.agents.middleware import wrap_tool_call
        from langchain_core.messages import ToolMessage

        @wrap_tool_call
        def tolerate_tool_errors(request, handler):
            try:
                return handler(request)
            except Exception as e:
                tc = request.tool_call or {}
                return ToolMessage(
                    content=f"Error running tool {tc.get('name')}: {e}",
                    tool_call_id=tc.get("id", ""),
                    name=tc.get("name"),
                    status="error",
                )

        return [tolerate_tool_errors]
    except Exception as e:
        print(f"Warning: could not install tool-error middleware: {e}")
        return []


class EDHAgent(ResponsesAgent):
    def __init__(self):
        self.agent = None
        self.streaming_enabled = True

    def load_context(self, context=None, user_token=None, selected_tools=None, selected_skills=None, user_prompt=None):
        import os
        from databricks.sdk import WorkspaceClient
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_agent
        from backend.tools.registry import get_langchain_tools, discover_skills
        
        # Initialize Databricks SDK
        is_app = bool(os.environ.get("DATABRICKS_APP_NAME"))
        if user_token:
            # Use On-Behalf-Of (OBO) authentication
            self.w = WorkspaceClient(token=user_token, auth_type="pat")
        elif is_app:
            self.w = WorkspaceClient()
        else:
            profile = os.getenv("DATABRICKS_PROFILE", "myenv")
            self.w = WorkspaceClient(profile=profile)
        
        # Get authentication token and host
        headers = self.w.config.authenticate()
        if isinstance(headers, dict) and "Authorization" in headers:
            token = headers["Authorization"].replace("Bearer ", "")
        else:
            token = os.environ.get("DATABRICKS_TOKEN") or self.w.config.token
            
        host = self.w.config.host.rstrip('/')
        if is_app and host and not host.startswith("http"):
            host = f"https://{host}"
        
        # AI Gateway routes with output guardrails must buffer the full response to inspect
        # it, so they can't stream. Detect this and only stream when guardrails are absent.
        self.streaming_enabled = not _has_output_guardrails(self.w, LLM_MODEL_NAME)

        # Databricks serving endpoints (foundation models, external models, and AI Gateway
        # routes alike) are reached through the OpenAI-compatible /serving-endpoints path.
        # Any AI Gateway guardrails configured on the endpoint are applied transparently here.
        base_url = f"{host}/serving-endpoints"
        llm = ChatOpenAI(
            model=LLM_MODEL_NAME, # The serving endpoint name (e.g. the EDH agent serving endpoint)
            api_key=token,
            base_url=base_url,
            streaming=self.streaming_enabled,
            max_tokens=MAX_TOKENS,
        )
        
        # Build System Prompt
        try:
            # When running in MLflow Model Serving, the context object provides the path
            if context and hasattr(context, "artifacts") and "prompt" in context.artifacts:
                prompt_path = context.artifacts["prompt"]
            else:
                prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
                
            with open(prompt_path, "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback if file isn't bundled correctly
            system_prompt = "You are the EDH Agent, an enterprise data assistant for Qualcomm running in Databricks."
        
        # Get Skills
        system_prompt += discover_skills(w=self.w, selected_skills=selected_skills, user_token=user_token)

        # Append the user-supplied main prompt last so it takes precedence over the
        # baked-in instructions (without letting it silently discard tool/skill guidance).
        if user_prompt and str(user_prompt).strip():
            system_prompt += (
                "\n\n## Additional user instructions\n"
                "The current user has provided the following instructions. Follow them, "
                "unless they conflict with the safety and tool-usage rules above.\n\n"
                f"{str(user_prompt).strip()}\n"
            )

        # Get Tools
        tools = get_langchain_tools(w=self.w, selected_tools=selected_tools, user_token=user_token)
        
        # Create the LangGraph agent. The tool-error middleware keeps a single failing tool
        # call (bad args, permissions, etc.) from crashing the whole streamed response.
        self.agent = create_agent(
            llm, tools, system_prompt=system_prompt, middleware=_build_tool_error_middleware()
        )

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        
        # Start a local MLflow trace explicitly if one isn't active
        local_trace = None
        try:
            active_trace_id = mlflow.get_last_active_trace_id()
            if not active_trace_id:
                local_trace = mlflow.start_trace(name="agent_predict")
        except Exception:
            pass
            
        try:
            # Convert MLflow input messages to Langchain format
            cc_msgs = to_chat_completions_input([i.model_dump() for i in request.input])
            
            session_id = "default_thread"
            if request.custom_inputs and "session_id" in request.custom_inputs:
                session_id = request.custom_inputs["session_id"]
                
            # recursion_limit caps LangGraph super-steps (~2 per agent turn: model call + tool
            # execution), so map the configured MAX_ITERATIONS (agent loops) to 2*N+1 nodes.
            config = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 2 * MAX_ITERATIONS + 1,
            }
            
            if self.streaming_enabled:
                yield from self._predict_streaming(cc_msgs, config)
            else:
                # Fallback for AI Gateway routes with output guardrails (no token streaming).
                yield from self._predict_blocking(cc_msgs, config)
            
        finally:
            if local_trace:
                try:
                    mlflow.end_trace(status="OK")
                except Exception:
                    pass

    def _reasoning_event(self, delta: str, item_id: str) -> ResponsesAgentStreamEvent:
        """Emit a thinking/reasoning delta. Uses a custom event type so it stays distinct
        from the visible answer deltas while remaining valid for ResponsesAgent."""
        return ResponsesAgentStreamEvent(
            type="response.reasoning_text.delta",
            delta=delta,
            item_id=item_id,
        )

    def _predict_streaming(self, cc_msgs, config) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Token-by-token streaming path used when the endpoint has no output guardrails.

        Streams the final answer as text deltas, and surfaces the agent's intermediate
        steps (extended-thinking content + tool calls) as reasoning deltas.
        """
        from langchain_core.messages import AIMessageChunk, ToolMessage

        answer_item_id = str(uuid.uuid4())
        reasoning_item_id = str(uuid.uuid4())
        answer_text = ""
        tool_calls_executed = []
        announced_tools = set()

        # We stream every model turn's text optimistically as the answer. A turn that is
        # actually a reasoning/acting step (not the final answer) is identified by any of:
        #   1. finish_reason == "tool_calls" on the turn's final chunk (most reliable; it
        #      survives external-model proxies even when the tool itself never returns —
        #      e.g. the agent errors or stops "early"),
        #   2. tool_calls / tool_call_chunks present on a streamed chunk, or
        #   3. a ToolMessage arriving afterwards.
        # When any of these fire we "reclassify" that turn's already-streamed text out of
        # the answer and into the thinking panel. The final answer is the turn that ends
        # without a tool-call signal, so it stays put.
        pending_msg_id = None  # model turn currently being streamed as the answer
        pending_text = ""  # its accumulated (sanitized) text, eligible for reclassification
        reclassified_ids = set()  # turns already moved to the thinking panel
        sanitizer = _AnswerSanitizer()  # strips inline tool scaffolding from the answer

        def reclassify_pending():
            nonlocal answer_text, pending_text, pending_msg_id
            leaked = pending_text
            if pending_msg_id is not None:
                reclassified_ids.add(pending_msg_id)
            pending_text = ""
            pending_msg_id = None
            if not leaked:
                return None
            if answer_text.endswith(leaked):
                answer_text = answer_text[: -len(leaked)]
            return ResponsesAgentStreamEvent(
                type="response.reasoning_reclassify",
                delta=leaked,
                item_id=reasoning_item_id,
            )

        def announce_tool(name):
            if not (name and name.strip()) or name in announced_tools:
                return None
            announced_tools.add(name)
            tool_calls_executed.append({"tool_name": name, "status": "executed inside agent"})
            return self._reasoning_event(f"Using {name}\n", reasoning_item_id)

        for chunk, _metadata in self.agent.stream(
            {"messages": cc_msgs}, config=config, stream_mode="messages"
        ):
            if isinstance(chunk, ToolMessage):
                event = reclassify_pending()
                if event is not None:
                    yield event
                event = announce_tool(getattr(chunk, "name", None))
                if event is not None:
                    yield event
                continue

            if not isinstance(chunk, AIMessageChunk):
                continue

            reasoning_delta = _extract_reasoning(chunk)
            if reasoning_delta:
                yield self._reasoning_event(reasoning_delta, reasoning_item_id)

            msg_id = getattr(chunk, "id", None) or "msg"
            text_delta = _extract_text(chunk)
            if text_delta:
                if msg_id in reclassified_ids:
                    # Turn already known to be a reasoning step: keep its text in Thoughts.
                    yield self._reasoning_event(text_delta, reasoning_item_id)
                else:
                    if msg_id != pending_msg_id:
                        pending_msg_id = msg_id
                        pending_text = ""
                        sanitizer = _AnswerSanitizer()
                    # Strip any inline tool scaffolding before it reaches the answer; the
                    # tool names it finds are surfaced in the thinking panel instead.
                    clean_delta, new_names = sanitizer.feed(text_delta)
                    for name in new_names:
                        event = announce_tool(name)
                        if event is not None:
                            yield event
                    if clean_delta:
                        answer_text += clean_delta
                        pending_text += clean_delta
                        yield ResponsesAgentStreamEvent(
                            **self.create_text_delta(delta=clean_delta, item_id=answer_item_id)
                        )

            # Early/robust signal that this turn is a tool step — reclassify before the tool
            # (if any) even returns, so a turn that ends "early" can't leak into the answer.
            if msg_id == pending_msg_id and (
                _has_tool_calls(chunk) or _finish_reason(chunk) == "tool_calls"
            ):
                event = reclassify_pending()
                if event is not None:
                    yield event

            for tc in (getattr(chunk, "tool_calls", None) or []):
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                event = announce_tool(name)
                if event is not None:
                    yield event

        # Emit any text the sanitizer held back waiting on a tag that never completed.
        tail = sanitizer.flush()
        if tail and pending_msg_id not in reclassified_ids:
            answer_text += tail
            yield ResponsesAgentStreamEvent(
                **self.create_text_delta(delta=tail, item_id=answer_item_id)
            )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=_clean_text(answer_text), id=answer_item_id),
            custom_outputs={"tool_calls": tool_calls_executed},
        )

    def _predict_blocking(self, cc_msgs, config) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Non-streaming path used when the endpoint enforces output guardrails.

        The answer can only be delivered as a single block, but we still surface the
        agent's intermediate reasoning and tool calls for the thinking panel.
        """
        answer_item_id = str(uuid.uuid4())
        reasoning_item_id = str(uuid.uuid4())
        tool_calls_executed = []

        result = self.agent.invoke({"messages": cc_msgs}, config=config)
        messages = result.get("messages", [])

        # Surface intermediate steps as reasoning before the final answer.
        for msg in messages:
            if type(msg).__name__ not in ("AIMessage", "AIMessageChunk"):
                continue

            reasoning_delta = _extract_reasoning(msg)
            if reasoning_delta:
                yield self._reasoning_event(reasoning_delta, reasoning_item_id)

            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                preamble = _extract_text(msg)
                if preamble.strip():
                    yield self._reasoning_event(preamble.strip() + "\n", reasoning_item_id)
                for tc in tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                    if name and name.strip():
                        if not any(t["tool_name"] == name for t in tool_calls_executed):
                            tool_calls_executed.append({"tool_name": name, "status": "executed inside agent"})
                        yield self._reasoning_event(f"Calling `{name}`\n", reasoning_item_id)

        # Final answer is the last AI message that carries text and no tool calls.
        answer_text = ""
        for msg in reversed(messages):
            if type(msg).__name__ in ("AIMessage", "AIMessageChunk") and not getattr(msg, "tool_calls", None):
                text = _extract_text(msg)
                if text:
                    answer_text = text
                    break

        answer_text = _clean_text(answer_text)
        if answer_text:
            yield ResponsesAgentStreamEvent(
                **self.create_text_delta(delta=answer_text, item_id=answer_item_id)
            )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=answer_text, id=answer_item_id),
            custom_outputs={"tool_calls": tool_calls_executed},
        )

def log_agent_model():
    import mlflow
    mlflow.langchain.autolog()
    
    with mlflow.start_run():
        logged_agent_info = mlflow.pyfunc.log_model(
            python_model="backend/agent/model.py",
            name="edh-agent",
            artifacts={"prompt": "backend/agent/prompt.md"}
        )
        return logged_agent_info

if __name__ == "__main__":
    pass
