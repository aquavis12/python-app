# Python Task Manager

A full-stack task manager: a **Flask REST API** backend + a **Streamlit** frontend, both Dockerized and wired together with Docker Compose.

## Architecture

```
Browser → Streamlit UI (port 8501)
               ↓  HTTP
          Flask API  (port 5000)
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API overview |
| GET | `/health` | Health check |
| GET | `/tasks` | List all tasks |
| POST | `/tasks` | Create a task (`{"title": "...", "description": "..."}`) |
| GET | `/tasks/<id>` | Get task by ID |
| DELETE | `/tasks/<id>` | Delete task by ID |

---

## Run with Docker Compose (recommended)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| Flask API | http://localhost:5000 |

## Run locally (without Docker)

**Terminal 1 – API:**
```bash
pip install -r requirements.txt
python app.py
```

**Terminal 2 – Frontend:**
```bash
pip install -r frontend/requirements.txt
streamlit run frontend/streamlit_app.py
```

## Example Usage

```bash
# Create a task
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy groceries", "description": "Milk, eggs, bread"}'

# List tasks
curl http://localhost:5000/tasks

# Get a specific task
curl http://localhost:5000/tasks/1

# Delete a task
curl -X DELETE http://localhost:5000/tasks/1
```
