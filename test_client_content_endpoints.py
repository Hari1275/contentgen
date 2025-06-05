#!/usr/bin/env python3
"""
Test script for the new client-based content endpoints
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
CLIENT_ID = 1  # Replace with your actual client ID

def test_get_client_content():
    """Test getting all content for a specific client"""
    print("🔍 Testing: Get content by client ID")
    
    url = f"{BASE_URL}/content/client/{CLIENT_ID}"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content_list = response.json()
            print(f"✅ Found {len(content_list)} content items for client {CLIENT_ID}")
            
            for content in content_list[:3]:  # Show first 3 items
                print(f"  - ID: {content['id']}, Title: {content['title'][:50]}...")
                print(f"    Type: {content['content_type']}, Status: {content['status']}")
                print(f"    Created: {content['created_at']}")
                print()
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_get_client_content_with_filters():
    """Test getting client content with filters"""
    print("🔍 Testing: Get content by client ID with filters")
    
    # Test with status filter
    url = f"{BASE_URL}/content/client/{CLIENT_ID}?status=review&limit=5"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content_list = response.json()
            print(f"✅ Found {len(content_list)} content items with status 'review'")
            
            for content in content_list:
                print(f"  - {content['title'][:40]}... (Status: {content['status']})")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_get_client_stats():
    """Test getting content statistics for a client"""
    print("🔍 Testing: Get client content statistics")
    
    url = f"{BASE_URL}/content/client/{CLIENT_ID}/stats"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Content statistics for client {CLIENT_ID}:")
            print(f"  📊 Total content: {stats['total_content']}")
            print(f"  📈 Recent content (7 days): {stats['recent_content_7_days']}")
            
            print("  📋 Status breakdown:")
            for status, count in stats['status_breakdown'].items():
                if count > 0:
                    print(f"    - {status}: {count}")
            
            print("  📝 Type breakdown:")
            for content_type, count in stats['type_breakdown'].items():
                if count > 0:
                    print(f"    - {content_type}: {count}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_pagination():
    """Test pagination with client content"""
    print("🔍 Testing: Pagination with client content")
    
    # Get first page
    url = f"{BASE_URL}/content/client/{CLIENT_ID}?skip=0&limit=2"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content_list = response.json()
            print(f"✅ Page 1: Found {len(content_list)} content items")
            
            # Get second page
            url = f"{BASE_URL}/content/client/{CLIENT_ID}?skip=2&limit=2"
            response = requests.get(url)
            
            if response.status_code == 200:
                content_list_page2 = response.json()
                print(f"✅ Page 2: Found {len(content_list_page2)} content items")
                
                # Check if pages are different
                if content_list and content_list_page2:
                    if content_list[0]['id'] != content_list_page2[0]['id']:
                        print("✅ Pagination working correctly - different content on each page")
                    else:
                        print("⚠️  Pagination might not be working - same content on both pages")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    """Run all tests"""
    print("🚀 Testing Client-Based Content Endpoints\n")
    print(f"Using Client ID: {CLIENT_ID}")
    print(f"API Base URL: {BASE_URL}\n")
    
    # Test basic functionality
    test_get_client_content()
    print("-" * 50)
    
    # Test with filters
    test_get_client_content_with_filters()
    print("-" * 50)
    
    # Test statistics
    test_get_client_stats()
    print("-" * 50)
    
    # Test pagination
    test_pagination()
    print("-" * 50)
    
    print("\n🎉 All tests completed!")
    print("\n📚 Available Endpoints:")
    print(f"  GET {BASE_URL}/content/client/{{client_id}} - Get all content for a client")
    print(f"  GET {BASE_URL}/content/client/{{client_id}}?status=review - Filter by status")
    print(f"  GET {BASE_URL}/content/client/{{client_id}}?content_type=blog - Filter by type")
    print(f"  GET {BASE_URL}/content/client/{{client_id}}?skip=0&limit=10 - Pagination")
    print(f"  GET {BASE_URL}/content/client/{{client_id}}/stats - Get statistics")

if __name__ == "__main__":
    main()
