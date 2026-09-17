import os
import io
import random
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands, tasks

# --- 1. Web Server (Render 24/7 Keep Alive) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "PERSISTX Master Bot + Full OwO RPG System Online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web, daemon=True)
    t.start()


# --- 2. Intents & Core Setup ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.invites = True
intents.reactions = True

MY_SERVER_ID = 1525181999147388958
MY_USER_ID = 1525179499602509977  # Sole Authorized Closer & Unlimited Wealth

# Hardcoded Whitelisted Bots (Anti-Nuke allows ONLY these IDs)
WHITELISTED_BOT_IDS = [
    1550169495681638541
]

AUTO_ROLE_IDS = [
    1525217661691236483,  # Family Role
    1536661490260770926   # PC Community Role
]

# Channels
WELCOME_CHANNEL_ID = 1525182000825237648       # PX WELCOMER BOT
INVITE_LOG_CHANNEL_ID = 1548745613640859729    # PX INVITER BOT
LEAVE_CHANNEL_ID = 1548745646717014029         # PX LEAVE BOT
OWO_CHANNEL_ID = 1548770349351575632           # PX OWO BOT

CHAT_CHANNEL_ID = 1536673179010080860
RULE_CHANNEL_ID = 1525203386025119807

TICKET_PANEL_CHANNEL_ID = 1525182000825237653  
TICKET_CATEGORY_ID = 1525181999646507118       # Only Category with Auto Inactivity-Close

# Ticket Notification Logs
TICKET_OPEN_LOG_ID = 1544967681898450985
TICKET_CLOSE_LOG_ID = 1544391704323563612

# Categories to scan for dynamic products
PC_CATEGORY_ID = 1525182001097998339
ANDROID_CATEGORY_ID = 1525182001097998345

# Specific Categories & Channels
PX_CLIENT_CHANNEL_ID = 1549535112620679251
RESELLER_CATEGORY_ID = 1549737126109773824
CUSTOM_PANEL_CATEGORY_ID = 1549737170691166289

QR_ALLOWED_CATEGORY_IDS = [
    TICKET_CATEGORY_ID,
    RESELLER_CATEGORY_ID,
    CUSTOM_PANEL_CATEGORY_ID
]

QR_IMAGE_URL = "https://cdn.discordapp.com/attachments/1525182000825237654/1547499435225911346/image.png?ex=6aa99368&is=6aa841e8&hm=ff5c6c833995f75802abfc9c57bd1226ebb87766937e78c32de84810844530d4&"
ACCESS_DENIED_MSG = "❌ Access Denied: For Use Contact Super Admin PERSISTX !"

# Caches
invites_cache = {}          
user_invites = {}           
member_invited_by = {}      
channel_webhooks = {}       
inactivity_warned = set()
active_giveaways = set()

# --- OwO RPG & Social In-Memory State ---
DEFAULT_COINS = 10000
user_balances = {}          
daily_cooldowns = {}
hunt_cooldowns = {}
battle_cooldowns = {}
daily_streaks = {}
user_zoos = {}              # {user_id: {tier_name: count}}
user_inventories = {}       # {user_id: {'crate': int, 'weapon': int, 'ring': int}}
user_marriage = {}          # {user_id: partner_id}
user_cookies = {}           # {user_id: count}
server_lottery_pot = 25000
server_lottery_entries = {} # {user_id: count}
server_prefix = "owo"

ANIMAL_TIERS = {
    "common": {"price": 25, "animals": ["🐶 Dog", "🐱 Cat", "🐭 Mouse", "🐰 Rabbit", "🦊 Fox"]},
    "uncommon": {"price": 60, "animals": ["🐻 Bear", "🐼 Panda", "🐨 Koala", "🐯 Tiger", "🦁 Lion"]},
    "rare": {"price": 180, "animals": ["🦄 Unicorn", "🐲 Dragon", "🦖 T-Rex", "🦚 Peacock"]},
    "mythic": {"price": 650, "animals": ["⚡ Phoenix", "🌌 Celestial Beast", "👑 Golden Griffin"]}
}

SHOP_CATALOG = {
    "crate": {"price": 1000, "desc": "Mystery Lootbox (contains cowoncy or weapons)"},
    "ring": {"price": 50000, "desc": "Wedding ring needed to marry someone"},
    "weapon": {"price": 5000, "desc": "Increases win rate in owo battle"}
}

# Persistent Ticket Counter Logic
COUNTER_FILE = "ticket_counter.txt"

def get_next_ticket_number() -> int:
    num = 210
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                content = f.read().strip()
                if content.isdigit():
                    num = int(content)
        except Exception:
            num = 210
    next_num = num + 1
    try:
        with open(COUNTER_FILE, "w") as f:
            f.write(str(next_num))
    except Exception:
        pass
    return num


# --- 3. Rating & Transcript Helpers ---
async def generate_transcript(channel: discord.TextChannel) -> discord.File:
    buffer = io.StringIO()
    buffer.write("========================================================\n")
    buffer.write("           PERSISTX OFFICIAL TICKET TRANSCRIPT          \n")
    buffer.write(f"Ticket Channel : #{channel.name}\n")
    buffer.write(f"Export Date    : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    buffer.write("========================================================\n\n")

    messages = [msg async for msg in channel.history(limit=500, oldest_first=True)]
    for msg in messages:
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = msg.author.display_name
        content = msg.clean_content or "[No text content]"
        buffer.write(f"[{timestamp}] {author}: {content}\n")
        if msg.attachments:
            for att in msg.attachments:
                buffer.write(f"    -> [Attachment]: {att.url}\n")
        buffer.write("\n")

    buffer.seek(0)
    return discord.File(fp=io.BytesIO(buffer.getvalue().encode('utf-8')), filename=f"transcript-{channel.name}.txt")


class TicketRatingView(discord.ui.View):
    def __init__(self, ticket_name: str, guild: discord.Guild):
        super().__init__(timeout=86400)
        self.ticket_name = ticket_name
        self.guild = guild

    async def submit_rating(self, interaction: discord.Interaction, stars: int):
        stars_display = "⭐" * stars
        await interaction.response.send_message(
            f"💖 **Thank you for your feedback!** Aapne PERSISTX Support ko **{stars_display}** rating di hai.",
            ephemeral=True
        )
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        close_log = self.guild.get_channel(TICKET_CLOSE_LOG_ID)
        if close_log:
            embed = discord.Embed(
                title="🌟  CUSTOMER REVIEW RECEIVED",
                description=(
                    f"A customer submitted a rating for their closed ticket.\n\n"
                    f"• **Ticket Name:** `#{self.ticket_name}`\n"
                    f"• **Customer:** {interaction.user.mention} (`{interaction.user.display_name}`)\n"
                    f"• **Rating Given:** {stars_display} (`{stars}/5 Stars`)\n"
                    f"• **Timestamp:** <t:{int(datetime.utcnow().timestamp())}:R>"
                ),
                color=0xFEE75C
            )
            embed.set_author(name="PX CUSTOMER SATISFACTION", icon_url=self.guild.icon.url if self.guild.icon else None)
            embed.set_footer(text="PERSISTX ENTERPRISE © 2026", icon_url=self.guild.icon.url if self.guild.icon else None)
            embed.timestamp = datetime.utcnow()
            await send_custom_channel_msg(close_log, "PX TICKET BOT", embed=embed)

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, custom_id="rate_1")
    async def r1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 1)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_2")
    async def r2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_3")
    async def r3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rate_4")
    async def r4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.success, custom_id="rate_5")
    async def r5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.submit_rating(interaction, 5)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.danger, custom_id="px_ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != MY_USER_ID:
            await interaction.response.send_message(
                "❌ **Access Denied:** Sirf Super Admin <@1525179499602509977> hi ticket close kar sakte hain!",
                ephemeral=True
            )
            return

        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        await interaction.response.send_message("⏳ **Closing Ticket & Generating Transcript...** Channel 5 seconds me delete ho jayega.")

        ticket_creator = None
        for target, overwrite in channel.overwrites.items():
            if isinstance(target, discord.Member) and target.id != bot.user.id:
                ticket_creator = target
                break

        transcript_file = None
        try:
            transcript_file = await generate_transcript(channel)
        except Exception as e:
            print(f"[TRANSCRIPT ERROR]: {e}")

        close_log_channel = guild.get_channel(TICKET_CLOSE_LOG_ID)
        if close_log_channel:
            close_embed = discord.Embed(
                title="🔒  TICKET CLOSED & TRANSCRIPT SAVED",
                description=(
                    f"A ticket has been permanently closed by Admin.\n\n"
                    f"• **Ticket Channel:** `#{channel.name}`\n"
                    f"• **Opened By:** {ticket_creator.mention if ticket_creator else 'Unknown'}\n"
                    f"• **Closed By:** {user.mention} (`{user.display_name}`)\n"
                    f"• **Transcript:** Attached below (`.txt`)\n"
                    f"• **Timestamp:** <t:{int(datetime.utcnow().timestamp())}:F>"
                ),
                color=0xED4245
            )
            close_embed.set_author(name="PX TICKET BOT", icon_url=guild.icon.url if guild.icon else None)
            close_embed.set_footer(text="PX Security & Ticket System © 2026", icon_url=guild.icon.url if guild.icon else None)
            close_embed.timestamp = datetime.utcnow()
            try:
                await send_custom_channel_msg(close_log_channel, "PX TICKET BOT", embed=close_embed, file=transcript_file)
            except Exception:
                pass

        if ticket_creator:
            try:
                dm_embed = discord.Embed(
                    title="✦  PERSISTX • TICKET CLOSED RECEIPT  ✦",
                    description=(
                        f"Hello **{ticket_creator.display_name}**,\n\n"
                        f"Aapka support ticket (`#{channel.name}`) close kar diya gaya hai.\n\n"
                        f"• **Server:** `{guild.name}`\n"
                        f"• **Closed By:** `{user.display_name}`\n"
                        f"• **Status:** `Resolved / Completed`\n\n"
                        f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
                        f"  ⭐ **RATE OUR ASSISTANCE**\n"
                        f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n"
                        f"Aapko hamari customer service kaisi lagi? Niche diye gaye buttons se rating zaroor dein! 👇"
                    ),
                    color=0xED4245
                )
                dm_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                dm_embed.set_footer(text="PX STORE © 2026 • Powered by PERSISTX", icon_url=guild.icon.url if guild.icon else None)
                dm_embed.timestamp = datetime.utcnow()
                rating_view = TicketRatingView(channel.name, guild)
                await ticket_creator.send(embed=dm_embed, view=rating_view)
            except Exception:
                pass

        await asyncio.sleep(4)
        try:
            await channel.delete(reason=f"Ticket closed by Super Admin {user.name}")
        except Exception as e:
            print(f"Error deleting ticket channel: {e}")


# --- 4. Bot Instance Declaration ---
class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["!", "/"], intents=intents)

    async def setup_hook(self):
        self.add_view(TicketCloseView())

bot = SecurityBot()


# --- 5. Economy & Identity Helpers ---
DEFAULT_COINS = 10000

def get_user_balance(user_id: int) -> int:
    if user_id == MY_USER_ID:
        return 999_999_999_999
    return user_balances.get(user_id, DEFAULT_COINS)

def format_balance(user_id: int) -> str:
    if user_id == MY_USER_ID:
        return "Unlimited (∞)"
    return f"{get_user_balance(user_id):,}"

def update_user_balance(user_id: int, amount: int):
    if user_id == MY_USER_ID:
        return
    current = user_balances.get(user_id, DEFAULT_COINS)
    user_balances[user_id] = max(0, current + amount)

def get_user_zoo(user_id: int) -> dict:
    if user_id not in user_zoos:
        user_zoos[user_id] = {"common": 0, "uncommon": 0, "rare": 0, "mythic": 0}
    return user_zoos[user_id]

def get_user_inv(user_id: int) -> dict:
    if user_id not in user_inventories:
        user_inventories[user_id] = {"crate": 0, "weapon": 0, "ring": 0}
    return user_inventories[user_id]

async def send_custom_channel_msg(channel: discord.TextChannel, bot_name: str, content=None, embed=None, view=None, file=None):
    if not channel or channel.guild.id != MY_SERVER_ID:
        return None
    try:
        webhook = channel_webhooks.get(channel.id)
        if not webhook:
            webhooks = await channel.webhooks()
            webhook = discord.utils.get(webhooks, name="PX-Identity-Hook")
            if not webhook:
                webhook = await channel.create_webhook(name="PX-Identity-Hook")
            channel_webhooks[channel.id] = webhook

        avatar_url = bot.user.display_avatar.url if bot.user else None
        return await webhook.send(
            content=content,
            embed=embed,
            view=view,
            file=file,
            username=bot_name,
            avatar_url=avatar_url,
            wait=True
        )
    except Exception:
        return await channel.send(content=content, embed=embed, view=view, file=file)


# --- 6. Anti-Nuke Engine ---
async def execute_antinuke_punishment(guild: discord.Guild, executor: discord.Member, action: str):
    if executor.id == bot.user.id or guild.id != MY_SERVER_ID:
        return

    print(f"[ANTINUKE] Action: {action} by {executor.name} ({executor.id})", flush=True)

    try:
        dangerous_roles = [r for r in executor.roles if r.name != "@everyone" and r < guild.me.top_role]
        if dangerous_roles:
            await executor.remove_roles(*dangerous_roles, reason=f"Anti-Nuke: {action}")
    except Exception as e:
        print(f"[ROLE STRIP ERROR]: {e}", flush=True)

    try:
        await guild.ban(executor, reason=f"Anti-Nuke: Unauthorized {action}", delete_message_days=0)
    except Exception as e:
        print(f"[BAN ERROR]: {e}", flush=True)

    try:
        owner = guild.owner
        if owner and owner.id != executor.id:
            await owner.send(
                f"🚨 **HIGH SECURITY ANTI-NUKE ALERT** 🚨\n\n"
                f"• **Offender:** `{executor.display_name}` (`{executor.id}`)\n"
                f"• **Action:** `{action}`\n"
                f"• **Status:** Roles Stripped & Ban Applied Immediately."
            )
    except Exception:
        pass


# --- 7. Reaction Restrictor for Giveaways ---
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    if payload.message_id in active_giveaways:
        if str(payload.emoji) != "🎉":
            try:
                channel = bot.get_channel(payload.channel_id)
                if channel:
                    msg = await channel.fetch_message(payload.message_id)
                    await msg.clear_reaction(payload.emoji)
            except Exception:
                pass


# --- 8. Dynamic Ticket Generator & Select View ---
def generate_ticket_options(guild: discord.Guild):
    pc_options = []
    android_options = []

    if guild:
        pc_cat = guild.get_channel(PC_CATEGORY_ID)
        android_cat = guild.get_channel(ANDROID_CATEGORY_ID)

        if not pc_cat or not android_cat:
            for cat in guild.categories:
                c_name = cat.name.lower().replace(" ", "")
                if "pcpanel" in c_name or "pc" in c_name:
                    pc_cat = cat
                elif "android" in c_name or "injector" in c_name:
                    android_cat = cat

        if pc_cat and isinstance(pc_cat, discord.CategoryChannel):
            for ch in pc_cat.text_channels:
                clean = ch.name.replace("🛒", "").replace("・", "").replace("-", " ").strip().title()
                pc_options.append(
                    discord.SelectOption(
                        label=f"PC PANEL • {clean}"[:100],
                        description=f"Direct key & setup for #{ch.name}"[:100],
                        emoji="💻"
                    )
                )

        if android_cat and isinstance(android_cat, discord.CategoryChannel):
            for ch in android_cat.text_channels:
                clean = ch.name.replace("🛒", "").replace("・", "").replace("-", " ").strip().title()
                android_options.append(
                    discord.SelectOption(
                        label=f"ANDROID • {clean}"[:100],
                        description=f"Direct key & setup for #{ch.name}"[:100],
                        emoji="📱"
                    )
                )

    mandatory_services = [
        discord.SelectOption(label="FREE PANEL • TRIAL / DAILY KEY", description="Get your free trial panel access key", emoji="🆓"),
        discord.SelectOption(label="CUSTOM PANEL DEVELOPMENT", description="Order private branded panel with your name", emoji="⚙️"),
        discord.SelectOption(label="RESELLER PANEL • BULK KEYS", description="Start your own panel reselling business", emoji="🤝"),
        discord.SelectOption(label="TECHNICAL SUPPORT & HELP", description="Direct assistance from PERSISTX", emoji="🆘")
    ]

    slots_for_products = 25 - len(mandatory_services)
    combined_products = (pc_options + android_options)[:slots_for_products]
    return combined_products + mandatory_services


class DynamicTicketSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Select PC Panel, Android Injector, or Support... 🛍️",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="px_dynamic_ticket_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        selected_product = self.values[0]

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category nahi mili! Check category ID.", ephemeral=True)
            return

        raw_display = user.global_name or user.display_name
        for prefix in ["PX |", "PX|", "px |", "px|", "PX ", "px "]:
            if raw_display.startswith(prefix):
                raw_display = raw_display[len(prefix):].strip()

        clean_name = "".join(c for c in raw_display.lower() if c.isalnum() or c in ['-', '_'])[:20]
        if not clean_name:
            clean_name = f"user-{user.id % 10000}"
            
        channel_name = clean_name
        current_ticket_num = get_next_ticket_number()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_permissions=True)
        }

        await interaction.response.defer(ephemeral=True)

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{current_ticket_num} | User: {raw_display} ({user.id}) | Item: {selected_product}"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Ticket create error: {e}", ephemeral=True)
            return

        open_log_channel = guild.get_channel(TICKET_OPEN_LOG_ID)
        if open_log_channel:
            open_embed = discord.Embed(
                title="🎫  NEW TICKET CREATED",
                description=(
                    f"A new ticket has been opened by {user.mention}.\n\n"
                    f"• **Ticket Channel:** {ticket_channel.mention} (`#{channel_name}`)\n"
                    f"• **Ticket ID:** `#{current_ticket_num}`\n"
                    f"• **User:** `{raw_display}` (`{user.id}`)\n"
                    f"• **Selected Item:** `{selected_product}`\n"
                    f"• **Created At:** <t:{int(datetime.utcnow().timestamp())}:F>"
                ),
                color=0x57F287
            )
            open_embed.set_thumbnail(url=user.display_avatar.url)
            open_embed.set_author(name="PX TICKET BOT", icon_url=guild.icon.url if guild.icon else None)
            open_embed.set_footer(text="PX Notification Service © 2026", icon_url=guild.icon.url if guild.icon else None)
            open_embed.timestamp = datetime.utcnow()
            try:
                await send_custom_channel_msg(open_log_channel, "PX TICKET BOT", embed=open_embed)
            except Exception:
                pass

        if "FREE" in selected_product:
            reason_text = "Free Trial / Daily Key Access Request"
        elif "SUPPORT" in selected_product:
            reason_text = "Technical Help & Troubleshooting Support"
        elif "CUSTOM" in selected_product:
            reason_text = "Private Branded Panel Development Order"
        elif "RESELLER" in selected_product:
            reason_text = "Bulk Keys & Reseller Business Inquiry"
        else:
            reason_text = f"Purchase Order for {selected_product}"

        embed = discord.Embed(
            title="✦  PERSISTX • SUPPORT DESK  ✦",
            description=(
                f"Welcome {user.mention} (**{raw_display}**)! Your private ticket is ready.\n\n"
                f"• **Ticket ID:** `#{current_ticket_num}`\n"
                f"• **Item Selected:** `{selected_product}`\n"
                f"• **Ticket Reason:** `{reason_text}`\n\n"
                f"╭──────────────────────────╮\n"
                f"  📌 **Quick Actions & Info**\n"
                f"╰──────────────────────────╯\n"
                f"• **Buy Product:** Type **`qr`** to get payment code.\n"
                f"• **Support / Key:** State your query below.\n\n"
                f"*Staff and <@{MY_USER_ID}> will assist you shortly!*"
            ),
            color=0xED4245
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name="PX TICKET BOT", icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text="PX STORE © 2026 • Verified Ticket", icon_url=guild.icon.url if guild.icon else None)
        embed.timestamp = datetime.utcnow()

        close_view = TicketCloseView()
        await send_custom_channel_msg(
            ticket_channel,
            "PX TICKET BOT",
            content=f"{user.mention} | <@{MY_USER_ID}>",
            embed=embed,
            view=close_view
        )
        await interaction.followup.send(f"Your ticket has been created ! {ticket_channel.mention}", ephemeral=True)


class DynamicTicketView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=None)
        self.add_item(DynamicTicketSelect(options))


def get_ticket_panel_embed(guild):
    embed = discord.Embed(
        title="✦  PERSISTX • OFFICIAL PC & ANDROID STORE  ✦",
        description=(
            "Welcome to **PERSISTX OFFICIAL STORE**! 🚀\n"
            "Choose your required **PC Panel**, **Android Injector**, or **Free Key** from the menu below.\n\n"
            "```yaml\n"
            "BINANCE PAY ID : Releasing Soon\n"
            "MERCHANT NAME  : PERSISTX_OFFICIAL\n"
            "DISPATCH       : INSTANT KEY & SETUP FILE\n"
            "SUPPORT        : 24/7 DEDICATED ASSISTANCE\n"
            "```\n"
            "• **Choose an option below to open a private ticket. 🛒**\n"
            "• **Please avoid opening tickets without genuine intent. 🚫**\n\n"
            "*Select your product below to get started!* 👇"
        ),
        color=0xED4245
    )
    embed.set_author(name="PX TICKET BOT", icon_url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="PERSISTX ENTERPRISE © 2026 • Verified Store", icon_url=guild.icon.url if guild.icon else None)
    return embed


async def force_fresh_ticket_panel(guild: discord.Guild):
    t_channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not t_channel:
        return

    try:
        async for msg in t_channel.history(limit=10):
            if msg.author.id == bot.user.id:
                await msg.delete()
                await asyncio.sleep(0.5)
    except Exception:
        pass

    options = generate_ticket_options(guild)
    view = DynamicTicketView(options)
    embed = get_ticket_panel_embed(guild)

    try:
        await t_channel.send(embed=embed, view=view)
        print("[AUTO-SYNC] Fresh panel posted!", flush=True)
    except Exception as e:
        print(f"[PANEL POST ERROR]: {e}", flush=True)


# --- 9. Inactivity Cleaner Task (ONLY FOR TICKET_CATEGORY_ID) ---
@tasks.loop(minutes=30)
async def ghost_tickets_cleaner():
    guild = bot.get_guild(MY_SERVER_ID)
    if not guild:
        return

    category = guild.get_channel(TICKET_CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        return

    now = datetime.utcnow()

    for channel in category.text_channels:
        if channel.category_id in [RESELLER_CATEGORY_ID, CUSTOM_PANEL_CATEGORY_ID] or channel.id == PX_CLIENT_CHANNEL_ID:
            continue
            
        c_name = channel.category.name.lower() if channel.category else ""
        if "reseller" in c_name or "custom" in c_name or "client" in c_name:
            continue

        try:
            last_msg = None
            async for msg in channel.history(limit=1):
                last_msg = msg
                break

            if not last_msg:
                continue

            idle_duration = now - last_msg.created_at.replace(tzinfo=None)

            if idle_duration > timedelta(hours=24) and channel.id not in inactivity_warned:
                inactivity_warned.add(channel.id)
                warn_embed = discord.Embed(
                    title="⚠️  INACTIVITY WARNING NOTICE",
                    description=(
                        "Is ticket me pichle **24 ghante** se koi message nahi aaya hai.\n"
                        "Agar agle **6 ghante** me koi response nahi milta hai, toh yeh ticket automatically close ho jayega.\n\n"
                        "*Aap message bhej kar is timer ko reset kar sakte hain!*"
                    ),
                    color=0xFEE75C
                )
                warn_embed.set_footer(text="PX Automation System • Ghost Ticket Clean")
                await send_custom_channel_msg(channel, "PX TICKET BOT", embed=warn_embed)

            elif idle_duration > timedelta(hours=30) and channel.id in inactivity_warned:
                transcript_file = await generate_transcript(channel)
                close_log = guild.get_channel(TICKET_CLOSE_LOG_ID)
                if close_log:
                    auto_embed = discord.Embed(
                        title="🔒  TICKET AUTO-CLOSED (INACTIVITY)",
                        description=(
                            f"Ticket `#{channel.name}` ko 30 ghante inactivity ki wajah se auto-close kiya gaya.\n"
                            f"• **Transcript:** Attached below\n"
                            f"• **Timestamp:** <t:{int(now.timestamp())}:F>"
                        ),
                        color=0xED4245
                    )
                    await send_custom_channel_msg(close_log, "PX TICKET BOT", embed=auto_embed, file=transcript_file)

                inactivity_warned.discard(channel.id)
                await channel.delete(reason="Auto-closed due to inactivity (30h)")

        except Exception as e:
            print(f"[GHOST CLEANER ERROR in #{channel.name}]: {e}")


# --- 10. Mines Mini-Game View ---
class MinesGameView(discord.ui.View):
    def __init__(self, user: discord.User, bet: int):
        super().__init__(timeout=90)
        self.user = user
        self.bet = bet
        self.revealed_gems = 0
        self.game_over = False

        self.bomb_indexes = set(random.sample(range(9), 3))
        self.multipliers = [1.3, 1.8, 2.5, 4.0, 6.5, 10.0]

        for i in range(9):
            row = i // 3
            btn = discord.ui.Button(label="❓", style=discord.ButtonStyle.secondary, row=row, custom_id=f"mine_{i}")
            btn.callback = self.make_callback(i)
            self.add_item(btn)

        self.cashout_btn = discord.ui.Button(label="💰 Cashout", style=discord.ButtonStyle.success, row=3, disabled=True)
        self.cashout_btn.callback = self.cashout_callback
        self.add_item(self.cashout_btn)

    def current_profit(self) -> int:
        if self.revealed_gems == 0:
            return self.bet
        mult = self.multipliers[min(self.revealed_gems - 1, len(self.multipliers) - 1)]
        return int(self.bet * mult)

    def make_callback(self, index: int):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("❌ Yeh aapka game nahi hai!", ephemeral=True)
                return

            if self.game_over:
                await interaction.response.defer()
                return

            target_btn = next((item for item in self.children if getattr(item, 'custom_id', None) == f"mine_{index}"), None)

            if index in self.bomb_indexes:
                self.game_over = True
                update_user_balance(self.user.id, -self.bet)
                disp_bal = format_balance(self.user.id)

                for i in range(9):
                    b = next((item for item in self.children if getattr(item, 'custom_id', None) == f"mine_{i}"), None)
                    if b:
                        b.disabled = True
                        if i in self.bomb_indexes:
                            b.label = "💣"
                            b.style = discord.ButtonStyle.danger
                        else:
                            b.label = "💎"
                            b.style = discord.ButtonStyle.success

                self.cashout_btn.disabled = True
                await interaction.response.edit_message(
                    content=f"💥 **BOOM!** {self.user.mention}, aapne bomb nikaal liya! Lost **{self.bet:,}** Coins. (Balance: **{disp_bal}**)",
                    view=self
                )
                self.stop()
            else:
                self.revealed_gems += 1
                target_btn.label = "💎"
                target_btn.style = discord.ButtonStyle.success
                target_btn.disabled = True

                profit = self.current_profit()
                self.cashout_btn.disabled = False
                self.cashout_btn.label = f"💰 Cashout ({profit:,} Coins)"

                if self.revealed_gems == 6:
                    self.game_over = True
                    winnings = int(self.bet * 10.0)
                    update_user_balance(self.user.id, winnings - self.bet)
                    disp_bal = format_balance(self.user.id)

                    for item in self.children:
                        item.disabled = True
                    await interaction.response.edit_message(
                        content=f"👑 **CLEARED THE FIELD!** {self.user.mention} won **{winnings:,}** OwO Coins! (Balance: **{disp_bal}**)",
                        view=self
                    )
                    self.stop()
                else:
                    await interaction.response.edit_message(
                        content=f"💎 Safe! Current: **{profit:,}** Coins ({self.multipliers[self.revealed_gems - 1]}x) | 3 💣 hidden remaining!",
                        view=self
                    )
        return button_callback

    async def cashout_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id or self.game_over or self.revealed_gems == 0:
            await interaction.response.defer()
            return

        self.game_over = True
        profit = self.current_profit()
        update_user_balance(self.user.id, profit - self.bet)
        disp_bal = format_balance(self.user.id)

        for i in range(9):
            b = next((item for item in self.children if getattr(item, 'custom_id', None) == f"mine_{i}"), None)
            if b:
                b.disabled = True
                if i in self.bomb_indexes:
                    b.label = "💣"
                    b.style = discord.ButtonStyle.danger
                elif b.label != "💎":
                    b.label = "💎"

        self.cashout_btn.disabled = True
        await interaction.response.edit_message(
            content=f"💰 **CASHOUT SUCCESSFUL!** {self.user.mention} secured **{profit:,}** OwO Coins! (Balance: **{disp_bal}**)",
            view=self
        )
        self.stop()


# --- 11. Security Checks & Ready Listener ---
@bot.tree.interaction_check
async def global_slash_check(interaction: discord.Interaction):
    if not interaction.guild or interaction.guild.id != MY_SERVER_ID:
        await interaction.response.send_message(ACCESS_DENIED_MSG, ephemeral=True)
        return False
    return True

@bot.event
async def on_ready():
    print(f"\n==========================================", flush=True)
    print(f"[ONLINE] Logged in as: {bot.user.name} ({bot.user.id})", flush=True)
    print(f"[SECURE] Authorized ONLY for Guild ID: {MY_SERVER_ID}", flush=True)
    print(f"[WHITELIST] Allowed Bots: {WHITELISTED_BOT_IDS}", flush=True)
    print(f"[ECONOMY] Default Balance: {DEFAULT_COINS:,} | Daily: 777 | Admin: Unlimited (∞)", flush=True)
    print(f"[TICKET ACCESS] Only Admin ID ({MY_USER_ID}) can close tickets!", flush=True)
    print(f"[CLEANER LIMIT] Auto-Inactivity Warning/Close locked ONLY to Category: {TICKET_CATEGORY_ID}", flush=True)
    print(f"==========================================\n", flush=True)

    guild = bot.get_guild(MY_SERVER_ID)
    if guild:
        try:
            guild_target = discord.Object(id=MY_SERVER_ID)
            bot.tree.copy_global_to(guild=guild_target)
            synced = await bot.tree.sync(guild=guild_target)
            print(f"[SLASH-SYNC SUCCESS] {len(synced)} slash commands registered instantly to Guild!", flush=True)
        except Exception as e:
            print(f"[SLASH-SYNC ERROR]: {e}", flush=True)

        try:
            guild_invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite in guild_invites}
        except Exception:
            pass

        if not ghost_tickets_cleaner.is_running():
            ghost_tickets_cleaner.start()

        await force_fresh_ticket_panel(guild)

    for g in list(bot.guilds):
        if g.id != MY_SERVER_ID:
            await g.leave()


# --- 12. Channels & Role Watchdog ---
@bot.event
async def on_guild_channel_create(channel):
    if channel.guild.id != MY_SERVER_ID:
        return
    if channel.category_id in [PC_CATEGORY_ID, ANDROID_CATEGORY_ID]:
        await asyncio.sleep(1)
        await force_fresh_ticket_panel(channel.guild)

@bot.event
async def on_guild_channel_delete(channel):
    if channel.guild.id != MY_SERVER_ID:
        return
    if channel.category_id in [PC_CATEGORY_ID, ANDROID_CATEGORY_ID]:
        await asyncio.sleep(1)
        await force_fresh_ticket_panel(channel.guild)
        return

    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        executor = entry.user
        if (hasattr(channel, 'category') and channel.category and 
            ("ticket" in channel.category.name.lower() or "client" in channel.category.name.lower())):
            return
        await execute_antinuke_punishment(guild, executor, f"Channel Deletion: #{channel.name}")

@bot.event
async def on_guild_channel_update(before, after):
    if after.guild.id != MY_SERVER_ID:
        return
    if after.category_id in [PC_CATEGORY_ID, ANDROID_CATEGORY_ID] and before.name != after.name:
        await force_fresh_ticket_panel(after.guild)

@bot.event
async def on_guild_role_delete(role):
    if role.guild.id != MY_SERVER_ID:
        return
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        executor = entry.user
        await execute_antinuke_punishment(guild, executor, f"Role Deletion: @{role.name}")


# --- 13. Member Events (Anti-Nuke with Whitelist Check) ---
@bot.event
async def on_member_join(member):
    if member.guild.id != MY_SERVER_ID:
        return
    guild = member.guild

    # 1. Zero-Tolerance Anti-Bot (Except Whitelisted Bots)
    if member.bot:
        if member.id in WHITELISTED_BOT_IDS:
            print(f"[WHITELIST] Authorized Bot Joined: {member.name} ({member.id})", flush=True)
            return

        inviter = None
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                inviter = entry.user
                break
        except Exception:
            pass

        try:
            await member.ban(reason="Anti-Nuke: Unauthorized Bot Addition Blocked")
            print(f"[STRICT ANTI-NUKE] Blocked & Banned Bot: {member.name} ({member.id})", flush=True)
        except Exception as e:
            print(f"[BOT BAN ERROR]: {e}", flush=True)

        if inviter:
            await execute_antinuke_punishment(guild, inviter, f"Attempted to Add Bot: {member.name}")
        return

    roles_to_add = []
    for r_id in AUTO_ROLE_IDS:
        role_obj = guild.get_role(r_id)
        if role_obj:
            roles_to_add.append(role_obj)
    
    if roles_to_add:
        try:
            await member.add_roles(*roles_to_add, reason="Auto-Role on server join")
            print(f"[AUTO-ROLE] Assigned {len(roles_to_add)} roles to {member.name}", flush=True)
        except Exception as e:
            print(f"[AUTO-ROLE ERROR]: {e}", flush=True)

    raw_name = member.global_name or member.display_name

    inviter = None
    try:
        current_invites = await guild.invites()
        old_invites = invites_cache.get(guild.id, {})
        for inv in current_invites:
            if inv.code in old_invites:
                if inv.uses > old_invites[inv.code]:
                    inviter = inv.inviter
                    break
            elif inv.uses > 0:
                inviter = inv.inviter
                break
        invites_cache[guild.id] = {invite.code: invite.uses for invite in current_invites}
    except Exception:
        pass

    inviter_id = inviter.id if inviter and not inviter.bot else MY_USER_ID
    inviter_name = inviter.name if inviter and not inviter.bot else "PERSIST-X"
    inviter_display = f"<@{inviter_id}>"

    member_invited_by[member.id] = inviter_id
    user_invites[inviter_id] = user_invites.get(inviter_id, 0) + 1
    total_invites = user_invites[inviter_id]

    invite_channel = guild.get_channel(INVITE_LOG_CHANNEL_ID)
    if invite_channel:
        invite_log_text = (
            f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
            f"  ✦ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 {member.mention} ✦\n"
            f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n\n"
            f"> 📨 **Invited By:** {inviter_name}\n"
            f"> 📊 **Total Invites:** `{total_invites}`\n\n"
            f"*Have a great time here!* ✧"
        )
        await send_custom_channel_msg(invite_channel, "PX INVITER BOT", content=invite_log_text)

    welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        guild_icon = guild.icon.url if guild.icon else None
        embed = discord.Embed(
            title="✦  WELCOME TO PX PANEL  ✦",
            description=(
                f"Hey {member.mention}, welcome to **{guild.name}**!\n"
                f"We're glad to have you with us in **PX FAMILY**.\n\n"
                f"**Member Information**\n"
                f"• **Name:** `{raw_name}`\n"
                f"• **Invited By:** {inviter_display}\n"
                f"• **Total Invites:** `{total_invites}`\n\n"
                f"• **Member Count:** `#{guild.member_count}`\n\n"
                f"**Important Channels**\n"
                f"📜 **Rules:** <#{RULE_CHANNEL_ID}>\n"
                f"💬 **General Chat:** <#{CHAT_CHANNEL_ID}>\n\n"
                f"*Please read the rules and have a wonderful time!* ✨"
            ),
            color=0xFEE75C
        )
        embed.set_author(name="New Member Joined!", icon_url=guild_icon)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
        embed.timestamp = datetime.utcnow()
        await send_custom_channel_msg(welcome_channel, "PX WELCOMER BOT", content=f"Welcome {member.mention}!", embed=embed)

    try:
        dm_embed = discord.Embed(
            title="✦  WELCOME TO PERSISTX OFFICIAL COMMUNITY  ✦",
            description=(
                f"Hello **{raw_name}**, welcome to **{guild.name}**! 🚀\n\n"
                f"We are delighted to have you as part of the **PX FAMILY**.\n\n"
                f"╭─────────────────────────────────╮\n"
                f"  📌 **QUICK ACCESS & GUIDELINES**\n"
                f"╰─────────────────────────────────╯\n"
                f"• 📜 **Official Server Rules:** <#{RULE_CHANNEL_ID}>\n"
                f"• 💬 **Community Lounge:** <#{CHAT_CHANNEL_ID}>\n"
                f"• 🛍️ **PC & Android Store:** <#{TICKET_PANEL_CHANNEL_ID}>\n\n"
                f"╭─────────────────────────────────╮\n"
                f"  💎 **AUTOMATED PRIVILEGES**\n"
                f"╰─────────────────────────────────╯\n"
                f"• You have been automatically assigned **Family & Community** roles.\n\n"
                f"*For official panel purchases or trial keys, please open a private ticket in <#{TICKET_PANEL_CHANNEL_ID}>.*"
            ),
            color=0xED4245
        )
        dm_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        dm_embed.set_author(name="PERSISTX ENTERPRISE", icon_url=guild.icon.url if guild.icon else None)
        dm_embed.set_footer(text="PERSISTX OFFICIAL STORE © 2026 • Verified Customer Portal", icon_url=guild.icon.url if guild.icon else None)
        dm_embed.timestamp = datetime.utcnow()
        await member.send(embed=dm_embed)
        print(f"[WELCOME DM SUCCESS] Sent luxury welcome DM to {raw_name}", flush=True)
    except Exception as e:
        print(f"[WELCOME DM FAILED]: Could not send DM to {member.name}: {e}", flush=True)


@bot.event
async def on_member_remove(member):
    if member.guild.id != MY_SERVER_ID:
        return
    guild = member.guild
    leave_channel = guild.get_channel(LEAVE_CHANNEL_ID)
    inviter_id = member_invited_by.pop(member.id, None) or MY_USER_ID
    if inviter_id in user_invites and user_invites[inviter_id] > 0:
        user_invites[inviter_id] -= 1

    if leave_channel:
        raw_name = member.global_name or member.display_name
        leave_text = (
            f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
            f"  ✧ 𝐆𝐨𝐨𝐝𝐛𝐲𝐞 {raw_name} ✧\n"
            f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n\n"
            f"> 🚪 **Member Left:** `{raw_name}`\n"
            f"> 🔗 **Invited By:** <@{inviter_id}>\n\n"
            f"*We hope to see you again!* 🥀"
        )
        await send_custom_channel_msg(leave_channel, "PX LEAVE BOT", content=leave_text)


# --- 14. Message Event (Universal QR & OwO RPG Engine) ---
@bot.event
async def on_message(message):
    global server_prefix, server_lottery_pot
    if message.author.bot or not message.guild:
        return

    content = message.content.strip()
    lowered = content.lower()

    is_ticket_by_topic = bool(message.channel.topic and "Ticket #" in message.channel.topic)
    cat_id = message.channel.category_id if hasattr(message.channel, 'category_id') else None
    cat_name = message.channel.category.name.lower() if message.channel.category else ""
    
    is_in_allowed_category = (
        (cat_id in QR_ALLOWED_CATEGORY_IDS)
        or "client" in cat_name 
        or "ticket" in cat_name
        or "reseller" in cat_name
        or "custom" in cat_name
    )
    is_client_channel = (message.channel.id == PX_CLIENT_CHANNEL_ID)

    if is_ticket_by_topic or is_in_allowed_category or is_client_channel:
        inactivity_warned.discard(message.channel.id)

        qr_triggers = ["qr", "!qr", "/qr", "qr code", "send qr", "scanner", "payment qr", "upi qr", "qr bhejo", "payment"]
        words = lowered.split()

        if lowered in qr_triggers or any(trigger in words for trigger in ["qr", "!qr", "/qr", "scanner"]):
            qr_embed = discord.Embed(
                title="✦  PERSISTX OFFICIAL PAYMENT QR  ✦",
                description=(
                    f"Hey {message.author.mention}, here is the official QR and Payment Details:\n\n"
                    f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
                    f"  💳 **PAYMENT INFORMATION**\n"
                    f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n"
                    f"• **BINANCE PAY ID:** `Releasing Soon` (NAME: `PERSISTX`)\n"
                    f"• **UPI / QR SCAN:** *Scan the official QR below to pay.*\n\n"
                    f"📌 *Payment complete karne ke baad screenshot yahan send karein!*"
                ),
                color=0xED4245
            )
            qr_embed.set_image(url=QR_IMAGE_URL)
            qr_embed.set_author(name="PX TICKET BOT", icon_url=message.guild.icon.url if message.guild.icon else None)
            qr_embed.set_footer(text="PX SECURE PAYMENT SYSTEM © 2026", icon_url=message.guild.icon.url if message.guild.icon else None)
            qr_embed.timestamp = datetime.utcnow()
            
            await send_custom_channel_msg(message.channel, "PX TICKET BOT", embed=qr_embed)
            return

    # Text Setup Fallback
    if lowered in ["!pxticketsetup", "!ticketsetup", "/pxticketsetup"]:
        if message.guild.id != MY_SERVER_ID:
            await message.channel.send(ACCESS_DENIED_MSG)
            return

        if not message.author.guild_permissions.administrator and message.author.id != MY_USER_ID:
            await message.channel.send("❌ Sirf Administrator use kar sakte hain!")
            return

        await force_fresh_ticket_panel(message.guild)
        await message.channel.send("✅ Dynamic ticket panel successfully refreshed & sent!")
        return

    # OwO RPG & Social System
    has_prefix = False
    args_str = ""

    if lowered.startswith(f"{server_prefix} "):
        has_prefix = True
        args_str = content[len(server_prefix)+1:].strip()
    elif lowered.startswith("owo "):
        has_prefix = True
        args_str = content[4:].strip()
    elif lowered.startswith("w "):
        has_prefix = True
        args_str = content[2:].strip()
    elif lowered in ["owo", "w", server_prefix]:
        has_prefix = True
        args_str = ""

    if has_prefix:
        if message.guild.id != MY_SERVER_ID:
            await message.channel.send(ACCESS_DENIED_MSG)
            return

        if message.channel.id != OWO_CHANNEL_ID:
            await message.channel.send(f"❌ OwO RPG commands sirf <#{OWO_CHANNEL_ID}> me allow hain!", delete_after=5)
            return

        parts = args_str.split()
        cmd = parts[0].lower() if len(parts) > 0 else "help"
        author = message.author
        now = datetime.utcnow()

        if cmd in ["daily"]:
            last_claim = daily_cooldowns.get(author.id)
            if last_claim and (now - last_claim) < timedelta(hours=24):
                rem = timedelta(hours=24) - (now - last_claim)
                hours, remainder = divmod(int(rem.total_seconds()), 3600)
                mins, _ = divmod(remainder, 60)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"⏳ **{author.display_name}**, next daily available in **{hours}h {mins}m**!")
                return

            streak = daily_streaks.get(author.id, 0) + 1
            daily_streaks[author.id] = streak
            reward = 777 + (streak * 10)
            update_user_balance(author.id, reward)
            daily_cooldowns[author.id] = now
            disp_bal = format_balance(author.id)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎁 **{author.display_name}**, aapko **{reward:,}** Cowoncy mile! (Streak: `{streak} Days` 🔥 | Balance: **{disp_bal}**)")

        elif cmd in ["money", "cash", "cowoncy", "bal", "balance"]:
            target_user = message.mentions[0] if message.mentions else author
            disp_bal = format_balance(target_user.id)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"👛 **{target_user.display_name}** has **{disp_bal}** Cowoncy (owo coins)!")

        elif cmd in ["give", "send", "pay"]:
            if len(message.mentions) == 0 or len(parts) < 3:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo give @user <amount>`")
                return
            target = message.mentions[0]
            if target.id == author.id:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Aap khud ko coins send nahi kar sakte!")
                return
            try:
                amount = int(parts[2])
            except ValueError:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Amount valid number hona chahiye!")
                return
            if amount <= 0:
                return
            bal = get_user_balance(author.id)
            if author.id != MY_USER_ID and amount > bal:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Insufficient cowoncy balance!")
                return

            update_user_balance(author.id, -amount)
            update_user_balance(target.id, amount)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💸 **{author.display_name}** transferred **{amount:,}** Cowoncy to {target.mention}!")

        elif cmd in ["quest"]:
            embed = discord.Embed(
                title=f"📜 {author.display_name}'s Daily Quests",
                description=(
                    "• `[1]` Hunt 5 animals in zoo: **(Progress: 3/5)** 🐾\n"
                    "• `[2]` Win 1 coinflip game: **(Completed)** ✅\n"
                    "• `[3]` Send a cookie to a friend: **(Progress: 0/1)** 🍪\n\n"
                    "Reward on all completed: **+2,500 Cowoncy**"
                ),
                color=0x57F287
            )
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["checklist", "cl"]:
            embed = discord.Embed(
                title=f"📋 OwO Daily Checklist for {author.display_name}",
                description=(
                    f"✅ **Daily Claim:** {'Claimed today' if (author.id in daily_cooldowns and (now - daily_cooldowns[author.id]) < timedelta(hours=24)) else 'Ready to claim (`owo daily`)'}\n"
                    f"🐾 **Hunt:** Ready (`owo h`)\n"
                    f"⚔️ **Battle:** Ready (`owo b`)\n"
                    f"🎰 **Lottery Ticket:** {'Entered' if author.id in server_lottery_entries else 'Not entered (`owo lottery 100`)'}\n"
                    f"🍪 **Cookies Given:** `{user_cookies.get(author.id, 0)}`"
                ),
                color=0xFEE75C
            )
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["shop"]:
            desc = "**Available OwO Shop Items:**\n\n"
            for k, v in SHOP_CATALOG.items():
                desc += f"• **`{k.upper()}`** — `{v['price']:,} Cowoncy`\n  *{v['desc']}*\n\n"
            desc += "*Use `owo buy <item>` to purchase!*"
            embed = discord.Embed(title="🛒 PERSISTX • OWO OFFICIAL SHOP", description=desc, color=0xED4245)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["buy"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo buy <crate|ring|weapon>`")
                return
            item = parts[1].lower()
            if item not in SHOP_CATALOG:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Item shop me nahi mila! Type `owo shop` dekhein.")
                return

            cost = SHOP_CATALOG[item]["price"]
            bal = get_user_balance(author.id)
            if author.id != MY_USER_ID and cost > bal:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Aapke paas is item ke liye coins kam hain!")
                return

            update_user_balance(author.id, -cost)
            inv = get_user_inv(author.id)
            inv[item] = inv.get(item, 0) + 1
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🛍️ **{author.display_name}** bought 1x **{item.upper()}** for **{cost:,}** Cowoncy! (Inv: `{inv[item]}`)")

        elif cmd in ["hunt", "h"]:
            last_hunt = hunt_cooldowns.get(author.id)
            if last_hunt and (now - last_hunt) < timedelta(seconds=15):
                rem_sec = 15 - int((now - last_hunt).total_seconds())
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🌲 Wait `{rem_sec}s` before hunting again!")
                return

            hunt_cooldowns[author.id] = now
            roll = random.random()
            if roll < 0.55:
                tier = "common"
            elif roll < 0.85:
                tier = "uncommon"
            elif roll < 0.97:
                tier = "rare"
            else:
                tier = "mythic"

            animal_name = random.choice(ANIMAL_TIERS[tier]["animals"])
            zoo = get_user_zoo(author.id)
            zoo[tier] += 1
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🌲 **{author.display_name}**, aapne jangal se ek **{tier.upper()}** animal pakad liya! 👉 **{animal_name}**!")

        elif cmd in ["zoo"]:
            zoo = get_user_zoo(author.id)
            desc = (
                f"🐶 **Common Animals:** `{zoo['common']}`\n"
                f"🐼 **Uncommon Animals:** `{zoo['uncommon']}`\n"
                f"🐲 **Rare Animals:** `{zoo['rare']}`\n"
                f"⚡ **Mythic Animals:** `{zoo['mythic']}`\n\n"
                f"📊 *Total Zoo Animals:* `{sum(zoo.values())}`\n"
                f"*Use `owo sell <tier|all>` to sell animals for cash.*"
            )
            embed = discord.Embed(title=f"🐾 {author.display_name}'s Zoo Reserve", description=desc, color=0x57F287)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["sell"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo sell <common|uncommon|rare|mythic|all>`")
                return
            tier_choice = parts[1].lower()
            zoo = get_user_zoo(author.id)

            if tier_choice == "all":
                total_earned = 0
                for t, data in ANIMAL_TIERS.items():
                    count = zoo[t]
                    total_earned += count * data["price"]
                    zoo[t] = 0
                if total_earned == 0:
                    await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Zoo me sell karne ke liye koi animals nahi hain!")
                    return
                update_user_balance(author.id, total_earned)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💰 Aapne saare animals bech kar **{total_earned:,}** Cowoncy kama liye!")
            elif tier_choice in ANIMAL_TIERS:
                count = zoo[tier_choice]
                if count <= 0:
                    await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"❌ Aapke paas ek bhi `{tier_choice}` animal nahi hai!")
                    return
                earned = count * ANIMAL_TIERS[tier_choice]["price"]
                zoo[tier_choice] = 0
                update_user_balance(author.id, earned)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💰 Sold `{count}`x **{tier_choice.upper()}** for **{earned:,}** Cowoncy!")
            else:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Invalid tier! Choose: `common`, `uncommon`, `rare`, `mythic`, ya `all`.")

        elif cmd in ["inv", "inventory"]:
            inv = get_user_inv(author.id)
            desc = (
                f"📦 **Mystery Crates:** `{inv.get('crate', 0)}`\n"
                f"⚔️ **Battle Weapons:** `{inv.get('weapon', 0)}`\n"
                f"💍 **Marriage Rings:** `{inv.get('ring', 0)}`\n"
            )
            embed = discord.Embed(title=f"🎒 {author.display_name}'s Backpack", description=desc, color=0xED4245)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["lootbox", "lb", "crate"]:
            inv = get_user_inv(author.id)
            if inv.get("crate", 0) <= 0:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Aapke paas koi crate nahi hai! (`owo buy crate` se khareedein).")
                return
            inv["crate"] -= 1
            win_coins = random.randint(800, 3500)
            update_user_balance(author.id, win_coins)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎁 **CRATE OPENED!** {author.mention} found **{win_coins:,}** Cowoncy inside!")

        elif cmd in ["battle", "b"]:
            last_b = battle_cooldowns.get(author.id)
            if last_b and (now - last_b) < timedelta(seconds=20):
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="⏳ Pet team is resting! Try in a few seconds.")
                return
            battle_cooldowns[author.id] = now
            inv = get_user_inv(author.id)
            bonus = 15 if inv.get("weapon", 0) > 0 else 0
            roll = random.randint(1, 100) + bonus

            if roll >= 45:
                loot = random.randint(400, 1500)
                update_user_balance(author.id, loot)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"⚔️ **VICTORY!** {author.display_name}'s battle team defeated the dungeon boss! Won **{loot:,}** Cowoncy!")
            else:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💀 **DEFEAT!** Boss was too strong. (Buy weapons in `owo shop` for higher winrate!)")

        elif cmd in ["team"]:
            zoo = get_user_zoo(author.id)
            embed = discord.Embed(
                title=f"🛡️ {author.display_name}'s Battle Squad",
                description=(
                    f"• **Slot 1 (Tank):** {'🐲 Dragon' if zoo['rare'] > 0 else '🐻 Bear'}\n"
                    f"• **Slot 2 (DPS):** {'⚡ Phoenix' if zoo['mythic'] > 0 else '🐯 Tiger'}\n"
                    f"• **Slot 3 (Support):** {'🦄 Unicorn' if zoo['rare'] > 1 else '🐶 Dog'}\n\n"
                    f"Weapon Boost: `{'+15% Power' if get_user_inv(author.id).get('weapon', 0) > 0 else 'None'}`"
                ),
                color=0xED4245
            )
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["owodex"]:
            zoo = get_user_zoo(author.id)
            total_species = 14
            collected = min(total_species, sum(1 for v in zoo.values() if v > 0) * 3 + random.randint(1, 2))
            pct = int((collected / total_species) * 100)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"📖 **OwOdex Progress for {author.display_name}:** `{collected}/{total_species}` ({pct}% Complete) 🐾")

        elif cmd in ["slots", "s"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo s <amount>`")
                return
            try:
                bet = int(parts[1])
            except ValueError:
                return
            if bet <= 0:
                return
            bal = get_user_balance(author.id)
            if author.id != MY_USER_ID and bet > bal:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Insufficient balance!")
                return

            icons = ["🍒", "🍋", "🍇", "💎", "7️⃣"]
            r1, r2, r3 = random.choice(icons), random.choice(icons), random.choice(icons)
            if r1 == r2 == r3:
                winnings = bet * 4
                update_user_balance(author.id, winnings)
                disp_bal = format_balance(author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n🔥 **JACKPOT!** Won **{winnings:,}** Cowoncy! (Balance: **{disp_bal}**)")
            elif r1 == r2 or r2 == r3 or r1 == r3:
                winnings = int(bet * 1.5)
                update_user_balance(author.id, winnings - bet)
                disp_bal = format_balance(author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n✨ Small Win! Won **{winnings:,}** Cowoncy! (Balance: **{disp_bal}**)")
            else:
                update_user_balance(author.id, -bet)
                disp_bal = format_balance(author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n💔 Lost **{bet:,}** Cowoncy.")

        elif cmd in ["coinflip", "cf"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo cf <amount> [h/t]`")
                return
            try:
                bet = int(parts[1])
            except ValueError:
                return
            if bet <= 0:
                return
            bal = get_user_balance(author.id)
            if author.id != MY_USER_ID and bet > bal:
                return
            choice = parts[2].lower()[0] if len(parts) >= 3 else "h"
            choice_str = "Heads" if choice == "h" else "Tails"
            result = random.choice(["Heads", "Tails"])

            if result == choice_str:
                update_user_balance(author.id, bet)
                disp_bal = format_balance(author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🪙 Lands on **{result}**! 🎉 Won **{bet:,}** Coins! (Balance: **{disp_bal}**)")
            else:
                update_user_balance(author.id, -bet)
                disp_bal = format_balance(author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🪙 Lands on **{result}**! 💀 Lost **{bet:,}** Coins. (Balance: **{disp_bal}**)")

        elif cmd in ["blackjack", "bj"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo bj <amount>`")
                return
            try:
                bet = int(parts[1])
            except ValueError:
                return
            bal = get_user_balance(author.id)
            if author.id != MY_USER_ID and bet > bal:
                return

            player_score = random.randint(16, 21)
            dealer_score = random.randint(15, 22)
            if dealer_score > 21 or player_score > dealer_score:
                win = bet
                update_user_balance(author.id, win)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🃏 **BLACKJACK!** You: `{player_score}` | Dealer: `{dealer_score if dealer_score <= 21 else 'Bust'}`. You won **{win:,}** Cowoncy!")
            elif player_score == dealer_score:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🃏 **PUSH!** Both scored `{player_score}`. Bet returned.")
            else:
                update_user_balance(author.id, -bet)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🃏 **DEALER WINS!** You: `{player_score}` | Dealer: `{dealer_score}`. Lost **{bet:,}** Cowoncy.")

        elif cmd in ["lottery"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎟️ **Server Lottery Pot:** `{server_lottery_pot:,}` Cowoncy! (Use `owo lottery <amount>` to buy tickets)")
                return
            try:
                tickets = int(parts[1])
            except ValueError:
                return
            if tickets <= 0:
                return
            cost = tickets * 100
            bal = get_user_balance(author.id)
            if author.id != MY_USER_ID and cost > bal:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Insufficient cowoncy!")
                return
            update_user_balance(author.id, -cost)
            server_lottery_pot += cost
            server_lottery_entries[author.id] = server_lottery_entries.get(author.id, 0) + tickets
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎟️ **{author.display_name}** bought `{tickets}` lottery tickets! Current Pot: **{server_lottery_pot:,}** Cowoncy!")

        elif cmd in ["profile"]:
            target = message.mentions[0] if message.mentions else author
            disp_bal = format_balance(target.id)
            partner = user_marriage.get(target.id)
            partner_str = f"<@{partner}>" if partner else "Single 💔"
            zoo = get_user_zoo(target.id)
            desc = (
                f"🪙 **Cowoncy:** `{disp_bal}`\n"
                f"💍 **Relationship:** {partner_str}\n"
                f"🍪 **Cookies Received:** `{user_cookies.get(target.id, 0)}`\n"
                f"🐾 **Animals Caught:** `{sum(zoo.values())}`\n"
                f"🔥 **Daily Streak:** `{daily_streaks.get(target.id, 0)} Days`\n"
            )
            embed = discord.Embed(title=f"🌸 {target.display_name}'s OwO Profile", description=desc, color=0xFEE75C)
            embed.set_thumbnail(url=target.display_avatar.url)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["marry"]:
            if len(message.mentions) == 0:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Mention someone to marry! (`owo marry @user`)")
                return
            target = message.mentions[0]
            if target.id == author.id:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Aap khud se shaadi nahi kar sakte!")
                return
            inv = get_user_inv(author.id)
            if inv.get("ring", 0) <= 0:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="💍 Shaadi karne ke liye pehle `owo buy ring` khareedein!")
                return

            user_marriage[author.id] = target.id
            user_marriage[target.id] = author.id
            inv["ring"] -= 1
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💍 💖 **CONGRATULATIONS!** {author.mention} and {target.mention} are now married!")

        elif cmd in ["divorce"]:
            if author.id not in user_marriage:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Aap pehle se hi single hain!")
                return
            old_p = user_marriage.pop(author.id, None)
            if old_p in user_marriage:
                user_marriage.pop(old_p, None)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💔 **{author.display_name}** has divorced their partner.")

        elif cmd in ["pray"]:
            target = message.mentions[0] if message.mentions else author
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🙏 **{author.display_name}** prayed for {target.mention}! Their RNG luck has been blessed for 10 minutes! ✨")

        elif cmd in ["curse"]:
            target = message.mentions[0] if message.mentions else author
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"😈 **{author.display_name}** cast a dark curse upon {target.mention}! May their rolls be unlucky! 💀")

        elif cmd in ["cookie"]:
            if len(message.mentions) == 0:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Mention kijiye kisko cookie deni hai! (`owo cookie @user`)")
                return
            target = message.mentions[0]
            user_cookies[target.id] = user_cookies.get(target.id, 0) + 1
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🍪 **{author.display_name}** gave a sweet cookie to {target.mention}! (Total: `{user_cookies[target.id]}` cookies)")

        elif cmd in ["8b"]:
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Question puchiye! (`owo 8b will I win?`)")
                return
            answers = ["Yes, absolutely! 🔮", "No way 💀", "Signs point to yes ✨", "Ask again later 🤔", "Very doubtful ❌"]
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎱 **8-Ball says:** {random.choice(answers)}")

        elif cmd in ["hug", "kiss", "slap", "pat", "bite", "cuddle"]:
            if len(message.mentions) == 0:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"❌ Mention someone to {cmd}!")
                return
            target = message.mentions[0]
            emojis = {"hug": "🫂", "kiss": "💋", "slap": "👋💥", "pat": "💆", "bite": "🧛", "cuddle": "🧸"}
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"{emojis[cmd]} **{author.display_name}** {cmd}ed {target.mention}!")

        elif cmd in ["blush", "cry", "dance", "pout", "smile", "smug"]:
            self_actions = {
                "blush": "is blushing warmly (//∇//) 💖",
                "cry": "is crying tears of sadness (╥﹏╥) 💧",
                "dance": "is dancing happily ヾ(⌐■_■)ノ♪ 🕺",
                "pout": "is pouting ( ಠ ʖ̯ ಠ ) 💢",
                "smile": "smiles brightly (◕‿◕) ✨",
                "smug": "looks smug ( ͡° ͜ʖ ͡°) 😏"
            }
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"✧ **{author.display_name}** {self_actions[cmd]}")

        elif cmd in ["top", "leaderboard"]:
            sorted_richest = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:5]
            desc = "🏆 **Richest Players in Server:**\n\n"
            for rank, (u_id, coins) in enumerate(sorted_richest, 1):
                user_obj = bot.get_user(u_id)
                u_name = user_obj.display_name if user_obj else f"User {u_id}"
                desc += f"`#{rank}` **{u_name}** — `{coins:,}` Cowoncy\n"
            embed = discord.Embed(title="👑 PERSISTX OWO LEADERBOARD", description=desc, color=0xFEE75C)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)

        elif cmd in ["prefix"]:
            if not author.guild_permissions.administrator and author.id != MY_USER_ID:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Only Admin can change the prefix!")
                return
            if len(parts) < 2:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"Current prefix: `{server_prefix}`. Usage: `owo prefix <new_prefix>`")
                return
            server_prefix = parts[1].lower()
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"✅ Server OwO prefix updated to: `{server_prefix}`!")

        elif cmd in ["help"]:
            embed = discord.Embed(
                title="✦ PERSISTX • OWO SYSTEM DIRECTORY ✦",
                description=(
                    "**🪙 Economy & Core**\n"
                    "`owo daily` `owo cash` `owo give @user <amt>` `owo quest` `owo checklist` `owo shop` `owo buy <item>`\n\n"
                    "**🐾 Animals, Hunting & Battle**\n"
                    "`owo hunt` `owo zoo` `owo sell <tier|all>` `owo inv` `owo crate` `owo battle` `owo team` `owo owodex`\n\n"
                    "**🎰 Gambling**\n"
                    "`owo slots <amt>` `owo coinflip <amt> <h/t>` `owo bj <amt>` `owo lottery <amt>` `owo mine <amt>`\n\n"
                    "**💖 Social & Fun**\n"
                    "`owo profile` `owo marry @user` `owo divorce` `owo pray` `owo curse` `owo cookie @user` `owo 8b <q>`\n\n"
                    "**🎭 Roleplay Emotes**\n"
                    "`owo hug` `owo kiss` `owo slap` `owo pat` `owo blush` `owo cry` `owo dance` `owo smug`\n\n"
                    "**📊 Utilities**\n"
                    "`owo top` `owo prefix <new>`"
                ),
                color=0xED4245
            )
            embed.set_footer(text="Default Balance: 10,000 Coins | Daily: 777 Coins")
            await send_custom_channel_msg(message.channel, "PX OWO BOT", embed=embed)
        return

    await bot.process_commands(message)


# --- 15. Slash Commands Suite ---
@bot.tree.command(name="resetnames", description="Reset all members nicknames to their default Discord Display Name")
async def resetnames(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ Access Denied: Administrator permission required!", ephemeral=True)
        return

    await interaction.response.defer()
    guild = interaction.guild
    reset_count = 0

    for member in guild.members:
        if member.bot or member.id == guild.owner_id:
            continue
        if guild.me.top_role <= member.top_role:
            continue

        if member.nick is not None:
            try:
                await member.edit(nick=None, reason="Admin reset nicknames to default display name")
                reset_count += 1
                await asyncio.sleep(0.4)
            except Exception:
                pass

    await interaction.followup.send(f"✅ Success! **{reset_count}** members ke nicknames reset karke unka **default Discord Name** set kar diya gaya hai (Saare double PX tags remove ho gaye).")


@bot.tree.command(name="pxticketsetup", description="Deploy/Refresh the dynamic store ticket panel")
async def pxticketsetup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
        await interaction.followup.send("❌ Sirf Administrator use kar sakte hain!", ephemeral=True)
        return
    await force_fresh_ticket_panel(interaction.guild)
    await interaction.followup.send("✅ Dynamic ticket panel successfully refreshed & deployed!", ephemeral=True)


@bot.tree.command(name="giveaway", description="Launch an official PERSISTX Giveaway event")
@app_commands.describe(prize="Inam ka naam", duration_minutes="Kitne minute chalega", winners="Kitne winners honge")
async def giveaway(interaction: discord.Interaction, prize: str, duration_minutes: int, winners: int = 1):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ Access Denied: Administrator permission required.", ephemeral=True)
        return

    await interaction.response.defer()
    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
    end_timestamp = int(end_time.timestamp())

    embed = discord.Embed(
        title="✦  PERSISTX • OFFICIAL GIVEAWAY EVENT  ✦",
        description=(
            f"> 🎁 **Prize Item:** `{prize.upper()}`\n"
            f"> 🏆 **Winners Count:** `{winners}`\n"
            f"> ⏱️ **Event Concludes:** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n"
            f"> 👤 **Hosted By:** {interaction.user.mention}\n\n"
            f"╭─────────────────────────────────╮\n"
            f"  📌 **PARTICIPATION REQUIREMENTS**\n"
            f"╰─────────────────────────────────╯\n"
            f"• Click the **🎉** reaction below to enter the pool.\n"
            f"• Any other reaction will be automatically purged.\n\n"
            f"*Good luck to all PERSISTX community participants!* ✧"
        ),
        color=0xFEE75C
    )
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_author(name="PERSISTX ENTERPRISE", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="PX AUTOMATED GIVEAWAY SYSTEM © 2026", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.timestamp = end_time

    gw_msg = await interaction.channel.send(content="📢 @everyone @here — **OFFICIAL GIVEAWAY LAUNCHED** 🎁", embed=embed)
    await gw_msg.add_reaction("🎉")

    active_giveaways.add(gw_msg.id)
    await interaction.followup.send(f"✅ Giveaway event deployed successfully: {gw_msg.jump_url}", ephemeral=True)

    await asyncio.sleep(duration_minutes * 60)

    try:
        fresh_msg = await interaction.channel.fetch_message(gw_msg.id)
        reaction = discord.utils.get(fresh_msg.reactions, emoji="🎉")
        users = [u async for u in reaction.users() if not u.bot]

        active_giveaways.discard(gw_msg.id)

        if not users:
            no_winner_embed = discord.Embed(
                title="✦  GIVEAWAY CONCLUDED: NO PARTICIPANTS  ✦",
                description=f"The giveaway event for **{prize.upper()}** has ended without any valid entries.",
                color=0xED4245
            )
            await interaction.channel.send(embed=no_winner_embed)
            return

        selected_winners = random.sample(users, k=min(winners, len(users)))
        winner_mentions = ", ".join(w.mention for w in selected_winners)

        win_embed = discord.Embed(
            title="✦  GIVEAWAY CONCLUDED: WINNER ANNOUNCEMENT  ✦",
            description=(
                f"Congratulations to the verified winner(s) of the official event!\n\n"
                f"> 🏆 **Winner(s):** {winner_mentions}\n"
                f"> 🎁 **Prize Secured:** `{prize.upper()}`\n"
                f"> ⏱️ **Completed At:** <t:{int(datetime.utcnow().timestamp())}:F>\n\n"
                f"╭─────────────────────────────────╮\n"
                f"  📌 **PRIZE CLAIM PROTOCOL**\n"
                f"╰─────────────────────────────────╯\n"
                f"1. Open a private ticket via <#{TICKET_PANEL_CHANNEL_ID}>.\n"
                f"2. Select **`FREE PANEL • TRIAL / DAILY KEY`** or **`SUPPORT`**.\n"
                f"3. Provide this announcement link to claim your reward.\n\n"
                f"⚠️ *Prizes must be claimed within 24 hours of this notice.*"
            ),
            color=0x57F287
        )
        win_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        win_embed.set_author(name="PX REWARD DISPATCH", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        win_embed.set_footer(text="PERSISTX ENTERPRISE © 2026 • Verified Reward", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        win_embed.timestamp = datetime.utcnow()

        await interaction.channel.send(content=f"👑 **Congratulations** {winner_mentions}!", embed=win_embed)
    except Exception as e:
        print(f"[GIVEAWAY END ERROR]: {e}")


@bot.tree.command(name="clear", description="Clear a specific number of chat messages")
@app_commands.describe(amount="Messages count (Max: 100)")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages and interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ Manage Messages permission required!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=max(1, min(amount, 100)))
    await interaction.followup.send(f"🧹 Cleaned `{len(deleted)}` messages successfully!", ephemeral=True)


@bot.tree.command(name="ping", description="Check bot latency and API heartbeat")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 **Pong!** WebSocket Latency: `{latency}ms` | System: `Online 24/7`")


class OwOGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="owo", description="OwO Mini-Game & Economy Slash System")

owo_group = OwOGroup()

@owo_group.command(name="cash", description="Check current coin balance")
async def owo_cash_slash(interaction: discord.Interaction):
    if interaction.channel_id != OWO_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Sirf <#{OWO_CHANNEL_ID}> me use karein!", ephemeral=True)
        return
    display_bal = format_balance(interaction.user.id)
    await interaction.response.send_message(f"👛 **{interaction.user.display_name}**'s Balance: **{display_bal}** OwO Coins")

@owo_group.command(name="mine", description="Play 3x3 interactive Mines game")
@app_commands.describe(amount="Kitne coins ki shart lagani hai")
async def owo_mine_slash(interaction: discord.Interaction, amount: int):
    if interaction.channel_id != OWO_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Sirf <#{OWO_CHANNEL_ID}> me chalega!", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Amount valid hona chahiye!", ephemeral=True)
        return
    bal = get_user_balance(interaction.user.id)
    if interaction.user.id != MY_USER_ID and amount > bal:
        await interaction.response.send_message("❌ Insufficient balance!", ephemeral=True)
        return

    view = MinesGameView(interaction.user, amount)
    await interaction.response.send_message(
        content=f"💣 **MINES GAME STARTED** | Bet: **{amount:,}** Coins\nGrid me **3 Hidden Bombs (💣)** hain. 💎 dhoondhein aur Cashout karein!",
        view=view
    )

bot.tree.add_command(owo_group)


@bot.tree.command(name="help", description="Display full PERSISTX command list")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✦  PERSISTX COMMAND CENTER  ✦",
        description=(
            "**Store & Operations**\n"
            "• `/pxticketsetup` — Refresh & post dynamic product tickets\n"
            "• `/giveaway` — Host a verified clean giveaway\n"
            "• `qr` — Auto-dispenses payment scanner (Tickets, PX Client, Reseller & Custom Categories)\n\n"
            "**Administration & Moderation**\n"
            "• `/resetnames` — Bulk reset all members to their default Discord display names\n"
            "• `/clear <amount>` — Purge chat history quickly\n"
            "• `/ping` — Check bot latency\n\n"
            "**Complete OwO RPG System (In <#{OWO_CHANNEL_ID}>)**\n"
            "• Prefix: `owo <cmd>` or `w <cmd>`\n"
            "• Try: `owo daily`, `owo cash`, `owo hunt`, `owo zoo`, `owo sell all`, `owo shop`, `owo buy crate`, `owo battle`, `owo profile`, `owo marry @user`\n"
        ),
        color=0xED4245
    )
    embed.set_footer(text="PERSISTX ENTERPRISE © 2026 • 24/7 Active", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 16. Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("[ERROR] DISCORD_TOKEN environment variable nahi mila!", flush=True)
    else:
        bot.run(token)
