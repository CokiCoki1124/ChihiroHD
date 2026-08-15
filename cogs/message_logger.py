import discord
from discord.ext import commands

# ==========================================
# ⚠️ PENTING: GANTI DENGAN ID CHANNEL LOG ANDA
# ==========================================
LOG_CHANNEL_ID = 1536072164942549137

class MessageLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        # Abaikan jika yang dihapus adalah pesan dari bot itu sendiri
        if message.author.bot:
            return
            
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return

        embed = discord.Embed(title="🗑️ Pesan Dihapus", color=discord.Color.red())
        embed.add_field(name="Pengirim", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Isi Pesan", value=message.content or "[Hanya Gambar/Sticker]", inline=False)
        
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        # Abaikan pesan bot atau jika pesannya tidak berubah (hanya beda embed)
        if before.author.bot or before.content == after.content:
            return
            
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return

        embed = discord.Embed(title="✏️ Pesan Diedit", color=discord.Color.orange())
        embed.add_field(name="Pengirim", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Sebelum", value=before.content or "[Kosong]", inline=False)
        embed.add_field(name="Sesudah", value=after.content or "[Kosong]", inline=False)
        
        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MessageLogger(bot))
    print("✅ Cog Loaded: Message Logger (CCTV)")
