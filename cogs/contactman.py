from discord.ext import commands, tasks
from discord import Interaction, app_commands as apc, Embed, ButtonStyle, ui
from dotenv import dotenv_values
import json, re
from rich import print as richPrint
from utils_bot import sysWebCheckUser
import sqlite3, requests
from sys import argv
from datetime import datetime

config = dotenv_values(".env")

if len(argv) > 1:
    if argv[1] == "--debug":
        DB_PATH_PORTFOLIO = config["DB_PORTFOLIO_PULLPATH_DEBUG"]
    else:
        DB_PATH_PORTFOLIO = config["DB_PORTFOLIO_PULLPATH"]

async def setup(bot):
    await bot.add_cog(ContactManager(bot))

class ContactManager(commands.Cog):
    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.dbRSS = sqlite3.connect(DB_PATH_PORTFOLIO)
    
    def __del__(self):
        richPrint(f"[blue]\[INFO][/blue] : Interrupting ContactManager...")
        self.dbRSS.close()
    
    @apc.command(name="contactemail", description="Agir sur une adresse mail")
    @sysWebCheckUser()
    @apc.describe(actions="Bannir/Debannir une adresse mail")
    @apc.choices(actions=[
        apc.Choice(name="Bannir", value="ban"),
        apc.Choice(name="Débannir", value="unban")
    ])
    async def contactemail(self, interact:Interaction, actions:apc.Choice[str], email:str):
        datenow = datetime.now()
        datefmt = datenow.strftime("%Y-%m-%d %H:%M")
        richPrint(datefmt)
        if actions.value == "ban":
            try:
                self.dbRSS.execute("INSERT INTO banned_emails(email_banned, date_banned) VALUES (?,?)", (email,datefmt))
                self.dbRSS.commit()
                return await interact.response.send_message(f"Adresse mail {email} bannie !", delete_after=3.0)
            except:
                return await interact.response.send_message(f"Impossible de bannir l'adresse mail {email} !", delete_after=3.0)
        elif actions.value == "unban":
            try:
                self.dbRSS.execute("DELETE FROM banned_emails WHERE email_banned = ?", (email,))
                self.dbRSS.commit()
                return await interact.response.send_message(f"Adresse mail {email} débannie !", delete_after=3.0)
            except:
                return await interact.response.send_message(f"Impossible de débannir l'adresse mail {email} !", delete_after=3.0)
