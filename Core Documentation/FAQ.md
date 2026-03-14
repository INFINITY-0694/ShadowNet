# Frequently Asked Questions (FAQ)

Common questions and answers about ShadowNet C2 Framework.

---

## Table of Contents

1. [General Questions](#general-questions)
2. [Installation & Setup](#installation--setup)
3. [Agent Questions](#agent-questions)
4. [Server Questions](#server-questions)
5. [Security & Legal](#security--legal)
6. [Troubleshooting](#troubleshooting)
7. [Features & Capabilities](#features--capabilities)
8. [Contributing](#contributing)

---

## General Questions

### What is ShadowNet C2?

ShadowNet is a Command and Control (C2) framework designed for security professionals to conduct authorized penetration testing and red team operations. It consists of a Python Flask server and Go-based agents that communicate via encrypted channels.

### Who should use this tool?

- Security researchers
- Penetration testers with proper authorization
- Red team operators in controlled environments
- Cybersecurity educators and students
- IT professionals conducting authorized security assessments

### Is this tool legal?

Yes, when used for authorized purposes only. Using this tool on systems you don't own or have explicit permission to test is **illegal** in most jurisdictions. Always obtain written authorization before conducting any security testing.

### Is this malware?

No. ShadowNet is a legitimate security testing tool. However, it uses techniques similar to malware (command execution, persistence, etc.) for educational and authorized testing purposes. It should only be used in controlled, authorized environments.

### What makes ShadowNet different from other C2 frameworks?

- **Modern, professional UI** - Clean dashboard instead of command-line only
- **Easy setup** - Quick installation with minimal dependencies
- **Cross-platform** - Works on Windows, Linux, and macOS
- **Educational focus** - Well-documented with clear code structure
- **Incident detection** - Built-in security event analysis
- **Encrypted communications** - AES-256-GCM encryption by default

---

## Installation & Setup

### What are the system requirements?

**Server:**
- Python 3.8 or higher
- 512MB RAM minimum (1GB recommended)
- 500MB free disk space
- Linux, Windows, or macOS

**Agent:**
- Go 1.19 or higher (for building)
- 50MB free disk space
- Target platform: Windows, Linux, or macOS

### Do I need root/admin privileges?

**Server:** No, can run as regular user on ports above 1024 (default: 8080)
**Agent:** Depends on commands you want to execute. Some system commands may require elevated privileges.

### Can I run this on Windows?

Yes! Both the server and agent work on Windows. Use PowerShell for running commands and setting environment variables.

### How do I change the default port?

In `server_with_event.py`, modify:
```python
app.run(host='0.0.0.0', port=8080, debug=False)
```

Change `port=8080` to your desired port.

### Do I need a database server?

No. ShadowNet uses SQLite which is file-based and included with Python. No separate database server is required.

### Can I use this with Docker?

Docker support is planned for future releases. Currently, you can create your own Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY server/ .
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "server_with_event.py"]
```

---

## Agent Questions

### How do I compile the agent?

```bash
cd agent
go build -o agent main.go
```

For cross-compilation:
```bash
# For Windows from Linux/macOS
GOOS=windows GOARCH=amd64 go build -o agent.exe main.go

# For Linux from Windows/macOS
GOOS=linux GOARCH=amd64 go build -o agent main.go
```

### Why isn't my agent showing up in the dashboard?

**Check these:**
1. **Server URL**: Ensure `serverURL` in agent code matches your server
2. **Encryption key**: Server and agent must use the same key
3. **Network connectivity**: Can the agent reach the server?
4. **Firewall**: Is port 8080 (or your port) open?
5. **Server running**: Is the Flask server actually running?

### How do I customize beacon intervals?

In `agent/main.go`, modify:
```go
minSleep := 5  // Minimum seconds
maxSleep := 15 // Maximum seconds
```

### Can agents survive reboots?

Basic persistence is included. For production use cases, you may need to configure platform-specific persistence mechanisms (startup folders, scheduled tasks, services, etc.).

### How do I see agent output?

- **Dashboard**: Go to the agent detail page, scroll to "Recent Tasks"
- **Command execution**: Results appear a few seconds after beacon
- **Logs**: Check the agent terminal for local logs

### Can I run multiple agents from the same machine?

Yes! Each agent gets a unique ID based on system information. They will appear as separate agents in the dashboard.

### How do I uninstall/remove an agent?

Simply stop the agent process. For persistence cleanup:
- **Windows**: Check Task Scheduler, Startup folder, Registry Run keys
- **Linux**: Check cron jobs, systemd services, init scripts

---

## Server Questions

### What is the default username and password?

- **Username**: `admin`
- **Password**: `admin123`

**IMPORTANT**: Change these immediately in production!

### How do I change the admin password?

1. Log in as admin
2. (Feature to be added in UI)

Or manually:
```python
import database, hashlib
new_hash = hashlib.sha256(b"NewPassword123").hexdigest()
database.update_user_password('admin', new_hash)
```

### How do I add more users?

Currently, manually via database:
```python
import database
database.create_user('username', 'password_hash', 'operator')
```

Web-based user management is planned for future releases.

### Can I run the server on a different machine than agents?

Yes! Update the `serverURL` in agent code:
```go
serverURL := "http://your-server-ip:8080/beacon"
```

### How do I enable HTTPS?

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed HTTPS setup with SSL certificates.

### Where is data stored?

All data is stored in `server/shadownet.db` (SQLite database). This includes:
- User accounts
- Agent information
- Task history
- Events and incidents
- Command templates

### How do I backup the database?

Create a backup:
```bash
cp server/shadownet.db server/shadownet_backup_$(date +%Y%m%d).db
```

Or use SQLite backup command:
```bash
sqlite3 server/shadownet.db ".backup 'backup.db'"
```

### Can I export data?

Yes, you can export to JSON:
```python
import database, json

agents = database.get_all_agents()
with open('agents_export.json', 'w') as f:
    json.dump(agents, f, indent=2)
```

---

## Security & Legal

### Is the communication encrypted?

Yes! All agent-server communication uses AES-256-GCM encryption with a shared secret key.

### How secure is the encryption?

AES-256-GCM is military-grade encryption used by governments and enterprises worldwide. The security depends on:
- Keeping your encryption key secret (32 bytes)
- Using HTTPS in production
- Proper operational security

### What if someone captures network traffic?

Without the encryption key, captured traffic appears as random encrypted data. However:
- Traffic patterns may still be analyzed
- Use HTTPS for additional transport encryption
- Consider traffic obfuscation techniques

### Is it safe to test on production networks?

**NO!** Always test in isolated lab environments:
- Virtual lab networks
- Separate physical networks
- Cloud-based isolated environments

Never test on production systems without explicit authorization.

### What legal authorization do I need?

- **Written permission** from system owner
- **Scope document** defining what can be tested
- **Rules of engagement**
- **Compliance** with local laws

Consult with legal counsel before conducting security testing.

### Can this be detected by antivirus/EDR?

Potentially, yes. The agent:
- Makes network connections
- Executes commands
- May exhibit suspicious behavior

For research purposes, you may need to:
- Add exceptions in test environments
- Study detection mechanisms
- Develop evasion techniques (educational purposes only)

### How do I report a security vulnerability?

**Do NOT open a public issue!**

Email security concerns privately to: security@[your-domain].com

See [SECURITY.md](SECURITY.md) for full policy.

---

## Troubleshooting

### "Agent not found" error

**Cause**: Agent ID doesn't exist in database

**Solution**:
- Ensure agent has successfully beaconed at least once
- Check agent logs for connection errors
- Verify server logs for incoming beacons

### "Invalid encryption key" error

**Cause**: Mismatched encryption keys between server and agent

**Solution**:
```bash
# Ensure both use the same 32-byte key
export SHADOWNET_SECRET_KEY="01234567890123456789012345678901"
```

### "Database is locked" error

**Cause**: Multiple processes accessing SQLite database simultaneously

**Solution**:
- Ensure only one server process is running
- Add database timeout: `conn = sqlite3.connect('shadownet.db', timeout=20)`
- Consider moving to PostgreSQL for production

### Commands not executing

**Check**:
1. Is the agent still connected? (Check "Last Seen" timestamp)
2. Is the command syntax correct for the OS?
3. Are there any errors in agent logs?
4. Does the command require elevated privileges?

### Dashboard not loading

**Check**:
1. Is the server running? (`python server_with_event.py`)
2. Is port 8080 accessible?
3. Browser console for JavaScript errors (F12)
4. Server logs for error messages

### "Loading commands..." stuck

**Cause**: Session expired or API authentication issue

**Solution**:
- Refresh the page and log in again
- Clear browser cookies
- Check that you're logged in (try accessing /dashboard)

### High CPU/Memory usage

**Causes**:
- Too many agents connected
- Database growing too large
- Memory leak in event logging

**Solutions**:
- Limit number of agents
- Archive old events: `DELETE FROM events WHERE timestamp < datetime('now', '-30 days')`
- Run `VACUUM` on database periodically

---

## Features & Capabilities

### What commands can agents execute?

Any shell command the agent has permissions to run:
- **Windows**: Uses `cmd.exe /C command`
- **Linux/macOS**: Uses `sh -c command`

25+ pre-built commands available in Command Library.

### Can agents download/upload files?

Basic file operations (list, read) are supported. Full file upload/download is on the roadmap.

### Does it support screenshotsing?

Not yet. Screenshot capture is planned for a future release.

### Can it capture keystrokes?

Not currently. Keylogger functionality is planned but should only be used in authorized testing.

### Does it support lateral movement?

Basic command execution is supported. Advanced lateral movement techniques (RDP, PSExec, WMI) can be implemented with custom commands.

### Can I add custom commands?

Yes! Use the Command Library:
1. Click "Command Library"
2. Click "Add Command Template"  
3. Fill in details and save

Or add directly to database.

### Is there an API?

Yes! RESTful API endpoints:
- `/api/agents` - Get all agents
- `/api/commands` - Get command templates
- `/api/incidents` - Get security incidents
- `/beacon` - Agent beacon endpoint

See README for details.

### Can I integrate with other tools?

Yes! The API allows integration with:
- SIEM systems
- Ticketing systems
- Analysis frameworks
- Custom automation scripts

---

## Contributing

### How can I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation
- Help others in discussions

### What should I work on?

Check the [Roadmap](#) or [GitHub Issues](https://github.com/yourusername/shadownet-c2/issues) for ideas:
- Features marked "help wanted"
- Bug fixes
- Documentation improvements
- Testing on different platforms

### How do I submit a bug report?

1. Check [existing issues](https://github.com/yourusername/shadownet-c2/issues)
2. If not found, create new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information
   - Logs/screenshots

### Do contributors get credit?

Yes! Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Release notes
- GitHub contributor graph

---

## More Questions?

**Can't find your answer?**

- 📖 Check [README.md](README.md) for general documentation
- 🚀 Read [QUICKSTART.md](QUICKSTART.md) for setup help
- 🔒 Review [SECURITY.md](SECURITY.md) for security topics
- 💬 Start a [Discussion](https://github.com/yourusername/shadownet-c2/discussions)
- 🐛 Open an [Issue](https://github.com/yourusername/shadownet-c2/issues)

---

<div align="center">

**Still have questions? Don't hesitate to ask!**

[Ask a Question](https://github.com/yourusername/shadownet-c2/discussions) • [Report a Bug](https://github.com/yourusername/shadownet-c2/issues) • [Documentation](README.md)

</div>
