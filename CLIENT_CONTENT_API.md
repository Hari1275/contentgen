# Client-Based Content API Documentation

## Overview

These endpoints allow you to retrieve content based on client ID, perfect for implementing user-specific dashboards and content management in your SaaS frontend.

## 🔐 Authentication Context

These endpoints are designed for authenticated users who should only see their own content. In your frontend implementation, you'll:

1. **Get Client ID from Authentication**: After user login, store their client ID
2. **Use Client ID in API Calls**: Pass the client ID to these endpoints
3. **Secure Access**: Ensure users can only access their own client ID

## 📋 Available Endpoints

### 1. Get Client Content

**Endpoint:** `GET /api/v1/content/client/{client_id}`

**Description:** Retrieve all content for a specific client with optional filtering and pagination.

**Parameters:**
- `client_id` (path): The ID of the client
- `skip` (query, optional): Number of records to skip (default: 0)
- `limit` (query, optional): Maximum records to return (default: 100)
- `status` (query, optional): Filter by content status (`draft`, `review`, `published`)
- `content_type` (query, optional): Filter by content type (`blog`, `social`, `email`, etc.)

**Example Requests:**
```bash
# Get all content for client
GET /api/v1/content/client/1

# Get content with pagination
GET /api/v1/content/client/1?skip=0&limit=10

# Get only published blog posts
GET /api/v1/content/client/1?status=published&content_type=blog

# Get recent content (first 5)
GET /api/v1/content/client/1?limit=5
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Natural Remedies for Better Sleep",
    "body": "Content body here...",
    "content_type": "blog",
    "status": "published",
    "topic": "Sleep Health",
    "keywords": "sleep, natural, remedies",
    "word_count": 500,
    "visual_suggestions": "Images of chamomile tea...",
    "client_id": 1,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T11:00:00"
  }
]
```

### 2. Get Client Content Statistics

**Endpoint:** `GET /api/v1/content/client/{client_id}/stats`

**Description:** Get comprehensive statistics about a client's content.

**Parameters:**
- `client_id` (path): The ID of the client

**Example Request:**
```bash
GET /api/v1/content/client/1/stats
```

**Response:**
```json
{
  "client_id": 1,
  "total_content": 25,
  "status_breakdown": {
    "draft": 5,
    "review": 8,
    "published": 12
  },
  "type_breakdown": {
    "blog": 15,
    "social": 7,
    "email": 3
  },
  "recent_content_7_days": 4
}
```

## 🎯 Frontend Integration Examples

### React/JavaScript Example

```javascript
// API service for client content
class ContentAPI {
  constructor(baseURL, clientId) {
    this.baseURL = baseURL;
    this.clientId = clientId;
  }

  // Get all content for the logged-in user
  async getMyContent(page = 1, limit = 10, filters = {}) {
    const skip = (page - 1) * limit;
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      ...filters
    });

    const response = await fetch(
      `${this.baseURL}/content/client/${this.clientId}?${params}`
    );
    return response.json();
  }

  // Get content statistics for dashboard
  async getMyStats() {
    const response = await fetch(
      `${this.baseURL}/content/client/${this.clientId}/stats`
    );
    return response.json();
  }

  // Get recent content for dashboard
  async getRecentContent(limit = 5) {
    return this.getMyContent(1, limit);
  }

  // Get content by status
  async getContentByStatus(status) {
    return this.getMyContent(1, 100, { status });
  }
}

// Usage in React component
const Dashboard = () => {
  const [content, setContent] = useState([]);
  const [stats, setStats] = useState(null);
  const clientId = useAuth().user.clientId; // Get from auth context
  
  const contentAPI = new ContentAPI('/api/v1', clientId);

  useEffect(() => {
    // Load dashboard data
    Promise.all([
      contentAPI.getRecentContent(5),
      contentAPI.getMyStats()
    ]).then(([recentContent, contentStats]) => {
      setContent(recentContent);
      setStats(contentStats);
    });
  }, []);

  return (
    <div>
      <h1>My Content Dashboard</h1>
      <div className="stats">
        <div>Total Content: {stats?.total_content}</div>
        <div>Recent (7 days): {stats?.recent_content_7_days}</div>
      </div>
      <div className="content-list">
        {content.map(item => (
          <ContentCard key={item.id} content={item} />
        ))}
      </div>
    </div>
  );
};
```

### Python/Requests Example

```python
import requests

class ContentClient:
    def __init__(self, base_url, client_id):
        self.base_url = base_url
        self.client_id = client_id
    
    def get_my_content(self, page=1, limit=10, **filters):
        """Get content for the authenticated client"""
        skip = (page - 1) * limit
        params = {'skip': skip, 'limit': limit, **filters}
        
        response = requests.get(
            f"{self.base_url}/content/client/{self.client_id}",
            params=params
        )
        return response.json()
    
    def get_my_stats(self):
        """Get content statistics"""
        response = requests.get(
            f"{self.base_url}/content/client/{self.client_id}/stats"
        )
        return response.json()

# Usage
client = ContentClient("http://localhost:8000/api/v1", client_id=1)

# Get recent content
recent_content = client.get_my_content(limit=5)

# Get published blog posts
blog_posts = client.get_my_content(
    content_type="blog", 
    status="published"
)

# Get statistics for dashboard
stats = client.get_my_stats()
print(f"Total content: {stats['total_content']}")
```

## 🔒 Security Considerations

### For Production Implementation:

1. **Authentication Required**: Always verify the user is authenticated
2. **Authorization Check**: Ensure the user can only access their own client_id
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Input Validation**: Validate all query parameters

### Example Security Middleware:

```python
# Add to your FastAPI route
from fastapi import Depends, HTTPException
from app.auth import get_current_user

@router.get("/client/{client_id}", response_model=List[ContentSchema])
def get_content_by_client(
    client_id: int,
    current_user = Depends(get_current_user),  # Add authentication
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify user can access this client
    if current_user.client_id != client_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Cannot access other client's content"
        )
    
    # Rest of the endpoint logic...
```

## 📊 Use Cases

### Dashboard Implementation
- Show recent content created
- Display content statistics
- Show content by status (drafts, published, etc.)

### Content Management
- List all user's content with pagination
- Filter content by type or status
- Search through user's content

### Analytics
- Track content creation trends
- Monitor content performance
- Generate usage reports

## 🚀 Testing

Use the provided test script to verify the endpoints:

```bash
python test_client_content_endpoints.py
```

This will test all the new endpoints and show example usage patterns.
