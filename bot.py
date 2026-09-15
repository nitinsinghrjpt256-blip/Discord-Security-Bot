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
import yt_dlp

# --- 1. Web Server (Render 24/7 Keep Alive) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "PERSISTX Master Bot is Online 24/7!"

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
intents.voice_states = True

MY_SERVER_ID = 1525181999147388958
MY_USER_ID = 1525179499602509977

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
TICKET_CATEGORY_ID = 1525181999646507118       

# Ticket Notification Logs
TICKET_OPEN_LOG_ID = 1544967681898450985
TICKET_CLOSE_LOG_ID = 1544391704323563612

# Categories to scan for dropdown
PC_CATEGORY_ID = 1525182001097998339
ANDROID_CATEGORY_ID = 1525182001097998345

# PX Client Channel / Support Channel
PX_CLIENT_CHANNEL_ID = 1549535112620679251

# 24/7 Voice Channel
PUBLIC_VC_ID = 1536673850358636614

QR_IMAGE_URL = "https://cdn.discordapp.com/attachments/1525182000825237654/1547499435225911346/image.png?ex=6aa99368&is=6aa841e8&hm=ff5c6c833995f75802abfc9c57bd1226ebb87766937e78c32de84810844530d4&"
ACCESS_DENIED_MSG = "❌ Access Denied: For Use Contact Super Admin PERSISTX !"

# Caches
invites_cache = {}          
user_invites = {}           
member_invited_by = {}      
user_balances = {}          
daily_cooldowns = {}        
channel_webhooks = {}       
inactivity_warned = set()
active_giveaways = set()

# Music Cache
song_queue = []
current_song = None

# Persistent Counter Logic
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
        author = f"{msg.author.name}#{msg.author.discriminator}" if msg.author.discriminator != '0' else msg.author.name
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
                    f"• **Customer:** {interaction.user.mention} (`{interaction.user.name}`)\n"
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
                    f"A ticket has been permanently closed.\n\n"
                    f"• **Ticket Channel:** `#{channel.name}`\n"
                    f"• **Opened By:** {ticket_creator.mention if ticket_creator else 'Unknown'}\n"
                    f"• **Closed By:** {user.mention} (`{user.name}`)\n"
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
                        f"Hello **{ticket_creator.name}**,\n\n"
                        f"Aapka support ticket (`#{channel.name}`) close kar diya gaya hai.\n\n"
                        f"• **Server:** `{guild.name}`\n"
                        f"• **Closed By:** `{user.name}`\n"
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
            await channel.delete(reason=f"Ticket closed by {user.name}")
        except Exception as e:
            print(f"Error deleting ticket channel: {e}")


# --- 4. Bot Instance Declaration ---
class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["!", "/"], intents=intents)

    async def setup_hook(self):
        self.add_view(TicketCloseView())

bot = SecurityBot()


# --- 5. Economy & Helpers ---
def get_user_balance(user_id: int) -> int:
    if user_id == MY_USER_ID:
        return 999_999_999_999
    return user_balances.get(user_id, 1000)

def format_balance(user_id: int) -> str:
    if user_id == MY_USER_ID:
        return "Unlimited (∞)"
    return f"{get_user_balance(user_id):,}"

def update_user_balance(user_id: int, amount: int):
    if user_id == MY_USER_ID:
        return
    current = user_balances.get(user_id, 1000)
    user_balances[user_id] = max(0, current + amount)

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
                f"• **Offender:** `{executor.name}` (`{executor.id}`)\n"
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


# --- 8. Dynamic Ticket Selection ---
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

        # Channel name is only the clean username (bina kisi ticket number ke)
        clean_name = "".join(c for c in user.name.lower() if c.isalnum() or c in ['-', '_'])[:20]
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
                topic=f"Ticket #{current_ticket_num} | User: {user.name} ({user.id}) | Item: {selected_product}"
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
                    f"• **User:** `{user.name}` (`{user.id}`)\n"
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
                f"Welcome {user.mention}! Your private ticket is ready.\n\n"
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


# --- 9. Inactivity Cleaner Task ---
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


# --- 11. Robust 24/7 Voice Channel Connection ---
@tasks.loop(seconds=30)
async def ensure_voice_connected():
    await bot.wait_until_ready()
    guild = bot.get_guild(MY_SERVER_ID)
    if not guild:
        return
    vc_channel = guild.get_channel(PUBLIC_VC_ID)
    if not vc_channel or not isinstance(vc_channel, discord.VoiceChannel):
        return

    voice_client = guild.voice_client
    try:
        if voice_client is None or not voice_client.is_connected():
            await vc_channel.connect(timeout=20.0, reconnect=True, self_deaf=True)
            print("[VOICE 24/7] Auto-Connected to Public VC!", flush=True)
        elif voice_client.channel.id != PUBLIC_VC_ID:
            await voice_client.move_to(vc_channel)
            print("[VOICE 24/7] Re-routed back to Public VC!", flush=True)
    except Exception as e:
        print(f"[VOICE CONNECT RETRY]: {e}", flush=True)


# --- 12. Security Checks & Ready Listener ---
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

        if not ensure_voice_connected.is_running():
            ensure_voice_connected.start()

        await force_fresh_ticket_panel(guild)

    for g in list(bot.guilds):
        if g.id != MY_SERVER_ID:
            await g.leave()


# --- 13. Channels & Role Watchdog ---
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
        # Ignored if inside any client or ticket related channel
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


# --- 14. Member Events ---
@bot.event
async def on_member_join(member):
    if member.guild.id != MY_SERVER_ID:
        return
    guild = member.guild

    # 1. Strict Anti-Nuke
    if member.bot:
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

    # 2. Auto-Role Assignment
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

    # 3. Auto PX Tag
    if member.id != guild.owner_id:
        try:
            if guild.me.top_role > member.top_role and not member.display_name.upper().startswith("PX"):
                await member.edit(nick=f"PX | {member.display_name}"[:32], reason="Auto PX tag on join")
        except Exception:
            pass

    # 4. Invite Tracker
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
                f"• **Username:** `{member.name}`\n"
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

    # 5. Professional Luxury Welcome DM
    try:
        dm_embed = discord.Embed(
            title="✦  WELCOME TO PERSISTX OFFICIAL COMMUNITY  ✦",
            description=(
                f"Hello **{member.name}**, welcome to **{guild.name}**! 🚀\n\n"
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
                f"• You have been automatically assigned **Family & Community** roles.\n"
                f"• Your profile has been formatted with the verified `PX | ` prefix.\n\n"
                f"*For official panel purchases or trial keys, please open a private ticket in <#{TICKET_PANEL_CHANNEL_ID}>.*"
            ),
            color=0xED4245
        )
        dm_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        dm_embed.set_author(name="PERSISTX ENTERPRISE", icon_url=guild.icon.url if guild.icon else None)
        dm_embed.set_footer(text="PERSISTX OFFICIAL STORE © 2026 • Verified Customer Portal", icon_url=guild.icon.url if guild.icon else None)
        dm_embed.timestamp = datetime.utcnow()
        await member.send(embed=dm_embed)
        print(f"[WELCOME DM SUCCESS] Sent luxury welcome DM to {member.name}", flush=True)
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
        leave_text = (
            f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
            f"  ✧ 𝐆𝐨𝐨𝐝𝐛𝐲𝐞 {member.name} ✧\n"
            f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n\n"
            f"> 🚪 **Member Left:** `{member.name}`\n"
            f"> 🔗 **Invited By:** <@{inviter_id}>\n\n"
            f"*We hope to see you again!* 🥀"
        )
        await send_custom_channel_msg(leave_channel, "PX LEAVE BOT", content=leave_text)


# --- 15. Message Event (Fixed QR for ALL Ticket & Client Channels) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    content = message.content.strip()
    lowered = content.lower()

    # --- QR ALLOWED CHECK (TICKET SYSTEM + PX CLIENT + TOPIC MATCH) ---
    is_ticket_by_topic = bool(message.channel.topic and "Ticket #" in message.channel.topic)
    
    cat_name = message.channel.category.name.lower() if message.channel.category else ""
    is_in_allowed_category = (
        (hasattr(message.channel, 'category_id') and message.channel.category_id == TICKET_CATEGORY_ID)
        or "client" in cat_name 
        or "ticket" in cat_name
    )
    is_client_channel = (message.channel.id == PX_CLIENT_CHANNEL_ID)

    # Agar inme se koi bhi match kare, channel me QR allowed hoga
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

    # OwO Mini-Games
    if lowered.startswith("owo") or lowered.startswith("px owo"):
        if message.guild.id != MY_SERVER_ID:
            await message.channel.send(ACCESS_DENIED_MSG)
            return
        if message.channel.id != OWO_CHANNEL_ID:
            return

        parts = content.split()
        if len(parts) == 1:
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"**{message.author.name}**! (Try `owo cash`, `owo daily`, `owo cf <amount>`, `owo s <amount>`, `owo mine <amount>`)")
            return

        subcmd = parts[1].lower()

        if subcmd in ["cash", "money", "bal", "balance"]:
            display_bal = format_balance(message.author.id)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"👛 **{message.author.display_name}**'s Balance: **{display_bal}** OwO Coins")

        elif subcmd in ["daily"]:
            now = datetime.utcnow()
            last_claim = daily_cooldowns.get(message.author.id)
            if last_claim and (now - last_claim) < timedelta(hours=24):
                rem = timedelta(hours=24) - (now - last_claim)
                hours, remainder = divmod(int(rem.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"⏳ Next claim in `{hours}h {minutes}m`.")
                return

            reward = 777
            update_user_balance(message.author.id, reward)
            daily_cooldowns[message.author.id] = now
            display_bal = format_balance(message.author.id)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎁 **{message.author.display_name}**, aapko daily **777** OwO Coins mile! Total: **{display_bal}**")

        elif subcmd in ["mine", "mines"]:
            if len(parts) < 3:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo mine <amount>`")
                return
            try:
                bet = int(parts[2])
            except ValueError:
                return
            if bet <= 0:
                return
            bal = get_user_balance(message.author.id)
            if message.author.id != MY_USER_ID and bet > bal:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Insufficient balance!")
                return

            view = MinesGameView(message.author, bet)
            await message.channel.send(
                content=f"💣 **MINES GAME STARTED** | Bet: **{bet:,}** OwO Coins\nGrid me **3 Hidden Bombs (💣)** hain. 💎 dhoondhein aur Cashout karein!",
                view=view
            )

        elif subcmd in ["cf", "coinflip"]:
            if len(parts) < 3:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo cf <amount> [h/t]`")
                return
            try:
                bet = int(parts[2])
            except ValueError:
                return
            if bet <= 0:
                return
            bal = get_user_balance(message.author.id)
            if message.author.id != MY_USER_ID and bet > bal:
                return
            choice = parts[3].lower()[0] if len(parts) >= 4 else "h"
            choice_str = "Heads" if choice == "h" else "Tails"
            result = random.choice(["Heads", "Tails"])

            if result == choice_str:
                update_user_balance(message.author.id, bet)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🪙 Lands on **{result}**! 🎉 Won **{bet:,}** Coins! (Balance: **{display_bal}**)")
            else:
                update_user_balance(message.author.id, -bet)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🪙 Lands on **{result}**! 💀 Lost **{bet:,}** Coins. (Balance: **{display_bal}**)")

        elif subcmd in ["s", "slot", "slots"]:
            if len(parts) < 3:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Usage: `owo s <amount>`")
                return
            try:
                bet = int(parts[2])
            except ValueError:
                return
            if bet <= 0:
                return
            bal = get_user_balance(message.author.id)
            if message.author.id != MY_USER_ID and bet > bal:
                return

            icons = ["🍒", "🍋", "🍇", "💎", "7️⃣"]
            r1, r2, r3 = random.choice(icons), random.choice(icons), random.choice(icons)
            if r1 == r2 == r3:
                winnings = bet * 4
                update_user_balance(message.author.id, winnings)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n🔥 **JACKPOT!** Won **{winnings:,}** Coins!")
            elif r1 == r2 or r2 == r3 or r1 == r3:
                winnings = int(bet * 1.5)
                update_user_balance(message.author.id, winnings - bet)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n✨ Small Win! Won **{winnings:,}** Coins!")
            else:
                update_user_balance(message.author.id, -bet)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n💔 Lost **{bet:,}** coins.")

        elif subcmd in ["give", "pay", "send"]:
            if len(message.mentions) == 0 or len(parts) < 4:
                return
            target = message.mentions[0]
            if target.id == message.author.id:
                return
            try:
                amount = int(parts[3])
            except ValueError:
                return
            if amount <= 0:
                return
            bal = get_user_balance(message.author.id)
            if message.author.id != MY_USER_ID and amount > bal:
                return
            update_user_balance(message.author.id, -amount)
            update_user_balance(target.id, amount)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"💸 Transferred **{amount:,}** Coins to {target.mention}!")

    await bot.process_commands(message)


# --- 16. Audio Streaming Core ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios']
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.9"'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

def play_next_song(guild: discord.Guild):
    global current_song
    if len(song_queue) > 0:
        next_track = song_queue.pop(0)
        current_song = next_track
        voice_client = guild.voice_client
        if voice_client and voice_client.is_connected():
            audio_source = discord.FFmpegPCMAudio(next_track['url'], **FFMPEG_OPTIONS)
            voice_client.play(audio_source, after=lambda e: play_next_song(guild))
    else:
        current_song = None


# --- 17. Slash Commands Suite ---
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


# --- Music Commands ---
@bot.tree.command(name="joinvc", description="Forcefully connect bot to 24/7 Public VC")
async def joinvc(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    vc_channel = guild.get_channel(PUBLIC_VC_ID)
    if not vc_channel:
        await interaction.followup.send("❌ Channel ID galat hai ya channel exist nahi karta!", ephemeral=True)
        return
        
    voice_client = guild.voice_client
    try:
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(vc_channel)
        else:
            await vc_channel.connect(timeout=20.0, reconnect=True, self_deaf=True)
        await interaction.followup.send(f"✅ Bot successfully joined <#{PUBLIC_VC_ID}>!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Join failed: `{e}`", ephemeral=True)


@bot.tree.command(name="play", description="Play audio from YouTube, Spotify title, or direct link in 24/7 VC")
@app_commands.describe(query="Song name or link")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    guild = interaction.guild

    vc_channel = guild.get_channel(PUBLIC_VC_ID)
    voice_client = guild.voice_client

    if not voice_client or not voice_client.is_connected():
        if vc_channel:
            voice_client = await vc_channel.connect(reconnect=True, self_deaf=True)
        else:
            await interaction.followup.send("❌ Public VC channel nahi mila!")
            return

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]

        track_url = data['url']
        track_title = data.get('title', 'Unknown Track')
        track_duration = str(timedelta(seconds=data.get('duration', 0))) if data.get('duration') else "Live / Unknown"

        song_info = {
            'title': track_title,
            'url': track_url,
            'webpage_url': data.get('webpage_url', query),
            'duration': track_duration,
            'requester': interaction.user.mention
        }

        if voice_client.is_playing() or voice_client.is_paused():
            song_queue.append(song_info)
            embed = discord.Embed(
                title="🎵  TRACK QUEUED",
                description=f"**[{track_title}]({song_info['webpage_url']})**\n\n• **Duration:** `{track_duration}`\n• **Requested by:** {interaction.user.mention}",
                color=0xFEE75C
            )
            embed.set_footer(text="PX 24/7 AUDIO ENGINE • PERSISTX")
            await interaction.followup.send(embed=embed)
        else:
            global current_song
            current_song = song_info
            audio_source = discord.FFmpegPCMAudio(track_url, **FFMPEG_OPTIONS)
            voice_client.play(audio_source, after=lambda e: play_next_song(guild))

            embed = discord.Embed(
                title="🔊  NOW PLAYING IN PUBLIC VC",
                description=(
                    f"**[{track_title}]({song_info['webpage_url']})**\n\n"
                    f"• **Channel:** <#{PUBLIC_VC_ID}>\n"
                    f"• **Duration:** `{track_duration}`\n"
                    f"• **Status:** `Streaming 24/7`\n"
                    f"• **Requested by:** {interaction.user.mention}"
                ),
                color=0x57F287
            )
            embed.set_footer(text="PERSISTX LUXURY AUDIO SUITE © 2026")
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error loading track: `{str(e)[:150]}`")


@bot.tree.command(name="skip", description="Skip currently playing track")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("⏭️ Track skipped!")
    else:
        await interaction.response.send_message("❌ Koi track play nahi ho raha hai.", ephemeral=True)


@bot.tree.command(name="pause", description="Pause current song")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("⏸️ Music paused.")
    else:
        await interaction.response.send_message("❌ Music already paused hai ya playing nahi hai.", ephemeral=True)


@bot.tree.command(name="resume", description="Resume paused song")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("▶️ Music resumed.")
    else:
        await interaction.response.send_message("❌ Music paused nahi hai.", ephemeral=True)


@bot.tree.command(name="stop", description="Clear music queue and stop playing (Bot stays in VC 24/7)")
async def stop(interaction: discord.Interaction):
    global current_song
    voice_client = interaction.guild.voice_client
    song_queue.clear()
    current_song = None
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
    await interaction.response.send_message("⏹️ Music stopped and queue cleared. Bot will remain in 24/7 Public VC.")


@bot.tree.command(name="queue", description="View songs in queue")
async def view_queue(interaction: discord.Interaction):
    if not current_song and len(song_queue) == 0:
        await interaction.response.send_message("📭 Queue bilkul empty hai.", ephemeral=True)
        return

    desc = ""
    if current_song:
        desc += f"**Now Playing:** `{current_song['title']}` ({current_song['duration']})\n\n**Upcoming Queue:**\n"

    for i, track in enumerate(song_queue[:10], 1):
        desc += f"`{i}.` {track['title']} (`{track['duration']}`) | {track['requester']}\n"

    if len(song_queue) > 10:
        desc += f"\n*...and {len(song_queue) - 10} more songs in queue.*"

    embed = discord.Embed(title="✦  PERSISTX AUDIO QUEUE  ✦", description=desc, color=0xED4245)
    await interaction.response.send_message(embed=embed)


# --- Utility Commands ---
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


@bot.tree.command(name="setpx", description="Apply PX | prefix to all non-tagged server members")
async def setpx(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ Administrator permission required!", ephemeral=True)
        return
    await interaction.response.defer()
    guild = interaction.guild
    changed = 0
    for member in guild.members:
        if member.bot or member.id == guild.owner_id:
            continue
        if guild.me.top_role <= member.top_role:
            continue
        if not member.display_name.upper().startswith("PX"):
            try:
                await member.edit(nick=f"PX | {member.display_name}"[:32])
                changed += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass
    await interaction.followup.send(f"✅ Updated `{changed}` members with `PX | ` prefix.")


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
            "• `qr` — Auto-dispenses payment scanner (Works in Tickets & Client Channels)\n\n"
            "**Music & Voice (24/7 in <#{PUBLIC_VC_ID}>)**\n"
            "• `/joinvc` — Force-join bot to 24/7 Public VC\n"
            "• `/play <query>` — Play YouTube/Spotify track title or URL\n"
            "• `/skip` — Skip active song\n"
            "• `/pause` & `/resume` — Control audio stream\n"
            "• `/queue` — View upcoming queued tracks\n"
            "• `/stop` — Clear queue (Bot stays in VC 24/7)\n\n"
            "**Administration & Moderation**\n"
            "• `/clear <amount>` — Purge chat history quickly\n"
            "• `/setpx` — Auto-apply `PX | ` tag across all members\n"
            "• `/ping` — Check bot latency\n\n"
            "**Economy & Games (In <#{OWO_CHANNEL_ID}>)**\n"
            "• `owo cash` / `/owo cash` — View coin reserves\n"
            "• `owo daily` — Claim daily 777 bonus coins\n"
            "• `owo mine <bet>` / `/owo mine <bet>` — Interactive 3x3 Mines\n"
            "• `owo cf <bet> [h/t]` — 50/50 Coin Flip\n"
            "• `owo s <bet>` — Casino Slots\n"
            "• `owo give @user <amount>` — Transfer coins\n"
        ),
        color=0xED4245
    )
    embed.set_footer(text="PERSISTX ENTERPRISE © 2026 • 24/7 Active", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 18. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("[ERROR] DISCORD_TOKEN environment variable nahi mila!", flush=True)
    else:
        bot.run(token)
