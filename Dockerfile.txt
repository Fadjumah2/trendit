# Trendit backend — needs both Python (FastAPI + ADK agent) and Node
# (the forked MCP server, spawned as a stdio subprocess) in one container.
FROM python:3.11-slim

# --- Node.js (for mcp_server/, a TypeScript project) ---
RUN apt-get update && apt-get install -y curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python deps ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- App code ---
COPY app ./app
COPY migrations ./migrations

# --- Forked MCP server (Node/TypeScript) ---
COPY mcp_server ./mcp_server
RUN cd mcp_server && npm install && npm run build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=.

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
