import os
import discord
from discord.ext import commands, tasks
import requests
import asyncio
from datetime import datetime

# ==============================
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
# ==============================
TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']   # ID del gremio Albion
CHANNEL_ID = int(os.environ['CHANNEL_ID'])  # ID del canal donde publica

# ==============================
# INTENTS Y BOT
# ==============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# FUNCIONES PARA TRAER DATOS DE ALBION
# ==============================
def get_guild_stats(guild_id):
    url = f"https://gameinfo.albiononline.com/api/gameinfo/guilds/{guild_id}/members"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def get_top_by_fame(guild_id, fame_type="KillFame"):
    members = get_guild_stats(guild_id)
    ranking = sorted(members, key=lambda x: x.get(fame_type, 0), reverse=True)[:10]
    return ranking

def format_ranking(ranking, fame_type):
    lines = []
    for i, member in enumerate(ranking, start=1):
        fame = member.get(fame_type, 0)
        lines.append(f"**{i}. {member['Name']}** — {fame:,} fama")
    return "\n".join(lines)

# ==============================
# COMANDOS
# ==============================
@bot.command(name="ranking")
async def ranking(ctx):
    ranking = get_top_by_fame(GUILD_ID, "KillFame")
    msg = format_ranking(ranking, "KillFame")
    await ctx.send(f"🏆 **Top 10 - Ranking General (PvP Kill Fame)** 🏆\n\n{msg}")

@bot.command(name="pvp")
async def pvp(ctx):
    ranking = get_top_by_fame(GUILD_ID, "KillFame")
    msg = format_ranking(ranking, "KillFame")
    await ctx.send(f"⚔️ **Top 10 PvP (Kill Fame)** ⚔️\n\n{msg}")

@bot.command(name="recoleccion")
async def recoleccion(ctx):
    ranking = get_top_by_fame(GUILD_ID, "GatheringFame")
    msg = format_ranking(ranking, "GatheringFame")
    await ctx.send(f"🌿 **Top 10 Recolección (Gathering Fame)** 🌿\n\n{msg}")

@bot.command(name="fabricacion")
async def fabricacion(ctx):
    ranking = get_top_by_fame(GUILD_ID, "CraftingFame")
    msg = format_ranking(ranking, "CraftingFame")
    await ctx.send(f"⚒️ **Top 10 Fabricación (Crafting Fame)** ⚒️\n\n{msg}")

# ==============================
# TAREA AUTOMÁTICA TODOS LOS DÍAS 23:00
# ==============================
@tasks.loop(minutes=1)
async def daily_ranking():
    now = datetime.utcnow().strftime("%H:%M")
    if now == "23:00":  # hora UTC, ajusta si querés horario argentino
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            ranking = get_top_by_fame(GUILD_ID, "KillFame")
            msg = format_ranking(ranking, "KillFame")
            await channel.send(f"📅 **Ranking diario de PvP** 📅\n\n{msg}")

@daily_ranking.before_lo
