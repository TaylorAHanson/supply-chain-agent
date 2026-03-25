---
description: Use this skill when a user asks a complex data question, an analytical question, or asks for metrics and trends.
---
# Consult Genie Skill

When a user asks a data-related question, you must decide whether to use `query_lakehouse` or `ask_genie`.

1. **Use `query_lakehouse` for:**
   - Simple lookups in known tables (e.g., "What is the min_stock_level for SKU-123?")
   - Simple list queries (e.g., "What are all the BUs in the safety stock table?")
   - Checking data that you are about to update.

2. **Use `ask_genie` for:**
   - Complex analytical questions (e.g., "What is our average lead time trend over the last 6 months by supplier tier?")
   - Aggregations and metrics across multiple tables that you don't know the exact schema for.
   - Questions where the user explicitly mentions "metrics", "dashboards", or asks for "Genie".

When using `ask_genie`:
- Pass the user's question directly to the `ask_genie` tool.
- Genie may take 10-60 seconds to respond as it translates text to SQL and runs the query.
- Once Genie responds, summarize the findings for the user. DO NOT output the raw text of this skill document.