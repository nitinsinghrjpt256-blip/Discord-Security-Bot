import os
import threading
from datetime import datetime, timedelta
from flask import Flask
import discord
from discord.ext import commands

# --- 1. Web Server (Render & UptimeRobot ke liye) ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is online and running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()


# --- 2. Discord Bot Setup ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Whitelist User IDs jinhe bot kabhi ban nahi karega
WHITELIST_USERS = [1525179499602509977]

# Anti-nuke settings: 5 second me 2 se zyada actions par trigger hoga
channel_deletions = {}
role_deletions = {}
THRESHOLD = 2          
WINDOW_SECONDS = 5

async def take_anti_nuke_action(guild, executor, action_name):
    """Attacker ke paas chahe koi bhi role ho, direct ban karega (Whitelist chhodkar)"""
    # Whitelist check: Owner, Bot khud, ya specific User ID
    if executor.id == guild.owner_id or executor.id == bot.user.id or executor.id in WHITELIST_USERS:
        return

    try:
        # Direct Ban attacker
        await guild.ban(executor, reason=f"Anti-Nuke Triggered: Mass {action_name}", delete_message_days=0)
        
        # Server owner ko DM alert bhejna
        owner = guild.owner
        if owner:
            await owner.send(
                f"🚨 **ANTI-NUKE ALERT**\n"
                f"User: `{executor.name}` (ID: `{executor.id}`)\n"
                f"Reason: Mass {action_name} detect hua (5 sec limit cross).\n"
                f"Action: Server se **Permanently Ban** kar diya gaya hai."
            )
    except Exception as e:
        print(f"Attacker ko ban karne me error: {e}")


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


# --- 4. Chat & Moderation Commands ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """Chat messages clear karne ke liye: !clear 10"""
    if amount < 1:
        await ctx.send("Kripya 1 se bada number daalein.", delete_after=4)
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 `{len(deleted) - 1}` messages delete kar diye gaye!", delete_after=4)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Koi reason nahi diya gaya"):
    """User kick karne ke liye: !kick @user reason"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} ko kick kar diya gaya. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Koi reason nahi diya gaya"):
    """User ban karne ke liye: !ban @user reason"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} ko ban kar diya gaya. Reason: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="Rule violation"):
    """User ko timeout/mute karne ke liye: !timeout @user 10 reason"""
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"⏳ {member.mention} ko {minutes} minute ke liye timeout par daal diya gaya.")

@bot.command()
async def ping(ctx):
    """Latency check: !ping"""
    await ctx.send(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Anti-Nuke security system is online!")


# --- 5. Start Bot ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable nahi mila!")
    else:
        bot.run(token)
