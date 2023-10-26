from discord.ext import commands
from discord import Interaction, app_commands as apc
from rich import print as richPrint
from utils_bot import isModerator, isAdmin

async def setup(bot):
    await bot.add_cog(ClearManager(bot))

class ClearManager(commands.Cog):
    def __init__(self, bot : commands.Bot):
        self.bot = bot
    
    @apc.command(name="clear", description="Efface 'N' messages")
    @apc.describe(nbrmesg="Nombre de messages à effacer")
    @apc.check(isModerator)
    async def clear(self, interact : Interaction, nbrmesg:int):
        try:
            
            async for mesg in interact.channel.history(limit=nbrmesg):
                await mesg.delete()
            return await interact.response.send_message(f"Suppression de {nbrmesg} messages réussi !", delete_after=5.0)
        except Exception as e:
            richPrint(e)
            return await interact.response.send_message("Échec lors de la suppression des derniers messages !", delete_after=5.0)

    @clear.error
    async def on_error_clear(self, interact:Interaction,error):
        print(type(error))