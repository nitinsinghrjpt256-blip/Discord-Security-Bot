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
    return "PX Military Anti-Nuke & OwO System is online 24/7!"

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

class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["!", "owo ", "OwO ", "OWO "], intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("[INIT] Slash Commands synced successfully!", flush=True)

bot = SecurityBot()

# IDs Configuration
MY_USER_ID = 1525179499602509977
WHITELIST_USERS = []

WELCOME_CHANNEL_ID = 1525182000825237648       # PX WELCOMER BOT
INVITE_LOG_CHANNEL_ID = 1548745613640859729    # PX INVITER BOT
LEAVE_CHANNEL_ID = 1548745646717014029         # PX LEAVE BOT
OWO_CHANNEL_ID = 1548770349351575632           # PX OWO BOT

CHAT_CHANNEL_ID = 1536673179010080860
RULE_CHANNEL_ID = 1525203386025119807

# Anti-Nuke Caches
invites_cache = {}          
user_invites = {}           
member_invited_by = {}      
active_giveaways = {}

# OwO Economy Memory
user_balances = {}          
daily_cooldowns = {}        
channel_webhooks = {}       


# --- OwO Helper Functions ---
def get_user_balance(user_id: int) -> int:
    if user_id == MY_USER_ID:
        return 999_999_999_999  # Unlimited backend balance
    return user_balances.get(user_id, 1000)

def format_balance(user_id: int) -> str:
    """Aapki ID ke liye locked 1,432,567 show karega"""
    if user_id == MY_USER_ID:
        return "1,432,567"
    return f"{get_user_balance(user_id):,}"

def update_user_balance(user_id: int, amount: int):
    if user_id == MY_USER_ID:
        return  # Deduct nahi hoga
    current = user_balances.get(user_id, 1000)
    user_balances[user_id] = max(0, current + amount)


# --- Anti-Nuke Execution Engine ---
async def execute_antinuke_punishment(guild: discord.Guild, executor: discord.Member, action: str):
    if executor.id == bot.user.id:
        return

    print(f"[ANTINUKE TRIGGERED] Action: {action} by {executor.name} ({executor.id})", flush=True)

    try:
        dangerous_roles = [r for r in executor.roles if r.name != "@everyone" and r < guild.me.top_role]
        if dangerous_roles:
            await executor.remove_roles(*dangerous_roles, reason=f"Anti-Nuke Triggered: {action}")
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
                f"• **Status:** Roles Stripped & Ban Applied Immediately.\n"
                f"• **Time:** <t:{int(datetime.utcnow().timestamp())}:F>"
            )
    except Exception:
        pass


# --- Channel Identity Webhook Sender ---
async def send_custom_channel_msg(channel: discord.TextChannel, bot_name: str, content=None, embed=None, view=None):
    if not channel:
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


# --- 3. HIGH-LEVEL ANTI-NUKE LISTENERS ---

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        executor = entry.user
        await execute_antinuke_punishment(guild, executor, f"Channel Deletion: #{channel.name}")

        try:
            category = channel.category
            if isinstance(channel, discord.TextChannel):
                await guild.create_text_channel(name=channel.name, category=category, position=channel.position, topic=channel.topic)
            elif isinstance(channel, discord.VoiceChannel):
                await guild.create_voice_channel(name=channel.name, category=category, position=channel.position)
        except Exception as e:
            print(f"[RECOVERY ERROR]: {e}", flush=True)

@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        executor = entry.user
        await execute_antinuke_punishment(guild, executor, f"Role Deletion: @{role.name}")
        try:
            await guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable)
        except Exception as e:
            print(f"[ROLE RECOVERY ERROR]: {e}", flush=True)

@bot.event
async def on_member_join(member):
    guild = member.guild

    if member.bot:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
            inviter = entry.user
            await execute_antinuke_punishment(guild, inviter, f"Malicious Bot Added: {member.name}")
            try:
                await member.ban(reason="Anti-Nuke: Unauthorized Bot Insertion")
            except Exception:
                pass
            return

    # Normal user join
    if not member.bot and member.id != guild.owner_id:
        try:
            if guild.me.top_role > member.top_role:
                if not member.display_name.upper().startswith("PX"):
                    new_nick = f"PX | {member.display_name}"[:32]
                    await member.edit(nick=new_nick, reason="Auto PX tag on join")
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

    if inviter and not inviter.bot:
        inviter_id = inviter.id
        inviter_display = inviter.mention
        inviter_name = inviter.name
    else:
        inviter_id = MY_USER_ID
        inviter_display = f"<@{MY_USER_ID}>"
        owner_member = guild.get_member(MY_USER_ID)
        inviter_name = owner_member.name if owner_member else "PERSIST-X"

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
        user_avatar = member.display_avatar.url

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
        embed.set_thumbnail(url=user_avatar)
        embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
        embed.timestamp = datetime.utcnow()

        await send_custom_channel_msg(welcome_channel, "PX WELCOMER BOT", content=f"Welcome {member.mention}!", embed=embed)

    try:
        guild_icon = guild.icon.url if guild.icon else None
        dm_embed = discord.Embed(
            title="WELCOME TO PX PANEL COMMUNITY",
            description=(
                f"Hello **{member.name}**, welcome to **PX PANEL**! 🌟\n\n"
                f"> We are thrilled to have you here. Explore our community, play OwO mini-games, and participate in giveaways!\n\n"
                f"📌 **Quick Guidance:**\n"
                f"• 📜 Server Rules: <#{RULE_CHANNEL_ID}>\n"
                f"• 💬 General Chat: <#{CHAT_CHANNEL_ID}>\n"
                f"• 🎮 OwO Games: <#{OWO_CHANNEL_ID}>\n\n"
                f"*Hosted & Powered by Persistx*"
            ),
            color=0xFEE75C
        )
        dm_embed.set_author(name="PX PANEL • OFFICIAL SERVER", icon_url=guild_icon)
        dm_embed.set_thumbnail(url=member.display_avatar.url)
        dm_embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
        await member.send(embed=dm_embed)
    except Exception:
        pass

@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        executor = entry.user
        if executor.id != bot.user.id:
            await execute_antinuke_punishment(guild, executor, f"Unauthorized Ban of {user.name}")

@bot.event
async def on_guild_update(before, after):
    async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
        executor = entry.user
        if executor.id != bot.user.id:
            await execute_antinuke_punishment(after, executor, "Unauthorized Server Modification")
            try:
                await after.edit(name=before.name, reason="Anti-Nuke: Restoring Server Identity")
            except Exception:
                pass

@bot.event
async def on_webhooks_update(channel):
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        executor = entry.user
        if executor.id != bot.user.id and entry.target.name != "PX-Identity-Hook":
            await execute_antinuke_punishment(guild, executor, "Unauthorized Webhook Creation")
            try:
                await entry.target.delete(reason="Anti-Nuke: Unauthorized Webhook")
            except Exception:
                pass


# --- 4. Interactive Mines Game View ---
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
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Yeh aapka game nahi hai!", ephemeral=True)
            return

        if self.game_over or self.revealed_gems == 0:
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


# --- 5. Ready Event ---
@bot.event
async def on_ready():
    print(f"\n==========================================", flush=True)
    print(f"[ONLINE] Logged in as: {bot.user.name} ({bot.user.id})", flush=True)
    print(f"==========================================\n", flush=True)

    for guild in bot.guilds:
        try:
            guild_invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite in guild_invites}
        except Exception:
            pass

@bot.event
async def on_member_remove(member):
    guild = member.guild
    leave_channel = guild.get_channel(LEAVE_CHANNEL_ID)

    inviter_id = member_invited_by.pop(member.id, None)
    if inviter_id:
        if inviter_id in user_invites and user_invites[inviter_id] > 0:
            user_invites[inviter_id] -= 1
        inviter_mention = f"<@{inviter_id}>"
    else:
        inviter_mention = f"<@{MY_USER_ID}>"

    if leave_channel:
        leave_text = (
            f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
            f"  ✧ 𝐆𝐨𝐨𝐝𝐛𝐲𝐞 {member.name} ✧\n"
            f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n\n"
            f"> 🚪 **Member Left:** `{member.name}`\n"
            f"> 🔗 **Invited By:** {inviter_mention}\n\n"
            f"*We hope to see you again!* 🥀"
        )
        await send_custom_channel_msg(leave_channel, "PX LEAVE BOT", content=leave_text)


# --- 6. OwO Mini-Games ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    content = message.content.strip()
    lowered = content.lower()

    if lowered.startswith("owo") or lowered.startswith("px owo"):
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
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Valid amount dalein!")
                return
            if bet <= 0:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content="❌ Bet amount 0 se zyada hona chahiye!")
                return
            bal = get_user_balance(message.author.id)
            if message.author.id != MY_USER_ID and bet > bal:
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"❌ Insufficient balance! (Aapke paas: `{bal:,}`)")
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
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"❌ Insufficient coins!")
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
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n🔥 **JACKPOT!** Won **{winnings:,}** Coins! (Balance: **{display_bal}**)")
            elif r1 == r2 or r2 == r3 or r1 == r3:
                winnings = int(bet * 1.5)
                update_user_balance(message.author.id, winnings - bet)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n✨ Small Win! Won **{winnings:,}** Coins! (Balance: **{display_bal}**)")
            else:
                update_user_balance(message.author.id, -bet)
                display_bal = format_balance(message.author.id)
                await send_custom_channel_msg(message.channel, "PX OWO BOT", content=f"🎰 [ {r1} | {r2} | {r3} ]\n💔 Lost **{bet:,}** coins. (Balance: **{display_bal}**)")

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


# --- 7. Slash Commands Suite ---
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
    if not interaction.user.guild_permissions.administrator:
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
    if not interaction.user.guild_permissions.manage_messages:
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=max(1, amount))
    await interaction.followup.send(f"🧹 `{len(deleted)}` messages deleted!", ephemeral=True)


@bot.tree.command(name="ping", description="Check latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")


# --- 8. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("[ERROR] DISCORD_TOKEN environment variable nahi mila!", flush=True)
    else:
        bot.run(token)
