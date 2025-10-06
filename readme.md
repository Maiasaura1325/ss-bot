# INFO
 - A discord bot for STUDY SERVER
 - Autolog support, daily meme if it works lol

If you want to fork it, you gotta make the files in gitignore
 - token.txt: contains a single bot token (you can find in discord dev portal)
 - keywords.txt: contains keywords for autologging
 - secret.txt: contains users for secret commands :0; every seperate line has a discord user id
 - testreminders.txt: contains test reminders
 - hwreminders.txt: contains homework reminders
 - quotes.txt: contains quotes
 - roles_and_channels.txt: contains channels and roles, goes in this exact order:
    - line 1: This is the role ID of the special bot commands role. This is to make sure random, unauthorized people can't use certain commands. Change it to whatever role ID you want, or you can remove "@app_commands.checks.has_role()" and change line 1 to "none",
    - line 2: The homework reminder channel. This is the channel ID of where the homework reminders get posted. 
    - line 3: The test/quiz reminder channel. This is the channel ID of where the test and quiz reminders get posted.
    - line 4: The role to ping when sending homework reminders
    - line 5: The role to ping when sending test/quiz reminders