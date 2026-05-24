#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║   WhatsApp Bot - Auto Deploy Vercel          ║
║   Dibuat untuk Termux (Python + neonize)     ║
║   Prefix: .  |  Pairing Code Auth           ║
╚══════════════════════════════════════════════╝
"""

import os
import sys
import re
import json
import time
import hashlib
import zipfile
import tempfile
import requests
from pathlib import Path
from config import (
    VERCEL_TOKEN,
    PREFIX,
    BOT_NAME,
    OWNER_NAME,
    SESSION_NAME
)

# ─── Cek library ───────────────────────────────────────────────────────────────
try:
    from neonize.client import NewClient
    from neonize.events import (
        MessageEv,
        ConnectedEv,
        DisconnectedEv,
    )
    pass  # imports selesai
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Coba: pip install --upgrade neonize")
    sys.exit(1)

# ─── Warna Terminal ─────────────────────────────────────────────────────────────
R  = "\033[91m"   # Merah
G  = "\033[92m"   # Hijau
Y  = "\033[93m"   # Kuning
B  = "\033[94m"   # Biru
C  = "\033[96m"   # Cyan
W  = "\033[97m"   # Putih
RS = "\033[0m"    # Reset
BD = "\033[1m"    # Bold

# ─── Banner ─────────────────────────────────────────────────────────────────────
def banner():
    os.system("clear")
    print(f"""
{C}{BD}╔══════════════════════════════════════════╗
║  ██╗   ██╗███████╗██████╗  ██████╗██████╗ ║
║  ██║   ██║██╔════╝██╔══██╗██╔════╝██╔══██╗║
║  ██║   ██║█████╗  ██████╔╝██║     ██████╔╝║
║  ╚██╗ ██╔╝██╔══╝  ██╔══██╗██║     ██╔══██╗║
║   ╚████╔╝ ███████╗██║  ██║╚██████╗██████╔╝║
║    ╚═══╝  ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═════╝ ║
║                                            ║
║     BOT  {W}WhatsApp Auto Deploy Vercel{C}     ║
║           Powered by {W}Python + neonize{C}     ║
╚══════════════════════════════════════════╝{RS}
{Y}  Prefix : {W}{PREFIX}   |   Bot : {W}{BOT_NAME}   |   Owner : {W}{OWNER_NAME}{RS}
""")

# ─── Menu Text ──────────────────────────────────────────────────────────────────
MENU_TEXT = f"""
╔══════════════════════════════╗
║  🤖 *{BOT_NAME}* - Daftar Menu  ║
╚══════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 *GENERAL*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ *{PREFIX}menu*
  └ Tampilkan semua menu

▸ *{PREFIX}ping*
  └ Cek apakah bot aktif

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 *VERCEL DEPLOY*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ *{PREFIX}deploy*
  └ Deploy file ke Vercel
  └ Kirim file + caption .deploy
  └ Support: .html .zip .json .css

▸ *{PREFIX}status*
  └ Status deployment terakhir

▸ *{PREFIX}list*
  └ List 5 deployment terakhir

▸ *{PREFIX}delete [id]*
  └ Hapus deployment by ID

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 *CARA DEPLOY:*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Siapkan file .html atau .zip
2️⃣ Kirim file di WhatsApp
3️⃣ Isi caption: *{PREFIX}deploy*
4️⃣ Tunggu URL dari bot 🎉

Untuk .zip: pastikan ada
*index.html* di dalam folder

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Bot by {OWNER_NAME} • {BOT_NAME}_
"""

# ─── Vercel API Class ────────────────────────────────────────────────────────────
class VercelAPI:
    """Handler untuk semua operasi Vercel API"""

    BASE = "https://api.vercel.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    # ── Upload file ke Vercel storage ──────────────────────────────────────────
    def _upload_file(self, content: bytes, filename: str) -> dict | None:
        sha  = hashlib.sha1(content).hexdigest()
        size = len(content)

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/octet-stream",
            "x-vercel-digest": sha,
            "Content-Length": str(size)
        }

        resp = requests.post(
            f"{self.BASE}/v2/files",
            headers=headers,
            data=content,
            timeout=30
        )

        if resp.status_code in (200, 201, 409):  # 409 = sudah ada, tidak apa
            return {"file": filename, "sha": sha, "size": size}

        print(f"{R}[Upload Error] {filename}: {resp.status_code} {resp.text[:200]}{RS}")
        return None

    # ── Buat deployment ────────────────────────────────────────────────────────
    def _create_deployment(self, name: str, files: list, framework: str = None) -> dict:
        payload = {
            "name": name,
            "files": files,
            "target": "production",
            "projectSettings": {
                "framework": framework,
                "outputDirectory": None
            }
        }

        resp = requests.post(
            f"{self.BASE}/v13/deployments",
            headers=self.headers,
            json=payload,
            timeout=60
        )

        data = resp.json()

        if resp.status_code in (200, 201):
            return {
                "ok": True,
                "id":     data.get("id", "-"),
                "url":    f"https://{data.get('url', '')}",
                "name":   data.get("name", name),
                "state":  data.get("readyState", "BUILDING"),
                "alias":  data.get("alias", [])
            }

        err_msg = data.get("error", {}).get("message", resp.text[:300])
        return {"ok": False, "error": err_msg}

    # ── Deploy HTML tunggal ────────────────────────────────────────────────────
    def deploy_html(self, html_bytes: bytes, project_name: str) -> dict:
        file_meta = self._upload_file(html_bytes, "index.html")
        if not file_meta:
            return {"ok": False, "error": "Gagal upload index.html"}
        return self._create_deployment(project_name, [file_meta])

    # ── Deploy ZIP ─────────────────────────────────────────────────────────────
    def deploy_zip(self, zip_bytes: bytes, project_name: str) -> dict:
        files_meta = []

        try:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(zip_bytes)
                tmp_path = tmp.name

            with zipfile.ZipFile(tmp_path, "r") as zf:
                names = [n for n in zf.namelist() if not n.endswith("/")]

                if not names:
                    return {"ok": False, "error": "ZIP kosong atau hanya folder"}

                for name in names:
                    raw = zf.read(name)
                    # Hapus prefix folder pertama supaya path lebih bersih
                    clean_name = "/".join(name.split("/")[1:]) if "/" in name else name
                    if not clean_name:
                        continue

                    meta = self._upload_file(raw, clean_name)
                    if meta:
                        files_meta.append(meta)

        finally:
            os.unlink(tmp_path)

        if not files_meta:
            return {"ok": False, "error": "Tidak ada file berhasil diupload dari ZIP"}

        return self._create_deployment(project_name, files_meta)

    # ── Deploy JSON (dibungkus HTML) ───────────────────────────────────────────
    def deploy_json(self, json_bytes: bytes, project_name: str) -> dict:
        try:
            parsed = json.loads(json_bytes)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            formatted = json_bytes.decode("utf-8", errors="replace")

        html = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>JSON Viewer – {project_name}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0d1117;color:#e6edf3;font-family:'JetBrains Mono',monospace;min-height:100vh;padding:2rem}}
    h1{{color:#58a6ff;font-size:1.2rem;margin-bottom:1rem;border-bottom:1px solid #30363d;padding-bottom:.5rem}}
    pre{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.5rem;overflow:auto;
         font-size:.85rem;line-height:1.7;white-space:pre-wrap;word-break:break-word}}
    .badge{{display:inline-block;background:#238636;color:#fff;font-size:.7rem;
            padding:.2rem .6rem;border-radius:20px;margin-left:.5rem}}
  </style>
</head>
<body>
  <h1>📦 JSON Data <span class="badge">Deployed via VercBot</span></h1>
  <pre>{formatted}</pre>
</body>
</html>"""

        return self.deploy_html(html.encode("utf-8"), project_name)

    # ── List deployments ───────────────────────────────────────────────────────
    def list_deployments(self, limit: int = 5) -> list:
        resp = requests.get(
            f"{self.BASE}/v6/deployments?limit={limit}",
            headers=self.headers,
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json().get("deployments", [])
        return []

    # ── Status deployment ──────────────────────────────────────────────────────
    def get_status(self, deploy_id: str) -> dict:
        resp = requests.get(
            f"{self.BASE}/v13/deployments/{deploy_id}",
            headers=self.headers,
            timeout=15
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "state": d.get("readyState", "UNKNOWN"),
                "url":   f"https://{d.get('url', '')}",
                "name":  d.get("name", "-"),
                "created": d.get("createdAt", 0)
            }
        return {"state": "ERROR", "url": "", "name": "-"}

    # ── Hapus deployment ───────────────────────────────────────────────────────
    def delete_deployment(self, deploy_id: str) -> bool:
        resp = requests.delete(
            f"{self.BASE}/v13/deployments/{deploy_id}",
            headers=self.headers,
            timeout=15
        )
        return resp.status_code in (200, 204)

    # ── Cek apakah token valid ─────────────────────────────────────────────────
    def validate_token(self) -> bool:
        resp = requests.get(
            f"{self.BASE}/v2/user",
            headers=self.headers,
            timeout=10
        )
        return resp.status_code == 200


# ─── Helper ──────────────────────────────────────────────────────────────────────
def make_project_name(filename: str) -> str:
    """Buat nama project Vercel dari nama file"""
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    suffix = str(int(time.time()))[-5:]
    name = f"{stem or 'deploy'}-{suffix}"
    return name[:52]  # Vercel max 52 karakter

def state_emoji(state: str) -> str:
    return {
        "READY":    "✅",
        "BUILDING": "🔄",
        "ERROR":    "❌",
        "CANCELED": "🚫",
        "QUEUED":   "⏳",
        "UNKNOWN":  "❓"
    }.get(state.upper(), "❓")

def log(level: str, msg: str):
    ts = time.strftime("%H:%M:%S")
    colors = {"INFO": C, "OK": G, "WARN": Y, "ERR": R, "CMD": B}
    col = colors.get(level, W)
    print(f"{col}[{ts}][{level}] {msg}{RS}")


# ─── Inisialisasi ────────────────────────────────────────────────────────────────
vercel       = VercelAPI(VERCEL_TOKEN)
client       = NewClient(SESSION_NAME)
last_deploy  = {}   # Simpan data deployment terakhir


# ─── Event Handlers ──────────────────────────────────────────────────────────────
@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    log("OK", f"Bot {BOT_NAME} berhasil terhubung ke WhatsApp! ✓")

@client.event(DisconnectedEv)
def on_disconnected(_: NewClient, __: DisconnectedEv):
    log("WARN", "Bot terputus dari WhatsApp. Mencoba reconnect...")


@client.event(MessageEv)
async def on_message(c: NewClient, msg: MessageEv):
    global last_deploy

    # ── Ambil info dasar pesan ─────────────────────────────────────────────────
    chat      = msg.Info.MessageSource.Chat
    from_me   = msg.Info.MessageSource.IsFromMe
    sender    = str(msg.Info.MessageSource.Sender)
    message   = msg.Message

    if from_me:
        return  # Abaikan pesan diri sendiri

    # ── Ekstrak teks dan dokumen (kompatibel neonize 0.3.x) ──────────────────
    text         = ""
    has_doc      = False
    doc_filename = ""
    doc_bytes    = b""

    try:
        if message.HasField("conversation"):
            text = message.conversation

        elif message.HasField("extendedTextMessage"):
            text = message.extendedTextMessage.text or ""

        elif message.HasField("documentMessage"):
            doc_info     = message.documentMessage
            doc_filename = doc_info.fileName or "file"
            text         = (doc_info.caption or "").strip()
            has_doc      = True
            try:
                doc_bytes = await c.download(message)
            except Exception as e:
                log("ERR", f"Gagal download dokumen: {e}")
                return

        elif message.HasField("documentWithCaptionMessage"):
            inner        = message.documentWithCaptionMessage.message.documentMessage
            doc_filename = inner.fileName or "file"
            text         = (inner.caption or "").strip()
            has_doc      = True
            try:
                doc_bytes = await c.download(message.documentWithCaptionMessage.message)
            except Exception as e:
                log("ERR", f"Gagal download dok captioned: {e}")
                return

        else:
            return

    except Exception:
        text = getattr(message, "conversation", "") or ""
        if not text:
            return

    # ── Cek prefix ────────────────────────────────────────────────────────────
    if not text.startswith(PREFIX):
        return

    raw_cmd = text[len(PREFIX):].strip()
    parts   = raw_cmd.split(None, 1)

    if not parts:
        return

    cmd  = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    log("CMD", f"[{sender}] {PREFIX}{cmd} {args}")

    # ── Kirim pesan helper ────────────────────────────────────────────────────
    async def reply(txt: str):
        await c.send_message(chat, txt)

    # ═══════════════════════════════════════════════════════════════════════════
    # .menu — Tampilkan semua perintah
    # ═══════════════════════════════════════════════════════════════════════════
    if cmd == "menu":
        await reply(MENU_TEXT)

    # ═══════════════════════════════════════════════════════════════════════════
    # .ping — Cek bot aktif
    # ═══════════════════════════════════════════════════════════════════════════
    elif cmd == "ping":
        await reply(f"🏓 *Pong!*\n_{BOT_NAME} aktif dan siap deploy_ 🚀")

    # ═══════════════════════════════════════════════════════════════════════════
    # .deploy — Auto deploy file ke Vercel
    # ═══════════════════════════════════════════════════════════════════════════
    elif cmd == "deploy":
        if not has_doc:
            await reply(
                f"❌ *Tidak ada file terdeteksi!*\n\n"
                f"📌 *Cara penggunaan:*\n"
                f"Kirim file dengan caption `{PREFIX}deploy`\n\n"
                f"📂 *Format yang didukung:*\n"
                f"  • `.html` / `.htm` — Halaman web\n"
                f"  • `.zip` — Project folder\n"
                f"  • `.json` — Data JSON\n\n"
                f"💡 Pastikan ZIP berisi `index.html`"
            )
            return

        ext = Path(doc_filename).suffix.lower()
        supported_exts = {".html", ".htm", ".zip", ".json"}

        if ext not in supported_exts:
            await reply(
                f"❌ Format `{ext}` *tidak didukung*\n\n"
                f"Format yang didukung:\n"
                f"`.html` `.htm` `.zip` `.json`"
            )
            return

        project_name = make_project_name(doc_filename)
        size_kb      = len(doc_bytes) / 1024

        await reply(
            f"⏳ *Sedang memproses deploy...*\n\n"
            f"📁 File    : `{doc_filename}`\n"
            f"📦 Ukuran  : `{size_kb:.1f} KB`\n"
            f"🏷️ Project : `{project_name}`\n\n"
            f"_Mohon tunggu, sedang upload ke Vercel..._"
        )

        result = {}
        try:
            if ext in (".html", ".htm"):
                result = vercel.deploy_html(doc_bytes, project_name)

            elif ext == ".zip":
                result = vercel.deploy_zip(doc_bytes, project_name)

            elif ext == ".json":
                result = vercel.deploy_json(doc_bytes, project_name)

        except Exception as e:
            log("ERR", f"Exception saat deploy: {e}")
            await reply(f"❌ *Error tidak terduga:*\n`{str(e)}`")
            return

        if result.get("ok"):
            last_deploy = result
            aliases = result.get("alias", [])
            alias_line = f"\n🔗 Alias : {aliases[0]}" if aliases else ""

            await reply(
                f"✅ *Deploy Berhasil!* 🎉\n"
                f"{'━'*30}\n"
                f"📁 File    : `{doc_filename}`\n"
                f"🏷️ Project : `{result['name']}`\n"
                f"🌐 URL     : {result['url']}{alias_line}\n"
                f"📊 Status  : `{result['state']}`\n"
                f"🔑 ID      : `{result['id'][:20]}...`\n"
                f"{'━'*30}\n"
                f"_Ketik `{PREFIX}status` untuk cek status_"
            )
            log("OK", f"Deploy sukses: {result['url']}")
        else:
            await reply(
                f"❌ *Deploy Gagal!*\n\n"
                f"🔴 Error: `{result.get('error', 'Unknown error')}`\n\n"
                f"_Pastikan VERCEL_TOKEN valid dan file benar_"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # .status — Status deployment terakhir
    # ═══════════════════════════════════════════════════════════════════════════
    elif cmd == "status":
        if not last_deploy:
            await reply(
                f"ℹ️ *Belum ada deployment*\n\n"
                f"Gunakan `{PREFIX}deploy` untuk mulai deploy file"
            )
            return

        dep_id = last_deploy.get("id", "")
        info   = vercel.get_status(dep_id)
        emoji  = state_emoji(info["state"])

        await reply(
            f"📊 *Status Deployment Terakhir*\n"
            f"{'━'*30}\n"
            f"{emoji} Status  : *{info['state']}*\n"
            f"🏷️ Project : `{info['name']}`\n"
            f"🌐 URL     : {info['url']}\n"
            f"🔑 ID      : `{dep_id[:20]}...`\n"
            f"{'━'*30}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # .list — List deployment terakhir
    # ═══════════════════════════════════════════════════════════════════════════
    elif cmd == "list":
        await reply("⏳ _Mengambil data deployment..._")
        deployments = vercel.list_deployments(5)

        if not deployments:
            await reply("ℹ️ Tidak ada deployment ditemukan di akun ini")
            return

        lines = [f"📋 *5 Deployment Terakhir*\n{'━'*30}"]
        for i, dep in enumerate(deployments, 1):
            state = dep.get("state", "UNKNOWN")
            emoji = state_emoji(state)
            name  = dep.get("name", "-")
            url   = dep.get("url", "-")
            dep_id = dep.get("uid", dep.get("id", "-"))[:12]

            lines.append(
                f"\n*{i}. {emoji} {name}*\n"
                f"   🌐 https://{url}\n"
                f"   🔑 `{dep_id}...`"
            )

        lines.append(f"\n{'━'*30}\n_Gunakan `{PREFIX}delete [id]` untuk hapus_")
        await reply("\n".join(lines))

    # ═══════════════════════════════════════════════════════════════════════════
    # .delete [id] — Hapus deployment
    # ═══════════════════════════════════════════════════════════════════════════
    elif cmd == "delete":
        if not args:
            await reply(
                f"❌ *Format salah!*\n\n"
                f"Penggunaan: `{PREFIX}delete [deployment-id]`\n"
                f"Contoh: `{PREFIX}delete dpl_abc123`\n\n"
                f"_Gunakan `{PREFIX}list` untuk lihat ID deployment_"
            )
            return

        dep_id = args.strip()
        await reply(f"🗑️ _Menghapus deployment `{dep_id}`..._")
        success = vercel.delete_deployment(dep_id)

        if success:
            await reply(f"✅ Deployment `{dep_id}` berhasil dihapus!")
        else:
            await reply(
                f"❌ Gagal menghapus deployment\n"
                f"Pastikan ID benar dan token memiliki izin"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # Command tidak dikenal
    # ═══════════════════════════════════════════════════════════════════════════
    else:
        await reply(
            f"❓ Perintah `{PREFIX}{cmd}` tidak dikenal\n\n"
            f"Ketik `{PREFIX}menu` untuk melihat semua perintah"
        )


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    banner()

    # Validasi token Vercel
    if VERCEL_TOKEN in ("", "YOUR_VERCEL_TOKEN_HERE"):
        print(f"{R}[ERROR] VERCEL_TOKEN belum diisi di config.py!{RS}")
        print(f"{Y}  1. Buka https://vercel.com/account/tokens")
        print(f"  2. Buat token baru")
        print(f"  3. Tempel di config.py pada VERCEL_TOKEN{RS}\n")
        sys.exit(1)

    print(f"{Y}⚡ Validasi Vercel Token...{RS}")
    if not vercel.validate_token():
        print(f"{R}[ERROR] Vercel Token tidak valid atau expired!{RS}")
        sys.exit(1)
    print(f"{G}✓ Vercel Token valid{RS}\n")

    # Input nomor HP untuk pairing
    print(f"{C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RS}")
    print(f"{W}📱 Masukkan nomor WhatsApp untuk Pairing Code{RS}")
    print(f"{Y}   Format: 628XXXXXXXXXX (tanpa + atau spasi){RS}")
    print(f"{C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RS}")
    phone = input(f"{W}  Nomor HP > {RS}").strip()

    # Normalisasi nomor
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    if not phone.startswith("62"):
        phone = "62" + phone

    print(f"\n{Y}📲 Meminta Pairing Code untuk {phone}...{RS}")

    # ── Cari method pairing yang tersedia di versi ini ─────────────────────
    pairing_methods = [m for m in dir(client) if "pair" in m.lower()]
    print(f"{C}[DEBUG] Pairing methods: {pairing_methods}{RS}")

    code = None
    try:
        # neonize 0.3.x — PairPhone(phone, show_push_notification)
        if hasattr(client, "PairPhone"):
            code = client.PairPhone(phone, True)
        elif hasattr(client, "pair_phone"):
            code = client.pair_phone(phone)
        elif hasattr(client, "get_pairing_code"):
            code = client.get_pairing_code(phone)
        elif hasattr(client, "request_pairing_code"):
            code = client.request_pairing_code(phone)
        else:
            # Fallback: connect dulu, pairing lewat QR/manual
            print(f"{Y}⚠️  Pairing code tidak didukung di versi ini.")
            print(f"   Bot akan connect, scan QR jika muncul.{RS}\n")
            client.connect()
            return

        if code:
            print(f"\n{G}{'━'*42}{RS}")
            print(f"{W}{BD}  🔑 PAIRING CODE : {G}{BD}{code}{RS}")
            print(f"{G}{'━'*42}{RS}")
            print(f"{Y}  1. Buka WhatsApp di HP")
            print(f"  2. Setelan → Perangkat Tertaut")
            print(f"  3. Tautkan Perangkat → Tautkan dengan Nomor HP")
            print(f"  4. Masukkan kode di atas{RS}\n")
        else:
            print(f"{R}[ERROR] Pairing code kosong!{RS}")
            sys.exit(1)

    except Exception as e:
        print(f"{R}[ERROR] Gagal pairing: {e}{RS}")
        print(f"{Y}Method tersedia: {[m for m in dir(client) if not m.startswith('_')]}{RS}")
        sys.exit(1)

    print(f"{C}⏳ Menunggu konfirmasi pairing...{RS}\n")

    try:
        client.connect()
    except KeyboardInterrupt:
        print(f"\n{Y}Bot dihentikan. Sampai jumpa!{RS}")
    except Exception as e:
        print(f"\n{R}[FATAL] {e}{RS}")
        sys.exit(1)


if __name__ == "__main__":
    main()
