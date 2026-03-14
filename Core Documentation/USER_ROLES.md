# ShadowNet C2 - User Roles & Permissions

## Role Hierarchy

### 1. **Admin** (Highest Access)
- ✅ Full system access
- ✅ Access Developer Console
- ✅ Manage users (create/delete)
- ✅ Database management (clear events, reset DB)
- ✅ Access control settings
- ✅ Execute commands on agents
- ✅ View all data

### 2. **Developer**
- ✅ Access Developer Console
- ✅ Execute commands on agents
- ✅ View all data
- ✅ Advanced C2 features
- ❌ Cannot manage users
- ❌ Cannot manage database

### 3. **Operator** (Standard User)
- ✅ Execute commands on agents
- ✅ View agents, tasks, incidents
- ✅ Send commands to agents
- ❌ No Developer Console access
- ❌ Cannot manage users
- ❌ Cannot manage database

### 4. **Viewer** (Read-Only)
- ✅ View agents, tasks, incidents
- ✅ View dashboard statistics
- ❌ Cannot execute commands
- ❌ Cannot access settings
- ❌ Cannot manage anything

### 5. **Demo** (Limited Access)
- Similar to Viewer role
- Intended for demonstrations
- Read-only access

## Creating Users

### Option 1: Developer Console (Web UI)
1. Login as **admin**
2. Click **Developer** button
3. Go to **User Management** section
4. Fill in username, password, and select role
5. Click **Create User**

### Option 2: Python Script
```bash
cd e:\shadowNet\server
python create_users.py
```

**Note:** Stop the server before running the script to avoid database locks.

## Default Users (if created via script)

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| admin | admin123 | Admin | Full access to everything |
| developer | dev123 | Developer | Development and testing |
| divy soni | divy123 | Operator | Standard C2 operations |
| demo | demo | Viewer | Read-only demo account |

⚠️ **SECURITY WARNING:** Change all default passwords immediately after first login!

## Permissions Matrix

| Feature | Admin | Developer | Operator | Viewer |
|---------|-------|-----------|----------|--------|
| View Dashboard | ✅ | ✅ | ✅ | ✅ |
| View Agents | ✅ | ✅ | ✅ | ✅ |
| Execute Commands | ✅ | ✅ | ✅ | ❌ |
| View Incidents | ✅ | ✅ | ✅ | ✅ |
| Developer Console | ✅ | ✅ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ |
| Database Management | ✅ | ❌ | ❌ | ❌ |
| System Settings | ✅ | ❌ | ❌ | ❌ |
| Change Own Password | ✅ | ✅ | ✅ | ✅ |

## Implementation Details

### Server-Side Decorators
```python
@login_required          # Any authenticated user
@operator_required       # Operator, Developer, Admin
@developer_required      # Developer, Admin only
@admin_required          # Admin only
```

### Protected Routes
- `/developer` - Developer Console (admin + developer)
- `/settings` - System Settings (admin only)
- `/api/task` - Command execution (operator+)
- `/api/admin/*` - Admin APIs (admin only)

## Managing Users from CLI

### List All Users
```python
python
>>> import database
>>> conn = database.get_db_connection()
>>> cursor = conn.cursor()
>>> cursor.execute('SELECT username, role FROM users')
>>> print(cursor.fetchall())
```

### Change User Role
```python
>>> cursor.execute('UPDATE users SET role = ? WHERE username = ?', ('admin', 'username'))
>>> conn.commit()
```

## Security Best Practices

1. **Change default passwords** immediately
2. **Use strong passwords** (minimum 6 characters, recommend 12+)
3. **Limit admin accounts** - Only create admin users when necessary
4. **Review user access** regularly
5. **Use viewer role** for monitoring-only users
6. **Enable access control** for IP whitelisting (in Developer Console)

## Troubleshooting

### "Admin access required" error
- Check you're logged in as admin
- Verify role in database: `SELECT username, role FROM users`

### Cannot create users
- Ensure you're logged in as admin
- Check if username already exists
- Verify password meets minimum requirements

### Database locked error
- Stop the server before running create_users.py script
- Or use the web UI (Developer Console) instead
