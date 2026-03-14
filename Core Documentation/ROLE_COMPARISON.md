# ShadowNet C2 - Complete Role Comparison

## 🔍 All 4 Roles Comparison

| Feature | Admin | Developer | Operator | Viewer |
|---------|:-----:|:---------:|:--------:|:------:|
| **Dashboard Access** | ✅ | ✅ | ✅ | ✅ |
| **View Agents** | ✅ | ✅ | ✅ | ✅ |
| **View Tasks** | ✅ | ✅ | ✅ | ✅ |
| **View Incidents** | ✅ | ✅ | ✅ | ✅ |
| **Execute Commands** | ✅ | ✅ | ✅ | ❌ |
| **Send Tasks to Agents** | ✅ | ✅ | ✅ | ❌ |
| **Developer Console** | ✅ | ✅ | ❌ | ❌ |
| **User Management** | ✅ | ❌ | ❌ | ❌ |
| **Database Management** | ✅ | ❌ | ❌ | ❌ |
| **Access Control Settings** | ✅ | ❌ | ❌ | ❌ |
| **System Information** | ✅ | ✅ | ❌ | ❌ |
| **Change Own Password** | ✅ | ✅ | ✅ | ✅ |

---

## 📊 Role by Role Breakdown

### 1️⃣ **ADMIN** - System Administrator
**Power Level:** ⭐⭐⭐⭐⭐ (5/5)

**Can Do:**
- ✅ Everything (full system control)
- ✅ Create/Delete users
- ✅ Clear database (events, tasks)
- ✅ Reset entire database
- ✅ Configure IP whitelist
- ✅ Access Developer Console
- ✅ Execute all C2 commands
- ✅ View all system metrics

**Cannot Do:**
- Nothing - has full access

**Use Case:** System owner, lead administrator, project manager

**Buttons Visible:**
- ✅ Change Password
- ✅ Developer
- ✅ Logout

---

### 2️⃣ **DEVELOPER** - Advanced User
**Power Level:** ⭐⭐⭐⭐ (4/5)

**Can Do:**
- ✅ Access Developer Console
- ✅ View system information
- ✅ Execute commands on agents
- ✅ View all C2 data
- ✅ Advanced features

**Cannot Do:**
- ❌ Create/Delete users
- ❌ Database management
- ❌ Access control settings
- ❌ Reset system

**Use Case:** Team developers, security researchers who need advanced tools but shouldn't manage system

**Buttons Visible:**
- ✅ Change Password
- ✅ Developer
- ✅ Logout

**Developer Console Shows:**
- ✅ Session Information
- ✅ System Information
- ❌ User Management (hidden)
- ❌ Database Management (hidden)
- ❌ Access Control (hidden)

---

### 3️⃣ **OPERATOR** - Standard C2 User
**Power Level:** ⭐⭐⭐ (3/5)

**Can Do:**
- ✅ Execute commands on agents
- ✅ Send tasks to agents
- ✅ View agents, tasks, incidents
- ✅ Monitor dashboard
- ✅ View command results

**Cannot Do:**
- ❌ Access Developer Console
- ❌ Manage users
- ❌ Manage database
- ❌ Configure system

**Use Case:** Red team operators, penetration testers, standard C2 users

**Buttons Visible:**
- ✅ Change Password
- ❌ Developer (hidden)
- ✅ Logout

---

### 4️⃣ **VIEWER** - Read-Only
**Power Level:** ⭐ (1/5)

**Can Do:**
- ✅ View dashboard
- ✅ View agents list
- ✅ View tasks (read-only)
- ✅ View incidents
- ✅ Monitor statistics

**Cannot Do:**
- ❌ Execute commands
- ❌ Send tasks
- ❌ Access Developer Console
- ❌ Manage anything
- ❌ Make any changes

**Use Case:** Monitoring users, management oversight, demo accounts, auditors

**Buttons Visible:**
- ✅ Change Password
- ❌ Developer (hidden)
- ✅ Logout

**Interface Changes:**
- Command execution disabled
- Execute buttons hidden/disabled

---

## 🆕 What's New in This System

### ✨ NEW: Multi-User Role System
- **4 distinct permission levels** instead of single admin user
- **Granular access control** for team environments
- **Secure delegation** - give team members only what they need

### 🔐 NEW: Developer Console
- **System Information** - View server stats, database size
- **User Management** (Admin only) - Create/delete users from web UI
- **Database Management** (Admin only) - Clear events, reset database
- **Access Control** (Admin only) - IP whitelist configuration

### 👥 NEW: User Management Features
- **Web-based user creation** - Create users directly from Developer Console
- **Role assignment** - Choose role when creating user
- **User deletion** - Remove users (except admin) with password confirmation
- **User listing** - See all users, their roles, and creation dates

### 🎨 NEW: Theme Enhancements
- **Modern dark theme** with coral accent (#d87757)
- **Professional UI** for 2026
- **Darker base colors** (#1a1a1a background)
- **Consistent styling** across all pages

### 🚀 NEW: Security Features
- **Password re-authentication** for sensitive operations
- **Role-based route protection** (@admin_required, @developer_required, @operator_required)
- **IP whitelist** access control (configurable by admin)
- **Protected admin account** (cannot be deleted)

### 📱 NEW: UI Improvements
- **Change Password** button accessible to all users from dashboard
- **Developer button** shows for admin + developer roles
- **Conditional UI** - sections appear/hide based on role
- **Better error messages** with toast notifications

---

## 🔄 Permission Flow

```
Admin (Full Control)
  └─ Can manage users
  └─ Can manage database
  └─ Can access Developer Console
      └─ Developer (Limited Control)
          └─ Can access Developer Console
          └─ Cannot manage users/database
              └─ Operator (Standard User)
                  └─ Can execute commands
                  └─ Cannot access Developer Console
                      └─ Viewer (Read-Only)
                          └─ Can only view
                          └─ Cannot execute anything
```

---

## 📋 Quick Reference

**Need to create users?** → Login as Admin → Developer Console → User Management

**Need advanced tools?** → Give user **Developer** role

**Standard C2 operator?** → Give user **Operator** role

**Monitoring only?** → Give user **Viewer** role

**Full system control?** → Give user **Admin** role (use sparingly!)

---

## 🔧 Server Changes Summary

### New Decorators:
- `@admin_required` - Admin only
- `@developer_required` - Admin + Developer
- `@operator_required` - Admin + Developer + Operator
- `@login_required` - Any authenticated user

### New API Endpoints:
- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `DELETE /api/admin/users/<username>` - Delete user
- `GET /api/admin/system-info` - System information

### Protected Routes:
- `/developer` - Requires Admin or Developer role
- `/settings` - Requires Admin role
- `/api/task` - Requires Operator+ role (can execute commands)
- `/api/admin/*` - Requires Admin role

---

## 🎯 Best Practices

1. **Limit Admin accounts** - Only 1-2 admins per system
2. **Use Developer for team leads** - They get tools but can't break things
3. **Most users should be Operators** - Standard C2 operations
4. **Use Viewer generously** - For monitoring, demos, auditing
5. **Change default passwords** - Immediately after user creation
6. **Review users regularly** - Delete inactive accounts

---

## ⚡ Quick Commands

**Create users from command line:**
```bash
cd e:\shadowNet\server
python create_users.py  # Creates default users
```

**Check all users:**
```bash
python test_users.py
```

**Manually check database:**
```sql
SELECT username, role FROM users;
```
