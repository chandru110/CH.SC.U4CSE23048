# vehicle_maintenance_scheduler

A production-style FastAPI backend built for the AffordMed Backend Assessment. This service authenticates with an external evaluation API, fetches depots and vehicle tasks, and computes an optimized maintenance schedule using a 0/1 knapsack algorithm.

## Tech Stack

- FastAPI
- httpx
- python-dotenv
- Pydantic
- Async programming

## Project Structure

```
vehicle_maintenance_scheduler/
├── main.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── middleware/
│   └── logger.py
├── services/
│   ├── auth_service.py
│   ├── api_service.py
│   └── scheduler_service.py
├── routes/
│   └── scheduler_routes.py
├── models/
│   └── schemas.py
└── utils/
    └── constants.py
```

## Features

- Reads environment variables from `.env` using `python-dotenv`
- Uses async `httpx` for all external HTTP requests
- Implements registration and authentication against the evaluation API
- Stores `clientID`, `clientSecret`, and `access_token` securely at runtime
- Adds reusable logging middleware with external log ingestion
- Fetches protected resources: depots and vehicles
- Computes optimal task schedule using dynamic programming (0/1 knapsack)
- Includes startup registration and authentication
- Handles exceptions cleanly and logs important events

## Setup

1. Create a Python virtual environment and activate it.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the required variables.

```ini
EVAL_BASE_URL=http://20.207.122.201
AFFORDMED_EMAIL=your-email@example.com
AFFORDMED_NAME=Your Name
AFFORDMED_MOBILE_NO=9999999999
AFFORDMED_GITHUB_USERNAME=your-github
AFFORDMED_ROLL_NO=YOUR_ROLL_NO
AFFORDMED_ACCESS_CODE=PTBMmQ
```

4. Optionally add pre-existing credentials to skip registration.

```ini
EVAL_CLIENT_ID=<client-id>
EVAL_CLIENT_SECRET=<client-secret>
```

## Running the Application

```bash
uvicorn main:app --reload
```

The application runs on `http://127.0.0.1:8000` by default.

## API Endpoints

### Schedule a Depot

`GET /schedule/{depot_id}`

Response:

```json
{
  "depot_id": 1,
  "mechanic_hours": 60,
  "maxImpact": 123,
  "selectedTasks": [
    {
      "id": 10,
      "duration": 20,
      "impact": 40
    }
  ]
}
```

## Auth Flow

1. On startup, the application loads `.env` values.
2. If no existing credentials are available, it registers the user at `/evaluation-service/register`.
3. It saves `clientID` and `clientSecret`.
4. It authenticates via `/evaluation-service/auth` and stores the returned `access_token`.
5. All protected API calls use the Bearer token.

## Logging

- The `middleware/logger.py` package exposes an async `Log(stack, level, package, message)` function.
- Logs are emitted locally and optionally forwarded to `/evaluation-service/logs` when an access token is available.
- Allowed log fields:
  - `stack`: `backend`
  - `level`: `debug`, `info`, `warn`, `error`, `fatal`
  - `package`: `cache`, `controller`, `cron_job`, `db`, `domain`, `handler`, `repository`, `route`, `service`, `auth`, `middleware`, `utils`

## Implementation Notes

- `utils/constants.py` defines environment loading and shared API paths.
- `services/auth_service.py` manages registration, authentication, and credential persistence.
- `services/api_service.py` fetches protected depots and vehicles.
- `services/scheduler_service.py` performs knapsack optimization.
- `routes/scheduler_routes.py` exposes the scheduling API.
- `models/schemas.py` contains request and response Pydantic models.

## `.gitignore`

Ensure your repository ignores:

```
.venv
.env
__pycache__
*.pyc
```

## Requirements

- fastapi
- uvicorn
- httpx
- python-dotenv
- pydantic

## Notes

- This project is designed to be runnable via `uvicorn main:app --reload`.
- Ensure `.env` contains all required variables before startup.
- The schedule endpoint uses a dynamic programming solution to maximize impact within depot mechanic hour constraints.

- ## Output
- uvicorn main:app --reload
INFO:     Will watch for changes in these directories: ['D:\\CH.SC.U4CSE23048\\vehicle_maintenance_scheduler']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [22080] using StatReload
INFO:     Started server process [12176]
INFO:     Waiting for application startup.
2026-05-06 15:52:17,815 INFO vehicle_maintenance_scheduler - [backend/info/middleware] Application starting up.
2026-05-06 15:52:17,815 INFO vehicle_maintenance_scheduler - [backend/info/auth] Loaded client credentials from environment.
2026-05-06 15:52:17,815 INFO vehicle_maintenance_scheduler - [backend/info/auth] Requesting access token (clientID=***7a5d).
2026-05-06 15:52:18,392 INFO httpx - HTTP Request: POST http://20.207.122.201/evaluation-service/auth "HTTP/1.1 400 Bad Request"
2026-05-06 15:52:18,395 INFO vehicle_maintenance_scheduler - [backend/error/auth] Auth attempt 1 failed: 400 path=/evaluation-service/auth location=None body='{"errors":[{"email":"is required"},{"name":"is required"},{"rollNo":"is required"},{"accessCode":"is required"}]}'
2026-05-06 15:52:18,887 INFO httpx - HTTP Request: POST http://20.207.122.201/evaluation-service/auth "HTTP/1.1 400 Bad Request"
2026-05-06 15:52:18,893 INFO vehicle_maintenance_scheduler - [backend/error/auth] Auth attempt 2 failed: 400 path=/evaluation-service/auth location=None body='{"errors":[{"email":"is required"},{"name":"is required"},{"rollNo":"is required"},{"accessCode":"is required"}]}'
2026-05-06 15:52:19,376 INFO httpx - HTTP Request: POST http://20.207.122.201/evaluation-service/auth "HTTP/1.1 201 Created"
2026-05-06 15:52:19,380 INFO vehicle_maintenance_scheduler - [backend/info/auth] Authentication successful; bearer token stored in-memory.
2026-05-06 15:52:19,886 INFO httpx - HTTP Request: POST http://20.207.122.201/evaluation-service/logs "HTTP/1.1 400 Bad Request"
2026-05-06 15:52:19,901 WARNING vehicle_maintenance_scheduler - External log failed: Client error '400 Bad Request' for url 'http://20.207.122.201/evaluation-service/logs'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
2026-05-06 15:52:19,901 INFO vehicle_maintenance_scheduler - [backend/info/middleware] Startup success: registered + authenticated.
2026-05-06 15:52:19,975 INFO httpx - HTTP Request: POST http://20.207.122.201/evaluation-service/logs "HTTP/1.1 201 Created"
INFO:     Application startup complete.
