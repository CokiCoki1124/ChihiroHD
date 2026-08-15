import discord
from discord.ext import commands
import re
import datetime

# ==========================================
# DAFTAR WEBSITE AMAN (WHITELIST FINAL)
# ==========================================
ALLOWED_DOMAINS = [
    # 🎵 Musik, Streaming & Hiburan
    "spotify.com", "open.spotify.com", "soundcloud.com", "music.apple.com", 
    "joox.com", "resso.com", "netflix.com", "primevideo.com", "disneyplus.com", 
    "viu.com", "iq.com", "bilibili.tv", "twitch.tv", "crunchyroll.com",

    # 💎 WEB TOP-UP GAME
    "codashop.com", "unipin.com", "itemku.com", "lapakgaming.com",
    "kiosgamer.co.id", "vcgamers.com", "jollymax.com", "kachishop.com",
    "duniagames.co.id", "coda.shop", "garuda-voucher.id",

    # 📱 Sosial Media, Chat & Komunitas
    "youtube.com", "youtu.be",
    "instagram.com", "tiktok.com", "vt.tiktok.com", "t.tiktok.com",
    "twitter.com", "x.com", "fxtwitter.com", "vxtwitter.com",
    "facebook.com", "fb.com", "fb.watch", "m.facebook.com",
    "reddit.com", "redd.it", "whatsapp.com", "wa.me", "telegram.org", "t.me",
    "discord.com", "discord.gg", "discordapp.com", "discordapp.net", 
    "media.discordapp.net", "cdn.discordapp.com", "discord.media",

    # 🎮 Gaming, Store & Komunitas Game
    "roblox.com", "minecraft.net", "mojang.com",
    "steampowered.com", "steamcommunity.com", "store.steampowered.com",
    "epicgames.com", "xbox.com", "playstation.com", "nintendo.com",
    "hoyoverse.com", "genshin.mihoyo.com", "mobilelegends.com", "riotgames.com",

    # 🛍️ E-Commerce / Belanja & Marketplace
    "shopee.co.id", "shopee.id", "tokopedia.com", "tokopedia.link",
    "lazada.co.id", "blibli.com", "bukalapak.com", "amazon.com", "amazon.co.id",

    # 🖼️ Hosting Gambar, GIF & Desain
    "tenor.com", "giphy.com", "gfycat.com", "imgur.com", 
    "prnt.sc", "gyazo.com", "imgbb.com", "canva.com", "pinterest.co.id", "pinterest.com",

    # 💻 Tools, Tech, Edukasi & Google
    "github.com", "replit.com", "chatgpt.com", "openai.com", "gemini.google.com",
    "google.com", "google.co.id", "drive.google.com", "docs.google.com", "forms.gle",
    "wikipedia.org", "yahoo.com", "bing.com", "microsoft.com"
]

class AntiLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}

    def contains_bad_link(self, text):
        text_lower = text.lower()
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_lower)
        
        if not urls:
            return False

        for url in urls:
            is_allowed = False
            for domain in ALLOWED_DOMAINS:
                if domain in url:
                    is_allowed = True
                    break
            
            if not is_allowed:
                return True
                
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        if message.guild:
            if message.author.id == message.guild.owner_id:
                return
            if getattr(message.author, 'guild_permissions', None) and message.author.guild_permissions.administrator:
                return

        if self.contains_bad_link(message.content):
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            user_id = message.author.id
            self.warnings[user_id] = self.warnings.get(user_id, 0) + 1
            sp_count = self.warnings[user_id]
            
            try:
                if sp_count == 1:
                    warning_msg = await message.channel.send(
                        f"⚠️ **[SP 1]** {message.author.mention}, Link tersebut tidak ada di daftar situs aman server. Pesan **dihapus**!\nHati-hati, jangan ulangi lagi ya."
                    )
                    await warning_msg.delete(delay=10)
                    
                elif sp_count == 2:
                    duration = datetime.timedelta(minutes=5)
                    await message.author.timeout(duration, reason="SP 2: Mengirim link tak dikenal")
                    warning_msg = await message.channel.send(
                        f"⛔ **[SP 2]** {message.author.mention} di-**Timeout 5 Menit** karena mengulangi kirim link di luar daftar aman!"
                    )
                    await warning_msg.delete(delay=15)

                elif sp_count >= 3:
                    duration = datetime.timedelta(weeks=1)
                    await message.author.timeout(duration, reason="SP 3: Mengirim link ilegal berulang")
                    await message.channel.send(
                        f"🚨 **[SP 3 - SANKSI BERAT]** {message.author.mention} di-**Timeout selama 1 Minggu** Weehh ada orang gila kirim link sesad {message.guild.default_role}, jangan ditemenin"
                    )
                    self.warnings[user_id] = 0
            except discord.Forbidden:
                await message.channel.send(f"❌ Gagal Timeout {message.author.mention}. Pangkat Bot kurang tinggi di server!")

async def setup(bot):
    await bot.add_cog(AntiLink(bot))
    print("✅ Cog Loaded: AntiLink (Custom SP 3 & 1 Minggu Timeout Aktif!)")
