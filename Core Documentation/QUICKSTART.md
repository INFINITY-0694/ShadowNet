# Quick Start Guide

Get ShadowNet C2 up and running in 5 minutes!

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.8 or higher
- ✅ Go 1.19 or higher
- ✅ Terminal/Command Prompt access
- ✅ 500MB free disk space

**Verify installations:**
```bash
python --version    # Should show 3.8+
go version          # Should show 1.19+
```

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/shadownet-c2.git
cd shadownet-c2
```

## Step 2: Set Up the Server (2 minutes)

### Install Python Dependencies

```bash
cd server
pip install -r requirements.txt
```

### Set Your Encryption Key

**Windows PowerShell:**
```powershell
$env:SHADOWNET_SECRET_KEY="01234567890123456789012345678901"
```

**Linux/macOS:**
```bash
export SHADOWNET_SECRET_KEY="01234567890123456789012345678901"
```

> ⚠️ **IMPORTANT**: Change this key to a random 32-byte string in production!

### Start the Server

```bash
python server_with_event.py
```

You should see:
```
 * Running on http://127.0.0.1:8080
```

## Step 3: Access the Dashboard (30 seconds)

1. Open your browser
2. Go to: **http://127.0.0.1:8080**
3. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin123`

> 🔐 **SECURITY**: Change these credentials immediately in production!

## Step 4: Build the Agent (1 minute)

**Open a NEW terminal** (keep the server running)

```bash
cd agent
go mod download
```

### Build for Your Platform

**Windows:**
```bash
go build -o agent.exe main.go
```

**Linux/macOS:**
```bash
go build -o agent main.go
```

### Cross-Compile (Optional)

**For Windows (from Linux/macOS):**
```bash
GOOS=windows GOARCH=amd64 go build -o agent_windows.exe main.go
```

**For Linux (from Windows/macOS):**
```bash
set GOOS=linux
set GOARCH=amd64
go build -o agent_linux main.go
```

## Step 5: Run the Agent (30 seconds)

### Set the Encryption Key

**Windows:**
```powershell
$env:SHADOWNET_SECRET_KEY="01234567890123456789012345678901"
```

**Linux/macOS:**
```bash
export SHADOWNET_SECRET_KEY="01234567890123456789012345678901"
```

### Start the Agent

**Windows:**
```bash
.\agent.exe
```

**Linux/macOS:**
```bash
./agent
```

You should see:
```
[INFO] Initializing agent...
[INFO] Beacon sent successfully
[INFO] Next beacon in XX seconds...
```

## Step 6: Verify Connection (10 seconds)

1. Go back to your browser at **http://127.0.0.1:8080**
2. You should see **1 online agent** in the dashboard
3. Click on the agent card to see details

## Step 7: Send Your First Command (1 minute)

### From the Dashboard:

1. Click on your agent in the dashboard
2. Scroll to "Send Command" section
3. Enter a command:
   - **Windows**: `whoami`
   - **Linux/macOS**: `whoami`
4. Click "Execute"
5. Wait a few seconds for the response

### From Command Library:

1. Click "Command Library" in the navigation
2. Browse pre-made commands
3. Click "Execute" on any command
4. Select your agent
5. Confirm execution

## Troubleshooting

### Agent Not Showing Up?

**Check Server URL in agent/main.go:**
```go
serverURL := "http://127.0.0.1:8080/beacon"  // Should be localhost
```

**Verify encryption key matches:**
- Server and agent MUST use the same key
- Key must be exactly 32 characters

**Check firewalls:**
- Ensure port 8080 is not blocked
- Try disabling firewall temporarily for testing

### Can't Login?

**Reset database:**
```bash
cd server
rm shadownet.db
python server_with_event.py  # Will recreate with defaults
```

### Command Not Executing?

**Check agent logs:**
- Look for error messages in agent terminal
- Verify command syntax is correct for your OS

**Check task in dashboard:**
- Go to agent detail page
- Scroll to "Recent Tasks"
- Check task status

## What's Next?

### Explore Features

✅ **Command Library**: 25+ pre-made commands  
✅ **Incident Detection**: Automatic threat detection  
✅ **Event Timeline**: Track all agent activities  
✅ **Multi-Agent**: Connect multiple agents  

### Customize

- Add custom commands in Command Library
- Create incident detection rules
- Configure agent jitter and sleep times
- Set up HTTPS for production

### Learn More

- Read [README.md](README.md) for full documentation
- Check [ARCHITECTURE.md](#) for system design
- See [API_DOCS.md](#) for API reference
- Review [SECURITY.md](SECURITY.md) for best practices

## Example Workflow

### 1. Reconnaissance Phase
```bash
# From Command Library, execute:
- System Information (Windows: systeminfo, Linux: uname -a)
- Network Configuration (ipconfig/ifconfig)
- Current User (whoami)
- Running Processes (tasklist/ps aux)
```

### 2. Persistence Check
```bash
# Check for persistence mechanisms:
- Scheduled Tasks (schtasks)
- Startup Items (registry query)
- Services (sc query)
```

### 3. Monitoring
- Watch the **Incidents** page for alerts
- Review **Events** for timeline of activities
- Export data for reporting

## Production Deployment

Before deploying to production:

1. **Change default credentials**
2. **Generate strong encryption key** (32 random bytes)
3. **Enable HTTPS** with SSL certificates
4. **Configure firewall** rules
5. **Set up logging** and monitoring
6. **Review security policy**
7. **Test in isolated environment** first

## Getting Help

- 📖 [Full Documentation](README.md)
- 🐛 [Report Bugs](https://github.com/yourusername/shadownet-c2/issues)
- 💬 [Discussions](https://github.com/yourusername/shadownet-c2/discussions)
- 🔒 [Security Policy](SECURITY.md)

## Legal Reminder

⚠️ **IMPORTANT**: Only use this tool on systems you own or have explicit written authorization to test. Unauthorized access is illegal.

---

**Congratulations!** You now have a working C2 infrastructure. Use responsibly and ethically! 🎉
