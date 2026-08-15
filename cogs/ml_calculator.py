import discord
from discord.ext import commands
import math

# ==========================================
# 1. FORMULIR POP-UP: TARGET WR (AKURASI TINGGI)
# ==========================================
class TargetWRModal(discord.ui.Modal, title='Kalkulator Target Winrate'):
    match_input = discord.ui.TextInput(
        label='Total Pertandingan Saat Ini', 
        style=discord.TextStyle.short, 
        placeholder='Contoh: 100', 
        required=True
    )
    wr_input = discord.ui.TextInput(
        label='Win Rate Kamu Saat Ini (%)', 
        style=discord.TextStyle.short, 
        placeholder='Contoh: 50.00', 
        required=True
    )
    target_input = discord.ui.TextInput(
        label='Win Rate Target Impian (%)', 
        style=discord.TextStyle.short, 
        placeholder='Contoh: 100', 
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            total_match = int(self.match_input.value)
            current_wr = float(self.wr_input.value.replace('%', '').replace(',', '.')) 
            target_wr = float(self.target_input.value.replace('%', '').replace(',', '.')) 
        except ValueError:
            await interaction.response.send_message("❌ Harap masukkan angka yang valid!", ephemeral=True)
            return

        if total_match <= 0 or current_wr < 0 or current_wr > 100 or target_wr <= 0:
            await interaction.response.send_message("❌ Persentase tidak valid!", ephemeral=True)
            return

        if target_wr <= current_wr:
            await interaction.response.send_message(f"✅ Winrate kamu **{current_wr}%**. Target **{target_wr}%** sudah tercapai dong!", ephemeral=True)
            return
            
        if target_wr >= 100:
            await interaction.response.send_message("❌ Target 100% **mustahil** dicapai jika WR-mu saat ini tidak 100% (karena kamu sudah punya kekalahan).", ephemeral=True)
            return

        # ==========================================
        # RUMUS AKURAT TINGKAT TINGGI (ABSOLUTE PRECISION)
        # ==========================================
        total_win_asli = round((current_wr / 100) * total_match)
        total_lose_asli = total_match - total_win_asli

        dibagi = 1 - (target_wr / 100)
        needed_wins = math.ceil(((target_wr / 100) * total_match - total_win_asli) / dibagi)

        # Sistem Penilai Gameplay Berdasarkan WR SAAT INI
        if current_wr < 45:
            julukan = "🥀 Dark System Survivor (Sering kena troll ya?)"
            warna = discord.Color.dark_gray()
        elif current_wr < 55:
            julukan = "🥉 Pejuang Solo Rank (Tetap semangat!)"
            warna = discord.Color.red()
        elif current_wr < 65:
            julukan = "🥈 Player Stabil (Jago nge-carry tim nih)"
            warna = discord.Color.blue()
        elif current_wr < 75:
            julukan = "🥇 Suhu / Glory (Mekanik udah mateng)"
            warna = discord.Color.gold()
        else:
            julukan = "👑 Penjoki / Pro Player (Ampun bang jago!)"
            warna = discord.Color.purple()

        embed = discord.Embed(title="🎯 Hasil Target Winrate", color=warna)
        embed.description = (
            f"Kamu butuh **{needed_wins} WIN TANPA KALAH** \n"
            f"untuk mendapatkan win rate **{target_wr}%**."
        )
        embed.add_field(name="Total Match Saat Ini", value=f"{total_match}", inline=True)
        embed.add_field(name="WR Saat Ini", value=f"{current_wr}%", inline=True)
        embed.add_field(name="Statistik Saat Ini", value=f"✅ **{total_win_asli}** Menang | ❌ **{total_lose_asli}** Kalah", inline=False)
        embed.add_field(name="Status Player", value=f"**{julukan}**", inline=False) 
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# 2. DUMMY VIEW (Agar main.py tidak error)
# ==========================================
class WRView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

# ==========================================
# 3. TOMBOL (VIEWS)
# ==========================================
class TargetWRView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
    
    @discord.ui.button(label="Hitung Target WR", style=discord.ButtonStyle.primary, custom_id="btn_target_wr_final", emoji="🎯")
    async def btn_target(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TargetWRModal())

# ==========================================
# 4. COMMANDS UNTUK MEMUNCULKAN MENU
# ==========================================
class MLCalculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup-targetwr", aliases=["setup-targetwr2", "setup-targerwr2"])
    @commands.has_permissions(administrator=True)
    async def setup_targetwr(self, ctx):
        embed = discord.Embed(
            title="🎯 Kalkulator Target Winrate ML", 
            description="Hitung berapa kemenangan beruntun yang kamu butuhkan untuk mencapai target WR Mobile Legends.\n\nMasukkan Total Match, Win Rate Saat Ini, dan Target WR (%).", 
            color=0x3498db 
        )
        await ctx.send(embed=embed, view=TargetWRView())

async def setup(bot):
    await bot.add_cog(MLCalculator(bot))
    print("✅ Cog Loaded: ML Calculator (Versi Final 100% Sempurna!)")
