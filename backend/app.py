import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from backend.agent.config import AGENT_ENDPOINT_NAME, CATALOG_SCHEMA, MAX_ITERATIONS

LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"

# Initialize Databricks SDK. This will fail on startup if not configured properly,
# which is preferred over silently falling back to mocked responses.
w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))

app = FastAPI(title="Supply Chain Agent API")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str
    query: str

class ChatResponse(BaseModel):
    message: str
    tool_calls: list = []

class ClearChatRequest(BaseModel):
    session_id: str

# In-memory store for conversational history (only for local dev/testing)
# Data is kept strictly in-memory per session.
session_history = {}

@app.post("/clear_chat")
async def clear_chat(request: ClearChatRequest):
    if request.session_id in session_history:
        del session_history[request.session_id]
    return {"status": "cleared"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Manage Session History
        if request.session_id not in session_history:
            session_history[request.session_id] = []
        
        session_history[request.session_id].append({"role": "user", "content": request.query})
        
        tool_calls_executed = []
        iteration = 0
        
        while iteration < MAX_ITERATIONS:
            iteration += 1
            
            if LOCAL_MODE:
                print("Running agent in LOCAL_MODE...")
                from backend.agent.model import SupplyChainPyFuncAgent
                agent = SupplyChainPyFuncAgent(catalog_schema=CATALOG_SCHEMA)
                agent.load_context(None)
                
                # Predict expects a dict with query and messages
                predictions = agent.predict(None, {
                    "query": request.query,
                    "messages": session_history[request.session_id]
                })
            else:
                # Call the hosted agent endpoint
                response = w.serving_endpoints.query(
                    name=AGENT_ENDPOINT_NAME,
                    inputs={"messages": session_history[request.session_id]}
                )
                predictions = response.predictions if hasattr(response, 'predictions') else []
                
            output_msg = predictions[0] if isinstance(predictions, list) and len(predictions) > 0 else "No response from agent."
            
            import json
            try:
                parsed_msg = json.loads(output_msg)
                if isinstance(parsed_msg, dict) and parsed_msg.get("type") == "fastmcp_tool_call":
                    tool_name = parsed_msg.get("tool")
                    args = parsed_msg.get("arguments", {})
                    assistant_msg = parsed_msg.get("assistant_message")
                    tool_call_id = parsed_msg.get("tool_call_id")
                    
                    # Execute FastMCP locally
                    import importlib
                    
                    tool_calls_executed.append({"tool_name": tool_name, "status": "executed locally via FastAPI"})
                    
                    try:
                        module = importlib.import_module(f"backend.tools.mcp.{tool_name}")
                        if hasattr(module, tool_name):
                            func = getattr(module, tool_name)
                            result = func(**args)
                        else:
                            result = f"Tool Error: Function {tool_name} not found in module."
                    except ModuleNotFoundError:
                        result = f"Tool Error: Tool {tool_name} not found locally."
                    except Exception as e:
                        result = f"Tool Error: {str(e)}"
                    
                    # 1. Append assistant tool_call message
                    if assistant_msg:
                        session_history[request.session_id].append(assistant_msg)
                    elif tool_call_id:
                        session_history[request.session_id].append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(args)
                                }
                            }]
                        })
                        
                    # 2. Append tool result message
                    session_history[request.session_id].append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": str(result)
                    })
                    
                    # Loop continues, allowing the agent to process the tool output
                    continue
                    
            except json.JSONDecodeError:
                pass # Normal string response from agent
                
            # Normal response received, break loop
            session_history[request.session_id].append({"role": "assistant", "content": output_msg})
            
            return ChatResponse(
                message=output_msg,
                tool_calls=tool_calls_executed
            )
            
        return ChatResponse(
            message="Agent reached maximum tool iterations.", 
            tool_calls=tool_calls_executed
        )
    except Exception as e:
        error_msg = str(e)
        if "not ready" in error_msg.lower() or "not_ready" in error_msg.lower() or "503" in error_msg:
            return ChatResponse(message="⏳ The Databricks Agent endpoint is still provisioning. This usually takes 5-10 minutes. Please try again shortly!")
        raise HTTPException(status_code=500, detail=f"Error querying agent endpoint: {error_msg}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        catalog, schema = CATALOG_SCHEMA.split(".")
        volume_path = f"/Volumes/{catalog}/{schema}/uploads/{file.filename}"
        
        contents = await file.read()
        w.files.upload(volume_path, contents, overwrite=True)
        
        return {"filename": file.filename, "volume_path": volume_path, "status": "uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
