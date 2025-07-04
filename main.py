import discord, os, json, dotenv, re, sys, pybound
from datetime import datetime, timedelta, timezone

dotenv.load_dotenv()

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

DATA_FILE = "data.json"

GAME_CHANNEL_ID = 814691396841766952  # replace with your #gaming channel ID
WORDLE_REGEX = r"Wordle (\d{3,5}) ([1-6X])/6"
CONN_REGEX = r"Connections\nPuzzle #(\d+)\n([\s\S]+)"

async def regex_message(message):
    content = message.content.strip().replace(",","")
    uid = str(message.author.id)
    username = message.author.name
    data = load_data()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ---- Wordle Parsing ----
    wordle_match = re.search(WORDLE_REGEX, content)
    if wordle_match:
        puzzle = int(wordle_match.group(1))
        result = wordle_match.group(2)
        guesses = 6 if result == "X" else int(result)
        failed = result == "X"

        # Prevent duplicates
        if uid in data["users"] and today_str in data["users"][uid].get("wordle", {}):
            return  # Already submitted

        data["users"].setdefault(uid, {"username": username, "wordle": {}, "connections": {}})
        data["users"][uid]["username"] = username  # Update display name
        data["users"][uid]["wordle"][today_str] = {
            "puzzle": puzzle,
            "guesses": guesses,
            "failed": failed
        }
        save_data(data)
        await message.add_reaction("📈")
        return

    # ---- Connections Parsing ----
    conn_match = re.search(CONN_REGEX, content)
    if conn_match:
        puzzle = int(conn_match.group(1))
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
        status = "win" if solved == 4 else "fail"

        base = {
            (4, 0): 95, (4, 1): 88, (4, 2): 81, (4, 3): 73,
            (2, 4): 65, (1, 4): 57, (0, 4): 50
        }.get((solved, mistakes), 50)

        # Bonuses
        bonus = 0
        
        if groups == ["🟪", "🟦", "🟨", "🟩"]:
            bonus += 4
        elif groups[:2] == ["🟪", "🟦"]:
            bonus += 3
        elif groups[:1] == ["🟦"]:
            bonus += 1
        elif groups[:1] == ["🟪"]:
            bonus += 2
        score = base + bonus

        # Prevent duplicates
        if uid in data["users"] and today_str in data["users"][uid].get("connections", {}):
            return  # Already submitted

        data["users"].setdefault(uid, {"username": username, "wordle": {}, "connections": {}})
        data["users"][uid]["username"] = username  # Update display name
        data["users"][uid]["connections"][today_str] = {
            "puzzle": puzzle,
            "mistakes": mistakes,
            "score": score
        }
        save_data(data)
        await message.add_reaction("🧠")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != GAME_CHANNEL_ID:
        return

    await regex_message(message)


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

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------\n\n")
    print("Processing channel history...")

    game_channel = bot.get_channel(GAME_CHANNEL_ID) or await bot.fetch_channel(GAME_CHANNEL_ID)

    # Count total messages first
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

        # Draw progress bar in terminal
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
    guesses_list = []
    recent_scores = []

    for date_str, e in entries.items():
        if not e["failed"]:
            g = e["guesses"]
            distribution[g - 1] += 1
            guesses_list.append(g)

            # check if it's within last 14 days
            
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_obj = date_obj.replace(tzinfo=timezone.utc)  # Make it timezone-aware

            if datetime.now(timezone.utc) - date_obj <= timedelta(days=14):
                recent_scores.append(g)
    avg_score = round(sum(guesses_list) / len(guesses_list), 2) if guesses_list else "N/A"
    recent_avg = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else "N/A"

    dist_str = "\n".join([f"{i+1}: {n}" for i, n in enumerate(distribution)])
    await ctx.respond(
        f"📊 **Wordle Stats for {user.mention}**\n"
        f"Games Played: {total}\n"
        f"Win Rate: {round((wins / total) * 100, 2)}%\n"
        f"Average Guesses: {avg_score}\n"
        f"14-day Avg: {recent_avg}\n"
        f"Distribution:\n```\n{dist_str}\n```"
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
        f"🧩 **Connections Stats for {user.mention}**\n"
        f"Games Played: {total}\n"
        f"Perfect Solves (Score 95): {perfects}\n"
        f"Average Score: {avg_score}\n"
        f"Highest Score: {max_score}\n"
        f"Lowest Score: {min_score}"
    )

# ----------- /leaderboard_wordle -------------
@wordleGroup.command(name="leaderboard", description="Wordle leaderboard.")
@discord.option("range", choices=["day", "week", "month"], required=True)
async def leaderboard_wordle(ctx, range: str):
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
        for date_str, e in user_data["wordle"].items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if date_obj >= cutoff and not e["failed"]:
                total_guesses += e["guesses"]
                count += 1
        if count > 0:
            avg = total_guesses / count
            scores.append((user_data["username"], round(avg, 2), count))

    if not scores:
        await ctx.respond(f"No Wordle entries in the past {range}.")
        return

    scores.sort(key=lambda x: x[1])
    text = "\n".join([f"**{i+1}. {u}** — {avg} avg over {n} games" for i, (u, avg, n) in enumerate(scores)])
    await ctx.respond(f"🏆 **Wordle Leaderboard ({range})**\n{text}")

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
        for date_str, e in user_data["connections"].items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if date_obj >= cutoff:
                total_score += e["score"]
                count += 1
        if count > 0:
            avg = total_score / count
            scores.append((user_data["username"], round(avg, 2), count))

    if not scores:
        await ctx.respond(f"No Connections entries in the past {range}.")
        return

    scores.sort(key=lambda x: x[1], reverse=True)
    text = "\n".join([f"**{i+1}. {u}** — {avg} avg over {n} games" for i, (u, avg, n) in enumerate(scores)])
    await ctx.respond(f"🏆 **Connections Leaderboard ({range})**\n{text}")

# Run the bot
bot.run(os.getenv("TOKEN"))
