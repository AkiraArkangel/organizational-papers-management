# Vercel Database Migration Instructions

Since Vercel doesn't support automatic database migrations during the build process, you need to run the migration manually after deployment.

## Option 1: Using Vercel CLI (Recommended)

1. Install Vercel CLI if not already installed:
   ```bash
   npm i -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Pull environment variables:
   ```bash
   vercel env pull .env.local
   ```

4. Run the migration:
   ```bash
   vercel run python manage.py migrate
   ```

## Option 2: Using Vercel Dashboard

1. Go to your Vercel project dashboard
2. Navigate to "Settings" > "Environment Variables"
3. Copy all environment variables to your local `.env` file
4. Run migration locally with production database:
   ```bash
   python manage.py migrate
   ```

## Option 3: Using Vercel Postgres (if using Vercel Postgres)

If you're using Vercel Postgres, you can run migrations through the Vercel dashboard:

1. Go to your Vercel project dashboard
2. Navigate to "Storage" > "Postgres"
3. Click on your database
4. Use the "Query" tab to run migration SQL manually

## Migration Details

The migration that needs to be applied is:
- **Migration 0023**: `0023_remove_document_corrected_file_and_more`

This migration:
- Removes all FileField fields (uploaded_file, corrected_file, logo, photo, template_file, signed_file)
- Adds BinaryField fields for binary storage
- Adds metadata fields (filename, content_type, size, checksum, timestamps)

## Verification

After running the migration, verify it was successful by checking:
1. The deployment is live on Vercel
2. File upload functionality works
3. File download functionality works
4. PDF preview works in browser

## Important Notes

- The migration must be run before the binary storage features will work
- Without the migration, the application will not function correctly
- The migration is safe to run multiple times (Django will detect if already applied)
- Make sure to backup your database before running migrations in production
