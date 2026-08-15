import discord
from discord.ext import commands
import asyncio

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reload")
    @commands.has_permissions(administrator=True)
    async def reload_cogs(self, ctx):
        embed = discord.Embed(
            title="♻️ Memproses Reload...", 
            description="Membaca ulang semua file kodingan... Tunggu sebentar!",
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        # Daftar lengkap semua file fitur Anda
        cogs_list = [
            "cogs.automod", 
            "cogs.antilink", 
            "cogs.ml_calculator", 
            "cogs.admin",
            "cogs.ticket_system",
            "cogs.message_logger",
            "cogs.help_system",
            "cogs.lofi_radio"
        ]
        
        gagal = []
        for cog in cogs_list:
            try:
                # Logika cerdas: Jika sudah ada, reload. Jika file baru, muat dari awal.
                if cog in self.bot.extensions:
                    await self.bot.reload_extension(cog)
                else:
                    await self.bot.load_extension(cog)
            except Exception as e:
                print(f"[ERROR] Gagal memuat {cog}: {e}")
                gagal.append(cog)
                
        if gagal:
            desc = f"**Peringatan!** Ada file yang error dan gagal dimuat:\n`{', '.join(gagal)}`\n*Cek terminal untuk melihat penyebab errornya.*"
            color = discord.Color.orange()
        else:
            desc = "**✅ Semua file (Radio, Ticket, Anti-Link, dll) berhasil diperbarui secara instan!**\nSistem siap digunakan sepenuhnya."
            color = discord.Color.green()

        embed_success = discord.Embed(
            title="✅ Reload Selesai!", 
            description=desc,
            color=color
        )
        await msg.edit(embed=embed_success)

    @commands.command(name="restart")
    @commands.has_permissions(administrator=True)
    async def restart_bot(self, ctx):
        embed = discord.Embed(
            title="🔄 Mematikan Sistem...", 
            description="**Bot sedang memutuskan koneksi dan dimatikan.**\n*(Script run_forever.sh akan otomatis menghidupkannya kembali dalam 3-5 detik!)*", 
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        print("[SYSTEM] Perintah !restart ditekan. Bot Log Out dengan aman...")
        
        await asyncio.sleep(1)
        
        # Cara Fiks & Paling Aman: Menutup koneksi bot. 
        # Karena di terminal Anda memakai ./run_forever.sh, saat bot tertutup, 
        # terminal akan langsung merestartnya secara otomatis tanpa nyangkut!
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
    print("✅ Cog Loaded: Admin (Reload & Restart Fiks)")
