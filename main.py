import discord
from discord import app_commands
from discord.ext import commands
import json, os, aiohttp, re
from datetime import datetime, timedelta, timezone as dt_timezone
from pytz import timezone as p_timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="ss!", intents=intents)
CONFIG_FILE = "config.json"
IMAGE_LOG_FILE = "image_log.json"
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

config = load_json(CONFIG_FILE)
image_log = load_json(IMAGE_LOG_FILE, default=[])
if not isinstance(image_log, list):
    print("imagelog.json is corupted or not a list. Reinitializing.")
    image_log = []

secret_list = []
with open('secret.txt', "r") as f:
    for item in f.read().split():
        secret_list.append(item)
def is_secret(ctx: discord.Interaction):
    return str(ctx.user.id) in secret_list

def is_cheating(text):
    with open('keywords.txt', 'r') as f:
        keywords = [line.strip() for line in f if line.strip()]
    return any(re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE) for keyword in keywords)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="set_input_channel", description="set input channel for daily memes [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_input_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["insert_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Insert channel set to {channel.mention}", ephemeral=True)
    print(f"set input channel: {channel}")

@bot.tree.command(name="set_output_channel", description="set output channel for daily memes [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_output_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["output_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Output channel set to {channel.mention}", ephemeral=True)
    print(f"set output channel: {channel}")

@bot.tree.command(name="set_autolog_channel", description="set autlog channel [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_autolog_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["autolog_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Autolog channel set to {channel.mention}", ephemeral=True)
    print(f"set autolog channel: {channel}")

@bot.tree.command(name="set_suggestions_channel", description="set suggestions channel (where it shows up) [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_autolog_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["suggest_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Suggestions channel set to {channel.mention}", ephemeral=True)
    print(f"set suggestions channel: {channel}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if str(config.get("insert_channel")) == str(message.channel.id):
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                index = len(image_log) + 1
                filename = f"{index}_{attachment.filename}"
                filepath = os.path.join(IMAGE_DIR, filename)

                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            with open(filepath, "wb") as f:
                                f.write(await resp.read())
                
                image_log.append({
                    "filename": filename,
                    "uploader": str(message.author.id),
                    "timestamp": str(datetime.now(dt_timezone.utc))
                })
                save_json(IMAGE_LOG_FILE, image_log)
                print("image added")
    else:
        if is_cheating(message.content):
            log_channel_id = config.get("autolog_channel")
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="Cheating Flagged",
                        description=message.content,
                        color=discord.Color.red(),
                        timestamp=datetime.now(dt_timezone.utc)
                    )
                    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
                    embed.add_field(name="Channel", value=message.channel.mention)
                    embed.add_field(name="Message Link", value=f"[Jump to message]({message.jump_url})")
                    await log_channel.send(embed=embed)
                    print("cheat logged")
    await bot.process_commands(message)
    
scheduler = AsyncIOScheduler(timezone=p_timezone("US/Central"))
@scheduler.scheduled_job("cron", hour=7, minute=0)
async def daily_post():
    if "output_channel" not in config:
        return
    
    index = config.get("current_index")
    if index >= len(image_log):
        return
    
    entry = image_log[index]
    channel = bot.get_channel(config["output_channel"])
    if not channel:
        return
    
    filepath = os.path.join(IMAGE_DIR, entry["filename"])
    if os.path.exists(filepath):
        await channel.send(f"Daily Image #{index + 1}", file=discord.File(filepath))
        config["current_index"] = index + 1
        save_json(CONFIG_FILE, config)
    print("daily sent")

@bot.tree.command(name="get_past_daily", description="get a past daily meme")
async def get_past_daily(ctx: discord.Interaction, number: int):
    if number <= 0 or number > len(image_log):
        await ctx.response.send_mesage(f"Invalid number: {number}. Your number must be between 1 and {len(image_log)}", ephemeral=True)
        return
    
    entry = image_log[number - 1]
    filepath = os.path.join(IMAGE_DIR, entry["filename"])

    if not os.path.exists(filepath):
        await ctx.response.send_message("Image file missing.", ephemeral=True)
        return
    
    await ctx.response.send_message(f"Image #{number}", file=discord.File(filepath))
    print("past daily sent")

@bot.tree.command(name="purge", description="purge messages [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def purge(ctx: discord.Interaction, count: int):
    await ctx.channel.purge(limit=int(count))
    await ctx.send_message(f"Purged {count} messages")
    print(f"purged {count} messages")

@bot.tree.command(name="add_keyword", description="Add keywords from autolog [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def add_keyword(ctx: discord.Interaction, phrase: str):
    with open('keywords.txt', 'a') as f:
        f.write("\n")
        f.write(phrase)
        f.close()
    await ctx.response.send_message(f"Your phrase '{phrase}' has been added to autolog keywords")
    print(f"added {phrase} to keywords")

@bot.tree.command(name="remove_keyword", description="Remove keywords from autolog [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def remove_keyword(ctx: discord.Interaction, phrase: str):
    with open('keywords.txt', 'r') as f:
        keywords = f.read().splitlines()
    
    normalized_keywords = [k.strip() for k in keywords]
    if phrase.strip() not in normalized_keywords:
        await ctx.response.send_message(f"The phrase '{phrase}' is not in the keyword list.", ephemeral=True)
        return
    normalized_keywords.remove(phrase.strip()+"\n")

    with open('keywords.txt', 'w') as f:
        for kw in normalized_keywords:
            f.write(kw + '\n')
    
    await ctx.response.send_message(f"Removed keyword: '{phrase}'")
    print(f"{phrase} removed form keywords")

@bot.tree.command(name="check_keywords", description="List keywords for autolog [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def check_keywords(ctx: discord.Interaction):
    with open('keywords.txt', 'r') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    if not keywords:
        await ctx.response.send_message("The keyword list is currently empty.", ephemeral=True)
        return
    
    keyword_list = "\n".join(f"- {kw}" for kw in keywords)
    await ctx.response.send_message(f"**Current Autolog Keywords ({len(keywords)}):**\n{keyword_list}", ephemeral=True)
    print("keywords checked")

@bot.tree.command(name="suggest", description="send any suggestions to the admins :)")
async def suggest(ctx: discord.Interaction, suggestion: str):
    log_channel_id = config.get("suggest_channel")
    if log_channel_id:
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="Suggestion",
                description=suggestion,
                color=discord.Color.blurple(),
                timestamp=datetime.now(dt_timezone.utc)
            )
            embed.set_author(name=str(ctx.user), icon_url=ctx.user.display_avatar.url)
            await log_channel.send(embed=embed)
            await ctx.response.send_message("Your suggestion has been sent :)", ephemeral=True)
            print(f"suggestion sent: {suggestion}")
        else:
            await ctx.response.send_message("It seems like there is no log channel. Perhaps spam a admin", ephemeral=True)
    else:
        await ctx.response.send_message("It seems like there is no log channel ID. Perhaps spam a admin", ephemeral=True)

@bot.tree.command(name="test", description="Testing the bot [SECRET ONLY]")
@app_commands.check(is_secret)
async def test(ctx: discord.Interaction):
    await ctx.response.send_message("Test passed", ephemeral=True)
    print("tested")

with open('token.txt', 'r') as f:
    TOKEN = f.read()

bot.run(TOKEN)