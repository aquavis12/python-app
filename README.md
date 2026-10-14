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

---

## Deploy to AWS ECS (single image via ECR + GitHub Actions)

For production, the app ships as **one Docker image** that runs both the Flask
API (port 5000) and the Streamlit UI (port 8501), supervised by `supervisord`.
This keeps it to a single ECR repo and a single ECS task.

```
ECS Task (Fargate)
└── python-task-app container
    ├── gunicorn  → :5000  (Flask API)
    └── streamlit → :8501  (UI, talks to API at http://localhost:5000)
```

### Build/run the combined image locally

```bash
docker build -t python-task-app .
docker run -p 5000:5000 -p 8501:8501 python-task-app
# UI:  http://localhost:8501
# API: http://localhost:5000
```

### Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Single combined image (Flask + Streamlit) |
| `deploy/supervisord.conf` | Runs both processes in the container |
| `deploy/ecs-task-definition.json` | Fargate task definition template |
| `.github/workflows/deploy.yml` | CI/CD: build → push to ECR → deploy to ECS |

### One-time AWS setup

1. **ECR repository**
   ```bash
   aws ecr create-repository --repository-name python-task-app
   ```
2. **ECS cluster + service** (Fargate) named to match the workflow `env` block
   (`python-task-cluster` / `python-task-service`), fronted by a load balancer
   if you want public access to ports 5000 and 8501.
3. **IAM roles**
   - `ecsTaskExecutionRole` — lets ECS pull from ECR and write CloudWatch logs.
   - A **GitHub OIDC deploy role** — trusted by `token.actions.githubusercontent.com`,
     with permissions for ECR push, ECS update, and `iam:PassRole` on the
     execution role.

### GitHub repository secrets

| Secret | Value |
|--------|-------|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the GitHub OIDC deploy role |
| `ECS_EXECUTION_ROLE_ARN` | ARN of `ecsTaskExecutionRole` |

### Workflow config

Edit the `env:` block at the top of `.github/workflows/deploy.yml` to match your
AWS region, ECR repo, ECS cluster, and service names. Pushing to `main` then
builds the image, pushes it to ECR, and rolls out a new ECS deployment.
