# Supabase Authentication Integration Guide

## 🎯 Overview

Your FastAPI backend now integrates seamlessly with your existing React + Supabase frontend authentication system. This eliminates the duplicate authentication and creates a unified system.

## ✅ What We've Done

### **Removed:**
- ❌ FastAPI JWT authentication system
- ❌ Local User model and routes
- ❌ Duplicate authentication logic

### **Added:**
- ✅ Supabase JWT token verification
- ✅ Integration with your existing frontend auth
- ✅ User ID linking using Supabase user UUIDs

## 🔧 Setup Steps

### **1. Update Environment Variables**

Add to your `.env` file:
```env
# Existing Supabase config
SUPABASE_URL=https://zixrefecjrzqngadgjxj.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Add this new one for JWT verification
SUPABASE_JWT_SECRET=your_jwt_secret_here
```

**To get your JWT secret:**
1. Go to your Supabase dashboard
2. Settings → API
3. Copy the "JWT Secret" value

### **2. Run Database Migration**

```bash
python migrate_to_supabase_auth.py
```

This will:
- Update the database schema
- Remove local user table
- Prepare for Supabase user IDs

### **3. Update Dependencies**

Remove the auth-related dependencies from `requirements.txt`:
```bash
# Remove these lines:
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
email-validator==2.1.0
```

## 🔗 Frontend Integration

### **Your Existing React Auth (Keep As Is):**
```javascript
// Your existing AuthContext.tsx - NO CHANGES NEEDED
const { user, session } = useAuth();
```

### **Update API Calls to Include Supabase Token:**

```javascript
// In your API service
class APIService {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
  }

  async getAuthHeaders() {
    const { data: { session } } = await supabase.auth.getSession();
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session?.access_token}`
    };
  }

  // Create client (now user-aware)
  async createClient(clientData) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/clients/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(clientData)
    });
    return response.json();
  }

  // Get user's clients
  async getMyClients() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/clients/`, {
      method: 'GET',
      headers
    });
    return response.json();
  }

  // Get client content
  async getClientContent(clientId) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/content/client/${clientId}`, {
      method: 'GET',
      headers
    });
    return response.json();
  }
}
```

### **React Hook for API Calls:**

```javascript
// hooks/useAPI.js
import { useAuth } from '../contexts/AuthContext';

export const useAPI = () => {
  const { session } = useAuth();

  const apiCall = async (endpoint, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...(session?.access_token && {
        'Authorization': `Bearer ${session.access_token}`
      }),
      ...options.headers
    };

    const response = await fetch(`/api/v1${endpoint}`, {
      ...options,
      headers
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return response.json();
  };

  return { apiCall };
};

// Usage in components
const Dashboard = () => {
  const { apiCall } = useAPI();
  const [clients, setClients] = useState([]);

  useEffect(() => {
    const loadClients = async () => {
      try {
        const data = await apiCall('/clients/');
        setClients(data);
      } catch (error) {
        console.error('Failed to load clients:', error);
      }
    };

    loadClients();
  }, []);

  return (
    <div>
      {clients.map(client => (
        <ClientCard key={client.id} client={client} />
      ))}
    </div>
  );
};
```

## 🔒 How Authentication Works Now

### **Flow:**
1. **User logs in** via your React Supabase auth
2. **Supabase returns JWT token** in session
3. **Frontend sends token** in Authorization header
4. **FastAPI verifies token** with Supabase JWT secret
5. **User ID extracted** from token for data filtering

### **Security:**
- ✅ Users only see their own clients
- ✅ Users only see content from their clients
- ✅ All routes are protected
- ✅ JWT tokens are verified server-side

## 📊 API Endpoints (Updated)

All endpoints now require Supabase JWT authentication:

```bash
# Client Management
GET    /api/v1/clients/           # Get user's clients
POST   /api/v1/clients/           # Create client for user
GET    /api/v1/clients/{id}       # Get user's specific client
PUT    /api/v1/clients/{id}       # Update user's client
DELETE /api/v1/clients/{id}       # Delete user's client

# Content Management
GET    /api/v1/content/client/{id}       # Get client's content
GET    /api/v1/content/client/{id}/stats # Get client's content stats

# All require: Authorization: Bearer {supabase_jwt_token}
```

## 🧪 Testing the Integration

### **1. Test with curl:**
```bash
# Get your JWT token from browser dev tools or Supabase
TOKEN="your_supabase_jwt_token"

# Test getting clients
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/clients/

# Test creating client
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Client","industry":"Health"}' \
     http://localhost:8000/api/v1/clients/
```

### **2. Test in React DevTools:**
```javascript
// In browser console
const { data: { session } } = await supabase.auth.getSession();
console.log('JWT Token:', session.access_token);

// Test API call
fetch('/api/v1/clients/', {
  headers: {
    'Authorization': `Bearer ${session.access_token}`
  }
}).then(r => r.json()).then(console.log);
```

## 🚨 Important Notes

### **For Development:**
If you don't have the JWT secret yet, you can temporarily use the development auth in `supabase_auth.py`:
```python
# Change this line in your routes temporarily:
current_user: SupabaseUser = Depends(get_current_user_dev)  # Development only
```

### **For Production:**
- ✅ Always use real JWT verification
- ✅ Set proper CORS origins
- ✅ Use HTTPS for all requests
- ✅ Validate JWT secret is set

## 🎉 Benefits

### **Single Source of Truth:**
- ✅ Supabase handles all user management
- ✅ No duplicate authentication systems
- ✅ Consistent user experience

### **Better Security:**
- ✅ JWT tokens verified server-side
- ✅ User data isolation
- ✅ No password management in FastAPI

### **Easier Maintenance:**
- ✅ One authentication system to maintain
- ✅ Leverage Supabase's built-in features
- ✅ Real-time auth state changes

Your authentication system is now fully integrated and ready for production! 🚀
