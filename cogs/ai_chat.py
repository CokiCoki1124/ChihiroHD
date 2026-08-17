import discord
from discord.ext import commands
import os
import aiohttp

# Mengambil Kunci Otak AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class SmartAIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.history = {} # Menyimpan memori chat per-channel
        self.max_history = 10 # Mengingat 10 tanya-jawab terakhir

    @commands.Cog.listener()
    async def on_message(self, message):
        # Jangan balas pesan bot lain / diri sendiri
        if message.author.bot:
            return

        # Bot merespons jika di channel "tanya-chihiro" ATAU jika di-mention
        if message.channel.name == "tanya-chihiro" or self.bot.user in message.mentions:
            # Bersihkan teks dari format mention (biar AI gak bingung)
            teks = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if not teks:
                teks = "Halo Chihiro!"
            await self.proses_ai(message, teks)

    @commands.command(name="ask")
    async def ask_ai(self, ctx, *, pertanyaan: str):
        """Tanya apapun ke AI ChihiroHD"""
        await self.proses_ai(ctx.message, pertanyaan)
        
    @commands.command(name="resetai")
    async def reset_ai(self, ctx):
        """Menghapus ingatan bot di channel ini (Mulai topik baru)"""
        self.history[ctx.channel.id] = []
        await ctx.send("🧹 **Wusshhh!** Ingatan Chihiro di channel ini sudah dihapus. Mari mulai obrolan baru!")

    async def proses_ai(self, message, teks):
        if not GEMINI_API_KEY:
            return await message.channel.send("⚠️ **Otak AI belum dipasang!** Developer harus menyuntikkan `GEMINI_API_KEY`.")

        channel_id = message.channel.id
        # Buat ruang memori baru jika channel ini belum pernah ngobrol
        if channel_id not in self.history:
            self.history[channel_id] = []

        async with message.channel.typing():
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
                headers = {'Content-Type': 'application/json'}
                
                # Masukkan chat user ke memori
                self.history[channel_id].append({"role": "user", "parts": [{"text": teks}]})
                
                # Sifat / Kepribadian Bot yang ditanamkan di akar AI
                kepribadian = (
                    "Kamu adalah ChihiroHD, bot Discord asisten server yang super pintar, ramah, dan asyik. "
                    "Kamu diciptakan oleh Coki. Bahasamu santai, gaul, kekinian, tapi tetap sopan. "
                    "Gunakan sapaan 'aku' dan 'kamu'. Gunakan emoji agar obrolan terasa hidup. "
                    "Format jawabanmu agar rapi dan mudah dibaca (gunakan bold/italic jika perlu). "
                    "Anggap user yang mengajakmu ngobrol sebagai teman baikmu."
                )
                
                # Struktur Data untuk dikirim ke Google (Membawa sejarah chat)
                payload = {
                    "systemInstruction": {"parts": [{"text": kepribadian}]},
                    "contents": self.history[channel_id]
                }

                # JALUR NINJA (Tanpa pydantic/rust/maturin yang bikin error di Termux)
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            jawaban = data['candidates'][0]['content']['parts'][0]['text']
                            
                            # Simpan jawaban bot ke memori agar ingatannya nyambung
                            self.history[channel_id].append({"role": "model", "parts": [{"text": jawaban}]})
                            
                            # Cukur memori kalau sudah kepanjangan biar tidak error (Maks 20 chat bergantian)
                            if len(self.history[channel_id]) > self.max_history * 2:
                                self.history[channel_id] = self.history[channel_id][-self.max_history * 2:]
                                
                        else:
                            error_text = await resp.text()
                            print(f"[AI ERROR] HTTP {resp.status}: {error_text}")
                            self.history[channel_id].pop() # Hapus ingatan yg gagal
                            return await message.reply("Maaf, otak Chihiro lagi nge-lag parah nih. Coba tanya lagi bentar ya! 😵‍💫")
                
                # Mengirim jawaban (Potong jadi pesan bersambung jika di atas batas 2000 huruf Discord)
                if len(jawaban) > 2000:
                    chunks = [jawaban[i:i+1990] for i in range(0, len(jawaban), 1990)]
                    for chunk in chunks:
                        await message.reply(chunk)
                else:
                    await message.reply(jawaban)
                
            except Exception as e:
                print(f"[AI ERROR EXCEPTION] {e}")
                await message.reply("Waduh, Chihiro agak pusing. Coba lagi nanti ya! 😵")

async def setup(bot):
    await bot.add_cog(SmartAIChat(bot))
    print("✅ Cog Loaded: Smart AI Chatbot V2 (Punya Ingatan & Super Gaul!)")
