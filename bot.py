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
        elif tipo.lower() == "pvp":
            valor = j.get("PvP", 0)
        elif tipo.lower() == "pve":
            valor = j.get("PvE", 0)
        elif tipo.lower() == "gathering":
            valor = j.get("Gathering", 0)
        elif tipo.lower() == "crafting":
            valor = j.get("Crafting", 0)
        else:
            valor = 0
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

# ---------- COMPOSICIONES ----------
composiciones = {
    "mono": [
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340970081943582/1_TANK_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340970765746236/2_SUPPORT_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340971352821830/3_DPS_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340971877236806/4_HEALER_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340972393140316/5_PRESS_MONO.png",
        "https://cdn.discordapp.com/attachments/1374340969411117077/1374340972967624724/6_KITE_MONO.png"
    ],
    "golpe": [
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338457870270524/1_TANKS_GOLPE.png",
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338458423922728/2_SUPPORT_GOLPE.png",
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338459073904640/3_DPS_GOLPE.png",
        "https://cdn.discordapp.com/attachments/1374338457438130267/1374338459614842890/4_HEALER_GOLPE.png"
    ],
    "montura": [
        "https://cdn.discordapp.com/attachments/1371393119458824232/1371393119727128616/BATTLE_MOUNT.png"
    ]
}

async def mostrar_compo(ctx, nombre_compo, titulo):
    urls = composiciones.get(nombre_compo.lower(), [])
    if not urls:
        await ctx.send("❌ No hay imágenes disponibles para esta composición.")
        return
    for url in urls:
        embed = discord.Embed(title=titulo, color=discord.Color.blue())
        embed.set_image(url=url)
        await ctx.send(embed=embed)

# ---------- ENVÍO DE GRÁFICOS ----------
async def enviar_ranking_grafico(ctx, ranking, titulo, color):
    archivo = generar_grafico_ranking(ranking, titulo)
    embed = discord.Embed(title=titulo, color=color)
    embed.set_image(url=f"attachment://{archivo}")
    await ctx.send(file=discord.File(archivo), embed=embed)

# ---------- COMANDOS DE COMPOS ----------
@bot.command(name="compo_mono")
async def compo_mono(ctx):
    await mostrar_compo(ctx, "mono", "💥 Composición Mono")

@bot.command(name="compo_golpe")
async def compo_golpe(ctx):
    await mostrar_compo(ctx, "golpe", "⚔️ Composición Golpe")

@bot.command(name="montura_batalla")
async def montura_batalla(ctx):
    await mostrar_compo(ctx, "montura", "🐴 Montura de Batalla")

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
            ("pvp","⚔️ PvP Diario",discord.Color.red()),
            ("pve","🐉 PvE Diario",discord.Color.green()),
            ("gathering","⛏️ Recolección Diario",discord.Color.blue()),
            ("crafting","⚒️ Fabricación Diario",discord.Color.dark_orange())
        ]
        for tipo, titulo, color in tipos:
            ranking_data = generar_ranking_diario_por_tipo(ranking_d, tipo)
            await enviar_ranking_grafico(canal, ranking_data, titulo, color)

# ---------- COMANDO AYUDA ----------
@bot.command(name="ayuda", help="📜 Lista de todos los comandos")
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
        ("💥 !compo_mono", "Muestra la composición Mono"),
        ("⚔️ !compo_golpe", "Muestra la composición Golpe"),
        ("🐴 !montura_batalla", "Muestra la montura de batalla")
    ]

    for nombre, desc in comandos:
        embed.add_field(name=nombre, value=desc, inline=False)

    embed.set_footer(text="Bot de Albion Online - Rankings y composiciones")
    await ctx.send(embed=embed)

# ---------- EVENTO ON_READY ----------
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    if not publicar_ranking_diario.is_running():
        publicar_ranking_diario.start()

# ---------- RUN BOT ----------
bot.run(TOKEN)
