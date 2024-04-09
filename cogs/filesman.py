from pydoc import describe
from typing import List
from discord.ext import commands, tasks
from discord import Interaction, app_commands as apc, Embed, ButtonStyle, ui
from dotenv import dotenv_values
import json, re
from rich import print as richPrint
import sqlite3, requests
from xmltodict import parse as xmlParse
from dotenv import dotenv_values
from random import random
from utils_bot import sysWebCheckUser, successMessage, errorMessage, infoMessage
from datetime import datetime
from email.utils import parsedate_tz
from random import randint
from sys import argv

DEBUG_MODE = False

if len(argv) > 1:
    if argv[1] == "--debug":
        DB_PATH = "DB_FULLPATH_DEBUG"
        DEBUG_MODE = True
    else:
        DB_PATH = "DB_FULLPATH"
        richPrint(f"Using: {DB_PATH}")
else:
    DB_PATH = "DB_FULLPATH"
async def setup(bot):
    await bot.add_cog(FilesManager(bot))

class FilesManager(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
    
    def __del__(self):
        richPrint(f"[blue]\[INFO][/blue] : Interrupting FilesManager...")

    def genUIDFile(self):
        alpha = "abcdefABCDEF0123456789"
        uidFile = ""
        for a in range(0,10):
            uidFile += alpha[randint(0,len(alpha)-1)]
        return uidFile
    
    def getDataFiles(self) -> list:
        dataFiles = []
        try:
            with open("./db/files_docs.json", "r", encoding="utf-8") as file: # put two diffrents path depending on DEBUG_MODE
                dataFiles = json.load(file)
        except:
            pass
        return dataFiles

    @apc.command(name="listfiles", description="Liste les fichiers présents sur le portfolio via HTTPS")
    @sysWebCheckUser()
    @apc.describe(startfile="Index de départ", endfile="Index de fin")
    async def listfiles(self, interact:Interaction, startfile:int=-1, endfile:int=-1):
        dataFiles = self.getDataFiles()
        embed = Embed(title="Liste des fichiers présents", description=f"INDEX_START {startfile if startfile >= 0 else 0}, END {endfile if endfile != -1 else '20'}")
        for d in range(startfile if startfile >= 0 else 0, endfile if endfile != -1 and len(dataFiles) >= 20 else len(dataFiles)-1):
            embed.add_field(name=f"Nom: __{dataFiles[d]['pathFile']}__ ID: **__{dataFiles[d]['guidFile']}__**", value=f"**Est privé? __{'Oui' if dataFiles[d]['isPrivate'] else 'Non'}__ Est répertorié? __{'Oui' if not dataFiles[d]['isUnlisted'] else 'Non'}__**", inline=False)
        else:
            embed.add_field(name="INFO:", value="Aucune autre donnée n'a été récupérée !")
        return await interact.response.send_message(embed=embed, delete_after=20.0)
    
    @apc.command(name="addfile", description="Veuillez mettre en ligne le fichier avant usage de la commande.")
    @sysWebCheckUser()
    @apc.choices(isprivate=[
        apc.Choice(name="Privé", value=1),
        apc.Choice(name="Public", value=0)],
        isunlisted=[
        apc.Choice(name="Non Répertorié", value=1),
        apc.Choice(name="Répertorié", value=0)
    ])
    @apc.describe(namefile="Alias (nom) du fichier",
    typefile="Type du fichier",
    isprivate="Visibilité du fichier",
    isunlisted="Indexation du fichier sur le portfolio",
    pathfile="Nom véritable du fichier")
    async def addfile(self, interact:Interaction, namefile:str,typefile:str, isprivate:apc.Choice[int], isunlisted:apc.Choice[int], pathfile:str):
        dataFiles = self.getDataFiles()
        dataFiles.append({
            "nameFile":namefile,
            "typeFile":typefile,
            "guidFile":self.genUIDFile(),
            "isPrivate":bool(isprivate),
            "isUnlisted":bool(isunlisted),
            "pathFile":pathfile
        })
        try:
            with open("./db/files_docs.json", "w", encoding="utf-8") as file: # put two diffrents path depending on DEBUG_MODE
                json.dump(dataFiles, file)
        except:
            return await interact.response.send_message(embed=Embed(title="ERR: Ajout des informations!", description="Veuillez vérifier les droits de lecture écriture ou consulter les Logs !", color=0xf1a004))
        return await interact.response.send_message(embed=Embed(title="Ajout effectué !", description="L'insertion des nouvelles données ont bien été effectués !", color=0x3f8ffc))

    @apc.command(name="delfile", description="Retire la référence du fichier via l'ID")
    @sysWebCheckUser()
    @apc.describe(uidfile="UID du fichier")
    async def delfile(self, interact:Interaction, uidfile:str):
        dataFiles = self.getDataFiles()
        found = False
        for d in range(0,len(dataFiles)):
            if dataFiles[d]["guidFile"] == uidfile:
                del dataFiles[d]
                found = True
                break
        if found:
            return await interact.response.send_message(embed=Embed(title=f"La référence UID:{uidfile} à ce fichier a bien été retiré !", color=0x3F8FFC))
        return await interact.response.send_message(embed=Embed(title=f"Aucune correspondance n'a été trouvé avec l'UID {uidfile} !", color=0xf1a004))