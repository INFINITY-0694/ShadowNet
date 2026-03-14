#!/usr/bin/env python3
"""
User Management Script for ShadowNet C2
Create and manage users with different roles and access levels
"""

import bcrypt
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import database

# Role Definitions:
# - admin: Full access to all features, database management, settings
# - developer: Access to developer console, command library, advanced features
# - operator: Standard C2 operator, can execute commands and view agents
# - viewer: Read-only access, can view but not execute commands
# - demo: Limited demo access with restricted permissions

def create_user(username, password, role='operator'):
    """Create a new user with specified role"""
    try:
        # Hash the password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        # Create user in database
        success = database.create_user(username, password_hash, role)
        
        if success:
            print(f"✓ User '{username}' created successfully with role: {role}")
            return True
        else:
            print(f"⚠ User '{username}' already exists (skipping)")
            return False
    except Exception as e:
        print(f"✗ Error creating user '{username}': {e}")
        return False

def list_users():
    """List all existing users"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, role, created_at FROM users ORDER BY created_at')
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            print("No users found in database")
            return
        
        print("\n" + "="*60)
        print(f"{'Username':<20} {'Role':<15} {'Created At':<25}")
        print("="*60)
        for user in users:
            print(f"{user['username']:<20} {user['role']:<15} {user['created_at']:<25}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"Error listing users: {e}")

def delete_user(username):
    """Delete a user (except admin)"""
    if username == 'admin':
        print("✗ Cannot delete admin user!")
        return False
    
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        count = cursor.rowcount
        conn.close()
        
        if count > 0:
            print(f"✓ User '{username}' deleted successfully")
            return True
        else:
            print(f"✗ User '{username}' not found")
            return False
    except Exception as e:
        print(f"✗ Error deleting user: {e}")
        return False

def main():
    print("="*60)
    print("ShadowNet C2 - User Management")
    print("="*60)
    
    # Initialize database if needed
    database.init_database()
    
    # Define users to create
    users_to_create = [
        {
            "username": "admin",
            "password": "admin123",  # Change this!
            "role": "admin"
        },
        {
            "username": "developer",
            "password": "dev123",  # Change this!
            "role": "developer"
        },
        {
            "username": "divy soni",
            "password": "divy123",  # Change this!
            "role": "operator"
        },
        {
            "username": "demo",
            "password": "demo",
            "role": "viewer"
        }
    ]
    
    print("\n[*] Creating users...")
    print("-"*60)
    
    for user_data in users_to_create:
        create_user(
            username=user_data["username"],
            password=user_data["password"],
            role=user_data["role"]
        )
    
    print("\n[*] Current users in database:")
    list_users()
    
    print("\n[!] SECURITY WARNING:")
    print("    Default passwords are being used!")
    print("    Please change passwords after first login using 'Change Password' button")
    print("\n[!] Role Permissions:")
    print("    - admin: Full access (settings, developer console, database management)")
    print("    - developer: Developer console, advanced features")
    print("    - operator: Standard C2 operations (execute commands, view agents)")
    print("    - viewer: Read-only access (view only, cannot execute)")
    print("="*60)

if __name__ == "__main__":
    main()
