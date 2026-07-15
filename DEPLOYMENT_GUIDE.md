# Deployment Guide: Django App to Vercel

## Prerequisites
- Vercel account (free tier available)
- GitHub account (for Git-based deployment)
- PostgreSQL database (recommended for production - Vercel Postgres or external)
- Python 3.14+ installed locally

## Step 1: Prepare Your Django App for Vercel

### 1.1 Update requirements.txt
Your current requirements.txt is minimal. Add missing dependencies:

```
asgiref==3.11.1
Django==6.0.4
sqlparse==0.5.5
tzdata==2026.2
psycopg2-binary==2.9.9  # PostgreSQL adapter
whitenoise==6.6.0  # Static file serving
gunicorn==21.2.0  # Production WSGI server
```

### 1.2 Create vercel.json Configuration
Create `vercel.json` in your project root:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "organizational_root/wsgi.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "organizational_root/wsgi.py"
    }
  ]
}
```

### 1.3 Create .env.example File
Create `.env.example` in your project root:

```
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@host:port/database
ALLOWED_HOSTS=your-app.vercel.app
```

### 1.4 Update Django Settings for Production
In `organizational_root/settings.py`:

```python
import os
import dj_database_url

# Security
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-development-secret-key')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database (PostgreSQL for production)
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True
        )
    }
else:
    # SQLite for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Whitenoise for static file serving
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... other middleware
]
```

### 1.5 Update requirements.txt Again
Add the new dependency:

```
dj-database-url==2.1.0
```

## Step 2: Set Up PostgreSQL Database

### Option A: Vercel Postgres (Recommended)
1. Go to Vercel dashboard
2. Click "Storage" → "Create Database"
3. Select "Postgres"
4. Choose a region and create
5. Copy the connection string (DATABASE_URL)

### Option B: External PostgreSQL
1. Use services like Supabase, Railway, or Neon
2. Get your DATABASE_URL connection string
3. Save it for environment variables

## Step 3: Push Code to GitHub

### 3.1 Initialize Git Repository
```bash
cd c:\Users\louie\OneDrive\Desktop\Organizational_Papers_Management_System
git init
git add .
git commit -m "Initial commit"
```

### 3.2 Create GitHub Repository
1. Go to GitHub.com
2. Create a new repository
3. Copy the repository URL

### 3.3 Push to GitHub
```bash
git remote add origin https://github.com/your-username/your-repo-name.git
git branch -M main
git push -u origin main
```

### 3.4 Create .gitignore
Create `.gitignore` in project root:

```
organizational_env/
__pycache__/
*.pyc
*.pyo
*.pyd
db.sqlite3
.env
.venv
*.log
.DS_Store
```

## Step 4: Deploy to Vercel

### 4.1 Connect Vercel to GitHub
1. Go to [vercel.com](https://vercel.com)
2. Sign up/login
3. Click "Add New Project"
4. Import your GitHub repository

### 4.2 Configure Project Settings
1. **Framework Preset**: Select "Other"
2. **Root Directory**: `organizational_root`
3. **Build Command**: Leave empty (Vercel auto-detects)
4. **Output Directory**: Leave empty

### 4.3 Add Environment Variables
In Vercel project settings → Environment Variables:

```
DEBUG = False
SECRET_KEY = (generate a strong random key)
DATABASE_URL = (your PostgreSQL connection string)
ALLOWED_HOSTS = your-project-name.vercel.app
```

**Generate SECRET_KEY:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4.4 Deploy
1. Click "Deploy"
2. Wait for deployment to complete
3. Vercel will provide a URL like `https://your-project.vercel.app`

## Step 5: Post-Deployment Setup

### 5.1 Run Migrations
Since Vercel is serverless, you need to run migrations manually:

**Option A: Use Vercel CLI**
```bash
npm install -g vercel
vercel login
vercel env pull .env
vercel run python manage.py migrate
```

**Option B: Use Django Admin Shell**
1. Access your deployed app
2. Add `/admin` to URL
3. Create superuser if needed
4. Use Django shell to run migrations

### 5.2 Collect Static Files
```bash
vercel run python manage.py collectstatic --noinput
```

### 5.3 Create Superuser (if needed)
```bash
vercel run python manage.py createsuperuser
```

## Step 6: Configure Custom Domain (Optional)

1. In Vercel project settings → Domains
2. Add your custom domain
3. Update DNS records as instructed by Vercel

## Troubleshooting

### Common Issues:

**1. Database Connection Errors**
- Verify DATABASE_URL is correct
- Check PostgreSQL database is accessible
- Ensure database allows connections from Vercel's IP ranges

**2. Static Files Not Loading**
- Ensure whitenoise is properly configured
- Run `collectstatic` command
- Check STATIC_ROOT setting

**3. 500 Errors**
- Check Vercel deployment logs
- Verify all environment variables are set
- Ensure DEBUG is False for production

**4. Allowed Hosts Error**
- Add your Vercel domain to ALLOWED_HOSTS
- Include both with and without www

## Maintenance

### Updating Your App
1. Make changes locally
2. Commit and push to GitHub
3. Vercel auto-deploys on push

### Database Backups
- If using Vercel Postgres, backups are automatic
- For external databases, set up regular backups

### Monitoring
- Use Vercel Analytics for performance monitoring
- Check Vercel logs for errors
- Set up error tracking (Sentry, etc.)

## Cost Considerations

- **Vercel**: Free tier includes:
  - 100GB bandwidth per month
  - 6,000 minutes of execution time
  - Unlimited deployments
  
- **Vercel Postgres**: Free tier includes:
  - 512MB storage
  - 60 hours of compute time per month
  
- **External PostgreSQL**: Costs vary by provider

## Security Best Practices

1. Never commit `.env` file
2. Use strong SECRET_KEY
3. Keep dependencies updated
4. Enable HTTPS (automatic on Vercel)
5. Regular database backups
6. Monitor for suspicious activity

## Support

- Vercel Documentation: https://vercel.com/docs
- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/
- Vercel Community: https://vercel.com/community
