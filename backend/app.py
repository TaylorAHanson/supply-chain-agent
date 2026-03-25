import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from backend.agent.config import AGENT_ENDPOINT_NAME, CATALOG_SCHEMA, MAX_ITERATIONS

LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"

# Initialize Databricks SDK.
w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE", "myenv"))

app = FastAPI(title="Supply Chain Agent API")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# In-memory store for conversational history
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
        if LOCAL_MODE:
            print("Running LangGraph agent in LOCAL_MODE...")
            from backend.agent.model import SupplyChainLangGraphAgent
            from mlflow.types.responses import ResponsesAgentRequest
            
            agent = SupplyChainLangGraphAgent()
            agent.load_context(None)
            
            # Construct the ResponsesAgentRequest
            req = ResponsesAgentRequest(
                input=[{"role": msg["role"], "content": msg["content"]} for msg in session_history[request.session_id]]
            )
            
            # Use Server-Sent Events to stream the response
            from fastapi.responses import StreamingResponse
            import json
            
            async def event_generator():
                nonlocal tool_calls_executed
                output_msg = ""
                try:
                    for stream_event in agent.predict_stream(req):
                        # The type could be accessible via attribute or dict key depending on MLflow version
                        event_type = getattr(stream_event, "type", None) if not isinstance(stream_event, dict) else stream_event.get("type")
                        
                        if event_type in ["response.output_text.delta", "output_text.delta"]:
                            chunk = getattr(stream_event, "delta", "") if not isinstance(stream_event, dict) else stream_event.get("delta", "")
                            if chunk:
                                output_msg += chunk
                                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                        elif event_type == "response.output_item.done":
                            # We monkey patched custom_outputs onto the done event in model.py
                            if hasattr(stream_event, "custom_outputs"):
                                tool_calls_executed = stream_event.custom_outputs.get("tool_calls", [])
                                yield f"data: {json.dumps({'type': 'tool_calls', 'content': tool_calls_executed})}\n\n"
                except Exception as stream_err:
                    print(f"DEBUG: Streaming error: {stream_err}")
                    import traceback
                    traceback.print_exc()
                    yield f"data: {json.dumps({'type': 'error', 'content': str(stream_err)})}\n\n"
                finally:
                    # Normal response received, break loop
                    session_history[request.session_id].append({"role": "assistant", "content": output_msg})
                    yield "data: [DONE]\n\n"
                    
            return StreamingResponse(event_generator(), media_type="text/event-stream")
                
        else:
            # Call the hosted agent endpoint using streaming
            import json
            import httpx
            from fastapi.responses import StreamingResponse
            
            # Construct the endpoint URL
            host = w.config.host
            
            # Authenticate properly (handles OAuth, PATs, etc)
            auth_headers = w.config.authenticate()
            if isinstance(auth_headers, dict) and "Authorization" in auth_headers:
                token = auth_headers["Authorization"].replace("Bearer ", "")
            else:
                token = w.config.token
                
            # Use the OpenAI-compatible chat/completions endpoint for ResponsesAgent
            endpoint_url = f"{host}/serving-endpoints/{AGENT_ENDPOINT_NAME}/invocations"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": session_history[request.session_id],
                "stream": True,
                "custom_inputs": {"session_id": request.session_id}
            }
            
            async def remote_event_generator():
                nonlocal tool_calls_executed
                output_msg = ""
                
                try:
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", endpoint_url, headers=headers, json=payload, timeout=60.0) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                print(f"DEBUG: Endpoint returned {response.status_code}: {error_text}")
                                yield f"data: {json.dumps({'type': 'error', 'content': f'Endpoint returned {response.status_code}'})}\n\n"
                                return
                                
                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                    
                                if line.startswith("data: "):
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        break
                                        
                                    try:
                                        data = json.loads(data_str)
                                        
                                        event_type = data.get("type", "")
                                        
                                        # Handle MLflow ResponsesAgent chunks
                                        if event_type in ["response.output_text.delta", "output_text.delta"]:
                                            chunk = data.get("delta", "")
                                            if chunk:
                                                output_msg += chunk
                                                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                                                
                                        # Also look for custom_outputs if the Databricks backend sends them in the stream
                                        if "custom_outputs" in data or event_type == "response.output_item.done":
                                            custom_outs = data.get("custom_outputs", {})
                                            tool_calls = custom_outs.get("tool_calls", [])
                                            if tool_calls:
                                                tool_calls_executed = tool_calls
                                                yield f"data: {json.dumps({'type': 'tool_calls', 'content': tool_calls_executed})}\n\n"
                                                
                                    except json.JSONDecodeError:
                                        pass
                                        
                except Exception as stream_err:
                    print(f"DEBUG: Remote streaming error: {stream_err}")
                    import traceback
                    traceback.print_exc()
                    yield f"data: {json.dumps({'type': 'error', 'content': str(stream_err)})}\n\n"
                finally:
                    # Normal response received, break loop
                    session_history[request.session_id].append({"role": "assistant", "content": output_msg})
                    yield "data: [DONE]\n\n"
                    
            return StreamingResponse(remote_event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        if "not ready" in error_msg.lower() or "not_ready" in error_msg.lower() or "503" in error_msg:
            return ChatResponse(message="⏳ The Databricks Agent endpoint is still provisioning. This usually takes 5-10 minutes. Please try again shortly!")
        raise HTTPException(status_code=500, detail=f"Error querying agent endpoint: {error_msg}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        import io
        catalog, schema = CATALOG_SCHEMA.split(".")
        volume_path = f"/Volumes/{catalog}/{schema}/uploads/{file.filename}"
        
        contents = await file.read()
        w.files.upload(volume_path, io.BytesIO(contents), overwrite=True)
        
        return {"filename": file.filename, "volume_path": volume_path, "status": "uploaded"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
