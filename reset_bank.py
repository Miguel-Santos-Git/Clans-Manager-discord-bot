import sqlite3
connection = sqlite3.connect("bank.db")
cursor = connection.cursor()

cursor.execute("DELETE FROM clans_table")
cursor.execute("DELETE FROM invites_table")
cursor.execute("DELETE FROM users_table")

connection.commit()