# 🌿 Lumière Beauty Clinic — AI Agent (Groq + Vercel)

## 📁 Struktur Proyek

```
lumiere-vercel/
├── vercel.json           ← Konfigurasi Vercel (routing, build, env)
├── requirements.txt      ← Dependensi Python untuk Vercel
├── api/
│   └── chat.py           ← Serverless function (POST /api/chat, GET /api/chat)
└── public/
    └── index.html        ← Frontend chat widget
```

---

## 🚀 Deploy ke Vercel — Step by Step

### Prasyarat
- Akun [Vercel](https://vercel.com) (gratis)
- Akun [Groq](https://console.groq.com) (gratis, dapat API key gratis)
- [Git](https://git-scm.com) terinstall di komputer Anda

---

### Langkah 1 — Dapatkan Groq API Key
1. Buka https://console.groq.com
2. Login / daftar akun
3. Klik **"API Keys"** di sidebar → **"Create API Key"**
4. Salin key (format: `gsk_...`) — simpan, tidak bisa dilihat lagi

---

### Langkah 2 — Upload ke GitHub
```bash
# Di folder lumiere-vercel/
git init
git add .
git commit -m "Initial commit: Lumiere Beauty Clinic AI Agent"

# Buat repo baru di GitHub (github.com → New Repository)
# Lalu:
git remote add origin https://github.com/USERNAME/NAMA-REPO.git
git push -u origin main
```

---

### Langkah 3 — Deploy di Vercel
1. Buka https://vercel.com → **"Add New Project"**
2. Import repo GitHub yang baru dibuat
3. Vercel otomatis mendeteksi konfigurasi dari `vercel.json`
4. Klik **"Deploy"** — tunggu ~2 menit

---

### Langkah 4 — Set Environment Variables
Setelah deploy pertama selesai:
1. Di dashboard Vercel → pilih project Anda
2. Buka tab **"Settings"** → **"Environment Variables"**
3. Tambahkan dua variabel berikut:

| Name | Value |
|------|-------|
| `GROQ_API_KEY` | `gsk_xxxxxxxxxxxxxxxxxxxx` (key dari Groq) |
| `ALLOWED_ORIGIN` | `https://nama-project.vercel.app` (URL Vercel Anda) |

4. Klik **"Save"**
5. Buka tab **"Deployments"** → klik **"Redeploy"** (agar env vars aktif)

---

### Langkah 5 — Verifikasi
1. Buka URL Vercel Anda: `https://nama-project.vercel.app`
2. Klik bubble chat di pojok kanan bawah
3. Coba tanya: *"Apa saja layanan kalian?"*
4. Cek health check API: `https://nama-project.vercel.app/api/chat` (GET → harus balik JSON status online)

---

## ⚠️ Catatan Penting

### Batas Vercel Hobby (gratis)
- **Timeout**: 10 detik per request
- **Solusi**: Gunakan pertanyaan singkat. Jika sering timeout → upgrade ke Vercel Pro (60 detik) atau gunakan Railway/Render untuk backend

### Model Groq yang Digunakan
```
llama-3.3-70b-versatile
```
Model ini gratis di Groq dengan rate limit yang generous. Alternatif jika rate limit:
- `llama-3.1-8b-instant` (lebih cepat, lebih hemat)
- `mixtral-8x7b-32768` (lebih panjang context)

Ubah di `api/chat.py` baris:
```python
model="llama-3.3-70b-versatile",
```

### Storage Booking
Saat ini menggunakan in-memory dict — **data hilang saat Vercel cold start**. Untuk production:
1. Daftar [Vercel KV](https://vercel.com/storage/kv) (Redis, gratis tier tersedia)
2. Atau gunakan [Supabase](https://supabase.com) (PostgreSQL gratis)

---

## 🔧 Custom Domain (Opsional)
1. Vercel Dashboard → Settings → Domains
2. Tambahkan domain Anda (misal: `chat.lumierebeauty.id`)
3. Update DNS di registrar domain Anda sesuai instruksi Vercel
4. Update env var `ALLOWED_ORIGIN` ke domain baru
