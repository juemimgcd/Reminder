import uvicorn

from services.memory_agent.app import create_memory_agent_app
from services.memory_agent.config import settings
from services.memory_agent.logging import configure_logging

configure_logging()
app = create_memory_agent_app()


if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT, access_log=False)
