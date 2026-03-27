# Local Testing

This project is easiest to test locally by running:

- the FastAPI backend on port `7860`
- a simple static file server for the frontend on port `8080`

## 1. Go To The Project

```bash
cd /Users/pleddy/docs/cloudautomat/code/projects/flux
```

## 2. Activate The Virtualenv

```bash
source ~/bin/venv/bin/activate
```

## 3. Run The Test Suite

```bash
bash run_tests.sh
```

## 4. Start The Backend

Run this in one terminal:

```bash
uvicorn main:app --host 127.0.0.1 --port 7860 --reload
```

The API will be available at:

- `http://127.0.0.1:7860`

Useful health check:

```bash
curl http://127.0.0.1:7860/health
```

## 5. Start The Frontend

Run this in a second terminal:

```bash
cd /Users/pleddy/docs/cloudautomat/code/projects/flux
python3 -m http.server 8080
```

The frontend will be available at:

- `http://127.0.0.1:8080/index.html`

When opened from `localhost` or `127.0.0.1`, the page automatically points its API calls at:

- `http://localhost:7860`

## 6. Open The App

Open this in your browser:

```text
http://127.0.0.1:8080/index.html
```

## 7. Recommended Local Checks

- Open two browser windows to verify live game-board updates.
- Create a game in one window and confirm it appears in the other.
- Join from the board using a remembered username.
- Leave a game and confirm `Rejoin` appears for that unfinished game.
- Verify the board returns without a manual refresh.

## Notes

- Game data is stored in memory only while the backend process is running.
- Restarting `uvicorn` clears the active game list.
- If the board or gameplay looks stale, hard refresh the browser after frontend changes.
