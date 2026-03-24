---
description: Use this skill when a user wants to analyze or update safety stock levels, especially after uploading a file.
---
# Analyze Safety Stock Skill

When a user wants to analyze safety stock or upload a file with safety stock data, follow these steps:

1. **Understand the Goal**: Identify what the user wants to achieve with the safety stock (e.g., update `min_stock_level` or `max_stock_level` for specific BUs or SKUs).
2. **Review Data**: If a user uploaded a file, ask them for the specific rules or deltas to apply. If they want to query existing stock, use the `query_lakehouse` tool.
3. **Draft the Changes**: Calculate the deltas (which rows change, what the new values will be).
4. **Review with Customer**: ALWAYS summarize the proposed changes and ask for the user's explicit approval before committing any changes to the database.
5. **Commit (Future)**: Once approved, you would commit these changes (this step will be implemented soon).
