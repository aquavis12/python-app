# Deployment Guide — GitHub Actions & Jenkins

This project deploys to **AWS ECS (Fargate)** from a **single Docker image** that
runs both the Flask API and the Streamlit UI. You can deploy using either
**GitHub Actions** (`.github/workflows/deploy.yml`) or **Jenkins** (`Jenkinsfile`).
Both pipelines perform the exact same steps against the same AWS resources.

---

## 1. What gets deployed

One Dockerfile builds one image containing two processes managed by `supervisord`:

```
Dockerfile  ──build──►  one image  ──run──►  ECS task (Fargate)
                                              ├── gunicorn  → :5000  (Flask API)
                                              └── streamlit → :8501  (UI)
```

The UI calls the API in the same container at `http://localhost:5000`.

| File | Role |
|------|------|
| `Dockerfile` | Builds the single combined image |
| `deploy/supervisord.conf` | Starts both processes inside the container |
| `deploy/ecs-task-definition.json` | Fargate task definition template (with placeholders) |
| `.github/workflows/deploy.yml` | GitHub Actions pipeline |
| `Jenkinsfile` | Jenkins pipeline |

The task definition template uses placeholders that each pipeline fills in at
deploy time:

- `${AWS_REGION}` → your region (for the CloudWatch log group)
- `${EXECUTION_ROLE_ARN}` → ARN of `ecsTaskExecutionRole`
- `<IMAGE>` → the freshly built image URI

---

## 2. Shared pipeline steps

Both pipelines run the same five logical steps:

1. **Checkout** the repository.
2. **Authenticate to AWS** (differs by platform — see below).
3. **Log in to ECR** and **build + push** the image, tagged with the commit SHA
   and `latest`.
4. **Render the task definition** — substitute the region/role placeholders and
   inject the new image URI.
5. **Deploy to ECS** — register the new task definition revision, update the
   service, and wait for the rollout to stabilize.

### Step-by-step comparison

| Step | GitHub Actions | Jenkins |
|------|----------------|---------|
| Checkout | `actions/checkout@v4` | `checkout scm` |
| AWS auth | OIDC role via `aws-actions/configure-aws-credentials@v4` | IAM instance role on the agent (or stored credentials) |
| ECR login | `aws-actions/amazon-ecr-login@v2` | `aws ecr get-login-password \| docker login` |
| Build & push | `docker build` + `docker push` | `docker build` + `docker push` |
| Render task def | `envsubst` + `aws-actions/amazon-ecs-render-task-definition@v1` | `envsubst` + `jq` |
| Deploy | `aws-actions/amazon-ecs-deploy-task-definition@v2` | `aws ecs register-task-definition` + `update-service` + `wait` |

The biggest difference is **step 2 (auth)** and the fact that GitHub Actions uses
ready-made marketplace actions, whereas Jenkins calls the `aws` and `docker` CLIs
directly.

---

## 3. One-time AWS setup (needed by BOTH pipelines)

1. **Create an ECR repository**
   ```bash
   aws ecr create-repository --repository-name python-task-app
   ```
2. **Create an ECS cluster and service** (Fargate) named to match the pipeline
   config (`python-task-cluster` / `python-task-service`). Front it with a load
   balancer if you want public access to ports 5000 and 8501.
3. **Create `ecsTaskExecutionRole`** — allows ECS to pull from ECR and write
   CloudWatch logs (attach the AWS-managed `AmazonECSTaskExecutionRolePolicy`).

---

## 4. GitHub Actions setup

### Authentication (OIDC — no stored keys)

1. Add GitHub as an OIDC identity provider in IAM
   (`token.actions.githubusercontent.com`).
2. Create a **deploy role** trusted by that provider, scoped to your repo, with
   permissions for ECR push, ECS update, and `iam:PassRole` on the execution role.

### Repository secrets

Add these under **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the GitHub OIDC deploy role |
| `ECS_EXECUTION_ROLE_ARN` | ARN of `ecsTaskExecutionRole` |

### Configuration

Edit the `env:` block at the top of `.github/workflows/deploy.yml`:

```yaml
env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: python-task-app
  ECS_CLUSTER: python-task-cluster
  ECS_SERVICE: python-task-service
  CONTAINER_NAME: python-task-app
```

### Trigger

The workflow runs automatically on every push to `main`, and can also be started
manually from the **Actions** tab (`workflow_dispatch`).

---

## 5. Jenkins setup

### Agent prerequisites

The build agent needs these installed:

- Docker CLI (with access to a Docker daemon)
- AWS CLI v2
- `jq`
- `envsubst` (from the `gettext` package)

### Authentication (two options)

- **Recommended:** attach an **IAM instance profile** to the Jenkins agent with
  ECR push, ECS update, and `iam:PassRole` permissions. The `Jenkinsfile` works
  with this out of the box.
- **Alternative:** store AWS keys in Jenkins and wrap the AWS stages in a
  `withCredentials` block (a commented example is at the bottom of the
  `Jenkinsfile`).

### Jenkins credentials

Add these under **Manage Jenkins → Credentials**:

| Credential ID | Type | Value |
|---------------|------|-------|
| `ecs-execution-role-arn` | Secret text | ARN of `ecsTaskExecutionRole` |
| `aws-deploy-creds` *(only if not using an instance role)* | Username with password | AWS access key / secret key |

### Configuration

Edit the `environment { }` block at the top of the `Jenkinsfile`:

```groovy
environment {
    AWS_REGION     = 'us-east-1'
    ECR_REPOSITORY = 'python-task-app'
    ECS_CLUSTER    = 'python-task-cluster'
    ECS_SERVICE    = 'python-task-service'
    CONTAINER_NAME = 'python-task-app'
}
```

### Trigger

Create a **Pipeline** job pointing at this repo with "Pipeline script from SCM"
and script path `Jenkinsfile`. Run it manually, or add an SCM webhook / poll
trigger to run on pushes.

---

## 6. Verifying a deployment

After either pipeline finishes:

```bash
# Check the service is running the new task definition and tasks are healthy
aws ecs describe-services \
  --cluster python-task-cluster \
  --services python-task-service \
  --query 'services[0].deployments'

# API health (through your load balancer or task IP)
curl http://<host>:5000/health
# UI
open http://<host>:8501
```

---

## 7. Choosing between the two

| Prefer **GitHub Actions** when... | Prefer **Jenkins** when... |
|-----------------------------------|-----------------------------|
| Your code already lives on GitHub | You run self-hosted CI already |
| You want zero infrastructure to maintain | You need on-prem / private-network agents |
| You want keyless OIDC auth | You want full control over the build environment |

Both produce the identical image and deploy it the same way, so you can start
with one and add the other later without changing the Dockerfile or task
definition.
