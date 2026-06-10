Deployment guide
===============

This project can be deployed via Docker or a PaaS (Render, Heroku, Railway). Below are quick instructions.

Docker (recommended):

1. Build the image:

```bash
docker build -t scholarship-app:latest .
```

2. Run the container (map a port and provide env vars):

```bash
docker run -e DATABASE_URL=... -e PG_SSLMODE=require -p 5000:5000 scholarship-app:latest
```

Heroku / Render / Railway (Procfile):

- Ensure `requirements.txt` includes `gunicorn` (already added).
- Push to Git and connect the repo to the PaaS; the `Procfile` will start the app.
- Set environment variables on the platform (`DATABASE_URL` preferred, or `PG_*`).

Notes:
- The app reads `.env` from the repo root in development. In production, set real environment variables via your host.
- Initialize database tables by running: `python Backend/debug_init_db.py` (requires DB access).
