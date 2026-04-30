/**
 * LUMIÈRE BEAUTY CLINIC — AI Agent Backend
 * Vercel Serverless Function (Node.js)
 * POST /api/chat | GET /api/chat
 */

const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = "llama-3.3-70b-versatile";

const JAM_OPERASIONAL = {
  0: { buka: "09:00", tutup: "20:00" },
  1: { buka: "09:00", tutup: "20:00" },
  2: { buka: "09:00", tutup: "20:00" },
  3: { buka: "09:00", tutup: "20:00" },
  4: { buka: "09:00", tutup: "20:00" },
  5: { buka: "09:00", tutup: "18:00" },
  6: null,
};

const HARI = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"];
const appointmentsDB = {};

const SYSTEM_PROMPT = `Kamu adalah Lumiere, asisten AI resmi dari Lumiere Beauty Clinic. Kamu adalah konsultan kecantikan virtual yang elegan, ramah, dan berpengetahuan luas. Berbicara hangat namun profesional.

## INFORMASI KLINIK
- Alamat: Jl. Kemang Raya No. 88, Jakarta Selatan
- Kontak: +62 812-3456-7890 | info@lumierebeauty.id
- Jam Operasional: Senin-Jumat 09.00-20.00 WIB | Sabtu 09.00-18.00 WIB | Minggu TUTUP

## LAYANAN & HARGA
- Konsultasi Dokter Kulit - 30 menit - Rp 250.000
- HydraFacial Classic - 60 menit - Rp 750.000
- HydraFacial Premium - 90 menit - Rp 1.200.000
- Chemical Peeling - 45 menit - Rp 500.000
- Laser Brightening - 60 menit - Rp 1.500.000
- Microneedling - 75 menit - Rp 1.800.000
- Botox per area - 30 menit - Rp 2.500.000
- Filler per 1ml - 30-45 menit - Rp 4.000.000
- Facial Acne Treatment - 60 menit - Rp 600.000
- Perawatan Rambut PRP - 90 menit - Rp 3.000.000
- Paket Glow Starter Konsultasi plus HydraFacial Classic - Rp 950.000 hemat Rp 50.000
- Paket Brite Skin Chemical Peeling plus Laser Brightening - Rp 1.850.000 hemat Rp 150.000

## ALUR KERJA
1. Sambut klien hangat, identifikasi kebutuhan
2. Berikan informasi atau rekomendasi yang relevan
3. Jika klien ingin booking: kumpulkan bertahap nama lengkap, nomor WhatsApp, tanggal format YYYY-MM-DD, waktu format HH:MM, layanan
4. Tampilkan ringkasan dan minta persetujuan klien
5. Setelah klien setuju panggil function create_appointment

## BATASAN KEAMANAN
- JANGAN mendiagnosis penyakit kulit atau merekomendasikan obat
- JANGAN menjanjikan hasil perawatan yang spesifik
- Arahkan pertanyaan medis serius ke konsultasi dokter

## GAYA KOMUNIKASI
- Bahasa Indonesia yang hangat dan elegan
- Gunakan emoji terbatas
- Respons singkat dan padat`;

const TOOLS = [
  {
    type: "function",
    function: {
      name: "check_availability",
      description: "Cek apakah tanggal dan waktu tertentu tersedia untuk booking.",
      parameters: {
        type: "object",
        properties: {
          date_str: { type: "string", description: "Tanggal format YYYY-MM-DD" },
          time_str: { type: "string", description: "Waktu format HH:MM" }
        },
        required: ["date_str", "time_str"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "create_appointment",
      description: "Buat dan simpan jadwal appointment baru setelah klien konfirmasi semua data.",
      parameters: {
        type: "object",
        properties: {
          name:     { type: "string", description: "Nama lengkap klien" },
          phone:    { type: "string", description: "Nomor WhatsApp aktif" },
          service:  { type: "string", description: "Nama layanan yang dipilih" },
          date_str: { type: "string", description: "Tanggal format YYYY-MM-DD" },
          time_str: { type: "string", description: "Waktu format HH:MM" }
        },
        required: ["name", "phone", "service", "date_str", "time_str"]
      }
    }
  }
];

function checkAvailability(date_str, time_str) {
  try {
    const today = new Date();
    today.setHours(0,0,0,0);
    const requestedDay = new Date(date_str + "T00:00:00");
    if (requestedDay < today) return "Tanggal " + date_str + " sudah lewat. Pilih tanggal yang akan datang.";

    const jsDay = requestedDay.getDay();
    const dayIdx = jsDay === 0 ? 6 : jsDay - 1;
    const dayName = HARI[dayIdx];
    const hours = JAM_OPERASIONAL[dayIdx];

    if (!hours) return "Maaf, klinik TUTUP setiap hari Minggu. Silakan pilih Senin-Sabtu.";

    const parts = time_str.split(":");
    const reqMinutes = parseInt(parts[0]) * 60 + parseInt(parts[1]);
    const openParts = hours.buka.split(":");
    const closeParts = hours.tutup.split(":");
    const openMinutes = parseInt(openParts[0]) * 60 + parseInt(openParts[1]);
    const closeMinutes = parseInt(closeParts[0]) * 60 + parseInt(closeParts[1]);

    if (reqMinutes < openMinutes || reqMinutes >= closeMinutes) {
      return "Pukul " + time_str + " di luar jam operasional hari " + dayName + ". Jam buka: " + hours.buka + "-" + hours.tutup + " WIB.";
    }

    return "Slot tersedia! Hari " + dayName + ", " + date_str + " pukul " + time_str + " WIB bisa dibooking.";
  } catch(e) {
    return "Error: " + e.message;
  }
}

function createAppointment(name, phone, service, date_str, time_str) {
  try {
    const availCheck = checkAvailability(date_str, time_str);
    if (!availCheck.startsWith("Slot tersedia")) return availCheck;

    const bookingId = "LMR-" + Math.random().toString(36).slice(2,8).toUpperCase();
    const d = new Date(date_str + "T00:00:00");
    const jsDay = d.getDay();
    const dayIdx = jsDay === 0 ? 6 : jsDay - 1;
    const dayName = HARI[dayIdx];

    appointmentsDB[bookingId] = { bookingId, name, phone, service, date: date_str, time: time_str, createdAt: new Date().toISOString(), status: "confirmed" };

    return "Booking BERHASIL!\n\nNo. Booking: " + bookingId + "\nNama: " + name + "\nTanggal: " + dayName + " " + date_str + "\nWaktu: " + time_str + " WIB\nLayanan: " + service + "\nWhatsApp: " + phone + "\n\nKonfirmasi akan dikirim ke WhatsApp Anda 1 hari sebelum jadwal. Harap tiba 10 menit lebih awal.";
  } catch(e) {
    return "Gagal membuat booking: " + e.message;
  }
}

function executeTool(name, args) {
  if (name === "check_availability") return checkAvailability(args.date_str, args.time_str);
  if (name === "create_appointment") return createAppointment(args.name, args.phone, args.service, args.date_str, args.time_str);
  return "Tool tidak ditemukan.";
}

async function runAgent(messages) {
  const groqKey = process.env.GROQ_API_KEY;
  if (!groqKey) throw new Error("GROQ_API_KEY tidak ditemukan.");

  for (let i = 0; i < 5; i++) {
    const response = await fetch(GROQ_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + groqKey
      },
      body: JSON.stringify({
        model: MODEL,
        messages: messages,
        tools: TOOLS,
        tool_choice: "auto",
        max_tokens: 1024,
        temperature: 0.4
      })
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error("Groq API error " + response.status + ": " + err);
    }

    const data = await response.json();
    const assistantMsg = data.choices[0].message;
    messages.push(assistantMsg);

    if (!assistantMsg.tool_calls || assistantMsg.tool_calls.length === 0) {
      return assistantMsg.content;
    }

    for (const toolCall of assistantMsg.tool_calls) {
      const toolArgs = JSON.parse(toolCall.function.arguments);
      const toolResult = executeTool(toolCall.function.name, toolArgs);
      messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: toolResult
      });
    }
  }

  return "Maaf, saya tidak dapat menyelesaikan permintaan Anda. Silakan coba lagi.";
}

export default async function handler(req, res) {
  const allowedOrigin = process.env.ALLOWED_ORIGIN || "*";
  res.setHeader("Access-Control-Allow-Origin", allowedOrigin);
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();

  if (req.method === "GET") {
    return res.status(200).json({ status: "online", service: "Lumiere Beauty Clinic AI Agent", model: MODEL });
  }

  if (req.method === "POST") {
    try {
      const { message, history = [], session_id } = req.body;
      if (!message || !message.trim()) return res.status(400).json({ error: "Message kosong." });

      const messages = [{ role: "system", content: SYSTEM_PROMPT }];
      for (const msg of history) {
        if (msg.role === "user" || msg.role === "assistant") {
          messages.push({ role: msg.role, content: msg.content });
        }
      }
      messages.push({ role: "user", content: message.trim() });

      const reply = await runAgent(messages);

      let bookingCreated = null;
      for (const [id, apt] of Object.entries(appointmentsDB)) {
        if (reply.includes(id)) { bookingCreated = apt; break; }
      }

      return res.status(200).json({ session_id, reply, booking_created: bookingCreated });
    } catch (error) {
      console.error("[ERROR]", error.message);
      return res.status(500).json({ error: "Terjadi kesalahan internal: " + error.message });
    }
  }

  return res.status(405).json({ error: "Method not allowed." });
}
