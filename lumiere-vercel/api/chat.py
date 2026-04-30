"""
=============================================================================
LUMIÈRE BEAUTY CLINIC — AI AGENT (Vercel Serverless Function)
Stack: Python | LangChain | Groq (llama-3.3-70b-versatile)
=============================================================================
File ini adalah satu-satunya serverless function di Vercel.
Endpoint: POST /api/chat

Catatan arsitektur:
  - Menggunakan create_openai_tools_agent (compatible dengan Groq's tool calling API)
  - In-memory storage (appointments hilang saat cold start) — untuk production
    ganti dengan Vercel KV, Supabase, atau Neon PostgreSQL
  - max_iterations=3 agar tidak timeout di Vercel (batas 60 detik Pro, 10 detik Hobby)
=============================================================================
"""

import os
import uuid
import json
from datetime import datetime, date
from typing import Optional
from http.server import BaseHTTPRequestHandler

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel

# =============================================================================
# IN-MEMORY STORAGE
# Catatan: Di production ganti dengan Vercel KV / Supabase
# =============================================================================
appointments_db: dict = {}

OPERATIONAL_HOURS = {
    0: ("09:00", "20:00"),
    1: ("09:00", "20:00"),
    2: ("09:00", "20:00"),
    3: ("09:00", "20:00"),
    4: ("09:00", "20:00"),
    5: ("09:00", "18:00"),
    6: None,  # Minggu TUTUP
}

LAYANAN_TERSEDIA = [
    "Konsultasi Dokter Kulit", "HydraFacial Classic", "HydraFacial Premium",
    "Chemical Peeling", "Laser Brightening", "Microneedling", "Botox",
    "Filler", "Facial Acne Treatment", "Perawatan Rambut PRP",
    "Paket Glow Starter", "Paket Brite Skin",
]

# =============================================================================
# LANGCHAIN TOOLS
# =============================================================================

@tool
def check_availability(date_str: str, time_str: str) -> str:
    """
    Cek ketersediaan slot waktu untuk booking treatment.
    Args:
        date_str: Format YYYY-MM-DD (contoh: "2025-08-15")
        time_str: Format HH:MM (contoh: "10:00")
    """
    try:
        requested_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        requested_time = datetime.strptime(time_str, "%H:%M").time()
        today = date.today()

        if requested_date < today:
            return f"Tanggal {date_str} sudah lewat. Pilih tanggal yang akan datang."

        day_of_week = requested_date.weekday()
        day_names = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
        day_name = day_names[day_of_week]

        hours = OPERATIONAL_HOURS.get(day_of_week)
        if hours is None:
            return "Maaf, klinik TUTUP setiap hari Minggu. Silakan pilih Senin–Sabtu."

        open_t = datetime.strptime(hours[0], "%H:%M").time()
        close_t = datetime.strptime(hours[1], "%H:%M").time()

        if requested_time < open_t or requested_time >= close_t:
            return (
                f"Pukul {time_str} di luar jam operasional hari {day_name}. "
                f"Jam buka: {hours[0]}–{hours[1]} WIB."
            )

        return f"✅ Slot tersedia! {day_name}, {date_str} pukul {time_str} WIB bisa dibooking."

    except ValueError as e:
        return f"Format tidak valid. Gunakan YYYY-MM-DD dan HH:MM. Detail: {str(e)}"


@tool
def create_appointment(name: str, phone: str, service: str, date_str: str, time_str: str) -> str:
    """
    Buat dan simpan jadwal appointment setelah klien konfirmasi semua data.
    Args:
        name: Nama lengkap klien
        phone: Nomor WhatsApp (format 08xx atau +628xx)
        service: Nama layanan yang dipilih
        date_str: Tanggal format YYYY-MM-DD
        time_str: Waktu format HH:MM
    """
    try:
        service_valid = any(s.lower() in service.lower() for s in LAYANAN_TERSEDIA)
        if not service_valid:
            return f"Layanan '{service}' tidak tersedia. Pilihan: {', '.join(LAYANAN_TERSEDIA)}"

        avail = check_availability.invoke({"date_str": date_str, "time_str": time_str})
        if "✅" not in avail:
            return avail

        booking_id = f"LMR-{uuid.uuid4().hex[:6].upper()}"
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        day_names = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
        formatted_date = f"{day_names[parsed_date.weekday()]}, {parsed_date.strftime('%d %B %Y')}"

        appointments_db[booking_id] = {
            "booking_id": booking_id, "name": name, "phone": phone,
            "service": service, "date": date_str, "time": time_str,
            "created_at": datetime.now().isoformat(), "status": "confirmed"
        }

        return (
            f"✅ Booking BERHASIL!\n\n"
            f"📋 No. Booking : {booking_id}\n"
            f"👤 Nama        : {name}\n"
            f"📅 Tanggal     : {formatted_date}\n"
            f"⏰ Waktu       : {time_str} WIB\n"
            f"💆 Layanan     : {service}\n"
            f"📞 WhatsApp    : {phone}\n\n"
            f"Konfirmasi akan dikirim ke WhatsApp Anda 1 hari sebelum jadwal. "
            f"Harap tiba 10 menit lebih awal ✨"
        )
    except Exception as e:
        return f"Gagal membuat booking: {str(e)}. Hubungi kami di +62 812-3456-7890."


@tool
def get_services_info(category: Optional[str] = None) -> str:
    """
    Ambil info layanan dan harga klinik.
    Args:
        category: Filter opsional — "facial", "laser", "injeksi", "rambut", "paket", "konsultasi"
    """
    services = {
        "konsultasi": [("Konsultasi Dokter Kulit", "30 menit", "Rp 250.000")],
        "facial": [
            ("HydraFacial Classic", "60 menit", "Rp 750.000"),
            ("HydraFacial Premium", "90 menit", "Rp 1.200.000"),
            ("Facial Acne Treatment", "60 menit", "Rp 600.000"),
        ],
        "laser": [
            ("Chemical Peeling", "45 menit", "Rp 500.000"),
            ("Laser Brightening", "60 menit", "Rp 1.500.000"),
            ("Microneedling", "75 menit", "Rp 1.800.000"),
        ],
        "injeksi": [
            ("Botox (per area)", "30 menit", "Rp 2.500.000"),
            ("Filler (per 1ml)", "30–45 menit", "Rp 4.000.000"),
        ],
        "rambut": [("Perawatan Rambut PRP", "90 menit", "Rp 3.000.000")],
        "paket": [
            ("Paket Glow Starter (Konsultasi + HydraFacial Classic)", "~90 menit", "Rp 950.000 (hemat Rp 50rb)"),
            ("Paket Brite Skin (Chemical Peeling + Laser Brightening)", "~105 menit", "Rp 1.850.000 (hemat Rp 150rb)"),
        ],
    }

    if category and category.lower() in services:
        items = services[category.lower()]
        result = f"Layanan '{category}':\n"
    else:
        items = [item for cat in services.values() for item in cat]
        result = "Semua layanan Lumière Beauty Clinic:\n"

    for name, duration, price in items:
        result += f"• {name} — {duration} | {price}\n"
    return result

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Kamu adalah **Lumière**, asisten AI resmi dari **Lumière Beauty Clinic**. Kamu adalah konsultan kecantikan virtual yang elegan, ramah, dan berpengetahuan luas. Berbicara hangat namun profesional — seperti resepsionis klinik premium yang benar-benar peduli dengan kebutuhan klien.

## INFORMASI KLINIK
- **Alamat**: Jl. Kemang Raya No. 88, Jakarta Selatan
- **Kontak**: +62 812-3456-7890 | info@lumierebeauty.id
- **Jam Operasional**: Senin–Jumat 09.00–20.00 WIB | Sabtu 09.00–18.00 WIB | Minggu TUTUP

## ALUR KERJA
1. Sambut klien hangat, identifikasi kebutuhan (info / rekomendasi / booking)
2. Berikan informasi atau rekomendasi yang relevan — gunakan tool get_services_info jika perlu
3. Jika klien tertarik booking: kumpulkan data secara bertahap (nama → WhatsApp → tanggal → waktu → layanan)
4. Cek ketersediaan dengan tool check_availability sebelum konfirmasi
5. Setelah klien konfirmasi ringkasan → panggil tool create_appointment
6. Sampaikan nomor booking dan instruksi selanjutnya

## BATASAN KEAMANAN
- JANGAN mendiagnosis penyakit kulit atau merekomendasikan obat/resep
- JANGAN menjanjikan hasil perawatan yang spesifik
- SELALU arahkan pertanyaan medis serius ke konsultasi dokter
- Tambahkan disclaimer: *"Untuk hasil terbaik, dikonfirmasi dulu dengan dokter kami saat konsultasi ya ✨"*

## GAYA KOMUNIKASI
- Bahasa Indonesia yang hangat dan elegan
- Gunakan emoji secara terbatas: ✨ 🌿 💆‍♀️
- Respons singkat dan padat, detail hanya jika diminta
- Jika klien komplain: empati dulu, tawarkan eskalasi ke +62 812-3456-7890"""

# =============================================================================
# AGENT FACTORY
# =============================================================================

def build_agent() -> AgentExecutor:
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",  # Model terbaik Groq untuk tool calling
        temperature=0.4,
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        max_tokens=1024,
    )

    tools = [check_availability, create_appointment, get_services_info]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm=llm, tools=tools, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=3,       # Batasi iterasi agar tidak timeout di Vercel
        handle_parsing_errors=True,
    )

# =============================================================================
# VERCEL SERVERLESS HANDLER
# Vercel memanggil class Handler dengan method do_POST / do_GET / do_OPTIONS
# =============================================================================

class handler(BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        allowed_origin = os.environ.get("ALLOWED_ORIGIN", "*")
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Preflight CORS request dari browser."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Health check."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "online",
            "service": "Lumière Beauty Clinic AI Agent",
            "model": "groq/llama-3.3-70b-versatile"
        }).encode())

    def do_POST(self):
        """Endpoint chat utama."""
        try:
            # Baca body request
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            message = data.get("message", "").strip()
            history_raw = data.get("history", [])
            session_id = data.get("session_id", "unknown")

            if not message:
                self._respond(400, {"error": "Field 'message' tidak boleh kosong."})
                return

            # Konversi history ke LangChain messages
            chat_history = []
            for msg in history_raw:
                if msg.get("role") == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))

            # Jalankan agent
            agent_executor = build_agent()
            result = agent_executor.invoke({
                "input": message,
                "chat_history": chat_history,
            })

            reply = result.get("output", "Maaf, saya tidak dapat memproses pesan Anda saat ini.")

            # Deteksi booking baru
            booking_data = None
            for booking_id, apt in appointments_db.items():
                if booking_id in reply:
                    booking_data = apt
                    break

            self._respond(200, {
                "session_id": session_id,
                "reply": reply,
                "booking_created": booking_data,
            })

        except json.JSONDecodeError:
            self._respond(400, {"error": "Request body bukan JSON yang valid."})
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            self._respond(500, {"error": "Terjadi kesalahan internal. Mohon coba lagi."})

    def _respond(self, status_code: int, payload: dict):
        """Helper: kirim JSON response."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress default HTTP logs (pakai print untuk debug)."""
        pass
