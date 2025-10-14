# ScoutAlina API

Base URL: `/api`

## Health

- `GET /health` → `{ status: "ok" }`

## Ping

- `GET /api/v1/ping` → `{ message: "pong" }`

## Events

- `POST /api/v1/events`
  - Body: JSON object representing a discovery event
  - Response: `201 Created` with `{ received: <payload> }`
  - TODO: Add schema, auth requirements, and error handling


