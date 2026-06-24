FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_URL=http://host.containers.internal:11434/api/generate
ENV AMBIENT_LOG_FILE=/app/data/ambient_agent_history.md
ENV AMBIENT_STATE_FILE=/app/data/ambient_agent_state.json

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY samples /app/samples
COPY src /app/src
RUN mkdir -p /app/data

CMD ["python", "samples/ambient_agent.py", "--source", "web-all", "--interval", "120"]
