import discord, os, json, dotenv, re, sys, pybound, io, calendar
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

# MATPLOT LIB
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_path = "assets/Franklin-Gothic.ttf"
font_manager.fontManager.addfont(font_path)
franklin_font = font_manager.FontProperties(fname=font_path)

# Emoji names and IDs (copy and paste for messaging and maybe reacting)
# <:ninety:1393042776114855966> <:eighty:1393042634104111124> <:seventy:1393061147363508254> <:sixty:1393039767746117652> <:fifty:1393060774087360552>
# <:wordle:1393063212248858805> <:connections:1393063471616102461> <:mini:1393063641309380799>

dotenv.load_dotenv()

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

DATA_FILE = "data.json"

GAME_CHANNEL_ID = 814691396841766952  # replace with your #gaming channel ID
WORDLE_REGEX = r"Wordle (\d{3,5}) ([1-6X])/6"
CONN_REGEX = r"Connections\nPuzzle #(\d+)\n([\s\S]+)"

def handle_seconds(seconds):
    if seconds < 60:
        t_time = f"{int(round(seconds))} seconds"
        return t_time
    else:
        minutes = int(round(seconds // 60))
        seconds = int(round(seconds % 60))
        t_time = f"{minutes}:{seconds:02}"
        return t_time

def generate_wordle_bar_chart(distribution, filepath="assets/wordle_bar_chart.png"):
    guess_labels = ['1', '2', '3', '4', '5', '6', 'X']
    if len(distribution) == 6:
        distribution.append(0)  # Add fails as "X"

    guess_labels = guess_labels[::-1]
    distribution = distribution[::-1]

    fig, ax = plt.subplots(figsize=(8, 4))

    bar_color = "#787c7e"
    min_bar_width = 0.15
    adjusted_distribution = [val if val > 0 else min_bar_width for val in distribution]

    bars = ax.barh(guess_labels, adjusted_distribution, color=bar_color)

    for bar, value in zip(bars, distribution):
        bar_width = bar.get_width()
        label = str(value)
        padding = 0.05
        text_x = bar_width - padding
        text_color = "white"
        y = bar.get_y() + bar.get_height() / 2

        for dx, dy in [(-0.25, 0), (0.25, 0), (0, -0.25), (0, 0.25)]:
            ax.text(
                text_x + dx * 0.01,
                y + dy * 0.01,
                label,
                ha='right',
                va='center',
                color=text_color,
                fontsize=12,
                fontproperties=franklin_font
            )

        ax.text(
            text_x,
            y,
            label,
            ha='right',
            va='center',
            color=text_color,
            fontsize=12,
            fontproperties=franklin_font
        )

    ax.set_xlim(0, max(max(distribution), min_bar_width) + 1)
    ax.set_xticks([])
    ax.yaxis.set_ticks_position('none')
    ax.set_yticks(range(len(guess_labels)))

    labels = ax.set_yticklabels(
        guess_labels,
        fontsize=12,
        fontweight='bold',
        color='black',
        fontproperties=franklin_font
    )

    last_label = labels[-1]
    pos = last_label.get_position()
    last_label.set_position((pos[0], pos[1] - 0.15))

    ax.set_xlabel("")
    ax.set_ylabel("")

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = {}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def regex_message(message):
    content = message.content.replace(",", "")
    uid = str(message.author.id)
    username = message.author.name
    data = load_data()

    # Initialize user if needed
    data["users"].setdefault(uid, {
        "username": username,
        "wordle": {},
        "connections": {},
        "mini": {}
    })
    data["users"][uid]["username"] = username

    # ---- Wordle Parsing ----
    wordle_match = re.search(WORDLE_REGEX, content)
    if wordle_match:
        puzzle = int(wordle_match.group(1))
        puzzle_key = str(puzzle)
        result = wordle_match.group(2)
        guesses = 7.5 if result == "X" else int(result)
        failed = result == "X"

        # Prevent duplicates
        if puzzle_key in data["users"][uid].get("wordle", {}):
            return

        data["users"][uid]["wordle"][puzzle_key] = {
            "guesses": guesses,
            "failed": failed
        }
        save_data(data)
        await message.add_reaction("<:wordle:1393063212248858805>")
        await message.add_reaction(r) if (r := {7.5: "❌", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}.get(guesses)) else None
        await message.add_reaction(s) if (s := {7.5: ""})
        return


    # ---- Connections Parsing ----
    conn_match = re.search(CONN_REGEX, content)
    if conn_match:
        puzzle = int(conn_match.group(1))
        puzzle_key = str(puzzle)
        grid_raw = conn_match.group(2).strip().split("\n")
        grid = [line.strip() for line in grid_raw if line.strip()]
        groups = []
        mistakes = 0

        for row in grid:
            unique = set(row)
            if len(unique) == 1:
                groups.append(unique.pop())
            else:
                mistakes += 1

        solved = len(groups)
        base = {
            (4, 0): 95, (4, 1): 88, (4, 2): 81, (4, 3): 73,
            (2, 4): 65, (1, 4): 57, (0, 4): 50
        }.get((solved, mistakes), 50)

        bonus = 0
        if groups == ["🟪", "🟦", "🟩", "🟨"]:
            bonus += 4
        elif groups[:2] == ["🟪", "🟦"]:
            bonus += 3
        elif groups[:1] == ["🟦"]:
            bonus += 1
        elif groups[:1] == ["🟪"]:
            bonus += 2

        score = base + bonus

        # Prevent duplicates
        if puzzle_key in data["users"][uid].get("connections", {}):
            return

        data["users"][uid]["connections"][puzzle_key] = {
            "mistakes": mistakes,
            "score": score
        }
        save_data(data)
        tens = score // 10
        ones = score % 10

        await message.add_reaction("<:connections:1393063471616102461>")
        # <:ninety:1393042776114855966> <:eighty:1393042634104111124> <:seventy:1393061147363508254>
        # <:fifty:1393060774087360552> <:sixty:1393039767746117652>
        match tens:
            case 5:
                await message.add_reaction("<:fifty:1393060774087360552>")
            case 6:
                await message.add_reaction("<:sixty:1393039767746117652>")
            case 7:
                await message.add_reaction("<:seventy:1393061147363508254>")
            case 8:
                await message.add_reaction("<:eighty:1393042634104111124>")
            case 9:
                await message.add_reaction("<:ninety:1393042776114855966>")
            
        await message.add_reaction(r) if (r := {0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"}.get(ones)) else None
        return


@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != GAME_CHANNEL_ID:
        return
    await regex_message(message)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------\n\n")
    print("Processing channel history...")
    game_channel = bot.get_channel(GAME_CHANNEL_ID) or await bot.fetch_channel(GAME_CHANNEL_ID)

    total_msgs = 0
    async for _ in game_channel.history(limit=None, oldest_first=True):
        total_msgs += 1

    pybound.cursor_up(num=1)
    pybound.erase_in_line("entireLine")
    print("Reading channel history...")
    processed = 0
    BAR_LENGTH = 30

    async for message in game_channel.history(limit=None, oldest_first=True):
        await regex_message(message)
        processed += 1
        if processed % 10 == 0 or processed == total_msgs:
            progress_ratio = processed / total_msgs
            filled = int(BAR_LENGTH * progress_ratio)
            empty = BAR_LENGTH - filled
            bar = "▮" * filled + "▯" * empty
            percent = int(progress_ratio * 100)
            sys.stdout.write(f"\rProgress: [{bar}] {percent}% ({processed}/{total_msgs})")
            sys.stdout.flush()
    pybound.cursor_up(num=2)
    print("\n✅ Channel history read complete.")
    pybound.cursor_down(num=2)

# ----------- /wordle_stats -------------
wordleGroup = bot.create_group(name="wordle", description="wordle")
@wordleGroup.command(name="stats", description="View someone's Wordle stats.")
@discord.option("user", description="User to view stats for", required=False)
async def wordle_stats(ctx, user: discord.User = None):
    await ctx.defer()
    user = user or ctx.author
    data = load_data()

    uid = str(user.id)
    if uid not in data["users"] or "wordle" not in data["users"][uid]:
        await ctx.respond(f"No Wordle data found for {user.mention}.")
        return

    entries = data["users"][uid]["wordle"]
    total = len(entries)
    wins = sum(1 for e in entries.values() if not e["failed"])
    distribution = [0] * 6  # guesses 1–6
    fails = 0
    guesses_list = []

    for e in entries.values():
        if e["failed"]:
            fails += 1
        else:
            g = e["guesses"]
            distribution[g - 1] += 1
            guesses_list.append(g)

    avg_score = round(sum(guesses_list) / len(guesses_list), 2) if guesses_list else "N/A"

    generate_wordle_bar_chart(distribution + [fails], filepath="assets/wordle_bar_chart.png")

    file = discord.File("assets/wordle_bar_chart.png", filename="assets/wordle_bar_chart.png")

    # dist_str = "\n".join([f"{i+1}: {n}" for i, n in enumerate(distribution)])
    await ctx.respond(
        f"<:wordle:1393063212248858805> **Wordle Stats for {user.mention}**\n"
        f"Games Played: {total}\n"
        f"Win Rate: {round((wins / total) * 100, 2)}%\n"
        f"Average Guesses: {avg_score}\n", file=file
        # f"Distribution:\n```{dist_str}\n```"
    )

# ----------- /connections_stats -------------
connectionsGroup = bot.create_group(name="connections", description="connections")
@connectionsGroup.command(name="stats", description="View someone's Connections stats.")
@discord.option("user", description="User to view stats for", required=False)
async def connections_stats(ctx, user: discord.User = None):
    await ctx.defer()
    user = user or ctx.author
    data = load_data()

    uid = str(user.id)
    if uid not in data["users"] or "connections" not in data["users"][uid]:
        await ctx.respond(f"No Connections data found for {user.mention}.")
        return

    entries = data["users"][uid]["connections"]
    total = len(entries)
    scores = [e["score"] for e in entries.values()]
    avg_score = round(sum(scores) / len(scores), 2) if scores else "N/A"
    perfects = sum(1 for e in entries.values() if e["score"] == 95)
    max_score = max(scores) if scores else "N/A"
    min_score = min(scores) if scores else "N/A"

    await ctx.respond(
        f"<:connections:1393063471616102461> **Connections Stats for {user.mention}**\n"
        f"Games Played: {total}\n"
        f"Perfect Solves (Score 95): {perfects}\n"
        f"Average Score: {avg_score}\n"
        f"Highest Score: {max_score}\n"
        f"Lowest Score: {min_score}"
    )


# ----------- /wordle_leaderboard -------------
@wordleGroup.command(name="leaderboard", description="Wordle leaderboard.")
@discord.option("range", choices=["day", "week", "month"], required=True)
async def wordle_leaderboard(ctx, range: str):
    await ctx.defer()
    data = load_data()
    today = datetime.now(timezone.utc)
    cutoff = today - {
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30)
    }[range]

    scores = []
    for _, user_data in data["users"].items():
        if "wordle" not in user_data:
            continue
        total_guesses = 0
        count = 0
        for puzzle_id_str, e in user_data["wordle"].items():

            if not e["failed"]:
                total_guesses += e["guesses"]
                count += 1
        if count > 0:
            avg = total_guesses / count
            scores.append((user_data["username"], round(avg, 2), count))

    if not scores:
        await ctx.respond(f"No Wordle entries found.")
        return

    scores.sort(key=lambda x: x[1])
    text = "\n".join([f"**{i+1}. {u}** — {avg} avg over {n} games" for i, (u, avg, n) in enumerate(scores)])
    await ctx.respond(f"🏆 **Wordle Leaderboard**\n{text}")

# ----------- /leaderboard_connections -------------
@connectionsGroup.command(name="leaderboard", description="Connections leaderboard.")
@discord.option("range", choices=["day", "week", "month"], required=True)
async def leaderboard_connections(ctx, range: str):
    await ctx.defer()
    data = load_data()
    today = datetime.now(timezone.utc)
    cutoff = today - {
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30)
    }[range]

    scores = []
    for _, user_data in data["users"].items():
        if "connections" not in user_data:
            continue
        total_score = 0
        count = 0
        for puzzle_id_str, e in user_data["connections"].items():
            # Same as Wordle, no date info so cannot filter by cutoff
            total_score += e["score"]
            count += 1
        if count > 0:
            avg = total_score / count
            scores.append((user_data["username"], round(avg, 2), count))

    if not scores:
        await ctx.respond(f"No Connections entries found.")
        return

    scores.sort(key=lambda x: x[1], reverse=True)
    text = "\n".join([f"**{i+1}. {u}** — {avg} avg over {n} games" for i, (u, avg, n) in enumerate(scores)])
    await ctx.respond(f"🏆 **Connections Leaderboard**\n{text}")


miniGroup = bot.create_group(name="mini", description="mini crossword")

@miniGroup.command(name="report", description="Report your Mini Crossword result.")
@discord.option("date", description="Date in YYYY-MM-DD format", required=True)
@discord.option("time", description="Completion time (in seconds or mm:ss)", required=True)
async def mini_report(ctx, date: str, time: str):
    await ctx.defer()
    user = ctx.author
    uid = str(user.id)
    username = user.name
    data = load_data()

    try:
        # Convert mm:ss or s to total seconds
        if ":" in time:
            minutes, seconds = map(int, time.split(":"))
            total_seconds = minutes * 60 + seconds
        else:
            total_seconds = int(time)
    except ValueError:
        await ctx.respond("⚠️ Invalid time format. Use seconds or mm:ss.")
        return

    data["users"].setdefault(uid, {"username": username, "wordle": {}, "connections": {}, "mini": {}})
    data["users"][uid]["username"] = username
    data["users"][uid].setdefault("mini", {})

    # Overwrite or add the time for the date
    data["users"][uid]["mini"][date] = total_seconds
    save_data(data)
    f_date = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
    t_time = handle_seconds(total_seconds)
    
    await ctx.respond(f"{user.mention} completed the {f_date} Mini Crossword in {t_time}.")

@miniGroup.command(name="stats", description="View someone's Mini Crossword stats.")
@discord.option("user", description="User to view stats for", required=False)
async def mini_stats(ctx, user: discord.User = None):
    await ctx.defer()
    user = user or ctx.author
    uid = str(user.id)
    data = load_data()

    if uid not in data["users"] or "mini" not in data["users"][uid]:
        await ctx.respond(f"No Mini Crossword data found for {user.mention}.")
        return

    entries = data["users"][uid]["mini"]
    times = [(d, t) for d, t in entries.items()]
    times.sort(key=lambda x: x[0], reverse=True)

    # Compute stats
    last_14 = [t for d, t in times[:14]]
    best_time = min(entries.values())
    avg_14 = round(sum(last_14) / len(last_14), 2) if last_14 else "N/A"

    

    await ctx.respond(
        f"🧠 **Mini Crossword Stats for {user.mention}**\n"
        f"14-day Average: {handle_seconds(avg_14)} sec\n"
        f"Best Time: {handle_seconds(best_time)} sec\n"
        f"Games Recorded: {len(entries)}"
    )

@miniGroup.command(name="leaderboard", description="Mini Crossword leaderboard.")
async def mini_leaderboard(ctx):
    await ctx.defer()
    data = load_data()
    today = datetime.now(timezone.utc)
    cutoff = today - timedelta(days=14)

    scores = []
    for uid, user_data in data["users"].items():
        if "mini" not in user_data:
            continue

        entries = [(datetime.strptime(d, "%Y-%m-%d"), t) for d, t in user_data["mini"].items()]
        recent = [t for date, t in entries if date >= cutoff]
        if recent:
            avg = round(sum(recent) / len(recent), 2)
            scores.append((user_data["username"], avg, len(recent)))

    if not scores:
        await ctx.respond("No Mini Crossword entries in the last 14 days.")
        return

    scores.sort(key=lambda x: x[1])
    leaderboard = "\n".join([
        f"**{i+1}. {name}** — {avg} sec over {count} games"
        for i, (name, avg, count) in enumerate(scores)
    ])
    await ctx.respond(f"🏁 **Mini Crossword Leaderboard (14-day avg)**\n{leaderboard}")

# Run the bot
bot.run(os.getenv("TOKEN"))
