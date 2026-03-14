package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

// =============================
// CONFIG
// =============================

var serverURL = "http://127.0.0.1:8080/beacon"
var secretKey = []byte("01234567890123456789012345678901")

// =============================
// STATE
// =============================

var agentID = loadOrCreateAgentID()

// =============================
// STRUCTS
// =============================

// Data sent TO server
type Beacon struct {
	AgentID string `json:"agent_id"`
	Ack     string `json:"ack,omitempty"`
}

// Data received FROM server
type ServerResponse struct {
	Task *Task `json:"task"`
}

type Task struct {
	ID   string `json:"id"`
	Type string `json:"type"`
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
	_, err = rand.Read(nonce)
	if err != nil {
		return "", err
	}

	ciphertext := gcm.Seal(nonce, nonce, data, nil)
	return base64.StdEncoding.EncodeToString(ciphertext), nil
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
	nonce, ciphertext := raw[:nonceSize], raw[nonceSize:]
	return gcm.Open(nil, nonce, ciphertext, nil)
}

// =============================
// BEACON COMMUNICATION
// =============================

func sendBeacon(ack string) (*ServerResponse, error) {

	beacon := Beacon{
		AgentID: agentID,
		Ack:     ack,
	}

	raw, _ := json.Marshal(beacon)
	enc, err := encrypt(raw)
	if err != nil {
		return nil, err
	}

	payload, _ := json.Marshal(map[string]string{
		"data": enc,
	})

	resp, err := http.Post(serverURL, "application/json", bytes.NewBuffer(payload))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var serverReply map[string]string
	json.NewDecoder(resp.Body).Decode(&serverReply)

	dec, err := decrypt(serverReply["data"])
	if err != nil {
		return nil, err
	}

	var sr ServerResponse
	json.Unmarshal(dec, &sr)

	return &sr, nil
}

// =============================
// AGENT ID MANAGEMENT
// =============================

func loadOrCreateAgentID() string {
	const file = ".agent_id"

	if data, err := os.ReadFile(file); err == nil {
		return string(data)
	}

	id := fmt.Sprintf("agent-%d", time.Now().UnixNano())
	_ = os.WriteFile(file, []byte(id), 0600)
	return id
}

// =============================
// JITTER SLEEP
// =============================

func sleepJitter() {
	base := 10
	jitter := time.Duration(time.Now().UnixNano()%5) * time.Second
	time.Sleep(time.Duration(base)*time.Second + jitter)
}

// =============================
// MAIN
// =============================

func main() {

	fmt.Println("[*] Agent started")
	fmt.Println("[*] Agent ID:", agentID)

	var pendingAck string = ""

	for {
		// 1. Send heartbeat / ACK
		resp, err := sendBeacon(pendingAck)
		if err != nil {
			sleepJitter()
			continue
		}

		// 2. If task received
		if resp != nil && resp.Task != nil {
			fmt.Println("[+] Task received:", resp.Task.Type)
			pendingAck = resp.Task.ID
		} else {
			pendingAck = ""
		}

		// 3. Sleep with jitter
		sleepJitter()
	}
}
