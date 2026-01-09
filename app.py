import random
import time
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mafia_classic_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mafia Online 🕵️‍♂️</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --accent-color: #c0392b; /* أحمر مافيا */
            --btn-color: #e74c3c;
            --border-color: #333;
        }

        /* ثيم النهار */
        body.day-theme {
            --bg-color: #f0f2f5;
            --card-bg: #ffffff;
            --text-color: #2c3e50;
            --accent-color: #2980b9;
            --border-color: #ddd;
        }

        body { 
            font-family: 'Tajawal', sans-serif; 
            background-color: var(--bg-color); 
            color: var(--text-color); 
            text-align: center; 
            padding: 20px; 
            margin: 0; 
            transition: background-color 1s ease, color 0.5s ease;
        }

        .container { max-width: 600px; margin: 0 auto; }

        .card { 
            background: var(--card-bg); 
            padding: 25px; 
            border-radius: 15px; 
            margin: 15px auto; 
            box-shadow: 0 8px 20px rgba(0,0,0,0.2); 
            border: 1px solid var(--border-color); 
            transition: background 0.5s ease;
        }

        h1 { 
            font-size: 3rem; 
            margin-bottom: 10px; 
            color: var(--accent-color); 
            text-transform: uppercase; 
            letter-spacing: 2px;
        }

        button { 
            background: var(--accent-color); 
            color: white; 
            border: none; 
            padding: 15px 30px; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            margin: 5px; 
            font-weight: bold; 
            width: 100%; 
            max-width: 300px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        button:hover { filter: brightness(1.1); transform: translateY(-2px); }
        button:disabled { background: #7f8c8d; cursor: not-allowed; opacity: 0.6; transform: none; }
        
        button.action-btn { background: #f39c12; color: #000; }
        button.vote-btn { background: #27ae60; }

        input { 
            padding: 15px; 
            border-radius: 8px; 
            border: 2px solid var(--border-color); 
            background: var(--bg-color); 
            color: var(--text-color); 
            width: 80%; 
            margin-bottom: 15px; 
            font-size: 16px; 
            outline: none;
        }
        input:focus { border-color: var(--accent-color); }

        .role-reveal { 
            font-size: 24px; 
            font-weight: bold; 
            color: #f1c40f; 
            margin: 20px 0; 
            padding: 15px; 
            background: rgba(0,0,0,0.3); 
            border-radius: 8px; 
            border-left: 5px solid #f1c40f; 
        }

        .status { font-size: 18px; margin-bottom: 15px; font-weight: bold; opacity: 0.8; }
        .hidden { display: none; }

        .player-item { 
            padding: 15px; 
            background: rgba(128, 128, 128, 0.1); 
            margin: 8px 0; 
            border-radius: 8px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-right: 4px solid transparent;
        }
        .player-item.alive { border-right-color: #27ae60; }
        .player-item.dead { border-right-color: #c0392b; opacity: 0.5; text-decoration: line-through; }

        #logs-container { 
            max-height: 250px; 
            overflow-y: auto; 
            text-align: right; 
            background: rgba(0,0,0,0.2); 
            padding: 15px; 
            border-radius: 8px; 
            font-size: 14px; 
        }
        .log-entry { margin-bottom: 8px; border-bottom: 1px solid rgba(128,128,128,0.2); padding-bottom: 4px; }
        .highlight { color: var(--accent-color); font-weight: bold; }
        
        /* أيقونات الحالة */
        .icon-sun { font-size: 50px; display: block; margin: 0 auto; animation: spin 10s linear infinite; }
        .icon-moon { font-size: 50px; display: block; margin: 0 auto; color: #f1c40f; text-shadow: 0 0 20px #f1c40f; }

        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="">
    <div class="container">
        <h1>MAFIA 🎩</h1>

        <div id="login-area" class="card">
            <h3>تسجيل الدخول</h3>
            <input type="text" id="username" placeholder="اسمك (مثال: المحقق)" />
            <input type="text" id="room" placeholder="اسم الغرفة (مثال: Room1)" />
            <br>
            <button onclick="joinGame()">دخول اللعبة</button>
        </div>

        <div id="game-area">
            <div class="card">
                <div id="phase-icon"></div>
                <h2>غرفة: <span id="room-name"></span></h2>
                <div id="game-status" class="status">جاري الاتصال...</div>
                <div id="my-role" class="role-reveal hidden"></div>
                
                <div id="action-area"></div>
                
                <button id="start-btn" onclick="startGame()" class="hidden">👑 بدء اللعبة (يلزم 5+)</button>
                <button id="restart-btn" onclick="restartGame()" class="hidden action-btn">🔄 لعبة جديدة</button>
            </div>

            <div class="card">
                <h3>اللاعبون <span id="player-count"></span></h3>
                <div id="players-list"></div>
            </div>
            
            <div class="card">
                <h3>سجل الأحداث</h3>
                <div id="logs-container">
                    <div id="game-logs"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io({transports: ['websocket', 'polling']});
        let myName = "";
        let myRoom = "";
        let myRole = "";
        let amIAlive = true;

        window.onload = function() {
            if(localStorage.getItem('mafia_name')) document.getElementById('username').value = localStorage.getItem('mafia_name');
            if(localStorage.getItem('mafia_room')) document.getElementById('room').value = localStorage.getItem('mafia_room');
        };

        function joinGame() {
            myName = document.getElementById('username').value.trim();
            myRoom = document.getElementById('room').value.trim();
            if (!myName || !myRoom) return alert("أدخل الاسم والغرفة");
            
            localStorage.setItem('mafia_name', myName);
            localStorage.setItem('mafia_room', myRoom);

            socket.emit('join', {username: myName, room: myRoom});
            document.getElementById('login-area').style.display = 'none';
            document.getElementById('game-area').style.display = 'block';
            document.getElementById('room-name').innerText = myRoom;
        }

        function startGame() { socket.emit('start_game', {room: myRoom}); }
        
        function restartGame() {
            if(confirm("بدء لعبة جديدة؟")) socket.emit('restart_game', {room: myRoom});
        }

        function sendAction(target, actionType) {
            socket.emit('night_action', {room: myRoom, target: target, action: actionType});
            document.getElementById('action-area').innerHTML = "<h3>⏳ تم تسجيل اختيارك...</h3>";
        }
        
        function votePlayer(target) {
            if(confirm(`التصويت ضد ${target}؟`)) socket.emit('day_vote', {room: myRoom, target: target});
        }

        socket.on('error_msg', (msg) => alert(msg));
        socket.on('check_result', (msg) => alert(`🔍 المحقق:\n${msg}`));
        socket.on('game_over', (msg) => alert(msg));

        socket.on('update_state', (data) => {
            const body = document.body;
            const iconDiv = document.getElementById('phase-icon');
            
            if (data.phase === 'voting' || data.phase === 'lobby' || data.phase === 'game_over') {
                body.classList.add('day-theme'); 
                iconDiv.innerHTML = (data.phase === 'voting') ? "<div class='icon-sun'>☀️</div>" : "";
            } else {
                body.classList.remove('day-theme'); 
                iconDiv.innerHTML = "<div class='icon-moon'>🌙</div>";
            }

            const list = document.getElementById('players-list');
            list.innerHTML = "";
            document.getElementById('player-count').innerText = `(${data.players.length})`;
            
            const isHost = data.players.length > 0 && data.players[0].name === myName; 
            
            document.getElementById('start-btn').classList.add('hidden');
            document.getElementById('restart-btn').classList.add('hidden');

            if (isHost) {
                if (data.phase === 'lobby') document.getElementById('start-btn').classList.remove('hidden');
                else if (data.phase === 'game_over') document.getElementById('restart-btn').classList.remove('hidden');
            }

            document.getElementById('game-status').innerText = data.phase_display;

            const me = data.players.find(p => p.name === myName);
            const roleDiv = document.getElementById('my-role');
            
            if (me) {
                amIAlive = me.is_alive;
                if (me.role && data.phase !== 'lobby') {
                    roleDiv.classList.remove('hidden');
                    roleDiv.innerText = `الدور: ${me.role}`;
                    myRole = me.role;
                } else {
                    roleDiv.classList.add('hidden');
                }
            }

            const actionArea = document.getElementById('action-area');
            actionArea.innerHTML = "";
            
            if (data.phase === 'game_over') {
                actionArea.innerHTML = "<h3>🏁 انتهت اللعبة</h3>";
            }
            else if (!amIAlive) {
                 actionArea.innerHTML = "<h3 style='color:#c0392b'>💀 لقد تم إقصاؤك</h3>";
            } 
            else if (data.phase === 'night') {
                actionArea.innerHTML = "<h3>🌙 اختر هدفك</h3>";
                if (data.pending_action) {
                     actionArea.innerHTML = "<h3>⏳ بانتظار الآخرين...</h3>";
                } else {
                    if (myRole === 'مافيا') {
                        actionArea.innerHTML += "<p style='font-size:12px;color:#e74c3c'>* يجب الاتفاق على ضحية واحدة</p>";
                        data.players.forEach(p => {
                            if (p.is_alive && p.name !== myName) 
                                actionArea.innerHTML += `<button onclick="sendAction('${p.name}', 'kill')">🔫 ${p.name}</button>`;
                        });
                    }
                    else if (myRole === 'دكتور') {
                        data.players.forEach(p => {
                            if (p.is_alive) 
                                actionArea.innerHTML += `<button class='action-btn' onclick="sendAction('${p.name}', 'save')">💉 ${p.name}</button>`;
                        });
                    }
                    else if (myRole === 'الشايب') {
                        data.players.forEach(p => {
                            if (p.is_alive && p.name !== myName) 
                                actionArea.innerHTML += `<button class='action-btn' onclick="sendAction('${p.name}', 'check')">🔍 ${p.name}</button>`;
                        });
                    } else {
                        actionArea.innerHTML += "<p>نم بسلام...</p>";
                    }
                }
            } 
            else if (data.phase === 'voting') {
                actionArea.innerHTML = `<h3>☀️ التصويت (${data.votes_needed} للخروج)</h3>`;
                data.players.forEach(p => {
                    if (p.is_alive && p.name !== myName) {
                        let votes = data.current_votes[p.name] || 0;
                        actionArea.innerHTML += `<button class='vote-btn' onclick="votePlayer('${p.name}')">🗳️ ${p.name} (${votes})</button>`;
                    }
                });
            }

            data.players.forEach(p => {
                const item = document.createElement('div');
                item.className = `player-item ${p.is_alive ? 'alive' : 'dead'}`;
                let statusIcon = p.is_alive ? '🙂' : '💀';
                item.innerHTML = `<strong>${p.name}</strong> <span>${statusIcon}</span>`;
                list.appendChild(item);
            });
        });

        socket.on('log_message', (msg) => {
            const logs = document.getElementById('game-logs');
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `> ${msg}`;
            logs.prepend(div);
        });
    </script>
</body>
</html>
"""

# --- Backend Logic ---

class Game:
    def __init__(self):
        self.players = [] 
        self.phase = 'lobby' 
        self.night_actions = {'saves': [], 'checks': []}
        self.mafia_votes = {} 
        self.players_who_acted = set()
        self.votes = {}

    def reset_game(self):
        self.phase = 'lobby'
        self.night_actions = {'saves': [], 'checks': []}
        self.mafia_votes = {}
        self.players_who_acted = set()
        self.votes = {}
        for p in self.players:
            p['role'] = None
            p['is_alive'] = True

    def get_state(self, requester_sid=None):
        public_players = []
        for p in self.players:
            public_players.append({
                'name': p['name'],
                'is_alive': p['is_alive'],
                'role': p['role']
            })
        
        phase_ar = {
            'lobby': 'صالة الانتظار',
            'night': 'الليل 🌑',
            'voting': 'النهار (نقاش وتصويت) ☀️',
            'game_over': 'انتهت اللعبة 🏁'
        }
        
        current_votes_count = {}
        for target in self.votes.values():
            current_votes_count[target] = current_votes_count.get(target, 0) + 1
            
        alive_count = sum(1 for p in self.players if p['is_alive'])
        votes_needed = (alive_count // 2) + 1 if alive_count > 0 else 1

        pending_action = False
        if requester_sid:
             player = next((p for p in self.players if p['sid'] == requester_sid), None)
             if player and player['name'] in self.players_who_acted:
                 pending_action = True

        return {
            'players': public_players,
            'phase': self.phase,
            'phase_display': phase_ar.get(self.phase, self.phase),
            'current_votes': current_votes_count,
            'votes_needed': votes_needed,
            'pending_action': pending_action
        }

    def assign_roles(self):
        names = [p['name'] for p in self.players]
        num_players = len(names)
        
        if num_players < 5:
            return False, "يجب توفر 5 لاعبين على الأقل!"

        roles_pool = ['مافيا', 'مافيا', 'دكتور', 'الشايب']
        citizens_needed = num_players - len(roles_pool)
        roles_pool.extend(['مواطن'] * citizens_needed)
        
        random.shuffle(roles_pool)
        for i, p in enumerate(self.players):
            p['role'] = roles_pool[i]
            p['is_alive'] = True
        
        self.start_night()
        return True, "بدأت اللعبة!"

    def start_night(self):
        self.phase = 'night'
        self.night_actions = {'saves': [], 'checks': []}
        self.mafia_votes = {} 
        self.players_who_acted = set()
        self.votes = {} 

    def process_night_results(self):
        killed_name = None
        targets = list(self.mafia_votes.values())
        
        target_to_kill = None
        if targets:
            if all(t == targets[0] for t in targets): target_to_kill = targets[0]
            else: target_to_kill = None
        
        if target_to_kill:
            if target_to_kill in self.night_actions['saves']: killed_name = None 
            else:
                killed_name = target_to_kill
                for p in self.players:
                    if p['name'] == killed_name: p['is_alive'] = False
        
        self.phase = 'voting'
        return killed_name

    def check_win_condition(self):
        mafia_alive = sum(1 for p in self.players if p['is_alive'] and p['role'] == 'مافيا')
        citizens_alive = sum(1 for p in self.players if p['is_alive'] and p['role'] != 'مافيا')
        
        # 1. فوز المواطنين: إذا مات جميع المافيا
        if mafia_alive == 0: 
            return 'citizens'
            
        # 2. فوز المافيا: إذا بقي مواطن واحد فقط (أو أقل)
        # هذا الشرط يشمل الحالات التي يتساوى فيها المافيا مع المواطنين 
        # لأن (مواطن واحد) يعني أن المافيا (2 على الأقل) يستطيعون السيطرة
        if citizens_alive <= 1: 
            return 'mafia'
            
        return None

games = {}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    if room not in games: games[room] = Game()
    game = games[room]
    
    existing_player = next((p for p in game.players if p['name'] == username), None)
    
    if existing_player:
        existing_player['sid'] = request.sid
        emit('log_message', f"عودة {username}", to=request.sid)
    else:
        if game.phase != 'lobby':
            emit('error_msg', "اللعبة جارية!", to=request.sid)
            return
        game.players.append({'name': username, 'role': None, 'is_alive': True, 'sid': request.sid})
        emit('log_message', f"انضم {username}", room=room)
    
    emit('update_state', game.get_state(request.sid), room=room)

@socketio.on('start_game')
def on_start(data):
    room = data['room']
    if room in games:
        game = games[room]
        success, msg = game.assign_roles()
        if success:
            emit('update_state', game.get_state(), room=room)
            emit('log_message', "🔔 <span class='highlight'>بدأ الليل...</span>", room=room)
        else:
            emit('error_msg', msg, to=request.sid)

@socketio.on('restart_game')
def on_restart(data):
    room = data['room']
    if room in games:
        game = games[room]
        game.reset_game()
        emit('update_state', game.get_state(), room=room)
        emit('log_message', "🔄 <span class='highlight'>إعادة اللعب!</span>", room=room)

@socketio.on('night_action')
def on_action(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'night': return
    
    action = data['action']
    target = data['target']
    player = next((p for p in game.players if p['sid'] == request.sid), None)
    if not player or not player['is_alive']: return

    if action == 'kill' and player['role'] == 'مافيا':
        game.mafia_votes[player['name']] = target
    elif action == 'save': game.night_actions['saves'].append(target)
    elif action == 'check': 
        target_role = next((p['role'] for p in game.players if p['name'] == target), 'مواطن')
        result = "😈 مافيا!" if target_role == 'مافيا' else "😇 بريء."
        emit('check_result', result, to=request.sid)
    
    game.players_who_acted.add(player['name'])
    emit('update_state', game.get_state(request.sid), to=request.sid)

    roles_needed = [p['name'] for p in game.players if p['is_alive'] and p['role'] in ['مافيا', 'دكتور', 'الشايب']]
    
    if all(name in game.players_who_acted for name in roles_needed):
        socketio.sleep(1)
        dead_person = game.process_night_results()
        
        msg = ""
        mafia_targets = list(game.mafia_votes.values())
        if mafia_targets and not all(t == mafia_targets[0] for t in mafia_targets):
             msg = "☀️ طلع الصباح! لم يمت أحد (نجاة بأعجوبة)"
        else:
             msg = f"☀️ مات: <span class='highlight'>{dead_person}</span>" if dead_person else "☀️ طلع الصباح! لم يمت أحد"

        emit('log_message', msg, room=room)
        
        winner = game.check_win_condition()
        if winner:
            game.phase = 'game_over'
            end_msg = "🎉 فاز المواطنون!" if winner == 'citizens' else "😈 فازت المافيا!"
            emit('log_message', end_msg, room=room)
            emit('game_over', end_msg, room=room)
            emit('update_state', game.get_state(), room=room)
        else:
            emit('update_state', game.get_state(), room=room)

@socketio.on('day_vote')
def on_vote(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'voting': return

    target = data['target']
    voter = next((p for p in game.players if p['sid'] == request.sid), None)
    if not voter or not voter['is_alive']: return

    game.votes[voter['name']] = target
    emit('update_state', game.get_state(), room=room)
    
    vote_counts = {}
    for t in game.votes.values(): vote_counts[t] = vote_counts.get(t, 0) + 1
    
    required = (sum(1 for p in game.players if p['is_alive']) // 2) + 1
    if vote_counts.get(target, 0) >= required:
        executed_player = next((p for p in game.players if p['name'] == target), None)
        if executed_player:
            executed_player['is_alive'] = False
            emit('log_message', f"⚖️ تم إعدام <span class='highlight'>{target}</span>!", room=room)
            
            winner = game.check_win_condition()
            if winner:
                game.phase = 'game_over'
                end_msg = "🎉 فاز المواطنون!" if winner == 'citizens' else "😈 فازت المافيا!"
                emit('log_message', end_msg, room=room)
                emit('game_over', end_msg, room=room)
            else:
                game.start_night()
                socketio.sleep(3)
                emit('log_message', "🌑 حل الظلام...", room=room)
            emit('update_state', game.get_state(), room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
