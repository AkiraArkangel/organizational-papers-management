# Manual DATABASE_URL Fix Instructions

## Problem
The DATABASE_URL environment variable in Vercel is corrupted (shows as `://` instead of a proper database URL). This prevents Django from connecting to your production database to run migrations.

## Solution Steps

### Step 1: Get POSTGRES_URL from Vercel Dashboard
Since environment variables are encrypted in the CLI, you need to get the value from the Vercel web dashboard:

1. Go to https://vercel.com/dashboard
2. Navigate to your project: `organizational-papers-management`
3. Go to **Settings** > **Environment Variables**
4. Find `POSTGRES_URL` in the list
5. Click the eye icon to reveal the value
6. Copy the full POSTGRES_URL value

**The POSTGRES_URL should look like:**
```
postgresql://username:password@host:port/database_name
```

### Step 2: Add DATABASE_URL to Vercel
Run this command in your terminal:
```bash
vercel env add DATABASE_URL
```

When prompted:
- **What is the value of DATABASE_URL?** - Paste the POSTGRES_URL value you copied
- **Select the scope:** - Choose `Production`

### Step 3: Pull Updated Environment Variables
```bash
vercel env pull .env.local
```

### Step 4: Run Migration
```bash
cd organizational_root
python manage.py migrate
```

### Step 5: Verify Migration
```bash
python manage.py showmigrations documents
```

You should see `0023_remove_document_corrected_file_and_more` marked with `[X]`

## Alternative: Construct DATABASE_URL from Individual Variables
If POSTGRES_URL is also corrupted or unavailable, construct it from individual POSTGRES variables:

From Vercel Dashboard, get these values:
- POSTGRES_HOST
- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DATABASE

Then construct the URL:
```
postgresql://POSTGRES_USER:POSTGRES_PASSWORD@POSTGRES_HOST/POSTGRES_DATABASE
```

Example:
```
postgresql://myuser:mypassword@myhost.example.com:5432/mydatabase
```

## After Fixing
Once the DATABASE_URL is corrected:
1. The migration will run against your actual production database
2. The `uploaded_file_data` column will be added
3. Your Vercel deployment will work correctly

## Current Status
- ✅ Vercel deployment is running
- ✅ Django application is responding
- ❌ Database schema is outdated (missing binary storage columns)
- ❌ DATABASE_URL is corrupted, preventing migration

## Next Action
Please follow the steps above to get the POSTGRES_URL value from your Vercel dashboard and add it as DATABASE_URL. Once you've done that, let me know and I'll help you run the migration.
