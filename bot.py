# 1. Giveaway Command with Live Countdown Timer
@bot.tree.command(name="giveaway", description="Naya giveaway start karein")
@app_commands.describe(
    prize="Giveaway ka prize (e.g., 1 MONTH NITRO ID)",
    duration_minutes="Giveaway kitne minute chalega",
    winners="Kitne winners select karne hain (default: 1)"
)
async def giveaway(interaction: discord.Interaction, prize: str, duration_minutes: int, winners: int = 1):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Aapke paas giveaway host karne ki permission nahi hai!", ephemeral=True)
        return

    # Calculate end time and timestamp
    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
    unix_timestamp = int(end_time.timestamp())

    # Live Timer Embed (Discord is timer ko har second live count down karega)
    embed = discord.Embed(
        title=f"🎁 {prize.upper()} 🎁",
        description=(
            f"• **Winners:** {winners}\n"
            f"• **Ends:** <t:{unix_timestamp}:R> (<t:{unix_timestamp}:f>)\n"
            f"• **Hosted by:** {interaction.user.mention}\n\n"
            f"• **React with 🎉 to participate!**\n\n"
            f"⏳ **Time Remaining:** <t:{unix_timestamp}:R>"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Ends at")
    embed.timestamp = end_time

    await interaction.response.send_message("🎉 **New Giveaway** 🎉", embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")

    # Wait until giveaway ends
    await asyncio.sleep(duration_minutes * 60)

    # Fetch updated reactions
    try:
        updated_msg = await interaction.channel.fetch_message(msg.id)
    except discord.NotFound:
        return

    reaction = discord.utils.get(updated_msg.reactions, emoji="🎉")
    users = [user async for user in reaction.users() if not user.bot]

    # Original embed ko update karke "Giveaway Ended" mark karein
    embed.title = f"🎁 {prize.upper()} (ENDED) 🎁"
    embed.description = (
        f"• **Winners:** {winners}\n"
        f"• **Ended:** <t:{unix_timestamp}:R>\n"
        f"• **Hosted by:** {interaction.user.mention}"
    )
    embed.color = discord.Color.dark_gray()
    await updated_msg.edit(embed=embed)

    if not users:
        await interaction.channel.send(f"Giveaway ended for **{prize}**! Koi valid participant nahi mila.")
        return

    # Random winner selection
    actual_winners_count = min(len(users), winners)
    selected_winners = random.sample(users, actual_winners_count)
    winners_mention = ", ".join([w.mention for w in selected_winners])

    end_embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=(
            f"**Prize:** {prize}\n"
            f"**Winner(s):** {winners_mention}\n"
            f"**Hosted by:** {interaction.user.mention}"
        ),
        color=discord.Color.green()
    )
    await interaction.channel.send(content=f"Badhai ho {winners_mention}! Aapne **{prize}** jeet liya hai! 🥳", embed=end_embed)
