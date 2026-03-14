package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
)

func main() {
	// Data to send
	data := map[string]string{
		"agent":  "go-agent",
		"status": "hello server",
	}

	// Convert data to JSON
	jsonData, err := json.Marshal(data)
	if err != nil {
		fmt.Println("Error creating JSON:", err)
		return
	}

	// Send POST request
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

	fmt.Println("Agent sent data successfully")
}
