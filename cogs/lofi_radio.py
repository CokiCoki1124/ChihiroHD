import asyncio
import random
import re
import discord
import yt_dlp
from discord.ext import commands

VERIFIED_ROLE_ID = 1507459341526237336

def is_verified():
    """Hanya member dengan role verifikasi (atau admin) yang boleh pakai command musik."""
    async def predicate(ctx: commands.Context):
        if ctx.author.guild_permissions.administrator:
            return True
        role = ctx.guild.get_role(VERIFIED_ROLE_ID)
        if role and role in ctx.author.roles:
            return True
        raise commands.CheckFailure(
            f"❌ **Akses Ditolak!** Hanya member dengan tag <@&{VERIFIED_ROLE_ID}> "
            f"yang memiliki izin untuk memakai command ini."
        )
    return commands.check(predicate)

class GuildPlayer:
    def __init__(self):
        self.vc = None
        self.queue = []
        self.is_playing = False
        self.autoplay = False
        self.history = []
        self.last_title = None
        self.text_channel = None
        self.lock = asyncio.Lock()

class MusicPlayer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}

        # PENINGKATAN AUDIO: Memaksimalkan kualitas suara (Lofi Radio Quality)
        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -b:a 192k",
        }
        
        # PENINGKATAN PENCARIAN: Filter yt-dlp yang lebih agresif
        self.YDL_OPTIONS = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch5",
            "source_address": "0.0.0.0",
        }

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    @staticmethod
    def clean_title(title: str) -> str:
        title = re.sub(r"\(.*?\)|\[.*?\]", "", title)
        title = re.sub(r"(official|video|lyrics?|audio|mv|hd|4k|full|version)", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s+", " ", title).strip()
        return title or title

    async def resolve_track(self, query: str) -> dict:
        loop = asyncio.get_event_loop()
        
        if "open.spotify.com" in query:
            title = await loop.run_in_executor(None, self._scrape_spotify_title, query)
            if not title:
                raise ValueError("Tidak bisa membaca judul dari link Spotify itu. Coba ketik judul lagunya saja.")
            search_query = f"ytsearch1:{title}"
        elif query.startswith("http://") or query.startswith("https://"):
            search_query = query
        else:
            search_query = f"ytsearch1:{query}"

        info = await self._extract(search_query, loop)
        if info is None and search_query.startswith("ytsearch1:"):
            info = await self._extract(search_query.replace("ytsearch1:", "scsearch1:"), loop)
        
        if info is None:
            raise ValueError("Lagu tidak ditemukan di sumber manapun.")
            
        if "entries" in info:
            entries = [e for e in info["entries"] if e]
            if not entries:
                raise ValueError("Lagu tidak ditemukan.")
            info = entries[0]
            
        return {
            "url": info["url"],
            "title": info.get("title", "Lagu Tidak Diketahui"),
            "webpage_url": info.get("webpage_url", info["url"]),
        }

    async def _extract(self, query: str, loop) -> dict:
        try:
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                return await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        except Exception as e:
            print(f"[YTDLP ERROR] {e}")
            return None

    @staticmethod
    def _scrape_spotify_title(url: str) -> str:
        try:
            import requests
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            match = re.search(r"<title>(.*?)</title>", resp.text)
            if match:
                return match.group(1).split("| Spotify")[0].replace("song and lyrics by", "-").strip()
        except Exception as e:
            print(f"[SPOTIFY SCRAPE ERROR] {e}")
        return None

    async def find_autoplay_track(self, gp: GuildPlayer) -> dict:
        if not gp.last_title:
            return None
        base_query = self.clean_title(gp.last_title)
        loop = asyncio.get_event_loop()
        info = await self._extract(f"ytsearch10:{base_query}", loop)
        
        if not info or "entries" not in info:
            return None
            
        candidates = [e for e in info["entries"] if e and e.get("webpage_url") not in gp.history]
        if not candidates:
            candidates = [e for e in info["entries"] if e]
        if not candidates:
            return None
            
        chosen = random.choice(candidates)
        return {
            "url": chosen["url"],
            "title": chosen.get("title", "Lagu Tidak Diketahui"),
            "webpage_url": chosen.get("webpage_url", chosen["url"]),
        }

    async def play_next(self, ctx_or_guild):
        guild = ctx_or_guild.guild if isinstance(ctx_or_guild, commands.Context) else ctx_or_guild
        gp = self.get_player(guild.id)
        
        async with gp.lock:
            if gp.vc is None or not gp.vc.is_connected():
                gp.is_playing = False
                return
                
            track = None
            if gp.queue:
                track = gp.queue.pop(0)
            elif gp.autoplay:
                track = await self.find_autoplay_track(gp)
            
            if track is None:
                gp.is_playing = False
                if gp.text_channel and not gp.autoplay:
                    await gp.text_channel.send("📻 Antrean habis. Bot tetap *stay* di Voice Channel (24/7).")
                return

            gp.is_playing = True
            gp.last_title = track["title"]
            gp.history.append(track["webpage_url"])
            gp.history = gp.history[-30:]

            try:
                source = await discord.FFmpegOpusAudio.from_probe(track["url"], **self.FFMPEG_OPTIONS)
            except Exception:
                self.bot.loop.create_task(self.play_next(guild))
                return

            gp.vc.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(guild)))
            if gp.text_channel:
                tag = "🔁 (Autoplay)" if gp.autoplay and not gp.queue else "🎶"
                await gp.text_channel.send(f"{tag} **Sekarang Memutar:** `{track['title']}`")

    @commands.command(name="play")
    @is_verified()
    async def play(self, ctx: commands.Context, *, pencarian: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Kamu harus masuk ke Voice Channel terlebih dahulu!")
            
        gp = self.get_player(ctx.guild.id)
        gp.text_channel = ctx.channel
        channel = ctx.author.voice.channel
        
        try:
            if gp.vc is None or not gp.vc.is_connected():
                # SUPER BYPASS: Timeout panjang (60 detik) agar Termux punya cukup waktu loading
                gp.vc = await channel.connect(timeout=60.0, reconnect=True)
            elif gp.vc.channel != channel:
                await gp.vc.move_to(channel)
        except Exception as e:
            print(f"[VOICE CONNECT ERROR] {e}")
            return await ctx.send(f"⚠️ **Gagal terhubung ke Voice Channel.**\n*Error Detail:* `{e}`")

        pesan_loading = await ctx.send(f"🔍 *Mencari:* `{pencarian}`...")
        
        try:
            track = await self.resolve_track(pencarian)
            gp.queue.append(track)
            
            if gp.is_playing:
                await pesan_loading.edit(content=f"✅ **Ditambahkan ke antrean:** `{track['title']}`")
            else:
                await pesan_loading.delete()
                await self.play_next(ctx)
        except Exception as e:
            await pesan_loading.edit(content="⚠️ **Gagal menemukan lagu.** Coba dengan kata kunci yang lebih spesifik atau gunakan link.")

    @commands.command(name="autoplay")
    @is_verified()
    async def autoplay(self, ctx: commands.Context, mode: str = None):
        gp = self.get_player(ctx.guild.id)
        gp.text_channel = ctx.channel

        if mode is None:
            gp.autoplay = not gp.autoplay
        elif mode.lower() in ("on", "aktif", "nyala"):
            gp.autoplay = True
        elif mode.lower() in ("off", "mati", "nonaktif"):
            gp.autoplay = False
        else:
            return await ctx.send("Gunakan `!autoplay on` atau `!autoplay off`.")

        status = "✅ **AKTIF** 📻 (bot akan terus cari & mutar lagu senada otomatis, seperti radio)" if gp.autoplay else "❌ **NONAKTIF**"
        await ctx.send(f"🔁 Mode Autoplay sekarang: {status}")

        if gp.autoplay and gp.vc and gp.vc.is_connected() and not gp.is_playing:
            await self.play_next(ctx)

    @commands.command(name="skip")
    @is_verified()
    async def skip(self, ctx: commands.Context):
        gp = self.get_player(ctx.guild.id)
        if gp.vc and gp.vc.is_playing():
            gp.vc.stop()
            await ctx.send("⏭️ **Lagu dilewati!**")
        else:
            await ctx.send("⚠️ Bot sedang tidak memutar apapun.")

    @commands.command(name="stop")
    @is_verified()
    async def stop(self, ctx: commands.Context):
        gp = self.get_player(ctx.guild.id)
        gp.queue.clear()
        gp.autoplay = False
        if gp.vc and gp.vc.is_playing():
            gp.vc.stop()
        gp.is_playing = False
        await ctx.send("🛑 **Musik dihentikan & antrean dikosongkan.** Bot tetap di Voice Channel.")

    @commands.command(name="leave")
    @is_verified()
    async def leave(self, ctx: commands.Context):
        gp = self.get_player(ctx.guild.id)
        if gp.vc and gp.vc.is_connected():
            gp.queue.clear()
            gp.autoplay = False
            gp.is_playing = False
            await gp.vc.disconnect()
            gp.vc = None
            await ctx.send("👋 Bot keluar dari Voice Channel.")
        else:
            await ctx.send("⚠️ Bot sedang tidak berada di Voice Channel.")

    @commands.command(name="queue")
    @is_verified()
    async def show_queue(self, ctx: commands.Context):
        gp = self.get_player(ctx.guild.id)
        if not gp.queue:
            return await ctx.send("📭 Antrean kosong.")
        lines = [f"{i + 1}. {t['title']}" for i, t in enumerate(gp.queue[:10])]
        extra = f"\n...dan {len(gp.queue) - 10} lagu lainnya" if len(gp.queue) > 10 else ""
        await ctx.send("📜 **Antrean saat ini:**\n" + "\n".join(lines) + extra)

    @commands.command(name="np")
    @is_verified()
    async def now_playing(self, ctx: commands.Context):
        gp = self.get_player(ctx.guild.id)
        if gp.is_playing and gp.last_title:
            await ctx.send(f"🎧 **Sedang diputar:** `{gp.last_title}`")
        else:
            await ctx.send("⚠️ Tidak ada lagu yang sedang diputar.")

    @play.error
    @skip.error
    @stop.error
    @autoplay.error
    @leave.error
    @show_queue.error
    @now_playing.error
    async def music_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(str(error))

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicPlayer(bot))
    print("✅ Cog Loaded: Lofi Radio Music (HQ Audio + Super Anti-Timeout VC)")
