import discord
from discord.ext import commands
import re

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # ==========================================
        # KAMUS KASAR ULTIMATE (FULL + SINGKATAN)
        # ==========================================
        kata_kotor_mentah = [
            # 1. KATA LENGKAP (INDO & DAERAH)
            "anjing", "bangsat", "kontol", "memek", "jembut", 
            "goblok", "tolol", "babi", "peler", "ngentot", 
            "bajingan", "pantek", "pukimak", "lonte", "keparat", "kimak",
            "jancok", "jancuk", "telaso", "sundala", "tempik",
            
            # 2. SINGKATAN & TYPO ALAY (YANG SERING DIPAKAI)
            "ajg", "anjg", "anj", "njir", "njing", "njeng", "asu", 
            "bgst", "bgsd", "bgsat", "bngst",
            "kntl", "kntol", "kontl", "knt",
            "mmk", "memk", "mk",
            "gblk", "gblok", "goblk", "gblg",
            "tll", "tlol",
            "plr", 
            "ngtd", "ngntd", "ntod", "ntot", "ngntot", 
            "bjgn", "bjg", 
            "lnt", "lonc", 
            "pkmk", "kmk", 
            "pntk",
            "jnck", "jncuk", "cukk", "ncuk", "ancuk",
            "bdok", "bdoh",
            
            # 3. INGGRIS
            "fuck", "shit", "bitch", "asshole", "dick", 
            "cunt", "motherfucker", "bastard", "slut", "whore", 
            "pussy", "nigger", "nigga", "cock", "dickhead", "faggot", "retard"
        ]
        
        # Mampatkan huruf ganda di kamus (contoh: aassuu -> asu)
        self.bad_words = [re.sub(r'(.)\1+', r'\1', kata) for kata in kata_kotor_mentah]

    def bersihkan_teks(self, teks: str) -> str:
        """Mesin Cuci Teks Anti-Bypass Level Dewa"""
        # 1. Hancurkan Besar-Kecil
        teks = teks.lower()
        
        # 2. Terjemahkan Simbol/Angka ke Huruf
        pengganti = {
            '@': 'a', '4': 'a',
            '1': 'i', '!': 'i', '|': 'i',
            '0': 'o',
            '3': 'e',
            '5': 's', '$': 's',
            '7': 't',
            '8': 'b',
            '9': 'g'
        }
        for sandi, huruf in pengganti.items():
            teks = teks.replace(sandi, huruf)
        
        # 3. Hapus Spasi & Tanda Baca (k o n t o l -> kontol)
        teks = re.sub(r'[^a-z]', '', teks)
        
        # 4. Hapus spam huruf panjang (aaaajjjjgggg -> ajg)
        teks = re.sub(r'(.)\1+', r'\1', teks)
        
        return teks

    async def periksa_dan_hukum(self, message):
        # Abaikan bot dan Admin (Admin Bebas!)
        if message.author.bot:
            return
        if getattr(message.author, 'guild_permissions', None) and message.author.guild_permissions.administrator:
            return

        teks_bersih = self.bersihkan_teks(message.content)
        
        terdeteksi = False
        for kata_kotor in self.bad_words:
            if kata_kotor in teks_bersih:
                terdeteksi = True
                break
                
        if terdeteksi:
            try:
                await message.delete()
                peringatan = await message.channel.send(
                    f"🛑 **DIBLOKIR!** {message.author.mention}, pesan kamu otomatis dihapus karena terdeteksi menggunakan kata-kata terlarang/kasar. Tolong jaga ketikanmu!"
                )
                await peringatan.delete(delay=5)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.periksa_dan_hukum(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.periksa_dan_hukum(after)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
    print("✅ Cog Loaded: AutoMod (Kamus Singkatan & Daerah Aktif!)")
