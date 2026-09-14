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
    return "PX Security Bot is online and running 24/7!"

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

# Aapki User ID (Whitelist + Real-time DM Reports)
MY_USER_ID = 1525179499602509977
WHITELIST_USERS = [MY_USER_ID]

# Anti-Nuke Settings (5 second me 2 se zyada deletions par direct ban)
channel_deletions = {}
role_deletions = {}
THRESHOLD = 2          
WINDOW_SECONDS = 5

# Active giveaways tracker
active_giveaways = {}

async def take_anti_nuke_action(guild, executor, action_name):
    """Attacker chahe koi bhi role rakhta ho, direct ban karega (Whitelist chhodkar)"""
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


# --- 4. Real-Time Giveaway Participant Tracking (DM to You) ---
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

            # Direct DM to your ID
            my_user = await bot.fetch_user(MY_USER_ID)
            joined_user = guild.get_member(payload.user_id) or await bot.fetch_user(payload.user_id)
            await my_user.send(
                f"📥 **PX PANEL Giveaway Update**\n\n"
                f"• **Prize:** `{prize}`\n"
                f"• **New Entry:** `{joined_user.name}` (`{joined_user.id}`)\n"
                f"• **Total Entries:** `{total_count}`"
            )
        except Exception as e:
            print(f"Tracking reaction error: {e}")


# --- 5. Slash Commands ---

# 1. Professional Giveaway Command
@bot.tree.command(name="giveaway", description="PX PANEL official giveaway host karein")
@app_commands.describe(
    prize="Giveaway prize (e.g., 7 DAYS VAULT PANEL)",
    duration_minutes="Duration in minutes (e.g., 1440 for 24 hours)",
    winners="Number of winners (default: 1)"
)
async def giveaway(interaction: discord.Interaction, prize: str, duration_minutes: int, winners: int = 1):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Aapke paas giveaway create karne ki permission nahi hai!", ephemeral=True)
        return

    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
    unix_timestamp = int(end_time.timestamp())
    guild_icon = interaction.guild.icon.url if interaction.guild.icon else None

    # Sleek & Clean Modern Embed
    embed = discord.Embed(
        title=f"🎉  {prize.upper()}",
        description=(
            f"> An official event brought to you by **PX PANEL**.\n"
            f"> Sponsored & Hosted by **Persistx**.\n\n"
            f"**Details**\n"
            f"• **Prize:** `{prize}`\n"
            f"• **Winners:** `{winners}`\n"
            f"• **Ending:** <t:{unix_timestamp}:R> (<t:{unix_timestamp}:f>)\n\n"
            f"**How to Enter**\n"
            f"Click the 🎉 reaction below to participate!"
        ),
        color=0xFEE75C
    )
    embed.set_author(name="PX PANEL • EXCLUSIVE GIVEAWAY", icon_url=guild_icon)
    embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
    embed.timestamp = end_time

    # Send Clean Alert
    await interaction.response.send_message(
        content="@everyone @here",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=True)
    )
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")

    active_giveaways[msg.id] = {"prize": prize}

    # Wait duration
    await asyncio.sleep(duration_minutes * 60)

    try:
        updated_msg = await interaction.channel.fetch_message(msg.id)
    except discord.NotFound:
        active_giveaways.pop(msg.id, None)
        return

    reaction = discord.utils.get(updated_msg.reactions, emoji="🎉")
    users = [user async for user in reaction.users() if not user.bot]

    active_giveaways.pop(msg.id, None)

    # Concluded State Embed
    embed.title = f"🔒  {prize.upper()} (ENDED)"
    embed.description = (
        f"> The giveaway has officially concluded.\n"
        f"> Sponsored & Hosted by **Persistx**.\n\n"
        f"**Details**\n"
        f"• **Prize:** `{prize}`\n"
        f"• **Winners:** `{winners}`\n"
        f"• **Ended:** <t:{unix_timestamp}:R>"
    )
    embed.color = 0x2B2D31
    await updated_msg.edit(embed=embed)

    if not users:
        no_winner_embed = discord.Embed(
            description=f"⚠️ **Giveaway Ended:** No valid participants entered for **{prize}**.",
            color=0xED4245
        )
        await interaction.channel.send(embed=no_winner_embed)
        return

    actual_winners_count = min(len(users), winners)
    selected_winners = random.sample(users, actual_winners_count)
    winners_mention = ", ".join([w.mention for w in selected_winners])

    end_embed = discord.Embed(
        title="🎊  GIVEAWAY CONCLUDED",
        description=(
            f"Congratulations {winners_mention}!\n\n"
            f"You have won **{prize}** courtesy of **PX PANEL**!\n"
            f"Hosted by **Persistx**.\n\n"
            f"> *Please open a ticket or contact host to claim your reward.*"
        ),
        color=0x57F287
    )
    end_embed.set_author(name="PX PANEL • RESULTS", icon_url=guild_icon)
    end_embed.set_footer(text="PX PANEL Community • PX FAMILY 💖", icon_url=guild_icon)
    
    await interaction.channel.send(content=f"Congratulations {winners_mention}!", embed=end_embed)

    # Final Summary DM to Owner
    try:
        my_user = await bot.fetch_user(MY_USER_ID)
        participants_names = "\n".join([f"• {u.name} (`{u.id}`)" for u in users])
        if len(participants_names) > 1500:
            participants_names = participants_names[:1500] + "\n...and more"

        await my_user.send(
            f"📊 **Giveaway Completed: {prize}**\n\n"
            f"• **Host:** Persistx\n"
            f"• **Total Entries:** `{len(users)}`\n"
            f"• **Winners:** {winners_mention}\n\n"
            f"**Participants:**\n{participants_names}"
        )
    except Exception as e:
        print(f"Summary DM error: {e}")


# 2. Clear Chat Command
@bot.tree.command(name="clear", description="Chat messages purge karein")
@app_commands.describe(amount="Kitne messages delete karne hain")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("Aapke paas messages delete karne ki permission nahi hai!", ephemeral=True)
        return
    if amount < 1:
        await interaction.response.send_message("Kam se kam 1 message specify karein.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 `{len(deleted)}` messages delete kar diye gaye!", ephemeral=True)


# 3. Kick Command
@bot.tree.command(name="kick", description="User ko server se kick karein")
@app_commands.describe(member="User to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} has been kicked. Reason: `{reason}`")


# 4. Ban Command
@bot.tree.command(name="ban", description="User ko server se permanently ban karein")
@app_commands.describe(member="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member.mention} has been permanently banned. Reason: `{reason}`")


# 5. Timeout Command
@bot.tree.command(name="timeout", description="User ko timeout/mute karein")
@app_commands.describe(member="User to mute", minutes="Duration in minutes", reason="Reason")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Rule violation"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Permission denied!", ephemeral=True)
        return
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"⏳ {member.mention} has been timed out for `{minutes}` minutes.")


# 6. Ping Command
@bot.tree.command(name="ping", description="Bot latency check karein")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("PX PANEL Security & Giveaway System is Online!")


# --- 6. Execution Start ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable nahi mila!")
    else:
        bot.run(token)
