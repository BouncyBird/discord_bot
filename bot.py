import os
from discord.errors import HTTPException
from discord.ext.commands.help import HelpCommand
import keyring
import requests
import discord
from discord.ext import commands
import asyncio
import youtube_dl
from discord_components import DiscordComponents, ComponentsBot, Button, Select, SelectOption
from bs4 import BeautifulSoup

TOKEN = keyring.get_password("discord_bot", "token")  # Put token here
# Put guild name here. Doesn't really matter
GUILD = keyring.get_password("discord_bot", "guild")

bot = commands.Bot(command_prefix='!')
DiscordComponents(bot)

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename


@bot.command(help='Say hello.')
async def hello(ctx):
    embed = discord.Embed()
    embed.description = f'Hello <@{ctx.message.author.id}>!'
    await ctx.send(embed=embed)


@bot.command(help='Get the current weather in a city. Seperate cities with spaces using +.')
async def cw(ctx, city):
    if city == () or city == (None,):
        await ctx.send(f"<@{ctx.message.author.id}> please state the city you want to check the weather for, after the command.")
        return None
    if city == "help":
        await ctx.send("Usage: !cw <city> <state> <country>.\nState applies to US only. State and Country are not required. Seperate cities with spaces using +.")
        return None

    r = requests.get(
        f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid=6fe538b57b431b8437ad5e27706608f2&units=imperial').json()

    if r['cod'] == 200:
        type_ = r['weather'][0]['main']
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        feelslike = r['main']['feels_like']
        low = r['main']['temp_min']
        high = r['main']['temp_max']
        humidity = r['main']['humidity']
        pid = r['weather'][0]['icon']
        n = r['name']
        embed = discord.Embed(title=f'Current Weather in {n}', description=f'')
        embed.add_field(name='Condition', value=type_, inline=True)
        embed.add_field(name='Description', value=desc, inline=True)
        embed.add_field(name='Humidity', value=f'{humidity} %', inline=False)
        embed.add_field(name='Temperature', value=f'{temp}° F', inline=True)
        embed.add_field(name='Feels Like',
                        value=f'{feelslike}° F', inline=True)
        embed.set_thumbnail(
            url="http://openweathermap.org/img/wn/{pid}@2x.png")
        await ctx.send(embed=embed)
    else:
        await ctx.send(r['message'])


@ cw.error
async def cw_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"<@{ctx.message.author.id}> please state the city you want to check the weather for, after the command.")


@bot.command(name='join', help='Tells the bot to join the voice channel you are currently in.')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()


@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command(name='play', help='Plays a song from the audio of a YouTube URL. Must be connected to a voice channel through !join command.')
async def play(ctx, url):
    server = ctx.message.guild
    voice_channel = server.voice_client
    if voice_channel is None:
        await ctx.send("The bot is not connected to a voice channel.")
        return

    async with ctx.typing():
        filename = await YTDLSource.from_url(url, loop=bot.loop)
        voice_channel.play(discord.FFmpegPCMAudio(
            executable="FFmpeg\\bin\\ffmpeg.exe", source=filename))  # Rememeber to change this to your own path or remove the executable line.
    await ctx.send('**Now playing:** {}'.format(filename))


@bot.command(name='pause', help='Pauses the currently playing song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='resume', help='Resumes the currently playing song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")


@bot.command(name='stop', help='Stops the currently playing song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(help="Get a random Dad Joke. All jokes are non-explicit and appropriate for all ages.")
async def dadjoke(ctx):
    joke = requests.get('https://icanhazdadjoke.com/',
                        headers={"Accept": "application/json"}).json()
    embed = discord.Embed(title='Dad Joke', description=joke['joke'])
    await ctx.send(embed=embed)


@bot.command(help="Get a random joke. All jokes are non-explicit and appropriate for all ages.")
async def joke(ctx):
    joke = requests.get(
        'https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,explicit').json()
    embed = discord.Embed(
        title='Joke', description=joke['joke'] if joke['type'] == 'single' else joke['setup'] + '\n' + joke['delivery'])
    embed.add_field(name='Category', value=joke['category'], inline=True)
    await ctx.send(embed=embed)

polls = []


@bot.command(help="Experimental; NOT RELIABLE. Create a poll.")
async def poll(ctx, *, args):
    arglist = args.split("|$|")
    if len(arglist) < 4:
        await ctx.send("Please enter at least two options separated by a |$|")
        return
    embed = discord.Embed(
        title=arglist[0], description=arglist[1], color=0x00ff00)
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    for i in polls:
        if i["title"] == arglist[0]:
            await ctx.send("A poll with the same title already exists.")
            return
    polls.append(
        {"title": arglist[0], "desc": arglist[1], "options": dict.fromkeys(arglist[2:], 0), "author": ctx.author.id, "aname": ctx.author.name, "avatar": ctx.author.avatar_url, "mid": ctx.message.id, "voted": []})
    pidx = len(polls) - 1
    orig = polls[pidx]
    odesc = ""
    for idx, i in enumerate(arglist[2:]):
        odesc += f"{idx+1}. {i}({polls[pidx]['options'][i]} vote(s))\n"
    embed.add_field(name="Options",
                    value=odesc, inline=False)
    msg = await ctx.send(
        embed=embed,
        components=[Button(label="Vote", custom_id="vote")]
    )
    polls[pidx]["msg"] = msg

    while True:
        try:
            polls[pidx]
        except IndexError:
            break
        interaction = await bot.wait_for("button_click", check=lambda x: x.custom_id == "vote")
        if interaction.user.id in polls[pidx]["voted"]:
            await ctx.send("You have already voted.")
        else:
            polls[pidx]["voted"].append(interaction.user.id)
            await interaction.send(content="Vote", components=[
                Select(
                    placeholder="Select what you would like to vote for.",
                    options=[
                        SelectOption(
                                label=f"{idx+1}. {i}", value=i)
                        for idx, i in enumerate(arglist[2:])],
                )
            ])

        interaction2 = await bot.wait_for("select_option")
        polls[pidx]['options'][interaction2.values[0]] += 1
        newembed = discord.Embed(
            title=arglist[0], description=arglist[1], color=0x00ff00)
        newembed.set_author(name=ctx.author.name,
                            icon_url=ctx.author.avatar_url)
        odesc = ""
        for idx, i in enumerate(arglist[2:]):
            odesc += f"{idx+1}. {i}({polls[pidx]['options'][i]} vote(s))\n"
        newembed.add_field(name="Options",
                           value=odesc, inline=False)
        await msg.edit(embed=newembed)
        await interaction2.send(content=f"{interaction2.values[0]} voted for!")


@bot.command(help="End a poll.")
async def endpoll(ctx, *, args):
    if len(polls) == 0:
        await ctx.send("There are no active polls.")
        return
    for i in polls:
        if i["title"] == args:
            polls.remove(i)
            newembed = discord.Embed(
                title=i["title"], description=i["desc"], color=0x00ff00)
            newembed.set_author(name=i["aname"],
                                icon_url=i["avatar"])
            odesc = ""
            for idx, ii in enumerate(i["options"]):
                odesc += f"{idx+1}. {ii}({i['options'][ii]} vote(s))\n"
            newembed.add_field(name="Options",
                               value=odesc, inline=False)
            newembed.set_footer(text="This poll has ended.")
            await i["msg"].edit(embed=newembed, components=[])
            return
    await ctx.send("There is no poll with that title.")


"""@bot.command()
async def button(ctx):
    await ctx.send(
        "Button Test",
        components=[
            Button(label="button", custom_id="button")
        ]
    )

    interaction = await bot.wait_for("button_click", check=lambda e: e.custom_id == "button")
    await interaction.send(content="You clicked the button!")"""


"""@bot.command()
async def select(ctx):
    await ctx.send(
        "Hello, World!",
        components=[
            Select(
                placeholder="Select something!",
                options=[
                    SelectOption(label="A", value="A"),
                    SelectOption(label="B", value="B")
                ]
            )
        ]
    )
    interaction = await bot.wait_for("select_option")
    await interaction.send(content=f"{interaction.values[0]} selected!")"""


@bot.event
async def on_member_join(member):
    channel = bot.get_channel(739131858442378752)
    await channel.send(f"Welcome {member.mention} to the server!")


@bot.command(help="Get a random meme. All memes are non-explicit and appropriate for all ages.")
async def meme(ctx):
    meme = requests.get(
        'https://meme-api.herokuapp.com/gimme').json()
    while meme["nsfw"] == True:
        meme = requests.get(
            'https://meme-api.herokuapp.com/gimme').json()
    embed = discord.Embed(
        title='Random Meme', description=meme['url'])
    embed.set_image(url=meme['url'])
    await ctx.send(embed=embed)


@bot.command(help="Send a text-based peace emoji(two fingers held up)")
async def peace(ctx):
    await ctx.send(embed=discord.Embed(description="""
    
☆┌─┐　─┐☆
　│▒│ /▒/
　│▒│/▒/ ¡ 
　│▒ /▒/─┬─┐
　│▒│▒|▒│▒│
┌┴─┴─┐-┘─
│▒┌──┘▒▒▒
└┐▒▒▒▒▒▒┌┘
　└┐▒▒▒▒┌
    """))


@bot.command(help='Send a text-based "fight me" emoji')
async def fightme(ctx):
    await ctx.send(embed=discord.Embed(description="""
    
(ง'̀-'́)ง
    """))


@bot.command(help='Send a text-based shrug emoji')
async def shrug(ctx):
    await ctx.send(embed=discord.Embed(description="""
    
¯\_(ツ)_/¯
    """))

bot.run(TOKEN)
