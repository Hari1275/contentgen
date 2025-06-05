#!/usr/bin/env python3
"""
Migration script to integrate with Supabase authentication
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def migrate_to_supabase_auth():
    """Update database to work with Supabase authentication"""
    
    # Load environment variables
    load_dotenv()
    
    # Check Supabase configuration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    
    if not supabase_url or not supabase_key or not db_password:
        print("ERROR: Please set up your Supabase configuration in .env file")
        return False
    
    # Build Supabase connection URL
    project_id = supabase_url.replace("https://", "").replace(".supabase.co", "")
    database_url = f"postgresql://postgres:{db_password}@db.{project_id}.supabase.co:5432/postgres"
    
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        
        with engine.connect() as connection:
            print("🔗 Connected to Supabase database")
            
            # Start a transaction
            trans = connection.begin()
            
            try:
                # Step 1: Check if we have existing clients
                result = connection.execute(text("SELECT COUNT(*) FROM clients"))
                client_count = result.fetchone()[0]
                print(f"📊 Found {client_count} existing clients")
                
                # Step 2: Drop the old foreign key constraint if it exists
                print("📝 Removing old foreign key constraint...")
                try:
                    connection.execute(text("""
                        ALTER TABLE clients 
                        DROP CONSTRAINT IF EXISTS fk_clients_user_id
                    """))
                    print("✅ Old foreign key constraint removed")
                except Exception as e:
                    print(f"ℹ️  No old constraint to remove: {e}")
                
                # Step 3: Update user_id column to store Supabase UUID
                print("📝 Updating user_id column to support Supabase UUIDs...")
                
                # First, add a temporary column
                connection.execute(text("""
                    ALTER TABLE clients 
                    ADD COLUMN IF NOT EXISTS user_id_new VARCHAR(36)
                """))
                
                # If we have existing clients, assign them a default Supabase user ID
                if client_count > 0:
                    default_user_id = "00000000-0000-0000-0000-000000000000"  # Placeholder
                    connection.execute(text("""
                        UPDATE clients 
                        SET user_id_new = :user_id 
                        WHERE user_id_new IS NULL
                    """), {"user_id": default_user_id})
                    print(f"✅ Assigned default user ID to {client_count} existing clients")
                    print(f"⚠️  IMPORTANT: Update these clients with real Supabase user IDs!")
                
                # Drop the old user_id column
                connection.execute(text("ALTER TABLE clients DROP COLUMN IF EXISTS user_id"))
                
                # Rename the new column
                connection.execute(text("""
                    ALTER TABLE clients 
                    RENAME COLUMN user_id_new TO user_id
                """))
                
                # Make it NOT NULL
                connection.execute(text("""
                    ALTER TABLE clients 
                    ALTER COLUMN user_id SET NOT NULL
                """))
                
                print("✅ user_id column updated to support Supabase UUIDs")
                
                # Step 4: Create index for better performance
                print("📝 Creating indexes...")
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id)
                """))
                print("✅ Indexes created")
                
                # Step 5: Drop users table if it exists (we use Supabase's built-in users)
                print("📝 Removing local users table (using Supabase users instead)...")
                connection.execute(text("DROP TABLE IF EXISTS users CASCADE"))
                print("✅ Local users table removed")
                
                # Commit the transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
                print("\n🎉 Supabase authentication integration is now active!")
                print("\n📋 Next Steps:")
                print("1. Update your .env file with SUPABASE_JWT_SECRET")
                print("2. In your React frontend, when creating clients, use the Supabase user ID")
                print("3. Pass Supabase JWT tokens in API requests")
                
                if client_count > 0:
                    print(f"\n⚠️  IMPORTANT: You have {client_count} existing clients with placeholder user IDs")
                    print("   You'll need to update them with real Supabase user IDs")
                
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                print(f"❌ Migration failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False

def show_integration_guide():
    """Show how to integrate with React frontend"""
    print("\n📚 Frontend Integration Guide:")
    print("\n1. Update your React client creation to include user ID:")
    print("""
    // In your React component
    const { user } = useAuth(); // Your Supabase auth context
    
    const createClient = async (clientData) => {
      const response = await fetch('/api/v1/clients/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}` // Supabase JWT
        },
        body: JSON.stringify({
          ...clientData,
          // user_id will be automatically set from JWT token
        })
      });
    };
    """)
    
    print("\n2. Update your API calls to include Supabase JWT:")
    print("""
    // Get Supabase session token
    const { data: { session } } = await supabase.auth.getSession();
    
    // Use in API calls
    const headers = {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    };
    """)
    
    print("\n3. Add SUPABASE_JWT_SECRET to your .env file:")
    print("   You can find this in your Supabase dashboard under Settings > API")

if __name__ == "__main__":
    print("🚀 Migrating to Supabase Authentication Integration...")
    
    success = migrate_to_supabase_auth()
    
    if success:
        print("\n🎉 Migration completed!")
        show_integration_guide()
    else:
        print("\n❌ Migration failed.")
        print("Please check the errors above.")
