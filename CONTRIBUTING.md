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
*Note: You do not need to restart the server or write any Python code for this to take effect on the next chat message.*

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
*Note: As soon as you save this file, the agent will know it exists and will read it when a user asks about expediting!*

---

## 3. Adding a New Tool

**When to modify:** You want the agent to actually *do* something—execute a SQL query, hit a third-party API, send a Slack message, or update a database table.

There are two types of tools: **UC Tools** (for Databricks data) and **FastMCP Tools** (for external APIs).

### A. Unity Catalog (UC) Tools
Use these when you want the agent to query or interact natively with Databricks Lakehouse data. 

**How to modify:**
1. Open `backend/tools/uc_tools.py`.
2. Add an empty Python function with a clear docstring and type hints. The agent uses this to know what data to provide.

**Example:**
```python
def check_warehouse_capacity(warehouse_id: str):
    """
    Get the total current utilization percentage for a specific warehouse.
    Use this when a user asks if a warehouse is full.
    """
    pass
```
*Note: You must also ensure the actual SQL function `check_warehouse_capacity` is created in Databricks Unity Catalog.*

### B. FastMCP Tools (External/Local execution)
Use these when you want the agent to perform actions outside of Databricks (e.g., calling the Salesforce API, processing a local file, hitting Slack).

**How to modify:**
1. Create a new Python file in the `backend/tools/mcp/` directory. The filename **must** match the function name.
2. Write the actual Python logic inside the function. Use type hints and a docstring.

**Example: `backend/tools/mcp/notify_warehouse_manager.py`**
```python
def notify_warehouse_manager(warehouse_id: str, message: str) -> str:
    """
    Sends an SMS notification to the manager of a specific warehouse.
    """
    # ... your python code to hit Twilio or an internal API ...
    
    return f"Successfully sent '{message}' to manager of {warehouse_id}."
```
*Note: FastAPI will dynamically discover this file. If the LLM decides to use this tool, FastAPI will execute the Python code inside this file automatically and return the result to the LLM.*
