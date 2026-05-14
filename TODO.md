# Post-Migration Databricks UI Configuration

The codebase has been successfully migrated to the North Star Architecture. However, several platform-level configurations must be completed manually in the Databricks UI or via the provided automation scripts.

Please complete the following checklist:

## 1. Configure AI Gateway & A/B Testing Route
You need to create an AI Gateway Route (`supply_chain_agent_endpoint`) that routes traffic between Claude and Llama for A/B testing.
- [ ] **Option A (Automated):** Run the provided script:
  ```bash
  DATABRICKS_PROFILE=myenv python scripts/create_ab_test_route.py
  ```
- [ ] **Option B (Manual):** 
  1. Go to **AI Gateway** in the Databricks UI.
  2. Click **Create route**.
  3. Name the route `supply_chain_agent_endpoint`.
  4. Add `databricks-claude-sonnet-4-6` and `databricks-meta-llama-3-70b-instruct` as targets.
  5. Configure the traffic split (e.g., 80% to Claude, 20% to Llama).

## 2. Register Unity Catalog Tools
The agent now uses `databricks-langchain` to load tools directly from Unity Catalog. You must register the Python functions in your catalog schema.
- [ ] **Option A (Automated):** Run the provided script:
  ```bash
  DATABRICKS_PROFILE=myenv python scripts/register_uc_tools.py
  ```
- [ ] **Option B (Manual):** 
  1. Open a Databricks SQL Notebook.
  2. Execute `CREATE OR REPLACE FUNCTION` statements for `get_inventory`, `manage_safety_stock`, etc., in your `taylor_hanson_build_catalog.supply_chain_schema`.

## 3. Enable Inference Tables
To capture production traffic, payload logs, and trace IDs (which are required for the feedback loop and LLM Judge), you must enable Inference Tables on the AI Gateway route.
- [ ] **Option A (Automated):** Run the provided script (ensure the route from Step 1 exists first):
  ```bash
  DATABRICKS_PROFILE=myenv python scripts/enable_inference_tables.py
  ```
- [ ] **Option B (Manual):**
  1. Go to **AI Gateway** in the Databricks UI and open the `supply_chain_agent_endpoint` route.
  2. Click **Enable Inference Tables** (or configure payload logging).
  3. Set the destination to `taylor_hanson_build_catalog.supply_chain_schema` with the prefix `agent_payload_logs`.

## 4. Deploy the Databricks App
Deploy the newly refactored app and the scheduled LLM Judge job using Databricks Asset Bundles.
- [ ] Run the deployment script:
  ```bash
  ./deploy_app.sh
  ```
- [ ] Verify the app is running in the Databricks UI under **Compute > Apps**.

## 5. Verify the Feedback Loop & LLM Judge
- [ ] Open the deployed App UI and interact with the agent.
- [ ] Click the Thumbs Up / Thumbs Down buttons to generate feedback.
- [ ] Verify that the `agent_feedback` Delta table is receiving the ratings.
- [ ] Verify that the `llm_judge_evaluator` job (defined in `databricks.yml`) runs successfully and populates the `agent_eval_scores` Delta table.
