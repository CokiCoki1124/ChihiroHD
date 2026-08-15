import os
import discord
from discord.ext import commands
from discord.ui import Button, View
from cogs.ml_calculator import WRView, TargetWRView

ROLE_MAN = 1507710764075450408
ROLE_WOMAN = 1507710910305665176

ROLE_EXP = 1507513107910623252
ROLE_GOLD = 1507513296679337994
ROLE_MID = 1507475536618983465
ROLE_JUNGLER = 1507513310759751844
ROLE_ROAMER = 1507515529840296066

ROLE_HOK = 1507843650242215967
ROLE_MLBB_GAME = 1507843551265034331
ROLE_MINECRAFT = 1507843676481650778
ROLE_BLOOD_STRIKE = 1507843823341142246

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class ChihiroBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        self.add_view(GenderView())
        self.add_view(GameView())
        self.add_view(MLBBView())
        self.add_view(WRView())
        self.add_view(TargetWRView())

        await self.load_extension("cogs.message_logger")
        await self.load_extension("cogs.antilink")
        await self.load_extension("cogs.ticket_system")
        await self.load_extension("cogs.automod")
        await self.load_extension("cogs.ml_calculator")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.lofi_radio")


bot = ChihiroBot()


async def toggle_role(interaction: discord.Interaction, role_id: int) -> None:
    role = interaction.guild.get_role(role_id)
    if not role:
        await interaction.response.send_message(
            "❌ Error: Role tidak ditemukan. Cek ID di konfigurasi.", ephemeral=True
        )
        return

    if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(
            f"➖ Role **{role.name}** berhasil dilepas.", ephemeral=True
        )
    else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"➕ Role **{role.name}** berhasil ditambahkan.", ephemeral=True
        )


class GenderView(View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Man", style=discord.ButtonStyle.primary, emoji="♂️", custom_id="btn_man")
    async def btn_man(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_MAN)

    @discord.ui.button(label="Woman", style=discord.ButtonStyle.danger, emoji="♀️", custom_id="btn_woman")
    async def btn_woman(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_WOMAN)


class GameView(View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="HOK", style=discord.ButtonStyle.secondary, custom_id="btn_hok")
    async def btn_hok(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_HOK)

    @discord.ui.button(label="MLBB", style=discord.ButtonStyle.secondary, custom_id="btn_mlbb_game")
    async def btn_mlbb(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_MLBB_GAME)

    @discord.ui.button(label="MINECRAFT", style=discord.ButtonStyle.secondary, custom_id="btn_minecraft")
    async def btn_minecraft(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_MINECRAFT)

    @discord.ui.button(label="Blood Strike", style=discord.ButtonStyle.secondary, custom_id="btn_bloodstrike")
    async def btn_bloodstrike(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_BLOOD_STRIKE)


class MLBBView(View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="EXP Laner", style=discord.ButtonStyle.primary, custom_id="btn_exp")
    async def btn_exp(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_EXP)

    @discord.ui.button(label="Gold Laner", style=discord.ButtonStyle.success, custom_id="btn_gold")
    async def btn_gold(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_GOLD)

    @discord.ui.button(label="Mid Laner", style=discord.ButtonStyle.danger, custom_id="btn_mid")
    async def btn_mid(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_MID)

    @discord.ui.button(label="Jungler", style=discord.ButtonStyle.secondary, custom_id="btn_jungler")
    async def btn_jungler(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_JUNGLER)

    @discord.ui.button(label="Roamer", style=discord.ButtonStyle.secondary, custom_id="btn_roamer")
    async def btn_roamer(self, interaction: discord.Interaction, button: Button) -> None:
        await toggle_role(interaction, ROLE_ROAMER)


@bot.event
async def on_ready() -> None:
    print(f"✅ Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("✅ Bot siap. Gunakan: !setup-gender, !setup-game, !setuproles-MLBB")


@bot.command(name="setup-game", aliases=["setup_game"])
@commands.has_permissions(administrator=True)
async def setup_game(ctx: commands.Context) -> None:
    embed = discord.Embed(
        title="🎮 Choose Your Favorite Game 🎮",
        description=(
            "**HOK** — Honor of Kings\n\n"
            "**MLBB** — Mobile Legends Bang Bang\n\n"
            "**MINECRAFT** — Minecraft\n\n"
            "**Blood Strike** — Blood Strike\n\n"
            "🔥 Choose Your Role And Enjoy 🏆"
        ),
        color=discord.Color.from_rgb(88, 101, 242),
    )
    await ctx.send(embed=embed, view=GameView())
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


@bot.command(name="setuproles-MLBB", aliases=["setup-MLBB", "setup_mlbb"])
@commands.has_permissions(administrator=True)
async def setup_roles_mlbb(ctx: commands.Context) -> None:
    embed = discord.Embed(
        title="⚔️ Choose Your MLBB Lane Role ⚔️",
        description=(
            ":shield: - **EXP Laner** The frontline warrior! Hold the line, engage in epic duels, and show your resilience!\n\n"
            ":coin: - **Gold Laner** The team's main damage dealer! Farm gold, scale up, and strike fear into your enemies!\n\n"
            ":zap: - **Mid Laner** The game's tempo controller! Master the mid, unleash burst damage, and turn the tides of battle!\n\n"
            ":leaves: - **Jungler** The shadow predator! Secure objectives, dominate the jungle, and ambush enemies with surprise ganks!\n\n"
            ":shield: - **Roamer** The team's guardian! Support your allies with fast rotations, vision control, and game-changing initiations!\n\n"
            "🔥 Choose your role now and conquer the battlefield! 🏆"
        ),
        color=discord.Color.from_rgb(255, 102, 0),
    )
    await ctx.send(embed=embed, view=MLBBView())
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN environment variable tidak ditemukan. Tambahkan token bot Anda sebelum menjalankan."
        )
    bot.run(token)
