"""
infohero.py — Cog Discord: MLBB Hero Rank Statistics
=====================================================
Data 1:1 dengan https://www.mobilelegends.com/rank
(RANKING / HERO / PICK RATE / WIN RATE / BAN RATE / COUNTER HERO)

Cara pakai:
  1. Simpan file ini di folder cogs/ lalu load: await bot.load_extension("cogs.infohero")
  2. Admin ketik: !setup-infohero          -> memasang panel di channel
  3. Member tinggal pencet tombol di panel -> hasilnya EPHEMERAL (cuma dia yang lihat)

Butuh: discord.py >= 2.3, aiohttp
  pip install -U "discord.py>=2.3" aiohttp
"""

import asyncio
import difflib
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

# ======================================================================
# KONFIGURASI
# ======================================================================

# Sumber data (mirror JSON dari halaman resmi mobilelegends.com/rank)
API_BASE = "https://arena.rone.dev/api"
API_BASE_FALLBACK = "https://arena-hv.fastapicloud.dev/api"

CACHE_TTL_MINUTES = 60      # data di-refresh otomatis tiap 60 menit
AUTO_REFRESH_HOURS = 1      # background task auto-update
PAGE_SIZE = 10              # jumlah hero per halaman
MAX_HEROES = 200            # ambil semua hero sekaligus
REQUEST_TIMEOUT = 20

# True  = command !setup-infohero (termasuk pencarian hero) hanya untuk admin
# False = member boleh ketik !setup-infohero <nama_hero>, tapi panel tetap admin-only
ADMIN_ONLY_SEARCH = True

WIB = timezone(timedelta(hours=7))

# ---- Pilihan filter (sama persis dengan dropdown di website) ----
DAYS_OPTIONS = [
    ("1", "Past 1 day", "🗓️"),
    ("3", "Past 3 days", "🗓️"),
    ("7", "Past 7 days", "🗓️"),
    ("15", "Past 15 days", "🗓️"),
    ("30", "Past 30 days", "🗓️"),
]

RANK_OPTIONS = [
    ("all", "All", "🌐"),
    ("epic", "Epic", "🟣"),
    ("legend", "Legend", "🔵"),
    ("mythic", "Mythic", "🟡"),
    ("honor", "Mythical Honor", "🟠"),
    ("glory", "Mythical Glory+", "🔴"),
]

# (value, label, field, order)
SORT_OPTIONS = [
    ("win_desc", "Win Rate — Tertinggi ⬇", "win", True),
    ("win_asc", "Win Rate — Terendah ⬆", "win", False),
    ("ban_desc", "Ban Rate — Tertinggi ⬇", "ban", True),
    ("ban_asc", "Ban Rate — Terendah ⬆", "ban", False),
    ("pick_desc", "Pick Rate — Tertinggi ⬇", "pick", True),
    ("pick_asc", "Pick Rate — Terendah ⬆", "pick", False),
]

DAYS_LABEL = {v: l for v, l, _ in DAYS_OPTIONS}
RANK_LABEL = {v: l for v, l, _ in RANK_OPTIONS}
SORT_LABEL = {v: l for v, l, _, _ in SORT_OPTIONS}
SORT_SPEC = {v: (f, d) for v, _, f, d in SORT_OPTIONS}

BRAND_COLOR = 0x1E90FF


# ======================================================================
# LAPISAN DATA
# ======================================================================

class MLBBRankAPI:
    """Ambil + cache statistik hero. Satu request melayani semua opsi sort."""

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[tuple[str, str], dict] = {}   # (days, rank) -> payload
        self._hero_names: dict[int, str] = {}
        self._hero_names_at: datetime | None = None
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                headers={"User-Agent": "DiscordBot-InfoHero/1.0"},
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str, params: dict):
        sess = await self.session()
        last_err = None
        for base in (API_BASE, API_BASE_FALLBACK):
            try:
                async with sess.get(f"{base}{path}", params=params) as r:
                    if r.status != 200:
                        last_err = f"HTTP {r.status}"
                        continue
                    return await r.json(content_type=None)
            except Exception as e:                                  # noqa: BLE001
                last_err = repr(e)
        raise RuntimeError(f"Gagal menghubungi API MLBB ({last_err})")

    # ---------------- hero id -> nama (untuk kolom Counter Hero) -------------
    async def hero_names(self) -> dict[int, str]:
        fresh = (
            self._hero_names_at
            and datetime.now(timezone.utc) - self._hero_names_at < timedelta(hours=24)
        )
        if self._hero_names and fresh:
            return self._hero_names
        try:
            data = await self._get("/heroes", {"size": MAX_HEROES, "index": 1, "lang": "en"})
            names: dict[int, str] = {}
            for rec in (data.get("data") or {}).get("records") or []:
                d = rec.get("data") or {}
                hid = d.get("hero_id")
                nm = (((d.get("hero") or {}).get("data") or {}).get("name"))
                if hid and nm:
                    names[int(hid)] = nm
            if names:
                self._hero_names = names
                self._hero_names_at = datetime.now(timezone.utc)
        except Exception as e:                                      # noqa: BLE001
            print(f"[InfoHero] gagal ambil daftar nama hero: {e}")
        return self._hero_names

    # ---------------- statistik rank ----------------------------------------
    async def get_stats(self, days: str, rank: str, force: bool = False) -> dict:
        key = (days, rank)
        cached = self._cache.get(key)
        if cached and not force:
            age = datetime.now(timezone.utc) - cached["fetched_at"]
            if age < timedelta(minutes=CACHE_TTL_MINUTES):
                return cached

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(key)
            if cached and not force:
                age = datetime.now(timezone.utc) - cached["fetched_at"]
                if age < timedelta(minutes=CACHE_TTL_MINUTES):
                    return cached
            try:
                raw = await self._get(
                    "/heroes/rank",
                    {
                        "days": days,
                        "rank": rank,
                        "sort_field": "win_rate",
                        "sort_order": "desc",
                        "size": MAX_HEROES,
                        "index": 1,
                        "lang": "en",
                    },
                )
            except Exception:
                if cached:                      # API mati -> pakai cache lama
                    return cached
                raise

            heroes = []
            for rec in (raw.get("data") or {}).get("records") or []:
                d = rec.get("data") or {}
                main = ((d.get("main_hero") or {}).get("data")) or {}
                name = main.get("name")
                if not name:
                    continue
                counters = sorted(
                    (d.get("sub_hero") or []),
                    key=lambda s: s.get("increase_win_rate") or 0,
                    reverse=True,
                )[:5]
                heroes.append({
                    "id": d.get("main_heroid"),
                    "name": name,
                    "head": main.get("head") or "",
                    "win": float(d.get("main_hero_win_rate") or 0) * 100,
                    "pick": float(d.get("main_hero_appearance_rate") or 0) * 100,
                    "ban": float(d.get("main_hero_ban_rate") or 0) * 100,
                    "counters": [c.get("heroid") for c in counters if c.get("heroid")],
                })

            if not heroes and cached:
                return cached

            payload = {
                "heroes": heroes,
                "fetched_at": datetime.now(timezone.utc),
                "days": days,
                "rank": rank,
            }
            self._cache[key] = payload
            return payload

    def sorted_heroes(self, payload: dict, sort_value: str) -> list[dict]:
        field, desc = SORT_SPEC.get(sort_value, ("win", True))
        return sorted(payload["heroes"], key=lambda h: h[field], reverse=desc)


# ======================================================================
# TAMPILAN (EMBED)
# ======================================================================

def fmt_time(dt: datetime) -> str:
    return dt.astimezone(WIB).strftime("%d-%m-%Y %H:%M WIB")


def build_list_embed(payload: dict, sort_value: str, page: int, api: MLBBRankAPI) -> discord.Embed:
    heroes = api.sorted_heroes(payload, sort_value)
    total = len(heroes)
    pages = max(1, -(-total // PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    chunk = heroes[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    header = f"{'#':>3} {'HERO':<16}{'PICK':>7}{'WIN':>8}{'BAN':>8}"
    lines = [header, "─" * len(header)]
    for i, h in enumerate(chunk, start=page * PAGE_SIZE + 1):
        nm = h["name"] if len(h["name"]) <= 15 else h["name"][:14] + "…"
        lines.append(
            f"{i:>3} {nm:<16}{h['pick']:>6.2f}%{h['win']:>7.2f}%{h['ban']:>7.2f}%"
        )

    embed = discord.Embed(
        title="📊 Mobile Legends — Hero Rank Statistics",
        description=(
            f"**Periode:** {DAYS_LABEL[payload['days']]}  •  "
            f"**Rank:** {RANK_LABEL[payload['rank']]}\n"
            f"**Urutan:** {SORT_LABEL[sort_value]}\n\n"
            "```\n" + "\n".join(lines) + "\n```"
        ),
        color=BRAND_COLOR,
    )
    embed.set_footer(
        text=(f"Halaman {page + 1}/{pages}  •  {total} hero  •  "
              f"Update: {fmt_time(payload['fetched_at'])}")
    )
    return embed


def tier_of(win: float) -> tuple[str, int]:
    if win >= 54:
        return "🔴 S+ Tier (OP)", 0xFF4444
    if win >= 52:
        return "🟠 S Tier (Kuat)", 0xFF8800
    if win >= 50:
        return "🟡 A Tier (Seimbang)", 0xFFCC00
    if win >= 48:
        return "🟢 B Tier (Situasional)", 0x44DD44
    return "🔵 C Tier (Lemah)", 0x4488FF


def build_hero_embed(hero: dict, position: int, total: int, payload: dict,
                     names: dict[int, str]) -> discord.Embed:
    tier, color = tier_of(hero["win"])
    embed = discord.Embed(
        title=f"📊 {hero['name'].upper()}",
        description=f"{tier}\n**Peringkat Win Rate:** #{position} dari {total} hero",
        color=color,
    )
    if hero["head"]:
        embed.set_thumbnail(url=hero["head"])
    embed.add_field(name="🎯 Win Rate", value=f"**{hero['win']:.2f}%**", inline=True)
    embed.add_field(name="📈 Pick Rate", value=f"**{hero['pick']:.2f}%**", inline=True)
    embed.add_field(name="🚫 Ban Rate", value=f"**{hero['ban']:.2f}%**", inline=True)

    if hero["counters"]:
        listed = [names.get(int(cid), f"Hero #{cid}") for cid in hero["counters"]]
        embed.add_field(name="⚔️ Counter Hero", value=" • ".join(listed), inline=False)

    embed.add_field(
        name="🔎 Filter Aktif",
        value=f"{DAYS_LABEL[payload['days']]} • {RANK_LABEL[payload['rank']]}",
        inline=False,
    )
    embed.set_footer(text=f"Update: {fmt_time(payload['fetched_at'])}")
    return embed


# ======================================================================
# MODAL PENCARIAN
# ======================================================================

class HeroSearchModal(discord.ui.Modal, title="🔍 Cari Hero"):
    hero_name = discord.ui.TextInput(
        label="Nama Hero",
        placeholder="Contoh: Ling, Fanny, Yi Sun-shin",
        max_length=40,
    )

    def __init__(self, view: "HeroStatsView"):
        super().__init__()
        self._view = view

    async def on_submit(self, interaction: discord.Interaction):
        await self._view.do_search(interaction, str(self.hero_name).strip())


# ======================================================================
# PANEL INTERAKTIF (EPHEMERAL, per user)
# ======================================================================

class HeroStatsView(discord.ui.View):
    """View pribadi. Dikirim ephemeral, jadi member lain tidak melihat apa pun."""

    def __init__(self, cog: "InfoHero", user_id: int):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.days = "1"
        self.rank = "glory"
        self.sort = "win_desc"
        self.page = 0
        self.payload: dict | None = None
        self._build_components()

    # ------------------------------------------------------------------
    def _build_components(self):
        self.clear_items()

        days_sel = discord.ui.Select(
            placeholder=f"🗓️ Periode: {DAYS_LABEL[self.days]}",
            row=0,
            options=[
                discord.SelectOption(label=l, value=v, emoji=e, default=(v == self.days))
                for v, l, e in DAYS_OPTIONS
            ],
        )
        days_sel.callback = self._on_days
        self.add_item(days_sel)

        rank_sel = discord.ui.Select(
            placeholder=f"🏆 Rank: {RANK_LABEL[self.rank]}",
            row=1,
            options=[
                discord.SelectOption(label=l, value=v, emoji=e, default=(v == self.rank))
                for v, l, e in RANK_OPTIONS
            ],
        )
        rank_sel.callback = self._on_rank
        self.add_item(rank_sel)

        sort_sel = discord.ui.Select(
            placeholder=f"↕️ Urutan: {SORT_LABEL[self.sort]}",
            row=2,
            options=[
                discord.SelectOption(label=l, value=v, default=(v == self.sort))
                for v, l, _, _ in SORT_OPTIONS
            ],
        )
        sort_sel.callback = self._on_sort
        self.add_item(sort_sel)

        first = discord.ui.Button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=3)
        prev = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary, row=3)
        nxt = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.primary, row=3)
        last = discord.ui.Button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=3)
        first.callback = self._go_first
        prev.callback = self._go_prev
        nxt.callback = self._go_next
        last.callback = self._go_last
        for b in (first, prev, nxt, last):
            self.add_item(b)

        search = discord.ui.Button(
            label="Cari Hero", emoji="🔍", style=discord.ButtonStyle.success, row=4)
        refresh = discord.ui.Button(
            label="Refresh Data", emoji="🔄", style=discord.ButtonStyle.secondary, row=4)
        search.callback = self._on_search
        refresh.callback = self._on_refresh
        self.add_item(search)
        self.add_item(refresh)

    # ------------------------------------------------------------------
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Panel ini bukan milikmu. Tekan tombol di panel utama untuk membuka punyamu sendiri.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    # ------------------------------------------------------------------
    async def _load(self, force: bool = False):
        self.payload = await self.cog.api.get_stats(self.days, self.rank, force=force)
        return self.payload

    def _max_page(self) -> int:
        if not self.payload:
            return 0
        return max(0, -(-len(self.payload["heroes"]) // PAGE_SIZE) - 1)

    async def refresh_message(self, interaction: discord.Interaction, force: bool = False):
        try:
            await self._load(force=force)
        except Exception as e:                                       # noqa: BLE001
            msg = f"❌ Gagal mengambil data: `{e}`"
            if interaction.response.is_done():
                await interaction.edit_original_response(content=msg, embed=None, view=self)
            else:
                await interaction.response.edit_message(content=msg, embed=None, view=self)
            return

        self.page = max(0, min(self.page, self._max_page()))
        self._build_components()
        embed = build_list_embed(self.payload, self.sort, self.page, self.cog.api)
        if interaction.response.is_done():
            await interaction.edit_original_response(content=None, embed=embed, view=self)
        else:
            await interaction.response.edit_message(content=None, embed=embed, view=self)

    # ---- callbacks ---------------------------------------------------
    async def _on_days(self, interaction: discord.Interaction):
        self.days = interaction.data["values"][0]
        self.page = 0
        await interaction.response.defer()
        await self.refresh_message(interaction)

    async def _on_rank(self, interaction: discord.Interaction):
        self.rank = interaction.data["values"][0]
        self.page = 0
        await interaction.response.defer()
        await self.refresh_message(interaction)

    async def _on_sort(self, interaction: discord.Interaction):
        self.sort = interaction.data["values"][0]
        self.page = 0
        await self.refresh_message(interaction)

    async def _go_first(self, interaction: discord.Interaction):
        self.page = 0
        await self.refresh_message(interaction)

    async def _go_prev(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        await self.refresh_message(interaction)

    async def _go_next(self, interaction: discord.Interaction):
        self.page = min(self._max_page(), self.page + 1)
        await self.refresh_message(interaction)

    async def _go_last(self, interaction: discord.Interaction):
        self.page = self._max_page()
        await self.refresh_message(interaction)

    async def _on_refresh(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.refresh_message(interaction, force=True)

    async def _on_search(self, interaction: discord.Interaction):
        await interaction.response.send_modal(HeroSearchModal(self))

    # ---- pencarian hero ---------------------------------------------
    async def do_search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        try:
            payload = await self._load()
        except Exception as e:                                       # noqa: BLE001
            await interaction.followup.send(f"❌ Gagal mengambil data: `{e}`", ephemeral=True)
            return

        hero, position = find_hero(payload, query)
        if hero is None:
            names = [h["name"] for h in payload["heroes"]]
            close = difflib.get_close_matches(query, names, n=3, cutoff=0.4)
            hint = f"\nMungkin maksudmu: **{'**, **'.join(close)}**" if close else ""
            await interaction.followup.send(
                f"❌ Hero **{query}** tidak ditemukan.{hint}", ephemeral=True)
            return

        names_map = await self.cog.api.hero_names()
        embed = build_hero_embed(hero, position, len(payload["heroes"]), payload, names_map)
        await interaction.followup.send(embed=embed, ephemeral=True)


def find_hero(payload: dict, query: str) -> tuple[dict | None, int]:
    """Cari hero (case-insensitive, exact -> prefix -> substring -> fuzzy)."""
    q = query.lower().strip()
    ranked = sorted(payload["heroes"], key=lambda h: h["win"], reverse=True)
    pos = {h["name"]: i + 1 for i, h in enumerate(ranked)}

    for h in payload["heroes"]:
        if h["name"].lower() == q:
            return h, pos[h["name"]]
    for h in payload["heroes"]:
        if h["name"].lower().startswith(q):
            return h, pos[h["name"]]
    for h in payload["heroes"]:
        if q in h["name"].lower():
            return h, pos[h["name"]]

    names = [h["name"] for h in payload["heroes"]]
    match = difflib.get_close_matches(query, names, n=1, cutoff=0.6)
    if match:
        for h in payload["heroes"]:
            if h["name"] == match[0]:
                return h, pos[h["name"]]
    return None, 0


# ======================================================================
# PANEL PUBLIK (persistent — tetap hidup walau bot restart)
# ======================================================================

class HeroPanelView(discord.ui.View):
    def __init__(self, cog: "InfoHero"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Buka Statistik Hero",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        custom_id="mlbb:infohero:open",
    )
    async def open_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HeroStatsView(self.cog, interaction.user.id)
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            payload = await view._load()
        except Exception as e:                                       # noqa: BLE001
            await interaction.followup.send(
                f"❌ Gagal mengambil data: `{e}`", ephemeral=True)
            return
        embed = build_list_embed(payload, view.sort, 0, self.cog.api)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ======================================================================
# COG
# ======================================================================

def is_admin():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        p = ctx.author.guild_permissions
        return p.administrator or p.manage_guild
    return commands.check(predicate)


class InfoHero(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api = MLBBRankAPI()

    async def cog_load(self):
        self.bot.add_view(HeroPanelView(self))   # panel tetap aktif setelah restart
        self.auto_update.start()

    async def cog_unload(self):
        self.auto_update.cancel()
        await self.api.close()

    # ---------------- auto update tiap jam ----------------------------
    @tasks.loop(hours=AUTO_REFRESH_HOURS)
    async def auto_update(self):
        combos = [("1", "glory"), ("1", "all"), ("7", "glory"), ("7", "all")]
        ok = 0
        for days, rank in combos:
            try:
                await self.api.get_stats(days, rank, force=True)
                ok += 1
            except Exception as e:                                   # noqa: BLE001
                print(f"[InfoHero] auto-update {days}d/{rank} gagal: {e}")
            await asyncio.sleep(1)
        try:
            await self.api.hero_names()
        except Exception:                                            # noqa: BLE001
            pass
        print(f"[InfoHero] 🔄 Auto-update selesai ({ok}/{len(combos)} filter diperbarui)")

    @auto_update.before_loop
    async def before_auto_update(self):
        await self.bot.wait_until_ready()
        print("[InfoHero] ✅ Background auto-updater aktif")

    # ---------------- command ----------------------------------------
    @commands.hybrid_command(
        name="setup-infohero",
        aliases=["setup_infohero", "infohero"],
        description="Pasang panel statistik hero MLBB (admin), atau cari 1 hero.",
    )
    @app_commands.describe(hero_name="Kosongkan untuk memasang panel. Isi untuk melihat 1 hero.")
    @is_admin()
    @commands.guild_only()
    async def setup_infohero(self, ctx: commands.Context, *, hero_name: str | None = None):
        # ---- mode pencarian satu hero ----
        if hero_name:
            await ctx.defer(ephemeral=True)
            try:
                payload = await self.api.get_stats("1", "glory")
            except Exception as e:                                   # noqa: BLE001
                await ctx.send(f"❌ Gagal mengambil data: `{e}`", ephemeral=True)
                return
            hero, position = find_hero(payload, hero_name)
            if hero is None:
                names = [h["name"] for h in payload["heroes"]]
                close = difflib.get_close_matches(hero_name, names, n=3, cutoff=0.4)
                hint = f"\nMungkin maksudmu: **{'**, **'.join(close)}**" if close else ""
                await ctx.send(f"❌ Hero **{hero_name}** tidak ditemukan.{hint}", ephemeral=True)
                return
            names_map = await self.api.hero_names()
            embed = build_hero_embed(hero, position, len(payload["heroes"]), payload, names_map)
            await ctx.send(embed=embed, ephemeral=True)
            return

        # ---- mode pasang panel ----
        embed = discord.Embed(
            title="📊 Mobile Legends — Hero Rank Statistics",
            description=(
                "Tekan tombol di bawah untuk membuka statistik hero.\n"
                "**Hasilnya hanya kamu yang bisa lihat** — member lain tidak akan terganggu.\n\n"
                "**Yang bisa diatur:**\n"
                "🗓️ Periode — Past 1 / 3 / 7 / 15 / 30 days\n"
                "🏆 Rank — All, Epic, Legend, Mythic, Mythical Honor, Mythical Glory+\n"
                "↕️ Urutan — Win Rate / Ban Rate / Pick Rate (tertinggi ⬇ atau terendah ⬆)\n"
                "🔍 Cari Hero — lihat Win/Pick/Ban rate + counter satu hero\n\n"
                f"Data otomatis diperbarui setiap {AUTO_REFRESH_HOURS} jam mengikuti "
                "[mobilelegends.com/rank](https://www.mobilelegends.com/rank)."
            ),
            color=BRAND_COLOR,
        )
        embed.set_footer(text="Sumber data: Mobile Legends: Bang Bang Official Rank Page")
        await ctx.send(embed=embed, view=HeroPanelView(self))

    @setup_infohero.error
    async def setup_infohero_error(self, ctx: commands.Context, error):
        if isinstance(error, (commands.CheckFailure, app_commands.CheckFailure)):
            await ctx.send(
                "⛔ Command ini hanya untuk **Admin**. "
                "Member cukup menekan tombol di panel yang sudah dipasang.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(InfoHero(bot))
    print("✅ Cog Loaded: InfoHero (MLBB Hero Rank)")
