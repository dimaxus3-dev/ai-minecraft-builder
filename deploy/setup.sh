#!/usr/bin/env bash
# Запуск на VDS:  cd /opt/hack && sudo bash deploy/setup.sh
set -euo pipefail
APP=/opt/hack
cd "$APP"

[ -f .env ] || { echo "Нет $APP/.env: скопируй deploy/.env.vds.example в .env, заполни и запусти снова"; exit 1; }
grep -q "ЗАМЕНИ" .env && { echo "В .env остались значения ЗАМЕНИ — заполни их"; exit 1; }

echo "[1/5] пакеты"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip rsync curl
python3 -c 'import sys; assert sys.version_info >= (3, 10), "нужен Python 3.10+, тут " + sys.version.split()[0]'

echo "[2/5] пользователь и папки"
id hack >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin hack
mkdir -p "$APP/data"

echo "[3/5] окружение Python (может занять пару минут)"
python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r backend/requirements.txt \
  || ./venv/bin/pip install -q fastapi "uvicorn[standard]" pydantic requests python-dotenv websockets python-multipart numpy scipy pillow

echo "[4/5] служба"
chmod 600 .env
chown -R hack:hack "$APP"
cp deploy/hack.service /etc/systemd/system/hack.service
systemctl daemon-reload
systemctl enable --now hack
systemctl restart hack

echo "[5/5] проверка"
sleep 4
systemctl is-active hack
curl -s -o /dev/null -w "сервер отвечает локально: HTTP %{http_code}\n" http://127.0.0.1:8000/api/requests
echo "дальше: настрой Caddy (deploy/Caddyfile) и проверь https-адрес с телефона"
