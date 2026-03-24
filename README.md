# Design Document: Supply Chain AI Agent

| | |
|---|---|
| **Stack** | Databricks Agent Framework (Mosaic AI), FastAPI, React, Unity Catalog (UC), FastMCP |
| **Status** | Active Development |

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Goals and non-goals](#2-goals-and-non-goals)
3. [System architecture](#3-system-architecture)
4. [Tooling and skill management](#4-tooling-and-skill-management)
5. [Implementation details](#5-implementation-details)
6. [Deployment workflow](#6-deployment-workflow)
7. [Security and governance](#7-security-and-governance)
8. [Data model](#8-data-model)
9. [API contract](#9-api-contract)
10. [Sequence diagram](#10-sequence-diagram)
11. [Phased roadmap](#11-phased-roadmap)
12. [Open questions and next steps](#12-open-questions-and-next-steps)

---

## 1. Executive summary

An autonomous **Supply Chain Agent** hosted as a **Custom Agent** in the Databricks workspace. It uses Unity Catalog for tool governance and FastAPI for core orchestration. The agent assists with **inventory management**, **purchase order (PO) generation**, and **external system integrations** (like ERP checks and Slack notifications).

---

## 2. Goals and non-goals

**Goals**

- Governed access to lakehouse data and external systems through UC and explicit tool contracts.
- Dynamic tool discovery and schema generation (self-documenting tools).
- A thin FastAPI layer acting as a secure gateway, session manager, and FastMCP router.
- Observable agent runs (tracing, tool-call audit) suitable for production review.

**Non-goals (initial phase)**

- Replacing full ERP workflows end-to-end; the agent assists and proposes, with human approval where required.
- Building a generic MCP marketplace inside this repo; we integrate specific bridges as needed.

---

## 3. System architecture

The architecture follows an **agentic bridge** pattern with dynamic tool routing:

| Layer | Role |
|--------|------|
| **Frontend** | React + Tailwind chat UI |
| **Orchestration** | FastAPI: secure gateway, FastMCP router, and session manager |
| **Agent** | Databricks Agent Serving endpoint (LLM + dynamically loaded tools) |
| **Tools (data)** | UC Functions for SQL/Python against the lakehouse |
| **Tools (external)** | FastMCP bridge for ERP/APIs and other MCP-capable systems |

### Component diagram

```mermaid
graph TD
    A[React Frontend] -->|REST| B[FastAPI Backend]
    B -->|Databricks SDK| C[Agent Serving Endpoint]
    C -->|Dynamic schema loading| D{Tool router}
    D -->|SQL execution| E[UC Functions]
    D -->|Yield fastmcp payload| B
    B -->|Local execution| F[FastMCP Server]
    E --> G[(Databricks Lakehouse)]
    F --> H[External ERP / Slack APIs]
```

### Request flow (high level)

1. User sends a message; FastAPI authenticates and forwards the query to the **serving endpoint**.
2. The agent reasoning loop evaluates the dynamically provided tool schemas.
3. For **UC tools**, the agent directly executes the SQL functions via the workspace client and processes the result.
4. For **FastMCP tools**, the agent returns a special payload instructing FastAPI to execute the tool locally.
5. FastAPI executes the local FastMCP tool and returns the formatted response.
6. The final response flows back to the UI.

---

## 4. Tooling and skill management

We use a **hybrid, dynamically discovered tooling model** managed by `backend/tools/registry.py`. We also support a **Skills Framework** for cognitive SOPs.

### A. Skills (Cognitive SOPs)

**Use case:** Providing the agent with standard operating procedures on how to analyze data, what policies to follow, or how to chain tools together for a specific business process.

- **Registration:** Add a `.md` file to `backend/skills/` with a YAML frontmatter `description`.
- **Execution:** The agent reads the description in its system prompt and uses the `read_skill` tool to read the markdown instructions when relevant.

### B. UC Functions (data and logic)

**Use case:** Any tool that queries the lakehouse.

- **Registration:** Defined in Python (`backend/tools/uc_tools.py`), schemas are dynamically extracted via inspection, and executed natively via SQL (`main.supply_chain_schema.*`).
- **Examples:** `get_inventory`, `get_supplier_lead_times`.

### C. FastMCP bridge (external connectivity)

**Use case:** External actions like ERP checks, Slack notifications, or processing uploaded files.

- **Registration:** Defined as individual `.py` files in `backend/tools/mcp/`. The registry automatically tags these as `fastmcp` tools. 
- **Execution:** Instead of running natively in Databricks, the agent yields a JSON payload telling FastAPI to execute the local FastMCP function, update the conversation history, and allow the agent to synthesize the result.
- **Examples:** `get_erp_supplier_status`, `notify_slack_channel`, `manage_safety_stock`.

---

## 5. Implementation details

### Project directory structure

```text
/
├── backend/
│   ├── app.py                 # FastAPI entry point & FastMCP payload router
│   ├── agent/
│   │   ├── model.py           # Custom PyFunc Agent logic (MLflow-logged)
│   │   ├── config.py          # Workspace configurations
│   │   └── prompt.md          # Core agent personality and system instructions
│   ├── skills/                # Markdown SOPs (e.g. analyze_safety_stock.md)
│   └── tools/
│       ├── mcp/               # Individual FastMCP tools (e.g. notify_slack.py)
│       ├── registry.py        # Dynamic tool/skill discovery
│       └── uc_tools.py        # UC tool schema definitions
├── frontend/                  # React + Tailwind UI
│   └── src/
├── scripts/
│   ├── setup_uc.py            # Programmatic UC schema/table/function provisioning
│   ├── seed_data.py           # Random data generator for inventory/suppliers/POs
│   └── deploy_agent.py        # MLflow model registration and deployment
├── start.sh                   # Cross-platform local launch script
└── pyproject.toml             # Python dependencies
```

### Backend: FastAPI orchestration

FastAPI acts as a proxy and FastMCP router. It manages an in-memory `session_history` dictionary to retain conversation context. If the agent returns a `fastmcp_tool_call` JSON payload, FastAPI executes it locally and feeds the result back into the agent loop.

```python
# backend/app.py logic snippet
if parsed_msg.get("type") == "fastmcp_tool_call":
    tool_name = parsed_msg.get("tool")
    args = parsed_msg.get("arguments", {})
    # Dynamically load and execute the local tool from backend/tools/mcp/
    module = importlib.import_module(f"backend.tools.mcp.{tool_name}")
    result = getattr(module, tool_name)(**args)
    # Append result to history and continue the agent loop
    session_history[session_id].append({"role": "tool", "content": result})
    continue
```

### Agent logic

The agent uses a custom `mlflow.pyfunc` class that dynamically discovers tools at runtime.

```python
# backend/agent/model.py logic snippet
from backend.tools.registry import discover_tools

class SupplyChainPyFuncAgent(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        tool_schemas, tool_routing = discover_tools()
        # ... queries the LLM with dynamic tools
        if execution_type == "uc":
            res = self._run_sql(f"SELECT * FROM {catalog}.{func_name}(...)")
        elif execution_type == "fastmcp":
            return [json.dumps({"type": "fastmcp_tool_call", "tool": func_name, "arguments": args})]
```

---

## 6. Deployment workflow

The project includes a generic deployment script (`deploy.sh`) that builds the environment and deploys the agent to Databricks Model Serving. It assumes you are deploying against an existing Unity Catalog and schema.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/taylor-hanson_data/supply-chain-agent.git
   cd supply-chain-agent
   ```
2. **Configure Environment**: 
   Ensure your Databricks CLI is configured (`databricks configure`). By default, the deploy script uses a profile named `myenv`. 
3. **Deploy the Agent**:
   Run the deployment script, overriding the defaults to point to your real Unity Catalog environment:
   ```bash
   CATALOG_SCHEMA="my_production_catalog.my_schema" \
   AGENT_ENDPOINT_NAME="my_agent_endpoint" \
   DATABRICKS_PROFILE="default" \
   ./deploy.sh
   ```
4. **Start Application**: 
   Run `./start.sh` to launch the FastAPI backend and React frontend locally. (Note: Use `LOCAL_MODE=true ./start.sh` if you want to bypass the hosted endpoint and run the agent logic locally for faster development).

### Optional: Sandbox Data Setup
If you are deploying this in a fresh environment and want to generate mock tables and data for testing instead of using real data, you can run the setup scripts *before* deploying:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_uc.py
python scripts/seed_data.py
```

---

## 7. Security and governance

| Concern | Approach |
|---------|----------|
| **Identity** | Local auth via `DATABRICKS_PROFILE` for FastAPI → Databricks. |
| **Traceability** | MLflow Tracing and explicit FastMCP logging in the UI. |
| **External calls** | MCP calls are executed in the secure FastAPI layer, not directly from the workspace container. |

---

## 8. Data model

The backend provisions a Unity Catalog schema (`taylor_hanson_build_catalog.supply_chain_schema`) seeded with randomized mock data via `scripts/seed_data.py`.

### Core Unity Catalog tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `inventory` | Current stock levels across warehouses. | `sku`, `warehouse_id`, `quantity_on_hand`, `reorder_point` |
| `suppliers` | Supplier metadata and performance metrics. | `supplier_id`, `name`, `avg_lead_time_days`, `reliability_score` |
| `purchase_orders` | Historical and active POs. | `po_id`, `sku`, `supplier_id`, `quantity`, `status`, `expected_date` |

---

## 9. API contract

The FastAPI layer exposes a thin REST API to the React frontend.

### `POST /chat`

**Request:**

```json
{
  "query": "Do we need to reorder SKU-555?"
}
```

**Response:**

```json
{
  "message": "Yes, SKU-555 is below the reorder point...",
  "tool_calls": [
    {
      "tool_name": "get_inventory",
      "status": "executed via UC SQL"
    }
  ]
}
```

---

## 10. Sequence diagram

```mermaid
sequenceDiagram
    actor User
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Agent as Databricks Agent (Serving)
    participant UC as Unity Catalog
    participant MCP as FastMCP (Local API)

    User->>UI: "Check stock for SKU-555 and notify Slack"
    UI->>API: POST /chat {query: "..."}
    API->>Agent: Query endpoint
    Agent->>UC: Execute SELECT * FROM get_inventory('SKU-555')
    UC-->>Agent: {stock: 15, reorder_point: 50}
    
    Agent-->>API: yield {type: "fastmcp_tool_call", tool: "notify_slack"}
    API->>MCP: call notify_slack_channel()
    MCP-->>API: Success response
    
    API-->>UI: "Stock is low. Slack notified."
    UI-->>User: (Displays message & tool badges)
```

---

## 11. Phased roadmap

| Phase | Focus | Status | Key Deliverables |
|-------|-------|--------|------------------|
| **Phase 1 (MVP)** | Read-only Lakehouse | ✅ Done | FastAPI + React. Read-only UC tools. Agent deployment. Data seeding. |
| **Phase 2** | Write-back & Tooling | ✅ Done | Dynamic tool registry. `draft_purchase_order` tool. |
| **Phase 3** | External Integrations | ✅ Done | FastMCP backend routing for `notify_slack_channel` and `get_erp_supplier_status`. |
| **Phase 4** | Advanced Capabilities | ✅ Done | File uploads (CSV/XLSX processing), `manage_safety_stock` tool. |
| **Phase 5** | Cognitive SOPs | ✅ Done | Dynamic Skill framework (`backend/skills/`) for markdown-based agent procedures. |

---

## 12. Open questions and next steps

**Suggested next steps**

1. Set up evaluation notebooks for Golden questions and tracing accuracy.
2. Add more complex UC functions that require cross-table joins.
3. Add a dedicated vector search tool for retrieving external context.

---

*Document version: 0.3.0 — Updated with Skills framework, file uploads, and history persistence.*
