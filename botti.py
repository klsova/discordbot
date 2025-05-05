import asyncio
import requests
import discord
import random
import json
import os
import time
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()


BOT_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1351888158320754823
GAMES_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
BALANCE = "balances.json"
COOLDOWNS = "cooldowns.json"
COOLDOWN_TIME = 24 * 60 * 60
FREE_CREDITS = 1000

COMMAND_HELP = """
**Botin kommennot**
`!balance` - Näytä nykyinen saldosi
`!slot <panos>` - Pelaa pelikonetta (esim. `!slot 100`)
`!cat` - Näytä söpö kissakuva
`!freecredits` - 1000 ilmaista kolikkoa (voi käyttää 24h välein)
"""

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def load_cooldowns():
    try:
        if os.path.exists(COOLDOWNS) and os.path.getsize(COOLDOWNS) > 0:
            with open(COOLDOWNS, 'r') as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_cooldowns(cooldowns):
    with open(COOLDOWNS, "w") as f:
        json.dump(cooldowns, f, indent=4)
        
def receive_free_credits(user_id):
    cooldowns = load_cooldowns()
    user_id = str(user_id)
    
    if user_id not in cooldowns:
        return True
    
    last_used = cooldowns[user_id]
    current_time = int(time.time())
    return (current_time - last_used) >= COOLDOWN_TIME

def update_cooldowns(user_id):
    cooldowns = load_cooldowns()
    cooldowns[str(user_id)] = int(time.time())
    save_cooldowns(cooldowns)
    
@bot.command(name="freecredits", help="1000 ilmaista kolikkoa 24h välein")
async def free_credits(ctx):
    user_id = ctx.author.id
    
    if not receive_free_credits(user_id):
        cooldowns = load_cooldowns()
        last_used = cooldowns.get(str(user_id), 0)
        remaining_time = COOLDOWN_TIME - (int(time.time()) - last_used)
        hours = remaining_time // 3600
        minutes = (remaining_time % 3600) // 60
        
        await ctx.send(
            f"{ctx.author.mention}, olet jo käyttänyt ilmaiset kolikot\n"
            f"Voit käyttää sen uudelleen {hours} tunnin ja {minutes} minuutin päästä"
        )
        return
    
    new_balance = update_balance(user_id, FREE_CREDITS)
    update_cooldowns(user_id)

    await ctx.send(
        f"{ctx.author.mention}, sait {FREE_CREDITS} ilmaista kolikkoa\n"
        f"Saldosi on nyt {new_balance}"
    )


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

@bot.command(name="cat", help="Näytä söpö kissakuva")
async def cat_pic(ctx):
    try:
        response = requests.get("https://api.thecatapi.com/v1/images/search")
        response.raise_for_status()
        data = response.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            image_url = data[0]["url"]
            await ctx.send(image_url)
        else:
            await ctx.send("Kissakuvaa ei löytynyt :(")
            
    except requests.RequestException as e:
        print(f"Virhe kissakuvan haussa: {e}")
        await ctx.send("Jokin meni pieleen kissakuvan haussa")

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