#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Pokreni kao root: bash setup.sh'; exit 1; }
APP="$(cd "$(dirname "$0")" && pwd)"; DATA=/var/lib/proxmox-ai-agent; U=proxmox-ai-agent
apt-get update; DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git curl ca-certificates
id "$U" >/dev/null 2>&1 || useradd --system --home "$DATA" --create-home --shell /usr/sbin/nologin "$U"
install -d -o "$U" -g "$U" "$DATA"
python3 -m venv "$APP/.venv"; "$APP/.venv/bin/pip" install --upgrade pip; "$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
read -r -s -p 'Postavi jedinstvenu administratorsku lozinku: ' PW; echo; [[ -n "$PW" ]] || exit 1
printf 'AGENT_SECRET_KEY=%s\nAGENT_ADMIN_PASSWORD=%s\nAGENT_DATA_DIR=%s\n' "$SECRET" "$PW" "$DATA" > /etc/proxmox-ai-agent.env; chmod 600 /etc/proxmox-ai-agent.env
cat > /etc/systemd/system/proxmox-ai-agent.service <<EOF
[Unit]
Description=Proxmox AI Agent Web UI
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=$U
Group=$U
WorkingDirectory=$APP
EnvironmentFile=/etc/proxmox-ai-agent.env
ExecStart=$APP/.venv/bin/gunicorn --workers 2 --timeout 150 --bind 0.0.0.0:8088 app:app
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$DATA
[Install]
WantedBy=multi-user.target
EOF
chown -R "$U:$U" "$APP"; systemctl daemon-reload; systemctl enable --now proxmox-ai-agent
systemctl --no-pager --full status proxmox-ai-agent || true
echo 'Otvori http://IP_ADRESA_LXC:8088'; echo 'Logovi: journalctl -u proxmox-ai-agent -f'
