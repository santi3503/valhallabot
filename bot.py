import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import json

# ---------- CONFIGURACIÓN ----------
TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
DATA_FILE = "ranking_diario.json"  # Archivo donde guardamos los valores diarios

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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
    embed.set_footer(text="Ranking de Albion Online")
    return embed


# ---------- FUNCIONES RANKING DIARIO ----------
def guardar_datos_diarios(jugadores_stats):
    data = {j["Name"]: j for j in jugadores_stats}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def calcular_ranking_diario(jugadores_stats):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data_antigua = json.load(f)
    except FileNotFoundError:
        data_antigua = {}

    ranking_diario = []
    for j in jugadores_stats:
        nombre = j["Name"]
        anterior = data_antigua.get(nombre, {"PvP": 0, "PvE": 0, "Gathering": 0, "Crafting": 0})
        incremento_total = (
            (j["PvP"] - anterior.get("PvP", 0)) +
            (j["PvE"] - anterior.get("PvE", 0)) +
            (j["Gathering"] - anterior.get("Gathering", 0)) +
            (j["Crafting"] - anterior.get("Crafting", 0))
        )
        ranking_diario.append({
            "Name": nombre,
            "PvP": j["PvP"] - anterior.get("PvP", 0),
            "PvE": j["PvE"] - anterior.get("PvE", 0),
            "Gathering": j["Gathering"] - anterior.get("Gathering", 0),
            "Crafting": j["Crafting"] - anterior.get("Crafting", 0),
            "Total": incremento_total
        })
    return ranking_diario


def generar_ranking_diario_por_tipo(ranking_diario, tipo, top=10):
    ranking = []
    for j in ranking_diario:
        if tipo == "total":
            valor = j["Total"]
        else:
            valor = j.get(tipo.capitalize(), 0)
        ranking.append((j["Name"], max(valor,0)))
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking[:top]


# ---------- COMANDOS MANUALES ----------
@bot.command(name="ranking", help="🏆 Muestra el Top 10 de Fama Total acumulada")
async def ranking(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "total")
    embed = crear_embed(ranking_data, "🏆 Fama Total", discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="pvp", help="⚔️ Muestra el Top 10 de Fama PvP acumulada")
async def pvp(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "pvp")
    embed = crear_embed(ranking_data, "⚔️ PvP", discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="pve", help="🐉 Muestra el Top 10 de Fama PvE acumulada")
async def pve(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "pve")
    embed = crear_embed(ranking_data, "🐉 PvE", discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="recoleccion", help="⛏️ Muestra el Top 10 de Fama de Recolección acumulada")
async def recoleccion(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "gathering")
    embed = crear_embed(ranking_data, "⛏️ Recolección", discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="fabricacion", help="⚒️ Muestra el Top 10 de Fama de Fabricación acumulada")
async def fabricacion(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "crafting")
    embed = crear_embed(ranking_data, "⚒️ Fabricación", discord.Color.dark_grey())
    await ctx.send(embed=embed)


# ---------- NUEVOS COMANDOS DIARIOS ----------
@bot.command(name="ranking_diario", help="📅 Muestra el Top 10 de Fama Total del día")
async def ranking_diario_cmd(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_diario_data = calcular_ranking_diario(jugadores_stats)
    ranking_data = generar_ranking_diario_por_tipo(ranking_diario_data, "total")
    embed = crear_embed(ranking_data, "🏆 Ranking Diario Total", discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="pvp_diario", help="⚔️ Muestra el Top 10 PvP del día")
async def pvp_diario_cmd(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_diario_data = calcular_ranking_diario(jugadores_stats)
    ranking_data = generar_ranking_diario_por_tipo(ranking_diario_data, "pvp")
    embed = crear_embed(ranking_data, "⚔️ PvP Diario", discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="pve_diario", help="🐉 Muestra el Top 10 PvE del día")
async def pve_diario_cmd(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_diario_data = calcular_ranking_diario(jugadores_stats)
    ranking_data = generar_ranking_diario_por_tipo(ranking_diario_data, "pve")
    embed = crear_embed(ranking_data, "🐉 PvE Diario", discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="recoleccion_diario", help="⛏️ Muestra el Top 10 Recolección del día")
async def recoleccion_diario_cmd(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_diario_data = calcular_ranking_diario(jugadores_stats)
    ranking_data = generar_ranking_diario_por_tipo(ranking_diario_data, "gathering")
    embed = crear_embed(ranking_data, "⛏️ Recolección Diario", discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="fabricacion_diario", help="⚒️ Muestra el Top 10 Fabricación del día")
async def fabricacion_diario_cmd(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_diario_data = calcular_ranking_diario(jugadores_stats)
    ranking_data = generar_ranking_diario_por_tipo(ranking_diario_data, "crafting")
    embed = crear_embed(ranking_data, "⚒️ Fabricación Diario", discord.Color.dark_grey())
    await ctx.send(embed=embed)


# ---------- COMANDO DE AYUDA ----------
@bot.command(name="ayuda", help="📜 Muestra todos los comandos disponibles")
async def ayuda(ctx):
    embed = discord.Embed(title="📜 Comandos disponibles", color=discord.Color.purple())
    for comando in bot.commands:
        descripcion = comando.help if comando.help else "No hay descripción."
        embed.add_field(name=f"!{comando.name}", value=descripcion, inline=False)
    embed.set_footer(text="Bot de Albion Online - Rankings diarios y comandos manuales")
    await ctx.send(embed=embed)


# ---------- LOOP DEL RANKING DIARIO ----------
@tasks.loop(hours=24)
async def ranking_diario_loop():
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("⚠️ No encontré el canal con ese ID.")
            return

        jugadores_stats = await obtener_todos_los_datos_gremio()
        ranking_diario_data = calcular_ranking_diario(jugadores_stats)
        tipos = {
            "🏆 Fama Total Diario": ("total", discord.Color.gold()),
            "⚔️ PvP Diario": ("pvp", discord.Color.red()),
            "🐉 PvE Diario": ("pve", discord.Color.green()),
            "⛏️ Recolección Diario": ("gathering", discord.Color.blue()),
            "⚒️ Fabricación Diario": ("crafting", discord.Color.dark_grey())
        }

        for titulo, (tipo, color) in tipos.items():
            ranking_data = generar_ranking_diario_por_tipo(ranking_diario_data, tipo)
            embed = crear_embed(ranking_data, titulo, color)
            await channel.send(embed=embed)

        # Guardar los datos actuales para el siguiente día
        guardar_datos_diarios(jugadores_stats)

        print("✅ Rankings diarios enviados correctamente.")
    except Exception as e:
        print(f"❌ Error enviando los rankings: {e}")


@ranking_diario_loop.before_loop
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
    if not ranking_diario_loop.is_running():
        ranking_diario_loop.start()
        print("▶️ Tarea 'ranking_diario_loop' iniciada.")


# ---------- INICIO ----------
bot.run(TOKEN)
