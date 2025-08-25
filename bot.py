import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

# ---------- CONFIGURACIÓN ----------
TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BASE_URL = "https://gameinfo.albiononline.com/api/gameinfo"

# ---------- FUNCIONES AUXILIARES ----------
async def get_json(session, url):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error al consultar {url}: {e}")
    return None


async def obtener_todos_los_datos_gremio():
    async with aiohttp.ClientSession() as session:
        miembros = await get_json(session, f"{BASE_URL}/guilds/{GUILD_ID}/members")
        if not miembros:
            return []

        tareas = [get_json(session, f"{BASE_URL}/players/{m['Id']}") for m in miembros]
        resultados = await asyncio.gather(*tareas)

        jugadores_stats = []
        for jugador in resultados:
            if jugador and "LifetimeStatistics" in jugador:
                jugadores_stats.append({
                    "Name": jugador["Name"],
                    "PvP": jugador["LifetimeStatistics"].get("PvP", {}).get("Total", 0),
                    "PvE": jugador["LifetimeStatistics"].get("PvE", {}).get("Total", 0),
                    "Gathering": jugador["LifetimeStatistics"].get("Gathering", {}).get("All", {}).get("Total", 0),
                    "Crafting": jugador["LifetimeStatistics"].get("Crafting", {}).get("Total", 0)
                })
        return jugadores_stats


def generar_ranking(jugadores_stats, tipo, top=10):
    ranking = []
    for j in jugadores_stats:
        if tipo == "total":
            valor = j["PvP"] + j["PvE"] + j["Gathering"] + j["Crafting"]
        else:
            valor = j.get(tipo.capitalize(), 0)
        ranking.append((j["Name"], valor))
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking[:top]


def crear_embed(ranking, titulo, color):
    embed = discord.Embed(title=titulo, color=color)
    emojis = ["🥇", "🥈", "🥉"]
    for i, (name, valor) in enumerate(ranking, start=1):
        prefix = emojis[i-1] if i <= 3 else f"{i}."
        embed.add_field(name=f"{prefix} {name}", value=f"{valor:,}", inline=False)
    embed.set_footer(text="Ranking diario de Albion Online")
    return embed


# ---------- COMANDOS MANUALES ----------
@bot.command(name="ranking")
async def ranking(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "total")
    embed = crear_embed(ranking_data, "🏆 Fama Total", discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="pvp")
async def pvp(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "pvp")
    embed = crear_embed(ranking_data, "⚔️ PvP", discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="pve")
async def pve(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "pve")
    embed = crear_embed(ranking_data, "🐉 PvE", discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="recoleccion")
async def recoleccion(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "gathering")
    embed = crear_embed(ranking_data, "⛏️ Recolección", discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="fabricacion")
async def fabricacion(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "crafting")
    embed = crear_embed(ranking_data, "⚒️ Fabricación", discord.Color.dark_grey())
    await ctx.send(embed=embed)


# ---------- COMANDO HELP AUTOMÁTICO ----------
@bot.command(name="help")
async def help_comandos(ctx):
    embed = discord.Embed(title="📜 Comandos disponibles", color=discord.Color.purple())
    for comando in bot.commands:
        descripcion = comando.help if comando.help else "No hay descripción."
        embed.add_field(name=f"!{comando.name}", value=descripcion, inline=False)
    embed.set_footer(text="Bot de Albion Online - Rankings diarios y comandos manuales")
    await ctx.send(embed=embed)


# ---------- LOOP DEL RANKING DIARIO ----------
@tasks.loop(hours=24)
async def ranking_diario():
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("⚠️ No encontré el canal con ese ID.")
            return

        jugadores_stats = await obtener_todos_los_datos_gremio()
        tipos = {
            "🏆 Fama Total": ("total", discord.Color.gold()),
            "⚔️ PvP": ("pvp", discord.Color.red()),
            "🐉 PvE": ("pve", discord.Color.green()),
            "⛏️ Recolección": ("gathering", discord.Color.blue()),
            "⚒️ Fabricación": ("crafting", discord.Color.dark_grey())
        }

        for titulo, (tipo, color) in tipos.items():
            ranking_data = generar_ranking(jugadores_stats, tipo)
            embed = crear_embed(ranking_data, titulo, color)
            await channel.send(embed=embed)

        print("✅ Rankings diarios enviados correctamente.")
    except Exception as e:
        print(f"❌ Error enviando los rankings: {e}")


@ranking_diario.before_loop
async def antes_de_loop():
    ahora = datetime.now(ZoneInfo("UTC"))
    proxima = ahora.replace(hour=23, minute=0, second=0, microsecond=0)
    if proxima <= ahora:
        proxima += timedelta(days=1)
    espera = (proxima - ahora).total_seconds()
    print(f"⏳ Esperando {espera/3600:.2f} horas hasta las 23:00 UTC para iniciar ranking diario.")
    await asyncio.sleep(espera)


# ---------- EVENTOS ----------
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    if not ranking_diario.is_running():
        ranking_diario.start()
        print("▶️ Tarea 'ranking_diario' iniciada.")


# ---------- INICIO ----------
bot.run(TOKEN)
