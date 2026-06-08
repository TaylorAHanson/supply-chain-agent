"""Unit tests for backend.tools.managed_mcp.

These are pure/no-network tests: the MCP client is replaced with a scripted stand-in, so they
run anywhere. Compatible with pytest (``def test_*``) but also runnable directly:

    python evals/test_managed_mcp.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import backend.tools.managed_mcp as mcp
from backend.tools.managed_mcp import (
    ManagedMCPClient,
    ManagedMCPError,
    build_sql_tool,
    build_genie_tools,
    genie_start,
    genie_poll_once,
    PENDING_POLL_PREFIX,
    _parse_jsonrpc_payload,
    _format_statement_result,
    _format_genie_answer,
    _render_genie_answer,
    _cell,
)

# Polling tools sleep between attempts; make that instant for tests.
mcp.time.sleep = lambda *a, **k: None


class _ScriptedClient(ManagedMCPClient):
    """A ManagedMCPClient whose call_tool returns scripted values (no network)."""

    def __init__(self, script):
        super().__init__(host="https://example.test", token="unit-test-token")
        self._script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def call_tool(self, path, name, arguments, timeout=60):
        self.calls.append((name, dict(arguments)))
        seq = self._script.get(name)
        if not seq:
            raise AssertionError(f"unexpected tool call: {name}")
        val = seq.pop(0)
        if isinstance(val, Exception):
            raise val
        return val


# --- payload parsing -------------------------------------------------------------------

def test_parse_plain_json():
    assert _parse_jsonrpc_payload('{"result": {"x": 1}}') == {"result": {"x": 1}}


def test_parse_sse_stream():
    sse = 'event: message\ndata: {"result": {"y": 2}}\n\n'
    assert _parse_jsonrpc_payload(sse) == {"result": {"y": 2}}


def test_parse_empty():
    assert _parse_jsonrpc_payload("") == {}
    assert _parse_jsonrpc_payload("   ") == {}


# --- cell + table formatting -----------------------------------------------------------

def test_cell_values():
    assert _cell({"string_value": "5"}) == "5"
    assert _cell({}) == ""          # null cell
    assert _cell(None) == ""


def test_format_statement_result():
    stmt = {
        "manifest": {"schema": {"columns": [{"name": "a"}, {"name": "b"}]}},
        "result": {"data_array": [{"values": [{"string_value": "1"}, {"string_value": "2"}]}]},
    }
    out = _format_statement_result(stmt)
    assert "Columns: a, b" in out
    assert "['1', '2']" in out


def test_format_statement_result_empty():
    assert "no data" in _format_statement_result({}).lower()


# --- SQL tool --------------------------------------------------------------------------

def _sql_success_sc(value="42", col="a"):
    return {
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": col}]}},
        "result": {"data_array": [{"values": [{"string_value": value}]}]},
    }


def test_sql_tool_immediate_success():
    client = _ScriptedClient({"execute_sql_read_only": [_sql_success_sc("42")]})
    out = build_sql_tool(client).invoke({"sql_query": "SELECT 42 a"})
    assert "42" in out


def test_sql_tool_long_running_polls():
    client = _ScriptedClient({
        "execute_sql_read_only": [{"status": {"state": "RUNNING"}, "statement_id": "stmt-1"}],
        "poll_sql_result": [_sql_success_sc("7")],
    })
    out = build_sql_tool(client).invoke({"sql_query": "SELECT 7"})
    assert "7" in out
    assert ("poll_sql_result", {"statement_id": "stmt-1"}) in client.calls


def test_sql_tool_failure_state():
    client = _ScriptedClient({"execute_sql_read_only": [
        {"status": {"state": "FAILED", "error": {"message": "syntax error"}}}
    ]})
    out = build_sql_tool(client).invoke({"sql_query": "SELEKT"})
    assert "failed" in out.lower() and "syntax error" in out


def test_sql_tool_error_is_caught():
    client = _ScriptedClient({"execute_sql_read_only": [ManagedMCPError("boom")]})
    out = build_sql_tool(client).invoke({"sql_query": "x"})
    assert "SQL error" in out and "boom" in out


# --- Genie tools -----------------------------------------------------------------------

def _ask_tool(client, blocking=False):
    return [t for t in build_genie_tools(client, w=None, blocking=blocking) if t.name == "ask_genie"][0]


# --- Genie start-only (default streaming path) -----------------------------------------

def test_genie_ask_start_only_returns_pending_poll():
    # Default (streaming) path: ask_genie only STARTS Genie and hands back a poll handle.
    client = _ScriptedClient({
        "genie_ask": [{"conversation_id": "c1", "response_id": "r1", "status": "in_progress"}],
    })
    out = _ask_tool(client).invoke({"question": "how many tables?"})
    assert out.startswith(PENDING_POLL_PREFIX)
    handle = json.loads(out[len(PENDING_POLL_PREFIX):])
    assert handle == {
        "kind": "genie",
        "conversation_id": "c1",
        "response_id": "r1",
        "space_id": "",
        "question": "how many tables?",
    }
    # Exactly one call: the start. No inline polling.
    assert client.calls == [("genie_ask", {"question": "how many tables?"})]


def test_genie_start_extracts_handle_variants():
    client = _ScriptedClient({
        "query_space_SP": [{"conversationId": "c1", "messageId": "m1", "status": "ASKING_AI"}],
    })
    handle = genie_start(client, "q", "SP")
    assert handle["conversation_id"] == "c1" and handle["response_id"] == "m1"
    assert client.calls[0] == ("query_space_SP", {"query": "q"})


def test_genie_poll_once_running_then_complete():
    client = _ScriptedClient({
        "genie_poll_response": [
            {"status": "in_progress"},
            {"status": "completed", "final_answer": "There are 42 tables."},
        ],
    })
    s1 = genie_poll_once(client, "c1", "r1", "")
    assert s1["status"] == "running" and s1["answer"] == ""  # placeholder suppressed
    s2 = genie_poll_once(client, "c1", "r1", "")
    assert s2["status"] == "complete" and "42 tables" in s2["answer"]


def test_genie_poll_once_failed():
    client = _ScriptedClient({"genie_poll_response": [{"status": "failed"}]})
    s = genie_poll_once(client, "c1", "r1", "")
    assert s["status"] == "failed" and "could not answer" in s["error"].lower()


# --- Genie blocking path (non-streaming / output-guardrails) ---------------------------

def test_genie_ask_blocking_workspace_wide():
    # blocking=True -> inline poll to completion (status is lowercase).
    client = _ScriptedClient({
        "genie_ask": [{"conversation_id": "c1", "response_id": "r1", "status": "in_progress"}],
        "genie_poll_response": [
            {"status": "in_progress", "conversation_id": "c1", "response_id": "r1"},
            {"status": "completed", "final_answer": "There are 42 tables."},
        ],
    })
    out = _ask_tool(client, blocking=True).invoke({"question": "how many tables?"})
    assert "42 tables" in out
    assert client.calls[0][0] == "genie_ask"
    assert client.calls.count(("genie_poll_response", {"conversation_id": "c1", "response_id": "r1"})) == 2


def test_genie_ask_blocking_targeted_space():
    # space_id provided -> per-space query_space_/poll_response_ path.
    client = _ScriptedClient({
        "query_space_SP": [{"conversationId": "c1", "messageId": "m1", "status": "ASKING_AI"}],
        "poll_response_SP": [
            {"status": "ASKING_AI", "conversationId": "c1", "messageId": "m1"},
            {"status": "COMPLETED", "content": {"textAttachments": ["The answer is 10."], "queryAttachments": []}},
        ],
    })
    out = _ask_tool(client, blocking=True).invoke({"question": "how many?", "space_id": "SP"})
    assert "The answer is 10." in out
    assert client.calls[0][0] == "query_space_SP"
    assert client.calls.count(("poll_response_SP", {"conversation_id": "c1", "message_id": "m1"})) == 2


def test_genie_ask_blocking_terminal_failure():
    client = _ScriptedClient({
        "genie_ask": [{"conversation_id": "c", "response_id": "r", "status": "failed"}],
    })
    out = _ask_tool(client, blocking=True).invoke({"question": "q"})
    assert "could not answer" in out.lower()


def test_genie_ask_requires_question():
    client = _ScriptedClient({})
    out = _ask_tool(client).invoke({"question": ""})
    assert "required" in out.lower()


def test_render_genie_answer_workspace_shape():
    sc = {"final_answer": "Top answer", "query_items": [{
        "description": "rows",
        "statement_response": {
            "manifest": {"schema": {"columns": [{"name": "c"}]}},
            "result": {"data_array": [{"values": [{"string_value": "9"}]}]},
        },
    }]}
    out = _render_genie_answer(sc)
    assert "Top answer" in out and "rows" in out and "9" in out


def test_format_genie_answer_with_query_attachment():
    sc = {"content": {
        "textAttachments": ["Answer text"],
        "queryAttachments": [{
            "description": "desc",
            "statement_response": {
                "manifest": {"schema": {"columns": [{"name": "c"}]}},
                "result": {"data_array": [{"values": [{"string_value": "9"}]}]},
            },
        }],
    }}
    out = _format_genie_answer(sc)
    assert "Answer text" in out and "desc" in out and "9" in out


def _run():
    tests = sorted(
        (k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)
    )
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"FAIL {name}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
