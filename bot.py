import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os
import json
import matplotlib.pyplot as plt

# ---------- CONFIGURACIÓN ----------
TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
DATA_FILE_DIARIO = "ranking_diario.json"
DATA_FILE_SEMANAL = "ranking_semanal.json"

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

def generar_grafico_ranking(ranking, titulo):
    nombres = [name for name, valor in ranking]
    valores = [valor for name, valor in ranking]

    plt.figure(figsize=(8,5))
    barras = plt.barh(nombres[::-1], valores[::-1], color='skyblue')
    plt.xlabel('Fama')
    plt.title(titulo)
    plt.tight_layout()

    for barra in barras:
        plt.text(barra.get_width() + max(valores)*0.01, barra.get_y() + barra.get_height()/2,
                 f'{int(barra.get_width()):,}', va='center')

    archivo = f"{titulo.replace(' ','_')}.png"
    plt.savefig(archivo)
    plt.close()
    return archivo

# ---------- FUNCIONES DIARIO ----------
def guardar_datos_diarios(jugadores_stats):
    data = {j["Name"]: j for j in jugadores_stats}
    with open(DATA_FILE_DIARIO, "w", encoding="utf-8") as f:
        json.dump(data, f)

def calcular_ranking_diario(jugadores_stats):
    try:
        with open(DATA_FILE_DIARIO, "r", encoding="utf-8") as f:
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

# ---------- FUNCIONES SEMANALES ----------
def guardar_datos_semanales(jugadores_stats):
    hoy = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d")
    try:
        with open(DATA_FILE_SEMANAL, "r", encoding="utf-8") as f:
            data_semanal = json.load(f)
    except FileNotFoundError:
        data_semanal = {}

    data_semanal[hoy] = {j["Name"]: j for j in jugadores_stats}
    fechas = sorted(data_semanal.keys(), reverse=True)[:7]
    data_semanal = {fecha: data_semanal[fecha] for fecha in fechas}

    with open(DATA_FILE_SEMANAL, "w", encoding="utf-8") as f:
        json.dump(data_semanal, f)

def calcular_ranking_semanal(tipo, top=10):
    try:
        with open(DATA_FILE_SEMANAL, "r", encoding="utf-8") as f:
            data_semanal = json.load(f)
    except FileNotFoundError:
        return []

    acumulado = {}
    for fecha, jugadores in data_semanal.items():
        for name, stats in jugadores.items():
            if name not in acumulado:
                acumulado[name] = {"PvP":0, "PvE":0, "Gathering":0, "Crafting":0, "Total":0}
            acumulado[name]["PvP"] += stats.get("PvP",0)
            acumulado[name]["PvE"] += stats.get("PvE",0)
            acumulado[name]["Gathering"] += stats.get("Gathering",0)
            acumulado[name]["Crafting"] += stats.get("Crafting",0)
            acumulado[name]["Total"] += stats.get("PvP",0) + stats.get("PvE",0) + stats.get("Gathering",0) + stats.get("Crafting",0)

    ranking = []
    for name, stats in acumulado.items():
        if tipo == "total":
            valor = stats["Total"]
        else:
            valor = stats.get(tipo.capitalize(),0)
        ranking.append((name, valor))
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking[:top]

# ---------- ENVÍO DE GRÁFICOS ----------
async def enviar_ranking_grafico(ctx, ranking, titulo, color):
    archivo = generar_grafico_ranking(ranking, titulo)
    embed = discord.Embed(title=titulo, color=color)
    embed.set_image(url=f"attachment://{archivo}")
    await ctx.send(file=discord.File(archivo), embed=embed)

# ---------- COMANDOS ----------
# Rankings acumulativos
@bot.command(name="ranking")
async def cmd_ranking(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "total")
    await enviar_ranking_grafico(ctx, ranking_data, "🏆 Fama Total", discord.Color.gold())

@bot.command(name="pvp")
async def cmd_pvp(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "PvP")
    await enviar_ranking_grafico(ctx, ranking_data, "⚔️ PvP", discord.Color.red())

@bot.command(name="pve")
async def cmd_pve(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "PvE")
    await enviar_ranking_grafico(ctx, ranking_data, "🐉 PvE", discord.Color.green())

@bot.command(name="recoleccion")
async def cmd_recoleccion(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "Gathering")
    await enviar_ranking_grafico(ctx, ranking_data, "⛏️ Recolección", discord.Color.blue())

@bot.command(name="fabricacion")
async def cmd_fabricacion(ctx):
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_data = generar_ranking(jugadores_stats, "Crafting")
    await enviar_ranking_grafico(ctx, ranking_data, "⚒️ Fabricación", discord.Color.dark_orange())

# Rankings diarios y semanales
# Similar a los anteriores, usando calcular_ranking_diario y calcular_ranking_semanal

# ---------- COMANDOS DE COMPOSICIÓN ----------
IMAGENES_COMPO = {
    "compo_mono": [
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340970081943582/1_TANK_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340970765746236/2_SUPPORT_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340971352821830/3_DPS_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340971877236806/4_HEALER_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340972393140316/5_PRESS_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340972967624724/6_KITE_MONO.png"
    ],
    "compo_golpe": [
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338457870270524/1_TANKS_GOLPE.png",
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338458423922728/2_SUPPORT_GOLPE.png",
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338459073904640/3_DPS_GOLPE.png",
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338459614842890/4_HEALER_GOLPE.png"
    ],
    "montura_batalla": [
        "https://cdn.discordapp.com/attachments/1371393119458824232/1371393119727128616/BATTLE_MOUNT.png"
    ]
}

@bot.command(name="compo_mono")
async def cmd_compo_mono(ctx):
    for url in IMAGENES_COMPO["compo_mono"]:
        await ctx.send(url)

@bot.command(name="compo_golpe")
async def cmd_compo_golpe(ctx):
    for url in IMAGENES_COMPO["compo_golpe"]:
        await ctx.send(url)

@bot.command(name="montura_batalla")
async def cmd_montura_batalla(ctx):
    for url in IMAGENES_COMPO["montura_batalla"]:
        await ctx.send(url)

# ---------- COMANDO AYUDA ----------
@bot.command(name="ayuda")
async def ayuda(ctx):
    embed = discord.Embed(
        title="📜 Comandos disponibles",
        description="Aquí están todos los comandos del bot de Albion Online:",
        color=discord.Color.purple()
    )

    comandos = [
        ("🏆 !ranking", "Top 10 Fama Total acumulativa"),
        ("⚔️ !pvp", "Top 10 PvP acumulativo"),
        ("🐉 !pve", "Top 10 PvE acumulativo"),
        ("⛏️ !recoleccion", "Top 10 Recolección acumulativo"),
        ("⚒️ !fabricacion", "Top 10 Fabricación acumulativo"),
        ("🏆 !ranking_diario", "Top 10 Fama Total del día"),
        ("⚔️ !pvp_diario", "Top 10 PvP del día"),
        ("🐉 !pve_diario", "Top 10 PvE del día"),
        ("⛏️ !recoleccion_diario", "Top 10 Recolección del día"),
        ("⚒️ !fabricacion_diario", "Top 10 Fabricación del día"),
        ("🏆 !ranking_semanal", "Top 10 Fama Total de la semana"),
        ("⚔️ !pvp_semanal", "Top 10 PvP de la semana"),
        ("🐉 !pve_semanal", "Top 10 PvE de la semana"),
        ("⛏️ !recoleccion_semanal", "Top 10 Recolección de la semana"),
        ("⚒️ !fabricacion_semanal", "Top 10 Fabricación de la semana"),
        ("🛡️ !compo_mono", "Imágenes de la composición Mono"),
        ("💥 !compo_golpe", "Imágenes de la composición Golpe"),
        ("🐎 !montura_batalla", "Imagen de montura de batalla")
    ]

    for nombre, desc in comandos:
        embed.add_field(name=nombre, value=desc, inline=False)

    embed.set_footer(text="Bot de Albion Online - Rankings y composiciones")
    await ctx.send(embed=embed)

# ---------- LOOP AUTOMÁTICO DIARIO ----------
@tasks.loop(time=time(hour=23, minute=0, second=0))
async def publicar_ranking_diario():
    await bot.wait_until_ready()
    jugadores_stats = await obtener_todos_los_datos_gremio()
    ranking_d = calcular_ranking_diario(jugadores_stats)
    guardar_datos_diarios(jugadores_stats)

    canal = bot.get_channel(CHANNEL_ID)
    if canal:
        tipos = [
            ("total","🏆 Fama Total Diario",discord.Color.gold()),
            ("PvP","⚔️ PvP Diario",discord.Color.red()),
            ("PvE","🐉 PvE Diario",discord.Color.green()),
            ("Gathering","⛏️ Recolección Diario",discord.Color.blue()),
            ("Crafting","⚒️ Fabricación Diario",discord.Color.dark_orange())
        ]
        for tipo, titulo, color in tipos:
            ranking_data = generar_ranking_diario_por_tipo(ranking_d, tipo)
            await enviar_ranking_grafico(canal, ranking_data, titulo, color)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    if not publicar_ranking_diario.is_running():
        publicar_ranking_diario.start()

# ---------- RUN BOT ----------
bot.run(TOKEN)
