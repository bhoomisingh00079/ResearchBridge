FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code as a Python package so relative imports work
RUN mkdir -p /app/agent_service
COPY . /app/agent_service/

EXPOSE 8100

CMD ["uvicorn", "agent_service.app:app", "--host", "0.0.0.0", "--port", "8100"]

