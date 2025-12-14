# Project Nerve

A high-performance monitoring and ops platform with a hybrid architecture designed to scale from MVP to a complex AIOps platform.

## Architecture

- **Go** - Fast, reliable monitoring agents
- **Python** - AI/AIOps intelligence layer (future)
- **Flutter** - Real-time mobile & web dashboards (future)
- **Supabase** - Central data, auth, and realtime layer
- **Railway** - Simple GitOps-based deployment

## Project Structure

```
Nerve/
├── agent-go/          # Go monitoring agent (always-on service)
├── backend-python/     # Python FastAPI + AIOps layer (future)
├── app-flutter/        # Flutter mobile + web app (future)
├── infra/             # CI/CD, env notes, deployment metadata
│   └── railway/       # Railway deployment configurations
└── README.md          # This file
```

## Current Status

### ✅ Phase 1: Go Monitoring Agent (COMPLETE)

The Go monitoring agent is ready for deployment. It:
- Fetches monitor configurations from Supabase
- Performs HTTP health checks at configured intervals
- Writes telemetry data to Supabase `ping_logs` table
- Refreshes monitor list periodically
- Supports graceful shutdown and structured logging

See [agent-go/README.md](agent-go/README.md) for detailed documentation.

### 🔄 Phase 2: Flutter Realtime Dashboard (PLANNED)

- Mobile app (iOS/Android) with realtime updates
- Live system health visualization
- Monitor status and latency charts

### 🔄 Phase 3: Ops Actions (PLANNED)

- Kill switch functionality
- Server restart capabilities
- Secure script execution

### 🔄 Phase 4: Python Backend & AIOps (PLANNED)

- Anomaly detection
- Failure prediction
- Trend analysis
- Alert classification

### 🔄 Phase 5: Scale & Polish (PLANNED)

- Push notifications
- SSL expiry monitoring
- Multi-region agents
- Billing & monetization
- Role-based access control

## Prerequisites

- **Go 1.21+** - For the monitoring agent
- **Supabase Account** - Database and realtime backend
- **Railway Account** - For deployment (optional, can run locally)
- **Git** - Version control

## Quick Start

### 1. Supabase Setup

Your Supabase project should already be configured with:
- `monitors` table (configuration)
- `ping_logs` table (telemetry)

See the project context document for the exact schema.

### 2. Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Rishi-Selarka/Nerve.git
   cd Nerve
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. **Run the Go agent:**
   ```bash
   cd agent-go
   go mod download
   go run main.go
   ```

   Or build and run:
   ```bash
   go build -o nerve-agent
   ./nerve-agent
   ```

### 3. Railway Deployment

1. **Create a Railway project:**
   - Go to [railway.app](https://railway.app)
   - Create new project
   - Connect to GitHub repository: `https://github.com/Rishi-Selarka/Nerve`

2. **Configure the service:**
   - Add environment variables:
     - `SUPABASE_URL`
     - `SUPABASE_SERVICE_KEY`
   - (Optional) Configure other settings from `.env.example`

3. **Deploy:**
   - Railway will auto-detect Go and build using Nixpacks
   - The agent will start automatically
   - Check logs to verify it's running

See [agent-go/README.md](agent-go/README.md) for detailed deployment instructions.

## Environment Variables

See [.env.example](.env.example) for all available configuration options.

**Required:**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key

**Optional:**
- `LOG_LEVEL` - Logging level (default: `info`)
- `HTTP_TIMEOUT` - HTTP timeout for checks (default: `10s`)
- `MONITOR_REFRESH_INTERVAL` - Monitor refresh interval (default: `5m`)
- `HEALTH_CHECK_PORT` - Health check endpoint port (default: `8080`)

## Database Schema

The project uses Supabase (PostgreSQL) with the following tables:

### `monitors` (Configuration)
- `id` (uuid, primary key)
- `url` (text, NOT NULL)
- `interval_seconds` (int4, NOT NULL, must be > 0)
- `is_enabled` (boolean, default true)
- `created_at` (timestamptz, default now())
- `user_id` (uuid, nullable)

### `ping_logs` (Telemetry)
- `id` (uuid, primary key)
- `monitor_id` (uuid, NOT NULL)
- `checked_at` (timestamptz, NOT NULL, default now())
- `latency_ms` (int4, NOT NULL)
- `status_code` (int4, NOT NULL)
- `is_success` (boolean, NOT NULL)

**Note:** RLS is enabled on both tables. The service role key bypasses RLS.

## Testing

### Add a Test Monitor

```sql
INSERT INTO monitors (url, interval_seconds, is_enabled)
VALUES ('https://www.google.com', 30, true);
```

### Verify Telemetry

```sql
SELECT * FROM ping_logs 
ORDER BY checked_at DESC 
LIMIT 10;
```

## Contributing

This is a private project. Development follows the phased roadmap outlined in `nerveprojectcontext.md`.

## License

[Add your license here]

## Support

For issues or questions, please refer to the individual component READMEs:
- [agent-go/README.md](agent-go/README.md) - Go agent documentation

