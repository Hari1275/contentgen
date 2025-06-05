# Supabase Setup Guide

Your Smart AI Content Generator now uses Supabase as the primary database. SQLite has been completely removed.

## Prerequisites

✅ You already have:
- Supabase Project URL: `https://zixrefecjrzqngadgjxj.supabase.co`
- Supabase API Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

## Step 1: Get Your Database Password

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project: `zixrefecjrzqngadgjxj`
3. Go to **Settings** → **Database**
4. Find your database password (or reset it if needed)
5. Copy the password - you'll need it for the next step

## Step 2: Update Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit your `.env` file and add:
   ```env
   # Your existing Gemini API key
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Supabase configuration (already filled in)
   SUPABASE_URL=https://zixrefecjrzqngadgjxj.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InppeHJlZmVjanJ6cW5nYWRnanhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg3NjMxOTQsImV4cCI6MjA2NDMzOTE5NH0.uTx45whd2qFu2zjwyFyaFAUuVjXb6F-dCrsoIeQXJGQ
   
   # Add your database password here
   SUPABASE_DB_PASSWORD=your_database_password_from_step1
   ```

## Step 3: Test the Connection

Run the application to test the Supabase connection:

```bash
python -m uvicorn app.main:app --reload
```

You should see output like:
```
Supabase configuration detected. Project ID: zixrefecjrzqngadgjxj
Supabase database connection configured
Database URL: postgresql://postgres:****@db.zixrefecjrzqngadgjxj.supabase.co:5432/postgres
```

## Step 4: Migrate Existing Data (Optional)

If you have existing data in SQLite that you want to migrate:

```bash
python migrate_to_supabase.py
```

This will:
- ✅ Create tables in Supabase
- ✅ Migrate all clients and content
- ✅ Backup your SQLite database
- ✅ Preserve all relationships

## Step 5: Verify Migration

1. Check your Supabase dashboard
2. Go to **Table Editor**
3. You should see `clients` and `contents` tables with your data

## Benefits of Using Supabase

✅ **Better Performance**: PostgreSQL is faster than SQLite for concurrent users
✅ **Real-time Features**: Built-in real-time subscriptions
✅ **Scalability**: Handles multiple users and large datasets
✅ **Backup & Recovery**: Automatic backups and point-in-time recovery
✅ **Security**: Row-level security and authentication
✅ **Dashboard**: Beautiful web interface to manage your data

## Troubleshooting

### Connection Issues
- Verify your database password is correct
- Check that your Supabase project is active
- Ensure you have internet connectivity

### Migration Issues
- Make sure your SQLite database exists in `./data/app.db`
- Check that all required environment variables are set
- Verify Supabase connection works before migrating

### Rollback to SQLite
If you need to go back to SQLite:
1. Remove or comment out Supabase variables in `.env`
2. Restore from backup: `cp ./data/app.db.backup ./data/app.db`
3. Restart the application

## Support

If you encounter any issues:
1. Check the console output for error messages
2. Verify all environment variables are correctly set
3. Test the database connection manually
4. Check Supabase project status in the dashboard
