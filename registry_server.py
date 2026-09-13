import asyncio
import logging
import os
import uvicorn
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from python_a2a import AgentCard

from registry_store import create_store_from_env, RegistryStore


# Data model for Agent registration
class AgentRegistration(BaseModel):
    name: str
    description: str
    url: str
    version: str
    capabilities: dict = {}
    skills: List[dict] = []


class UnregisterRequest(BaseModel):
    url: str


class HeartbeatRequest(BaseModel):
    url: str


HEARTBEAT_TIMEOUT = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "90"))
CLEANUP_INTERVAL = float(os.getenv("CLEANUP_INTERVAL_SECONDS", "30"))

store: RegistryStore = create_store_from_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the cleanup task when the server starts."""
    cleanup_task = asyncio.create_task(cleanup_stale_agents())
    yield
    cleanup_task.cancel()


async def cleanup_stale_agents():
    """Periodically clean up agents that haven't sent heartbeats."""
    while True:
        try:
            pruned = store.prune_stale(HEARTBEAT_TIMEOUT)
            for url in pruned:
                logging.warning(
                    f"Agent {url} has not sent heartbeat for {HEARTBEAT_TIMEOUT} "
                    f"seconds, removing from registry"
                )
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

        await asyncio.sleep(CLEANUP_INTERVAL)


app = FastAPI(
    title="A2A Agent Registry Server",
    description="FastAPI server for agent discovery",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/registry/register", response_model=AgentCard)
async def register_agent(registration: AgentRegistration):
    """Registers a new agent with the registry (idempotent upsert)."""
    agent_card = AgentCard(**registration.model_dump())
    ok = store.register(agent_card)
    if not ok:
        raise HTTPException(status_code=400, detail="Agent URL is required")
    return agent_card


@app.post("/registry/unregister")
async def unregister_agent(request: UnregisterRequest):
    """Unregisters an agent from the registry."""
    if store.unregister(request.url):
        logging.info(f"Unregistered agent: {request.url}")
        return {"success": True}
    logging.warning(f"Unregister requested for unknown agent: {request.url}")
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Agent not registered"},
    )


@app.post("/registry/heartbeat")
async def heartbeat(request: HeartbeatRequest):
    """Handle agent heartbeat."""
    try:
        if store.heartbeat(request.url):
            logging.info(f"Received heartbeat from agent at {request.url}")
            return {"success": True}
        logging.warning(f"Received heartbeat from unregistered agent: {request.url}")
        return {"success": False, "error": "Agent not registered"}, 404
    except Exception as e:
        logging.error(f"Error processing heartbeat: {e}")
        return {"success": False, "error": str(e)}, 400


@app.get("/registry/agents", response_model=List[AgentCard])
async def list_registered_agents():
    """Lists all currently registered agents."""
    return store.list()


@app.get("/registry/agents/{url}", response_model=AgentCard)
async def get_agent(url: str):
    """Get a specific agent by URL (full URL, e.g. https://host:port)."""
    agent = store.get(url)
    if agent:
        return agent
    raise HTTPException(status_code=404, detail=f"Agent with URL '{url}' not found")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
