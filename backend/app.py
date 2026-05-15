import os
import mlflow
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from backend.agent.config import CATALOG_SCHEMA, MAX_ITERATIONS

# Set MLflow Experiment so traces are visible in the Shared folder
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/supply_chain_agent")
mlflow.set_experiment(experiment_name)

# Enable MLflow tracing
mlflow.langchain.autolog()

IS_DATABRICKS_APP = bool(os.getenv("DATABRICKS_APP_NAME"))

# Initialize Databricks SDK for App Service Principal (Shared Auth)
if IS_DATABRICKS_APP:
    # Auto-authenticates using the App's service principal
    shared_w = WorkspaceClient()
else:
    shared_w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE"))

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

class FeedbackRequest(BaseModel):
    session_id: str
    trace_id: str = None
    rating: int # 1 for upvote, -1 for downvote
    comment: str = None

# In-memory store for conversational history
session_history = {}

@app.post("/clear_chat")
async def clear_chat(request: ClearChatRequest):
    if request.session_id in session_history:
        del session_history[request.session_id]
    return {"status": "cleared"}

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    try:
        # In a production scenario, this would write directly to a Delta table via UC
        # For example, using the Databricks SQL Connector or WorkspaceClient
        print(f"Feedback received: Session {request.session_id}, Trace {request.trace_id}, Rating {request.rating}")
        
        # Example of writing to UC (commented out until table exists)
        # catalog, schema = CATALOG_SCHEMA.split(".")
        # sql = f"INSERT INTO {catalog}.{schema}.agent_feedback (session_id, trace_id, rating, comment) VALUES ('{request.session_id}', '{request.trace_id}', {request.rating}, '{request.comment}')"
        # shared_w.statement_execution.execute_statement(statement=sql, warehouse_id=WH_ID)
        
        return {"status": "success"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
@mlflow.trace(name="chat_endpoint")
async def chat(request: ChatRequest, req_obj: Request):
    try:
        print(f"DEBUG Headers: {req_obj.headers}")
        # Extract user token for OBO (On-Behalf-Of) authentication
        user_token = req_obj.headers.get("X-Forwarded-Access-Token")
        if not user_token:
            user_token = req_obj.headers.get("x-forwarded-access-token")
        if not user_token:
            user_token = req_obj.headers.get("X-Forwarded-Authorization")
        if not user_token:
            auth_header = req_obj.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                user_token = auth_header.replace("Bearer ", "")
        
        # Manage Session History
        if request.session_id not in session_history:
            session_history[request.session_id] = []
        
        session_history[request.session_id].append({"role": "user", "content": request.query})
        
        tool_calls_executed = []
        
        from backend.agent.model import SupplyChainLangGraphAgent
        
        agent = SupplyChainLangGraphAgent()
        agent.load_context(context=None, user_token=user_token)
        
        from mlflow.types.responses import ResponsesAgentRequest
        
        # Construct the request dictionary matching MLflow ResponsesAgent schema
        req = ResponsesAgentRequest(
            input=[{"role": msg["role"], "content": msg["content"]} for msg in session_history[request.session_id]],
            custom_inputs={"session_id": request.session_id}
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
                    elif event_type in ["response.output_item.done", "output_item.done"]:
                        if hasattr(stream_event, "custom_outputs"):
                            tool_calls_executed = stream_event.custom_outputs.get("tool_calls", [])
                            yield f"data: {json.dumps({'type': 'tool_calls', 'content': tool_calls_executed})}\n\n"
                        elif isinstance(stream_event, dict) and "custom_outputs" in stream_event:
                            tool_calls_executed = stream_event.get("custom_outputs", {}).get("tool_calls", [])
                            yield f"data: {json.dumps({'type': 'tool_calls', 'content': tool_calls_executed})}\n\n"
            except Exception as stream_err:
                print(f"DEBUG: Streaming error: {stream_err}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'content': str(stream_err)})}\n\n"
            finally:
                # Normal response received, break loop
                trace_id = "unknown"
                try:
                    import mlflow
                    active_trace = mlflow.get_last_active_trace()
                    if active_trace:
                        trace_id = active_trace.info.request_id
                except:
                    pass
                
                session_history[request.session_id].append({"role": "assistant", "content": output_msg})
                yield f"data: {json.dumps({'type': 'trace_id', 'content': trace_id})}\n\n"
                yield "data: [DONE]\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        if "not ready" in error_msg.lower() or "not_ready" in error_msg.lower() or "503" in error_msg:
            return ChatResponse(message="⏳ The Databricks Agent endpoint is still provisioning. This usually takes 5-10 minutes. Please try again shortly!")
        raise HTTPException(status_code=500, detail=f"Error querying agent endpoint: {error_msg}")

@app.get("/tools-and-skills")
async def get_tools_and_skills(req_obj: Request):
    user_token = req_obj.headers.get("X-Forwarded-Access-Token")
    if not user_token:
        user_token = req_obj.headers.get("x-forwarded-access-token")
    if not user_token:
        user_token = req_obj.headers.get("X-Forwarded-Authorization")
    if not user_token:
        auth_header = req_obj.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            user_token = auth_header.replace("Bearer ", "")
            
    try:
        if user_token:
            w = WorkspaceClient(
                host=os.getenv("DATABRICKS_HOST"), 
                token=user_token,
                auth_type="pat"
            )
        else:
            w = shared_w
            
        from backend.agent.config import DATABRICKS_WAREHOUSE_ID
        
        tools = []
        skills = []
        
        # Query for tools (functions)
        query_tools = """
        SELECT routine_catalog, routine_schema, routine_name 
        FROM system.information_schema.routines 
        WHERE routine_type = 'FUNCTION' AND routine_catalog != 'system'
        """
        response_tools = w.statement_execution.execute_statement(
            statement=query_tools,
            warehouse_id=DATABRICKS_WAREHOUSE_ID,
            wait_timeout="30s"
        )
        if response_tools.status.state.value == 'SUCCEEDED':
            for row in response_tools.result.data_array:
                tools.append(f"{row[0]}.{row[1]}.{row[2]}")
                
        # Query for skills (volumes named 'skills')
        query_skills = """
        SELECT volume_catalog, volume_schema, volume_name 
        FROM system.information_schema.volumes
        WHERE volume_name = 'skills'
        """
        response_skills = w.statement_execution.execute_statement(
            statement=query_skills,
            warehouse_id=DATABRICKS_WAREHOUSE_ID,
            wait_timeout="30s"
        )
        
        if response_skills.status.state.value == 'SUCCEEDED':
            for row in response_skills.result.data_array:
                volume_path = f"/Volumes/{row[0]}/{row[1]}/{row[2]}"
                try:
                    files = w.files.list_directory_contents(volume_path)
                    for file_info in files:
                        if file_info.path.endswith(".md"):
                            skills.append(os.path.basename(file_info.path)[:-3])
                except Exception as e:
                    print(f"Error listing volume {volume_path}: {e}")
                    
        return {"tools": tools, "skills": skills}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        import io
        catalog, schema = CATALOG_SCHEMA.split(".")
        volume_path = f"/Volumes/{catalog}/{schema}/uploads/{file.filename}"
        
        contents = await file.read()
        shared_w.files.upload(volume_path, io.BytesIO(contents), overwrite=True)
        
        return {"filename": file.filename, "volume_path": volume_path, "status": "uploaded"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Mount static React frontend for Databricks Apps
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
if os.path.exists(frontend_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
