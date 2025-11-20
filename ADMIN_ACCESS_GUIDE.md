# Admin Module Access Guide

This guide explains how to access and use the admin module in DetectifAI.

## Quick Access

### 1. **Admin Sign-In Page**
Navigate to: **`http://localhost:3000/admin/signin`**

Or directly access:
- Admin Dashboard: `http://localhost:3000/admin/dashboard`
- User Management: `http://localhost:3000/admin/users`
- Pricing Management: `http://localhost:3000/admin/pricing`

## Prerequisites

### Step 1: Create an Admin User

You need to have a user account with `role: "admin"` in your MongoDB database. Here are two ways to create one:

#### Option A: Using MongoDB Directly

Connect to your MongoDB database and insert an admin user:

```javascript
// In MongoDB shell or MongoDB Compass
db.users.insertOne({
  "user_id": "admin_" + new Date().getTime(),
  "username": "admin",
  "email": "admin@detectifai.com",
  "password_hash": "$2a$10$...", // Use bcrypt to hash your password
  "role": "admin",
  "is_active": true,
  "profile_data": {},
  "created_at": new Date(),
  "updated_at": new Date(),
  "last_login": null
})
```

#### Option B: Using Python Script

Create a file `create_admin.py` in the `backend/DetectifAI_db/` directory:

```python
from pymongo import MongoClient
from uuid import uuid4
from datetime import datetime, timezone
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/detectifai"))
db = client.get_default_database()
users = db.users

# Create admin user
admin_email = "admin@detectifai.com"
admin_password = "admin123"  # Change this!

# Check if admin already exists
if users.find_one({"email": admin_email}):
    print(f"Admin user {admin_email} already exists")
else:
    # Hash password
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin_user = {
        "user_id": str(uuid4()),
        "username": "admin",
        "email": admin_email,
        "password_hash": password_hash,
        "password": admin_password,  # For Flask backend compatibility
        "role": "admin",
        "is_active": True,
        "profile_data": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None
    }
    
    users.insert_one(admin_user)
    print(f"✅ Admin user created: {admin_email} / {admin_password}")
    print("⚠️  Please change the password after first login!")

client.close()
```

Run it:
```bash
cd backend/DetectifAI_db
python create_admin.py
```

## Accessing the Admin Module

### Step 2: Start the Application

1. **Start the Backend (Flask)**:
   ```bash
   cd backend/DetectifAI_db
   python app_integrated.py
   ```
   Backend should run on `http://localhost:5000`

2. **Start the Frontend (Next.js)**:
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend should run on `http://localhost:3000`

### Step 3: Login as Admin

1. Navigate to `http://localhost:3000/admin/signin`
2. Enter your admin credentials:
   - **Email**: `admin@detectifai.com` (or your admin email)
   - **Password**: The password you set when creating the admin user
3. Click "Log in"

### Step 4: Access Admin Features

After successful login, you'll be redirected to the admin dashboard. You can access:

- **Admin Dashboard** (`/admin/dashboard`): Overview and quick stats
- **User Management** (`/admin/users`): 
  - View all users
  - Create new users
  - Edit user information
  - Delete users
  - Search and filter users
- **Pricing Management** (`/admin/pricing`): Manage subscription plans

## Important Notes

### Authentication System

The admin module uses **dual authentication**:

1. **NextAuth (Frontend)**: Used for accessing admin pages in the frontend
   - Checks user role from MongoDB
   - Requires `role: "admin"` in the user document

2. **Flask Backend JWT (API)**: Used for admin API endpoints
   - Admin API endpoints (`/api/admin/users/*`) require a JWT token
   - Token must have `role: "admin"` in the payload
   - Token should be stored in localStorage as `auth_token`

### For Full API Functionality

To use the admin API endpoints (create, update, delete users), you also need to:

1. **Login through Flask backend** to get a JWT token:
   ```javascript
   const response = await fetch('http://localhost:5000/api/login', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ 
       email: 'admin@detectifai.com', 
       password: 'your_password' 
     })
   })
   const { token } = await response.json()
   localStorage.setItem('auth_token', token)
   ```

2. The frontend API utility (`frontend/lib/api.ts`) will automatically use this token for admin API calls.

### Troubleshooting

**Problem**: "Invalid admin credentials" error
- **Solution**: Make sure the user exists in MongoDB with `role: "admin"` and the password is correct

**Problem**: Can't access `/admin/users` page
- **Solution**: Check that your session has `role: "admin"`. Try logging out and logging back in.

**Problem**: API calls fail with 401/403 errors
- **Solution**: Make sure you've logged in through the Flask backend and stored the token in localStorage

**Problem**: Admin pages redirect to signin
- **Solution**: The middleware checks for admin role. Ensure your user document has `role: "admin"` (not `"administrator"` or any other value)

## Admin Routes

| Route | Description | Access Level |
|-------|-------------|--------------|
| `/admin/signin` | Admin login page | Public |
| `/admin/dashboard` | Admin dashboard | Admin only |
| `/admin/users` | User management | Admin only |
| `/admin/pricing` | Pricing management | Admin only |

## Security Notes

⚠️ **Important Security Considerations**:

1. **Change Default Passwords**: Always change default admin passwords after first login
2. **Use Strong Passwords**: Admin accounts should have strong, unique passwords
3. **Limit Admin Access**: Only grant admin role to trusted users
4. **Token Security**: JWT tokens should be stored securely and have expiration times
5. **HTTPS in Production**: Always use HTTPS in production environments

## Next Steps

After accessing the admin module, you can:

1. **Manage Users**: Create, edit, and delete user accounts
2. **Set User Roles**: Assign roles (admin, contributor, viewer, user) to users
3. **Activate/Deactivate Users**: Control user access with the `is_active` field
4. **Monitor Activity**: View user information and activity (when implemented)

---

For more information, see the main README or contact the development team.



