import os
import json
import httpx
import asyncio
from databricks.sdk import WorkspaceClient
from backend.agent.config import AGENT_ENDPOINT_NAME

async def test():
    w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))
    host = w.config.host
    auth_headers = w.config.authenticate()
    if isinstance(auth_headers, dict) and "Authorization" in auth_headers:
        token = auth_headers["Authorization"].replace("Bearer ", "")
    else:
        token = w.config.token
    
    endpoint_url = f"{host}/serving-endpoints/{AGENT_ENDPOINT_NAME}/invocations"
    print("Endpoint:", endpoint_url)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Using 'input' per ResponsesAgent schema
    payload = {
        "input": [{"role": "user", "content": "testing"}],
        "stream": True,
        "custom_inputs": {"session_id": "test_session"}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", endpoint_url, headers=headers, json=payload, timeout=60.0) as response:
                print("Status Code:", response.status_code)
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"Error: {error_text}")
                    return
                    
                async for line in response.aiter_lines():
                    if line:
                        print("LINE:", line)
    except Exception as e:
        print("EXCEPTION:", e)

asyncio.run(test())
