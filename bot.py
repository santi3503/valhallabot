import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import pytz
import os

TOKEN = os.environ['TOKEN']
GUILD_ID = os.environ['GUILD_ID']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- LOOP DEL RANKING ----------
@tasks.loop(hours=24)
async def ranking_diario():
    try:
        guild = bot.get_guild(int(GUILD_ID))
        channel = guild.get_channel(CHANNEL_ID)
        if channel:
            await channel.send("📊 Ranking diario de Albion Online listo 🚀")
            print("✅ Ranking diario enviado correctamente.")
        else:
            print("⚠️ No encontré el canal con ese ID.")
    except Exception as e:
        print(f"❌ Error enviando el ranking: {e}")


@ranking_diario.before_loop
async def antes_de_loop():
    # Espera hasta las 23:00 UTC exactas para arrancar
    ahora = datetime.now(pytz.UTC)
    proxima = ahora.replace(hour=23, minute=0, second=0, microsecond=0)

    if proxima <= ahora:
        proxima += timedelta(days=1)

    espera = (proxima - ahora).total_seconds()
    print(f"⏳ Esperando {espera/3600:.2f} horas hasta las 23:00 UTC para iniciar ranking.")
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
