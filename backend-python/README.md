# Nerve AIOps Backend

Python FastAPI backend providing AIOps intelligence for the Nerve monitoring platform.

## Features

- **Anomaly Detection** - Identifies unusual patterns in latency and status codes
- **Failure Prediction** - Predicts potential failures before they happen
- **Trend Analysis** - Analyzes performance trends over time
- **Alert Classification** - Categorizes and prioritizes alerts by severity

## Architecture

- **FastAPI** - Modern Python web framework
- **Supabase** - Database and data access
- **Background Workers** - Continuous analysis of monitoring data
- **ML/Statistics** - scikit-learn, pandas, numpy for analysis

## Setup

### Prerequisites

- Python 3.9+
- Supabase project with `monitors` and `ping_logs` tables

### Installation

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in `backend-python/`:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   ```

## Running

### Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or use Python directly:
```bash
python main.py
```

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check

### Monitors
- `GET /api/monitors` - Get all monitors
- `GET /api/monitors/{monitor_id}` - Get specific monitor

### Alerts
- `GET /api/alerts` - Get all alerts
- `GET /api/alerts?monitor_id={id}` - Get alerts for a monitor
- `GET /api/alerts/{monitor_id}/summary` - Get alert summary

### Predictions
- `GET /api/predictions` - Get all failure predictions
- `GET /api/predictions?monitor_id={id}` - Get prediction for monitor
- `GET /api/predictions/{monitor_id}` - Get specific prediction

### Trends
- `GET /api/trends` - Get all trend analyses
- `GET /api/trends?monitor_id={id}&days=7` - Get trends for monitor
- `GET /api/trends/{monitor_id}?days=7` - Get specific trend

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Background Worker

The analyzer worker runs continuously in the background:
- Analyzes all monitors every 5 minutes
- Detects anomalies
- Generates predictions
- Analyzes trends
- Classifies alerts

## Services

### AnomalyDetector
- Detects latency anomalies using IQR method
- Identifies unexpected status code changes
- Analyzes patterns in monitoring data

### FailurePredictor
- Calculates failure risk scores
- Identifies risk factors (latency increase, failure rate, etc.)
- Provides confidence levels

### TrendAnalyzer
- Analyzes latency trends (increasing/decreasing/stable)
- Tracks uptime trends
- Calculates performance metrics (P95, P99, etc.)

### AlertClassifier
- Classifies alerts by severity (critical/high/medium/low)
- Categorizes by type (availability/performance/general)
- Prioritizes alerts by importance

## Development

### Project Structure

```
backend-python/
├── app/
│   ├── services/          # Business logic services
│   │   ├── anomaly_detector.py
│   │   ├── failure_predictor.py
│   │   ├── trend_analyzer.py
│   │   ├── alert_classifier.py
│   │   └── supabase_client.py
│   ├── routers/          # API route handlers
│   │   ├── monitors.py
│   │   ├── alerts.py
│   │   ├── predictions.py
│   │   └── trends.py
│   └── workers/          # Background workers
│       └── analyzer_worker.py
├── main.py               # FastAPI application
├── requirements.txt      # Dependencies
└── README.md
```

## Testing

Test the API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Get all monitors
curl http://localhost:8000/api/monitors

# Get predictions
curl http://localhost:8000/api/predictions

# Get trends
curl http://localhost:8000/api/trends
```

## Environment Variables

- `SUPABASE_URL` (required) - Supabase project URL
- `SUPABASE_SERVICE_KEY` (required) - Supabase service role key

## License

Part of the Nerve project.

