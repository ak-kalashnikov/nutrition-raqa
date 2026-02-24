# Deployment Guide

This guide covers deploying the Nutrition & Sports Health RAQA system to various platforms.

## Table of Contents

- [Local Development](#local-development)
- [Docker (Recommended for Production)](#docker-recommended-for-production)
- [Hugging Face Spaces (Free, Interactive Demo)](#hugging-face-spaces-free-interactive-demo)
- [Streamlit Cloud (Free, Easy)](#streamlit-cloud-free-easy)
- [Render (Affordable, Easy)](#render-affordable-easy)
- [AWS (Scalable)](#aws-scalable)
- [Production Checklist](#production-checklist)

## Local Development

### Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd nutrition-raqa

# Run the setup script
bash setup.sh

# This will:
# - Create a virtual environment
# - Install dependencies
# - Run tests

# Then activate and run:
source .venv/bin/activate
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` for API and `http://localhost:8000/docs` for interactive API docs.

### Run Interactive Demo

In a new terminal:
```bash
source .venv/bin/activate
streamlit run demo.py
```

Visit `http://localhost:8501`

---

## Docker (Recommended for Production)

### Single Container

Build and run:
```bash
docker build -t nutrition-raqa:latest .
docker run -p 8000:8000 nutrition-raqa:latest
```

Verify:
```bash
curl http://localhost:8000/health
```

### Docker Compose (API + Demo)

```bash
docker-compose up --build
```

This starts:
- **API:** http://localhost:8000
- **Demo:** http://localhost:8501

Shut down:
```bash
docker-compose down
```

### Push to Docker Registry

For private deployment:

```bash
# Docker Hub
docker build -t yourusername/nutrition-raqa:latest .
docker login
docker push yourusername/nutrition-raqa:latest

# AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_ECR_URL>
docker build -t <YOUR_ECR_URL>/nutrition-raqa:latest .
docker push <YOUR_ECR_URL>/nutrition-raqa:latest
```

---

## Hugging Face Spaces (Free, Interactive Demo)

Perfect for showcasing your model.

### 1. Create Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Select **Streamlit** as the SDK
4. Name: `nutrition-raqa`
5. Visibility: `Public`

### 2. Upload Files

Upload to your new Space:
- `demo.py` (main file)
- `requirements.txt`
- `data/nutrition_qa.jsonl`
- `app/retriever.py`
- `app/schemas.py`
- `app/__init__.py`

Or push via Git:
```bash
cd nutrition-raqa
git remote add space https://huggingface.co/spaces/yourusername/nutrition-raqa
git push space main
```

### 3. Rename `demo.py` to `app.py`

Hugging Face Spaces looks for `app.py` by default.

```bash
mv demo.py app.py
```

Wait for automatic rebuild (~2-3 minutes).

### 4. Share

Your demo is live at:
```
https://huggingface.co/spaces/yourusername/nutrition-raqa
```

---

## Streamlit Cloud (Free, Easy)

Good for standalone Streamlit demos.

### 1. Push Code to GitHub

```bash
git push origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect GitHub repo
4. Select branch and file: `demo.py`
5. Click "Deploy"

### 3. Share

Your app is live at:
```
https://share-streamlit-app-url.streamlit.app
```

### Environment Variables

If you need to configure `API_URL`, add to `.streamlit/secrets.toml`:

```toml
API_URL = "https://your-api.example.com"
```

---

## Render (Affordable, Easy)

Deploy the FastAPI backend with a free tier.

### 1. Push to GitHub

```bash
git push origin main
```

### 2. Create New Web Service

1. Go to [render.com](https://render.com) (sign up with GitHub)
2. Click "New Web Service"
3. Connect GitHub repo
4. Settings:
   - **Name:** `nutrition-raqa-api`
   - **Runtime:** Python 3.11
   - **Build:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app`
   - **Plan:** Free tier (sleeps after 15 min inactivity)

### 3. Deploy

Click "Create Web Service" and wait for build (~2-5 minutes).

Your API is live at:
```
https://nutrition-raqa-api.onrender.com
```

### Test

```bash
curl https://nutrition-raqa-api.onrender.com/health
```

---

## AWS (Scalable)

For production-grade deployments.

### Option A: AWS Lambda (Serverless, Pay-per-use)

1. Package the app with dependencies
2. Use AWS Lambda with custom Docker image
3. Set up API Gateway for HTTP access

### Option B: ECS (Elastic Container Service)

1. Push Docker image to ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ECR_URI>
   docker tag nutrition-raqa:latest <ECR_URI>/nutrition-raqa:latest
   docker push <ECR_URI>/nutrition-raqa:latest
   ```

2. Create ECS cluster and task definition
3. Deploy service with load balancer (ALB)

### Option C: SageMaker

For ML Model Endpoint hosting (higher cost, better features):

1. Package as SageMaker inference container
2. Deploy endpoint via SageMaker console
3. Invoke via boto3 or API

```python
client = boto3.client('sagemaker-runtime')
response = client.invoke_endpoint(
    EndpointName='nutrition-raqa',
    Body=json.dumps({"question": "How much protein..."}),
    ContentType='application/json'
)
```

---

## GCP Cloud Run

### 1. Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Build and Push

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nutrition-raqa
```

### 3. Deploy

```bash
gcloud run deploy nutrition-raqa \
  --image gcr.io/YOUR_PROJECT_ID/nutrition-raqa \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --timeout 300
```

Your API is live at the returned URL:
```
https://nutrition-raqa-xxx.run.app
```

---

## Production Checklist

Before deploying to production:

### Code Quality
- [ ] Run tests: `pytest -v`
- [ ] Format code: `black app/ tests/`
- [ ] Lint code: `ruff check app/ tests/`
- [ ] No hardcoded credentials in code

### Configuration
- [ ] Environment variables in `.env` (not in code)
- [ ] Database or cache connections configured
- [ ] Logging configured with appropriate level
- [ ] CORS settings for API (if needed)

### Security
- [ ] API authentication/authorization (if needed)
- [ ] Rate limiting configured
- [ ] HTTPS enforced (all platforms)
- [ ] Input validation on all endpoints
- [ ] No sensitive data in logs

### Monitoring & Observability
- [ ] Error tracking (Sentry, DataDog, etc.)
- [ ] Performance monitoring
- [ ] Log aggregation (CloudWatch, ELK, etc.)
- [ ] Health check endpoint accessible

### Documentation
- [ ] README is up-to-date
- [ ] API documentation auto-generated (FastAPI Swagger)
- [ ] Deployment guide available
- [ ] Runbook for common issues

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Load testing (simulate expected traffic)
- [ ] Manual smoke test of deployed endpoint

### Performance
- [ ] Response times acceptable (<500ms)
- [ ] Memory usage reasonable
- [ ] Model loading optimized
- [ ] Cache strategy in place (if needed)

---

## Monitoring & Scaling

### Health Checks

All platforms support health endpoints:

```bash
# Every platform should expose:
GET /health
# Returns: {"status": "ok"}
```

### Auto-Scaling

**Render:** Automatic on Pro plan
**AWS:** Configure via IAM
**GCP Cloud Run:** Automatic based on traffic
**Azure:** Configure Virtual Machine Scale Sets

### Rate Limiting

Add to FastAPI for production safety:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## Troubleshooting Deployments

### Cold Start (Serverless)

Cold starts (10-30 seconds) are normal for serverless. To reduce:
- Use VM-based deployments (Render, AWS EC2)
- Keep model file small
- Use model quantization

### Memory Issues

If you get OOM errors:
- Reduce model size (use smaller sentence-transformer)
- Use quantization (bit-width reduction)
- Increase container memory allocation

### Slow Queries

**Solutions:**
- Cache embeddings for common queries
- Use faster model: `all-MiniLM-L6-v2` (small, fast)
- Upgrade to GPU instance (if available)

### Failed Deployments

1. Check logs: `docker logs container_id`
2. Verify `.env` variables are set
3. Ensure data file path is correct
4. Check Python version compatibility

---

## Cost Estimation

| Platform | Cost | Pros | Cons |
|----------|------|------|------|
| **Hugging Face Spaces** | Free | Interactive, easy, public | Limited to Streamlit |
| **Streamlit Cloud** | Free | Simple, easy | Single Python app only |
| **Render Free** | Free | Easy, Docker support | Sleeps after 15 min |
| **Render Pro** | $12/mo | Always-on, auto-scaling | Requires payment |
| **AWS Lambda** | ~$0.20/M requests | Scalable, pay-per-use | Complex setup |
| **GCP Cloud Run** | Similar to Lambda | Generous free tier | Slightly higher cost |
| **Heroku** | $7+/mo (paid only) | Simple deployment | Expensive for long-term |

**Recommendation for portfolio:** Start with **Hugging Face Spaces** (free demo) + **Render** (free backend for portfolio).

---

For questions or issues, see [CONTRIBUTING.md](CONTRIBUTING.md) or open a GitHub issue.
