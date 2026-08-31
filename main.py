# Librarys
import discord
from discord.ext import commands
import sqlite3
import json

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
    cursor.execute("SELECT * FROM clans_table WHERE clan_id = ?",(clan_id,))
    return cursor.fetchone()

@bot.event
async def on_ready():
    sings = await bot.tree.sync()
    print(f"{len(sings)} comands sync.")
    print("Bot start with sucess.")

@bot.tree.command(description = "Create a new clan")
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

@bot.tree.command(description = "Delete your clan")
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
    await interaction.response.send_message("Your clan as deleted with sucess")

@bot.tree.command(description= "Get your clan situation")
async def situation(interaction: discord.Interaction):
    infos = get_infos_by_user_id(interaction.user.id)
    await interaction.response.send_message(f"Infos: {infos}")

bot.run(token)