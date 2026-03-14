package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
)

func main() {
	hostname, err := os.Hostname()
	if err != nil {
		hostname = "unknown"
	}

	data := map[string]string{
		"agent":    "go-agent",
		"hostname": hostname,
		"os":       runtime.GOOS,
		"arch":     runtime.GOARCH,
		"status":   "alive",
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		fmt.Println("Error creating JSON:", err)
		return
	}

	resp, err := http.Post(
		"http://127.0.0.1:8080/beacon",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		fmt.Println("Error sending request:", err)
		return
	}
	defer resp.Body.Close()

	fmt.Println("Agent beacon sent successfully")
}
