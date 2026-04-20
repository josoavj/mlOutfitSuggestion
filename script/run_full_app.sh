#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: script/run_full_app.sh [options]

Lance l'application complète :
- serveur FastAPI
- interface web de test sur /ui

Options:
  --host <host>       Hôte d'écoute (défaut : 127.0.0.1)
  --port <port>       Port d'écoute (défaut : 8000)
  --no-reload         Désactive le mode reload
  --open-browser      Ouvre automatiquement l'interface dans le navigateur
  --python <path>     Chemin explicite de l'interpréteur Python
  -h, --help          Affiche cette aide

Exemples:
  script/run_full_app.sh
  script/run_full_app.sh --host 0.0.0.0 --port 8080
  script/run_full_app.sh --open-browser
EOF
}

HOST="127.0.0.1"
PORT="8000"
RELOAD="true"
OPEN_BROWSER="false"
PYTHON_BIN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --no-reload)
      RELOAD="false"
      shift
      ;;
    --open-browser)
      OPEN_BROWSER="true"
      shift
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Option inconnue: $1" >&2
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "/home/shadowcraft/.pyenv/bin/python" ]]; then
    PYTHON_BIN="/home/shadowcraft/.pyenv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "Aucun interpréteur Python détecté." >&2
    exit 1
  fi
fi

if [[ ! -f "src/outfit_ml/api.py" ]]; then
  echo "Fichier src/outfit_ml/api.py introuvable. Lance le script depuis le dépôt." >&2
  exit 1
fi

RELOAD_ARGS=()
if [[ "$RELOAD" == "true" ]]; then
  RELOAD_ARGS+=(--reload)
fi

APP_URL="http://${HOST}:${PORT}/ui"

echo "Démarrage du serveur FastAPI..."
echo "Python: $PYTHON_BIN"
echo "Interface de test: $APP_URL"

if [[ "$OPEN_BROWSER" == "true" ]]; then
  (
    sleep 2
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$APP_URL" >/dev/null 2>&1 || true
    fi
  ) &
fi

exec "$PYTHON_BIN" -m uvicorn src.outfit_ml.api:app --host "$HOST" --port "$PORT" "${RELOAD_ARGS[@]}"
