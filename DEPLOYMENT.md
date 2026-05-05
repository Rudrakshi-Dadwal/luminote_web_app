# LUMINOTE - Deployment Guide

This guide covers deploying LUMINOTE to production in different environments.

## 🎯 Deployment Options

### Option 1: Docker (Recommended for Production)

Docker makes deployment simple and consistent across any server.

#### Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  luminote:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MAX_TRANSCRIPT_CHARS=18000
      - LOG_LEVEL=INFO
    volumes:
      - ./.cache:/app/.cache  # Cache ML models
    restart: unless-stopped
```

#### Run with Docker:

```bash
# Build image
docker build -t luminote .

# Run container
docker run -p 8000:8000 luminote

# Or with docker-compose
docker-compose up
```

Then open: `http://localhost:8000`

---

### Option 2: Heroku (Free/Cheap)

#### 1. Create `Procfile`:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### 2. Create `runtime.txt`:

```
python-3.11.4
```

#### 3. Deploy:

```bash
# Install Heroku CLI from heroku.com/cli

heroku login
heroku create your-app-name
git push heroku main

# View logs
heroku logs --tail
```

Your app will be at: `https://your-app-name.herokuapp.com`

---

### Option 3: Railway.app (Simple & Modern)

1. Go to https://railway.app
2. Click "New Project"
3. Connect GitHub repo
4. Select Python
5. Railway auto-detects and deploys!

**Note**: Railway charges per use, but LUMINOTE is lightweight.

---

### Option 4: AWS (Scalable)

Use **AWS Elastic Beanstalk**:

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 luminote

# Create environment
eb create luminote-prod

# Deploy
git commit -m "deployment"
eb deploy

# Open app
eb open
```

---

### Option 5: DigitalOcean (Cheap & Simple)

1. Create a Droplet (Ubuntu 22.04, $4/month)
2. SSH into server
3. Clone your repo
4. Run:

```bash
# On server
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or with systemd (persistent)
# Copy startup script and configure as service
```

---

### Option 6: PythonAnywhere (Python-Specific)

1. Sign up at https://www.pythonanywhere.com
2. Upload your code
3. Configure WSGI file
4. Set domain name
5. App runs automatically!

---

## 🔒 Production Checklist

Before deploying, ensure:

- [ ] `DEBUG = False` (no debug mode in production)
- [ ] `.env` is configured with production values
- [ ] `.gitignore` includes `.env` (never commit secrets)
- [ ] `requirements.txt` includes all dependencies
- [ ] App works locally: `python -m uvicorn app.main:app`
- [ ] No hardcoded URLs (use environment variables)
- [ ] Logging is configured for debugging
- [ ] CORS is properly configured (not `allow_origins=["*"]` for production)
- [ ] Rate limiting is enabled (to prevent abuse)
- [ ] Database backups configured (if using database)
- [ ] HTTPS enabled (automatic on Heroku/Railway)
- [ ] Health check endpoint exists (`/health`, `/api/health`)

---

## 🚀 Production Deployment Example (Heroku)

### Complete Steps:

```bash
# 1. Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# 2. Create runtime.txt
echo "python-3.11.4" > runtime.txt

# 3. Update requirements.txt with gunicorn (production server)
pip install gunicorn
pip freeze > requirements.txt

# 4. Update Procfile to use gunicorn
echo "web: gunicorn app.main:app" > Procfile

# 5. Commit to git
git add .
git commit -m "ready for production"

# 6. Deploy to Heroku
heroku login
heroku create luminote-app
git push heroku main

# 7. View live
heroku open
```

Your app is now live at: `https://luminote-app.herokuapp.com` 🎉

---

## 📊 Monitoring in Production

### Health Checks

Your app has built-in health endpoints:

```bash
# Check if app is running
curl https://luminote-app.herokuapp.com/health

# Response: {"status": "ok"}
```

### Logs

Different platforms have different log viewers:

```bash
# Heroku
heroku logs --tail

# Docker
docker logs container-name

# DigitalOcean (SSH into server)
tail -f /path/to/app.log
```

### Error Tracking

Add error tracking service:

```python
# In app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://key@sentry.io/project",
    integrations=[FastApiIntegration()],
    environment="production"
)
```

---

## 🔄 Continuous Deployment (CI/CD)

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Heroku
        uses: akhileshns/heroku-deploy@v3.12.12
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: "luminote-app"
          heroku_email: "your@email.com"
```

Now every push to `main` auto-deploys! 🚀

---

## 💾 Database Backup (If Using DB)

### PostgreSQL Example

```bash
# Backup
pg_dump database_name > backup.sql

# Restore
psql database_name < backup.sql

# Or with Docker
docker exec container_name pg_dump -U postgres > backup.sql
```

---

## 🎯 Next Steps

1. **Choose platform**: Heroku (easiest), Railway (modern), Docker (most flexible)
2. **Test locally**: `python -m uvicorn app.main:app`
3. **Create accounts**: On chosen platform
4. **Deploy**: Follow platform-specific steps above
5. **Monitor**: Set up logging and error tracking
6. **Scale**: Add caching, database, more servers as needed

---

## 🆘 Troubleshooting Deployment

### App crashes after deploy

1. Check logs: `heroku logs --tail` (or platform equivalent)
2. Common causes:
   - Missing dependency in `requirements.txt`
   - Wrong Python version
   - Environment variable not set
   - Port not 8000 (use `PORT` env var)

### "Module not found" errors

```bash
# Make sure requirements.txt has all packages
pip freeze > requirements.txt
git push heroku main
```

### App works locally but not deployed

1. Check environment variables match
2. Verify Python version matches
3. Check `LOG_LEVEL=DEBUG` for more details
4. Use `gunicorn` instead of `uvicorn` for production

---

## 📚 Platform-Specific Docs

- **Heroku**: https://devcenter.heroku.com
- **Railway**: https://docs.railway.app
- **AWS**: https://docs.aws.amazon.com/elasticbeanstalk
- **DigitalOcean**: https://docs.digitalocean.com
- **Docker**: https://docs.docker.com
- **PythonAnywhere**: https://www.pythonanywhere.com/help

---

**Ready to deploy? Pick a platform above and follow the steps!** 🚀
