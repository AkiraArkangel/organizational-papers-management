# Deployment Guide: Django App to Vercel (2024 Updated)

## Prerequisites
- Vercel account (free tier available)
- GitHub account (for Git-based deployment)
- PostgreSQL database (recommended for production - Vercel Postgres or external)

## Step 1: Prepare Your Django App for Vercel

### 1.1 Update requirements.txt
Your current requirements.txt should include:

```
asgiref==3.11.1
Django==6.0.4
sqlparse==0.5.5
tzdata==2026.2
psycopg2-binary==2.9.9  # PostgreSQL adapter
whitenoise==6.6.0  # Static file serving
dj-database-url==2.1.0  # Database URL parsing
```

### 1.2 Update Django Settings for Production
Your settings are already configured for production with environment variables. Key settings:
- `DEBUG` controlled by environment variable
- `SECRET_KEY` controlled by environment variable  
- `ALLOWED_HOSTS` controlled by environment variable
- Database switches between SQLite (local) and PostgreSQL (production)
- Whitenoise middleware for static files

### 1.3 Create .env.example File
Your `.env.example` should be:

```
DEBUG=False
SECRET_KEY=replace-this-with-a-long-random-secret-key
DATABASE_URL=postgresql://user:password@host:port/database
ALLOWED_HOSTS=your-app.vercel.app
```

## Step 2: Set Up PostgreSQL Database

### Option A: Vercel Database Marketplace (Recommended)
Vercel now offers PostgreSQL through their marketplace providers. Here are the best options:

**Supabase (Recommended - Free Tier Available)**
1. Go to Vercel dashboard → "Storage" → "Create Database"
2. Select "Supabase" from the marketplace
3. Click "Add" and follow the setup wizard
4. Create a new Supabase project or link existing one
5. Once connected, go to your Vercel project settings → Environment Variables
6. Copy the `POSTGRES_URL` or `DATABASE_URL` provided by Supabase

**Neon (Alternative - Free Tier Available)**
1. Go to Vercel dashboard → "Storage" → "Create Database"
2. Select "Neon" from the marketplace
3. Click "Add" and follow the setup wizard
4. Create a new Neon project
5. Copy the connection string from Neon dashboard
6. Add as `DATABASE_URL` in Vercel environment variables

**Prisma Postgres (Alternative)**
1. Go to Vercel dashboard → "Storage" → "Create Database"
2. Select "Prisma Postgres" from the marketplace
3. Follow the setup wizard
4. Copy the connection string provided
5. Add as `DATABASE_URL` in Vercel environment variables

### Option B: External PostgreSQL (Manual Setup)
If you prefer to set up PostgreSQL outside Vercel:

**Supabase (External)**
1. Go to [supabase.com](https://supabase.com) and sign up
2. Create a new project
3. Wait for project to be ready (2-3 minutes)
4. Go to Project Settings → Database
5. Copy the "Connection string" under "Connection info"
6. Replace `[your-password]` with your actual database password
7. Use this as your `DATABASE_URL`

**Neon (External)**
1. Go to [neon.tech](https://neon.tech) and sign up
2. Create a new project
3. Copy the connection string from the dashboard
4. Use this as your `DATABASE_URL`

**Railway (External)**
1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Provision PostgreSQL"
3. Copy the connection string from the database view
4. Use this as your `DATABASE_URL`

**Connection String Format:**
```
postgresql://username:password@host:port/database_name
```

## Step 3: Deploy to Vercel (Current Interface)

### 3.1 Go to Vercel Dashboard
1. Go to [vercel.com](https://vercel.com) and sign in
2. Click **"Add New Project"** button (top right)

### 3.2 Import Your GitHub Repository
1. You should see your GitHub repositories listed
2. Find and click **"AkiraArkangel/organizational-papers-management"**
3. Click **"Import"** button

### 3.3 Configure Project (Current Vercel Interface)
Vercel will automatically detect Django and show a configuration screen:

**Project Configuration:**
- **Project Name**: Leave as default or change to something memorable
- **Framework Preset**: Should auto-detect as "Django" (if not, select "Django")
- **Root Directory**: Type `organizational_root`
- **Build Command**: Leave empty (Vercel auto-detects)
- **Output Directory**: Leave empty

Click **"Continue"** to proceed.

### 3.4 Add Environment Variables
On the next screen, add these environment variables:

```
DEBUG = False
SECRET_KEY = (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DATABASE_URL = (leave empty for now, will add after database setup)
ALLOWED_HOSTS = localhost
```

Click **"Continue"** to proceed.

### 3.5 Deploy
1. Click **"Deploy"** button
2. Wait for deployment to complete (1-2 minutes)
3. Vercel will provide a URL like `https://your-project-name.vercel.app`
4. Copy this URL for later use

### 3.6 Connect Supabase Database
After deployment completes:

1. Go to your Vercel project dashboard
2. Click **"Storage"** tab in left sidebar
3. Click **"Create Database"**
4. Select **"Supabase"** from the marketplace
5. Click **"Add"**
6. In the integration form:
   - **Connect a Project**: Select your Vercel project (should now appear)
   - **Environments**: Select **Production**
   - **Custom Prefix**: Leave as `STORAGE_URL`
7. Click **"Install"**

### 3.7 Update Environment Variables with Database
After Supabase integration:

1. Go to your Vercel project → **Settings** → **Environment Variables**
2. Look for the Supabase connection string (likely named `POSTGRES_URL` or similar)
3. Add/update these variables:
   ```
   DATABASE_URL = (the Supabase connection string)
   ALLOWED_HOSTS = (your Vercel URL from step 3.5)
   ```
4. Click **"Save"**
5. Vercel will automatically redeploy with the database connection

### 3.8 Run Database Migrations
After the redeployment completes, you need to run migrations:

1. Install Vercel CLI: `npm install -g vercel`
2. Login: `vercel login`
3. Run migrations: `vercel run python manage.py migrate`
4. Collect static files: `vercel run python manage.py collectstatic --noinput`

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
