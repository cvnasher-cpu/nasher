# Nasher — ناشر

Automated CV distribution service. Sends CVs to company HR emails via Gmail SMTP, scheduled daily at 490 emails/job.

## Stack
- Python / Flask
- SQLite (Flask-SQLAlchemy)
- APScheduler
- openpyxl

## Setup

```bash
pip install -r requirements.txt
python app.py
```

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask session secret | hardcoded dev key |
| `DATA_DIR` | Path for DB, CVs, codes.json | `./data` |
| `ADMIN_PASSWORD` | Password for `/admin/upload-companies` | — |
| `PORT` | Server port | `5000` |

## Deployment (Railway)

1. Set `DATA_DIR=/data` and mount a volume at `/data`
2. Set `SECRET_KEY` and `ADMIN_PASSWORD`
3. Deploy — Procfile uses gunicorn

## Activation codes

Generate codes with:

```bash
python generate_code.py
```
