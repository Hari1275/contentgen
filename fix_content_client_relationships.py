#!/usr/bin/env python3
"""
Script to fix content-client relationships after authentication migration
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def fix_content_relationships():
    """Fix content-client relationships and assign orphaned content to current user"""
    
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
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as db:
            print("🔗 Connected to Supabase database")
            
            # Step 1: Check current state
            print("\n📊 Current Database State:")
            
            # Check clients
            clients_result = db.execute(text("SELECT id, name, user_id FROM clients ORDER BY id"))
            clients = clients_result.fetchall()
            print(f"📋 Found {len(clients)} clients:")
            
            valid_clients = []
            for client in clients:
                user_id = client[2] if len(client) > 2 else None
                print(f"  - Client {client[0]}: {client[1]}, user_id: {user_id}")
                if user_id:
                    valid_clients.append(client[0])
            
            # Check content (table name is 'contents' plural)
            content_result = db.execute(text("SELECT id, title, client_id FROM contents ORDER BY id"))
            content_items = content_result.fetchall()
            print(f"📋 Found {len(content_items)} content items:")
            
            orphaned_content = []
            valid_content = []
            
            for content in content_items:
                content_id, title, client_id = content[0], content[1], content[2]
                if client_id in valid_clients:
                    valid_content.append(content_id)
                    print(f"  ✅ Content {content_id}: '{title[:50]}...' → Client {client_id} (VALID)")
                else:
                    orphaned_content.append(content_id)
                    print(f"  ❌ Content {content_id}: '{title[:50]}...' → Client {client_id} (ORPHANED)")
            
            print(f"\n📊 Summary:")
            print(f"  - Valid clients with user_id: {len(valid_clients)}")
            print(f"  - Valid content: {len(valid_content)}")
            print(f"  - Orphaned content: {len(orphaned_content)}")
            
            if len(orphaned_content) == 0:
                print("✅ No orphaned content found. Database is clean!")
                return True
            
            # Step 2: Handle orphaned content
            print(f"\n🔧 Fixing {len(orphaned_content)} orphaned content items...")
            
            # Option 1: Create a default client for the current user
            current_user_id = "f32a2497-9a2e-46ff-929e-8a7f85d57b61"  # Your user ID from the logs
            
            # Check if user already has a client
            user_client_result = db.execute(text("""
                SELECT id, name FROM clients WHERE user_id = :user_id LIMIT 1
            """), {"user_id": current_user_id})
            user_client = user_client_result.fetchone()
            
            if user_client:
                default_client_id = user_client[0]
                print(f"✅ Using existing client {default_client_id}: {user_client[1]}")
            else:
                # Create a default client for the user
                print(f"📝 Creating default client for user {current_user_id}...")
                
                insert_result = db.execute(text("""
                    INSERT INTO clients (name, industry, brand_voice, target_audience, user_id, created_at, updated_at)
                    VALUES (:name, :industry, :brand_voice, :target_audience, :user_id, NOW(), NOW())
                    RETURNING id
                """), {
                    "name": "Default Client (Migrated Content)",
                    "industry": "Health & Wellness",
                    "brand_voice": "Friendly and professional",
                    "target_audience": "Health-conscious individuals",
                    "user_id": current_user_id
                })
                
                default_client_id = insert_result.fetchone()[0]
                print(f"✅ Created default client {default_client_id}")
            
            # Step 3: Move orphaned content to the default client
            print(f"📝 Moving {len(orphaned_content)} orphaned content items to client {default_client_id}...")
            
            for content_id in orphaned_content:
                db.execute(text("""
                    UPDATE contents
                    SET client_id = :client_id, updated_at = NOW()
                    WHERE id = :content_id
                """), {
                    "client_id": default_client_id,
                    "content_id": content_id
                })
                print(f"  ✅ Moved content {content_id} to client {default_client_id}")
            
            # Commit all changes
            db.commit()
            
            print(f"\n🎉 Successfully fixed all orphaned content!")
            print(f"📋 All content is now accessible through client {default_client_id}")
            print(f"👤 Client belongs to user: {current_user_id}")
            
            return True
            
    except Exception as e:
        print(f"❌ Failed to fix content relationships: {e}")
        return False

def verify_fix():
    """Verify that the fix worked"""
    print("\n🔍 Verifying the fix...")
    
    # You can add verification logic here
    print("✅ Please test your frontend now!")
    print("📋 Try accessing content through your clients")

if __name__ == "__main__":
    print("🚀 Fixing Content-Client Relationships...")
    
    success = fix_content_relationships()
    
    if success:
        verify_fix()
        print("\n🎉 Fix completed!")
        print("\nNext steps:")
        print("1. Restart your FastAPI server")
        print("2. Test your frontend")
        print("3. Check that content is now accessible")
    else:
        print("\n❌ Fix failed.")
        print("Please check the errors above.")
