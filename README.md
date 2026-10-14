# Prox AI Agent — starter bez Dockera

Sadrži web sučelje s lozinkom, spremljeni chat, konfiguraciju OpenAI-kompatibilnog AI endpointa, Git clone/pull i strogo ograničenu lokalnu read-only dijagnostiku.

## Instalacija
1. Napravi Debian 12/13 ili Ubuntu Server LXC. Preporučeni početak: 2 CPU, 4 GB RAM, 60 GB disk.
2. Kopiraj/raspakiraj mapu `proxmox-ai-agent` u LXC.
3. `cd proxmox-ai-agent && chmod +x setup.sh && bash setup.sh`
4. Otvori `http://IP_ADRESA_LXC:8088` s pouzdane LAN mreže i prijavi se lozinkom koju postavi instalacija.
5. U Postavkama postavi API base URL, naziv modela i API ključ ako ga provider traži. Za lokalni Ollama endpoint obično se koristi `http://IP_OLLAMA:11434/v1`.

## Važno — opseg
Ovo je funkcionalan početni web agent, ne još puni autonomni coding agent. Model nije uključen. Git clone i ručni `git pull --ff-only` rade, a terminal dopušta samo hostname, uptime, free -h, df -h i whoami. Još nema SSH pristupa drugim Proxmox čvorovima, uređivanja koda ili build runnera. To treba dodati zasebno uz ograničene ovlasti i potvrde za rizične radnje.

Ne izlaži port 8088 izravno internetu. Koristi LAN/VPN i kasnije HTTPS reverse proxy. Privatni Git repozitoriji zahtijevaju sigurno konfigurirane Git/SSH vjerodajnice na LXC-u. API ključ se sprema u lokalnu SQLite bazu; ograniči pristup LXC-u i napravi backup podataka.

Provjera: `systemctl status proxmox-ai-agent`, `journalctl -u proxmox-ai-agent -n 100 --no-pager`, `curl http://127.0.0.1:8088/health`.
