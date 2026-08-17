import discord
from discord.ext import commands

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reload")
    @commands.has_permissions(administrator=True)
    async def reload_cogs(self, ctx):
        """Mereload semua cog bot tanpa harus restart Termux"""
        msg = await ctx.send("🔄 Sedang mereload semua fitur bot...")
        
        # Daftar lengkap semua file fitur aktif Anda (Tanpa lofi radio, ada AI Chat)
        cogs_list = [
            "cogs.automod",
            "cogs.antilink",
            "cogs.ml_calculator",
            "cogs.admin",
            "cogs.ticket_system",
            "cogs.message_logger",
            "cogs.ai_chat"
        ]
        
        gagal = []
        for cog in cogs_list:
            try:
                if cog in self.bot.extensions:
                    await self.bot.reload_extension(cog)
                else:
                    await self.bot.load_extension(cog)
            except Exception as e:
                print(f"[ERROR] Gagal memuat {cog}: {e}")
                gagal.append(cog)

        if gagal:
            desc = f"⚠️ **Peringatan!** Ada file yang gagal direload: `{', '.join(gagal)}`"
            color = discord.Color.orange()
        else:
            desc = "✅ **Semua file fitur (AutoMod, Antilink, Kalkulator ML, Admin, Tiket, Logger, AI Chat) berhasil direload dengan sempurna!**"
            color = discord.Color.green()

        embed_success = discord.Embed(
            title="🔄 Reload Selesai!",
            description=desc,
            color=color
        )
        await msg.edit(content=None, embed=embed_success)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
    print("✅ Cog Loaded: Admin Commands")
