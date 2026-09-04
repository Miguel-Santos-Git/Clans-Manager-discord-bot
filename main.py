# Librarys
import discord
from discord.ext import commands
import sqlite3
import json
from views.invites import invites_ as invites_view
# Vars
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents = intents)

connection = sqlite3.connect("bank.db")

with open("configs.json","r") as file:
    token = json.load(file)["token"]

# Logic
cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users_table (
id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
user_id INTEGER NOT NULL UNIQUE,
clan_id INTEGER,
clan_position TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS clans_table (
id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
clan_name TEXT NOT NULL, 
owner_id INTEGER NOT NULL
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS invites_table (
clan_id INTEGER NOT NULL, 
user_id INTEGER NOT NULL,
PRIMARY KEY (clan_id, user_id)
)""")

connection.commit()

def get_infos_by_user_id(user_id):
    cursor.execute("SELECT * FROM users_table WHERE user_id = ?",(user_id,) )
    return cursor.fetchone()

def in_clan(user_id):
    infos = get_infos_by_user_id(user_id)
    if infos is None:
        return False

    _,_,clan_id, _ = infos
    return not clan_id is None

def clan_exist_by_name(name: str):
    infos = cursor.execute("SELECT * FROM clans_table WHERE clan_name = ?",(name,))
    return infos is None

def get_clan_id_by_name(name):
    cursor.execute("SELECT * FROM clans_table WHERE clan_name = ?",(name,))
    infos = cursor.fetchone()
    return infos[0]

def get_clan_by_id(clan_id):
    cursor.execute("SELECT * FROM clans_table WHERE id = ?",(clan_id,))
    return cursor.fetchone()

def has_invited(clan_id, member_id):
    cursor.execute("SELECT * FROM invites_table WHERE clan_id = ? AND user_id = ?",(clan_id,member_id))
    return cursor.fetchone() is not None

def get_clan_members(clan_id):
    cursor.execute("SELECT * FROM users_table WHERE clan_id = ?",(clan_id,))
    return cursor.fetchall()

@bot.event
async def on_ready():
    sings = await bot.tree.sync()
    print(f"{len(sings)} comands sync.")
    print("Bot start with sucess.")

@bot.tree.command(description = "Create a new clan.")
async def create_clan(interaction: discord.Interaction, clan_name: str):
    user_id = interaction.user.id

    user_in_clan = in_clan(user_id)
    if user_in_clan:
        return await interaction.response.send_message("You already are in a clan.") 

    clan_exist = clan_exist_by_name(clan_name)
    if clan_exist:
        return await interaction.response.send_message("This clan already exists, please try with new name.")

    cursor.execute("INSERT INTO clans_table (clan_name, owner_id) VALUES (?, ?)",(clan_name,user_id))
    clan_id = get_clan_id_by_name(clan_name)

    infos = get_infos_by_user_id(user_id)
    if infos:
        cursor.execute("UPDATE users_table SET clan_id = ?, clan_position = ? WHERE user_id = ?",(clan_id,"OWNER",user_id))
    else:
        cursor.execute("INSERT INTO users_table (user_id, clan_id, clan_position) VALUES (?,?,?)",(user_id,clan_id,"OWNER"))

    connection.commit()

    await interaction.response.send_message(f"""Your clan is create with sucess:
Clan name: {clan_name}
Clan id: {clan_id}
OWNER name: {interaction.user.name}
OWNER id: {user_id}
    """)

@bot.tree.command(description = "Delete your clan.")
async def del_clan(interaction: discord.Interaction):
    infos = get_infos_by_user_id(interaction.user.id)
    _, _, clan_id, clan_pos = infos

    if clan_pos != "OWNER":
        return await interaction.response.send_message("You are't owner of this clan.", ephemeral = True)
    
    cursor.execute("DELETE FROM clans_table WHERE id = ?",(clan_id,))
    cursor.execute("SELECT * FROM users_table WHERE clan_id = ?",(clan_id,))
    
    members = cursor.fetchall()
    for _, user_id, clan_id, clan_pos in members:
        cursor.execute("UPDATE users_table SET clan_id = ?, clan_position = ? WHERE user_id = ?",(None,None,user_id))
        connection.commit()

    connection.commit()
    await interaction.response.send_message("Your clan as deleted with sucess.")

@bot.tree.command(description="Send a invitation to user.")
async def send_invite(interaction: discord.Interaction, member:discord.Member):
    infos = get_infos_by_user_id(interaction.user.id)
    _, _, clan_id, clan_pos = infos

    if clan_pos != "OWNER" and clan_pos != "SUBOWNER":
        return await interaction.response.send_message("You are't owner/subowner of this clan.", ephemeral = True)

    if in_clan(member.id):
        return await interaction.response.send_message("This member already in a clan.")

    if has_invited(clan_id, member.id):
        return await interaction.response.send_message("This invitation has already been sent.")

    cursor.execute("INSERT INTO invites_table (clan_id, user_id) VALUES (?,?)",(clan_id, member.id))
    connection.commit()
    await interaction.response.send_message("Your invite has send with sucess")

@bot.tree.command(description= "Get your clan situation.")
async def situation(interaction: discord.Interaction):
    user_infos = get_infos_by_user_id(interaction.user.id)
    _, user_id, clan_id, _ = user_infos
    if clan_id is None:
        return await interaction.response.send_message("You aren't in a clan.")

    clan_members = get_clan_members(clan_id)
    text = ""
    for _, member_id, _, position in clan_members:
        name = await bot.fetch_user(member_id)
        text += f"{name}: {position} \n"

    await interaction.response.send_message(text)    

@bot.tree.command(description="List your clans invites.")
async def list_invites(interaction: discord.Interaction):
    cursor.execute("SELECT * FROM invites_table WHERE user_id = ?",(interaction.user.id,))
    invites = cursor.fetchall()
    if not invites:
        return await interaction.response.send_message("You don't have a invitations.", ephemeral = True)

    view = invites_view(interaction.user, invites)
    text = "Join in clan:  \n"

    for invite in invites:
        clan_id = invite[0]
        clan_infos = get_clan_by_id(clan_id)
        text += f"{clan_infos[1]} \n"

    await interaction.response.send_message(text, view=view)

@bot.tree.command(description = "Promote a user to subowner.")
async def promote(interaction: discord.Interaction, member:discord.Member):
    user_infos = get_infos_by_user_id(interaction.user.id)
    _, user_id, user_clan_id, user_clan_pos = user_infos
    if not user_clan_pos == "OWNER" and user_clan_pos == "SUBOWNER":
        return await interaction.response.send_message("You aren't owner/subowner of your clan.", ephemeral = True)

    member_infos = get_infos_by_user_id(member.id)
    if not member_infos:
        return await interaction.response.send_message("This user aren't a member of your clan.")
    _, member_id, member_clan_id, _ = member_infos
    if member_clan_id != user_clan_id:
        return await interaction.response.send_message("This user aren't a member of your clan.")

    cursor.execute("UPDATE users_table SET clan_position = ? WHERE user_id = ?",("SUBOWNER",member_id))
    await interaction.response.send_message(f"The user {member.name} has promoted with sucess.")

@bot.tree.command(description="Remove a member of your clan.")
async def remove_member(interaction: discord.Interaction, member:discord.Member):
    user_infos = get_infos_by_user_id(interaction.user.id)
    _, user_id, user_clan_id, user_clan_pos = user_infos
    if not (user_clan_pos == "OWNER" or user_clan_pos == "SUBOWNER"):
        return await interaction.response.send_message("You aren't owner/subowner of your clan.", ephemeral = True)
    
    member_infos = get_infos_by_user_id(member.id)
    if not member_infos:
        return await interaction.response.send_message("This user aren't a member of your clan.")
    _, member_id, member_clan_id, member_pos = member_infos
    if member_clan_id != user_clan_id:
        return await interaction.response.send_message("This user aren't a member of your clan.")

    if member_pos == "OWNER":
        return await interaction.response.send_message("This is a owner of clan.")

    if user_clan_pos == "SUBOWNER" and member_pos == "SUBOWNER":
        return await interaction.response.send_message("You can't remove other subowner.")
    
    cursor.execute("UPDATE users_table SET clan_position = ?, clan_id WHERE user_id = ?",(None,None,member_id))
    await interaction.response.send_message(f"The user {member.name} has removed from your clan with sucess.")

bot.run(token)