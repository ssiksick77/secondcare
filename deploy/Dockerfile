# SECONDCare server image. Build from the repository root:
#   docker build -f deploy/Dockerfile -t secondcare .
# Everything that changes at run time lives under /data (a host folder,
# see docker-compose.yml): the ledger, backups, .env, Google files, chats.
FROM python:3.12-slim
WORKDIR /srv/app
COPY app/requirements.txt .
# pystray and pillow are only for the Windows tray launcher.
RUN grep -vE '^(pystray|pillow)' requirements.txt > requirements.server.txt \
 && pip install --no-cache-dir -r requirements.server.txt
COPY app/ .
# The code keeps these paths next to main.py; point them into the volume.
RUN rm -rf backup __pycache__ .env google_token.json google_client_secret.json drive_folders.json \
 && ln -s /data/backup backup \
 && for f in google_token.json google_client_secret.json google_oauth_client.json drive_folders.json google_token.expired; do ln -s /data/$f $f; done
ENV PYTHONUNBUFFERED=1 \
    LEDGER_HOST=0.0.0.0 \
    LEDGER_PORT=8791 \
    LEDGER_ENV=/data/.env \
    LEDGER_CHAT_DB=/data/chats.sqlite \
    LEDGER_NO_BROWSER=1
CMD ["python", "main.py"]
