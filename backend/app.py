import os
import mlflow
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from backend.agent.config import CATALOG_SCHEMA, MAX_ITERATIONS

IS_DATABRICKS_APP = bool(os.getenv("DATABRICKS_APP_NAME"))

# Set MLflow Experiment so traces are visible in the Shared folder
experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/supply_chain_agent")
if IS_DATABRICKS_APP:
    mlflow.set_tracking_uri("databricks")
else:
    # Use local profile for authentication when running locally
    profile = os.getenv("DATABRICKS_PROFILE", "myenv")
    mlflow.set_tracking_uri(f"databricks://{profile}")
    
mlflow.set_experiment(experiment_name)

# Enable MLflow tracing
mlflow.langchain.autolog()

# Initialize Databricks SDK for App Service Principal (Shared Auth)
if IS_DATABRICKS_APP:
    # Auto-authenticates using the App's service principal
    shared_w = WorkspaceClient()
else:
    shared_w = WorkspaceClient(profile=os.getenv("DATABRICKS_PROFILE"))

app = FastAPI(title="EDH Agent API")

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
    selected_tools: list = None
    selected_skills: list = None
    user_prompt: str = None

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

class UserSkillRequest(BaseModel):
    name: str
    content: str = ""


def _extract_user_token(req_obj: Request):
    """Pull the OBO access token out of the inbound request headers, if present."""
    token = req_obj.headers.get("X-Forwarded-Access-Token") or req_obj.headers.get("x-forwarded-access-token")
    if not token:
        token = req_obj.headers.get("X-Forwarded-Authorization")
    if not token:
        auth_header = req_obj.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    return token


def _workspace_client_for(req_obj: Request):
    """Build a WorkspaceClient scoped to the calling user (OBO), falling back to the app identity."""
    token = _extract_user_token(req_obj)
    if token:
        return WorkspaceClient(host=os.getenv("DATABRICKS_HOST"), token=token, auth_type="pat")
    return shared_w

# In-memory store for conversational history
session_history = {}


def _extract_item_text(item):
    """Pull the plain text out of a ResponsesAgent output item (object or dict)."""
    if item is None:
        return None
    content = getattr(item, "content", None) if not isinstance(item, dict) else item.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in ("output_text", "text"):
                parts.append(block.get("text", ""))
        return "".join(parts)
    return None

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
        
        from backend.agent.model import EDHAgent
        
        agent = EDHAgent()
        agent.load_context(
            context=None, 
            user_token=user_token,
            selected_tools=request.selected_tools,
            selected_skills=request.selected_skills,
            user_prompt=request.user_prompt
        )
        
        from mlflow.types.responses import ResponsesAgentRequest
        
        # Construct the request dictionary matching MLflow ResponsesAgent schema
        req = ResponsesAgentRequest(
            input=[{"role": msg["role"], "content": msg["content"]} for msg in session_history[request.session_id]],
            custom_inputs={"session_id": request.session_id}
        )
        
        # Use Server-Sent Events to stream the response
        from fastapi.responses import StreamingResponse
        import asyncio
        import json
        
        async def event_generator():
            nonlocal tool_calls_executed
            output_msg = ""
            # The agent's predict_stream is a *blocking* generator (tools like ask_genie can
            # poll Genie for minutes). Run it on a worker thread and hand events back to the
            # event loop through a queue, so other requests aren't stalled. Keeping the whole
            # generator on one executor thread also keeps MLflow's trace context consistent.
            loop = asyncio.get_running_loop()
            event_queue: asyncio.Queue = asyncio.Queue()  # unbounded: put_nowait never raises
            _PRODUCER_DONE = object()

            def _produce_events():
                try:
                    for ev in agent.predict_stream(req):
                        loop.call_soon_threadsafe(event_queue.put_nowait, ("event", ev))
                except Exception as exc:
                    loop.call_soon_threadsafe(event_queue.put_nowait, ("error", exc))
                finally:
                    loop.call_soon_threadsafe(event_queue.put_nowait, ("done", _PRODUCER_DONE))

            producer_future = loop.run_in_executor(None, _produce_events)
            try:
                while True:
                    _kind, _payload = await event_queue.get()
                    if _kind == "done":
                        break
                    if _kind == "error":
                        raise _payload
                    stream_event = _payload
                    # The type could be accessible via attribute or dict key depending on MLflow version
                    event_type = getattr(stream_event, "type", None) if not isinstance(stream_event, dict) else stream_event.get("type")
                    
                    if event_type in ["response.output_text.delta", "output_text.delta"]:
                        chunk = getattr(stream_event, "delta", "") if not isinstance(stream_event, dict) else stream_event.get("delta", "")
                        if chunk:
                            output_msg += chunk
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    elif event_type in ["response.reasoning_text.delta", "reasoning_text.delta"]:
                        reasoning_chunk = getattr(stream_event, "delta", "") if not isinstance(stream_event, dict) else stream_event.get("delta", "")
                        if reasoning_chunk:
                            yield f"data: {json.dumps({'type': 'reasoning', 'content': reasoning_chunk})}\n\n"
                    elif event_type in ["response.reasoning_reclassify", "reasoning_reclassify"]:
                        moved = getattr(stream_event, "delta", "") if not isinstance(stream_event, dict) else stream_event.get("delta", "")
                        if moved:
                            # Pull the leaked preamble back out of the running answer text.
                            if output_msg.endswith(moved):
                                output_msg = output_msg[: -len(moved)]
                            yield f"data: {json.dumps({'type': 'reclassify', 'content': moved})}\n\n"
                    elif event_type in ["response.output_item.done", "output_item.done"]:
                        # Authoritative final answer (scaffolding already stripped) — replace
                        # whatever was streamed so no raw tool markup can remain visible.
                        item = getattr(stream_event, "item", None) if not isinstance(stream_event, dict) else stream_event.get("item")
                        final_text = _extract_item_text(item)
                        if final_text is not None:
                            output_msg = final_text
                            yield f"data: {json.dumps({'type': 'final', 'content': final_text})}\n\n"
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
                # Ensure the worker thread has fully finished before we close the stream.
                try:
                    await producer_future
                except Exception:
                    pass
                # Normal response received, break loop
                trace_id = "unknown"
                try:
                    import mlflow
                    active_trace_id = mlflow.get_last_active_trace_id()
                    if active_trace_id:
                        trace_id = active_trace_id
                        print(f"DEBUG: Trace ID extracted: {trace_id}")
                    else:
                        print("DEBUG: No active trace found in finally block.")
                except Exception as e:
                    print(f"DEBUG: Error getting trace ID: {e}")
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

# Tools that the agent always binds regardless of UC discovery or user selection. These don't
# come from system.information_schema, so we inject them into the discovery response so the UI
# can show them. They are governed at call time by the user's OBO identity.
ALWAYS_ON_TOOLS = [
    {"name": "query_lakehouse", "type": "Managed MCP · SQL", "always_on": True},
    {"name": "ask_genie", "type": "Managed MCP · Genie", "always_on": True},
    {"name": "list_genies", "type": "Managed MCP · Genie", "always_on": True},
    {"name": "read_skill", "type": "Local", "always_on": True},
]


def _with_always_on_tools(tools):
    """Prepend the always-on tools to a discovered tool list (de-duplicated by name)."""
    existing = {t.get("name") for t in tools}
    return [t for t in ALWAYS_ON_TOOLS if t["name"] not in existing] + list(tools)


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
            
    # Optional SQLite cache for tools and skills
    import sqlite3
    import hashlib
    import json
    import time
    
    token_hash = hashlib.sha256(user_token.encode()).hexdigest() if user_token else "shared"
    cache_db_path = os.path.join(os.path.dirname(__file__), 'tools_skills_cache.db')
    
    try:
        conn = sqlite3.connect(cache_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                token_hash TEXT PRIMARY KEY,
                tools TEXT,
                skills TEXT,
                timestamp REAL
            )
        ''')
        conn.commit()
        
        cursor.execute("SELECT tools, skills, timestamp FROM cache WHERE token_hash = ?", (token_hash,))
        row = cursor.fetchone()
        
        # Cache valid for 1 hour (3600 seconds)
        if row and (time.time() - row[2]) < 3600:
            cached_tools = _with_always_on_tools(json.loads(row[0]))
            cached_skills = json.loads(row[1])
            
            default_tools_env = os.getenv("DEFAULT_TOOLS", "")
            if default_tools_env.strip().lower() == "all":
                default_tools = [t["name"] for t in cached_tools]
            else:
                default_tools = [t.strip() for t in default_tools_env.split(",") if t.strip()]
                
            default_skills_env = os.getenv("DEFAULT_SKILLS", "")
            if default_skills_env.strip().lower() == "all":
                default_skills = cached_skills
            else:
                default_skills = [s.strip() for s in default_skills_env.split(",") if s.strip()]
                
            return {
                "tools": cached_tools, 
                "skills": cached_skills,
                "default_tools": default_tools,
                "default_skills": default_skills
            }
    except Exception as e:
        print(f"Warning: Cache error {e}")
        
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

        if not DATABRICKS_WAREHOUSE_ID:
            # Without a warehouse we can't query information_schema. Don't 500 the whole panel:
            # the always-on managed-MCP tools and personal skills don't need it.
            print("Warning: DATABRICKS_WAREHOUSE_ID is not set; skipping UC tool/skill discovery.")

        # Query for tools (functions). Wrapped so a warehouse failure doesn't break the panel —
        # the always-on managed-MCP tools are still returned below.
        if DATABRICKS_WAREHOUSE_ID:
            try:
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
                if response_tools.status.state.value == 'SUCCEEDED' and response_tools.result.data_array:
                    for row in response_tools.result.data_array:
                        tool_name = f"{row[0]}.{row[1]}.{row[2]}"
                        tool_type = "Genie Space" if "genie" in row[2].lower() else "UC Function"
                        tools.append({"name": tool_name, "type": tool_type})
            except Exception as e:
                print(f"Warning: UC tool discovery failed: {e}")

        # Query for skills (volumes named 'skills'). Also wrapped — personal skills are served
        # separately by /user-skills, so a warehouse failure here shouldn't break the panel.
        if DATABRICKS_WAREHOUSE_ID:
            try:
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
                if response_skills.status.state.value == 'SUCCEEDED' and response_skills.result.data_array:
                    for row in response_skills.result.data_array:
                        volume_path = f"/Volumes/{row[0]}/{row[1]}/{row[2]}"
                        try:
                            files = w.files.list_directory_contents(volume_path)
                            for file_info in files:
                                if file_info.path.endswith(".md"):
                                    skills.append(os.path.basename(file_info.path)[:-3])
                        except Exception as e:
                            print(f"Error listing volume {volume_path}: {e}")
            except Exception as e:
                print(f"Warning: UC skill discovery failed: {e}")
                    
        # Save to cache
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO cache (token_hash, tools, skills, timestamp) VALUES (?, ?, ?, ?)",
                (token_hash, json.dumps(tools), json.dumps(skills), time.time())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to save to cache {e}")
            
        tools = _with_always_on_tools(tools)

        default_tools_env = os.getenv("DEFAULT_TOOLS", "")
        if default_tools_env.strip().lower() == "all":
            default_tools = [t["name"] for t in tools]
        else:
            default_tools = [t.strip() for t in default_tools_env.split(",") if t.strip()]
            
        default_skills_env = os.getenv("DEFAULT_SKILLS", "")
        if default_skills_env.strip().lower() == "all":
            default_skills = skills
        else:
            default_skills = [s.strip() for s in default_skills_env.split(",") if s.strip()]
        
        return {
            "tools": tools, 
            "skills": skills,
            "default_tools": default_tools,
            "default_skills": default_skills
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# User-scoped skills: personal markdown skills stored in the caller's own
# Databricks workspace folder (/Workspace/Users/{email}/edh_agent_skills/).
# Managed under the user's OBO identity so each user only sees/edits their own.
# ---------------------------------------------------------------------------
@app.get("/user-skills")
async def list_user_skills_endpoint(req_obj: Request):
    try:
        from backend.tools import user_skills
        w = _workspace_client_for(req_obj)
        return {"skills": user_skills.list_user_skills(w)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to list user skills: {str(e)}")


@app.get("/user-skills/{name}")
async def get_user_skill_endpoint(name: str, req_obj: Request):
    try:
        from backend.tools import user_skills
        w = _workspace_client_for(req_obj)
        content = user_skills.read_user_skill(w, name)
        if content is None:
            raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
        return {"name": user_skills.safe_skill_name(name), "content": content}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to read user skill: {str(e)}")


@app.put("/user-skills")
async def save_user_skill_endpoint(request: UserSkillRequest, req_obj: Request):
    try:
        from backend.tools import user_skills
        if not user_skills.safe_skill_name(request.name):
            raise HTTPException(status_code=400, detail="A valid skill name is required.")
        w = _workspace_client_for(req_obj)
        path = user_skills.write_user_skill(w, request.name, request.content)
        return {"status": "saved", "name": user_skills.safe_skill_name(request.name), "path": path}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save user skill: {str(e)}")


@app.delete("/user-skills/{name}")
async def delete_user_skill_endpoint(name: str, req_obj: Request):
    try:
        from backend.tools import user_skills
        w = _workspace_client_for(req_obj)
        ok = user_skills.delete_user_skill(w, name)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
        return {"status": "deleted", "name": user_skills.safe_skill_name(name)}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete user skill: {str(e)}")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        import io
        if not CATALOG_SCHEMA or "." not in CATALOG_SCHEMA:
            raise HTTPException(status_code=400, detail="CATALOG_SCHEMA is not configured; cannot resolve an upload volume.")
        catalog, schema = CATALOG_SCHEMA.split(".", 1)
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
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8001, reload=True)
