import random
import time
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mafia_classic_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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
        :root { --bg-color: #121212; --card-bg: #1e1e1e; --text-color: #e0e0e0; --accent-color: #c0392b; --admin-color: #8e44ad; }
        body.day-theme { --bg-color: #f0f2f5; --card-bg: #ffffff; --text-color: #2c3e50; --accent-color: #2980b9; }
        body { font-family: 'Tajawal', sans-serif; background-color: var(--bg-color); color: var(--text-color); text-align: center; padding: 20px; margin: 0; transition: background-color 1s ease; }
        .container { max-width: 600px; margin: 0 auto; }
        .card { background: var(--card-bg); padding: 25px; border-radius: 15px; margin: 15px auto; box-shadow: 0 8px 20px rgba(0,0,0,0.2); }
        h1 { color: var(--accent-color); margin-bottom: 10px; }
        button { background: var(--accent-color); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 5px; width: 100%; max-width: 300px; font-weight: bold; }
        button.admin-btn { background: var(--admin-color); border: 2px solid #fff; }
        button:hover { filter: brightness(1.1); transform: translateY(-2px); }
        input[type="text"] { padding: 15px; width: 80%; margin-bottom: 10px; border-radius: 8px; border: 1px solid #555; background: #333; color: white; }
        .checkbox-container { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 15px; padding: 10px; background: rgba(142, 68, 173, 0.2); border-radius: 8px; }
        .role-reveal { font-size: 20px; color: #f1c40f; margin: 15px 0; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; }
        .player-item { padding: 10px; margin: 5px 0; border-radius: 5px; background: rgba(128,128,128,0.1); display: flex; justify-content: space-between; align-items: center; }
        .player-item.dead { text-decoration: line-through; opacity: 0.6; background: rgba(192, 57, 43, 0.2); }
        .role-badge { font-size: 0.8em; padding: 2px 6px; border-radius: 4px; background: #555; color: #fff; margin-right: 5px; }
        #logs-container { height: 200px; overflow-y: auto; text-align: right; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; }
        .log-entry { font-size: 14px; margin-bottom: 5px; border-bottom: 1px solid #444; }
        .admin-panel { border: 2px solid var(--admin-color); padding: 10px; border-radius: 10px; margin-bottom: 20px; display: none;}
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MAFIA 🎩</h1>

        <!-- شاشة الدخول -->
        <div id="login-area" class="card">
            <h3>تسجيل الدخول</h3>
            <input type="text" id="username" placeholder="الاسم" />
            <input type="text" id="room" placeholder="اسم الغرفة" oninput="checkAdminStatus()" />
            
            <div id="admin-option" class="checkbox-container hidden">
                <input type="checkbox" id="is-admin-check">
                <label for="is-admin-check">دخول كمشرف (Admin) 🛠️</label>
            </div>

            <button onclick="joinGame()">دخول</button>
        </div>

        <!-- منطقة اللعبة -->
        <div id="game-area" class="hidden">
            
            <!-- لوحة المشرف -->
            <div id="admin-controls" class="admin-panel">
                <h3 style="color:var(--admin-color)">🛠️ لوحة تحكم المشرف</h3>
                <p>أنت تدير هذه اللعبة.</p>
                <button onclick="startGame()" class="admin-btn">👑 بدء اللعبة</button>
                <button onclick="restartGame()" class="admin-btn">🔄 إعادة اللعبة</button>
            </div>

            <div class="card">
                <div id="phase-icon"></div>
                <h2>غرفة: <span id="room-name"></span></h2>
                <div id="game-status" class="status"></div>
                <div id="my-role" class="role-reveal hidden"></div>
                <div id="action-area"></div>
            </div>

            <div class="card">
                <h3>اللاعبون <span id="player-count"></span></h3>
                <div id="players-list"></div>
            </div>
            
            <div class="card">
                <h3>سجل الأحداث</h3>
                <div id="logs-container"><div id="game-logs"></div></div>
            </div>
        </div>
    </div>

    <script>
        const socket = io({transports: ['websocket', 'polling']});
        let myName = "";
        let myRoom = "";
        let amIAdmin = false;

        function checkAdminStatus() {
            const roomName = document.getElementById('room').value.trim();
            if(roomName.length > 2) socket.emit('check_admin_exists', {room: roomName});
            else document.getElementById('admin-option').classList.add('hidden');
        }

        socket.on('admin_status', (data) => {
            const adminDiv = document.getElementById('admin-option');
            if (data.exists) {
                adminDiv.classList.add('hidden');
                document.getElementById('is-admin-check').checked = false;
            } else {
                adminDiv.classList.remove('hidden');
            }
        });

        function joinGame() {
            myName = document.getElementById('username').value.trim();
            myRoom = document.getElementById('room').value.trim();
            amIAdmin = document.getElementById('is-admin-check').checked;

            if (!myName || !myRoom) return alert("البيانات ناقصة");

            socket.emit('join', {username: myName, room: myRoom, is_admin: amIAdmin});
            
            document.getElementById('login-area').style.display = 'none';
            document.getElementById('game-area').style.display = 'block';
            document.getElementById('room-name').innerText = myRoom;

            // إظهار لوحة التحكم فوراً إذا كنت مشرفاً
            if (amIAdmin) {
                document.getElementById('admin-controls').style.display = 'block';
                document.getElementById('action-area').innerHTML = "<p><em>أنت تراقب اللعبة...</em></p>";
            }
        }

        function startGame() { socket.emit('start_game', {room: myRoom}); }
        function restartGame() { if(confirm("هل أنت متأكد؟")) socket.emit('restart_game', {room: myRoom}); }
        function sendAction(target, actionType) { socket.emit('night_action', {room: myRoom, target: target, action: actionType}); }
        function votePlayer(target) { if(confirm(`التصويت ضد ${target}؟`)) socket.emit('day_vote', {room: myRoom, target: target}); }

        socket.on('error_msg', (msg) => alert(msg));
        socket.on('check_result', (msg) => alert(`🔍 نتيجة الفحص:\n${msg}`));
        socket.on('action_confirmed', () => document.getElementById('action-area').innerHTML = "<h3>✅ تم التسجيل</h3>");
        
        socket.on('log_message', (msg) => {
            const logs = document.getElementById('game-logs');
            logs.innerHTML = `<div class="log-entry">> ${msg}</div>` + logs.innerHTML;
        });

        socket.on('update_state', (data) => {
            // تحديث الثيم
            if (data.phase === 'voting' || data.phase === 'lobby') {
                document.body.classList.add('day-theme');
                document.getElementById('phase-icon').innerHTML = "☀️";
            } else {
                document.body.classList.remove('day-theme');
                document.getElementById('phase-icon').innerHTML = "🌙";
            }

            document.getElementById('game-status').innerText = data.phase_display;
            document.getElementById('player-count').innerText = `(${data.players.length})`;

            // تحديث قائمة اللاعبين
            const list = document.getElementById('players-list');
            list.innerHTML = "";
            data.players.forEach(p => {
                const item = document.createElement('div');
                item.className = `player-item ${p.is_alive ? '' : 'dead'}`;
                
                // المشرف يرى كل الأدوار، اللاعب يرى دوره فقط (الذي يأتي من السيرفر)
                let roleDisplay = "";
                if (data.is_admin && p.role) {
                     roleDisplay = `<span class="role-badge" style="background:${getRoleColor(p.role)}">${p.role}</span>`;
                }
                
                item.innerHTML = `
                    <div>${roleDisplay} <strong>${p.name}</strong></div>
                    <div>${p.is_alive ? '🙂' : '💀'}</div>
                `;
                list.appendChild(item);
            });

            // تحديث منطقة الأكشن للاعبين فقط
            if (!amIAdmin) {
                const me = data.players.find(p => p.name === myName);
                const roleDiv = document.getElementById('my-role');
                const actionArea = document.getElementById('action-area');
                actionArea.innerHTML = "";

                if (me) {
                    if (me.role && data.phase !== 'lobby') {
                        roleDiv.classList.remove('hidden');
                        roleDiv.innerText = `أنت: ${me.role}`;
                        
                        // رسم الأزرار بناءً على الدور
                        if (!me.is_alive) {
                            actionArea.innerHTML = "<h3 style='color:#c0392b'>لقد تم إقصاؤك 💀</h3>";
                        } 
                        else if (data.phase === 'night') {
                            if (data.pending_action) {
                                actionArea.innerHTML = "<h3>⏳ بانتظار البقية...</h3>";
                            } else {
                                renderNightButtons(actionArea, data.players, me.role);
                            }
                        } 
                        else if (data.phase === 'voting') {
                            actionArea.innerHTML = `<h3>🗳️ التصويت (${data.votes_needed} للخروج)</h3>`;
                            data.players.forEach(p => {
                                if (p.is_alive && p.name !== myName) {
                                    let v = data.current_votes[p.name] || 0;
                                    actionArea.innerHTML += `<button class="vote-btn" onclick="votePlayer('${p.name}')">${p.name} (${v})</button>`;
                                }
                            });
                        }
                    } else {
                        roleDiv.classList.add('hidden');
                        if (data.phase === 'lobby') actionArea.innerHTML = "<p>بانتظار المشرف لبدء اللعبة...</p>";
                    }
                }
            }
        });

        function renderNightButtons(container, players, role) {
            if (role === 'مافيا') {
                container.innerHTML = "<h3>🔫 اختر الضحية</h3>";
                players.forEach(p => {
                    if (p.is_alive && p.name !== myName) 
                        container.innerHTML += `<button onclick="sendAction('${p.name}', 'kill')">${p.name}</button>`;
                });
            } else if (role === 'دكتور') {
                container.innerHTML = "<h3>💉 اختر شخصاً لحمايته</h3>";
                players.forEach(p => {
                    if (p.is_alive) 
                        container.innerHTML += `<button class="action-btn" onclick="sendAction('${p.name}', 'save')">${p.name}</button>`;
                });
            } else if (role === 'الشايب') {
                container.innerHTML = "<h3>🔍 اختر شخصاً لكشفه</h3>";
                players.forEach(p => {
                    if (p.is_alive && p.name !== myName) 
                        container.innerHTML += `<button class="action-btn" onclick="sendAction('${p.name}', 'check')">${p.name}</button>`;
                });
            } else {
                container.innerHTML = "<h3>💤 نم بسلام...</h3>";
            }
        }

        function getRoleColor(role) {
            if(role === 'مافيا') return '#c0392b';
            if(role === 'دكتور') return '#27ae60';
            if(role === 'الشايب') return '#f39c12';
            return '#7f8c8d';
        }
    </script>
</body>
</html>
"""

class Game:
    def __init__(self):
        self.players = [] 
        self.admin_sid = None
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
        is_admin = (requester_sid == self.admin_sid)
        
        public_players = []
        for p in self.players:
            # إذا كان هو المشرف، أو هو اللاعب نفسه، نرسل الدور
            role_to_show = p['role'] if (is_admin or p['sid'] == requester_sid) else None
            
            public_players.append({
                'name': p['name'],
                'is_alive': p['is_alive'],
                'role': role_to_show 
            })
        
        phase_ar = {'lobby': 'صالة الانتظار', 'night': 'الليل 🌑', 'voting': 'النهار ☀️', 'game_over': 'نهاية اللعبة 🏁'}
        
        current_votes_count = {}
        for target in self.votes.values():
            current_votes_count[target] = current_votes_count.get(target, 0) + 1
            
        alive_count = sum(1 for p in self.players if p['is_alive'])
        votes_needed = (alive_count // 2) + 1 if alive_count > 0 else 1

        pending_action = False
        if requester_sid and not is_admin:
             player = next((p for p in self.players if p['sid'] == requester_sid), None)
             if player and player['name'] in self.players_who_acted:
                 pending_action = True

        return {
            'players': public_players,
            'phase': self.phase,
            'phase_display': phase_ar.get(self.phase, self.phase),
            'current_votes': current_votes_count,
            'votes_needed': votes_needed,
            'pending_action': pending_action,
            'is_admin': is_admin
        }

    def assign_roles(self):
        names = [p['name'] for p in self.players]
        if len(names) < 5: return False, "يجب توفر 5 لاعبين على الأقل!"

        roles_pool = ['مافيا', 'مافيا', 'دكتور', 'الشايب']
        citizens_needed = len(names) - len(roles_pool)
        roles_pool.extend(['مواطن'] * citizens_needed)
        
        random.shuffle(roles_pool)
        for i, p in enumerate(self.players):
            p['role'] = roles_pool[i]
            p['is_alive'] = True
        
        self.start_night()
        return True, "تم توزيع الأدوار!"

    def start_night(self):
        self.phase = 'night'
        self.night_actions = {'saves': [], 'checks': []}
        self.mafia_votes = {} 
        self.players_who_acted = set()
        self.votes = {} 

    def process_night_results(self):
        killed_name = None
        targets = list(self.mafia_votes.values())
        if targets and all(t == targets[0] for t in targets):
            target_to_kill = targets[0]
            if target_to_kill not in self.night_actions['saves']:
                killed_name = target_to_kill
                for p in self.players:
                    if p['name'] == killed_name: p['is_alive'] = False
        
        self.phase = 'voting'
        return killed_name

    def check_win_condition(self):
        mafia = sum(1 for p in self.players if p['is_alive'] and p['role'] == 'مافيا')
        citizens = sum(1 for p in self.players if p['is_alive'] and p['role'] != 'مافيا')
        if mafia == 0: return 'citizens'
        if citizens <= 1: return 'mafia'
        return None

games = {}

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@socketio.on('check_admin_exists')
def on_check_admin(data):
    room = data['room']
    has_admin = (room in games and games[room].admin_sid is not None)
    emit('admin_status', {'exists': has_admin}, to=request.sid)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    is_admin = data.get('is_admin', False)
    
    join_room(room)
    if room not in games: games[room] = Game()
    game = games[room]
    
    if is_admin:
        if game.admin_sid is not None:
             emit('error_msg', "يوجد مشرف بالفعل!", to=request.sid)
             return
        game.admin_sid = request.sid
        emit('log_message', f"🛡️ المشرف {username} انضم", room=room)
    else:
        existing = next((p for p in game.players if p['name'] == username), None)
        if existing:
            existing['sid'] = request.sid
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
    game = games.get(room)
    if not game or request.sid != game.admin_sid: return
    success, msg = game.assign_roles()
    if success:
        # تحديث للجميع (اللاعبين + المشرف)
        emit('update_state', game.get_state(), room=room) 
        # تحديث خاص للمشرف ليرى الأدوار فوراً
        emit('update_state', game.get_state(game.admin_sid), to=game.admin_sid)
        emit('log_message', "🔔 بدأت اللعبة!", room=room)
    else:
        emit('error_msg', msg, to=request.sid)

@socketio.on('restart_game')
def on_restart(data):
    room = data['room']
    game = games.get(room)
    if not game or request.sid != game.admin_sid: return
    game.reset_game()
    emit('update_state', game.get_state(), room=room)
    emit('update_state', game.get_state(game.admin_sid), to=game.admin_sid)
    emit('log_message', "🔄 تصفير اللعبة!", room=room)

@socketio.on('night_action')
def on_action(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'night': return
    
    player = next((p for p in game.players if p['sid'] == request.sid), None)
    if not player or not player['is_alive']: return

    action = data['action']
    target = data['target']

    if action == 'kill' and player['role'] == 'مافيا':
        t_p = next((p for p in game.players if p['name'] == target), None)
        if t_p and t_p['role'] == 'مافيا':
             emit('error_msg', "لا تقتل زميلك!", to=request.sid)
             return
        game.mafia_votes[player['name']] = target
    elif action == 'save': game.night_actions['saves'].append(target)
    elif action == 'check': 
        t_p = next((p for p in game.players if p['name'] == target), None)
        res = "😈 مافيا!" if t_p and t_p['role'] == 'مافيا' else "😇 بريء."
        emit('check_result', res, to=request.sid)

    game.players_who_acted.add(player['name'])
    emit('action_confirmed', to=request.sid)
    
    # تحديث اللاعب (لإظهار الانتظار) وتحديث المشرف (ليرى التقدم)
    emit('update_state', game.get_state(request.sid), to=request.sid)
    if game.admin_sid: emit('update_state', game.get_state(game.admin_sid), to=game.admin_sid)

    roles = [p['name'] for p in game.players if p['is_alive'] and p['role'] in ['مافيا', 'دكتور', 'الشايب']]
    if all(name in game.players_who_acted for name in roles):
        socketio.sleep(1)
        dead = game.process_night_results()
        msg = f"☀️ مات: {dead}" if dead else "☀️ لم يمت أحد"
        emit('log_message', msg, room=room)
        
        win = game.check_win_condition()
        if win:
            game.phase = 'game_over'
            emit('log_message', f"🎉 الفائز: {win}", room=room)
        
        # تحديث جماعي للجميع (يخفي الأدوار)
        emit('update_state', game.get_state(), room=room)
        # تحديث خاص للمشرف (يظهر الأدوار)
        if game.admin_sid: emit('update_state', game.get_state(game.admin_sid), to=game.admin_sid)

@socketio.on('day_vote')
def on_vote(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'voting': return
    
    player = next((p for p in game.players if p['sid'] == request.sid), None)
    if not player or not player['is_alive']: return

    game.votes[player['name']] = data['target']
    
    emit('update_state', game.get_state(), room=room)
    if game.admin_sid: emit('update_state', game.get_state(game.admin_sid), to=game.admin_sid)

    counts = {}
    for t in game.votes.values(): counts[t] = counts.get(t, 0) + 1
    
    alive = sum(1 for p in game.players if p['is_alive'])
    needed = (alive // 2) + 1
    
    for t, c in counts.items():
        if c >= needed:
            for p in game.players:
                if p['name'] == t: p['is_alive'] = False
            emit('log_message', f"⚖️ إعدام: {t}", room=room)
            
            win = game.check_win_condition()
            if win:
                game.phase = 'game_over'
                emit('log_message', f"🎉 الفائز: {win}", room=room)
            else:
                game.start_night()
                emit('log_message', "🔔 الليل...", room=room)
            
            emit('update_state', game.get_state(), room=room)
            if game.admin_sid: emit('update_state', game.get_state(game.admin_sid), to=game.admin_sid)
            break

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
