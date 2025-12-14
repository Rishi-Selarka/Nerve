package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/supabase-community/postgrest-go"
)

// Monitor represents a monitor configuration from the database
type Monitor struct {
	ID             string `json:"id"`
	URL            string `json:"url"`
	IntervalSeconds int   `json:"interval_seconds"`
	IsEnabled      bool   `json:"is_enabled"`
}

// PingLog represents a telemetry entry to be inserted
type PingLog struct {
	MonitorID  string `json:"monitor_id"`
	CheckedAt  string `json:"checked_at"`
	LatencyMS  int    `json:"latency_ms"`
	StatusCode int    `json:"status_code"`
	IsSuccess  bool   `json:"is_success"`
}

// Config holds application configuration
type Config struct {
	SupabaseURL         string
	SupabaseServiceKey  string
	LogLevel            string
	HTTPTimeout         time.Duration
	MonitorRefreshInterval time.Duration
	HealthCheckPort     string
}

// Agent represents the monitoring agent
type Agent struct {
	config      Config
	supabase    *postgrest.Client
	logger      *logrus.Logger
	monitors    map[string]*Monitor
	ctx         context.Context
	cancel      context.CancelFunc
	httpClient  *http.Client
}

// NewAgent creates a new monitoring agent instance
func NewAgent(config Config) (*Agent, error) {
	// Initialize logger
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{})
	
	level, err := logrus.ParseLevel(config.LogLevel)
	if err != nil {
		level = logrus.InfoLevel
	}
	logger.SetLevel(level)

	// Initialize Supabase PostgREST client
	supabaseClient := postgrest.NewClient(
		config.SupabaseURL+"/rest/v1",
		"",
		map[string]string{
			"apikey":        config.SupabaseServiceKey,
			"Authorization": "Bearer " + config.SupabaseServiceKey,
		},
	)

	// Create HTTP client with timeout
	httpClient := &http.Client{
		Timeout: config.HTTPTimeout,
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 10,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &Agent{
		config:     config,
		supabase:   supabaseClient,
		logger:     logger,
		monitors:   make(map[string]*Monitor),
		ctx:        ctx,
		cancel:     cancel,
		httpClient: httpClient,
	}, nil
}

// ValidateConfig validates the configuration
func (a *Agent) ValidateConfig() error {
	if a.config.SupabaseURL == "" {
		return fmt.Errorf("SUPABASE_URL is required")
	}
	if a.config.SupabaseServiceKey == "" {
		return fmt.Errorf("SUPABASE_SERVICE_KEY is required")
	}
	return nil
}

// FetchMonitors fetches all enabled monitors from Supabase
func (a *Agent) FetchMonitors() ([]Monitor, error) {
	var monitors []Monitor
	
	// Query monitors table where is_enabled = true
	response, count, err := a.supabase.From("monitors").
		Select("id,url,interval_seconds,is_enabled", "", false).
		Eq("is_enabled", "true").
		Execute()
	
	if err != nil {
		return nil, fmt.Errorf("failed to fetch monitors: %w", err)
	}
	
	_ = count // Count not used

	if err := json.Unmarshal([]byte(response), &monitors); err != nil {
		return nil, fmt.Errorf("failed to parse monitors: %w", err)
	}

	return monitors, nil
}

// UpdateMonitorList refreshes the monitor list and manages goroutines
func (a *Agent) UpdateMonitorList() error {
	monitors, err := a.FetchMonitors()
	if err != nil {
		return fmt.Errorf("failed to fetch monitors: %w", err)
	}

	a.logger.WithField("count", len(monitors)).Info("Fetched monitors from Supabase")

	// Create a set of current monitor IDs
	currentIDs := make(map[string]bool)
	for _, m := range monitors {
		currentIDs[m.ID] = true
	}

	// Stop goroutines for monitors that are no longer enabled
	for id, monitor := range a.monitors {
		if !currentIDs[id] {
			a.logger.WithField("monitor_id", id).WithField("url", monitor.URL).Info("Stopping monitor (disabled or removed)")
			delete(a.monitors, id)
		}
	}

	// Start goroutines for new monitors
	for _, m := range monitors {
		if _, exists := a.monitors[m.ID]; !exists {
			a.monitors[m.ID] = &m
			go a.startMonitor(m)
			a.logger.WithField("monitor_id", m.ID).WithField("url", m.URL).WithField("interval", m.IntervalSeconds).Info("Started monitoring")
		}
	}

	return nil
}

// startMonitor starts a goroutine to monitor a specific URL
func (a *Agent) startMonitor(monitor Monitor) {
	interval := time.Duration(monitor.IntervalSeconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	// Perform initial check immediately
	a.performCheck(monitor)

	for {
		select {
		case <-a.ctx.Done():
			return
		case <-ticker.C:
			a.performCheck(monitor)
		}
	}
}

// performCheck performs a single health check
func (a *Agent) performCheck(monitor Monitor) {
	startTime := time.Now()

	req, err := http.NewRequestWithContext(a.ctx, "GET", monitor.URL, nil)
	if err != nil {
		a.logger.WithError(err).WithField("monitor_id", monitor.ID).Error("Failed to create request")
		a.insertPingLog(monitor.ID, 0, 0, false)
		return
	}

	// Set custom User-Agent
	req.Header.Set("User-Agent", "Nerve-Monitor/1.0")

	resp, err := a.httpClient.Do(req)
	latency := int(time.Since(startTime).Milliseconds())

	var statusCode int
	var isSuccess bool

	if err != nil {
		// Network error (timeout, DNS failure, etc.)
		statusCode = 0
		isSuccess = false
		a.logger.WithError(err).
			WithField("monitor_id", monitor.ID).
			WithField("url", monitor.URL).
			WithField("latency_ms", latency).
			Warn("Health check failed")
	} else {
		defer resp.Body.Close()
		statusCode = resp.StatusCode
		isSuccess = statusCode >= 200 && statusCode < 300

		level := logrus.InfoLevel
		if !isSuccess {
			level = logrus.WarnLevel
		}

		a.logger.WithFields(logrus.Fields{
			"monitor_id":  monitor.ID,
			"url":         monitor.URL,
			"status_code": statusCode,
			"latency_ms":  latency,
			"success":     isSuccess,
		}).Log(level, "Health check completed")
	}

	// Insert result into ping_logs
	a.insertPingLog(monitor.ID, latency, statusCode, isSuccess)
}

// insertPingLog inserts a ping log entry into Supabase
func (a *Agent) insertPingLog(monitorID string, latencyMS int, statusCode int, isSuccess bool) {
	now := time.Now().UTC().Format(time.RFC3339)
	
	pingLog := PingLog{
		MonitorID:  monitorID,
		CheckedAt:  now,
		LatencyMS:  latencyMS,
		StatusCode: statusCode,
		IsSuccess:  isSuccess,
	}

	_, _, err := a.supabase.From("ping_logs").Insert(pingLog, false, "", "", "").Execute()
	if err != nil {
		a.logger.WithError(err).
			WithField("monitor_id", monitorID).
			Error("Failed to insert ping log")
		return
	}
}

// StartHealthCheckServer starts an HTTP server for health checks (optional)
func (a *Agent) StartHealthCheckServer() {
	if a.config.HealthCheckPort == "" {
		return
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	server := &http.Server{
		Addr:    ":" + a.config.HealthCheckPort,
		Handler: mux,
	}

	go func() {
		a.logger.WithField("port", a.config.HealthCheckPort).Info("Health check server started")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			a.logger.WithError(err).Error("Health check server error")
		}
	}()

	// Graceful shutdown for health check server
	go func() {
		<-a.ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		server.Shutdown(shutdownCtx)
	}()
}

// Run starts the agent and runs until interrupted
func (a *Agent) Run() error {
	// Validate configuration
	if err := a.ValidateConfig(); err != nil {
		return fmt.Errorf("configuration error: %w", err)
	}

	a.logger.Info("Starting Nerve monitoring agent")

	// Start health check server
	a.StartHealthCheckServer()

	// Initial monitor fetch
	if err := a.UpdateMonitorList(); err != nil {
		return fmt.Errorf("failed to fetch initial monitor list: %w", err)
	}

	// Set up monitor refresh ticker
	refreshTicker := time.NewTicker(a.config.MonitorRefreshInterval)
	defer refreshTicker.Stop()

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Main loop
	for {
		select {
		case <-a.ctx.Done():
			return nil
		case <-sigChan:
			a.logger.Info("Received shutdown signal, gracefully shutting down...")
			a.cancel()
			// Give goroutines time to finish
			time.Sleep(2 * time.Second)
			return nil
		case <-refreshTicker.C:
			if err := a.UpdateMonitorList(); err != nil {
				a.logger.WithError(err).Error("Failed to refresh monitor list")
				// Continue running even if refresh fails
			}
		}
	}
}

func main() {
	// Load configuration from environment variables
	config := Config{
		SupabaseURL:            getEnv("SUPABASE_URL", ""),
		SupabaseServiceKey:     getEnv("SUPABASE_SERVICE_KEY", ""),
		LogLevel:               getEnv("LOG_LEVEL", "info"),
		HTTPTimeout:            parseDuration(getEnv("HTTP_TIMEOUT", "10s"), 10*time.Second),
		MonitorRefreshInterval: parseDuration(getEnv("MONITOR_REFRESH_INTERVAL", "5m"), 5*time.Minute),
		HealthCheckPort:        getEnv("HEALTH_CHECK_PORT", "8080"),
	}

	// Create agent
	agent, err := NewAgent(config)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to create agent: %v\n", err)
		os.Exit(1)
	}

	// Run agent
	if err := agent.Run(); err != nil {
		agent.logger.WithError(err).Fatal("Agent failed")
		os.Exit(1)
	}

	agent.logger.Info("Agent stopped")
}

// Helper functions

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func parseDuration(s string, defaultDuration time.Duration) time.Duration {
	d, err := time.ParseDuration(s)
	if err != nil {
		return defaultDuration
	}
	return d
}

