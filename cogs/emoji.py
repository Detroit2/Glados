import discord
from discord.ext.commands.errors import MissingPermissions
import requests
import io
import re
from discord.ext import commands

class Emoji(commands.Cog):

    def __init__(self, client):
        self.client = client

    def find_emoji(self, msg):
        msg = re.sub("<a?:(.+):([0-9]+)>", "\\2", msg)
        color_modifiers = ["1f3fb", "1f3fc", "1f3fd", "1f44c", "1f3fe", "1f3ff"]
        
        name = None

        for guild in self.client.guilds:
            for emoji in guild.emojis:
                if msg.strip().lower() in emoji.name.lower():
                    name = emoji.name + (".gif" if emoji.animated else ".png")
                    url = emoji.url
                    id = emoji.id
                    guild_name = guild.name
                if msg.strip() in (str(emoji.id), emoji.name):
                    name = emoji.name + (".gif" if emoji.animated else ".png")
                    url = emoji.url
                    return name, url, emoji.id, guild.name
        if name:
            return name, url, id, guild_name

        codepoint_regex = re.compile('([\d#])?\\\\[xuU]0*([a-f\d]*)')
        unicode_raw = msg.encode('unicode-escape').decode('ascii')
        codepoints = codepoint_regex.findall(unicode_raw)
        if codepoints == []:
            return "", "", "", ""

        if len(codepoints) > 1 and codepoints[1][1] in color_modifiers:
            codepoints.pop(1)

        if codepoints[0][0] == '#':
            emoji_code = '23-20e3'
        elif codepoints[0][0] == '':
            codepoints = [x[1] for x in codepoints]
            emoji_code = '-'.join(codepoints)
        else:
            emoji_code = "3{}-{}".format(codepoints[0][0], codepoints[0][1])
        url = "https://raw.githubusercontent.com/astronautlevel2/twemoji/gh-pages/128x128/{}.png".format(emoji_code)
        name = "emoji.png"
        return name, url, "N/A", "Official"

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"emoji file is ready")

    @commands.has_permissions(manage_emojis=True)
    @commands.command(pass_context=True, aliases=['emote'], invoke_without_command=True)
    async def emoji(self, ctx, *, msg):
        emojis = msg.split()
        if msg.startswith('s '):
            emojis = emojis[1:]
            get_guild = True
        else:
            get_guild = False

        if len(emojis) > 5:
            return await ctx.send(self.bot.bot_prefix + "Maximum of 5 emojis at a time.")

        images = []
        for emoji in emojis:
            name, url, id, guild = self.find_emoji(emoji)
            if url == "":
                await ctx.send(self.bot.bot_prefix + "Could not find {}. Skipping.".format(emoji))
                continue
            response = requests.get(url, stream=True)
            if response.status_code == 404:
                await ctx.send(self.bot.bot_prefix + "Emoji {} not available. Open an issue on <https://github.com/astronautlevel2/twemoji> with the name of the missing emoji".format(emoji))
                continue

            img = io.BytesIO()
            for block in response.iter_content(1024):
                if not block:
                    break
                img.write(block)
            img.seek(0)
            images.append((guild, str(id), url, discord.File(img, name)))

        for (guild, id, url, file) in images:
            if ctx.channel.permissions_for(ctx.author).attach_files:
                if get_guild:
                    await ctx.send(content='**ID:** {}\n**Server:** {}'.format(id, guild), file=file)
                else:
                    await ctx.send(file=file)
            else:
                if get_guild:
                    await ctx.send('**ID:** {}\n**Server:** {}\n**URL: {}**'.format(id, guild, url))
                else:
                    await ctx.send(url)
            file.close()

    #copy command
    @commands.command(pass_context=True, aliases=["steal"])
    @commands.has_permissions(manage_emojis=True)
    async def copy(self, ctx, *, msg):
        msg = re.sub("<:(.+):([0-9]+)>", "\\2", msg)
        match = None
        exact_match = False
        for guild in self.client.guilds:
            for emoji in guild.emojis:
                if msg.strip().lower() in str(emoji):
                    match = emoji
                if msg.strip() in (str(emoji.id), emoji.name):
                    match = emoji
                    exact_match = True
                    break
            if exact_match:
                break

        if not match:
            return await ctx.send('Could not find emoji.')

        response = requests.get(match.url)
        emoji = await ctx.guild.create_custom_emoji(name=match.name, image=response.content)
        await ctx.send("Successfully added the emoji {0.name} <{1}:{0.name}:{0.id}>!".format(emoji, "a" if emoji.animated else ""))

    #add command
    @commands.command(pass_context=True)
    async def add(self, ctx, name, url):
        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema, requests.exceptions.ConnectionError):
            return await ctx.send("The URL you have provided is invalid.")
        if response.status_code == 404:
            return await ctx.send("The URL you have provided leads to a 404.")
        try:
            emoji = await ctx.guild.create_custom_emoji(name=name, image=response.content)
        except discord.InvalidArgument:
            return await ctx.send("Invalid image type. Only PNG, JPEG and GIF are supported.")
        await ctx.send("Successfully added the emoji {0.name} <{1}:{0.name}:{0.id}>!".format(emoji, "a" if emoji.animated else ""))

    #rem command
    @commands.command(pass_context=True)
    @commands.has_permissions(manage_emojis=True)
    async def rem(self, ctx, name):
        emotes = [x for x in ctx.guild.emojis if x.name == name]
        emote_length = len(emotes)
        if not emotes:
            return await ctx.send("No emotes with that name could be found on this server.")
        for emote in emotes:
            await emote.delete()
        if emote_length == 1:
            await ctx.send("Successfully removed the {} emoji!".format(name))
        else:
            await ctx.send("Successfully removed {} emoji with the name {}.".format(emote_length, name))

    #all errors

    #copy error
    @copy.error
    async def copy_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            em = discord.Embed(title="<a:no:801303064178196520> You dont have permissions to use that?!", color=discord.Color.red())
            await ctx.send(embed=em)
            return

        raise error

    #add error
    @add.error
    async def add_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            em = discord.Embed(title="<a:no:801303064178196520> You dont have permissions to use that?!", color=discord.Color.red())
            await ctx.send(embed=em)
            return

        raise error

    #rem error
    @rem.error
    async def rem_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            em = discord.Embed(title="<a:no:801303064178196520> You dont have permissions to use that?!", color=discord.Color.red())
            await ctx.send(embed=em)
            return

        raise error

    #emoji error
    @emoji.error
    async def emoji_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            em = discord.Embed(title="<a:no:801303064178196520> You dont have permissions to use that?!", color=discord.Color.red())
            await ctx.send(embed=em)
            return

        raise error

def setup(client):
    client.add_cog(Emoji(client))