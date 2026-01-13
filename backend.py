import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from configparser import ConfigParser
from firebase_admin import credentials, firestore
import firebase_admin


def config(filename='database.ini', section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in {filename}')
    return db


def get_db_connection():
    try:
        params = config()
        connection = psycopg2.connect(**params)
        return connection
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None


def backup_database():
    
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("C:/Users/idekb/OneDrive/Desktop/Project/player-portal-backup-firebase-adminsdk-fbsvc-ff02727fc1.json")
            firebase_admin.initialize_app(cred)

        
        db = firestore.client()
    except Exception as e:
        messagebox.showerror("Firebase Error", f"Error initializing Firebase:\n{e}")
        return

   
    conn = get_db_connection()
    if conn is None:
        messagebox.showerror("Database Error", "Could not connect to PostgreSQL database.")
        return

    cursor = conn.cursor()


    tables = {
        "users": "users",
        "games": "games",
        "player_games": "player_games",
        "teams": "teams",
        "team_members": "team_members",
        "tournaments": "tournaments",
        "tournament_participants": "tournament_participants",
        "matches": "matches",
        "player_stats": "player_stats"
    }


    try:
        for table, collection in tables.items():

            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            for row in rows:
                data = dict(zip(columns, row))
                db.collection(collection).add(data)
        messagebox.showinfo("Success", "Database backed up to Firebase successfully.")

    except Exception as e:
        messagebox.showerror("Backup Error", f"Error during backup:\n{e}")
    finally:
        cursor.close()
        conn.close()


def authenticate_user(username, password):
    conn = get_db_connection()
    if conn is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, role FROM users 
            WHERE username = %s AND password = %s
        """, (username, password))

        row = cursor.fetchone()
        if row:
            return {
                "success": True,
                "user": {
                    "id": row[0],
                    "username": username,
                    "role": row[1]
                }
            }
        else:
            return {"success": False, "message": "Invalid username or password."}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        cursor.close()
        conn.close()


def login(root, username_var, password_var):
    username = username_var.get()
    password = password_var.get()

    if not username or not password:
        messagebox.showerror("Error", "Please fill in all fields")
        return

    result = authenticate_user(username, password)

    if result['success']:
        current_user = result['user']
        if current_user['role'] == 'admin':
            show_admin_dashboard(root, current_user)
        else:
            show_player_dashboard(root, current_user)
    else:
        messagebox.showerror("Error", result['message'])



def register_user(root, username_var, password_var):
    username = username_var.get()
    password = password_var.get()
    
    if not username or not password:
        messagebox.showerror("Error", "Please fill in all fields")
        return
    
    conn = get_db_connection()
    if conn is None:
        return
    
    cursor = conn.cursor()
    
   
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        messagebox.showerror("Error", "Username already exists")
        cursor.close()
        conn.close()
        return
    
    
    cursor.execute("""
        INSERT INTO users (username, password, role)
        VALUES (%s, %s, 'player')
        RETURNING id
    """, (username, password))
    
    user_id = cursor.fetchone()[0]
    
    
    cursor.execute("""
        INSERT INTO player_stats (player_id)
        VALUES (%s)
    """, (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    messagebox.showinfo("Success", "Registration successful! Please login.")
    show_login_window(root)


def get_games():
    conn = get_db_connection()
    if conn is None:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM games")
    games = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return games

def get_players():
    conn = get_db_connection()
    if conn is None:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE role = 'player'")
    players = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return players

def get_teams():
    conn = get_db_connection()
    if conn is None:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM teams")
    teams = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return teams


def fetch_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.username, 
                   STRING_AGG(g.name, ', ') as games,
                   t.name as team,
                   ps.tournaments_won,
                   ps.matches_won
            FROM users u
            LEFT JOIN player_games pg ON u.id = pg.player_id
            LEFT JOIN games g ON pg.game_id = g.id
            LEFT JOIN team_members tm ON u.id = tm.player_id
            LEFT JOIN teams t ON tm.team_id = t.id
            LEFT JOIN player_stats ps ON u.id = ps.player_id
            WHERE u.role = 'player'
            GROUP BY u.id, u.username, t.name, ps.tournaments_won, ps.matches_won
        """)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return columns, rows
    except Exception as e:
        print("Database error:", e)
        return [], []


def register_player_to_tournament(player_id, tournament_name):
    conn = get_db_connection()
    if conn is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO tournament_participants (tournament_id, player_id)
            SELECT t.id, %s
            FROM tournaments t
            WHERE t.name = %s
        """, (player_id, tournament_name))
        conn.commit()
        return {"success": True, "message": f"Registered for tournament {tournament_name} successfully!"}
    except IntegrityError:
        conn.rollback()
        return {"success": False, "message": "Already registered for this tournament."}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        cursor.close()
        conn.close()


def get_user_id_by_username(username):
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return user_id[0] if user_id else None
    except Exception as e:
        raise e


def get_game_id_by_name(game_name):
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM games WHERE name = %s", (game_name,))
        game_id = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return game_id[0] if game_id else None
    except Exception as e:
        raise e


def get_match_players(match_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute("""
            SELECT player1_id, player2_id, winner_id
            FROM matches
            WHERE id = %s
        """, (match_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result
    except Exception as e:
        raise e


def update_stats_on_match_delete(player1_id, player2_id, winner_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE player_stats
            SET total_matches = total_matches - 1
            WHERE player_id IN (%s, %s)
        """, (player1_id, player2_id))
        
        cursor.execute("""
            UPDATE player_stats
            SET matches_won = matches_won - 1
            WHERE player_id = %s
        """, (winner_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise e


def delete_players_by_ids(player_ids):
    if not player_ids:
        return {"success": False, "message": "No player IDs provided."}

    conn = get_db_connection()
    if conn is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = conn.cursor()
    try:
        for player_id in player_ids:
            cursor.execute("DELETE FROM player_stats WHERE player_id = %s", (player_id,))
            cursor.execute("DELETE FROM player_games WHERE player_id = %s", (player_id,))
            cursor.execute("DELETE FROM team_members WHERE player_id = %s", (player_id,))
            cursor.execute("DELETE FROM tournament_participants WHERE player_id = %s", (player_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (player_id,))

        conn.commit()
        return {"success": True, "message": "Player(s) deleted successfully."}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"Failed to delete player(s): {str(e)}"}
    finally:
        cursor.close()
        conn.close()


def get_player_tournaments_status(player_id):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT 
                    t.name as tournament_name, 
                    g.name as game_name,
                    CASE 
                        WHEN tp.player_id IS NOT NULL THEN 'Registered'
                        ELSE 'Available'
                    END as status
                FROM tournaments t
                INNER JOIN games g ON t.game_id = g.id
                INNER JOIN player_games pg ON g.id = pg.game_id AND pg.player_id = %s
                LEFT JOIN tournament_participants tp ON t.id = tp.tournament_id AND tp.player_id = %s
                ORDER BY t.name ASC
            """, (player_id, player_id))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching tournaments: {e}")
        return []
    finally:
        conn.close()


def register_for_tournament(tree, player_id):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showerror("Error", "Please select a tournament")
        return

    tournament_name = tree.item(selected_item[0])['values'][0]

    result = register_player_to_tournament(player_id, tournament_name)

    if result['success']:
        messagebox.showinfo("Success", result['message'])
    else:
        messagebox.showerror("Error", result['message'])

def delete_tournament(tree):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "No tournament selected for deletion.")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Delete {len(selected_items)} tournament(s)?")
    if not confirm:
        return

    try:
        for item in selected_items:
            tournament_id = tree.item(item)['values'][0]
            delete_tournament_by_id(tournament_id)

        messagebox.showinfo("Success", "Tournament(s) deleted successfully!")
        refresh_tournaments(tree)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to delete tournament(s): {str(e)}")


def edit_tournament(tree, name_var, game_var):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "No tournament selected for editing.")
        return

    if len(selected_items) > 1:
        messagebox.showwarning("Warning", "Please select only one tournament to edit.")
        return

    tournament_id = tree.item(selected_items[0])['values'][0]
    new_name = name_var.get()
    new_game = game_var.get()

    if not new_name or not new_game:
        messagebox.showerror("Error", "Please fill in all fields")
        return

    try:
        game_id = get_game_id_by_name(new_game)
        if not game_id:
            messagebox.showerror("Error", "Selected game not found")
            return

        update_tournament(tournament_id, new_name, game_id)
        messagebox.showinfo("Success", "Tournament updated successfully!")
        name_var.set("")
        game_var.set("")
        refresh_tournaments(tree)

    except psycopg2.IntegrityError as e:
        if "unique constraint" in str(e).lower():
            messagebox.showerror("Error", "A tournament with this name already exists")
        else:
            messagebox.showerror("Error", f"Database error: {str(e)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update tournament: {str(e)}")



def delete_match(tree):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "No match selected for deletion.")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Delete {len(selected_items)} match(es)?")
    if not confirm:
        return

    try:
        for item in selected_items:
            match_id = tree.item(item)['values'][0]
            match_info = get_match_players(match_id)

            if match_info:
                player1_id, player2_id, winner_id = match_info
                update_stats_on_match_delete(player1_id, player2_id, winner_id)

            delete_match_by_id(match_id)

        messagebox.showinfo("Success", "Match(es) deleted successfully!")
        refresh_matches(tree)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to delete match(es): {str(e)}")


def edit_match(tree, player1_var, player2_var, game_var, winner_var, match_type_var):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "No match selected for editing.")
        return

    if len(selected_items) > 1:
        messagebox.showwarning("Warning", "Please select only one match to edit.")
        return

    match_id = tree.item(selected_items[0])['values'][0]
    player1 = player1_var.get()
    player2 = player2_var.get()
    game = game_var.get()
    winner = winner_var.get()
    match_type = match_type_var.get().lower()

    if not all([player1, player2, game, winner, match_type]):
        messagebox.showerror("Error", "Please fill in all fields")
        return

    try:
        player1_id = get_user_id_by_username(player1)
        player2_id = get_user_id_by_username(player2)
        winner_id = get_user_id_by_username(winner)
        game_id = get_game_id_by_name(game)
        
        old_match_info = old_match_info(match_id)
        if not old_match_info:
            messagebox.showerror("Error", "Original match not found.")
            return

        old_winner_id, old_player1_id, old_player2_id = old_match_info

        update_match_and_stats(
            match_id, game_id, player1_id, player2_id, winner_id,
            match_type, old_winner_id, old_player1_id, old_player2_id
        )

        messagebox.showinfo("Success", "Match updated successfully!")

        player1_var.set("")
        player2_var.set("")
        game_var.set("")
        winner_var.set("")
        match_type_var.set("")
        refresh_matches(tree)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to update match: {str(e)}")


def get_common_games(player1_username, player2_username):
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor()

    
    cursor.execute("SELECT id FROM users WHERE username = %s AND role = 'player'", (player1_username,))
    p1 = cursor.fetchone()
    cursor.execute("SELECT id FROM users WHERE username = %s AND role = 'player'", (player2_username,))
    p2 = cursor.fetchone()

    if not p1 or not p2:
        cursor.close()
        conn.close()
        return []

    player1_id = p1[0]
    player2_id = p2[0]


    query = """
        SELECT DISTINCT g.name
        FROM player_games pg1
        JOIN player_games pg2 ON pg1.game_id = pg2.game_id
        JOIN games g ON pg1.game_id = g.id
        WHERE pg1.player_id = %s AND pg2.player_id = %s
    """
    cursor.execute(query, (player1_id, player2_id))
    common_games = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return common_games



def restore_tournament(tree):
    try:
        restored_id = restore_tournament_from_backup()
        
        if restored_id:
            restore_tournament_participants_from_backup(restored_id)
            
            messagebox.showinfo("Success", "Tournament restored successfully!")
            refresh_tournaments(tree)
        else:
            messagebox.showinfo("Info", "No deleted tournaments to restore.")
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to restore tournament: {str(e)}")



def restore_match(tree, player_tree):
    try:
        restored = restore_match_from_backup()
        
        if restored:
            winner_id, player1_id, player2_id = restored
            update_player_stats_for_restored_match(winner_id, player1_id, player2_id)
            
            messagebox.showinfo("Success", "Match restored successfully!")
            refresh_matches(tree)
            refresh_tree(player_tree)
        else:
            messagebox.showinfo("Info", "No deleted matches to restore.")
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to restore match: {str(e)}")



def restore_player(tree):
    try:
        restored_id = restore_user_from_backup()
        
        if restored_id:
            restore_player_stats_from_backup(restored_id)
            restore_player_games_from_backup(restored_id)
            restore_team_memberships_from_backup(restored_id)
            
            messagebox.showinfo("Success", "Player restored successfully!")
            refresh_tree(tree)
        else:
            messagebox.showinfo("Info", "No deleted players to restore.")
            
    except Exception as e:
        messagebox.showerror("Error", f"Failed to restore player: {str(e)}")



def delete_tournament_by_id(tournament_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return False

        cursor = conn.cursor()
        cursor.execute("DELETE FROM tournament_participants WHERE tournament_id = %s", (tournament_id,))
        cursor.execute("DELETE FROM tournaments WHERE id = %s", (tournament_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        raise e



def delete_match_by_id(match_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return

        cursor = conn.cursor()
        cursor.execute("DELETE FROM matches WHERE id = %s", (match_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise e



def old_match_info(match_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT winner_id, player1_id, player2_id
            FROM matches
            WHERE id = %s
        """, (match_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result
    except Exception as e:
        raise e


def update_match_and_stats(match_id, game_id, player1_id, player2_id, winner_id, match_type, old_winner_id, old_player1_id, old_player2_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE matches 
            SET game_id = %s, 
                player1_id = %s, 
                player2_id = %s, 
                winner_id = %s, 
                match_type = %s
            WHERE id = %s
        """, (game_id, player1_id, player2_id, winner_id, match_type, match_id))
        
        if old_winner_id != winner_id:
            
            cursor.execute("""
                UPDATE player_stats
                SET matches_won = matches_won - 1
                WHERE player_id = %s
            """, (old_winner_id,))

            cursor.execute("""
                UPDATE player_stats
                SET matches_won = matches_won + 1
                WHERE player_id = %s
            """, (winner_id,))

            
            cursor.execute("""
                UPDATE player_stats
                SET total_matches = total_matches - 1
                WHERE player_id IN (%s, %s)
            """, (old_player1_id, old_player2_id))

            cursor.execute("""
                UPDATE player_stats
                SET total_matches = total_matches + 1
                WHERE player_id IN (%s, %s)
            """, (player1_id, player2_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        raise e


def update_tournament(tournament_id, new_name, new_game_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tournaments 
            SET name = %s, game_id = %s
            WHERE id = %s
        """, (new_name, new_game_id, tournament_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise e


def create_team_with_player(player_id, team_name):
    conn = get_db_connection()
    if conn is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO teams (name)
            VALUES (%s)
            RETURNING id
        """, (team_name,))
        team_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO team_members (team_id, player_id)
            VALUES (%s, %s)
        """, (team_id, player_id))

        conn.commit()
        return {"success": True, "message": f"Team '{team_name}' created successfully!"}
    except psycopg2.IntegrityError:
        conn.rollback()
        return {"success": False, "message": "Team name already exists."}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        cursor.close()
        conn.close()


def update_player_games_db(player_id, selected_games):
    conn = get_db_connection()
    if conn is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        
        
        cursor.execute("ALTER TABLE player_games DISABLE TRIGGER trg_backup_player_games")
        
        
        cursor.execute("DELETE FROM player_games WHERE player_id = %s", (player_id,))
        
        
        for game, var in selected_games:
            if var.get():
                cursor.execute("""
                    INSERT INTO player_games (player_id, game_id)
                    SELECT %s, id FROM games WHERE name = %s
                """, (player_id, game))

        
        cursor.execute("ALTER TABLE player_games ENABLE TRIGGER trg_backup_player_games")
        
        conn.commit()
        return {"success": True, "message": "Games updated successfully!"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        cursor.close()
        conn.close()



def join_team_by_name(player_id, team_name):
    conn = get_db_connection()
    if conn is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM teams WHERE name = %s", (team_name,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "Team not found."}
        
        team_id = row[0]

        cursor.execute("""
            INSERT INTO team_members (team_id, player_id)
            VALUES (%s, %s)
        """, (team_id, player_id))

        conn.commit()
        return {"success": True, "message": f"Joined team '{team_name}' successfully!"}
    except psycopg2.IntegrityError:
        conn.rollback()
        return {"success": False, "message": "Already a member of this team."}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        cursor.close()
        conn.close()


def refresh_player_tournaments(tree, player_id):

    for item in tree.get_children():
        tree.delete(item)

    try:
        tournaments = get_player_tournaments_status(player_id)
        for row in tournaments:
            tree.insert('', tk.END, values=row)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to refresh tournaments: {str(e)}")


def refresh_tree(tree):
    try:
        for item in tree.get_children():
            tree.delete(item)
        
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, 
                   STRING_AGG(g.name, ', ') as games,
                   t.name as team,
                   ps.tournaments_won,
                   ps.matches_won
            FROM users u
            LEFT JOIN player_games pg ON u.id = pg.player_id
            LEFT JOIN games g ON pg.game_id = g.id
            LEFT JOIN team_members tm ON u.id = tm.player_id
            LEFT JOIN teams t ON tm.team_id = t.id
            LEFT JOIN player_stats ps ON u.id = ps.player_id
            WHERE u.role = 'player'
            GROUP BY u.id, u.username, t.name, ps.tournaments_won, ps.matches_won
        """)
        
        for row in cursor.fetchall():
            tree.insert('', tk.END, values=row)
        
        cursor.close()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to refresh data: {str(e)}")

def delete_player(tree):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "No player selected for deletion.")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Delete {len(selected_items)} player(s)?")
    if not confirm:
        return

    player_ids = [tree.item(item)['values'][0] for item in selected_items]
    result = delete_players_by_ids(player_ids)

    if result['success']:
        messagebox.showinfo("Success", result['message'])
        refresh_tree(tree)
    else:
        messagebox.showerror("Error", result['message'])


def create_tournament(name_var, game_var, tree, admin_id, tournament_tree):
    name = name_var.get()
    game = game_var.get()
    
    if not name or not game:
        messagebox.showerror("Error", "Please fill in all fields")
        return
    
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        
        
        cursor.execute("SELECT id FROM games WHERE name = %s", (game,))
        game_result = cursor.fetchone()
        
        if not game_result:
            messagebox.showerror("Error", "Selected game not found")
            cursor.close()
            conn.close()
            return
        
        game_id = game_result[0]
        
        
        cursor.execute("""
            INSERT INTO tournaments (name, game_id, created_by)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (name, game_id, admin_id))
        
        tournament_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        messagebox.showinfo("Success", f"Tournament '{name}' created successfully!")
        name_var.set("")
        game_var.set("")
        
    
        refresh_tree(tree)
        refresh_tournaments(tournament_tree)
        
    except psycopg2.IntegrityError as e:
        if "unique constraint" in str(e).lower():
            messagebox.showerror("Error", "A tournament with this name already exists")
        else:
            messagebox.showerror("Error", f"Database error: {str(e)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create tournament: {str(e)}")

def create_match(player1_var, player2_var, game_var, winner_var, match_type_var, tree, match_tree):
    player1 = player1_var.get()
    player2 = player2_var.get()
    game = game_var.get()
    winner = winner_var.get()
    match_type = match_type_var.get().lower()  
    
    if not all([player1, player2, game, winner, match_type]):
        messagebox.showerror("Error", "Please fill in all fields")
        return
    
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (player1,))
        player1_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (player2,))
        player2_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (winner,))
        winner_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM games WHERE name = %s", (game,))
        game_id = cursor.fetchone()[0]
        
        
        cursor.execute("""
            INSERT INTO matches (game_id, player1_id, player2_id, winner_id, match_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (game_id, player1_id, player2_id, winner_id, match_type))
        
        
        cursor.execute("""
            UPDATE player_stats
            SET matches_won = matches_won + 1,
                total_matches = total_matches + 1
            WHERE player_id = %s
        """, (winner_id,))
        
        
        cursor.execute("""
            UPDATE player_stats
            SET total_matches = total_matches + 1
            WHERE player_id IN (%s, %s)
            AND player_id != %s
        """, (player1_id, player2_id, winner_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        messagebox.showinfo("Success", "Match recorded successfully!")
        
        player1_var.set("")
        player2_var.set("")
        game_var.set("")
        winner_var.set("")
        match_type_var.set("")
        
        
        refresh_tree(tree)
        refresh_matches(match_tree)
        
    except Exception as e:
        messagebox.showerror("Error", str(e))


def edit_tournament(tree, name_var, game_var):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("Warning", "No tournament selected for editing.")
        return

    if len(selected_items) > 1:
        messagebox.showwarning("Warning", "Please select only one tournament to edit.")
        return

    tournament_id = tree.item(selected_items[0])['values'][0]
    new_name = name_var.get()
    new_game = game_var.get()

    if not new_name or not new_game:
        messagebox.showerror("Error", "Please fill in all fields")
        return

    try:
        game_id = get_game_id_by_name(new_game)
        if not game_id:
            messagebox.showerror("Error", "Selected game not found")
            return

        update_tournament(tournament_id, new_name, game_id)
        messagebox.showinfo("Success", "Tournament updated successfully!")
        name_var.set("")
        game_var.set("")
        refresh_tournaments(tree)

    except psycopg2.IntegrityError as e:
        if "unique constraint" in str(e).lower():
            messagebox.showerror("Error", "A tournament with this name already exists")
        else:
            messagebox.showerror("Error", f"Database error: {str(e)}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update tournament: {str(e)}")


def refresh_matches(tree):
    for item in tree.get_children():
        tree.delete(item)
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.id, g.name, 
                       u1.username as player1, 
                       u2.username as player2,
                       w.username as winner,
                       m.match_type
                FROM matches m
                JOIN games g ON m.game_id = g.id
                JOIN users u1 ON m.player1_id = u1.id
                JOIN users u2 ON m.player2_id = u2.id
                JOIN users w ON m.winner_id = w.id
                ORDER BY m.id DESC
            """)
            
            for row in cursor.fetchall():
                tree.insert('', tk.END, values=row)
            
            cursor.close()
            conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to refresh matches: {str(e)}")

def refresh_tournaments(tree):
    for item in tree.get_children():
        tree.delete(item)
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.name, g.name, u.username
                FROM tournaments t
                JOIN games g ON t.game_id = g.id
                JOIN users u ON t.created_by = u.id
                ORDER BY t.id DESC
            """)
            
            for row in cursor.fetchall():
                tree.insert('', tk.END, values=row)
            
            cursor.close()
            conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to refresh tournaments: {str(e)}")



def restore_tournament_from_backup():
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()

        cursor.execute("""
            WITH deleted_tournament AS (
                DELETE FROM tournaments_backup
                WHERE id = (
                    SELECT id 
                    FROM tournaments_backup 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
                RETURNING *
            )
            INSERT INTO tournaments (id, name, game_id, created_by, created_at, winner_id)
            SELECT id, name, game_id, created_by, created_at, winner_id
            FROM deleted_tournament
            RETURNING id;
        """)
        
        restored_id = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return restored_id[0] if restored_id else None

    except Exception as e:
        raise e


def restore_tournament_participants_from_backup(tournament_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()

        cursor.execute("""
            WITH deleted_participants AS (
                DELETE FROM tournament_participants_backup
                WHERE tournament_id = %s
                RETURNING *
            )
            INSERT INTO tournament_participants (tournament_id, player_id, registered_at)
            SELECT tournament_id, player_id, registered_at
            FROM deleted_participants;
        """, (tournament_id,))
        
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        raise e



def restore_match_from_backup():
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH deleted_match AS (
                DELETE FROM matches_backup
                WHERE id = (
                    SELECT id 
                    FROM matches_backup 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
                RETURNING *
            )
            INSERT INTO matches (id, game_id, player1_id, player2_id, winner_id, match_type, created_at)
            SELECT id, game_id, player1_id, player2_id, winner_id, match_type, created_at
            FROM deleted_match
            RETURNING winner_id, player1_id, player2_id;
        """)
        
        restored_data = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return restored_data  
    except Exception as e:
        raise e


def update_player_stats_for_restored_match(winner_id, player1_id, player2_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()

        
        cursor.execute("""
            UPDATE player_stats
            SET matches_won = matches_won + 1,
                total_matches = total_matches + 1
            WHERE player_id = %s
        """, (winner_id,))
        
        
        cursor.execute("""
            UPDATE player_stats
            SET total_matches = total_matches + 1
            WHERE player_id IN (%s, %s)
              AND player_id != %s
        """, (player1_id, player2_id, winner_id))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise e



def restore_user_from_backup():
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH deleted_user AS (
                DELETE FROM users_backup
                WHERE id = (
                    SELECT id 
                    FROM users_backup 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
                RETURNING *
            )
            INSERT INTO users (id, username, password, role, created_at)
            SELECT id, username, password, role, created_at
            FROM deleted_user
            RETURNING id;
        """)
        
        restored_id = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return restored_id[0] if restored_id else None
    
    except Exception as e:
        raise e



def restore_player_stats_from_backup(player_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH deleted_stats AS (
                DELETE FROM player_stats_backup
                WHERE player_id = %s
                RETURNING *
            )
            INSERT INTO player_stats (player_id, tournaments_won, matches_won, total_matches)
            SELECT player_id, tournaments_won, matches_won, total_matches
            FROM deleted_stats;
        """, (player_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    except Exception as e:
        raise e



def restore_player_games_from_backup(player_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH deleted_games AS (
                DELETE FROM player_games_backup
                WHERE player_id = %s
                RETURNING *
            )
            INSERT INTO player_games (player_id, game_id)
            SELECT player_id, game_id
            FROM deleted_games;
        """, (player_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    except Exception as e:
        raise e


def restore_team_memberships_from_backup(player_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH deleted_memberships AS (
                DELETE FROM team_members_backup
                WHERE player_id = %s
                RETURNING *
            )
            INSERT INTO team_members (team_id, player_id, joined_at)
            SELECT team_id, player_id, joined_at
            FROM deleted_memberships;
        """, (player_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    except Exception as e:
        raise e





