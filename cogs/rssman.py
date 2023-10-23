from discord.ext import commands, tasks
from discord import Interaction, app_commands as apc, Embed
from dotenv import dotenv_values
import json, re
from rich import print as richPrint
import sqlite3, requests
from xmltodict import parse as xmlParse
from dotenv import dotenv_values
from random import random


def getCategs():
    dbCategs = []
    sqlCateg = sqlite3.connect(dotenv_values(".env")["DB_FULLPATH"])
    cur = sqlCateg.cursor()
    res = cur.execute("SELECT * FROM categsFeed", [])
    tmpData = cur.fetchall()
    for categ in tmpData:
        dbCategs.append({
            "name":categ[1],
            "value":categ[0],
        })
    cur.close()
    sqlCateg.close()
    with open("./db/categs.json", "w", encoding="utf-8") as file:
        json.dump(dbCategs, file)
    return dbCategs

def addCateg(name:str):
    try:
        categs:list = getCategs()
        categs.append({
            "name":name,
            "value":len(categs)+1,
        })
        with open("./db/categs.json", "w", encoding="utf-8") as file:
            json.dump(categs, file)
        return True
        sqlCateg = sqlite3.connect(dotenv_values(".env")["DB_FULLPATH"], isolation_level=None)
        cur = sqlCateg.cursor()
        res = cur.execute("INSERT INTO categsFeed(descCateg) VALUES(:descCateg);",[name])
        sqlCateg.commit()
        cur.close()
        sqlCateg.clsoe()
    except:
        return False
def getRSSFeeds()->list:
    rssFeeds = []
    with open("./rssFeeds.json", "r", encoding="utf-8") as file:
        rssfeeds = json.load(file)
    return rssfeeds

def setRSSFeeds(obj:list)->list:
    try:

        with open("./rssFeeds.json", "w", encoding="utf-8") as file:
            json.dump(obj, file)
        return True
    except:
        return False

async def setup(bot):
    await bot.add_cog(RSSManager(bot))


class RSSManager(commands.Cog):
    
    dbCategs:list

    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.envsValues = dotenv_values(".env")
        self.postRSSFeeds.start()
        self.newsHasStarted = False

    @apc.command(name="addrssfeed", description="Ajouter un flux RSS")
    @commands.has_role(985918266490904657)
    @apc.describe(rssfeedlink="Lien vers le flux RSS",namefeed="Nom du Flux RSS")
    @apc.choices(choices=[apc.Choice(name=categ["name"],value=categ["value"]) for categ in getCategs()])
    async def addrssfeed(self, interact : Interaction, rssfeedlink:str, namefeed:str, choices:apc.Choice[int]):
        regexList = [
            "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$",
            "^[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
        ]
        for reg in regexList:
            if re.match(reg, rssfeedlink):
                rssfeed = getRSSFeeds()
                sqlVerify = sqlite3.connect(self.envsValues["DB_FULLPATH"], isolation_level=None)
                cur = sqlVerify.cursor()
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
                if setRSSFeeds(rssfeed): return await interact.response.send_message(f"Flux RSS ajouté dans la catégorie {choices.value} !")
        return await interact.response.send_message("Échec lors de l'ajout !")
    
    @apc.command(name="addcategrss", description="Ajout d'une nouvelle catégorie de flux RSS.")
    @commands.has_role(985918266490904657)
    @apc.describe(namecateg="Nom de la catégorie à ajouter")
    async def addcategrss(self, interact : Interaction, namecateg : str):
        if not addCateg(namecateg):
            return await interact.response.send_message(f"Échec lors de l'ajout de cette catégorie !")
        return await interact.response.send_message(f"Catégorie: {namecateg} a bien été ajouté")

    @apc.command(name="listrssfeeds", description="Liste les flux RSS ajoutés")
    @commands.has_role(985918266490904657)
    async def listrssfeeds(self, interact : Interaction):
        embed = Embed(title="Liste des flux RSS", color=0x3F8FFC)
        rssfeeds = getRSSFeeds()
        for i in range(len(rssfeeds)):
            embed.add_field(name=f"#{i}", value=f"__{rssfeeds[i]['link']}__, catégorie: **{rssfeeds[i]['nameCateg']}**", inline=False)
        return await interact.response.send_message(embed=embed)

    @apc.command(name="removerssfeed", description="Retirer un flux RSS")
    @commands.has_role(985918266490904657)
    @apc.describe(idlink="Identifiant flux RSS")
    async def removerssfeed(self, interact : Interaction, idlink:int):
        rssfeeds:list = getRSSFeeds()
        try:
            infoRSS = rssfeeds[idlink]["link"]
            rssfeeds.pop(idlink)
            setRSSFeeds(rssfeeds)
            return await interact.response.send_message(f"Le flux RSS #{idlink}: __{infoRSS}__ a bien été retiré !")
        except IndexError:
            return await interact.response.send_message(f"Le flux RSS #{idlink} renseigné est inexistant !") 

    ### TASKS ###
    @tasks.loop(minutes=10)
    async def postRSSFeeds(self):
        richPrint("[blue]\[TASK_INFO][/blue]: Apply non-updated and non-sent RSS Feeds...")
        rssFeeds = getRSSFeeds()
        dbFeeds = sqlite3.connect(self.envsValues["DB_FULLPATH"], isolation_level=None)
        for rss in rssFeeds:
            if not rss["issent"] or not rss["isupdated"]:
                try:
                    cur = dbFeeds.cursor()
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
        setRSSFeeds(rssFeeds)
        dbFeeds.close()
        if not self.newsHasStarted:
            self.newsHasStarted = True
            self.postRSSNews.start()

    @tasks.loop(seconds=20)
    async def postRSSNews(self):
        # richPrint("[blue]\[INFO_TASK][/blue]: fetch RSS News")
        rssFeeds = getRSSFeeds()
        #richPrint(len(rssFeeds))
        try:
            sqlPostFeed = sqlite3.connect(self.envsValues["DB_FULLPATH"], isolation_level=None)
            for rss in rssFeeds:
                richPrint(f"[yellow]Fetch {rss['name']}[/yellow]")
                session = requests.Session()
                req = session.get(rss["link"])
                res = xmlParse(req.content.decode("utf-8"), encoding="utf-8")
                session.close()
                #richPrint(rss)
                for itemRSS in res["rss"]["channel"]["item"]:
                    curSelect = sqlPostFeed.cursor()
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
                            itemRSS["description"],
                            itemRSS["pubDate"],
                            rss["idname"],
                            rss["categ"]
                        ])
                        sqlPostFeed.commit()
                        curInsert.close()
                        richPrint(f"[green]\[SUCCESS][/green]: Post {itemRSS['guid']} inserted!")
            sqlPostFeed.close()
        except sqlite3.Error as e:
            richPrint(e.args)
            sqlPostFeed.close()

