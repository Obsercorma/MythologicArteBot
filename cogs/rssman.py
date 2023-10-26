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

async def setup(bot):
    global appChoices
    rssman = RSSManager(bot)
    await bot.add_cog(rssman)


class RSSManager(commands.Cog):
    appChoices = []
    lstCategs:list

    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.envsValues = dotenv_values(".env")
        self.postRSSFeeds.start()
        self.newsHasStarted = False
        self.dbRSS = sqlite3.connect(self.envsValues["DB_FULLPATH"], isolation_level=None)
        appChoices = [apc.Choice(name=categ["name"],value=categ["value"]) for categ in self.getCategs()]

    def __del__(self):
        richPrint("[blue]\[INFO][/blue] : Interrupting RSSManager...")
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
        except sqlite3.Error as e:
            richPrint(e)
            return False
    def getRSSFeeds(self):
        rssFeeds = []
        with open("./rssFeeds.json", "r", encoding="utf-8") as file:
            rssfeeds = json.load(file)
        return rssfeeds

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
            embed.add_field(name=f"#{i}", value=f"__{rssfeeds[i]['link']}__, catégorie: **{rssfeeds[i]['nameCateg']}**", inline=False)
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
    @apc.describe(idcateg="Identifiant de la catégorie", action="Conserver ou supprimer les articles de la catégorie")
    @apc.choices(action=[
        apc.Choice(name="Conserver et retirer", value=1), 
        apc.Choice(name="Supprimer", value=2)
    ])
    async def removecategrss(self, interact:Interaction, idcateg:int, action:apc.Choice[int]):
        categFeed = self.getCategs()
        if action.value == 1:
            req = self.dbRSS.cursor()
            req.execute("UPDATE categsFeed SET isHidden = TRUE WHERE idCateg = ?", [idcateg])
            self.dbRSS.commit()
            req.close()
            return await interact.response.send_message(embed=infoMessage(description=f"Conservation et retrait des articles effectué !"))
        elif action.value == 2:
            req = self.dbRSS.cursor()
            req.execute("UPDATE categsFeed SET isHidden = TRUE WHERE idCateg = ?", [idcateg])
            req.execute("DELETE FROM data_feeds WHERE idCateg = ?", [idcateg])
            self.dbRSS.commit()
            req.close()

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
            SELECT D.titlePost,D.linkPost,D.datePost,C.descCateg FROM data_feeds D 
            INNER JOIN categsFeed C ON D.idCateg = C.idCateg
            WHERE C.isHidden = FALSE ORDER BY D.datePost LIMIT ?""", [nbrCheck])
            res = req.fetchall()
            embed = Embed(title=f"Liste des {nbrCheck} derniers articles", color=0x3F8FFC)
            for art in res:
                tmpDate = parsedate_tz(art[2])
                embed.add_field(name=art[0], value=f"**[Lien article]({art[1]})**\nAjouté le {tmpDate[2]:02d}/{tmpDate[1]:02d}/{tmpDate[0]} {tmpDate[3]:02d}:{tmpDate[4]:02d} | Catégorie: {art[3]}", inline=False)
            return await interact.response.send_message(embed=embed)
        except sqlite3.Error as e:
            richPrint(e)
        return await interact.response.send_message(embed=errorMessage(description=f"Une erreur s'est produite lors de la récupération des {nbrCheck} derniers articles !"))

    ### TASKS ###
    @tasks.loop(minutes=10)
    async def postRSSFeeds(self):
        richPrint("[blue]\[TASK_INFO][/blue]: Apply non-updated and non-sent RSS Feeds...")
        rssFeeds = self.getRSSFeeds()
        for rss in rssFeeds:
            if not rss["issent"] or not rss["isupdated"]:
                try:
                    cur = self.dbRSS.cursor()
                    cur.execute("INSERT INTO feeds(nameFeed,linkFeed,categFeed) VALUES(?,?,?);",[
                        rss["name"],
                        rss["link"],
                        rss["categ"]
                    ])
                    dbFeeds.commit()
                    cur.close()
                    richPrint(f"[blue][INFO][/blue]: RSS Feed {rss['name']} updated!")
                except sqlite3.Error:
                    richPrint(f"[red][WARNING][/red]: RSS Feed {rss['name']} cannot be inserted!")
                rss["issent"] = True
                rss["isupdated"] = True
        self.setRSSFeeds(rssFeeds)
        if not self.newsHasStarted:
            self.newsHasStarted = True
            self.postRSSNews.start()

    @tasks.loop(seconds=20)
    async def postRSSNews(self):
        # richPrint("[blue]\[INFO_TASK][/blue]: fetch RSS News")
        rssFeeds = self.getRSSFeeds()
        #richPrint(len(rssFeeds))
        try:
            for rss in rssFeeds:
                if not rss["ishidden"]:
                    richPrint(f"[yellow]Fetch {rss['name']}[/yellow]")
                    session = requests.Session()
                    req = session.get(rss["link"])
                    res = xmlParse(req.content.decode("utf-8"), encoding="utf-8")
                    session.close()
                    #richPrint(rss)
                    for itemRSS in res["rss"]["channel"]["item"]:
                        curSelect = self.dbRSS.cursor()
                        curSelect.execute("SELECT COUNT(*) FROM data_feeds WHERE guidPost=?;", [itemRSS["guid"]])
                        selectRowCount = curSelect.fetchone()
                        curSelect.close()
                        # richPrint(selectRowCount[0], type(selectRowCount[0]))
                        if selectRowCount[0] < 1:
                            curInsert = sqlPostFeed.cursor()
                            curInsert.execute("""
                            INSERT INTO data_feeds(guidPost,titlePost,linkPost,descPost,datePost,idFeed,idCateg)
                            VALUES(?,?,?,?,?,?,?);
                            """,[
                                itemRSS["guid"],
                                itemRSS["title"],
                                itemRSS["link"],
                                (itemRSS["description"] if not itemRSS["description"] is None else "Aucune Description"),
                                itemRSS["pubDate"],
                                rss["idname"],
                                rss["categ"]
                            ])
                            sqlPostFeed.commit()
                            curInsert.close()
                            richPrint(f"[green]\[SUCCESS][/green]: Post {itemRSS['guid']} inserted!")
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