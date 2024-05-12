from datetime import datetime
from discord import Interaction, app_commands as apc
from discord import Embed
import json
from rich import print as richPrint
from datetime import datetime

SYS_WEB_ID = 1166018238656827506
data_roles = {}
with open("./db/rolesInfos.json", "r", encoding="utf-8") as file:
    data_roles = json.load(file)

def sysWebCheckUser():
    def predicate(interact:Interaction):
        for role in interact.user.roles:
            if role.id == SYS_WEB_ID:
                return True
        return False
    return apc.check(predicate)

def isModerator(interact:Interaction):
    def predicate():
        for role in interact.user.roles:
            if data_roles["moderator"]["id"] == role.id or data_roles["admin"]["id"] == role.id:
                return True
        return False
    return apc.check(predicate)

def isAdmin(interact:Interaction):
    def predicate():
        for role in interact.user.roles:
            if data_roles["admin"]["id"] == role.id:
                return True
        return False
    return apc.check(predicate)


### LOGS MESSAGE WITH RICH ###


def printLogSuccess(content:str, putDate:bool)->None:
    date = datetime.now().strftime('(%m.%d.%Y, %H-%M-%S)')
    richPrint(f"[green]\[SUCCESS][/green] {date if putDate else ''}: {content}")

def printLogInfo(content:str, putDate:bool)->None:
    date = datetime.now().strftime('(%m.%d.%Y, %H-%M-%S)')
    richPrint(f"[blue]\[INFO][/blue] {date if putDate else ''}: {content}")


def printLogWarn(content:str, putDate:bool)->None:
    date = datetime.now().strftime('(%m.%d.%Y, %H-%M-%S)')
    richPrint(f"[yellow]\[WARN][/yellow] {date if putDate else ''}: {content}")

    
def printLogError(content:str, putDate:bool)->None:
    date = datetime.now().strftime('(%m.%d.%Y, %H-%M-%S)')
    richPrint(f"[red]\[ERROR][/red] {date if putDate else ''}: {content}")

### EMBED MESSAGES ###

def successMessage(**kwargs)->Embed:
    return Embed(title="Requête exécuté !", description=kwargs["description"], color=0x29C90D)

def errorMessage(**kwargs)->Embed:
    return Embed(title="Échec de la requête !", description=kwargs["description"], color=0xF1A004)

def infoMessage(**kwargs)->Embed:
    return Embed(title="INFO:", description=kwargs["description"], color=0x3F8FFC)