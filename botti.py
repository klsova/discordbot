import asyncio
import requests
import discord
import random
import json
import os
from discord.ext import commands

BOT_TOKEN = "bot token here"
CHANNEL_ID = 1351888158320754823
GAMES_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
BALANCE = "balances.json"

COMMAND_HELP = """
**Botin kommennot**
`!balance` - Näytä nykyinen saldosi
`!slot <panos>` - Pelaa pelikonetta (esim. `!slot 100`)
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "🍉", "7️⃣"]
STARTING_BALANCE = 1000

def load_balance():
    try:
        if os.path.exists(BALANCE) and os.path.getsize(BALANCE) > 0:
            with open(BALANCE, 'r') as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_balance(balance):
    with open(BALANCE, 'w') as f:
        json.dump(balance, f, indent=4)
        
def fetch_balance(user_id):
    balance = load_balance()
    return balance.get(str(user_id), STARTING_BALANCE)

def update_balance(user_id, amount):
    balance = load_balance()
    user_id = str(user_id)
    current_balance = balance.get(user_id, STARTING_BALANCE)
    new_balance = current_balance + amount
    balance[user_id] = new_balance
    save_balance(balance)
    return new_balance
         
@bot.command(name="balance", aliases=["bal"], help="Näytä tämänhetkinen saldo")
async def show_balance(ctx):
    balance = fetch_balance(ctx.author.id)
    await ctx.send(f"{ctx.author.mention}, saldosi on {balance}")

@bot.command(name="slot", help="Tervetuloa kasinolle, pelaa käyttämällä komentoa !slot *numero*")
async def slot_machine(ctx, bet: int):
    if bet <= 0:
        await ctx.send("Panoksen täytyy olla suurempi kuin 0")
        return
    current_balance = fetch_balance(ctx.author.id)
    
    if bet > current_balance:
        await ctx.send(f"Saldosi ei riitä! Saldosi on {current_balance}")
        return
    
    update_balance(ctx.author.id, -bet)
    

    slots = [random.choice(SLOT_SYMBOLS) for _ in range(3)] 
    
    if slots[0] == slots[1] == slots[2]:
        winnings = bet * 10
        result = f"**JACKPOT!** Voitit {winnings}!"
    elif slots[0] == slots[1] or slots[1] == slots[2] or slots[0] == slots[2]:
        winnings = bet * 2
        result = f"Voitit {winnings}!"
    else:
        winnings = 0
        result = "Ei voittoa, yritä uudelleen!"
    
    if winnings > 0:
        new_balance = update_balance(ctx.author.id, winnings)
    else:
        new_balance = fetch_balance(ctx.author.id)
    
    await ctx.send(
        f"{ctx.author.mention} pyöräytti slot-konetta:\n"
        f"[ {slots[0]} | {slots[1]} | {slots[2]} ]\n"
        f"{result}\n"
        f"Saldo: {new_balance} kolikkoa"
    )


async def fetchFreeGames():
    try:
        response = requests.get(GAMES_URL)
        response.raise_for_status()
        data = response.json()
    
        if not data or "data" not in data or "Catalog" not in data["data"]:
            return []
    
        games = data["data"]["Catalog"]["searchStore"]["elements"]
        free_games = []

        for game in games:
            try:
                if game["price"]["totalPrice"]["discountPrice"] == 0:
                    has_promotion = any([
                        game.get("promotions", {}).get("promotionalOffers"),
                        game.get("promotions", {}).get("upcomingPromotionalOffers")
                    ])

                    if has_promotion:
                        url = None
                        if game.get("catalogNs", {}).get("mappings"):
                            for mapping in game["catalogNs"]["mappings"]:
                                if mapping.get("pageSlug"):
                                    url = f"https://store.epicgames.com/en-Us/p/{mapping['pageSlug']}"
                                break
                            
                        if not url and game.get("productSlug"):
                            url = f"http://store.epicgames.com/en-US/p/{game['productSlug']}"
                            
                        if not url and game.get("urlSlug"):
                            url = f"https://store.epicgames.com/en-US/p/{game['urlSlug']}"
                        
                        if not url and game.get("offerMappings"):
                            for mapping in game["offerMappings"]:
                                if mapping.get("pageSlug"):
                                    url = f"https://store.epicgames.com/en-US/p/{mapping['pageSlug']}"
                                    break
                        free_games.append({
                            "title": game.get("title"),
                            "url": url
                        })                            
            except (KeyError, TypeError):
                continue
        
        return free_games
    
    except (requests.RequestException, json.JSONDecoder) as e:
        print(f"Virhe pelien haussa: {e}")
        return []

async def send_free_game_updates():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
        
    while True:
        free_games = await fetchFreeGames()
            
        if free_games:
            message = "Ilmaiset pelit Epic Games Storessa tällä hetkellä"
                
        for game in free_games:
            title = game.get("title")
            if game["url"]:
                url = f"{game['url']}"
                message = f"Nyt ois sitä ilmasta peliä: **{title}**\n [Täällä näi]({url})"
            else:
                message = f"Nyt ois sitä ilmasta peliä: **{title}**\n (URL ei saatavilla)"
            await channel.send(message)
        
        await asyncio.sleep(86400)
        
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(COMMAND_HELP)
    if not os.path.exists(BALANCE):
        with open (BALANCE, 'w') as f:
            json.dump({}, f)
    bot.loop.create_task(send_free_game_updates())
    
bot.run(BOT_TOKEN)