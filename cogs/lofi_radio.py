import discord
from discord.ext import commands
import yt_dlp
import asyncio
import urllib.parse
import urllib.request
import re

def is_verified():
    async def predicate(ctx):
        role_id = 1507459341526237336
        if ctx.author.guild_permissions.administrator:
            return True
        role = ctx.guild.get_role(role_id)
        if role and role in ctx.author.roles:
            return True
        raise commands.CheckFailure(f"❌ **Akses Ditolak!** Hanya member dengan tag <@&{1507459341526237336}git add .> yang memiliki izin.")
    return commands.check(predicate)

class CustomMusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc = None
        self.queue = []
        self.is_playing = False
        
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
        self.YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            # Trik Bypass: Menyamar sebagai Android agar YouTube tidak memblokir IP
            'extractor_args': {'youtube': ['player_client=android']},
            'source_address': '0.0.0.0'
        }

    async def play_next(self, ctx):
        if len(self.queue) > 0:
            self.is_playing = True
            url = self.queue[0][0]
            judul = self.queue[0][1]
            self.queue.pop(0)

            try:
                source = await discord.FFmpegOpusAudio.from_probe(url, **self.FFMPEG_OPTIONS)
                self.vc.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))
                await ctx.send(f"🎶 **Sekarang Memutar:** `{judul}`")
            except Exception as e:
                print(f"[MUSIC ERROR] {e}")
                await self.play_next(ctx) 
        else:
            self.is_playing = False
            await ctx.send("📻 Antrean habis. Bot akan tetap *stay* di Voice Channel (24/7).")

    @commands.command(name="play")
    @is_verified()
    async def play(self, ctx, *, pencarian: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Kamu harus masuk ke Voice Channel terlebih dahulu!")

        channel = ctx.author.voice.channel
        
        try:
            if self.vc is None or not self.vc.is_connected():
                self.vc = await channel.connect()
            elif self.vc.channel != channel:
                await self.vc.move_to(channel)
        except Exception as e:
            return await ctx.send("⚠️ Gagal terhubung ke Voice Channel.")

        pesan_loading = await ctx.send(f"🔍 *Mencari diam-diam:* `{pencarian}`...")

        if pencarian.startswith("http") and "spotify.com" in pencarian:
            return await pesan_loading.edit(content="❌ **Error Spotify:** Tolong ketik **Judul Lagunya** saja!")

        # 🧠 SUPER SMART SEARCH: Mencari manual lewat jalur belakang agar tidak dicegat YouTube
        if pencarian.startswith("http"):
            target_url = pencarian
        else:
            try:
                query_string = urllib.parse.urlencode({"search_query": pencarian})
                html_content = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
                search_results = re.findall(r'watch\?v=(\S{11})', html_content.read().decode())
                
                if search_results:
                    target_url = f"https://www.youtube.com/watch?v={search_results[0]}"
                else:
                    return await pesan_loading.edit(content="⚠️ **Gagal menemukan lagu di YouTube.**")
            except Exception as e:
                print(f"[URLLIB ERROR] {e}")
                return await pesan_loading.edit(content="⚠️ **Koneksi ke YouTube terputus.**")

        # Setelah dapat link rahasianya, baru masukkan ke sistem musik
        try:
            loop = asyncio.get_event_loop()
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(target_url, download=False))
                
                if 'entries' in info:
                    info = info['entries'][0]
                
                url_audio = info['url']
                judul = info.get('title', 'Lagu Ditemukan')
                
                self.queue.append((url_audio, judul))
                
                if self.is_playing:
                    await pesan_loading.edit(content=f"✅ **Berhasil dimasukkan ke antrean:** `{judul}`")
                else:
                    await pesan_loading.delete()
                    await self.play_next(ctx)

        except Exception as e:
            await pesan_loading.edit(content="⚠️ **Gagal.** YouTube menolak memberikan lagunya kepada server cloud. Silakan coba lagu lain!")
            print(f"[YTDLP ERROR] {e}")

    @commands.command(name="skip")
    @is_verified()
    async def skip(self, ctx):
        if self.vc and self.vc.is_playing():
            self.vc.stop() 
            await ctx.send("⏭️ **Lagu dilewati!**")
        else:
            await ctx.send("⚠️ Bot sedang tidak memutar apapun saat ini.")

    @commands.command(name="stop")
    @is_verified()
    async def stop(self, ctx):
        if self.vc and self.vc.is_connected():
            self.queue.clear()
            self.vc.stop()
            await self.vc.disconnect()
            self.vc = None
            self.is_playing = False
            await ctx.send("🛑 **Musik dihentikan.** Antrean dihapus dan bot keluar dari Voice Channel.")
        else:
            await ctx.send("⚠️ Bot sedang tidak berada di Voice Channel.")

    @play.error
    @skip.error
    @stop.error
    async def music_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(str(error))

async def setup(bot):
    await bot.add_cog(CustomMusicPlayer(bot))
    print("✅ Cog Loaded: 24/7 Custom Music (Super Bypass Aktif)")
