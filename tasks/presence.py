from discord.ext import tasks, commands
import pypresence
from rich import print as richPrint

async def setup(bot):
    await bot.add_cog(Presence(bot))

class Presence(commands.Cog):
    def __init__(self, bot : commands.Bot):
        self.bot = bot
    
    def __del__(self):
        richPrint(f"[blue]\[INFO][/blue] : Interrupting Presence...")

    async def setup_hook(self):
        self.application_id = "1160132244497780746"
        self.rpc = pypresence.Presence(self.application_id)
        self.rpc.connect()
        await self.updatePresence.start()

    async def cog_unload(self):
        self.updatePresence.cancel()

    @tasks.loop(minutes=1)
    async def updatePresence(self):
        self.rpc.update(state="Bot de MythologicArte", details="Bot de modération", large_image="icon")

    @updatePresence.before_loop
    async def before_updatePresence(self):
        await self.bot.wait_until_ready()