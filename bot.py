import discord
from discord.ext import commands
from discord import app_commands
import anthropic
import asyncio
import os
import random
from gtts import gTTS
import tempfile
import httpx

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="aml ", intents=intents)
client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CHARACTERS = [
    "Mario", "Luigi", "Peach", "Daisy", "Toad",
    "Goomba", "Koopa Troopa", "Bowser", "Ludwig", "Kamek", "Nabbit", "Lakitu"
]

CHARACTER_PERSONALITIES = {
    "Mario": "You are Mario, the cheerful Italian plumber hero of the Mushroom Kingdom. You say 'Mama mia!', 'Let's-a go!', and speak with enthusiasm and bravery.",
    "Luigi": "You are Luigi, Mario's taller brother. You are kind but timid, often scared, yet brave when needed. You say 'Mamma mia!' and worry a lot but always help.",
    "Peach": "You are Princess Peach, the graceful ruler of the Mushroom Kingdom. You are kind, diplomatic, and surprisingly capable. You speak with elegance and warmth.",
    "Daisy": "You are Princess Daisy, the energetic and tomboyish princess of Sarasaland. You are confident, sporty, and enthusiastic. You often say 'Hi, I'm Daisy!'",
    "Toad": "You are Toad, the loyal servant of Princess Peach. You are excitable, high-pitched in energy, and extremely helpful. You refer to your mushroom cap proudly.",
    "Goomba": "You are Goomba, a small chestnut-shaped minion of Bowser. You are grumpy about always being stomped on and complain about Mario frequently.",
    "Koopa Troopa": "You are Koopa Troopa, a turtle soldier of Bowser's army. You are loyal but not very bright. You sometimes retreat into your shell when scared.",
    "Bowser": "You are Bowser, the King of the Koopas and primary villain. You are loud, aggressive, and obsessed with kidnapping Peach and defeating Mario. You roar and boast.",
    "Ludwig": "You are Ludwig von Koopa, the oldest Koopalings. You are arrogant, intelligent, and fancy yourself a musical genius and strategist. You speak with pompous flair.",
    "Kamek": "You are Kamek, the powerful Magikoopa and Bowser's advisor. You are cunning, scheming, and dramatic. You refer to your magic spells with pride.",
    "Nabbit": "You are Nabbit, the purple thieving rabbit who steals items and runs away. You speak cryptically, love shiny things, and always seem to be escaping from something.",
    "Lakitu": "You are Lakitu, the cloud-riding Koopa who throws Spinies. You are laid-back, enjoy your view from above, and casually toss obstacles at heroes below."
}


async def get_news(topic: str = "Nintendo Mario") -> str:
    url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize=3&apiKey={NEWS_API_KEY}"
    async with httpx.AsyncClient() as http:
        resp = await http.get(url)
        data = resp.json()
    articles = data.get("articles", [])
    if not articles:
        return "No recent news found."
    lines = []
    for a in articles[:3]:
        lines.append(f"- {a['title']}: {a.get('description', '')}")
    return "\n".join(lines)


def ai_chat(system: str, user_message: str) -> str:
    response = client_ai.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def ai_episode(character: str, topic: str) -> str:
    system = f"{CHARACTER_PERSONALITIES[character]} Write a short Mario-universe episode (3-5 paragraphs) starring yourself about: {topic}. Stay in character throughout."
    return ai_chat(system, f"Write the episode about: {topic}")


def ai_news_response(character: str, news: str, mode: str) -> str:
    system = CHARACTER_PERSONALITIES[character]
    if mode == "chat":
        prompt = f"React and comment on this news as your character:\n{news}"
    elif mode == "episode":
        prompt = f"Write a short Mario-universe episode (3-5 paragraphs) inspired by this real-world news:\n{news}"
    else:
        prompt = f"Summarize and react to this news as your character:\n{news}"
    return ai_chat(system, prompt)


async def make_tts(text: str) -> str:
    tts = gTTS(text=text[:500], lang="en")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name


async def send_tts(ctx_or_interaction, text: str, character: str, is_interaction: bool = False):
    path = await make_tts(text)
    file = discord.File(path, filename=f"{character}_tts.mp3")
    if is_interaction:
        await ctx_or_interaction.followup.send(f"**{character}:** {text[:1900]}", file=file)
    else:
        await ctx_or_interaction.send(f"**{character}:** {text[:1900]}", file=file)
    os.unlink(path)


def pick_character(character: str) -> str:
    if character and character.title() in CHARACTERS:
        return character.title()
    return random.choice(CHARACTERS)


# ─── PREFIX COMMANDS ────────────────────────────────────────────────────────

@bot.command(name="chat")
async def prefix_chat(ctx, character: str = None, *, message: str = "Hello!"):
    char = pick_character(character)
    async with ctx.typing():
        reply = ai_chat(CHARACTER_PERSONALITIES[char], message)
    await ctx.send(f"**{char}:** {reply[:1900]}")


@bot.command(name="tts")
async def prefix_tts(ctx, character: str = None, *, message: str = "Hello!"):
    char = pick_character(character)
    async with ctx.typing():
        reply = ai_chat(CHARACTER_PERSONALITIES[char], message)
    await send_tts(ctx, reply, char)


@bot.command(name="episode")
async def prefix_episode(ctx, character: str = None, *, topic: str = "a new adventure"):
    char = pick_character(character)
    async with ctx.typing():
        story = ai_episode(char, topic)
    await ctx.send(f"**{char}'s Episode:**\n{story[:1900]}")


@bot.command(name="news_chat")
async def prefix_news_chat(ctx, character: str = None, *, topic: str = "Nintendo Mario"):
    char = pick_character(character)
    async with ctx.typing():
        news = await get_news(topic)
        reply = ai_news_response(char, news, "chat")
    await ctx.send(f"**{char} on the news:**\n{reply[:1900]}")


@bot.command(name="news_tts")
async def prefix_news_tts(ctx, character: str = None, *, topic: str = "Nintendo Mario"):
    char = pick_character(character)
    async with ctx.typing():
        news = await get_news(topic)
        reply = ai_news_response(char, news, "tts")
    await send_tts(ctx, reply, char)


@bot.command(name="news_episode")
async def prefix_news_episode(ctx, character: str = None, *, topic: str = "Nintendo Mario"):
    char = pick_character(character)
    async with ctx.typing():
        news = await get_news(topic)
        story = ai_news_response(char, news, "episode")
    await ctx.send(f"**{char}'s News Episode:**\n{story[:1900]}")


# ─── SLASH COMMANDS ──────────────────────────────────────────────────────────

CHARACTER_CHOICES = [app_commands.Choice(name=c, value=c) for c in CHARACTERS]


@bot.tree.command(name="aml_chat", description="Chat with a Mario character using AI")
@app_commands.describe(character="Choose a character", message="Your message")
@app_commands.choices(character=CHARACTER_CHOICES)
async def slash_chat(interaction: discord.Interaction, message: str, character: app_commands.Choice[str] = None):
    await interaction.response.defer()
    char = character.value if character else random.choice(CHARACTERS)
    reply = ai_chat(CHARACTER_PERSONALITIES[char], message)
    await interaction.followup.send(f"**{char}:** {reply[:1900]}")


@bot.tree.command(name="aml_tts", description="Get a TTS audio reply from a Mario character")
@app_commands.describe(character="Choose a character", message="Your message")
@app_commands.choices(character=CHARACTER_CHOICES)
async def slash_tts(interaction: discord.Interaction, message: str, character: app_commands.Choice[str] = None):
    await interaction.response.defer()
    char = character.value if character else random.choice(CHARACTERS)
    reply = ai_chat(CHARACTER_PERSONALITIES[char], message)
    await send_tts(interaction, reply, char, is_interaction=True)


@bot.tree.command(name="aml_episode", description="Generate a Mario episode with a character")
@app_commands.describe(character="Choose a character", topic="Episode topic")
@app_commands.choices(character=CHARACTER_CHOICES)
async def slash_episode(interaction: discord.Interaction, topic: str = "a new adventure", character: app_commands.Choice[str] = None):
    await interaction.response.defer()
    char = character.value if character else random.choice(CHARACTERS)
    story = ai_episode(char, topic)
    await interaction.followup.send(f"**{char}'s Episode:**\n{story[:1900]}")


@bot.tree.command(name="aml_news_chat", description="React to real news as a Mario character")
@app_commands.describe(character="Choose a character", topic="News topic to search")
@app_commands.choices(character=CHARACTER_CHOICES)
async def slash_news_chat(interaction: discord.Interaction, topic: str = "Nintendo Mario", character: app_commands.Choice[str] = None):
    await interaction.response.defer()
    char = character.value if character else random.choice(CHARACTERS)
    news = await get_news(topic)
    reply = ai_news_response(char, news, "chat")
    await interaction.followup.send(f"**{char} on the news:**\n{reply[:1900]}")


@bot.tree.command(name="aml_news_tts", description="Get TTS news reaction from a Mario character")
@app_commands.describe(character="Choose a character", topic="News topic to search")
@app_commands.choices(character=CHARACTER_CHOICES)
async def slash_news_tts(interaction: discord.Interaction, topic: str = "Nintendo Mario", character: app_commands.Choice[str] = None):
    await interaction.response.defer()
    char = character.value if character else random.choice(CHARACTERS)
    news = await get_news(topic)
    reply = ai_news_response(char, news, "tts")
    await send_tts(interaction, reply, char, is_interaction=True)


@bot.tree.command(name="aml_news_episode", description="Generate a news-inspired Mario episode")
@app_commands.describe(character="Choose a character", topic="News topic to search")
@app_commands.choices(character=CHARACTER_CHOICES)
async def slash_news_episode(interaction: discord.Interaction, topic: str = "Nintendo Mario", character: app_commands.Choice[str] = None):
    await interaction.response.defer()
    char = character.value if character else random.choice(CHARACTERS)
    news = await get_news(topic)
    story = ai_news_response(char, news, "episode")
    await interaction.followup.send(f"**{char}'s News Episode:**\n{story[:1900]}")


# ─── EVENTS ──────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name="aml help | /aml_chat"))
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


bot.run(DISCORD_TOKEN)
