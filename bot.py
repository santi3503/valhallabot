from discord.ext import commands, tasks
import discord
import os
import aiohttp
import asyncio

TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

intents = discord.Intents.default()
intents.message_content = True  # Para que lea comandos
bot = commands.Bot(command_prefix="!", intents=intents)


async def obtener_ranking():
    url = f"https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID}/members"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            # Ordenar por fama total y top 10
            ranking = sorted(data, key=lambda x: x["KillFame"], reverse=True)[:10]
            return ranking


@bot.command()
async def ranking(ctx):
    ranking = await obtener_ranking()
    if not ranking:
        await ctx.send("No pude obtener el ranking 😢")
        return

    mensaje = "**🏆 Ranking Top 10 Kill Fame del Gremio 🏆**\n\n"
    for i, jugador in enumerate(ranking, start=1):
        mensaje += f"{i}. {jugador['Name']} — {jugador['KillFame']:,} fama\n"

    await ctx.send(mensaje)


# 🔁 Tarea automática cada día a las 23:00 UTC
@tasks.loop(hours=24)
async def ranking_diario():
    await bot.wait_until_ready()
    canal = bot.get_channel(CHANNEL_ID)
    if canal:
        ranking = await obtener_ranking()
        if not ranking:
            await canal.send("No pude obtener el ranking hoy 😢")
            return

        mensaje = "**🏆 Ranking Diario Top 10 Kill Fame 🏆**\n\n"
        for i, jugador in enumerate(ranking, start=1):
            mensaje += f"{i}. {jugador['Name']} — {jugador['KillFame']:,} fama\n"

        await canal.send(mensaje)


@ranking_diario.before_loop
async def antes_de_loop():
    # Espera hasta las 23:00 UTC exactas para arrancar
    from datetime import datetime, timedelta
    import pytz

    ahora = datetime.now(pytz.UTC)
    proxima = ahora.replace(hour=23, minute=0, second=0, microsecond=0)

    if proxima <= ahora:
        proxima += timedelta(days=1)

    espera = (proxima - ahora).total_seconds()
    await asyncio.sleep(espera)


ranking_diario.start()

bot.run(TOKEN)
