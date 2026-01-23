# Ekumen - Live Demo

This is the simulated demo version of [Ekumen](https://github.com/aydinguven/ekumen).
It runs entirely in Python without requiring Ansible, SSH, or actual servers.

## Features

- **Simulated Execution**: Commands return realistic dummy output.
- **In-Memory History**: Changes persist in browser localStorage.
- **Safe Sandbox**: No actual side effects on the host system.

## Deployment

Deploying this demo is simple. It only requires Python and Flask.

### 1. Requirements

- Python 3.8+
- Flask (`pip install flask`)

### 2. Run Locally

```bash
# Install dependencies
pip install flask

# Start the server
python app.py
```

The app will be available at `http://localhost:5000`.

### 3. Deploy to Render / Railway / Heroku

This directory is ready for cloud deployment.
- `requirements.txt` is present.
- `app.py` exposes the Flask app.
- Port is configurable via `PORT` environment variable.

**Example Command:**
```bash
gunicorn app:app
```
