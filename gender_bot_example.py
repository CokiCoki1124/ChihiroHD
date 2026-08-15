import discord
from discord.ext import commands
from discord.ui import Button, View

# ==========================================
# GANTI DENGAN ID ROLE GENDER DI SERVER ANDA
# ==========================================
ROLE_MAN = 1507710764075450408
ROLE_WOMAN = 1507710910305665176

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def toggle_role(interaction: discord.Interaction, role_id: int):
    role = interaction.guild.get_role(role_id)
    if not role:
        await interaction.response.send_message(
            "❌ Error: Role tidak ditemukan. Cek ID Role di codingan.",
            ephemeral=True,
        )
        return

    if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(
            f"➖ Role **{role.name}** berhasil dilepas.",
            ephemeral=True,
        )
    else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"➕ Role **{role.name}** berhasil ditambahkan.",
            ephemeral=True,
        )


class GenderView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Man", style=discord.ButtonStyle.primary, emoji="♂️", custom_id="btn_man_new")
    async def btn_man(self, interaction: discord.Interaction, button: Button):
        await toggle_role(interaction, ROLE_MAN)

    @discord.ui.button(label="Woman", style=discord.ButtonStyle.danger, emoji="♀️", custom_id="btn_woman_new")
    async def btn_woman(self, interaction: discord.Interaction, button: Button):
        await toggle_role(interaction, ROLE_WOMAN)


@bot.command()
@commands.has_permissions(administrator=True)
async def setup_gender(ctx):
    embed = discord.Embed(
        title="React to give yourself a role",
        color=0x2B2D31,
    )
    embed.description = "@🚹 • **man** Man\n@🚺 • **woman** Woman"

    # Masukkan link gambar di sini jika ingin.
    embed.set_image(url="MASUKKAN_LINK_GAMBAR_DISINI")

    await ctx.send(embed=embed, view=GenderView())


@bot.event
async def on_ready():
    print(f"Bot siap sebagai {bot.user}")


bot.run("MTUzNTcyNzI1NzExNTQyNjk3Nw.GniLEq.5JZcMKmCiLKEWaq4Ci00USeEdxHwuLi42FB3Hc")
