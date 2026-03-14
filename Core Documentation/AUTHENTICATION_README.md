# ShadowNet Authentication System

## 🔐 Features Added

### 1. **User Authentication**
- Secure login system with session management
- Password hashing (SHA-256)
- Role-based access control (admin/operator)
- Session timeout and security

### 2. **Login Page**
- Modern, professional design
- Default admin credentials shown
- Error handling and feedback
- Auto-focus and keyboard shortcuts

### 3. **Session Management**
- Flask session-based authentication
- Automatic redirect to login if not authenticated
- Logout functionality
- Session data stored securely

### 4. **Protected Routes**
- All dashboard routes require login
- Beacon endpoint (for agents) has no auth requirement
- Admin-only routes for future user management

## 🚀 Quick Start

### Default Login Credentials
```
Username: admin
Password: admin123
```

**⚠️ IMPORTANT: Change the default password immediately after first login!**

### Files Updated

1. **server.py** - Added authentication system
   - Login/logout routes
   - Session management
   - `@login_required` decorator
   - `@admin_required` decorator (for future admin features)

2. **database.py** - Already has user functions
   - `create_user()`
   - `get_user()`
   - `verify_user()`

3. **login.html** - New login page
   - Clean, modern UI
   - Error handling
   - Responsive design

4. **dashboard.html** - Updated
   - Shows logged-in username
   - Logout button in header
   - Session-aware

## 📋 How It Works

### Login Flow
1. User visits `http://localhost:8080/`
2. If not logged in → Redirected to `/login`
3. Enter credentials → POST to `/login`
4. Server verifies password hash
5. Creates session with username and role
6. Redirects to dashboard

### Session Management
```python
session['username'] = 'admin'
session['role'] = 'admin'
session['login_time'] = '2024-02-24T10:30:00'
```

### Protected Routes
All routes except `/login` and `/beacon` require authentication:
```python
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session['username'])
```

## 🔑 Password Management

### Current Implementation
- Passwords are hashed using SHA-256
- Stored in database as hex digest
- Never transmitted or stored in plain text

### Changing Admin Password (Console)
```python
import hashlib
import database

new_password = "your_new_secure_password"
password_hash = hashlib.sha256(new_password.encode()).hexdigest()

# Update in database (you'll need to add this function)
conn = database.get_db_connection()
cursor = conn.cursor()
cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', 
               (password_hash, 'admin'))
conn.commit()
conn.close()
```

## 👥 User Roles

### Admin Role
- Full system access
- Can create/manage users (future feature)
- Access to all routes

### Operator Role
- Dashboard access
- Can execute commands
- View agents and incidents
- Cannot manage users

## 🛡️ Security Features

### Current
✅ Password hashing (SHA-256)
✅ Session-based authentication
✅ Login required for all dashboard routes
✅ Secure session cookies
✅ Role-based access control structure

### Recommendations for Production
⚠️ Use bcrypt or argon2 instead of SHA-256
⚠️ Implement rate limiting on login endpoint
⚠️ Add CSRF protection
⚠️ Use HTTPS only
⚠️ Implement password complexity requirements
⚠️ Add account lockout after failed attempts
⚠️ Implement session expiry
⚠️ Add audit logging for authentication events

## 📦 Installation

1. Replace your existing files:
   - `server.py`
   - `dashboard.html`
   - Add `login.html` to templates folder

2. Restart your server:
   ```bash
   python server.py
   ```

3. Visit `http://localhost:8080/`

4. Login with default credentials

5. **CHANGE THE DEFAULT PASSWORD!**

## 🔧 Configuration

### Session Secret Key
Located in `server.py`:
```python
SECRET_KEY = b"01234567890123456789012345678901"
app.secret_key = SECRET_KEY
```

⚠️ **Change this to a random 32-byte key for production!**

### Session Timeout
Add to `server.py` if needed:
```python
from datetime import timedelta
app.permanent_session_lifetime = timedelta(hours=2)
```

## 🧪 Testing

### Test Login
1. Go to `http://localhost:8080/login`
2. Enter: admin / admin123
3. Should redirect to dashboard

### Test Protected Routes
1. Logout
2. Try accessing `http://localhost:8080/`
3. Should redirect back to login

### Test Agent Beacon (No Auth)
The `/beacon` endpoint should work without authentication (for agents to connect).

## 📝 Future Enhancements

### User Management Page
- Create new users
- Edit existing users
- Delete users
- Change passwords
- View login history

### Password Reset
- Forgot password functionality
- Email verification
- Temporary reset tokens

### Multi-Factor Authentication
- TOTP (Google Authenticator)
- SMS codes
- Backup codes

### Audit Logging
- Track all login attempts
- Log command executions
- User activity monitoring

## ❓ Troubleshooting

### "Invalid credentials" error
- Check username/password
- Verify database has admin user
- Check console for error messages

### Redirect loop
- Clear browser cookies
- Check session secret key is set
- Verify database is initialized

### Session not persisting
- Check `app.secret_key` is set
- Verify Flask session configuration
- Check browser cookie settings

## 🎯 Quick Reference

### Login Endpoint
```
POST /login
Body: {"username": "admin", "password": "admin123"}
Response: {"success": true, "username": "admin", "role": "admin"}
```

### Logout Endpoint
```
POST /logout
Response: {"success": true}
```

### Check Session
```
GET /api/session
Response: {"logged_in": true, "username": "admin", "role": "admin"}
```

## 📞 Support

If you encounter issues:
1. Check server console for error messages
2. Verify database is initialized
3. Check browser developer console
4. Ensure all files are in correct locations

---

**Remember: Security is critical! Change default passwords and implement additional security measures for production use.**