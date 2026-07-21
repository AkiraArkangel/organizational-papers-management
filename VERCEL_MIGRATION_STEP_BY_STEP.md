# Step-by-Step Guide: Run Database Migration Using Vercel CLI

## Prerequisites
- Node.js installed on your computer
- Vercel account with access to the project
- Git repository connected to Vercel

## Step 1: Install Node.js (if not already installed)
1. Download Node.js from https://nodejs.org/
2. Install the LTS version (recommended)
3. Verify installation:
   ```bash
   node --version
   npm --version
   ```

## Step 2: Install Vercel CLI
1. Open PowerShell or Command Prompt
2. Run the following command:
   ```bash
   npm install -g vercel
   ```
3. Verify installation:
   ```bash
   vercel --version
   ```

## Step 3: Login to Vercel
1. Run the login command:
   ```bash
   vercel login
   ```
2. Choose your login method (GitHub, GitLab, Bitbucket, or Email)
3. Follow the authentication steps in your browser
4. Once authenticated, you'll see a success message

## Step 4: Navigate to Your Project Directory
1. Open PowerShell and navigate to your project:
   ```bash
   cd "c:\Users\louie\OneDrive\Desktop\Organizational_Papers_Management_System"
   ```

## Step 5: Pull Environment Variables
1. Run the following command to pull your Vercel environment variables:
   ```bash
   vercel env pull .env.local
   ```
2. This will create a `.env.local` file with your production environment variables
3. This file includes your `DATABASE_URL` and other production settings

## Step 6: Verify Environment Variables
1. Check that the `.env.local` file was created:
   ```bash
   Get-Content .env.local
   ```
2. Ensure it contains your `DATABASE_URL` and other necessary variables

## Step 7: Activate Virtual Environment
1. Activate your Python virtual environment:
   ```bash
   .\organizational_env\Scripts\Activate.ps1
   ```
2. You should see `(organizational_env)` in your command prompt

## Step 8: Install Dependencies (if needed)
1. Navigate to the organizational_root directory:
   ```bash
   cd organizational_root
   ```
2. Install dependencies if not already installed:
   ```bash
   pip install -r requirements.txt
   ```

## Step 9: Run Database Migration
1. Run the Django migration command:
   ```bash
   python manage.py migrate
   ```
2. You should see output like:
   ```
   Operations to perform:
     Apply all migrations: admin, auth, contenttypes, documents, sessions
   Running migrations:
     Applying documents.0023_remove_document_corrected_file_and_more... OK
   ```
3. If successful, the migration will be applied to your production database

## Step 10: Verify Migration
1. Check that the migration was applied:
   ```bash
   python manage.py showmigrations
   ```
2. Look for `documents.0023_remove_document_corrected_file_and_more` marked with `[X]`

## Step 11: Test Your Application
1. Visit your Vercel deployment URL
2. Test the dashboard and other pages
3. Verify that file upload and download functionality works

## Troubleshooting

### Issue: "vercel: command not found"
**Solution:** Ensure Node.js is installed and Vercel CLI is installed globally

### Issue: "Authentication failed"
**Solution:** Run `vercel logout` then `vercel login` again

### Issue: "No environment variables found"
**Solution:** Ensure your Vercel project has environment variables configured in the dashboard

### Issue: "Database connection error"
**Solution:** Check that your `DATABASE_URL` in `.env.local` is correct and the database is accessible

### Issue: "Migration already applied"
**Solution:** This is normal if the migration was already run. Check `python manage.py showmigrations`

### Issue: "Permission denied" on PowerShell
**Solution:** Run PowerShell as Administrator or use execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Additional Notes

- The `.env.local` file contains sensitive information - do not commit it to Git
- You can run `vercel env pull` anytime to get the latest environment variables
- If you need to add new environment variables, use the Vercel dashboard or `vercel env add`
- The migration is safe to run multiple times - Django will detect if it's already applied

## Cleanup (Optional)

After completing the migration, you can remove the `.env.local` file for security:
```bash
Remove-Item .env.local
```

You can always pull it again later with `vercel env pull .env.local` if needed.
