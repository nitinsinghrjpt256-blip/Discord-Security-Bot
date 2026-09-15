import os
import random
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# --- 1. Web Server (Render 24/7 Keep Alive) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "PX Complete Dynamic Ticket & OwO Master Bot is Online 24/7!"

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
MY_USER_ID = 1525179499602509977
WHITELIST_USERS = []

WELCOME_CHANNEL_ID = 1525182000825237648       # PX WELCOMER BOT
INVITE_LOG_CHANNEL_ID = 1548745613640859729    # PX INVITER BOT
LEAVE_CHANNEL_ID = 1548745646717014029         # PX LEAVE BOT
OWO_CHANNEL_ID = 1548770349351575632           # PX OWO BOT

CHAT_CHANNEL_ID = 1536673179010080860
RULE_CHANNEL_ID = 1525203386025119807

TICKET_PANEL_CHANNEL_ID = 1525182000825237653  
TICKET_CATEGORY_ID = 1525181999646507118       

# Ticket Logs Notification Channels
TICKET_OPEN_LOG_ID = 1544967681898450985
TICKET_CLOSE_LOG_ID = 1544391704323563612

# Product Categories jo Dropdown me auto-reflect hongi
SYNC_CATEGORY_IDS = [1525182001097998345, 1525182001097998339]

# Official CDN QR Code Link
QR_IMAGE_URL = "https://cdn.discordapp.com/attachments/1525182000825237654/1547499435225911346/image.png?ex=6aa99368&is=6aa841e8&hm=ff5c6c833995f75802abfc9c57bd1226ebb87766937e78c32de84810844530d4&"

ticket_counter = 207
ACCESS_DENIED_MSG = "❌ Access Denied: For Use Contact Super Admin PERSISTX !"

# Caches
invites_cache = {}          
user_invites = {}           
member_invited_by = {}      
user_balances = {}          
daily_cooldowns = {}        
channel_webhooks = {}       
panel_message_id = None


# --- 3. OwO Economy Helpers ---
def get_user_balance(user_id: int) -> int:
    if user_id == MY_USER_ID:
        return 999_999_999_999
    return user_balances.get(user_id, 1000)

def format_balance(user_id: int) -> str:
    if user_id == MY_USER_ID:
        return "1,432,567"
    return f"{get_user_balance(user_id):,}"

def update_user_balance(user_id: int, amount: int):
    if user_id == MY_USER_ID:
        return
    current = user_balances.get(user_id, 1000)
    user_balances[user_id] = max(0, current + amount)


# --- 4. Webhook Identity Sender ---
async def send_custom_channel_msg(channel: discord.TextChannel, bot_name: str, content=None, embed=None, view=None):
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
        if view:
            return await channel.send(content=content, embed=embed, view=view)

        return await webhook.send(
            content=content,
            embed=embed,
            username=bot_name,
            avatar_url=avatar_url,
            wait=True
        )
    except Exception:
        return await channel.send(content=content, embed=embed, view=view)


# --- 5. Anti-Nuke Engine ---
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
                f"• **Status:** Stripped roles & Banned instantly."
            )
    except Exception:
        pass


# --- 6. Aesthetic Ticket System & Ordered Generator ---
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.danger, custom_id="px_ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        await interaction.response.send_message("⏳ **Closing Ticket...** Channel 3 seconds me delete ho jayega.")

        # Professional Close Log Notification
        close_log_channel = guild.get_channel(TICKET_CLOSE_LOG_ID)
        if close_log_channel:
            close_embed = discord.Embed(
                title="🔒  TICKET CLOSED LOG",
                description=(
                    f"A ticket has been permanently closed.\n\n"
                    f"• **Ticket Channel:** `#{channel.name}`\n"
                    f"• **Closed By:** {user.mention} (`{user.name}`)\n"
                    f"• **Category:** `PERSISTX TICKETS`\n"
                    f"• **Timestamp:** <t:{int(datetime.utcnow().timestamp())}:F>"
                ),
                color=0xED4245
            )
            close_embed.set_author(name="PX TICKET AUDIT", icon_url=guild.icon.url if guild.icon else None)
            close_embed.set_footer(text="PX Security & Ticket System © 2026", icon_url=guild.icon.url if guild.icon else None)
            close_embed.timestamp = datetime.utcnow()
            try:
                await close_log_channel.send(embed=close_embed)
            except Exception:
                pass

        await asyncio.sleep(3)
        try:
            await channel.delete(reason=f"Ticket closed by {user.name}")
        except Exception as e:
            print(f"Error deleting ticket channel: {e}")


def generate_ticket_options(guild: discord.Guild):
    pc_options = []
    android_options = []

    android_keywords = ["APK", "MOD", "INJECTOR", "ROOT", "DRIP", "PATO", "HAXXCKER", "NINE-X", "BR-MOD"]

    if guild:
        for cat_id in SYNC_CATEGORY_IDS:
            cat = guild.get_channel(cat_id)
            if cat and isinstance(cat, discord.CategoryChannel):
                for ch in cat.text_channels:
                    clean_name = ch.name.replace("🛒", "").replace("・", "").replace("-", " ").strip().upper()
                    raw_upper = ch.name.upper()

                    is_android = any(k in raw_upper or k in clean_name for k in android_keywords)

                    if is_android:
                        android_options.append(
                            discord.SelectOption(
                                label=f"ANDROID • {clean_name}"[:100],
                                description=f"Instant purchase & key for #{ch.name}"[:100],
                                emoji="📱"
                            )
                        )
                    else:
                        pc_options.append(
                            discord.SelectOption(
                                label=f"PC PANEL • {clean_name}"[:100],
                                description=f"Instant purchase & key for #{ch.name}"[:100],
                                emoji="💻"
                            )
                        )

    other_options = [
        discord.SelectOption(label="FREE PANEL • TRIAL / DAILY KEY", description="Get your free trial panel access key", emoji="🆓"),
        discord.SelectOption(label="RESELLER PANEL • BULK KEYS", description="Start your own panel reselling business", emoji="🤝"),
        discord.SelectOption(label="CUSTOM PANEL DEVELOPMENT", description="Order private branded panel with your name", emoji="⚙️"),
        discord.SelectOption(label="TECHNICAL SUPPORT & HELP", description="Direct assistance from PERSISTX", emoji="🆘")
    ]

    available_slots = 25 - len(other_options)
    half_slots = available_slots // 2

    selected_pc = pc_options[:half_slots]
    selected_android = android_options[:(available_slots - len(selected_pc))]

    ordered_options = selected_pc + selected_android + other_options
    return ordered_options[:25]


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
        global ticket_counter
        guild = interaction.guild
        user = interaction.user
        selected_product = self.values[0]

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category nahi mili! Check category ID.", ephemeral=True)
            return

        clean_name = "".join(c for c in user.name.lower() if c.isalnum() or c in ['-', '_'])[:10]
        channel_name = f"ticket-{clean_name}-{ticket_counter}"
        current_ticket_num = ticket_counter
        ticket_counter += 1

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

        # Professional Open Log Notification
        open_log_channel = guild.get_channel(TICKET_OPEN_LOG_ID)
        if open_log_channel:
            open_embed = discord.Embed(
                title="🎫  NEW TICKET CREATED",
                description=(
                    f"A new ticket has been opened by {user.mention}.\n\n"
                    f"• **Ticket Channel:** {ticket_channel.mention} (`#{channel_name}`)\n"
                    f"• **Ticket ID:** `#{current_ticket_num}`\n"
                    f"• **User:** `{user.name}` (`{user.id}`)\n"
                    f"• **Selected Product:** `{selected_product}`\n"
                    f"• **Created At:** <t:{int(datetime.utcnow().timestamp())}:F>"
                ),
                color=0x57F287
            )
            open_embed.set_thumbnail(url=user.display_avatar.url)
            open_embed.set_author(name="PX TICKET LOGS", icon_url=guild.icon.url if guild.icon else None)
            open_embed.set_footer(text="PX Notification Service © 2026", icon_url=guild.icon.url if guild.icon else None)
            open_embed.timestamp = datetime.utcnow()
            try:
                await open_log_channel.send(embed=open_embed)
            except Exception:
                pass

        embed = discord.Embed(
            title="✦  PERSISTX • ORDER & SUPPORT TICKET  ✦",
            description=(
                f"Hello {user.mention}, thank you for reaching out!\n"
                f"> 🎫 **Ticket ID:** `#{current_ticket_num}`\n"
                f"> 📦 **Selected Product:** `{selected_product}`\n"
                f"> ⏱️ **Delivery Status:** `Instant Auto-Dispatch / Admin Verification`\n\n"
                f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
                f"  💳 **PAYMENT & DETAILS**\n"
                f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n"
                f"• **BINANCE PAY ID:** `Releasing Soon` (NAME: `PERSISTX`)\n"
                f"• **UPI / QR SCAN:** *Scan the official QR code below.*\n\n"
                f"📌 **Next Steps:**\n"
                f"1. Agar **Buy** karna hai toh payment karke screenshot yahan bhejein.\n"
                f"2. Agar **Free Panel Key** ya **Support** chahiye toh yahan message type karein.\n\n"
                f"💡 *Tip: Chat me kabhi bhi **qr** likhenge toh instant payment QR code aa jayega!* 🚀\n\n"
                f"*Staff and <@{MY_USER_ID}> will assist you shortly!*"
            ),
            color=0xED4245
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=QR_IMAGE_URL)
        embed.set_footer(text="PX STORE © 2026 • Powered by PERSISTX", icon_url=guild.icon.url if guild.icon else None)
        embed.timestamp = datetime.utcnow()

        close_view = TicketCloseView()
        await ticket_channel.send(content=f"{user.mention} | <@{MY_USER_ID}>", embed=embed, view=close_view)
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
    embed.set_author(name="PX TICKET KING • PERSISTX", icon_url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="PERSISTX ENTERPRISE © 2026 • Verified Store", icon_url=guild.icon.url if guild.icon else None)
    return embed


async def update_ticket_panel(guild: discord.Guild):
    global panel_message_id
    t_channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not t_channel:
        return

    options = generate_ticket_options(guild)
    view = DynamicTicketView(options)
    embed = get_ticket_panel_embed(guild)

    try:
        if panel_message_id:
            try:
                msg = await t_channel.fetch_message(panel_message_id)
                await msg.edit(embed=embed, view=view)
                print("[AUTO-SYNC] Panel updated dynamically with ordered options!", flush=True)
                return
            except Exception:
                pass

        async for msg in t_channel.history(limit=10):
            if msg.author.id == bot.user.id and len(msg.embeds) > 0:
                panel_message_id = msg.id
                await msg.edit(embed=embed, view=view)
                print("[AUTO-SYNC] Panel message refreshed with ordered options!", flush=True)
                return

        new_msg = await t_channel.send(embed=embed, view=view)
        panel_message_id = new_msg.id
        print("[AUTO-SYNC] Fresh panel posted!", flush=True)
    except Exception as e:
        print(f"[PANEL UPDATE ERROR]: {e}", flush=True)


# --- 7. Mines Mini-Game View ---
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


# --- 8. Bot Setup ---
class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["!", "/"], intents=intents)

    async def setup_hook(self):
        self.add_view(TicketCloseView())

bot = SecurityBot()


# --- 9. Event Listeners ---
@bot.event
async def on_ready():
    print(f"\n==========================================", flush=True)
    print(f"[ONLINE] Logged in as: {bot.user.name} ({bot.user.id})", flush=True)
    print(f"[SECURE] Authorized ONLY for Guild ID: {MY_SERVER_ID}", flush=True)
    print(f"==========================================\n", flush=True)

    guild = bot.get_guild(MY_SERVER_ID)
    if guild:
        try:
            guild_obj = discord.Object(id=MY_SERVER_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"[SLASH-SYNC] Synced {len(synced)} commands directly to Guild!", flush=True)
        except Exception as e:
            print(f"[SLASH-SYNC ERROR]: {e}", flush=True)

        try:
            guild_invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite in guild_invites}
        except Exception:
            pass

        await update_ticket_panel(guild)

    for g in list(bot.guilds):
        if g.id != MY_SERVER_ID:
            await g.leave()


@bot.event
async def on_guild_channel_create(channel):
    if channel.guild.id != MY_SERVER_ID:
        return
    if channel.category_id in SYNC_CATEGORY_IDS:
        await asyncio.sleep(1)
        await update_ticket_panel(channel.guild)


@bot.event
async def on_guild_channel_delete(channel):
    if channel.guild.id != MY_SERVER_ID:
        return
    
    if channel.category_id in SYNC_CATEGORY_IDS:
        await asyncio.sleep(1)
        await update_ticket_panel(channel.guild)
        return

    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        executor = entry.user
        if "ticket-" in channel.name.lower():
            return
        await execute_antinuke_punishment(guild, executor, f"Channel Deletion: #{channel.name}")


@bot.event
async def on_guild_channel_update(before, after):
    if after.guild.id != MY_SERVER_ID:
        return
    if after.category_id in SYNC_CATEGORY_IDS and before.name != after.name:
        await update_ticket_panel(after.guild)


@bot.event
async def on_guild_role_delete(role):
    if role.guild.id != MY_SERVER_ID:
        return
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        executor = entry.user
        await execute_antinuke_punishment(guild, executor, f"Role Deletion: @{role.name}")


@bot.event
async def on_member_join(member):
    if member.guild.id != MY_SERVER_ID:
        return
    guild = member.guild

    if member.bot:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
            inviter = entry.user
            await execute_antinuke_punishment(guild, inviter, f"Bot Added: {member.name}")
            try:
                await member.ban(reason="Anti-Nuke: Unauthorized Bot")
            except Exception:
                pass
            return

    if not member.bot and member.id != guild.owner_id:
        try:
            if guild.me.top_role > member.top_role and not member.display_name.upper().startswith("PX"):
                await member.edit(nick=f"PX | {member.display_name}"[:32], reason="Auto PX tag on join")
        except Exception:
            pass

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


# --- 10. Message Event (Auto-QR in Tickets, OwO & Commands) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    content = message.content.strip()
    lowered = content.lower()

    # 1. AUTO-QR TRIGGER IN TICKETS
    is_in_ticket = "ticket-" in message.channel.name.lower() or (
        hasattr(message.channel, 'category_id') and message.channel.category_id == TICKET_CATEGORY_ID
    )

    if is_in_ticket and lowered in ["qr", "send qr", "!qr", "qr code", "payment qr", "scanner"]:
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
        qr_embed.set_footer(text="PX SECURE PAYMENT SYSTEM © 2026", icon_url=message.guild.icon.url if message.guild.icon else None)
        qr_embed.timestamp = datetime.utcnow()
        await message.channel.send(embed=qr_embed)
        return

    # 2. Text Setup Command
    if lowered in ["!pxticketsetup", "!ticketsetup", "/pxticketsetup"]:
        if message.guild.id != MY_SERVER_ID:
            await message.channel.send(ACCESS_DENIED_MSG)
            return

        if not message.author.guild_permissions.administrator and message.author.id != MY_USER_ID:
            await message.channel.send("❌ Sirf Administrator use kar sakte hain!")
            return

        await update_ticket_panel(message.guild)
        await message.channel.send("✅ Dynamic ticket panel successfully updated/sent!")
        return

    # 3. OwO Mini-Games
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

            reward = random.randint(5000, 15000)
            update_user_balance(message.author.id, reward)
            daily_cooldowns[message.author.id] = now
            display_bal = format_balance(message.author.id)
            await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎁 **{message.author.display_name}**, aapko **{reward:,}** OwO Coins mile! Total: **{display_bal}**")

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


# --- 11. Slash Commands Suite ---
@bot.tree.command(name="pxticketsetup", description="Deploy dynamic ticket panel reading from categories")
async def pxticketsetup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
        await interaction.followup.send("❌ Sirf Administrator use kar sakte hain!", ephemeral=True)
        return

    await update_ticket_panel(interaction.guild)
    await interaction.followup.send("✅ Dynamic ticket panel successfully updated!", ephemeral=True)


class OwOGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="owo", description="OwO Mini-Game & Economy Commands")

owo_group = OwOGroup()

@owo_group.command(name="cash", description="Check coin balance")
async def owo_cash(interaction: discord.Interaction):
    if interaction.channel_id != OWO_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Sirf <#{OWO_CHANNEL_ID}> me chalega!", ephemeral=True)
        return
    display_bal = format_balance(interaction.user.id)
    await interaction.response.send_message(f"👛 Balance: **{display_bal}** OwO Coins")

@owo_group.command(name="mine", description="Play 3x3 interactive Mines game")
@app_commands.describe(amount="Kitne coins ki shart lagani hai")
async def owo_mine_slash(interaction: discord.Interaction, amount: int):
    if interaction.channel_id != OWO_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Sirf <#{OWO_CHANNEL_ID}> me chalega!", ephemeral=True)
        return
    if amount <= 0:
        return
    bal = get_user_balance(interaction.user.id)
    if interaction.user.id != MY_USER_ID and amount > bal:
        await interaction.response.send_message("❌ Insufficient balance!", ephemeral=True)
        return

    view = MinesGameView(interaction.user, amount)
    await interaction.response.send_message(
        content=f"💣 **MINES GAME STARTED** | Bet: **{amount:,}** Coins\n3 Hidden Bombs (💣). 💎 dhoondhein aur Cashout karein!",
        view=view
    )

bot.tree.add_command(owo_group)


@bot.tree.command(name="setpx", description="Bulk apply PX | prefix to members")
async def setpx(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
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
    await interaction.followup.send(f"✅ `{changed}` members updated with `PX | `.")


@bot.tree.command(name="clear", description="Clear chat messages")
@app_commands.describe(amount="Messages count")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages and interaction.user.id != MY_USER_ID:
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=max(1, amount))
    await interaction.followup.send(f"🧹 `{len(deleted)}` messages deleted!", ephemeral=True)


@bot.tree.command(name="ping", description="Check latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")


# --- 12. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("[ERROR] DISCORD_TOKEN environment variable nahi mila!", flush=True)
    else:
        bot.run(token)
