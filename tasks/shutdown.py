from discord.ext import tasks, commands
import pypresence
from rich import print as richPrint

async def setup(bot):
    await bot.add_cog(ShutdownManager(bot))

class ShutdownManager(commands.Cog):
    def __init__(self, bot : commands.Bot):
        self.bot = bot
    
    def __del__(self):
        richPrint(f"[blue]\[INFO][/blue] : Interrupting ShutdownManager...")

    async def setup_hook(self):
        await self.checkStatus.start()
        richPrint("[blue][INFO] [/blue]: ShutdownManager has been started!")

    async def cog_unload(self):
        self.checkStatus.cancel()

    @tasks.loop(seconds=10)
    async def checkStatus(self):
        with open("./status.txt", "r", encoding="utf-8") as file:
            status = file.read()
        richPrint(f"Status: {status}")
        if status.startswith("stop"):
            richPrint("[yellow][WARN] [/yellow]: Bot has been stopped!")
            self.close()

    @checkStatus.before_loop
    async def before_checkStatus(self):
        await self.bot.wait_until_ready()