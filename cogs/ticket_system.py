import discord
from discord.ext import commands
import asyncio

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Tutup Tiket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Menutup dan menghapus tiket dalam 3 detik...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Buka Tiket", style=discord.ButtonStyle.primary, emoji="📩", custom_id="btn_open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        user = interaction.user
        
        # 1. CEK ANTI-SPAM: Apakah user sudah punya tiket aktif?
        nama_channel_dicari = f"ticket-{user.name.lower()}"
        existing_channel = discord.utils.get(guild.text_channels, name=nama_channel_dicari)
        
        if existing_channel:
            await interaction.followup.send(
                f"❌ **Gagal!** Kamu masih memiliki tiket aktif di {existing_channel.mention}.\nTolong selesaikan atau tunggu sampai tiket tersebut ditutup oleh Admin/Moderator sebelum membuka tiket baru.",
                ephemeral=True
            )
            return

        # 2. ATUR HAK AKSES (PRIVAT)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 3. ATUR POSISI DI BAWAH CHANNEL PANEL
        current_channel = interaction.channel
        target_position = current_channel.position + 1
        
        # Membuat channel baru
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}", 
            overwrites=overwrites,
            position=target_position,
            category=current_channel.category
        )
        
        # 4. EMBED BERSIH TANPA TAG DI LUAR
        embed = discord.Embed(
            title="📩 Support Ticket", 
            description=f"Halo {user.mention}!\nSilakan sampaikan pertanyaan, laporan, atau keluhan Anda di sini. Tim admin akan segera membantu Anda.", 
            color=0x2b2d31
        )
        
        # Kirim Embed Bersih (Hanya mention user pembuat tiket di dalam embed)
        await channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())
        
        # 5. GHOST PING KHUSUS OWNER, ADMIN, & MODERATOR (TIDAK KELIATAN TAPI MASUK NOTIF)
        owner_id = 1507429520200958064
        admin_id = 1507446465075871897
        mod_id = 1507450508812488775
        
        ping_teks = f"<@&{owner_id}> <@&{admin_id}> <@&{mod_id}> Tiket baru dari {user.mention}"
        
        ghost_ping = await channel.send(ping_teks)
        await ghost_ping.delete() # Pesan langsung musnah seketika, tapi notifikasi tetap terkirim ke Staff!

        await interaction.followup.send(f"✅ Tiket privat Anda berhasil dibuat di {channel.mention}", ephemeral=True)

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="setup-ticket")
    @commands.has_permissions(administrator=True)
    async def setup_ticket(self, ctx):
        embed = discord.Embed(
            title="📞 Pusat Bantuan Server", 
            description="Klik tombol **Buka Tiket** di bawah ini untuk menghubungi Admin secara privat.\n\n*Gunakan tiket ini untuk melaporkan member nakal, bertanya, atau urusan server lainnya.*", 
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=TicketView())

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    print("✅ Cog Loaded: Ticket System (Ghost Ping Official Staff Active)")
