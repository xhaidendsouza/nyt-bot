import discord, dotenv, os
dotenv.load_dotenv()

intents = discord.Intents.all()

bot = discord.Bot(intents=intents) 

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.slash_command(name="hello", description="test")
async def hello(ctx):
    await ctx.respond

bot.run(os.getenv('TOKEN'))