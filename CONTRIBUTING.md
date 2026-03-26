# Contributing to the Supply Chain AI Agent

Welcome! This guide is designed to help you, whether you are a supply chain analyst, a product manager, or a developer, add new capabilities to the Supply Chain AI Agent. 

We have designed the system to be as modular and "code-free" as possible for most cognitive updates. 

There are three main areas you might want to modify:
1. **The System Prompt** (Changing the agent's core personality)
2. **Skills** (Teaching the agent standard operating procedures)
3. **Tools** (Giving the agent the ability to take action or fetch data)

---

## 1. Modifying the System Prompt

**When to modify:** You want to change the agent's core tone, give it a new universal instruction (like "always speak in Spanish" or "always use Tailwind classes"), or restrict its general behavior.

**How to modify:**
Simply open `backend/agent/prompt.md` and edit the text. 

**Example:**
```markdown
# Supply Chain AI Agent Instructions
You are a helpful, extremely polite supply chain AI agent. 
Never guess inventory numbers; if you don't know, explicitly state "I don't know."
```
*Note: The prompt is read at runtime by the FastAPI backend. In local development (`dev.sh`), changes take effect immediately on reload. In production, you must re-run `./deploy_app.sh`.*

---

## 2. Adding a New Skill

**When to modify:** You want to teach the agent a Standard Operating Procedure (SOP). For example, "What is our company policy when a user wants to expedite a PO?" or "How should you analyze a safety stock upload?". A Skill tells the agent *how to think* about a task before it uses tools.

**How to modify:**
Create a new Markdown file in the `backend/skills/` directory.

The agent will automatically discover this file. The only requirement is that the file must start with a YAML block describing when to use the skill, followed by the markdown instructions.

**Example: `backend/skills/expedite_policy.md`**
```markdown
---
description: Use this skill when a user asks about expediting a purchase order or a shipment is late.
---
# Expedite Policy
If a user asks to expedite a shipment, follow these steps:
1. Check the `get_erp_supplier_status` tool to see if the supplier is in good standing.
2. Draft an email summarizing the SKU and requested date.
3. Show the draft to the user for approval. 
```

---

## 3. Adding a New Tool

**When to modify:** You want the agent to actually *do* something—execute a SQL query, hit a third-party API, send a Slack message, or update a database table.

The agent runs inside a **Databricks App Container** and uses the **LangGraph/LangChain** framework. Any Python function you add will automatically be converted into a LangChain `@tool` and injected into the agent's brain.

### How to modify:
1. Create a new Python file in the `backend/tools/mcp/` directory. The filename **must** match the function name.
2. Write the actual Python logic inside the function. Use type hints and a detailed docstring. **The docstring is what the LLM reads to understand how to use your tool.**

**Example: `backend/tools/mcp/notify_warehouse_manager.py`**
```python
import requests

def notify_warehouse_manager(warehouse_id: str, message: str) -> str:
    """
    Sends an SMS notification to the manager of a specific warehouse.
    Use this tool whenever you detect low inventory and need to alert staff.
    """
    # ... your python code to hit Twilio or an internal API ...
    
    return f"Successfully sent '{message}' to manager of {warehouse_id}."
```

### Important Notes on Tools:
* **Execution Environment:** Your code will execute *inside* the Databricks App container. If it interacts with Databricks APIs (like Genie or UC), it will use the App's injected Service Principal credentials in production, or your CLI profile locally.
* **Dependencies:** If your tool requires a new pip package (e.g., `requests` or `twilio`), you must add it to `requirements.txt`.
* **Deployment:** After adding a new tool, run `./deploy_app.sh` to package and deploy the new code to Databricks Apps.

---

## 4. Local Development

To test your changes before deploying:

1. Ensure your Databricks CLI is authenticated (`databricks auth login`).
2. Run the local development script:
   ```bash
   ./dev.sh
   ```
3. This script will start the FastAPI backend on port 8000 and the React frontend on port 5173.
4. Open your browser to `http://localhost:5173`. 
5. The backend uses `uvicorn --reload`, so changes to Python files (or markdown skills/prompts) will automatically restart the server. Changes to React files will hot-reload in the browser.