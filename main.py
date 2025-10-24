import discord
from discord import app_commands
from discord.ext import commands, tasks
import json, os, aiohttp, re
from datetime import datetime as dtmod, timedelta, time, timezone as dt_timezone
import random
import datetime as dt
#intents and files
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
all_allowed_mention = discord.AllowedMentions(everyone=True, users=True, roles=True, replied_user=True)
no_allowed_mention = discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=False)
bot = commands.Bot(command_prefix="ss!", intents=intents)
CONFIG_FILE = "config.json"
IMAGE_LOG_FILE = "image_log.json"
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# access roles_and_channel.txt, assigns channels and roles, line order specified in readme.md
f = open('roles_and_channels.txt', "r")
flines = f.readlines()
bot_commands_role = flines[0]
bot_commands_role = int(bot_commands_role.rstrip())

hw_reminders_channel = flines[1]
hw_reminders_channel = int(hw_reminders_channel.rstrip())

test_reminders_channel = flines[2]
test_reminders_channel = int(test_reminders_channel.rstrip())

hw_reminders_role = flines[3]
hw_reminders_role = int(hw_reminders_role.rstrip())

test_reminders_role = flines[4]
test_reminders_role = int(test_reminders_role.rstrip())

admin_channel = flines[5]
admin_channel = int(admin_channel.rstrip())

# variables to make code less cluttered
red = discord.Color.red()

# variables for the scheduled functions, the auto meme and the hw/test reminders
# gets the current timezone so you don't have to use UTC, you're welcome
# https://github.com/Rapptz/discord.py/discussions/9547
currenttz = dt.datetime.now().astimezone().tzinfo

# still have to deal with a 24 hr clock tho
# right now it is at 5pm for both hw/test reminders and daily meme
timeToRepeat = dt.time(hour=17, minute=0, tzinfo=currenttz)

# function to open a file with a specific mode, takes only r and a
# since read mode was used with the line.strip thing the entire time and append mode was used in the way that it was,
# I just decided to make a general purpose function for it to decrease clutter
def open_file(file:str, mode:str, strtowrite:str=None):
    if mode == "r":
        # r mode is used many times without this functionality, but there are too many differences to make it worth it to add it to this function
        with open(file, "r") as f:
            return_thing = [line.strip() for line in f if line.strip()]
            f.close()
        return return_thing
    else:
        # same deal with this
        with open(file, 'a') as f:
            f.write(strtowrite)
            f.write("\n")
            f.close()

#for images ig idk wth this is
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

# for that random secret command maiasaura messes with
secret_list = []
with open('secret.txt', "r") as f:
    for item in f.read().split():
        secret_list.append(item)
def is_secret(ctx: discord.Interaction):
    return str(ctx.user.id) in secret_list

# function to see if message may contain cheating MAY PRODUCE FALSE POSITIVES DO NOT BAN PEOPLE JUST CUZ THEY SHOW UP HERE!!!!!!!!!!!!!!!!
def is_cheating(text):
    with open('keywords.txt', 'r') as f:
        keywords = [line.strip() for line in f if line.strip()]
    return any(re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE) for keyword in keywords)

# stuff to say and or do when ready and if there is an error
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} slash commands.")
        if not job_loop.is_running():
            job_loop.start()
            print("job loop has started")
        
        if not daily_post.is_running():
            daily_post.start()
            print("daily post script running")

        channel = bot.get_channel(admin_channel)
        await channel.send("Bot online!")

    except Exception as e:
        print(f"Error syncing commands: {e}")



# calls fuctions to see if people are cheating everytime someone sends a message
@bot.event
async def on_message(message):
    # ignores if the author was the bot
    if message.author.bot:
        return
    # this has smth to do with images im not gonna bother with this
    content = message.content
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
                
                # logs the file's name, author ID, author nickname (dreex added), author username (dreex added) and timestamp
                image_log.append({
                    "filename": filename,
                    "uploaderID": str(message.author.id),
                    "uploaderNickname": str(message.author.nick),
                    "uploaderUsername": str(message.author),
                    "timestamp": str(dt.datetime.now(dt_timezone.utc))
                })
                save_json(IMAGE_LOG_FILE, image_log)
                await bot.get_channel(config.get("insert_channel")).send(f"New image has been logged as #{len(image_log)}!")
                print("image added")
    else:
        # if the message is not an attatchment, checks if cheating and calls the necesary functions and stuff
        if is_cheating(content):
            log_channel_id = config.get("autolog_channel")
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        color=red,
                        title="Cheating Flagged",
                        description=content,
                        timestamp=dt.datetime.now(dt_timezone.utc)
                    )
                    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
                    embed.add_field(name="Channel", value=message.channel.mention)
                    embed.add_field(name="Message Link", value=f"[Jump to message]({message.jump_url})")
                    await log_channel.send(embed=embed)
                    print("cheat logged")
        if "kys" in content.lower():
            # the triple asterisk is discord formatting, makess it so that it's italicized and bolded ⬇️
            await message.reply("We do not tolerate this type of violence in this server. How ***dare*** you!")
        if "kms" in content.lower():
            await message.reply("Do I need to call the suicide prevention lifeline? I'm sure you can do it yourself, it's right on the back of your ID!")
    await bot.process_commands(message)
    
    
# admin only commands

# command for input channel for memes
@bot.tree.command(name="set_input_channel", description="set input channel for daily memes [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_input_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["insert_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Insert channel set to {channel.mention}", ephemeral=True)
    print(f"set input channel: {channel}")

# command for output channel for daily memes
@bot.tree.command(name="set_output_channel", description="set output channel for daily memes [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_output_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["output_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Output channel set to {channel.mention}", ephemeral=True)
    print(f"set output channel: {channel}")

# sets an autolog channel
@bot.tree.command(name="set_autolog_channel", description="set autlog channel [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_autolog_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["autolog_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Autolog channel set to {channel.mention}", ephemeral=True)
    print(f"set autolog channel: {channel}")

# sets a channel where suggestions will appear
@bot.tree.command(name="set_suggestions_channel", description="set suggestions channel (where it shows up) [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def set_autolog_channel(ctx: discord.Interaction, channel: discord.TextChannel):
    config["suggest_channel"] = channel.id
    save_json(CONFIG_FILE, config)
    await ctx.response.send_message(f"Suggestions channel set to {channel.mention}", ephemeral=True)
    print(f"set suggestions channel: {channel}")
    
# deletes x amt of messages
@bot.tree.command(name="purge", description="purge messages [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def purge(ctx: discord.Interaction, count: int=5):
    await ctx.channel.purge(limit=int(count))
    await ctx.send_message(f"Purged {count} messages")
    print(f"purged {count} messages")

# adds a keyword to keywords.txt
@bot.tree.command(name="add_keyword", description="Add keywords from autolog [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def add_keyword(ctx: discord.Interaction, phrase: str):
    # with open('keywords.txt', 'a') as f:
    #     f.write(phrase)
    #     f.write("\n")
    #     f.close()
    open_file('keywords.txt', 'a', phrase)
    await ctx.response.send_message(f"Your phrase ```{phrase}``` has been added to autolog keywords")
    print(f"added {phrase} to keywords")

# removes a keyword from keywords.txt
@bot.tree.command(name="remove_keyword", description="Remove keywords from autolog [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def remove_keyword(ctx: discord.Interaction, phrase: str):
    with open('keywords.txt', 'r') as f:
        keywords = f.read().splitlines()
    
    normalized_keywords = [k.strip() for k in keywords]
    if phrase.strip() not in normalized_keywords:
        await ctx.response.send_message(f"The phrase ```{phrase}``` is not in the keyword list.", ephemeral=True)
        return
    try:
        normalized_keywords.remove(phrase.strip()+"\n")
    except Exception:
        normalized_keywords.remove(phrase.strip())

    with open('keywords.txt', 'w') as f:
        for kw in normalized_keywords:
            f.write(kw + '\n')
    
    await ctx.response.send_message(f"Removed keyword: ```{phrase}```")
    print(f"{phrase} removed from keywords")

# sends a list of the keywords
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
    
# removes a quote from quotes.txt, also reskinned
# quote indexing support
@bot.tree.command(name="remove_quote", description="Remove quote from the list of quotes [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def remove_quote(ctx: discord.Interaction, quote: str=None, index: int=None):
    if quote == None and index == None:
        await ctx.response.send_message("Please provide either a quote or an index", ephemeral=True)
        return
    if quote != None and index != None:
        await ctx.response.send_message("Please provide only one of the two options. Do not provide both the quote and the index", ephemeral=True)
    with open('quotes.txt', 'r') as f:
        quotes = f.read().splitlines()
        if index != None:
            if index >= len(quotes) or index < 0: 
                await ctx.response.send_message(f"Your index {index} is out of bounds. Please provide a valid index in the range [0,{len(quotes)}]")
                return
            quote = quotes[index-1]
    
    normalized_quotes = [k.strip() for k in quotes]
    if quote.strip() not in normalized_quotes:
        await ctx.response.send_message(f"The quote ```{quote}``` is not in the keyword list.", ephemeral=True)
        return
    try:
        normalized_quotes.remove(quote.strip()+"\n")
    except Exception:
        normalized_quotes.remove(quote.strip())

    with open('quotes.txt', 'w') as f:
        for kw in normalized_quotes:
            f.write(kw + '\n')
    
    await ctx.response.send_message(f"Removed quote: ```{quote}```")
    print(f"{quote} removed from quotes")
    

# quotes and meme functions
    
# sends a list of the quotes, also reskinned and dreex made (its as if I can't actually code)
# dont worry i can actually code, coders are just lazy. Bro write your own code its not that hard. or at least write something that doesn't look copy pasted from my code.
# hell no
@bot.tree.command(name="check_quotes", description="List all quotes from the list of quotes [ADMIN ONLY]")
@app_commands.checks.has_permissions(administrator=True)
async def check_quotes(ctx: discord.Interaction, show_index: bool):
    with open('quotes.txt', 'r') as f:
        quotes = [line.strip() for line in f if line.strip()]
    
    if not quotes:
        await ctx.response.send_message("The quotes list is currently empty.", ephemeral=True)
        return
    
    if show_index == True:
        quote_list = ""
        for i in range(len(quotes)):
            quote_list += f"[{i}] {quotes[i]}\n"
    else:
        quote_list = "\n".join(f"- {kw}" for kw in quotes)
    
    await ctx.response.send_message(f"**Current quotes ({len(quotes)}):**\n{quote_list}", ephemeral=True)
    print("quotes checked")
      
# command to get the past daily meme
@bot.tree.command(name="get_past_daily", description="get a past daily meme")
async def get_past_daily(ctx: discord.Interaction, number: int):
    if number <= 0 or number > len(image_log):
        await ctx.response.send_message(f"Invalid number: {number}. Your number must be between 1 and {len(image_log)}", ephemeral=True)
        return
    
    entry = image_log[number - 1]
    filepath = os.path.join(IMAGE_DIR, entry["filename"])

    if not os.path.exists(filepath):
        await ctx.response.send_message("Image file missing.", ephemeral=True)
        return
    
    await ctx.response.send_message(f"Image #{number}", file=discord.File(filepath))
    print("past daily sent")

@bot.tree.command(name="get_random_meme", description="get a random meme")
async def get_random_meme(ctx: discord.Interaction):
    num = random.randint(0, len(image_log)-1)
    entry = image_log[num - 1]
    filepath = os.path.join(IMAGE_DIR, entry["filename"])
    if not os.path.exists(filepath):
        await ctx.response.send_message("Image file is missing. Try again", ephemeral=True)
        print(f"Random image error. Image index: {num}")
        return
    
    await ctx.response.send_message(f"Image #{num+1}", file=discord.File(filepath))
    print(f"Random image sent: Index {num}")


    
# adds a quote to quotes.txt (reskinned add keyword command)
@bot.tree.command(name="add_quote", description="Adds a quote; No shift enter or enter key on phone")
async def add_quote(ctx: discord.Interaction, quote: str):
    # with open('quotes.txt', 'a') as f:
    #     f.write(quote)
    #     f.write("\n")
    #     f.close()
        
    open_file('quotes.txt', 'a', quote)
    with open('quotes.txt', 'r') as f:
        length = len(f.read().splitlines())
        f.close()
    await ctx.response.send_message(f"Your quote ```{quote}``` has been added to the list of quotes. The index of your quote is {length-1}")
    print(f"added {quote} to quotes")
    

    
# sends a random quote, not actually a reskin 
@bot.tree.command(name="random_quote", description="generates a random quote")
async def random_quote(ctx: discord.Interaction, show_index: bool):
    with open("quotes.txt", 'r') as f:
        quotes = [line.strip() for line in f if line.strip()]
    if not quotes:
        await ctx.response.send_message("The quotes list is currently empty.", ephemeral=True)
        return
    quote = random.randint(0, len(quotes) - 1)
    if show_index == True:
        await ctx.response.send_message(quotes[quote]+" \nIndex: " + str(quote))
    else:
        await ctx.response.send_message(quotes[quote])
    print("random quote sent. \nIndex: " + str(quote))
    
# a working (cough cough) daily meme
@tasks.loop(time=timeToRepeat)
async def daily_post():
    print("[DEBUG] daily post triggered")
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
    
    
# command to send a suggestion to the designated channel
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
                timestamp=dtmod.now(dt_timezone.utc)
            )
            embed.set_author(name=str(ctx.user), icon_url=ctx.user.display_avatar.url)
            await log_channel.send(embed=embed)
            await ctx.response.send_message("Your suggestion has been sent :)", ephemeral=True)
            print(f"suggestion sent: {suggestion}")
        else:
            # why spam an admin 😭
            await ctx.response.send_message("It seems like there is no log channel. Perhaps spam a admin", ephemeral=True)
    else:
        await ctx.response.send_message("It seems like there is no log channel ID. Perhaps spam a admin", ephemeral=True)

# command to see who made this
@bot.tree.command(name="credits", description="see who contributed to this beautiful bot")
async def credits(ctx: discord.Interaction):
    # longest line 💀
    await ctx.response.send_message("<@1146930572179017883> made almost all of the code while <@1274754262181613691> mostly yapped through comments but did actually add code, and last but not the least, we have to give credit to our good friend ChatGPT (<@1146930572179017883> doing not me blame her when ai takes over the world)", ephemeral=True, allowed_mentions=no_allowed_mention)

# test the bot, either for the random secret command or maiasaura thinks commoners can't see this command even though they probably can
@bot.tree.command(name="test", description="Testing the bot [SECRET ONLY]")
@app_commands.check(is_secret)
async def test(ctx: discord.Interaction):
    await ctx.response.send_message("Test passed", ephemeral=True)
    print("tested")


# test/hw reminder commands

# command to add a reminder
@bot.tree.command(name="add_reminder", description="remind people of their homework/tests, include due date in description if you want")
@app_commands.checks.has_role(bot_commands_role)
async def add_reminder(ctx: discord.Interaction, test_or_homeworks: str, subject: str, description: str):
    remindstring = subject + " - " + description
    test_or_homework = test_or_homeworks.lower()
    if test == "homework" or test_or_homework == "hw":
        # with open('hwreminders.txt', 'a') as f:
        #     f.write(hwremindstring)
        #     f.write("\n")
        #     f.close()
            
        open_file('hwreminders.txt', 'a', remindstring)
        await ctx.response.send_message("You sent the homework reminder: " + remindstring)
    elif test_or_homework == "test" or test_or_homework == "quiz":
        # with open('testreminders.txt', 'a') as f:
        #     f.write(remindstring)
        #     f.write("\n")
        #     f.close()
            
        open_file('testreminders.txt', 'a', remindstring)
        await ctx.response.send_message(f"You sent the {test_or_homework} reminder: " + remindstring)
    else:
        await ctx.response.send_message("Only \"test\", \"quiz\", \"homework\", or \"hw\" are accepted.", ephemeral=True)
   
# shows you reminders for the selected category 
@bot.tree.command(name="see_reminders", description="see the test/quiz or homework reminders lined up")
@app_commands.checks.has_role(bot_commands_role)
async def see_reminders(ctx:discord.Interaction, test_or_homeworks: str):
    test_or_homework = test_or_homeworks.lower()
    if test_or_homework == "test" or test_or_homework == "quiz":
        with open('testreminders.txt', 'r') as f:
            reminders = [line.strip() for line in f if line.strip()]
            f.close()
        if not reminders:
            await ctx.response.send_message("There are no test/quiz reminders right now.", ephemeral=True)
        else:
            await ctx.response.send_message(reminders)
    elif test_or_homework == "homework" or test_or_homework == "hw":
        with open('hwreminders.txt', 'r') as f:
            reminders = [line.strip() for line in f if line.strip()]
            f.close()
        if not reminders:
            await ctx.response.send_message("There are no homework reminders right now.", ephemeral=True)
        await ctx.response.send_message(reminders)
    else:
        await ctx.response.send_message("Only \"test\", \"quiz\", \"homework\", or \"hw\" are accepted.", ephemeral=True)
    
# clears the reminders for a certain category (test or quiz)
@bot.tree.command(name="clear_reminders", description="clear the homework reminders")
@app_commands.checks.has_role(bot_commands_role)
async def clear_reminders(ctx:discord.Interaction, test_or_homeworks: str):
    test_or_homework = test_or_homeworks.lower()
    if test_or_homework == "test" or test_or_homework == "quiz":
        with open('testreminders.txt', 'w') as f:
            f.write("")
            f.close()
        await ctx.response.send_message("Test reminders cleared!")
    elif test_or_homework == "hw" or test_or_homework == "homework":
        with open('hwreminders.txt', 'w') as f:
            f.write("")
            f.close()
        await ctx.response.send_message("Homework reminders cleared!")
    else:
        await ctx.response.send_message("Only \"test\", \"quiz\", \"homework\", or \"hw\" are accepted.", ephemeral=True)
        
# test command to see if the channels and roles are correct
# @bot.tree.command(name="link_channels", description="[TEST COMMAND], makes sure that the pings and the channels are correct.")
# @app_commands.checks.has_role(bot_commands_role)
# async def link_channels(ctx:discord.Interaction):
#     await ctx.response.send_message(f"Role that is allowed to use certain bot commands: <@&{bot_commands_role}>\nChannel for homework reminders: <#{hw_reminders_channel}>\nChannel for test/quiz reminders: <#{test_reminders_channel}>")

# another test function, tests if you can ping roles and users
# @bot.tree.command(name="ping_someone", description="ping someone or ping a role")
# @app_commands.checks.has_role(bot_commands_role)
# async def ping_someone(ctx: discord.Interaction, ping:str):
#     await ctx.response.send_message(f"{ping}", allowed_mentions=all_allowed_mention)


@tasks.loop(time=timeToRepeat)
async def job_loop():
    print("reminders script running")
    channel = bot.get_channel(test_reminders_channel)
    await channel.send(get_hw_reminders())
    
    channel = bot.get_channel(hw_reminders_channel)
    await channel.send(get_hw_reminders())
    

# as the description says, does what the previous command did just at any time you want
@bot.tree.command(name="send_reminders", description="just in case it doesn't send on its own")
@app_commands.checks.has_role(bot_commands_role)
async def send_reminders(ctx:discord.Interaction):
    channel = bot.get_channel(test_reminders_channel)
    await channel.send(get_test_reminders())
    
    channel = bot.get_channel(hw_reminders_channel)
    await channel.send(get_hw_reminders())
 

# functions to send the test and quiz reminders so I don't have to copy and paste the code 15 different times    
def get_test_reminders():
    channel = bot.get_channel(test_reminders_channel)
    with open('testreminders.txt', 'r') as f:
        reminders = [line.strip() for line in f if line.strip()]
        f.close()
    
    reminders = '\n'.join(reminders)
    return f"<@&{test_reminders_role}>\n" + reminders

def get_hw_reminders():
    with open('hwreminders.txt', 'r') as f:
        reminders = [line.strip() for line in f if line.strip()]
        f.close()
    channel = bot.get_channel(hw_reminders_channel)
    reminders = '\n'.join(reminders)
    return f"<@&{hw_reminders_role}>\n" + reminders



with open('token.txt', 'r') as f:
    TOKEN = f.read()

bot.run(TOKEN)