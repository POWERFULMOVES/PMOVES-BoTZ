#!/usr/bin/env bash
set -euo pipefail
WHITELIST_KEYS=(
  SLACK_CHANNEL DOCS_LOG_CHANNEL SLACK_BOT_TOKEN DISCORD_WEBHOOK_URL TEAMS_WEBHOOK_URL
  TS_AUTHKEY HOSTINGER_API_KEY HOSTINGER_PROJECT_ID HOSTINGER_ENV
  N8N_RUNNERS_AUTH_TOKEN
  HIRAG_URL MEILI_URL MEILI_MASTER_KEY QDRANT_URL NEO4J_URL NEO4J_USER NEO4J_PASSWORD
  MINIO_ENDPOINT MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_SECURE
  PLAYWRIGHT_BASE_URL
)
ENV_OUT=".env"; BACKUP_TS="$(date +%Y%m%d-%H%M%S)"; SCAN_DIR=""; FROM_FILE=""; INTERACTIVE=1
usage(){ cat <<'H'; exit 0; H
setup_env.sh
  --scan <dir>      Scan directory for keys.info / *.env / *.txt and merge
  --from-file <f>   Import KEY=VALUE lines from file
  --help            This help
H
}
merge_kv(){ local l="$1"; local k="${l%%=*}"; local v="${l#*=}"; v="${v%"}"; v="${v#"}"; v="${v%'}"; v="${v#'}"; if grep -qE "^[# ]*${k}=" .env.new 2>/dev/null; then sed -i.bak -E "s|^[# ]*${k}=.*|${k}=${v}|" .env.new; else echo "${k}=${v}" >> .env.new; fi; }
import_file(){ local f="$1"; [ -f "$f" ] || return 0; while IFS= read -r line; do line="${line#export }"; line="$(echo "$line" | tr -d ' ')"; [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*=.+$ ]] || continue; k="${line%%=*}"; for allow in "${WHITELIST_KEYS[@]}"; do [[ "$k" == "$allow" ]] && { merge_kv "$line"; break; }; done; done < "$f"; }
scan_dir(){ local d="$1"; find "$d" -maxdepth 2 -type f \( -iname "keys.info" -o -iname "*.env" -o -iname ".env" -o -iname "*.env.local" -o -iname "*.txt" \) | while read -r f; do import_file "$f"; done; }
prompt_var(){ local k="$1"; local s="$2"; local cur=""; cur="$(grep -E "^${k}=" .env.new 2>/dev/null | head -n1 | cut -d= -f2- || true)"; [ -n "$cur" ] && echo "${k} (Enter keeps current):" || echo "${k}:"; if [ "$s" = "1" ]; then read -s -p "> " input; echo; else read -p "> " input; fi; [ -n "${input:-}" ] && merge_kv "${k}=${input}"; }
while [[ $# -gt 0 ]]; do case "$1" in --scan) SCAN_DIR="${2:-.}"; INTERACTIVE=0; shift 2;; --from-file) FROM_FILE="$2"; INTERACTIVE=0; shift 2;; --help|-h) usage;; *) echo "Unknown arg: $1"; usage;; esac; done
[ -f "$ENV_OUT" ] && { cp "$ENV_OUT" ".env.${BACKUP_TS}.bak"; cp "$ENV_OUT" .env.new; } || touch .env.new
[ -n "$FROM_FILE" ] && import_file "$FROM_FILE"; [ -n "$SCAN_DIR" ] && scan_dir "$SCAN_DIR"
if [ "$INTERACTIVE" = "1" ]; then
  echo "Interactive mode — press Enter to keep current."
  for k in SLACK_CHANNEL DOCS_LOG_CHANNEL HOSTINGER_ENV PLAYWRIGHT_BASE_URL HIRAG_URL MEILI_URL QDRANT_URL NEO4J_URL MINIO_ENDPOINT MINIO_SECURE; do prompt_var "$k" 0; done
  for k in SLACK_BOT_TOKEN DISCORD_WEBHOOK_URL TEAMS_WEBHOOK_URL TS_AUTHKEY HOSTINGER_API_KEY HOSTINGER_PROJECT_ID N8N_RUNNERS_AUTH_TOKEN MEILI_MASTER_KEY NEO4J_USER NEO4J_PASSWORD MINIO_ACCESS_KEY MINIO_SECRET_KEY; do if [[ "$k" == "NEO4J_USER" ]]; then prompt_var "$k" 0; else prompt_var "$k" 1; fi; done
fi
mv .env.new "$ENV_OUT"; echo "Wrote $ENV_OUT (backup: .env.${BACKUP_TS}.bak if existed)."