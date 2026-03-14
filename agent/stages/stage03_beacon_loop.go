package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"time"
)

type AgentInfo struct {
	Agent    string `json:"agent"`
	Hostname string `json:"hostname"`
	OS       string `json:"os"`
	Arch     string `json:"arch"`
	Status   string `json:"status"`
}

func collectSystemInfo() AgentInfo {
	hostname, err := os.Hostname()
	if err != nil {
		hostname = "unknown"
	}

	return AgentInfo{
		Agent:    "go-agent",
		Hostname: hostname,
		OS:       runtime.GOOS,
		Arch:     runtime.GOARCH,
		Status:   "alive",
	}
}

func sendBeacon(info AgentInfo) error {
	jsonData, err := json.Marshal(info)
	if err != nil {
		return err
	}

	resp, err := http.Post(
		"http://127.0.0.1:8080/beacon",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

func main() {
	fmt.Println("[*] ShadowNet agent started (main.go)")

	for {
		info := collectSystemInfo()

		err := sendBeacon(info)
		if err != nil {
			fmt.Println("[!] Beacon failed:", err)
		} else {
			fmt.Println("[+] Beacon sent successfully")
		}

		time.Sleep(10 * time.Second)
	}
}
