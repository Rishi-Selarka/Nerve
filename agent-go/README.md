# Nerve Monitoring Agent (Go)

A high-performance, stateless monitoring agent that continuously checks URLs and writes telemetry data to Supabase.

## Features

- ✅ Fetches monitor configurations from Supabase
- ✅ Performs HTTP health checks at configured intervals
- ✅ Measures latency and captures status codes
- ✅ Writes telemetry data to Supabase `ping_logs` table
- ✅ Automatically refreshes monitor list (configurable interval)
- ✅ Graceful shutdown on SIGTERM/SIGINT
- ✅ Structured JSON logging
- ✅ Optional health check HTTP endpoint
- ✅ Custom User-Agent header for identification

## Architecture

The agent runs as a single process with:
- One goroutine per active monitor (ticker-based scheduling)
- Periodic monitor list refresh (default: 5 minutes)
- Stateless design (no caching, Supabase is source of truth)
- Context-based cancellation for graceful shutdown

## Configuration

All configuration is done via environment variables:

### Required

- `SUPABASE_URL` - Your Supabase project URL (e.g., `https://xxxxx.supabase.co`)
- `SUPABASE_SERVICE_KEY` - Your Supabase service role key (has admin access)

### Optional

- `LOG_LEVEL` - Logging level: `debug`, `info`, `warn`, `error` (default: `info`)
- `HTTP_TIMEOUT` - HTTP timeout for health checks, e.g., `10s`, `30s` (default: `10s`)
- `MONITOR_REFRESH_INTERVAL` - How often to refresh monitor list, e.g., `5m`, `10m` (default: `5m`)
- `HEALTH_CHECK_PORT` - Port for health check endpoint (default: `8080`). Set to empty string to disable.

## Local Development

### Prerequisites

- Go 1.21 or higher
- Supabase project with `monitors` and `ping_logs` tables configured

### Setup

1. Copy `.env.example` to `.env` and fill in your Supabase credentials:
   ```bash
   cp ../.env.example .env
   # Edit .env with your Supabase credentials
   ```

2. Install dependencies:
   ```bash
   go mod download
   ```

3. Build the agent:
   ```bash
   go build -o nerve-agent
   ```

4. Run the agent:
   ```bash
   ./nerve-agent
   ```

   Or run directly with `go run`:
   ```bash
   go run main.go
   ```

### Testing

1. **Add a test monitor to Supabase:**
   ```sql
   INSERT INTO monitors (url, interval_seconds, is_enabled)
   VALUES ('https://www.google.com', 30, true);
   ```

2. **Run the agent** and watch the logs

3. **Check ping_logs table:**
   ```sql
   SELECT * FROM ping_logs ORDER BY checked_at DESC LIMIT 10;
   ```

4. **Test graceful shutdown:**
   - Start the agent
   - Press `Ctrl+C` or send SIGTERM
   - Verify it shuts down gracefully

## Deployment

### Railway

1. **Create a Railway project** and connect it to your GitHub repository

2. **Set environment variables** in Railway dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - (Optional) Other configuration variables

3. **Configure the service:**
   - Root directory: `/` (monorepo root)
   - Build command: Railway will auto-detect Go and use Nixpacks
   - Start command: `cd agent-go && ./nerve-agent`

4. **Deploy:** Railway will automatically deploy on push to main branch

The `infra/railway/nixpacks.toml` file configures the build process.

### Health Checks

If `HEALTH_CHECK_PORT` is set (default: 8080), the agent exposes a `/health` endpoint that returns:
```json
{"status":"ok"}
```

Railway can use this for health checks.

## Troubleshooting

### Agent doesn't fetch monitors

- Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set correctly
- Verify RLS policies allow service role to read `monitors` table
- Check logs for connection errors

### Ping logs not being inserted

- Verify service role key has insert permissions on `ping_logs` table
- Check RLS policies allow inserts
- Review logs for insertion errors

### High memory usage

- Reduce `MONITOR_REFRESH_INTERVAL` if you have many monitors
- Check for goroutine leaks (should be one per monitor)

### Monitor not running

- Verify `is_enabled = true` in database
- Check `interval_seconds > 0`
- Review logs for monitor-specific errors

## Logging

The agent uses structured JSON logging with the following levels:
- `debug` - Detailed information for debugging
- `info` - General informational messages
- `warn` - Warning messages (e.g., failed health checks)
- `error` - Error messages (e.g., database connection failures)

Example log output:
```json
{"level":"info","msg":"Starting Nerve monitoring agent","time":"2024-01-01T12:00:00Z"}
{"level":"info","count":3,"msg":"Fetched monitors from Supabase","time":"2024-01-01T12:00:00Z"}
{"level":"info","monitor_id":"xxx","url":"https://example.com","status_code":200,"latency_ms":150,"success":true,"msg":"Health check completed","time":"2024-01-01T12:00:30Z"}
```

## Database Schema

The agent expects the following Supabase tables:

### `monitors` table
- `id` (uuid, primary key)
- `url` (text, NOT NULL)
- `interval_seconds` (int4, NOT NULL, must be > 0)
- `is_enabled` (boolean, default true)
- `created_at` (timestamptz, default now())
- `user_id` (uuid, nullable)

### `ping_logs` table
- `id` (uuid, primary key)
- `monitor_id` (uuid, NOT NULL)
- `checked_at` (timestamptz, NOT NULL, default now())
- `latency_ms` (int4, NOT NULL)
- `status_code` (int4, NOT NULL)
- `is_success` (boolean, NOT NULL)

## License

Part of the Nerve project.

