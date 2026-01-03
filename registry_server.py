import time
import asyncio
import logging
import uvicorn
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from python_a2a import AgentCard
from python_a2a.discovery import AgentRegistry


# Data model for Agent registration
class AgentRegistration(BaseModel):
    name: str
    description: str
    url: str
    version: str
    capabilities: dict = {}
    skills: List[dict] = []


class HeartbeatRequest(BaseModel):
    url: str


# Create registry server and FastAPI app
registry_server = AgentRegistry(
    name="A2A Registry Server", description="Registry server for agent discovery"
)

# Constants for cleanup
HEARTBEAT_TIMEOUT = 30  # seconds
CLEANUP_INTERVAL = 10  # seconds


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
            current_time = time.time()
            agents_to_remove = []

            # Check each agent's last heartbeat time
            for url, last_seen in registry_server.last_seen.items():
                if current_time - last_seen > HEARTBEAT_TIMEOUT:
                    agents_to_remove.append(url)
                    logging.warning(
                        f"Agent {url} has not sent heartbeat for {HEARTBEAT_TIMEOUT} seconds, removing from registry"
                    )

            # Remove stale agents
            for url in agents_to_remove:
                registry_server.unregister_agent(url)
                logging.info(f"Removed stale agent: {url}")

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


@app.post("/registry/register", response_model=AgentCard, status_code=201)
async def register_agent(registration: AgentRegistration):
    """Registers a new agent with the registry."""
    agent_card = AgentCard(**registration.model_dump())
    registry_server.register_agent(agent_card)
    return agent_card


@app.post("/registry/heartbeat")
async def heartbeat(request: HeartbeatRequest):
    """Handle agent heartbeat."""
    try:
        if request.url in registry_server.agents:
            registry_server.last_seen[request.url] = time.time()
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
    return list(registry_server.get_all_agents())


@app.get("/registry/agents/{url}", response_model=AgentCard)
async def get_agent(url: str):
    """Get a specific agent by URL."""
    agent = registry_server.get_agent(url)
    if agent:
        return agent
    raise HTTPException(status_code=404, detail=f"Agent with URL '{url}' not found")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
