# Deploying AeroRisk

Architecture: **Cloudflare Pages** (SPA) → **Cloudflare Tunnel** → **FastAPI backend on your own box**.

No inbound ports open on the backend. Free TLS. Free DDoS protection. The Pages SPA hits a hostname like `api.your-domain.example` which Cloudflare routes through the tunnel back to `uvicorn` on the backend host.

## 1. Backend — run uvicorn

On whatever box will host the backend (laptop, VPS, a NUC under your desk):

```bash
cd aerorisk/backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Production env vars
export DATABASE_URL="sqlite:///./aerorisk.db"   # or a real Postgres URL
export REQUIRE_AUTH=true                         # enforce login
export JWT_SECRET="$(openssl rand -hex 32)"      # rotate from the demo default
export CORS_ALLOW_ORIGINS="https://aerorisk.pages.dev,https://aerorisk.example.com"
export PUBLIC_BASE_URL="https://aerorisk.example.com"

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The bind is **127.0.0.1**, not `0.0.0.0` — only the tunnel needs to reach it.

For a real deployment wrap this in `systemd` (Linux) or `launchd` (Mac).

## 2. Cloudflare Tunnel

```bash
# Install once
brew install cloudflared           # macOS
# or: apt install cloudflared      # Debian/Ubuntu

# Auth once (opens browser, pick the zone)
cloudflared tunnel login

# Create the tunnel
cloudflared tunnel create aerorisk-api

# Wire DNS — picks the right zone automatically
cloudflared tunnel route dns aerorisk-api api.your-domain.example

# Copy deploy/cloudflared.config.example.yml → cloudflared.config.yml,
# paste the tunnel UUID + credentials-file path it printed, then:
cloudflared tunnel --config cloudflared.config.yml run
```

Verify: `curl https://api.your-domain.example/health` returns `{"status":"healthy"}`.

## 3. Frontend — Cloudflare Pages

In the Cloudflare dashboard → Workers & Pages → Create → Pages → Connect to git → pick the repo:

| Setting | Value |
| --- | --- |
| Production branch | `main` (or your release branch) |
| Build command | `cd aerorisk/frontend && npm install && npm run build` |
| Build output directory | `aerorisk/frontend/dist` |
| Root directory | *(leave empty)* |

**Environment variables** (Production scope):
- `VITE_API_BASE` = `https://api.your-domain.example`

Trigger a deploy. Pages serves the SPA at `https://<project>.pages.dev`, then add your custom domain in the Pages dashboard.

The `_redirects` and `_headers` files in `public/` ship automatically — `_redirects` makes react-router's `/share/:token` and `/welcome` work, `_headers` caches hashed assets forever and never caches `index.html`.

## 4. Smoke test

1. `https://api.your-domain.example/health` → 200
2. `https://aerorisk.pages.dev/welcome` → marketing page loads, "live numbers" strip populates from the real backend
3. `https://aerorisk.pages.dev/` → AuthGate triggers, login screen shows
4. Sign in with `admin@aerorisk.ai` / your rotated password
5. Upload a CycloneDX SBOM on the `/bom` page → analysis returns

If the login page hangs at "Loading session…" the SPA can't reach the API — check CORS_ALLOW_ORIGINS and that the tunnel is up.
