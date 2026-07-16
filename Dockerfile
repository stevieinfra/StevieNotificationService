# Stevie Notification Tool — image with BOTH Python (the form/API) and Node
# (the send engine), because the FastAPI app shells out to scripts/broadcast.js.

FROM python:3.11-slim

# --- Install Node.js 20 (send engine uses global fetch, needs Node 18+) ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y curl && apt-get autoremove -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies ---
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- Node dependencies ---
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# --- App source ---
COPY . .

# Host provides $PORT at runtime; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000
# If SUBSCRIBERS_CSV_CONTENT is set (e.g. on Railway, which has no secret files),
# write it to a file and point SUBSCRIBERS_CSV at it — keeps real numbers out of
# the repo/image. Then start the server.
CMD ["sh", "-c", "if [ -n \"$SUBSCRIBERS_CSV_CONTENT\" ]; then printf '%s' \"$SUBSCRIBERS_CSV_CONTENT\" > /tmp/subscribers.csv && export SUBSCRIBERS_CSV=/tmp/subscribers.csv; fi; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
