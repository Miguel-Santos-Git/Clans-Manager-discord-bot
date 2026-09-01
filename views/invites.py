import discord
import sqlite3

connection = sqlite3.connect("bank.db")
cursor = connection.cursor()


def get_infos_by_user_id(user_id):
    cursor.execute(
        "SELECT * FROM users_table WHERE user_id = ?",
        (user_id,)
    )
    return cursor.fetchone()


def get_clan_by_id(clan_id):
    cursor.execute(
        "SELECT * FROM clans_table WHERE id = ?",
        (clan_id,)
    )
    return cursor.fetchone()


class invites_(discord.ui.View):
    def __init__(self, user, invites):
        super().__init__()

        self.user = user
        self.invites = invites
        self.used = False

        # Cria um botão para cada convite
        for invite in self.invites:
            clan_id = invite[0]
            user_id = invite[1]

            clan = get_clan_by_id(clan_id)
            if not clan: continue

            name = clan[1]
            button = discord.ui.Button(label=f"Enter in: {name}", style=discord.ButtonStyle.green)

            async def accept_invite(interaction: discord.Interaction, button=button, clan_id=clan_id, user_id=user_id):
                if interaction.user.id != self.user.id:
                    return await interaction.response.send_message("This isn't your invite menu!", ephemeral=True)
                
                if self.used: return
                self.used = True

                for child in self.children:
                    child.disabled = True

                infos = get_infos_by_user_id(user_id)

                if infos:
                    cursor.execute("UPDATE users_table SET clan_id = ?, clan_position = ? WHERE user_id = ?",(clan_id, "MEMBER", user_id))
                else:
                    cursor.execute("INSERT INTO users_table(user_id, clan_id, clan_position)VALUES (?, ?, ?)",(user_id, clan_id, "MEMBER"))

                cursor.execute("DELETE FROM invites_table WHERE clan_id = ? AND user_id = ?",(clan_id, user_id))

                connection.commit()
                await interaction.response.edit_message(view=self)
                await interaction.followup.send(f"You entered in: **{name}**!",ephemeral=True)

            button.callback = accept_invite
            self.add_item(button)