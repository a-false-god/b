# Prawko B — Production Operations Runbook

Authoritative maintenance, deployment, and troubleshooting guide for the **Prawko B** production environment hosted on an **Oracle Cloud Always Free (E2.1.Micro / 1 GB RAM)** instance.

---

## 1. Production Architecture Overview

* **Host:** Oracle Cloud VM (`Ubuntu 24.04 LTS`, AMD64, 1 GB RAM, 1 OCPU, 2 GB Swap).
* **Domain & Ingress:** `https://prawko.lqdb.pl` $\to$ Caddy 2 reverse proxy with automatic Let's Encrypt TLS.
* **Application:** FastAPI (Python 3.11) + React 18 SPA bundled into Docker image `prawko:latest`.
* **Database:** SQLite WAL stored in `data/prawko.sqlite` (persisted on host volume).
* **Media Assets:** ~2 GB video & image files stored on host in `media/` (mounted read-only).
* **Automated Backups:** Daily local SQLite snapshots via `tools/backup_db.py` (retention: 14 daily + 4 weekly) and offsite sync via `ops/rclone-backup.sh` at 04:00 UTC.

---

## 2. Standard Deployment / Update Flow

> [!CAUTION]
> **HARD RULE: NEVER RUN DOCKER BUILD OR NPM ON THE 1 GB VPS!**
> Compiling React assets and running multi-stage Docker builds on a 1 GB RAM instance will trigger Linux kernel OOM (Out Of Memory) kills. All images must be built locally (or in CI) and transferred.

### Step-by-Step Update Procedure:

#### 1. Local Machine (Build & Package)
Ensure you are on the `main` branch with a clean test suite:

```bash
# 1. Pull latest code
git checkout main && git pull origin main

# 2. Verify all tests pass
pytest -v

# 3. Build image locally for Linux AMD64 architecture
docker buildx build --platform linux/amd64 -t prawko:latest --load .

# 4. Export and compress the image
docker save prawko:latest | gzip > prawko-image.tar.gz

# 5. Transfer the compressed image to the VPS
rsync -avz --progress prawko-image.tar.gz ubuntu@92.5.132.113:~/b/
```

#### 2. VPS Server (Load & Restart)
Connect via SSH and apply the update:

```bash
# 1. Connect to VPS
ssh ubuntu@92.5.132.113

# 2. Go to project directory and sync config / compose files
cd ~/b
git pull origin main

# 3. Load the pre-built Docker image and clean up archive
gunzip -c prawko-image.tar.gz | docker load
rm prawko-image.tar.gz

# 4. Restart container using production compose configuration
docker compose -f docker-compose.prod.yml up -d

# 5. Prune dangling old images
docker image prune -f
```

---

## 3. Health & Sanity Verification

After any deployment or restart, verify system health:

```bash
# Local check on VPS
curl -s http://localhost:8000/healthz

# External check via public domain
curl -s https://prawko.lqdb.pl/healthz
```

### Expected Response:
```json
{
  "status": "ok",
  "db_ok": true,
  "questions_count": 3698
}
```

---

## 4. Logs & Observability

### Real-Time Application Logs:
```bash
# Backend application logs (HTTP requests, errors, startup diagnostics)
docker compose -f docker-compose.prod.yml logs -f prawko

# Caddy reverse proxy logs (TLS negotiation, public traffic routing)
docker compose -f docker-compose.prod.yml logs -f caddy
```

### Request Logging Output Format:
Every API and page request is logged to stdout by FastAPI middleware:
```text
[GET] /healthz -> 200 (1.42ms)
[POST] /auth/login -> 200 (112.50ms)
[GET] /media/005TRAM3org.mp4 -> 200 (15.20ms)
```

---

## 5. Rollback Procedure

If a bad migration or data anomaly occurs, restore the database from the latest verified snapshot:

### 1. Identify Available Snapshots:
```bash
ls -lh ~/b/data/backups/
```

### 2. Execute Restore Drill:
```bash
# Stop application container to prevent writes during restore
docker compose -f docker-compose.prod.yml stop prawko

# Run the restore tool (automatically verifies PRAGMA integrity_check before replacing)
python3 tools/backup_db.py --restore data/backups/prawko_YYYYMMDD_HHMMSS.sqlite

# Restart application
docker compose -f docker-compose.prod.yml start prawko
```
> [!NOTE]
> `tools/backup_db.py --restore` creates a safety backup (`data/prawko.sqlite.pre_restore_YYYYMMDD_HHMMSS`) before overwriting.

---

## 6. Security, Secrets & Key Rotation

### `.env` File Location:
The live `.env` resides at `~/b/.env` on the host and is mounted by `docker-compose.prod.yml`.

### Rotating the Registration Key (`REGISTRATION_KEY`):
To prevent new sign-ups or change the invite token:
```bash
# 1. Edit .env on the VPS
nano ~/b/.env

# Update or generate a new secret:
# REGISTRATION_KEY=new_secret_key_here

# 2. Apply change instantly
docker compose -f docker-compose.prod.yml up -d
```

### Trusted Proxy Configuration (`TRUSTED_PROXIES`):
Ensure `TRUSTED_PROXIES` is set to `127.0.0.1,172.16.0.0/12` so that client IPs behind Caddy are resolved accurately for rate limiting (`5 attempts/min`).

---

## 7. Monthly Housekeeping & Maintenance

Perform these routine checks once a month:

### 1. Verify Offsite Backups:
```bash
# Check the nightly cron sync log
tail -n 30 /var/log/rclone-backup.log
```
Expected output:
```text
Starting automated SQLite backup & sync...
Creating local backup snapshot...
Syncing '/home/ubuntu/b/data/backups' to 'remote:prawko-backups'...
Backup sync completed successfully.
```

### 2. Disk Space Usage:
```bash
df -h
```
* `media/` requires ~2.0 GB.
* `data/backups/` maintains ~50 MB (18 snapshots).
* Ensure root disk `/` has at least 5 GB free.

---

## 8. Oracle Cloud Idle-Reclamation Recovery

> [!WARNING]
> **Oracle Cloud Always Free Reclamation Policy:**
> Oracle automatically reclaims/stops Always Free compute instances if 7-day average CPU and memory utilization drops below 15%.

### Symptoms:
* SSH connection times out (`Connection refused` or `Host unreachable`).
* `https://prawko.lqdb.pl` is unresponsive.

### Recovery Steps:
1. Log in to [Oracle Cloud Console](https://cloud.oracle.com/).
2. Navigate to **Compute** $\to$ **Instances** $\to$ Select `vcn-20260816-1318` instance.
3. If status is **Stopped**, click **Start**.
4. **IP Verification**:
   * If you use an ephemeral public IP, check if the IP changed.
   * If changed, update your DNS `A` record for `prawko.lqdb.pl` to the new IP.
   * *(Recommendation: Assign a Reserved Public IP in Oracle Networking to avoid IP changes).*
5. **Verify Containers Auto-Started**:
   Containers have `restart: unless-stopped` configured and will resume automatically when the VM boots.
   ```bash
   ssh ubuntu@<VPS_IP>
   docker ps
   curl -s http://localhost:8000/healthz
   ```
