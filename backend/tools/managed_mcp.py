"""Thin client + LangChain tool wrappers for Databricks **managed MCP servers**.

Databricks exposes managed MCP servers over plain JSON-RPC (streamable HTTP) at:
  - ``/api/2.0/mcp/sql``                 -> execute_sql / execute_sql_read_only / poll_sql_result
  - ``/api/2.0/mcp/genie``              -> genie_ask / genie_poll_response (workspace-wide)
  - ``/api/2.0/mcp/genie/{space_id}``   -> query_space_{id} / poll_response_{id} (per-space)

These endpoints accept stateless JSON-RPC POSTs (no MCP ``initialize`` handshake), so a small
``requests``-based client is enough — we don't need an async MCP SDK.

Genie and long SQL statements are asynchronous: the "ask"/"execute" call returns an id, and a
companion "poll" tool is called until the work reaches a terminal state. We hide that loop *inside*
each tool so the agent sees a single blocking call that returns the final answer — this keeps the
agent's reasoning loop short (no dozens of poll round-trips) and matches how the old hand-rolled
``ask_genie`` behaved.

Auth is via a bearer token (the caller passes the user's OBO token for governance parity).
"""

import hashlib
import json
import os
import re
import time

import requests

# Process-wide cache for list_genies output, keyed by user token (spaces are user-specific).
_GENIE_SPACES_CACHE = {}
_GENIE_SPACES_TTL_S = 300


# Genie's terminal status spelling varies across the workspace-wide vs per-space MCP servers and
# across releases, so match a few synonyms rather than just "COMPLETED".
GENIE_TERMINAL_OK = {"COMPLETED", "COMPLETE", "SUCCEEDED", "SUCCESS", "DONE", "FINISHED"}
GENIE_TERMINAL_BAD = {"FAILED", "CANCELLED", "CANCELED", "QUERY_RESULT_EXPIRED", "ERROR"}


def _genie_status_ok(status) -> bool:
    return (status or "").upper() in GENIE_TERMINAL_OK


def _genie_status_bad(status) -> bool:
    return (status or "").upper() in GENIE_TERMINAL_BAD


def _genie_terminal(status) -> bool:
    return _genie_status_ok(status) or _genie_status_bad(status)

# Transient HTTP statuses worth retrying (rate limiting + gateway/backend hiccups).
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2
_RETRY_BACKOFF_S = 1.5

# How long to block a single tool call while Genie / a long SQL statement finishes.
# Databricks Apps enforce a hard ~5-min (300s) total request timeout that NO amount of SSE
# heartbeating can beat — if a single request runs longer, the platform kills it mid-flight
# (the symptom: ~5-min hang, no error logged anywhere). So Genie's blocking wait must stay well
# under 300s to leave budget for the LLM turn(s) that share the same request. Override via
# GENIE_MAX_WAIT_S if your deployment has a different cap. 240s default = ~60s headroom.
_GENIE_MAX_WAIT_S = int(os.getenv("GENIE_MAX_WAIT_S", "240"))
_GENIE_POLL_INTERVAL_S = 4
_SQL_MAX_WAIT_S = int(os.getenv("SQL_MAX_WAIT_S", "120"))
_SQL_POLL_INTERVAL_S = 2


# Sentinel that ``ask_genie`` returns instead of a blocking answer. The agent loop
# (model.py) recognizes a ToolMessage whose content starts with this prefix, emits a
# ``pending_poll`` event, and halts the turn so the CLIENT drains Genie via short poll
# requests — never holding one request open past the Databricks Apps ~5-min cap. The JSON
# after the prefix carries the Genie handle (conversation_id / response_id / space_id).
PENDING_POLL_PREFIX = "__GENIE_PENDING_POLL__:"

# Field names Genie may use to ship a deep link back to the conversation in Databricks One.
_GENIE_URL_FIELDS = (
    "conversation_url", "share_url", "share_link", "deep_link",
    "deeplink", "permalink", "link", "url",
)


class ManagedMCPError(Exception):
    pass


class ManagedMCPClient:
    """Minimal JSON-RPC client for Databricks managed MCP servers."""

    def __init__(self, host: str, token: str):
        self.host = host.rstrip("/")
        self.token = token

    def _rpc(self, path: str, method: str, params: dict, timeout: int = 60) -> dict:
        url = f"{self.host}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

        last_err = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                last_err = ManagedMCPError(f"network error calling {path}: {e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                    continue
                raise last_err from e

            if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                continue

            resp.raise_for_status()
            data = _parse_jsonrpc_payload(resp.text)
            if data.get("error"):
                raise ManagedMCPError(json.dumps(data["error"]))
            return data.get("result", {})

        # Exhausted retries on a retryable status.
        raise last_err or ManagedMCPError(f"request to {path} failed after retries")

    def list_tools(self, path: str) -> list:
        return self._rpc(path, "tools/list", {}).get("tools", [])

    def call_tool(self, path: str, name: str, arguments: dict, timeout: int = 60) -> dict:
        """Call a tool and return its raw MCP result (``structuredContent`` preferred).

        Raises ``ManagedMCPError`` when the server flags ``isError``.
        """
        result = self._rpc(path, "tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
        if result.get("isError"):
            raise ManagedMCPError(_text_content(result) or "tool reported an error")
        sc = result.get("structuredContent")
        return sc if sc is not None else {"_text": _text_content(result)}


def _parse_jsonrpc_payload(text: str) -> dict:
    """Parse a JSON-RPC response that may be plain JSON or an SSE (``data:``) stream."""
    text = (text or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        return json.loads(text)
    # SSE: take the last non-empty ``data:`` line that parses as JSON.
    last = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            chunk = line[len("data:"):].strip()
            try:
                last = json.loads(chunk)
            except json.JSONDecodeError:
                continue
    return last or {}


def _text_content(result: dict) -> str:
    parts = []
    for item in result.get("content", []) or []:
        if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
            parts.append(item["text"])
    return "\n".join(parts)


def _format_statement_result(stmt: dict, max_rows: int = 100) -> str:
    """Render a Databricks ``statement_response``-shaped dict as a compact text table."""
    manifest = stmt.get("manifest", {}) or {}
    schema = manifest.get("schema", {}) or {}
    columns = [c.get("name") for c in schema.get("columns", []) or []]
    result = stmt.get("result", {}) or {}
    data_array = result.get("data_array", []) or []

    rows = []
    for raw in data_array[:max_rows]:
        # MCP returns rows as {"values": [{"string_value": "..."} | {} (null), ...]}.
        if isinstance(raw, dict) and "values" in raw:
            rows.append([_cell(v) for v in raw["values"]])
        elif isinstance(raw, list):
            rows.append([("" if v is None else str(v)) for v in raw])

    if not columns and not rows:
        return "Query executed successfully but returned no data."

    lines = ["Columns: " + ", ".join(columns), "Data:"]
    for r in rows:
        lines.append(str(r))
    if len(data_array) > max_rows:
        lines.append(f"... ({len(data_array) - max_rows} more rows truncated)")
    return "\n".join(lines)


def _cell(v) -> str:
    if isinstance(v, dict):
        if "string_value" in v:
            return str(v["string_value"])
        return ""  # null cell
    return "" if v is None else str(v)


# --------------------------------------------------------------------------------------
# Tool builders. Each returns a LangChain StructuredTool bound to ``client``.
# --------------------------------------------------------------------------------------

def build_sql_tool(client: "ManagedMCPClient"):
    from langchain_core.tools import tool

    @tool
    def query_lakehouse(sql_query: str) -> str:
        """Execute a read-only SQL query against the Databricks Lakehouse (Unity Catalog).

        Use this to answer data questions. ALWAYS use fully qualified names
        (`catalog.schema.table`). If you do not know the catalog/schema, discover it with
        `SHOW CATALOGS`, `SHOW SCHEMAS IN <catalog>`, or by querying `system.information_schema`.
        """
        path = "/api/2.0/mcp/sql"
        try:
            sc = client.call_tool(path, "execute_sql_read_only", {"query": sql_query}, timeout=120)
        except ManagedMCPError as e:
            return f"SQL error: {e}"

        state = (sc.get("status") or {}).get("state")
        statement_id = sc.get("statement_id")

        # Long-running statements come back not-yet-SUCCEEDED with a statement_id to poll.
        waited = 0
        while state not in ("SUCCEEDED", "FAILED", "CANCELED", "CANCELLED", "CLOSED") and statement_id:
            if waited >= _SQL_MAX_WAIT_S:
                return f"SQL query is still running after {_SQL_MAX_WAIT_S}s (statement_id={statement_id})."
            time.sleep(_SQL_POLL_INTERVAL_S)
            waited += _SQL_POLL_INTERVAL_S
            try:
                sc = client.call_tool(path, "poll_sql_result", {"statement_id": statement_id}, timeout=60)
            except ManagedMCPError as e:
                return f"SQL error while polling: {e}"
            state = (sc.get("status") or {}).get("state")

        if state and state != "SUCCEEDED":
            err = (sc.get("status") or {}).get("error", {})
            return f"SQL failed ({state}): {err.get('message', '')}".strip()
        return _format_statement_result(sc)

    return query_lakehouse


def build_genie_tools(client: "ManagedMCPClient", w=None, blocking: bool = False):
    """Return ``[list_genies, ask_genie]`` backed by the Genie managed MCP server.

    ``list_genies`` uses the (OBO) WorkspaceClient to enumerate spaces the caller can see.

    ``ask_genie`` defaults to *start-only*: it kicks off the Genie turn and hands a poll handle
    back via a sentinel so the client drains the answer over short requests (no long-held
    request → no Apps ~5-min timeout). Set ``blocking=True`` for the non-streaming path (output
    guardrails), where the agent runs ``agent.invoke`` atomically and can't hand off mid-turn —
    there ``ask_genie`` polls to completion inline like before.
    """
    from langchain_core.tools import tool

    _cache_key = hashlib.sha256((getattr(client, "token", "") or "").encode()).hexdigest()

    @tool
    def list_genies() -> str:
        """List the Databricks Genie spaces you can access, with their names, descriptions, and space_ids.

        Optional: `ask_genie` searches across all of your Genie spaces by default, so you usually do
        NOT need this. Use it only when you want to *target* one specific space by `space_id`.
        """
        if w is None:
            return "Error: no Databricks client available to list Genie spaces."

        cached = _GENIE_SPACES_CACHE.get(_cache_key)
        if cached and (time.time() - cached[0]) < _GENIE_SPACES_TTL_S:
            return cached[1]

        try:
            res = w.genie.list_spaces()
        except Exception as e:
            return f"Error listing Genie spaces: {e}"
        spaces = getattr(res, "spaces", None) or []
        if not spaces:
            return "No Genie spaces found."
        out = []
        for s in spaces:
            out.append(
                f"- **Name**: {getattr(s, 'title', 'Unknown')}\n"
                f"  **Space ID**: {getattr(s, 'space_id', 'Unknown')}\n"
                f"  **Description**: {getattr(s, 'description', 'No description provided')}"
            )
        result = "\n\n".join(out)
        _GENIE_SPACES_CACHE[_cache_key] = (time.time(), result)
        return result

    @tool
    def ask_genie(question: str, space_id: str = "") -> str:
        """Ask a natural-language data/analytics question to Databricks Genie.

        By DEFAULT Genie searches across **all** of your accessible Genie spaces / enterprise data
        and writes the SQL itself — you do NOT need to choose a space. This is the preferred way to
        ask analytical questions. Optionally pass a `space_id` (from `list_genies`) to restrict the
        question to one specific space.

        This returns immediately with a pending handle; the answer streams in to the user
        afterwards. Do NOT call it again for the same question — the result is delivered out of band.
        """
        if not question:
            return "Error: question is required."

        mode = f"space={space_id}" if space_id else "workspace-wide"
        print(f"[ask_genie] start ({mode}) q={question[:80]!r} blocking={blocking}", flush=True)
        try:
            handle = genie_start(client, question, space_id)
        except ManagedMCPError as e:
            print(f"[ask_genie] ask FAILED: {e}", flush=True)
            return f"Error asking Genie: {e}"

        conv_id, resp_id = handle.get("conversation_id"), handle.get("response_id")
        if not conv_id or not resp_id:
            print(f"[ask_genie] no conversation/response id returned (keys may differ)", flush=True)
            return "Genie did not return a conversation/response id to poll."

        if blocking:
            # Non-streaming path: poll inline to completion (the agent invoke is atomic here).
            if _genie_status_bad(handle.get("status")):
                print(f"[ask_genie] terminal BAD at start status={handle.get('status')!r}", flush=True)
                return f"Genie could not answer (status={handle.get('status')})."
            waited = 0
            while waited < _GENIE_MAX_WAIT_S:
                time.sleep(_GENIE_POLL_INTERVAL_S)
                waited += _GENIE_POLL_INTERVAL_S
                try:
                    snap = genie_poll_once(client, conv_id, resp_id, space_id)
                except ManagedMCPError as e:
                    print(f"[ask_genie] poll FAILED at {waited}s: {e}", flush=True)
                    return f"Error polling Genie: {e}"
                print(f"[ask_genie] poll {waited}s: status={snap['status']!r}", flush=True)
                if snap["status"] == "complete":
                    return snap.get("answer") or "Genie completed but returned no textual answer."
                if snap["status"] == "failed":
                    return snap.get("error") or "Genie could not answer."
            print(f"[ask_genie] TIMEOUT after {waited}s", flush=True)
            return f"Genie is still processing after {_GENIE_MAX_WAIT_S}s. Try again or narrow the question."

        print(
            f"[ask_genie] started: conv_id={conv_id!r} resp_id={resp_id!r} "
            f"(pending poll handed to client)",
            flush=True,
        )
        # Start-only: hand the poll handle back to the agent loop via a sentinel string. The
        # loop (model.py) recognizes the prefix, emits a pending_poll event, and stops the turn.
        return PENDING_POLL_PREFIX + json.dumps({
            "kind": "genie",
            "conversation_id": conv_id,
            "response_id": resp_id,
            "space_id": space_id or "",
            "question": question,
        })

    return [list_genies, ask_genie]


# --------------------------------------------------------------------------------------
# Genie async primitives (start / poll) shared by the ask_genie tool and the /genie/poll
# HTTP endpoint. Splitting "start" from "poll" lets the agent return immediately while the
# client drains the answer over many short requests (no single long-held request).
# --------------------------------------------------------------------------------------

def _genie_paths(space_id: str):
    """Return ``(path, ask_name, poll_name, per_space)`` for a (possibly empty) space_id."""
    if space_id:
        return (
            f"/api/2.0/mcp/genie/{space_id}",
            f"query_space_{space_id}",
            f"poll_response_{space_id}",
            True,
        )
    return ("/api/2.0/mcp/genie", "genie_ask", "genie_poll_response", False)


def genie_start(client: "ManagedMCPClient", question: str, space_id: str = "") -> dict:
    """Kick off a Genie turn and return its poll handle (no waiting).

    Returns ``{conversation_id, response_id, status, space_id, question}``. Raises
    ``ManagedMCPError`` if the start call itself fails.
    """
    path, ask_name, _poll_name, per_space = _genie_paths(space_id)
    ask_args = {"query": question} if per_space else {"question": question}
    sc = client.call_tool(path, ask_name, ask_args, timeout=120)
    conv_id = sc.get("conversation_id") or sc.get("conversationId")
    resp_id = (
        sc.get("response_id") or sc.get("responseId")
        or sc.get("message_id") or sc.get("messageId")
    )
    return {
        "conversation_id": conv_id,
        "response_id": resp_id,
        "status": sc.get("status"),
        "space_id": space_id or "",
        "question": question,
    }


def genie_poll_once(client: "ManagedMCPClient", conversation_id: str, response_id: str, space_id: str = "") -> dict:
    """Run ONE Genie poll and return a normalized snapshot.

    Returns ``{status, answer, final, narration, deep_link, error}``:
      - ``answer``    — what to SHOW live this poll (the real partial answer if Genie has one,
                        else the progress narration incl. the SQL it's running). REPLACE each poll.
      - ``final``     — the real answer text ONLY (empty until Genie actually has it). The client
                        uses this as the completion signal so it never settles on narration.
      - ``narration`` — Genie's progress steps + SQL, rendered for the "thinking" view.
    """
    path, _ask_name, poll_name, per_space = _genie_paths(space_id)
    poll_args = (
        {"conversation_id": conversation_id, "message_id": response_id}
        if per_space else
        {"conversation_id": conversation_id, "response_id": response_id}
    )
    sc = client.call_tool(path, poll_name, poll_args, timeout=60)
    status = sc.get("status")
    if _genie_status_bad(status):
        return {"status": "failed", "error": f"Genie could not answer (status={status})."}

    deep_link = _find_genie_deep_link(sc)
    narration = _build_genie_progress(sc)
    answer = _render_genie_answer(sc)
    if answer == "Genie completed but returned no textual answer.":
        answer = ""

    if _genie_status_ok(status):
        return {"status": "complete", "answer": answer, "final": answer, "narration": narration, "deep_link": deep_link}
    # Still running: show the real partial answer if present, otherwise the live narration/SQL.
    return {
        "status": "running",
        "answer": answer or narration,
        "final": answer,  # empty until the real answer lands → drives early completion
        "narration": narration,
        "deep_link": deep_link,
    }


# Genie embeds raw query-result tables between HTML comment markers; they're unreadable in a live
# progress feed, so strip them out and just narrate the step.
_GENIE_QUERY_BLOCK_RE = re.compile(r"<!--\s*begin:.*?-->.*?<!--\s*end:.*?-->", re.DOTALL)
_GENIE_STEP_TEXT_KEYS = (
    "content", "text", "description", "message", "markdown", "summary",
    "detail", "title", "name", "label", "step",
)


def _genie_step_text(step) -> str:
    """Best-effort pull of human-readable text from one Genie progress step."""
    if isinstance(step, str):
        return step.strip()
    if not isinstance(step, dict):
        return ""
    for key in _GENIE_STEP_TEXT_KEYS:
        val = step.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    longest = ""
    for val in step.values():
        if isinstance(val, str) and len(val.strip()) > len(longest):
            longest = val.strip()
    return longest


def _clean_genie_step(text: str) -> str:
    """Turn a raw progress step into a short readable one-liner (strip result tables, trim SQL)."""
    text = _GENIE_QUERY_BLOCK_RE.sub("", text)
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("|")]
    cleaned = " ".join(" ".join(lines).split()).rstrip(": ").strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:200].rstrip() + "…"
    return cleaned


def _build_genie_progress(sc: dict) -> str:
    """Assemble a live "thinking" feed from Genie's progress steps + the SQL it's running.

    Shows the most recent steps (rolling window) and any SQL statements as fenced code blocks so
    the UI can render the same SQL + narration you see in the native Databricks Genie view.
    """
    parts = []
    steps = sc.get("progress_steps")
    if isinstance(steps, list):
        lines = [t for s in steps if (t := _clean_genie_step(_genie_step_text(s)))]
        if lines:
            parts.append("\n".join(f"- {ln}" for ln in lines[-6:]))
    for it in (sc.get("query_items") or []):
        if isinstance(it, dict):
            q = it.get("query") or it.get("statement")
            if isinstance(q, str) and q.strip():
                parts.append(f"```sql\n{q.strip()}\n```")
    return "\n\n".join(parts).strip()


def _find_genie_deep_link(sc: dict):
    """Best-effort scan for a Databricks-hosted conversation URL in a Genie response."""
    def _ok(v):
        if not isinstance(v, str):
            return None
        v = v.strip()
        if v.startswith(("http://", "https://")) and "databricks." in v:
            return v
        return None

    candidates = [sc.get(k) for k in _GENIE_URL_FIELDS]
    for nest in ("content", "result", "data"):
        nested = sc.get(nest)
        if isinstance(nested, dict):
            candidates.extend(nested.get(k) for k in _GENIE_URL_FIELDS)
    for items_key in ("query_items", "attachments"):
        items = sc.get(items_key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    candidates.extend(it.get(k) for k in _GENIE_URL_FIELDS)
    for c in candidates:
        url = _ok(c)
        if url:
            return url
    return None


def _render_genie_answer(sc: dict) -> str:
    """Render a completed Genie response from either Genie MCP shape.

    Workspace-wide ``genie_ask`` returns ``final_answer`` (markdown) plus optional ``query_items``;
    the per-space server returns ``content.textAttachments`` / ``content.queryAttachments``.
    """
    final = sc.get("final_answer")
    if final:
        parts = [final if isinstance(final, str) else str(final)]
        parts.extend(_render_query_items(sc.get("query_items")))
        return "\n\n".join(p for p in parts if p)
    return _format_genie_answer(sc)


def _render_query_items(items) -> list:
    """Best-effort render of workspace-wide ``query_items`` (SQL + results attachments).

    Shows the SQL Genie ran (so the user sees the query, like the native Genie view) followed by
    the result table.
    """
    out = []
    for it in items or []:
        if isinstance(it, dict):
            desc = it.get("description") or it.get("title")
            if desc:
                out.append(str(desc))
            q = it.get("query") or it.get("statement")
            if isinstance(q, str) and q.strip():
                out.append(f"```sql\n{q.strip()}\n```")
            stmt = it.get("statement_response")
            if isinstance(stmt, dict):
                out.append(_format_statement_result(stmt))
        elif it:
            out.append(str(it))
    return out


def _format_genie_answer(sc: dict) -> str:
    """Render a completed Genie response (text answer + any SQL/result attachment)."""
    content = sc.get("content") or {}
    parts = []
    for txt in content.get("textAttachments", []) or []:
        if txt:
            parts.append(txt if isinstance(txt, str) else str(txt))
    for qa in content.get("queryAttachments", []) or []:
        if not isinstance(qa, dict):
            continue
        desc = qa.get("description")
        if desc:
            parts.append(desc)
        q = qa.get("query") or qa.get("statement")
        if isinstance(q, str) and q.strip():
            parts.append(f"```sql\n{q.strip()}\n```")
        stmt = qa.get("statement_response")
        if isinstance(stmt, dict):
            parts.append(_format_statement_result(stmt))
    answer = "\n\n".join(p for p in parts if p)
    return answer or "Genie completed but returned no textual answer."
