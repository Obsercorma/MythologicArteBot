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

if len(argv) > 1:
    if argv[1] == "--debug":
        DB_PATH = "DB_FULLPATH_DEBUG"
    else:
        DB_PATH = "DB_FULLPATH"
        richPrint(f"Using: {DB_PATH}")
else:
    DB_PATH = "DB_FULLPATH"
async def setup(bot):
    rssman = RSSManager(bot)
    await bot.add_cog(rssman)

def genUID(strlen=16)->str:
    s=""
    alpha="abcdef1234567890"
    for a in range(strlen):
        s+= alpha[randint(0,len(alpha)-1)]
    return s

def checkURL(url:str)->bool:
    regexList = [
        "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$",
        "^[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
    ]
    for regex in regexList:
        if re.match(regex, url):
            return True
    return False       

def getCategs():
    dbCategs = []
    env_values = dotenv_values(".env")
    try:
        cur = sqlite3.connect(env_values[DB_PATH], isolation_level=None).cursor()
        res = cur.execute("SELECT * FROM categsFeed", [])
        tmpData = cur.fetchall()
        for categ in tmpData:
            dbCategs.append({
                "ishidden":categ[2],
                "name":categ[1],
                "value":categ[0],
            })
        cur.close()
    except sqlite3.Error as e:
        richPrint(e)
    with open("./db/categs.json", "w", encoding="utf-8") as file:
        json.dump(dbCategs, file)
    return dbCategs

def getRSSFeeds():
    rssFeeds = []
    with open("./rssFeeds.json", "r", encoding="utf-8") as file:
        rssfeeds = json.load(file)
    return rssfeeds

appChoices = [apc.Choice(name=categ["name"],value=categ["value"]) for categ in getCategs()]
appChoicesFeeds = [apc.Choice(name=feeds["name"], value=feeds["idname"]) for feeds in getRSSFeeds()]
#richPrint(appChoices, appChoicesFeeds)

class RSSManager(commands.Cog):
    lstCategs:list
    global appChoices, appChoicesFeeds

    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.envsValues = dotenv_values(".env")
        self.postRSSFeeds.start()
        self.newsHasStarted = False
        self.dbRSS = sqlite3.connect(self.envsValues[DB_PATH], isolation_level=None)
        

    def __del__(self):
        richPrint(f"[blue]\[INFO][/blue] : Interrupting RSSManager...")
        self.dbRSS.close()

    def getCategs(self):
        dbCategs = []
        try:
            cur = self.dbRSS.cursor()
            res = cur.execute("SELECT * FROM categsFeed", [])
            tmpData = cur.fetchall()
            for categ in tmpData:
                dbCategs.append({
                    "ishidden":categ[2],
                    "name":categ[1],
                    "value":categ[0],
                })
            cur.close()
        except sqlite3.Error as e:
            richPrint(e)
        with open("./db/categs.json", "w", encoding="utf-8") as file:
            json.dump(dbCategs, file)
        return dbCategs

    def addCateg(self, name:str):
        try:
            categs:list = self.getCategs()
            categs.append({
                "name":name,
                "value":len(categs)+1,
            })
            with open("./db/categs.json", "w", encoding="utf-8") as file:
                json.dump(categs, file)
            cur = self.dbRSS.cursor()
            cur.execute("INSERT INTO categsFeed(descCateg) VALUES(?);",[name])
            self.dbRSS.commit()
            cur.close()
            return True
        except sqlite3.Error as e:
            richPrint(e)
            return False
    def getRSSFeeds(self):
        rssFeeds = []
        try:
            req = self.dbRSS.cursor()
            req.execute("SELECT F.*,C.descCateg FROM feeds F INNER JOIN categsFeed C ON F.categFeed = C.idCateg;")
            tmpFetch = req.fetchall()
            for dtf in tmpFetch:
                rssFeeds.append({
                    "idname":dtf[0],
                    "name":dtf[1],
                    "link":dtf[2],
                    "ishidden":dtf[4],
                    "categ":dtf[3],
                    "nameCateg":dtf[5],
                    "issent":False,
                    "isupdated":False
                })
                req.close()
        except sqlite3.Error as e:
            richPrint(e)
        with open("rssFeeds.json", 'r', encoding="utf-8") as file:
            tmpData = json.load(file)
            for dtj in range(0,len(rssFeeds)-1):
                rssFeeds[dtj]["issent"] = tmpData[dtj]["issent"]
                rssFeeds[dtj]["isupdated"] = tmpData[dtj]["isupdated"]
        return rssFeeds

    def setRSSFeeds(self, obj:list)->list:
        try:
            with open("./rssFeeds.json", "w", encoding="utf-8") as file:
                json.dump(obj, file)
            return True
        except:
            return False

    @apc.command(name="addrssfeed", description="Ajouter un flux RSS")
    @sysWebCheckUser()
    @apc.describe(rssfeedlink="Lien vers le flux RSS",namefeed="Nom du Flux RSS")
    @apc.choices(choices=appChoices)
    async def addrssfeed(self, interact : Interaction, rssfeedlink:str, namefeed:str, choices:apc.Choice[int]):
        regexList = [
            "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$",
            "^[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
        ]
        for reg in regexList:
            if re.match(reg, rssfeedlink):
                rssfeed = self.getRSSFeeds()
                appChoicesFeeds.clear()
                for feed in rssfeed.items():
                    appChoicesFeeds.append(apc.Choice(name=feed["nameFeed"], value=feed["idFeed"]))
                cur = self.dbRSS.cursor()
                cur.execute("SELECT idFeed FROM feeds ORDER BY idFeed DESC", [])
                res = cur.fetchone()
                cur.close()
                sqlVerify.close()
                rssfeed.append({
                    "link":rssfeedlink,
                    "name":namefeed,
                    "idname":res[0]+1,
                    "nameCateg":choices.name,
                    "categ":choices.value,
                    "issent":False,
                    "ishidden":False,
                    "isupdated":True
                })
                if self.setRSSFeeds(rssfeed): return await interact.response.send_message(f"Flux RSS ajouté dans la catégorie {choices.value} !")
        return await interact.response.send_message("Échec lors de l'ajout !")
    
    @apc.command(name="addcategrss", description="Ajout d'une nouvelle catégorie de flux RSS.")
    @sysWebCheckUser()
    @apc.describe(namecateg="Nom de la catégorie à ajouter")
    async def addcategrss(self, interact : Interaction, namecateg : str):
        if not self.addCateg(namecateg):
            return await interact.response.send_message(f"Échec lors de l'ajout de cette catégorie !")
        return await interact.response.send_message(f"Catégorie: {namecateg} a bien été ajouté")

    @apc.command(name="listcategrss", description="Liste toutes les catégories")
    @sysWebCheckUser()
    async def listcategrss(self, interact:Interaction):
        embed = Embed(title="Liste des catégories de flux", color=0x3F8FFC)
        categsFeed = self.getCategs()
        for categ in categsFeed:
            tmpIsHidden = "Oui" if not categ['ishidden'] else "Non"
            embed.add_field(name=f"#{categ['value']}", value=f"__{categ['name']}__. Est publique: {tmpIsHidden}", inline=False)
        return await interact.response.send_message(embed=embed)
    

    @apc.command(name="listrssfeeds", description="Liste les flux RSS ajoutés")
    @sysWebCheckUser()
    async def listrssfeeds(self, interact : Interaction):
        embed = Embed(title="Liste des flux RSS", color=0x3F8FFC)
        rssfeeds = self.getRSSFeeds()
        for i in range(len(rssfeeds)):
            tmpIsHidden = "Oui" if not rssfeeds[i]["ishidden"] else "Non"
            embed.add_field(name=f"#{i}", value=f"__{rssfeeds[i]['link']}__, catégorie: **{rssfeeds[i]['nameCateg']}**.\n Est publique: **{tmpIsHidden}**.", inline=False)
        return await interact.response.send_message(embed=embed)

    @apc.command(name="removerssfeed", description="Retirer un flux RSS")
    @sysWebCheckUser()
    @apc.describe(idlink="Identifiant flux RSS")
    async def removerssfeed(self, interact : Interaction, idlink:int):
        rssfeeds:list = self.getRSSFeeds()
        try:
            infoRSS = rssfeeds[idlink]["link"]
            rssfeeds.pop(idlink)
            self.setRSSFeeds(rssfeeds)
            return await interact.response.send_message(f"Le flux RSS #{idlink}: __{infoRSS}__ a bien été retiré !")
        except IndexError:
            return await interact.response.send_message(f"Le flux RSS #{idlink} renseigné est inexistant !") 

    @apc.command(name="removecategrss", description="Supprime la catégorie selectionné.")
    @sysWebCheckUser()
    @apc.describe(idcateg="Catégorie", action="Conserver ou supprimer les articles de la catégorie")
    @apc.choices(action=[
        apc.Choice(name="Conserver et retirer", value=1), 
        apc.Choice(name="Supprimer", value=2)
    ], idcateg=appChoices)
    async def removecategrss(self, interact:Interaction, idcateg:apc.Choice[int], action:apc.Choice[int]):
        categFeed = self.getCategs()
        if action.value == 1:
            req = self.dbRSS.cursor()
            req.execute("UPDATE categsFeed SET isHidden = TRUE WHERE idCateg = ?", [idcateg.value])
            self.dbRSS.commit()
            req.close()
            return await interact.response.send_message(embed=infoMessage(description=f"Conservation et retrait des articles effectué !"), delete_after=5.0)
        elif action.value == 2:
            req = self.dbRSS.cursor()
            req.execute("DELETE FROM categsFeed WHERE idCateg = ?", [idcateg.value])
            req.execute("DELETE FROM data_feeds WHERE idCateg = ?", [idcateg.value])
            self.dbRSS.commit()
            req.close()
            # for categ in range(len(appChoices)):
            #     if appChoices[categ].value == idcateg.value:
            #         appChoices.remove(categ)
            # await self.bot.tree.sync()
            return await interact.response.send_message(embed=infoMessage(description="Suppression de la catégorie et des articles associés effectués !"), delete_after=5.0)

    @apc.command(name="showcateg", description="Remise en place de la catégorie")
    @sysWebCheckUser()
    @apc.describe(idcateg="Identifiant de la catégorie")
    async def showcateg(self, interact:Interaction, idcateg:int):
        try:
            reqVerify = self.dbRSS.execute("SELECT idCateg FROM categsFeed WHERE idCateg = ?;", [idcateg])
            reqVerify.fetchone()
            if reqVerify.rowcount > 0:
                return await interact.response.send_message(embed=infoMessage(description=f"La catégorie **#{idcateg}** est inexistante !"))
            
            req = self.dbRSS.cursor()
            req.execute("UPDATE categsFeed SET isHidden = FALSE WHERE idCateg = ?;", [idcateg])
            self.dbRSS.commit()
            req.close()
            return await interact.response.send_message(embed=successMessage(description=f"La catégorie **#{idcateg}** est de nouveau rendu accessible"))
        except sqlite3.Error as e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur est survenue lors de l'exécution de la requêtte !"))
    
    @apc.command(name="showlastarticles", description="Affiche les 'N' derniers articles")
    @apc.describe(nbrarticle="Nombre d'articles à récupérer (20 articles MAX)")
    async def showlastarticles(self, interact:Interaction, nbrarticle:int):
        nbrCheck = nbrarticle if nbrarticle<= 15 else 15
        try:
            req = self.dbRSS.cursor()
            req.execute("""
            SELECT D.titlePost,D.linkPost,D.datePost,D.verify_key,C.descCateg FROM data_feeds D 
            INNER JOIN categsFeed C ON D.idCateg = C.idCateg
            WHERE C.isHidden = FALSE ORDER BY D.datePost LIMIT ?""", [nbrCheck])
            res = req.fetchall()
            embed = Embed(title=f"<:news:1167385507764916234> Liste des {nbrCheck} derniers articles", color=0x3F8FFC)
            for art in res:
                tmpDate = parsedate_tz(art[2])
                embed.add_field(name=art[0], value=f"**[Lien article]({art[1]})**\nAjouté le {tmpDate[2]:02d}/{tmpDate[1]:02d}/{tmpDate[0]} {tmpDate[3]:02d}:{tmpDate[4]:02d}\nCatégorie: {art[4]}\nID: **{art[3]}**", inline=False)
            return await interact.response.send_message(embed=embed)
        except sqlite3.Error as e:
            richPrint(e)
        return await interact.response.send_message(embed=errorMessage(description=f"Une erreur s'est produite lors de la récupération des {nbrCheck} derniers articles !"))

    @apc.command(name="updaterss", description="Met à jour les informations du flux RSS")
    @apc.choices(idfeed=appChoicesFeeds)
    @apc.describe(link="Nouveau lien RSS", idfeed="Identifiant flux RSS", namefeed="Nom du flux RSS")
    @sysWebCheckUser()
    async def updaterss(self, interact:Interaction, idfeed:apc.Choice[int], link:str, namefeed:str=None):
        try:
            if not checkURL(link):
                return await interact.response.send_message(embed=errorMessage(description="Le lien RSS renseigné est incorrect !"))
            if namefeed:
                if not re.match("[a-zA-Z0-9\-\_ ]+", namefeed):
                    return await interact.response.send_message(embed=errorMessage(description="Le nom renseigné contient des carractères invalides !"))
            reqVerify = self.dbRSS.cursor()
            reqVerify.execute("SELECT idFeed FROM feeds WHERE idFeed = ?;", [idfeed.value])
            reqVerify.fetchone()
            rc = reqVerify.rowcount
            reqVerify.close()
            if rc > 0:
                return await interact.response.send_message(embed=errorMessage(description="L'identifiant renseigné est inexistant !"))
            req = self.dbRSS.cursor()
            richPrint(f"nameFeed: {namefeed}")
            if not namefeed is None:
                req.execute("UPDATE feeds SET linkFeed = ?, nameFeed = ? WHERE idFeed = ?;", [link, namefeed, idfeed.value])
            else:
                req.execute("UPDATE feeds SET linkFeed = ? WHERE idFeed = ?;", [link,idfeed.value])
                
            self.dbRSS.commit()
            req.close()
            return await interact.response.send_message(embed=successMessage(description="Le flux RSS a bien été mis à jour !"))
        except sqlite3.Error as e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur est survenue lors de la mise à jour du flux RSS !"))

    @apc.command(name="pinarticle", description="Épingle un article RSS.")
    @apc.choices(action=[apc.Choice(name="Épingler", value=1),apc.Choice(name="Retirer", value=0)])
    @apc.describe(idarticle="Identifiant de l'article", action="Action")
    @sysWebCheckUser()
    async def pinarticle(self, interact:Interaction, idarticle:str, action:apc.Choice[int]):
        try:
            req = self.dbRSS.cursor()
            if action.value == 1:
                req.execute("SELECT idFeed FROM data_feeds WHERE verify_key = ? AND isMarked = FALSE;", [idarticle])
                req.fetchone()
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage(description="L'article a déjà été épinglé ou, l'identifiant renseigné n'existe pas !"),delete_after=3.0)
                req.execute("UPDATE data_feeds SET isMarked = TRUE WHERE verify_key = ?", [idarticle])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="L'article a bien été épinglé !"),delete_after=3.0)
            else:
                req.execute("SELECT idFeed FROM data_feeds WHERE verify_key = ? AND isMarked = FALSE;", [idarticle])
                req.fetchone()
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage(description="L'article a déjà été retiré ou, l'identifiant renseigné n'existe pas !"),delete_after=3.0)
                req.execute("UPDATE data_feeds SET isMarked = TRUE WHERE verify_key = ?", [idarticle])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="L'article a bien été retiré !"),delete_after=3.0)
        except sqlite3.Error as e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur s'est produite avec la DB!"),delete_after=3.0)
        


    @apc.command(name="hidearticle", description="Cache un article.")
    @apc.choices(action=[apc.Choice(name="Retirer", value=1),apc.Choice(name="Afficher", value=0)])
    @apc.describe(idarticle="Identifiant de l'article", action="Action")
    @sysWebCheckUser()
    async def hidearticle(self, interact:Interaction, idarticle:str, action:apc.Choice[int]):
        try:
            req = self.dbRSS.cursor()
            if action.value == 1:
                req.execute("SELECT idFeed FROM data_feeds WHERE verify_key = ? AND isHidden = FALSE;", [idarticle])
                req.fetchone()
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage(description="L'article a déjà été retiré ou, l'identifiant n'existe pas !"), delete_after=3.0)
                req.execute("UPDATE data_feeds SET isHidden = TRUE WHERE verify_key = ?;", [idarticle])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="L'article a bien été retiré !"),delete_after=3.0)
            else:
                req.execute("SELECT idFeed FROM data_feeds WHERE verify_key = ? AND isHidden = TRUE;", [idarticle])
                req.fetchone()
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage(description="L'article a déjà visible ou, l'identifiant renseigné n'existe pas !"), delete_after=3.0)
                req.execute("UPDATE data_feeds SET isHidden = FALSE WHERE verify_key = ?;", [idarticle])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="L'article est de nouveau visible !"),delete_after=3.0)
        except sqlite3.Error as e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur s'est produite avec la DB!"),delete_after=3.0)


    @apc.command(name="hidecateg", description="Cache tous les articles de la catégorie concerné.")
    @apc.choices(idcateg=appChoices, action=[apc.Choice(name="Retirer", value=1),apc.Choice(name="Afficher", value=0)])
    @apc.describe(idcateg="Identifiant de la catégorie", action="Action")
    @sysWebCheckUser()
    async def hidecateg(self, interact:Interaction,idcateg:apc.Choice[int], action:apc.Choice[int]):
        try:
            req = self.dbRSS.cursor()
            if action.value == 1:
                req.execute("SELECT idCateg FROM categsFeed WHERE idCateg = ? AND isHidden = FALSE;", [idcateg.value])
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage("La catégorie est déjà visible ou, l'identifiant renseigné n'existe pas !"),delete_after=3.0)
                req.execute("UPDATE categsFeed SET isHidden = TRUE WHERE idCateg = ?;", [idcateg.value])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="La catégorie a bien été retiré !"),delete_after=3.0)
            else:
                req.execute("SELECT idCateg FROM categsFeed WHERE idCateg = ? AND isHidden = TRUE;", [idcateg.value])
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage("La catégorie est déjà été retiré ou, l'identifiant renseigné n'existe pas !"),delete_after=3.0)
                req.execute("UPDATE categsFeed SET isHidden = FALSE WHERE idCateg = ?;", [idcateg.value])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="La catégorie est de nouveau visible !"),delete_after=3.0)
        except sqlite3.Error as e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur s'est produite avec la DB !"),delete_after=3.0)


    @apc.command(name="hidefeed", description="Cache tous les articles de flux RSS concerné.")
    @apc.choices(idfeed=appChoicesFeeds, action=[apc.Choice(name="Retirer", value=1),apc.Choice(name="Afficher", value=0)])
    @apc.describe(idfeed="Identifiant du flux RSS")
    @sysWebCheckUser()
    async def hidefeed(self, interact:Interaction,idfeed:apc.Choice[int], action:apc.Choice[int]):
        try:
            req = self.dbRSS.cursor()
            if action.value == 1:
                req.execute("SELECT idFeed FROM feeds WHERE idFeed = ? AND isHidden = FALSE;", [idfeed.value])
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage("Ce flux RSS est déjà visible ou, l'identifiant renseigné n'existe pas !"),delete_after=3.0)
                req.execute("UPDATE feeds SET isHidden = TRUE WHERE idFeed = ?;", [idfeed.value])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="Le flux RSS a bien été retiré !"),delete_after=3.0)
            else:
                req.execute("SELECT idFeed FROM feeds WHERE idFeed = ? AND isHidden = TRUE;", [idfeed.value])
                rwc = req.rowcount
                if rwc == 0:
                    req.close()
                    return await interact.response.send_message(embed=errorMessage("Le flux RSS a déjà été retiré ou, l'identifiant renseigné n'existe pas !"),delete_after=3.0)
                req.execute("UPDATE feeds SET isHidden = FALSE WHERE idFeed = ?;", [idfeed.value])
                self.dbRSS.commit()
                req.close()
                return await interact.response.send_message(embed=successMessage(description="Le flux RSS a bien été retiré !"),delete_after=3.0)
        except sqlite3.Error as e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur s'est produite avec la DB !"),delete_after=3.0)

    @apc.command(name="hiddenarticles", description="Affiche les articles retirés en fonction de la catégorie.")
    @apc.choices(categ=appChoices)
    @apc.describe(categ="Catégorie")
    @sysWebCheckUser()
    async def hiddenarticles(self, interact:Interaction, categ:apc.Choice[int]):
        try:
            req = self.dbRSS.cursor()
            req.execute("""
            SELECT D.titlePost,D.linkPost,D.datePost,D.verify_key,C.descCateg FROM data_feeds D 
            INNER JOIN categsFeed C ON D.idCateg = C.idCateg 
            WHERE C.idCateg = ? AND D.isHidden = TRUE ORDER BY D.datePost DESC LIMIT 15;""", [categ.value])
            data = req.fetchall()
            embed = Embed(title="Voici tous les articles **cachés** de la catégorie :", color=0x3F8FFC)
            for art in data:
                tmpDate = parsedate_tz(art[2])
                embed.add_field(name=art[0], value=f"**[Lien article]({art[1]})**\nAjouté le {tmpDate[2]:02d}/{tmpDate[1]:02d}/{tmpDate[0]} {tmpDate[3]:02d}:{tmpDate[4]:02d}\nCatégorie: {art[4]}\nID: **{art[3]}**", inline=False)
            else:
                embed.add_field(name="INFO:", value="Aucun articles n'a été retiré !")
            return await interact.response.send_message(embed=embed)
        except e:
            richPrint(e)
            return await interact.response.send_message(embed=errorMessage(description="Une erreur s'est produite lors de la récupération des articles !"), delete_after=3.0)

    ### TASKS ###
    @tasks.loop(minutes=10)
    async def postRSSFeeds(self):
        richPrint("[blue]\[TASK_INFO][/blue]: Apply non-updated and non-sent RSS Feeds...")
        rssFeeds = self.getRSSFeeds()
        #richPrint(rssFeeds)
        # appChoicesFeeds.clear()
        for rss in rssFeeds:
            # appChoicesFeeds.append(apc.Choice(name=rss["name"], value=rss["idname"]))
            if not rss["issent"] or not rss["isupdated"]:
                try:
                    req = self.dbRSS.cursor()
                    req.execute("SELECT COUNT(*) FROM feeds WHERE nameFeed = ?;", [rss["name"]])
                    rwc = req.fetchone()
                    if rwc[0] > 0:
                        req.close()
                        continue
                    req.execute("INSERT INTO feeds(nameFeed,linkFeed,categFeed) VALUES(?,?,?);",[
                        rss["name"],
                        rss["link"],
                        rss["categ"]
                    ])
                    self.dbRSS.commit()
                    req.close()
                    richPrint(f"[blue][INFO][/blue]: RSS Feed {rss['name']} updated!")
                except sqlite3.Error:
                    richPrint(f"[red][WARNING][/red]: RSS Feed {rss['name']} cannot be inserted!")
                rss["issent"] = True
                rss["isupdated"] = True
        # await self.bot.tree.sync()
        self.setRSSFeeds(rssFeeds)
        if not self.newsHasStarted:
            self.newsHasStarted = True
            self.postRSSNews.start()

    @tasks.loop(minutes=1)
    async def postRSSNews(self):
        rssFeeds = self.getRSSFeeds()
        try:
            for rss in rssFeeds:
                if not rss["ishidden"]:
                    richPrint(f"[yellow]Fetch {rss['name']}[/yellow]")
                    session = requests.Session()
                    req = session.get(rss["link"])
                    res = xmlParse(req.content.decode("utf-8"), encoding="utf-8")
                    session.close()
                    #richPrint(rss)
                    for _itemRSS in res["rss"]["channel"].items():
                        if _itemRSS[0] == "item":
                            for itemRSS in _itemRSS[1]:
                                #richPrint(itemRSS)
                                verify_key = genUID()
                                curSelect = self.dbRSS.cursor()
                                curSelect.execute("SELECT COUNT(*) FROM data_feeds WHERE guidPost=?;", [itemRSS["guid"]])
                                selectRowCount = curSelect.fetchone()
                                curSelect.close()
                                # richPrint(selectRowCount[0])
                                if selectRowCount[0] < 1:
                                    curInsert = self.dbRSS.cursor()
                                    curInsert.execute("""
                                    INSERT INTO data_feeds(verify_key,guidPost,titlePost,linkPost,descPost,datePost,idFeed,idCateg)
                                    VALUES(?,?,?,?,?,?,?,?);
                                    """,[
                                        verify_key,
                                        itemRSS["guid"],
                                        itemRSS["title"],
                                        itemRSS["link"],
                                        (itemRSS["description"] if not itemRSS["description"] is None else "Aucune Description"),
                                        itemRSS["pubDate"],
                                        rss["idname"],
                                        rss["categ"]
                                    ])
                                    self.dbRSS.commit()
                                    curInsert.close()
                                    richPrint(f"[green]\[SUCCESS][/green]: Post {verify_key} inserted!")
        except sqlite3.Error as e:
            richPrint(e.args)

    ### ERRORS HANDLING METHODS ###
    @listrssfeeds.error
    async def on_error_listrssfeeds(self, interact:Interaction,error):
        if isinstance(error, apc.errors.CheckFailure):
            await interact.response.send_message("Vous n'avez pas les permissions d'exécuter cette commande")
    
    @addrssfeed.error
    async def on_error_addrssfeed(self, interact:Interaction,error):
        if isinstance(error, apc.errors.CheckFailure):
            await interact.response.send_message("Vous n'avez pas les permissions d'exécuter cette commande")
    
    @addcategrss.error
    async def on_error_addcategrss(self, interact:Interaction,error):
        if isinstance(error, apc.errors.CheckFailure):
            await interact.response.send_message("Vous n'avez pas les permissions d'exécuter cette commande")
    @removerssfeed.error
    async def on_error_removerssfeed(self, interact:Interaction,error):
        if isinstance(error, apc.errors.CheckFailure):
            await interact.response.send_message("Vous n'avez pas les permissions d'exécuter cette commande")
    @listcategrss.error
    async def on_error_listcategrss(self, interact:Interaction,error):
        # print(error)
        if isinstance(error, apc.errors.CheckFailure):
            await interact.response.send_message("Vous n'avez pas les permissions d'exécuter cette commande")
        elif isinstance(error, CommandInvokeError):
            await interact.response.send_message(
                embed=errorMessage(description=f"Vous ne pouvez pas retirer cette catégorie (Verifiez qu'aucun articles ne dépendent de cette dernière)!"))
