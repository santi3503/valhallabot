import os
import discord
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# Variables de entorno
TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

intents = discord.Intents.default()
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler()


def obtener_ranking(tipo: str, limite: int = 10):
    miembros = requests.get(
        f"https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID}/members"
    ).json()

    ranking = []

    for m in miembros:
        try:
            player = requests.get(
                f"https://gameinfo.albiononline.com/api/gameinfo/players/{m['Id']}"
            ).json()

            stats = player["LifetimeStatistics"]

            if tipo == "total":
                valor = (
                    stats["PvE"]["Total"]
                    + stats["PvP"]["Total"]
                    + stats["Gathering"]["All"]["Total"]
                    + stats["Crafting"]["Total"]
                )
            elif tipo == "pvp":
                valor = stats["PvP"]["Total"]
            elif tipo == "pve":
                valor = stats["PvE"]["Total"]
            elif tipo == "recoleccion":
                valor = stats["Gathering"]["All"]["Total"]
            elif tipo == "fabricacion":
                valor = stats["Crafting"]["Total"]
            else:
                valor = 0

            ranking.append((m["Name"], valor))
        except:
            pass

    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking[:limite]


async def enviar_ranking():
    canal = client.get_channel(CHANNEL_ID)
    if canal is None:
        print("⚠️ Canal no encontrado, revisá el ID")
        return

    tipos = {
        "🏆 Fama Total": "total",
        "⚔️ PvP": "pvp",
        "🐉 PvE": "pve",
        "⛏️ Recolección": "recoleccion",
        "⚒️ Fabricación": "fabricacion"
    }

    for titulo, tipo in tipos.items():
        ranking = obtener_ranking(tipo)
        mensaje = f"**{titulo} - Top 10 diario**\n\n"
        for i, (name, valor) in enumerate(ranking, start=1):
            mensaje += f"**{i}. {name}** - {valor:,}\n"
        await canal.send(mensaje)


@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")
    # Scheduler para publicar automáticamente a las 23:00
    scheduler.add_job(lambda: asyncio.create_task(enviar_ranking()), "cron", hour=23, minute=0)
    scheduler.start()


@client.event
async def on_message(message):
    if message.author.bot:
        return

    comando = message.content.lower()

    if comando.startswith("!help"):
        respuesta = (
            "**📜 Comandos disponibles:**\n\n"
            "`!ranking` → Top 10 por fama total (PvE + PvP + Recolección + Fabricación)\n"
            "`!pvp` → Top 10 por fama PvP ⚔️\n"
            "`!pve` → Top 10 por fama PvE 🐉\n"
            "`!recoleccion` → Top 10 por fama de recolección ⛏️\n"
            "`!fabricacion` → Top 10 por fama de fabricación ⚒️\n"
        )
        await message.channel.send(respuesta)

    elif comando.startswith("!ranking"):
        ranking = obtener_ranking("total")
        respuesta = "**🏆 Ranking de Fama Total 🏆**\n\n"
    elif comando.startswith("!pvp"):
        ranking = obtener_ranking("pvp")
        respuesta = "**⚔️ Ranking PvP ⚔️**\n\n"
    elif comando.startswith("!pve"):
        ranking = obtener_ranking("pve")
        respuesta = "**🐉 Ranking PvE 🐉**\n\n"
    elif comando.startswith("!recoleccion"):
        ranking = obtener_ranking("recoleccion")
        respuesta = "**⛏️ Ranking Recolección ⛏️**\n\n"
    elif comando.startswith("!fabricacion"):
        ranking = obtener_ranking("fabricacion")
        respuesta = "**⚒️ Ranking Fabricación ⚒️**\n\n"
    else:
        return

    if not comando.startswith("!help"):
        for i, (name, valor) in enumerate(ranking, start=1):
            respuesta += f"**{i}. {name}** - {valor:,}\n"

        await message.channel.send(respuesta)


client.run(TOKEN)

