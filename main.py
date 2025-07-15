import discord, os, json, dotenv, re, sys, pybound, io, calendar
from discord.ui import View, Button

import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

from io import BytesIO


# Emoji names and IDs (copy and paste for messaging and maybe reacting)
# <:ninety:1393042776114855966> <:eighty:1393042634104111124> <:seventy:1393061147363508254> <:sixty:1393039767746117652> <:fifty:1393060774087360552>
# <:wordle:1393063212248858805> <:connections:1393063471616102461> <:mini:1393063641309380799>

dotenv.load_dotenv()

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

DATA_FILE = "data.json"

GAME_CHANNEL_ID = 814691396841766952  # replace with your #gaming channel ID
WORDLE_REGEX = r"Wordle (\d+) ([1-6X])/6"
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

def generate_connections_mistake_chart(distribution, filepath):
    guess_labels = ['0', '1', '2', '3', '4']  # Mistakes labels; 4 is loss

    # Reverse for horizontal bar order (top to bottom)
    guess_labels = guess_labels[::-1]
    distribution = distribution[::-1]

    fig, ax = plt.subplots(figsize=(8, 4))

    bar_color = "#787c7e"  # Gray bars
    min_bar_width = 0.2
    adjusted_distribution = [val if val > 0 else min_bar_width for val in distribution]

    bars = ax.barh(guess_labels, adjusted_distribution, color=bar_color)

    for bar, value in zip(bars, distribution):
        bar_width = bar.get_width()
        label = str(value)
        padding = 0.05
        text_x = bar_width - padding
        y = bar.get_y() + bar.get_height() / 2
        ax.text(
            text_x,
            y,
            label,
            ha='right',
            va='center',
            color='white',
            fontsize=12,
            fontweight='bold'
        )

    ax.set_xlim(0, max(max(distribution), min_bar_width) + 1)
    ax.set_xticks([])  # no x-axis ticks

    # y-axis ticks but no line ticks or spine visible
    ax.yaxis.set_ticks_position('none')

    # Use y-ticks and labels
    ax.set_yticks(range(len(guess_labels)))
    ax.set_yticklabels(
        guess_labels,
        fontsize=12,
        fontweight='bold',
        color='black'
    )

    # White background and remove spines
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches='tight', transparent=False)
    plt.close()

def generate_wordle_bar_chart(distribution, filepath):
    guess_labels = ['1', '2', '3', '4', '5', '6', 'X']
    if len(distribution) == 6:
        distribution.append(0)  # Add fails as "X"

    guess_labels = guess_labels[::-1]
    distribution = distribution[::-1]

    fig, ax = plt.subplots(figsize=(8, 4))

    bar_color = "#787c7e"  # NYT gray
    min_bar_width = 0.2

    adjusted_distribution = [val if val > 0 else min_bar_width for val in distribution]
    bars = ax.barh(guess_labels, adjusted_distribution, color=bar_color)

    for bar, value in zip(bars, distribution):
        bar_width = bar.get_width()
        label = str(value)
        text_x = bar.get_x() + bar_width - 0.05
        y = bar.get_y() + bar.get_height() / 2
        ax.text(
            text_x,
            y,
            label,
            ha='right',
            va='center',
            color='white',
            fontsize=12,
            fontweight='bold'
        )

    ax.set_xlim(0, max(max(distribution), min_bar_width) + 1)
    ax.set_xticks([])
    ax.yaxis.set_ticks_position('none')

    ax.set_yticks(range(len(guess_labels)))
    labels = ax.set_yticklabels(
        guess_labels,
        fontsize=12,
        fontweight='bold',
        color='black'
    )

    # Move "X" label down slightly
    labels[-1].set_position((labels[-1].get_position()[0], labels[-1].get_position()[1] - 0.15))

    ax.set_xlabel("")
    ax.set_ylabel("")
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.patch.set_alpha(1)           # opaque background
    ax.set_facecolor("white")        # white plot background

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

        data["users"][uid]["wordle"][puzzle_key] = {
            "guesses": guesses,
            "failed": failed
        }
        save_data(data)
        await message.add_reaction("<:wordle:1393063212248858805>")
        [await message.add_reaction(e) for e in {1: ("1️⃣", "🤩"), 2: ("2️⃣", "😎"), 3: ("3️⃣", "😃"), 4: ("4️⃣", "🙂"), 5: ("5️⃣", "😬"), 6: ("6️⃣", "😅"), 7.5: ("❌", "😔")}[guesses]]
        return


    # ---- Connections Parsing ----
    conn_match = re.search(CONN_REGEX, content)
    if conn_match:
        puzzle = int(conn_match.group(1))
        puzzle_key = str(puzzle)

        # Split and filter lines that contain any Connections emoji
        emoji_line_regex = re.compile(r"[🟪🟦🟨🟩]")
        all_lines = conn_match.group(2).strip().split("\n")
        grid = [line.strip() for line in all_lines if emoji_line_regex.search(line)]

        # Init parsed values
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
        purple_first = False
        if groups == ["🟪", "🟦", "🟩", "🟨"]:
            bonus += 4
            purple_first = True
        elif groups[:2] == ["🟪", "🟦"]:
            bonus += 3
            purple_first = True
        elif groups[:2] == ["🟦", "🟪"]:
            bonus += 3
        elif groups[:1] == ["🟪"]:
            bonus += 2
            purple_first = True
        elif groups[:1] == ["🟦"]:
            bonus += 1

        score = base + bonus

        data["users"][uid]["connections"][puzzle_key] = {
            "mistakes": mistakes,
            "score": score,
            "purple_first": purple_first
        }
        save_data(data)

        await message.add_reaction("<:connections:1393063471616102461>")
        await message.add_reaction({5: "<:fifty:1393060774087360552>", 6: "<:sixty:1393039767746117652>", 7: "<:seventy:1393061147363508254>", 8: "<:eighty:1393042634104111124>", 9: "<:ninety:1393042776114855966>"}[score // 10])
        await message.add_reaction({0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"}[score % 10])
        await message.add_reaction({0: "🤩", 1: "😎", 2: "🙂", 3: "😅", 4: "😔"}[mistakes])
        if score == 99: [await message.add_reaction(e) for e in ("⏪", "🌈")]


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
    distribution = [0] * 6
    fails = 0
    guesses_list = []

    # --- All-time stats ---
    for e in entries.values():
        if e["failed"]:
            fails += 1
        else:
            g = e["guesses"]
            distribution[g - 1] += 1
            guesses_list.append(g)

    avg_score = round(sum(guesses_list) / len(guesses_list), 2) if guesses_list else "N/A"
    win_rate = round((wins / total) * 100, 2) if total else 0

    # --- Determine latest Wordle number and 14-day window ---
    wordle_numbers = sorted(int(k) for k in entries.keys())
    latest_wordle = wordle_numbers[-1] if wordle_numbers else None
    if latest_wordle is None:
        await ctx.respond("No Wordle data available.")
        return

    start_wordle_14day = max(latest_wordle - 13, wordle_numbers[0])  # inclusive

    # --- 14-day stats ---
    dist_14day = [0] * 6
    fails_14day = 0
    guesses_14day = []
    total_14day = 0
    wins_14day = 0

    for wn in wordle_numbers:
        if start_wordle_14day <= wn <= latest_wordle:
            e = entries[str(wn)]
            total_14day += 1
            if e["failed"]:
                fails_14day += 1
            else:
                wins_14day += 1
                g = e["guesses"]
                dist_14day[g - 1] += 1
                guesses_14day.append(g)

    avg_score_14day = round(sum(guesses_14day) / len(guesses_14day), 2) if guesses_14day else "N/A"
    win_rate_14day = round((wins_14day / total_14day) * 100, 2) if total_14day else 0

    # --- Streak Calculations ---
    max_streak = 0
    current_streak = 0
    temp_streak = 0
    last_seen = None

    sorted_entries = sorted(((int(k), v) for k, v in entries.items()), reverse=True)

    for num, entry in sorted_entries:
        if last_seen is None or last_seen - 1 == num:
            if not entry["failed"]:
                temp_streak += 1
                if current_streak == 0:
                    current_streak = temp_streak
            else:
                if current_streak == 0:
                    current_streak = 0
                temp_streak = 0
        else:
            if current_streak == 0:
                current_streak = 0
            temp_streak = 1 if not entry["failed"] else 0
        max_streak = max(max_streak, temp_streak)
        last_seen = num

    # --- Charts ---
    generate_wordle_bar_chart(distribution + [fails], filepath="assets/wordle_bar_chart_alltime.png")
    generate_wordle_bar_chart(dist_14day + [fails_14day], filepath="assets/wordle_bar_chart_14day.png")

    # --- Embeds ---
    embed_alltime = discord.Embed(
        title=f"<:wordle:1393063212248858805> All-Time Wordle Stats for {user.name}",
        color=discord.Color.green()
    )
    embed_alltime.add_field(name="Games Played", value=str(total))
    embed_alltime.add_field(name="Win Rate", value=f"{win_rate}%")
    embed_alltime.add_field(name="Average Guesses", value=str(avg_score))
    embed_alltime.set_footer(text=f"Best Streak: {max_streak}🔥")
    embed_alltime.set_image(url="attachment://wordle_bar_chart_alltime.png")

    embed_14day = discord.Embed(
        title=f"<:wordle:1393063212248858805> Current Wordle Stats for {user.name}",
        color=discord.Color.blurple()
    )
    embed_14day.add_field(name="Games Played", value=str(total_14day))
    embed_14day.add_field(name="Win Rate", value=f"{win_rate_14day}%")
    embed_14day.add_field(name="Average Guesses", value=str(avg_score_14day))
    embed_14day.set_footer(text=f"Current Streak: {current_streak}🔥")
    embed_14day.set_image(url="attachment://wordle_bar_chart_14day.png")

    pages = [
        {"embed": embed_alltime, "filepath": "assets/wordle_bar_chart_alltime.png"},
        {"embed": embed_14day, "filepath": "assets/wordle_bar_chart_14day.png"},
    ]

    view = View(timeout=120)
    view.current_page = 1

    toggle_button = Button(label="See All-Time Stats", style=discord.ButtonStyle.secondary)
    view.add_item(toggle_button)

    async def toggle_callback(interaction: discord.Interaction):
        if interaction.user != ctx.author:
            await interaction.response.send_message("You're not allowed to use this.", ephemeral=True)
            return

        view.current_page = 0 if view.current_page == 1 else 1
        new_page = view.current_page
        toggle_button.label = "See All-Time Stats" if new_page == 1 else "See Current Stats"

        with open(pages[new_page]["filepath"], "rb") as f:
            chart_file = discord.File(f, filename=pages[new_page]["filepath"].split("/")[-1])
            await interaction.response.edit_message(embed=pages[new_page]["embed"], view=view, file=chart_file)

    toggle_button.callback = toggle_callback

    chart_file_14day = discord.File("assets/wordle_bar_chart_14day.png", filename="wordle_bar_chart_14day.png")
    await ctx.respond(embed=embed_14day, view=view, file=chart_file_14day)

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
    perfects = sum(1 for e in entries.values() if e["score"] >= 95)
    wins = sum(1 for e in entries.values() if e["mistakes"] <= 3)

    # Mistake distribution 0-4 (4 = loss)
    mistakes_list = [e["mistakes"] for e in entries.values()]
    mistake_distribution = [mistakes_list.count(i) for i in range(5)]

    # Calculate latest puzzle and 14-day rolling window
    puzzle_keys = sorted(int(k) for k in entries.keys())
    latest_puzzle = puzzle_keys[-1] if puzzle_keys else None
    if latest_puzzle is None:
        await ctx.respond("No Connections data available.")
        return

    start_puzzle_14day = max(latest_puzzle - 13, puzzle_keys[0])  # inclusive

    # 14-day rolling stats
    scores_14day = []
    perfects_14day = 0
    mistakes_14day = []
    total_14day = 0
    wins_14day = 0

    for pk in puzzle_keys:
        if start_puzzle_14day <= pk <= latest_puzzle:
            e = entries[str(pk)]
            total_14day += 1
            scores_14day.append(e["score"])
            if e["score"] >= 95:
                perfects_14day += 1
            if e["mistakes"] <= 3:
                wins_14day += 1
            mistakes_14day.append(e["mistakes"])

    avg_score_14day = round(sum(scores_14day) / len(scores_14day), 2) if scores_14day else "N/A"
    mistake_distribution_14day = [mistakes_14day.count(i) for i in range(5)]

    # Calculate streaks (perfect and regular)
    sorted_entries = sorted(((int(k), v) for k, v in entries.items()), reverse=True)

    max_streak = 0
    current_streak = 0
    perfect_streak = 0
    current_perfect_streak = 0
    last_seen = None

    for num, entry in sorted_entries:
        if last_seen is None or last_seen - 1 == num:
            if entry["score"] >= 95:
                current_perfect_streak += 1
                current_streak += 1
            else:
                current_perfect_streak = 0
                if entry["mistakes"] <= 3:  # consider any non-loss as part of streak
                    current_streak += 1
                else:
                    current_streak = 0
        else:
            current_streak = 1 if entry["mistakes"] <= 3 else 0
            current_perfect_streak = 1 if entry["score"] >= 95 else 0

        max_streak = max(max_streak, current_streak)
        perfect_streak = max(perfect_streak, current_perfect_streak)
        last_seen = num

    # Generate charts
    generate_connections_mistake_chart(mistake_distribution_14day, "assets/connections_mistake_14day.png")
    generate_connections_mistake_chart(mistake_distribution, "assets/connections_mistake_alltime.png")

    # Embeds
    embed_14day = discord.Embed(
        title=f"<:connections:1393063471616102461> Current Connections Stats for {user.name}",
        color=discord.Color.blurple()
    )
    embed_14day.add_field(name="Games Played", value=str(total_14day))
    embed_14day.add_field(name="Win Rate", value=f"{round((wins_14day / total_14day) * 100, 2) if total_14day else 0}%")
    embed_14day.add_field(name="Average Skill Score", value=str(avg_score_14day))
    embed_14day.add_field(name="# Perfects", value=str(perfects_14day))
    embed_14day.add_field(name="# Purple Firsts", value=str(sum(1 for e in entries.values() if e.get("purple_first", False))))
    embed_14day.add_field(name="# Reverse Rainbows", value=str(sum(1 for e in entries.values() if e["score"] == 99)))
    embed_14day.set_footer(text=f"Current Win Streak: {current_streak}🔥 | Current Perfect Streak: {current_perfect_streak}🔥")
    embed_14day.set_image(url="attachment://connections_mistake_14day.png")

    embed_alltime = discord.Embed(
        title=f"<:connections:1393063471616102461> All-Time Connections Stats for {user.name}",
        color=discord.Color.green()
    )
    embed_alltime.add_field(name="Games Played", value=str(total))
    embed_alltime.add_field(name="Win Rate", value=f"{round((wins / total) * 100, 2) if total else 0}%")
    embed_alltime.add_field(name="Average Skill Score", value=str(avg_score))
    embed_alltime.add_field(name="Perfect Solves", value=str(perfects))
    embed_alltime.add_field(name="# Purple First", value=str(sum(1 for e in entries.values() if e.get("purple_first", False))))
    embed_alltime.add_field(name="# Reverse Rainbow", value=str(sum(1 for e in entries.values() if e["score"] == 99)))
    embed_alltime.set_footer(text=f"Best Win Streak: {max_streak}🔥 | Best Perfect Streak: {perfect_streak}🔥")
    embed_alltime.set_image(url="attachment://connections_mistake_alltime.png")

    pages = [
        {"embed": embed_14day, "filepath": "assets/connections_mistake_14day.png"},
        {"embed": embed_alltime, "filepath": "assets/connections_mistake_alltime.png"},
    ]

    view = View(timeout=120)
    view.current_page = 0

    toggle_button = Button(label="See All-Time Stats", style=discord.ButtonStyle.secondary)
    view.add_item(toggle_button)

    async def toggle_callback(interaction: discord.Interaction):
        if interaction.user != ctx.author:
            await interaction.response.send_message("You're not allowed to use this.", ephemeral=True)
            return

        view.current_page = 1 if view.current_page == 0 else 0
        new_page = view.current_page
        toggle_button.label = "See Current Stats" if new_page == 1 else "See All-Time Stats"

        with open(pages[new_page]["filepath"], "rb") as f:
            chart_file = discord.File(f, filename=pages[new_page]["filepath"].split("/")[-1])
            await interaction.response.edit_message(embed=pages[new_page]["embed"], view=view, file=chart_file)

    toggle_button.callback = toggle_callback

    chart_file_14day = discord.File("assets/connections_mistake_14day.png", filename="connections_mistake_14day.png")
    await ctx.respond(embed=embed_14day, view=view, file=chart_file_14day)

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
@discord.option("date", description="Date in MM/DD/YYYY format", required=True)
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

    try:
        dt_obj = datetime.strptime(date, "%m/%d/%Y")
        f_date = dt_obj.strftime("%A %m/%d/%Y")  # e.g., Friday 07/12/2025
    except ValueError:
        await ctx.respond("⚠️ Invalid date format. Use MM/DD/YYYY.")
        return

    # Store data
    data["users"].setdefault(uid, {"username": username, "wordle": {}, "connections": {}, "mini": {}})
    data["users"][uid]["username"] = username
    data["users"][uid].setdefault("mini", {})
    data["users"][uid]["mini"][f_date] = total_seconds
    save_data(data)

    # Generate image
    try:
        img = Image.open("assets/mini_template.png").convert("RGBA")
        draw = ImageDraw.Draw(img)

        # Choose a font (you may need to provide your own TTF)

        # Text positions
        w, h = img.size

        # Username center
        text_user = username
        text_w, text_h = draw.textsize(text_user)
        draw.text(((w - text_w) / 2, h / 2 - text_h / 2), text_user, fill="black")

        # Date bottom center
        text_date = f_date
        date_w, date_h = draw.textsize(text_date)
        draw.text(((w - date_w) / 2, h - date_h - 40), text_date, fill="black")

        # Send image
        with BytesIO() as img_bytes:
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            await ctx.respond(file=discord.File(img_bytes, filename="mini_report.png"))

    except Exception as e:
        await ctx.respond(f"❌ Failed to generate image: {e}")

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
