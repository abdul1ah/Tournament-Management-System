import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from configparser import ConfigParser
from firebase_admin import credentials, firestore
import firebase_admin
from backend import *



def setup_styles():

    style = ttk.Style()
    
    style.configure('TFrame', background='#f0f0f0')
    
    style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
    
    style.configure('TButton', font=('Arial', 10))
    
    style.configure('Header.TLabel', font=('Arial', 16, 'bold'))
    
    style.configure('TEntry', font=('Arial', 10))



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


def clear_window(root):
    
    for widget in root.winfo_children():
    
        widget.destroy()


def show_register_window(root):
    
    clear_window(root)
    
    main_frame = ttk.Frame(root, padding="20")
    
    main_frame.pack(expand=True, fill='both')
    
    ttk.Label(main_frame, text="Register New Player", style='Header.TLabel').pack(pady=20)
    
    register_frame = ttk.Frame(main_frame)
    register_frame.pack(pady=10)
    
    ttk.Label(register_frame, text="Username:").grid(row=0, column=0, pady=5, padx=5)
    username_var = tk.StringVar()
    ttk.Entry(register_frame, textvariable=username_var, width=30).grid(row=0, column=1, pady=5)
    
    ttk.Label(register_frame, text="Password:").grid(row=1, column=0, pady=5, padx=5)
    password_var = tk.StringVar()
    ttk.Entry(register_frame, textvariable=password_var, width=30, show="*").grid(row=1, column=1, pady=5)
    
    ttk.Button(register_frame, text="Register", 
               command=lambda: register_user(root, username_var, password_var), 
               width=20).grid(row=2, column=0, columnspan=2, pady=10)
    
    ttk.Button(register_frame, text="Back to Login", 
               command=lambda: show_login_window(root), 
               width=20).grid(row=3, column=0, columnspan=2, pady=5)


def show_login_window(root):
    clear_window(root)
    setup_styles()
    
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(expand=True, fill='both')
    
    ttk.Label(main_frame, text="Gaming Portal Project", style='Header.TLabel').pack(pady=20)
    
    login_frame = ttk.Frame(main_frame)
    login_frame.pack(pady=10)
    
    ttk.Label(login_frame, text="Username:").grid(row=0, column=0, pady=5, padx=5)
    username_var = tk.StringVar()
    ttk.Entry(login_frame, textvariable=username_var, width=30).grid(row=0, column=1, pady=5)
    
    ttk.Label(login_frame, text="Password:").grid(row=1, column=0, pady=5, padx=5)
    password_var = tk.StringVar()
    ttk.Entry(login_frame, textvariable=password_var, width=30, show="*").grid(row=1, column=1, pady=5)
    
    ttk.Button(login_frame, text="Login", 
               command=lambda: login(root, username_var, password_var), 
               width=20).grid(row=2, column=0, columnspan=2, pady=10)
    
    ttk.Button(login_frame, text="Register as Player", 
               command=lambda: show_register_window(root), 
               width=20).grid(row=3, column=0, columnspan=2, pady=5)
    
    ttk.Button(login_frame, text="View as Spectator", 
               command=lambda: show_spectator_view(root), 
               width=20).grid(row=4, column=0, columnspan=2, pady=5)

def show_spectator_view(root):
    clear_window(root)
    
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(expand=True, fill='both')
    
    ttk.Label(main_frame, text="Player Statistics", style='Header.TLabel').pack(pady=10)
    
    columns = ('Username', 'Tournaments Won', 'Matches Won', 'Total Matches')
    tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=10)
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    
    tree.pack(pady=10, padx=10, fill='both', expand=True)
    
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tree.configure(yscrollcommand=scrollbar.set)
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, ps.tournaments_won, ps.matches_won, ps.total_matches
            FROM users u
            JOIN player_stats ps ON u.id = ps.player_id
            WHERE u.role = 'player'
        """)
        
        for row in cursor.fetchall():
            tree.insert('', tk.END, values=row)
        
        cursor.close()
        conn.close()
    
    ttk.Button(main_frame, text="Back to Login", 
               command=lambda: show_login_window(root)).pack(pady=10)



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

def show_admin_dashboard(root, current_user):
    clear_window(root)

    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(expand=True, fill='both')

    ttk.Label(main_frame, text=f"Admin Dashboard - {current_user['username']}", 
              style='Header.TLabel').pack(pady=10)

    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill='both', expand=True, padx=10, pady=5)

    players_frame = ttk.Frame(notebook)
    notebook.add(players_frame, text='Players')

    columns = ('ID', 'Username', 'Games', 'Team', 'Tournaments Won', 'Matches Won')
    tree = ttk.Treeview(players_frame, columns=columns, show='headings', height=10)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=80)

    tree.pack(pady=10, padx=10, fill='both', expand=True)

    scrollbar = ttk.Scrollbar(players_frame, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tree.configure(yscrollcommand=scrollbar.set)

    btn_frame = ttk.Frame(players_frame)
    btn_frame.pack(pady=5)

    ttk.Button(btn_frame, text="Delete Player", 
               command=lambda: delete_player(tree)).pack(side=tk.LEFT, padx=5)

    ttk.Button(btn_frame, text="Undo Delete Player", 
               command=lambda: restore_player(tree)).pack(side=tk.RIGHT, padx=5)

    tournaments_frame = ttk.Frame(notebook)
    notebook.add(tournaments_frame, text='Tournaments')

    tournament_form = ttk.Frame(tournaments_frame)
    tournament_form.pack(pady=20)


    ttk.Label(tournament_form, text="Tournament Name:").grid(row=0, column=0, padx=5, pady=5)
    tournament_name = tk.StringVar()
    ttk.Entry(tournament_form, textvariable=tournament_name).grid(row=0, column=1, padx=5, pady=5)


    ttk.Label(tournament_form, text="Game:").grid(row=1, column=0, padx=5, pady=5)
    tournament_game = tk.StringVar()
    game_combo = ttk.Combobox(tournament_form, textvariable=tournament_game)
    game_combo['values'] = get_games()
    game_combo.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(tournaments_frame, text="Existing Tournaments").pack(pady=10)
    tournament_tree = ttk.Treeview(tournaments_frame, columns=('ID', 'Name', 'Game', 'Created By'), show='headings', height=5)

    for col in ('ID', 'Name', 'Game', 'Created By'):
        tournament_tree.heading(col, text=col)
        tournament_tree.column(col, width=100)

    tournament_tree.pack(pady=10, padx=10, fill='both', expand=True)

    tournament_buttons = ttk.Frame(tournaments_frame)
    tournament_buttons.pack(pady=5)

    ttk.Button(tournament_form, text="Create Tournament", 
               command=lambda: create_tournament(tournament_name, tournament_game, tree, current_user['id'], tournament_tree)).grid(row=2, column=0, columnspan=2, pady=10)

    ttk.Button(tournament_buttons, text="Edit Tournament", 
               command=lambda: edit_tournament(tournament_tree, tournament_name, tournament_game)).pack(side=tk.LEFT, padx=5)

    ttk.Button(tournament_buttons, text="Delete Tournament", 
               command=lambda: delete_tournament(tournament_tree)).pack(side=tk.LEFT, padx=5)

    ttk.Button(tournament_buttons, text="Undo Delete Tournament", 
               command=lambda: restore_tournament(tournament_tree)).pack(side=tk.LEFT, padx=5)

    matches_frame = ttk.Frame(notebook)
    notebook.add(matches_frame, text='Matches')

    match_form = ttk.Frame(matches_frame)
    match_form.pack(pady=20)

    players = get_players()

    ttk.Label(match_form, text="Player 1:").grid(row=0, column=0, padx=5, pady=5)
    player1_var = tk.StringVar()
    player1_combo = ttk.Combobox(match_form, textvariable=player1_var)
    player1_combo['values'] = players
    player1_combo.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(match_form, text="Player 2:").grid(row=1, column=0, padx=5, pady=5)
    player2_var = tk.StringVar()
    player2_combo = ttk.Combobox(match_form, textvariable=player2_var)
    player2_combo['values'] = players
    player2_combo.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(match_form, text="Game:").grid(row=2, column=0, padx=5, pady=5)
    match_game_var = tk.StringVar()
    match_game_combo = ttk.Combobox(match_form, textvariable=match_game_var)
    match_game_combo.grid(row=2, column=1, padx=5, pady=5)

    ttk.Label(match_form, text="Winner:").grid(row=3, column=0, padx=5, pady=5)
    winner_var = tk.StringVar()
    winner_combo = ttk.Combobox(match_form, textvariable=winner_var)
    winner_combo.grid(row=3, column=1, padx=5, pady=5)

    def update_match_options(*args):
        p1 = player1_var.get()
        p2 = player2_var.get()
        if p1 and p2:
            if p1 == p2:
                winner_combo['values'] = []
                match_game_combo['values'] = []
            else:
                winner_combo['values'] = [p1, p2]
                common_games = get_common_games(p1, p2)
                match_game_combo['values'] = common_games
        else:
            winner_combo['values'] = []
            match_game_combo['values'] = []

    player1_var.trace_add('write', update_match_options)
    player2_var.trace_add('write', update_match_options)

    ttk.Label(match_form, text="Match Type:").grid(row=4, column=0, padx=5, pady=5)
    match_type_var = tk.StringVar()
    match_type_combo = ttk.Combobox(match_form, textvariable=match_type_var)
    match_type_combo['values'] = ['Friendly', 'Tournament']
    match_type_combo.grid(row=4, column=1, padx=5, pady=5)


    ttk.Button(match_form, text="Record Match", 
               command=lambda: create_match(player1_var, player2_var, match_game_var, winner_var, match_type_var, tree, match_tree)).grid(row=5, column=0, columnspan=2, pady=10)

    ttk.Label(matches_frame, text="Match History").pack(pady=10)
    match_tree = ttk.Treeview(matches_frame, 
                             columns=('ID', 'Game', 'Player 1', 'Player 2', 'Winner', 'Type'), 
                             show='headings', 
                             height=5)

    for col in ('ID', 'Game', 'Player 1', 'Player 2', 'Winner', 'Type'):
        match_tree.heading(col, text=col)
        match_tree.column(col, width=80)

    match_tree.pack(pady=10, padx=10, fill='both', expand=True)

    match_buttons = ttk.Frame(matches_frame)
    match_buttons.pack(pady=5)

    ttk.Button(match_buttons, text="Edit Match", 
               command=lambda: edit_match(match_tree, player1_var, player2_var, match_game_var, winner_var, match_type_var)).pack(side=tk.LEFT, padx=5)

    ttk.Button(match_buttons, text="Delete Match", 
               command=lambda: delete_match(match_tree)).pack(side=tk.LEFT, padx=5)

    ttk.Button(match_buttons, text="Undo Delete Match", 
               command=lambda: restore_match(match_tree, tree)).pack(side=tk.LEFT, padx=5)

    backup_button_frame = ttk.Frame(main_frame)
    backup_button_frame.pack(pady=10)

    ttk.Button(backup_button_frame, text="Backup Database", 
               command=backup_database).pack(side=tk.LEFT, padx=5)

    ttk.Button(main_frame, text="Logout", 
               command=lambda: show_login_window(root)).pack(pady=10)

    refresh_tree(tree)
    refresh_tournaments(tournament_tree)
    refresh_matches(match_tree)



def show_player_dashboard(root, current_user):
    clear_window(root)
    
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(expand=True, fill='both')
    
    ttk.Label(main_frame, text=f"Player Dashboard - {current_user['username']}", 
              style='Header.TLabel').pack(pady=10)
    
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill='both', expand=True, padx=10, pady=5)
    
    
    profile_frame = ttk.Frame(notebook)
    notebook.add(profile_frame, text='Profile')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, ps.tournaments_won, ps.matches_won, ps.total_matches
            FROM users u
            JOIN player_stats ps ON u.id = ps.player_id
            WHERE u.id = %s
        """, (current_user['id'],))
        
        player_info = cursor.fetchone()
        
        info_frame = ttk.Frame(profile_frame)
        info_frame.pack(pady=20)
        
    
        ttk.Label(info_frame, text=f"Username: {player_info[0]}").grid(row=0, column=0, pady=5, sticky='w')
        ttk.Label(info_frame, text=f"Tournaments Won: {player_info[1]}").grid(row=1, column=0, pady=5, sticky='w')
        ttk.Label(info_frame, text=f"Matches Won: {player_info[2]}").grid(row=2, column=0, pady=5, sticky='w')
        ttk.Label(info_frame, text=f"Total Matches: {player_info[3]}").grid(row=3, column=0, pady=5, sticky='w')
        
        cursor.close()
        conn.close()
    
    
    games_frame = ttk.Frame(notebook)
    notebook.add(games_frame, text='Games')
    
    ttk.Label(games_frame, text="Select Games:").pack(pady=10)
    
    games_list = ttk.Frame(games_frame)
    games_list.pack(pady=10)
    
    selected_games = []
    games = get_games()
    
    
    tournaments_frame = ttk.Frame(notebook)
    notebook.add(tournaments_frame, text='Tournaments')
    
    ttk.Label(tournaments_frame, text="Available Tournaments").pack(pady=10)
    
    columns = ('Name', 'Game', 'Status')
    tournaments_tree = ttk.Treeview(tournaments_frame, columns=columns, show='headings', height=10)
    
    for col in columns:
        tournaments_tree.heading(col, text=col)
        tournaments_tree.column(col, width=150)
    
    tournaments_tree.pack(pady=10, padx=10, fill='both', expand=True)
    

    for i, game in enumerate(games):
        var = tk.BooleanVar()
        ttk.Checkbutton(games_list, text=game, variable=var).grid(row=i, column=0, sticky='w', pady=2)
        selected_games.append((game, var))
    
    ttk.Button(games_list, text="Update Games", 
               command=lambda: update_player_games(current_user['id'], selected_games, tournaments_tree)).grid(row=len(games), column=0, pady=10)
    
  
    teams_frame = ttk.Frame(notebook)
    notebook.add(teams_frame, text='Teams')
    
    ttk.Label(teams_frame, text="Team Management").pack(pady=10)
    
    team_form = ttk.Frame(teams_frame)
    team_form.pack(pady=10)
    
    ttk.Label(team_form, text="Join Team:").grid(row=0, column=0, pady=5, padx=5)
    team_choice = tk.StringVar()
    team_combo = ttk.Combobox(team_form, textvariable=team_choice, width=28)
    team_combo['values'] = get_teams()
    team_combo.grid(row=0, column=1, pady=5)
    
    ttk.Button(team_form, text="Join Team", 
               command=lambda: join_team(current_user['id'], team_choice)).grid(row=1, column=0, columnspan=2, pady=5)
    
    ttk.Label(team_form, text="Create Team:").grid(row=2, column=0, pady=5, padx=5)
    new_team_name = tk.StringVar()
    ttk.Entry(team_form, textvariable=new_team_name, width=30).grid(row=2, column=1, pady=5)
    
    ttk.Button(team_form, text="Create Team", 
               command=lambda: create_team(current_user['id'], new_team_name)).grid(row=3, column=0, columnspan=2, pady=5)
    
    ttk.Button(tournaments_frame, text="Register for Tournament", 
               command=lambda: register_for_tournament(tournaments_tree, current_user['id'])).pack(pady=10)
    
    ttk.Button(main_frame, text="Logout", 
               command=lambda: show_login_window(root)).pack(pady=10)
    
  
    refresh_player_tournaments(tournaments_tree, current_user['id'])

def refresh_player_tournaments(tree, player_id):

    for item in tree.get_children():
        tree.delete(item)

    try:
        tournaments = get_player_tournaments_status(player_id)
        for row in tournaments:
            tree.insert('', tk.END, values=row)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to refresh tournaments: {str(e)}")



def update_player_games(player_id, selected_games, tournaments_tree=None):
    result = update_player_games_db(player_id, selected_games)

    if result['success']:
        messagebox.showinfo("Success", result['message'])
        if tournaments_tree:
            refresh_player_tournaments(tournaments_tree, player_id)
    else:
        messagebox.showerror("Error", result['message'])



def join_team(player_id, team_choice):
    team_name = team_choice.get()
    if not team_name:
        messagebox.showerror("Error", "Please select a team")
        return

    result = join_team_by_name(player_id, team_name)

    if result['success']:
        messagebox.showinfo("Success", result['message'])
    else:
        messagebox.showerror("Error", result['message'])



def create_team(player_id, team_name_var):

    team_name = team_name_var.get()
    if not team_name:
        messagebox.showerror("Error", "Please enter a team name")
        return

    result = create_team_with_player(player_id, team_name)

    if result['success']:
        messagebox.showinfo("Success", result['message'])
        team_name_var.set("")
    else:
        messagebox.showerror("Error", result['message'])



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


def main():
    root = tk.Tk()
    root.title("Tournament Manager")
    root.geometry("800x600")
    show_login_window(root)
    root.mainloop()

if __name__ == "__main__":
    main() 