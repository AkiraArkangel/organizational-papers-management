# Fix DATABASE_URL and Run Migration

## Problem
The `DATABASE_URL` environment variable in Vercel is corrupted, causing Django to fail connecting to the production database. The error shows:
- `dj_database_url.UnknownSchemeError: Scheme '://' is unknown`
- This means the DATABASE_URL has an invalid format

## Solution
Use the individual POSTGRES_* environment variables to construct a proper DATABASE_URL.

## Step 1: Get your POSTGRES environment variables from Vercel
Run this command to see your current POSTGRES variables:
```bash
vercel env ls
```

You should see these variables:
- POSTGRES_HOST
- POSTGRES_USER  
- POSTGRES_PASSWORD
- POSTGRES_DATABASE
- POSTGRES_URL (this might already be correct)

## Step 2: Construct the DATABASE_URL
The DATABASE_URL format should be:
```
postgresql://POSTGRES_USER:POSTGRES_PASSWORD@POSTGRES_HOST/POSTGRES_DATABASE
```

For example:
```
postgresql://user:password@host.example.com:5432/database_name
```

## Step 3: Add the DATABASE_URL to Vercel
Run this command:
```bash
vercel env add DATABASE_URL
```

When prompted:
- Select "Production" environment
- Paste your constructed DATABASE_URL
- Confirm the addition

## Step 4: Pull the updated environment variables
```bash
vercel env pull .env.local
```

## Step 5: Run the migration
```bash
cd organizational_root
python manage.py migrate
```

## Alternative: Use POSTGRES_URL directly
If `POSTGRES_URL` already exists and is correctly formatted, you can:
1. Remove the corrupted DATABASE_URL (already done)
2. Update Django settings to use POSTGRES_URL as fallback
3. Or add POSTGRES_URL as DATABASE_URL

## Quick Fix - Use POSTGRES_URL
Since you have POSTGRES_URL in your environment variables, try using that:

```bash
vercel env add DATABASE_URL
```
- When prompted for value, use the value from POSTGRES_URL
- You can get POSTGRES_URL value by running `vercel env pull .env.local` and checking the file

## After Fixing DATABASE_URL
Once the DATABASE_URL is fixed:
1. Pull environment variables: `vercel env pull .env.local`
2. Run migration: `python manage.py migrate`
3. Verify: `python manage.py showmigrations documents`
4. Test your Vercel deployment
