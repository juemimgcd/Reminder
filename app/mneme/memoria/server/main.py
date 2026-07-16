import uvicorn

from app.mneme.memoria.server.app import create_memory_agent_app
from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.logging import configure_logging

configure_logging()
app = create_memory_agent_app()


if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT, access_log=False)
