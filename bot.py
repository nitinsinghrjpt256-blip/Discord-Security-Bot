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
    return "PX Security & Invite Bot is online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web, daemon=True)
    t.start()


# --- 2. Discord Bot Setup & Intents ---
intents = discord.Intents.default()
intents.members = True          # Join/Leave tracking ke liye mandatory
intents.message_content = True  
intents.guilds = True           
intents.invites = True          # Invite Cache Tracking
intents.reactions = True        

class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("[INIT] Slash Commands synced successfully!", flush=True)

bot = SecurityBot()

# IDs Configuration
MY_USER_ID = 1525179499602509977
WHITELIST_USERS = [MY_USER_ID]

# Teeno Channels
WELCOME_CHANNEL_ID = 1525182000825237648       # Professional Welcome with Avatar & Links
INVITE_LOG_CHANNEL_ID = 1548745613640859729    # Invite Tracker Log
LEAVE_CHANNEL_ID = 1548745646717014029         # Leave Notification

CHAT_CHANNEL_ID = 1536673179010080860
RULE_CHANNEL_ID = 1525203386025119807

# Anti-Nuke Settings
channel_deletions = {}
role_deletions = {}
THRESHOLD = 2          
WINDOW_SECONDS = 5

# Invite Tracker Caches
invites_cache = {}          # guild_id: {code: uses}
user_invites = {}           # inviter_id: total_invites_count
member_invited_by = {}      # member_id: inviter_id
active_giveaways = {}


async def take_anti_nuke_action(guild, executor, action_name):
    """Attacker ko ban karega (Whitelist chhodkar)"""
    if executor.id == guild.owner_id or executor.id == bot.user.id or executor.id in WHITELIST_USERS:
        return

    try:
        await guild.ban(executor, reason=f"Anti-Nuke Triggered: Mass {action_name}", delete_message_days=0)
        owner = guild.owner
        if owner:
            await owner.send(
                f"🚨 **ANTI-NUKE ALERT**\n\n"
                f"• **User:** `{executor.name}` (ID: `{executor.id}`)\n"
                f"• **Action:** Mass {action_name} detect hone par ban kiya gaya."
            )
    except Exception as e:
        print(f"[ANTI-NUKE ERROR] {e}", flush=True)


# --- 3. Ready Event & Pre-Caching Invites ---
@bot.event
async def on_ready():
    print(f"\n==========================================", flush=True)
    print(f"[ONLINE] Logged in as: {bot.user.name} ({bot.user.id})", flush=True)
    print(f"==========================================\n", flush=True)

    for guild in bot.guilds:
        try:
            guild_invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite in guild_invites}
            print(f"[CACHE] Cached {len(guild_invites)} invites for '{guild.name}'", flush=True)
        except Exception as e:
            print(f"[CACHE ERROR] Guild {guild.name}: {e}", flush=True)


@bot.event
async def on_invite_create(invite):
    if invite.guild.id not in invites_cache:
        invites_cache[invite.guild.id] = {}
    invites_cache[invite.guild.id][invite.code] = invite.uses

@bot.event
async def on_invite_delete(invite):
    if invite.guild.id in invites_cache and invite.code in invites_cache[invite.guild.id]:
        del invites_cache[invite.guild.id][invite.code]


# --- 4. Member Join Event (Welcome Channel + Invite Tracker Channel + Auto-Nick + DM) ---
@bot.event
async def on_member_join(member):
    print(f"\n[JOIN EVENT] Member Joined: {member.name} ({member.id})", flush=True)
    guild = member.guild

    # 1. Automatic Nickname Tag (PX | Name)
    if not member.bot and member.id != guild.owner_id:
        try:
            if guild.me.top_role > member.top_role:
                if not member.display_name.upper().startswith("PX"):
                    new_nick = f"PX | {member.display_name}"[:32]
                    await member.edit(nick=new_nick, reason="Auto PX tag on join")
                    print(f"[AUTO-NICK] Nick changed to {new_nick}", flush=True)
        except Exception as e:
            print(f"[AUTO-NICK ERROR] {e}", flush=True)

    # 2. Invite Tracking Calculation
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
    except Exception as e:
        print(f"[INVITE ERROR] {e}", flush=True)

    # Fallback to PERSIST-X agar unknown ya direct ho
    if inviter and not inviter.bot:
        inviter_id = inviter.id
        inviter_display = inviter.mention
        inviter_name = inviter.name
    else:
        inviter_id = MY_USER_ID
        inviter_display = f"<@{MY_USER_ID}>"
        owner_member = guild.get_member(MY_USER_ID)
        inviter_name = owner_member.name if owner_member else "PERSIST-X"

    # Save tracking and increment invites
    member_invited_by[member.id] = inviter_id
    user_invites[inviter_id] = user_invites.get(inviter_id, 0) + 1
    total_invites = user_invites[inviter_id]

    # ----------------------------------------------------
    # A. INVITE TRACKER CHANNEL (1548745613640859729)
    # ----------------------------------------------------
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
        try:
            await invite_channel.send(invite_log_text)
            print(f"[SUCCESS] Sent invite log to #{invite_channel.name}", flush=True)
        except Exception as e:
            print(f"[INVITE LOG SEND ERROR] {e}", flush=True)

    # ----------------------------------------------------
    # B. WELCOME CHANNEL (1525182000825237648) with Avatar & Links
    # ----------------------------------------------------
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

        try:
            await welcome_channel.send(content=f"Welcome {member.mention}!", embed=embed)
            print(f"[SUCCESS] Sent welcome card to #{welcome_channel.name}", flush=True)
        except Exception as e:
            print(f"[WELCOME SEND ERROR] {e}", flush=True)

    # ----------------------------------------------------
    # C. MEMBER PERSONAL DIRECT MESSAGE (DM)
    # ----------------------------------------------------
    try:
        guild_icon = guild.icon.url if guild.icon else None
        dm_embed = discord.Embed(
            title="WELCOME TO PX PANEL COMMUNITY",
            description=(
                f"Hello **{member.name}**, welcome to **PX PANEL**! 🌟\n\n"
                f"> We are thrilled to have you here. Explore our community, participate in exclusive events & giveaways, and enjoy your time.\n\n"
                f"📌 **Quick Guidance:**\n"
                f"• 📜 Server Rules: <#{RULE_CHANNEL_ID}>\n"
                f"• 💬 General Chat: <#{CHAT_CHANNEL_ID}>\n"
                f"• Need help? Create a ticket or reach out to staff.\n\n"
                f"*Hosted & Powered by Persistx*"
            ),
            color=0xFEE75C
        )
        dm_embed.set_author(name="PX PANEL • OFFICIAL SERVER", icon_url=guild_icon)
        dm_embed.set_thumbnail(url=member.display_avatar.url)
        dm_embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
        await member.send(embed=dm_embed)
    except Exception as e:
        print(f"[DM SKIP] User ka DM band tha: {e}", flush=True)


# --- 5. Member Leave Event (1548745646717014029) ---
@bot.event
async def on_member_remove(member):
    print(f"\n[LEAVE EVENT] Member Left: {member.name} ({member.id})", flush=True)
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
        try:
            await leave_channel.send(leave_text)
            print(f"[SUCCESS] Sent leave message to #{leave_channel.name}", flush=True)
        except Exception as e:
            print(f"[LEAVE SEND ERROR] {e}", flush=True)


# --- 6. Anti-Nuke Event Listeners ---
@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        executor = entry.user
        now = datetime.utcnow()
        actions = channel_deletions.get(executor.id, [])
        actions = [t for t in actions if now - t < timedelta(seconds=WINDOW_SECONDS)]
        actions.append(now)
        channel_deletions[executor.id] = actions

        if len(actions) >= THRESHOLD:
            await take_anti_nuke_action(guild, executor, "Channel Deletions")

@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        executor = entry.user
        now = datetime.utcnow()
        actions = role_deletions.get(executor.id, [])
        actions = [t for t in actions if now - t < timedelta(seconds=WINDOW_SECONDS)]
        actions.append(now)
        role_deletions[executor.id] = actions

        if len(actions) >= THRESHOLD:
            await take_anti_nuke_action(guild, executor, "Role Deletions")


# --- 7. Giveaway Reaction Tracking (Live DM to Owner) ---
@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id in active_giveaways and str(payload.emoji) == "🎉":
        if payload.user_id == bot.user.id:
            return

        giveaway_data = active_giveaways[payload.message_id]
        prize = giveaway_data["prize"]
        guild = bot.get_guild(payload.guild_id)
        channel = bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            msg = await channel.fetch_message(payload.message_id)
            reaction = discord.utils.get(msg.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot]
            total_count = len(users)

            my_user = await bot.fetch_user(MY_USER_ID)
            joined_user = guild.get_member(payload.user_id) or await bot.fetch_user(payload.user_id)
            await my_user.send(
                f"📥 **PX PANEL Giveaway Update**\n"
                f"• Prize: `{prize}`\n"
                f"• Participant: `{joined_user.name}` (`{joined_user.id}`)\n"
                f"• Total Entries: `{total_count}`"
            )
        except Exception as e:
            print(f"[REACTION ERROR] {e}", flush=True)


# --- 8. Slash Commands ---

# 1. Bulk Set PX Tag
@bot.tree.command(name="setpx", description="Server ke sabhi members ke name ke aage PX tag lagayein")
async def setpx(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Sirf Administrator use kar sakte hain!", ephemeral=True)
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

    await interaction.followup.send(f"✅ Completed! `{changed}` members ke naam ke aage `PX | ` lag chuka hai.")


# 2. Giveaway Command (Zynrax Style)
@bot.tree.command(name="giveaway", description="Start a new giveaway")
@app_commands.describe(prize="Prize", duration_minutes="Duration in minutes", winners="Number of winners")
async def giveaway(interaction: discord.Interaction, prize: str, duration_minutes: int, winners: int = 1):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return

    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
    unix_timestamp = int(end_time.timestamp())

    embed = discord.Embed(
        title=f"🎁  {prize.upper()}  🎁",
        description=(
            f"• **Winners:** {winners}\n"
            f"• **Ends** <t:{unix_timestamp}:R> ( <t:{unix_timestamp}:f> )\n"
            f"• **Hosted by** {interaction.user.mention}\n\n"
            f"• **React with 🎉 to participate!**"
        ),
        color=0xFEE75C
    )
    embed.set_footer(text="PX PANEL • PX FAMILY 💖 • Ends at")
    embed.timestamp = end_time

    await interaction.response.send_message(
        content="@everyone @here 🎉 **New Giveaway** 🎉",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=True)
    )
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")

    active_giveaways[msg.id] = {"prize": prize}
    await asyncio.sleep(duration_minutes * 60)

    try:
        updated_msg = await interaction.channel.fetch_message(msg.id)
    except discord.NotFound:
        active_giveaways.pop(msg.id, None)
        return

    reaction = discord.utils.get(updated_msg.reactions, emoji="🎉")
    users = [user async for user in reaction.users() if not user.bot]
    active_giveaways.pop(msg.id, None)

    embed.title = f"🎁  {prize.upper()} (ENDED)  🎁"
    embed.description = (
        f"• **Winners:** {winners}\n"
        f"• **Ended** <t:{unix_timestamp}:R>\n"
        f"• **Hosted by** {interaction.user.mention}"
    )
    embed.color = 0x2B2D31
    await updated_msg.edit(embed=embed)

    if not users:
        await interaction.channel.send(f"⚠️ Giveaway ended for **{prize}**! Koi valid entry nahi aayi.")
        return

    actual_winners_count = min(len(users), winners)
    selected_winners = random.sample(users, actual_winners_count)
    winners_mention = ", ".join([w.mention for w in selected_winners])

    end_embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=(
            f"**Prize:** {prize}\n"
            f"**Winner(s):** {winners_mention}\n"
            f"**Hosted by:** {interaction.user.mention} *(by Persistx)*"
        ),
        color=0x57F287
    )
    end_embed.set_footer(text="PX PANEL • PX FAMILY 💖")
    await interaction.channel.send(content=f"Badhai ho {winners_mention}! Aapne **{prize}** jeet liya hai! 🥳", embed=end_embed)


# 3. Check Invites Command
@bot.tree.command(name="invites", description="Check total invites")
async def invites(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    count = user_invites.get(target.id, 0)
    await interaction.response.send_message(f"📊 {target.mention} ke paas abhi total **{count}** active invites hain.")


# 4. Clear Chat Command
@bot.tree.command(name="clear", description="Clear chat messages")
@app_commands.describe(amount="Messages count")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=max(1, amount))
    await interaction.followup.send(f"🧹 `{len(deleted)}` messages deleted!", ephemeral=True)


# 5. Ping Command
@bot.tree.command(name="ping", description="Check latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")


# --- 9. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("[ERROR] DISCORD_TOKEN environment variable nahi mila!", flush=True)
    else:
        bot.run(token)
