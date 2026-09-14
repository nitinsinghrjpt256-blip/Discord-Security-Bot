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
    # Render default port 8080 use karta hai
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()


# --- 2. Discord Bot Setup ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Anti-nuke tracking variables
channel_deletions = {}
role_deletions = {}
THRESHOLD = 3          # 10 second me 3 actions par trigger hoga
WINDOW_SECONDS = 10

async def take_anti_nuke_action(guild, executor, action_name):
    """Attacker ke roles hatana aur ban karna"""
    if executor.id == guild.owner_id or executor.id == bot.user.id:
        return

    try:
        # Dangerous roles hatana
        for role in executor.roles:
            if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_channels:
                await executor.remove_roles(role, reason=f"Anti-Nuke Triggered: Mass {action_name}")
        
        # User ko ban karna
        await executor.ban(reason=f"Anti-Nuke Triggered: Mass {action_name}")
        
        # Server owner ko DM bhejna
        owner = guild.owner
        if owner:
            await owner.send(f"🚨 **ANTI-NUKE ALERT**: `{executor.name}` ne mass {action_name} kiya tha. Unhe server se ban kar diya gaya hai.")
    except Exception as e:
        print(f"Action execute karne me error: {e}")


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
    print("Anti-Nuke system is active!")


# --- 5. Start Bot ---
if __name__ == "__main__":
    keep_alive()  # Web server background me start karega
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable nahi mila!")
    else:
        bot.run(token)
