import discord
from discord.ext import commands
from discord import app_commands as apc, Game
from dotenv import dotenv_values
import json
from rich import print as richPrint
from utils_bot import sysWebCheckUser

config = dotenv_values(".env")
with open("./exts.json", "r", encoding="utf-8") as file:
    exts = json.load(file)

class MyBot(commands.Bot):
    syncedCommands = []
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="?", intents=intents)
    
    async def setup_hook(self):
        for ext in exts.values():
            richPrint(f"EXT STATUS: {ext['name']} : {ext['isActive']}!")
            if ext["isActive"]:
                await self.load_extension(f"cogs.{ext['name']}")
        self.syncedCommands = await self.tree.sync()
    
    async def on_ready(self):
        await self.change_presence(activity=Game(name="Administre le serveur Discord MythlogicArte.fr"))
        richPrint(f"Synced commands: {len(self.syncedCommands)}.")


bot = MyBot()

@bot.tree.command(name="reloadext", description="Recharger une extension du bot")
@sysWebCheckUser()
@apc.describe(extname="Nom de l'extension (cog)")
async def reloadext(interact:discord.Interaction, extname:str):
    try:
        richPrint(f"[blue][INFO] [/blue]: Reloading {extname} extension...")
        await bot.reload_extension(f"cogs.{extname}")
        richPrint(f"[green][SUCCESS] [/green]: {extname} extension has been reloaded!")
        return await interact.response.send_message("Rechargement effectué !")
    except:
        richPrint(f"[yellow][WARNING] [/yellow]: Cannot reload {extname} extension!")
        return await interact.response.send_message("Rechargement de l'extension impossible !")
   

@bot.tree.command(name="ping", description="Get pong latency")
@sysWebCheckUser()
async def ping(interact:discord.Interaction):
    bot_latency = round(bot.latency * 1000)
    await interact.response.send_message(f"Pong {bot_latency}ms !")

@reloadext.error
async def on_error_reloadext(interact:discord.Interaction, error):
    richPrint(error)
    await interact.response.send_message("Une erreur est survenu lors du rechargement de l'extension !")

if __name__ == "__main__":
    bot.run(config["TOKEN"])
