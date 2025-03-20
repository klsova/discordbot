import asyncio
import requests
import discord

BOT_TOKEN = #insert token here
CHANNEL_ID = 1351888158320754823
GAMES_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def fetchFreeGames():
    response = requests.get(GAMES_URL)
    data = response.json()
    
    games = data["data"]["Catalog"]["searchStore"]["elements"]
    free_games = [game for game in games if game["price"]["totalPrice"]["discountPrice"] == 0] # Tarkistaa onko peli täysin ilmainen
    
    return free_games

async def send_free_game_updates():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    
    while True:
        free_games = await fetchFreeGames()
        for game in free_games:
            title = game["title"]
            url = game["productSlug"]
            if url:  # Jostain syystä URLia ei aina ole, tai sit mä en vaa osaa parsia tota filua oikein :D
                message = f"Nyt ois sitä ilmasta peliä: **{title}**\n [Täällä näi](https://store.epicgames.com/en-US/p/{url})"
            else:
                message = f"Nyt ois sitä ilmasta peliä: **{title}**\n (URL ei saatavilla)"
            await channel.send(message)
        await asyncio.sleep(86400) # Päivitetään aina päivittäin
        
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(send_free_game_updates())
    
client.run(BOT_TOKEN)