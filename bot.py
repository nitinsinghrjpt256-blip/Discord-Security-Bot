import os
import random
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# --- 1. Web Server (Render & UptimeRobot 24/7) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "PX Military Anti-Nuke, Ticket & OwO System is online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web, daemon=True)
    t.start()


# --- 2. Discord Bot Setup & Intents ---
intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  
intents.guilds = True           
intents.invites = True          
intents.reactions = True        

# Configuration Constants
MY_SERVER_ID = 1525181999147388958             # Target Guild ID
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
QR_IMAGE_URL = "https://i.ibb.co/3sLz11T/px-qr.png" 

ticket_counter = 207
ACCESS_DENIED_MSG = "❌ Access Denied: For Use Contact Super Admin PERSISTX !"

# Caches
invites_cache = {}          
user_invites = {}           
member_invited_by = {}      
active_giveaways = {}
user_balances = {}          
daily_cooldowns = {}        
channel_webhooks = {}       


class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TicketSelectView())
        self.add_view(TicketCloseView())

bot = SecurityBot()


# --- OwO Helper Functions ---
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


# --- Anti-Nuke Execution Engine ---
async def execute_antinuke_punishment(guild: discord.Guild, executor: discord.Member, action: str):
    if executor.id == bot.user.id or guild.id != MY_SERVER_ID:
        return

    print(f"[ANTINUKE TRIGGERED] Action: {action} by {executor.name} ({executor.id})", flush=True)

    try:
        dangerous_roles = [r for r in executor.roles if r.name != "@everyone" and r < guild.me.top_role]
        if dangerous_roles:
            await executor.remove_roles(*dangerous_roles, reason=f"Anti-Nuke: {action}")
    except Exception as e:
        print(f"[ROLE STRIP ERROR]: {e}", flush=True)

    try:
        await guild.ban(executor, reason=f"Anti-Nuke Protection: Unauthorized {action}", delete_message_days=0)
        print(f"[ANTINUKE SUCCESS] {executor.name} banned instantly!", flush=True)
    except Exception as e:
        print(f"[BAN ERROR]: {e}", flush=True)

    try:
        owner = guild.owner
        if owner and owner.id != executor.id:
            await owner.send(
                f"🚨 **HIGH SECURITY ANTI-NUKE ALERT** 🚨\n\n"
                f"• **Offender:** `{executor.name}` (`{executor.id}`)\n"
                f"• **Action Detected:** `{action}`\n"
                f"• **Status:** Roles Stripped & Ban Applied Immediately."
            )
    except Exception:
        pass


# --- Channel Identity Webhook Sender ---
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


# --- 3. AESTHETIC TICKET SYSTEM COMPONENTS ---

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.danger, custom_id="px_ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏳ **Closing Ticket...** Channel 3 seconds me delete ho jayega.")
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except Exception as e:
            print(f"Error deleting ticket channel: {e}")


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="PC PANEL • FULL VIP (EXE)", description="Aimkill, Headshot, Silent Aim, ESP - PC", emoji="💻"),
            discord.SelectOption(label="PC PANEL • STREAMER BYPASS", description="Stream-Proof undetected bypass for PC", emoji="🖥️"),
            discord.SelectOption(label="PC PANEL • INTERNAL INJECTION", description="Ultra-smooth internal memory panel", emoji="⚡"),
            discord.SelectOption(label="ANDROID INJECTOR • ROOT / NON-ROOT", description="Auto Headshot, Aimlock, 32/64 Bit Android", emoji="📱"),
            discord.SelectOption(label="ANDROID INJECTOR • LIB BYPASS VIP", description="100% Main ID Safe Lib Memory Injector", emoji="🛡️"),
            discord.SelectOption(label="ANDROID INJECTOR • EMOTE & VAULT", description="Rare bundles & all emotes unlock injector", emoji="✨"),
            discord.SelectOption(label="FREE PANEL • TRIAL / DAILY KEY", description="Get your free trial panel access key", emoji="🆓"),
            discord.SelectOption(label="RESELLER PANEL • BULK KEYS", description="Start your own panel reselling business", emoji="🤝"),
            discord.SelectOption(label="FF ID MARKET • BUY / SELL", description="Verified high-level Free Fire ID deals", emoji="🛒"),
            discord.SelectOption(label="CUSTOM PANEL DEVELOPMENT", description="Order private branded panel with your name", emoji="⚙️"),
            discord.SelectOption(label="TECHNICAL SUPPORT & HELP", description="Direct support from Super Admin PERSISTX", emoji="🆘")
        ]
        super().__init__(
            placeholder="Select PC Panel or Android Injector... 🛍️",
            min_values=1,
            max_values=1,
            custom_id="px_ticket_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        global ticket_counter
        guild = interaction.guild
        user = interaction.user
        selected_product = self.values[0]

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category nahi mili! Check `TICKET_CATEGORY_ID`.", ephemeral=True)
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
            await interaction.followup.send(f"❌ Ticket create nahi ho paya: {e}", ephemeral=True)
            return

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
                f"• **BINANCE PAY ID:** `1210948888` (NAME: `PERSISTX`)\n"
                f"• **UPI / QR SCAN:** *Scan the official QR code below.*\n\n"
                f"📌 **Next Steps:**\n"
                f"1. Agar aapne **Buy** karna hai to payment karke screenshot yahan bhejein.\n"
                f"2. Agar **Free Panel Key** ya **Support** chahiye to apni inquiry yahan likhein.\n\n"
                f"*Staff and <@{MY_USER_ID}> will assist you shortly!*"
            ),
            color=0xED4245
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=QR_IMAGE_URL)
        embed.set_footer(text=f"PX STORE © 2026 • Powered by PERSISTX", icon_url=guild.icon.url if guild.icon else None)
        embed.timestamp = datetime.utcnow()

        close_view = TicketCloseView()
        await ticket_channel.send(content=f"{user.mention} | <@{MY_USER_ID}>", embed=embed, view=close_view)
        await interaction.followup.send(f"✅ Ticket create ho gaya: {ticket_channel.mention}", ephemeral=True)


class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


def get_ticket_panel_embed(guild):
    embed = discord.Embed(
        title="✦  PERSISTX • OFFICIAL PC & ANDROID STORE  ✦",
        description=(
            "Welcome to **PERSISTX OFFICIAL STORE**! 🚀\n"
            "Choose your required **PC Panel**, **Android Injector**, or **Free Key** from the menu below.\n\n"
            "```yaml\n"
            "BINANCE PAY ID : 1210948888\n"
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


# --- 4. AUTO-CATEGORY SYNC ---
@bot.event
async def on_guild_channel_create(channel):
    if channel.guild.id != MY_SERVER_ID:
        return

    name_lower = channel.name.lower()
    keywords = ["pc-panel", "pcpanel", "android", "injector", "free-key", "panel-key"]
    
    if any(k in name_lower for k in keywords) and channel.category_id != TICKET_CATEGORY_ID:
        target_category = channel.guild.get_channel(TICKET_CATEGORY_ID)
        if target_category and isinstance(target_category, discord.CategoryChannel):
            try:
                await channel.edit(category=target_category, sync_permissions=True, reason="Auto-moved to Ticket/Panel category")
                print(f"[AUTO-SYNC] Moved channel #{channel.name} into Ticket Category!", flush=True)
            except Exception as e:
                print(f"[AUTO-SYNC ERROR]: {e}", flush=True)


# --- 5. SERVER AUTHORIZATION SYSTEM ---
@bot.event
async def on_guild_join(guild):
    if guild.id != MY_SERVER_ID:
        print(f"[UNAUTHORIZED SERVER] Auto-leaving: {guild.name}", flush=True)
        try:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(ACCESS_DENIED_MSG)
                    break
        except Exception:
            pass
        await guild.leave()


@bot.tree.interaction_check
async def global_slash_check(interaction: discord.Interaction):
    if not interaction.guild or interaction.guild.id != MY_SERVER_ID:
        await interaction.response.send_message(ACCESS_DENIED_MSG, ephemeral=True)
        return False
    return True


# --- 6. ANTI-NUKE LISTENERS ---
@bot.event
async def on_guild_channel_delete(channel):
    if channel.guild.id != MY_SERVER_ID:
        return
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        executor = entry.user
        if "ticket-" in channel.name.lower():
            return
        await execute_antinuke_punishment(guild, executor, f"Channel Deletion: #{channel.name}")

@bot.event
async def on_guild_role_delete(role):
    if role.guild.id != MY_SERVER_ID:
        return
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        executor = entry.user
        await execute_antinuke_punishment(guild, executor, f"Role Deletion: @{role.name}")


# --- 7. Member Join & Leave Events ---
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
                await member.edit(nick=f"PX | {member.display_name}"[:32], reason="Auto PX tag")
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
                f"• **Total Invites:** `{total_invites}`\n"
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


# --- 8. Interactive Mines Game View ---
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
                    content=f"💥 **BOOM!** {self.user.mention}, aapne bomb nikaal liya! Aap **{self.bet:,}** OwO Coins haar gaye. (Balance: **{disp_bal}**)",
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
                        content=f"👑 **CLEARED THE FIELD!** {self.user.mention} ne sabhi 6 💎 dhoondh liye aur **{winnings:,}** OwO Coins jeet liye! (Balance: **{disp_bal}**)",
                        view=self
                    )
                    self.stop()
                else:
                    await interaction.response.edit_message(
                        content=f"💎 Safe! Current Value: **{profit:,}** Coins ({self.multipliers[self.revealed_gems - 1]}x) | 3 💣 bache hain!",
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
            content=f"💰 **CASHOUT SUCCESSFUL!** {self.user.mention} ne **{profit:,}** OwO Coins secure kar liye! (Balance: **{disp_bal}**)",
            view=self
        )
        self.stop()


# --- 9. Ready Event (Auto-Post Panel + Instant Guild Slash Sync) ---
@bot.event
async def on_ready():
    print(f"\n==========================================", flush=True)
    print(f"[ONLINE] Logged in as: {bot.user.name} ({bot.user.id})", flush=True)
    print(f"[SECURE] Authorized ONLY for Guild ID: {MY_SERVER_ID}", flush=True)
    print(f"==========================================\n", flush=True)

    # Force Guild Slash Commands Sync to appear instantly on UI
    try:
        guild_obj = discord.Object(id=MY_SERVER_ID)
        bot.tree.copy_global_to(guild=guild_obj)
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"[SLASH-SYNC] Successfully synced {len(synced)} slash commands directly to Guild!", flush=True)
    except Exception as e:
        print(f"[SLASH-SYNC ERROR]: {e}", flush=True)

    # Invite Cache
    for guild in list(bot.guilds):
        if guild.id != MY_SERVER_ID:
            await guild.leave()
        else:
            try:
                guild_invites = await guild.invites()
                invites_cache[guild.id] = {invite.code: invite.uses for invite in guild_invites}
            except Exception:
                pass

            # Auto Check & Post Ticket Panel
            try:
                t_channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
                if t_channel:
                    history = [msg async for msg in t_channel.history(limit=5)]
                    already_posted = any(msg.author.id == bot.user.id and len(msg.embeds) > 0 for msg in history)
                    if not already_posted:
                        embed = get_ticket_panel_embed(guild)
                        view = TicketSelectView()
                        await t_channel.send(embed=embed, view=view)
                        print(f"[AUTO-DEPLOY] Ticket panel posted in #{t_channel.name}!", flush=True)
            except Exception as e:
                print(f"[AUTO-DEPLOY ERROR]: {e}", flush=True)


# --- 10. SLASH COMMANDS ---

# Official Setup Slash Command
@bot.tree.command(name="pxticketsetup", description="Deploy the official ticket support panel")
async def pxticketsetup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ Sirf Administrator use kar sakte hain!", ephemeral=True)
        return

    channel = interaction.guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message(f"❌ Ticket Channel `{TICKET_PANEL_CHANNEL_ID}` nahi mila!", ephemeral=True)
        return

    embed = get_ticket_panel_embed(interaction.guild)
    view = TicketSelectView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Aesthetic ticket panel successfully sent to {channel.mention}!", ephemeral=True)


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
        await interaction.response.send_message(f"❌ Insufficient balance!", ephemeral=True)
        return

    view = MinesGameView(interaction.user, amount)
    await interaction.response.send_message(
        content=f"💣 **MINES GAME STARTED** | Bet: **{amount:,}** Coins\n3 Hidden Bombs (💣). 💎 dhoondhein aur Cashout karein!",
        view=view
    )

bot.tree.add_command(owo_group)


@bot.tree.command(name="setpx", description="Bulk PX tag apply")
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


# --- 11. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("[ERROR] DISCORD_TOKEN environment variable nahi mila!", flush=True)
    else:
        bot.run(token)
