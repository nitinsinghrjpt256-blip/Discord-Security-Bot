import os
import random
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# --- 1. Web Server (Render & UptimeRobot ke liye) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "PX Security & Invite Bot is online 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()


# --- 2. Discord Bot Setup ---
intents = discord.Intents.all()

class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash Commands successfully sync ho gaye!")

bot = SecurityBot()

# IDs Configuration
MY_USER_ID = 1525179499602509977
WHITELIST_USERS = [MY_USER_ID]

WELCOME_CHANNEL_ID = 1525182000825237648
LEAVE_CHANNEL_ID = 1548745646717014029

CHAT_CHANNEL_ID = 1536673179010080860
RULE_CHANNEL_ID = 1525203386025119807

# Anti-Nuke Settings (5 sec me 2 se zyada deletion par direct ban)
channel_deletions = {}
role_deletions = {}
THRESHOLD = 2          
WINDOW_SECONDS = 5

# Invite Tracker Caches
invites_cache = {}          # guild_id: {code: uses}
user_invites = {}           # inviter_id: total_invites_count
member_invited_by = {}      # member_id: inviter_id
active_giveaways = {}


async def auto_apply_bot_permissions(guild: discord.Guild):
    """Server ke saare categories aur VCs me permissions auto update karega"""
    bot_member = guild.me
    if not bot_member:
        return

    overwrites = discord.PermissionOverwrite(
        view_channel=True,
        connect=True,
        speak=True,
        stream=True,
        mute_members=True,
        deafen_members=True,
        move_members=True,
        use_voice_activation=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_channels=True,
        manage_permissions=True
    )

    for channel in guild.channels:
        try:
            current_perms = channel.overwrites_for(bot_member)
            if not (current_perms.view_channel and current_perms.connect and current_perms.speak):
                await channel.set_permissions(bot_member, overwrite=overwrites, reason="Auto Sync Bot Channel Permissions")
        except Exception as e:
            print(f"Error setting perms in {channel.name}: {e}")


async def take_anti_nuke_action(guild, executor, action_name):
    """Attacker chahe koi bhi role rakhta ho, direct ban karega"""
    if executor.id == guild.owner_id or executor.id == bot.user.id or executor.id in WHITELIST_USERS:
        return

    try:
        await guild.ban(executor, reason=f"Anti-Nuke Triggered: Mass {action_name}", delete_message_days=0)
        owner = guild.owner
        if owner:
            await owner.send(
                f"🚨 **ANTI-NUKE ALERT**\n\n"
                f"• **Target User:** `{executor.name}` (ID: `{executor.id}`)\n"
                f"• **Trigger:** Mass {action_name} detected within 5 seconds.\n"
                f"• **Action Taken:** Permanently banned from the server."
            )
    except Exception as e:
        print(f"Anti-nuke ban error: {e}")


# --- 3. Anti-Nuke Listeners ---
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


# --- 4. Ready Event ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    
    for guild in bot.guilds:
        try:
            guild_invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite in guild_invites}
        except Exception as e:
            print(f"Failed to fetch invites for guild {guild.name}: {e}")

        asyncio.create_task(auto_apply_bot_permissions(guild))
            
    print("PX Security, Giveaway, Invites & Auto-Nick System is Online!")

@bot.event
async def on_invite_create(invite):
    if invite.guild.id not in invites_cache:
        invites_cache[invite.guild.id] = {}
    invites_cache[invite.guild.id][invite.code] = invite.uses

@bot.event
async def on_invite_delete(invite):
    if invite.guild.id in invites_cache and invite.code in invites_cache[invite.guild.id]:
        del invites_cache[invite.guild.id][invite.code]


# --- 5. Member Join Event (Auto PX Nickname + Welcome Embed + DM) ---
@bot.event
async def on_member_join(member):
    print(f"[JOIN EVENT] {member.name} ({member.id}) ne server join kiya!")
    guild = member.guild

    # 1. Auto Nickname: Agar naam me PX nahi hai to PX | add karein
    try:
        current_name = member.display_name
        if not current_name.upper().startswith("PX"):
            new_nick = f"PX | {current_name}"[:32]  # Discord limit 32 characters
            await member.edit(nick=new_nick, reason="Auto PX tag on join")
            print(f"[AUTO-NICK] {member.name} ka nick change karke {new_nick} kiya gaya.")
    except Exception as e:
        print(f"[AUTO-NICK ERROR] {member.name} ka nick change nahi ho paya: {e}")

    # 2. Invite Tracking
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
        print(f"[ERROR] Invites check failed: {e}")

    if inviter and not inviter.bot:
        inviter_id = inviter.id
        inviter_display = inviter.mention
    else:
        inviter_id = MY_USER_ID
        inviter_display = f"<@{MY_USER_ID}>"

    member_invited_by[member.id] = inviter_id
    user_invites[inviter_id] = user_invites.get(inviter_id, 0) + 1
    total_invites = user_invites[inviter_id]

    # 3. Welcome Channel Embed
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
        except Exception as e:
            print(f"[ERROR] Failed to send welcome embed: {e}")

    # 4. DM to Member
    try:
        dm_embed = discord.Embed(
            title="WELCOME TO PX PANEL COMMUNITY",
            description=(
                f"Hello **{member.name}**, welcome to **PX PANEL**! 🌟\n\n"
                f"> We are thrilled to have you here. Explore our server, participate in exclusive giveaways, and enjoy your time.\n\n"
                f"📌 **Quick Links:**\n"
                f"• 📜 Server Rules: <#{RULE_CHANNEL_ID}>\n"
                f"• 💬 Chit-Chat: <#{CHAT_CHANNEL_ID}>\n"
                f"• Need help? Reach out to our moderators or open a ticket.\n\n"
                f"*Powered & Sponsored by Persistx*"
            ),
            color=0xFEE75C
        )
        guild_icon = guild.icon.url if guild.icon else None
        dm_embed.set_author(name="PX PANEL • OFFICIAL SERVER", icon_url=guild_icon)
        dm_embed.set_thumbnail(url=member.display_avatar.url)
        dm_embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
        await member.send(embed=dm_embed)
    except Exception as e:
        print(f"[DM Skipped] Could not send DM: {e}")


# --- 6. Member Leave Event ---
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
        leave_msg = (
            f"╭─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╮\n"
            f"  ✧ 𝐆𝐨𝐨𝐝𝐛𝐲𝐞 {member.name} ✧\n"
            f"╰─── ･ ｡ﾟ☆: *.☽ .* :☆ﾟ. ───╯\n\n"
            f"> 🚪 **Member Left:** `{member.name}`\n"
            f"> 🔗 **Invited By:** {inviter_mention}\n\n"
            f"*We hope to see you again!* 🥀"
        )
        try:
            await leave_channel.send(leave_msg)
        except Exception as e:
            print(f"Error sending leave message: {e}")


# --- 7. Giveaway Reaction Tracking ---
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
            print(f"Reaction tracking error: {e}")


# --- 8. Slash Commands ---

# 1. Sabhi Members ke Name ke aage PX lagane wala Command
@bot.tree.command(name="setpx", description="Server ke sabhi members jinke naam ke aage PX nahi hai, PX tag lagayein")
async def setpx(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Yeh command sirf Administrator use kar sakte hain!", ephemeral=True)
        return

    await interaction.response.defer()
    guild = interaction.guild
    changed_count = 0
    skipped_count = 0

    status_msg = await interaction.followup.send("🔄 **Processing:** Members ke nicknames scan ho rahe hain, kripya wait karein...")

    for member in guild.members:
        if member.bot:
            continue
        
        # Server owner ka nick bot change nahi kar sakta
        if member.id == guild.owner_id:
            skipped_count += 1
            continue

        # Check agar bot ka role member se bada hai ya nahi
        if guild.me.top_role <= member.top_role:
            skipped_count += 1
            continue

        current_name = member.display_name
        # Agar pehle se PX ya px nahi laga
        if not current_name.upper().startswith("PX"):
            new_nick = f"PX | {current_name}"[:32]
            try:
                await member.edit(nick=new_nick, reason="Bulk PX tag applied by Admin")
                changed_count += 1
                await asyncio.sleep(0.5)  # Discord rate limit prevention
            except Exception:
                skipped_count += 1

    await status_msg.edit(
        content=(
            f"✅ **Task Completed!**\n\n"
            f"• **Updated Members:** `{changed_count}` logo ke aage `PX | ` lag chuka hai.\n"
            f"• **Skipped/Already had PX:** `{skipped_count}` members (Owner/Higher Roles/Already PX)."
        )
    )


# 2. Sync Permissions
@bot.tree.command(name="syncperms", description="Server ke sabhi VC aur Categories me bot permissions sync karein")
async def syncperms(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Sirf Administrator use kar sakte hain!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    await auto_apply_bot_permissions(interaction.guild)
    await interaction.followup.send("✅ **Done!** Permissions successfully sync ho gaye.", ephemeral=True)


# 3. Giveaway Command
@bot.tree.command(name="giveaway", description="Start a new giveaway")
@app_commands.describe(
    prize="Giveaway prize (e.g., 1 MONTH NITRO ID)",
    duration_minutes="Giveaway duration in minutes",
    winners="Number of winners (default: 1)"
)
async def giveaway(interaction: discord.Interaction, prize: str, duration_minutes: int, winners: int = 1):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Aapke paas permission nahi hai!", ephemeral=True)
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

    try:
        my_user = await bot.fetch_user(MY_USER_ID)
        participants_names = "\n".join([f"• {u.name} (`{u.id}`)" for u in users])
        if len(participants_names) > 1500:
            participants_names = participants_names[:1500] + "\n...and more"

        await my_user.send(
            f"📊 **Giveaway Summary: {prize}**\n\n"
            f"• **Total Entries:** `{len(users)}`\n"
            f"• **Winner(s):** {winners_mention}\n\n"
            f"**Participants:**\n{participants_names}"
        )
    except Exception as e:
        print(f"Summary DM error: {e}")


# 4. Check Invites
@bot.tree.command(name="invites", description="Apne ya kisi member ke total invites check karein")
@app_commands.describe(member="Member jiske invites dekhne hain (optional)")
async def invites(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    count = user_invites.get(target.id, 0)
    await interaction.response.send_message(f"📊 {target.mention} ke paas abhi total **{count}** active invites hain.")


# 5. Clear Chat Command
@bot.tree.command(name="clear", description="Chat messages delete karein")
@app_commands.describe(amount="Kitne messages delete karne hain")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    if amount < 1:
        await interaction.response.send_message("Kam se kam 1 message select karein.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 `{len(deleted)}` messages delete kar diye gaye!", ephemeral=True)


# 6. Kick Command
@bot.tree.command(name="kick", description="User ko kick karein")
@app_commands.describe(member="Member jise kick karna hai", reason="Reason")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Koi reason nahi diya gaya"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} ko kick kar diya gaya. Reason: `{reason}`")


# 7. Ban Command
@bot.tree.command(name="ban", description="User ko permanently ban karein")
@app_commands.describe(member="Member jise ban karna hai", reason="Reason")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Koi reason nahi diya gaya"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member.mention} ko ban kar diya gaya. Reason: `{reason}`")


# 8. Timeout Command
@bot.tree.command(name="timeout", description="User ko timeout/mute karein")
@app_commands.describe(member="Member", minutes="Minutes", reason="Reason")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Rule violation"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"⏳ {member.mention} ko `{minutes}` minute ke liye timeout kar diya gaya.")


# 9. Ping Command
@bot.tree.command(name="ping", description="Bot latency check karein")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")


# --- 9. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable nahi mila!")
    else:
        bot.run(token)
