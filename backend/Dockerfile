FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/main.py ./main.py
COPY backend/app ./app
COPY backend/member_b.py backend/project_workspace.py backend/notifier.py ./
COPY backend/static ./static
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/migrations ./backend/migrations

EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && python -m app.seed && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
