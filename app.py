import random
import time
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'falcons_secret_key_123'
# تفعيل eventlet لدعم الـ WebSockets بشكل صحيح
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- HTML Template (الواجهة) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مافيا فالكونز 🦅</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; text-align: center; padding: 20px; margin: 0; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 12px; margin: 15px auto; max-width: 500px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #333; }
        h1 { color: #2ecc71; text-shadow: 0 0 10px rgba(46, 204, 113, 0.3); }
        button { background: #27ae60; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 5px; transition: all 0.3s; font-weight: bold; width: 100%; max-width: 300px; }
        button:hover { background: #219150; transform: translateY(-2px); }
        button:disabled { background: #555; cursor: not-allowed; transform: none; opacity: 0.6; }
        button.vote-btn { background: #c0392b; }
        button.vote-btn:hover { background: #a93226; }
        button.action-btn { background: #f39c12; color: #000; }
        input { padding: 12px; border-radius: 8px; border: 1px solid #444; background: #2c2c2c; color: white; width: 80%; margin-bottom: 10px; font-size: 16px; }
        .role-reveal { font-size: 24px; font-weight: bold; color: #f1c40f; margin: 20px 0; padding: 15px; background: rgba(241, 196, 15, 0.1); border-radius: 8px; border: 1px solid #f1c40f; }
        .status { color: #aaa; font-size: 14px; margin-bottom: 10px; font-weight: bold; }
        #game-area { display: none; }
        .hidden { display: none; }
        .player-item { padding: 12px; background: #2c2c2c; margin: 8px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border-left: 5px solid #555; }
        .player-item.alive { border-left-color: #27ae60; }
        .player-item.dead { border-left-color: #c0392b; opacity: 0.6; text-decoration: line-through; }
        #logs-container { max-height: 250px; overflow-y: auto; text-align: right; background: #000; padding: 10px; border-radius: 5px; font-size: 13px; font-family: monospace; border: 1px solid #333; }
        .log-entry { margin-bottom: 5px; border-bottom: 1px solid #222; padding-bottom: 2px; }
        .highlight { color: #f1c40f; }
    </style>
</head>
<body>
    <h1>🦅 مافيا فالكونز</h1>

    <!-- Login Area -->
    <div id="login-area" class="card">
        <h3>تسجيل الدخول</h3>
        <input type="text" id="username" placeholder="اسمك (مثال: عادل)" />
        <input type="text" id="room" placeholder="اسم الغرفة (مثال: Falcons1)" />
        <br><br>
        <button onclick="joinGame()">🚀 دخول اللعبة</button>
    </div>

    <!-- Game Area -->
    <div id="game-area">
        <div class="card">
            <h2>غرفة: <span id="room-name"></span></h2>
            <div id="game-status" class="status">جاري الاتصال...</div>
            <div id="my-role" class="role-reveal hidden"></div>
            
            <div id="action-area"></div>
            
            <button id="start-btn" onclick="startGame()" class="hidden">👑 بدء اللعبة (للمشرف)</button>
        </div>

        <div class="card">
            <h3>👥 اللاعبون <span id="player-count"></span></h3>
            <div id="players-list"></div>
        </div>
        
        <div class="card">
            <h3>📜 الأحداث</h3>
            <div id="logs-container">
                <div id="game-logs"></div>
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
            if (!myName || !myRoom) return alert("الرجاء إدخال الاسم واسم الغرفة");
            
            localStorage.setItem('mafia_name', myName);
            localStorage.setItem('mafia_room', myRoom);

            socket.emit('join', {username: myName, room: myRoom});
            document.getElementById('login-area').style.display = 'none';
            document.getElementById('game-area').style.display = 'block';
            document.getElementById('room-name').innerText = myRoom;
        }

        function startGame() {
            if(confirm("هل أنت متأكد من بدء اللعبة؟")) {
                socket.emit('start_game', {room: myRoom});
            }
        }

        function sendAction(target, actionType) {
            socket.emit('night_action', {room: myRoom, target: target, action: actionType});
            document.getElementById('action-area').innerHTML = "<h3>⏳ تم إرسال أمرك... في انتظار باقي الأدوار</h3>";
        }
        
        function votePlayer(target) {
            if(confirm(`هل تريد التصويت لإعدام ${target}؟`)) {
                socket.emit('day_vote', {room: myRoom, target: target});
            }
        }

        socket.on('error_msg', (msg) => alert(msg));
        
        socket.on('check_result', (msg) => {
            alert(`🔍 نتيجة تحقيق الشايب:\n${msg}`);
        });

        socket.on('game_over', (msg) => {
             alert(msg);
             location.reload();
        });

        socket.on('update_state', (data) => {
            const list = document.getElementById('players-list');
            list.innerHTML = "";
            document.getElementById('player-count').innerText = `(${data.players.length})`;
            
            const isHost = data.players.length > 0 && data.players[0].name === myName; 
            
            if (isHost && data.phase === 'lobby') {
                document.getElementById('start-btn').classList.remove('hidden');
            } else {
                document.getElementById('start-btn').classList.add('hidden');
            }

            document.getElementById('game-status').innerText = `المرحلة: ${data.phase_display}`;

            // My State
            const me = data.players.find(p => p.name === myName);
            const roleDiv = document.getElementById('my-role');
            
            if (me) {
                amIAlive = me.is_alive;
                if (me.role && data.phase !== 'lobby') {
                    roleDiv.classList.remove('hidden');
                    roleDiv.innerText = `أنت: ${me.role}`;
                    myRole = me.role;
                } else {
                    roleDiv.classList.add('hidden');
                }
            }

            // Action Area Logic
            const actionArea = document.getElementById('action-area');
            actionArea.innerHTML = "";
            
            if (!amIAlive) {
                 actionArea.innerHTML = "<h3 style='color:#c0392b'>💀 لقد تم إقصاؤك (ميت)</h3><p>تابع اللعبة بصمت.</p>";
            } else if (data.phase === 'night') {
                actionArea.innerHTML = "<h3>🌙 الليل: قم بمهمتك السرية</h3>";
                
                // التأكد هل قمت بالفعل بدوري؟ (لتجنب التكرار)
                if (data.pending_action) {
                     actionArea.innerHTML = "<h3>⏳ تم تسجيل اختيارك، بانتظار البقية...</h3>";
                } else {
                    if (myRole === 'مافيا') {
                        actionArea.innerHTML += "<p style='color:#e74c3c'>اختر ضحية للاغتيال:</p>";
                        data.players.forEach(p => {
                            if (p.is_alive && p.name !== myName) {
                                actionArea.innerHTML += `<button class='vote-btn' onclick="sendAction('${p.name}', 'kill')">🔫 ${p.name}</button>`;
                            }
                        });
                    }
                    else if (myRole === 'دكتور') {
                        actionArea.innerHTML += "<p style='color:#3498db'>اختر شخصاً لإنقاذه:</p>";
                        data.players.forEach(p => {
                            if (p.is_alive) {
                                actionArea.innerHTML += `<button class='action-btn' onclick="sendAction('${p.name}', 'save')">💉 ${p.name}</button>`;
                            }
                        });
                    }
                    else if (myRole === 'الشايب') {
                        actionArea.innerHTML += "<p style='color:#f39c12'>اختر شخصاً للكشف عنه:</p>";
                        data.players.forEach(p => {
                            if (p.is_alive && p.name !== myName) {
                                actionArea.innerHTML += `<button class='action-btn' onclick="sendAction('${p.name}', 'check')">🔍 ${p.name}</button>`;
                            }
                        });
                    } else {
                        actionArea.innerHTML += "<p>أنت مواطن، نم بسلام وانتظر الصباح.</p>";
                    }
                }

            } else if (data.phase === 'voting') {
                actionArea.innerHTML = `<h3>☀️ النهار: التصويت (${data.votes_needed} أصوات للإقصاء)</h3>`;
                data.players.forEach(p => {
                    if (p.is_alive && p.name !== myName) {
                        // إظهار عدد الأصوات الحالية لكل لاعب
                        let votes = data.current_votes[p.name] || 0;
                        actionArea.innerHTML += `<button class='vote-btn' onclick="votePlayer('${p.name}')">🗳️ ${p.name} (${votes})</button>`;
                    }
                });
            }

            // Players List
            data.players.forEach(p => {
                const item = document.createElement('div');
                item.className = `player-item ${p.is_alive ? 'alive' : 'dead'}`;
                let statusIcon = p.is_alive ? '💚' : '💀';
                item.innerHTML = `<strong>${p.name}</strong> <span>${statusIcon}</span>`;
                list.appendChild(item);
            });
        });

        socket.on('log_message', (msg) => {
            const logs = document.getElementById('game-logs');
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `> ${msg}`; // innerHTML للسماح بتنسيق الألوان
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
        self.night_actions = {'kills': [], 'saves': [], 'checks': []}
        # لتتبع من قام بدوره في الليل لتجنب إنهاء الليل مبكراً
        self.players_who_acted = set()
        self.votes = {}

    def get_state(self, requester_sid=None):
        public_players = []
        for p in self.players:
            public_players.append({
                'name': p['name'],
                'is_alive': p['is_alive'],
                'role': p['role'] # الفلترة تتم في الفرونت إند، أو يمكن فلترتها هنا لمزيد من الأمان
            })
        
        phase_ar = {
            'lobby': 'الانتظار في اللوبي',
            'night': 'الليل 🌑',
            'voting': 'النهار والتصويت ☀️',
            'game_over': 'انتهت اللعبة'
        }
        
        # حساب الأصوات الحالية للعرض
        current_votes_count = {}
        for target in self.votes.values():
            current_votes_count[target] = current_votes_count.get(target, 0) + 1
            
        alive_count = sum(1 for p in self.players if p['is_alive'])
        votes_needed = (alive_count // 2) + 1 if alive_count > 0 else 1

        # هل قام هذا اللاعب بفعله؟
        pending_action = False
        if requester_sid:
             # البحث عن اسم اللاعب
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
        random.shuffle(names)
        
        roles_dist = {}
        count = len(names)
        
        # توزيع متوازن
        if count >= 1: roles_dist[names[0]] = 'مافيا'
        if count >= 3: roles_dist[names[1]] = 'دكتور'
        if count >= 4: roles_dist[names[2]] = 'الشايب'
        if count >= 7: roles_dist[names[3]] = 'مافيا' # مافيا ثاني للعدد الكبير
        
        for p in self.players:
            p['role'] = roles_dist.get(p['name'], 'مواطن')
            p['is_alive'] = True
        
        self.start_night()

    def start_night(self):
        self.phase = 'night'
        self.night_actions = {'kills': [], 'saves': [], 'checks': []}
        self.players_who_acted = set()
        self.votes = {} # تصفية أصوات النهار السابق

    def process_night_results(self):
        # 1. القتل
        killed_name = None
        # إذا تعددت أصوات المافيا نأخذ آخر واحد (أو الأول)، للتبسيط نأخذ آخر قرار
        target_to_kill = self.night_actions['kills'][-1] if self.night_actions['kills'] else None
        
        if target_to_kill:
            # 2. الإنقاذ
            # هل الدكتور حمى هذا الشخص؟
            if target_to_kill in self.night_actions['saves']:
                killed_name = None # نجى
            else:
                killed_name = target_to_kill
                for p in self.players:
                    if p['name'] == killed_name:
                        p['is_alive'] = False
        
        self.phase = 'voting'
        return killed_name

    def check_win_condition(self):
        mafia_alive = sum(1 for p in self.players if p['is_alive'] and p['role'] == 'مافيا')
        citizens_alive = sum(1 for p in self.players if p['is_alive'] and p['role'] != 'مافيا')
        
        if mafia_alive == 0:
            return 'citizens'
        if mafia_alive >= citizens_alive:
            return 'mafia'
        return None

# --- Global Storage ---
games = {}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    if room not in games:
        games[room] = Game()
    
    game = games[room]
    existing_player = next((p for p in game.players if p['name'] == username), None)
    
    if existing_player:
        existing_player['sid'] = request.sid
        emit('log_message', f"مرحباً بعودتك يا {username}!", to=request.sid)
    else:
        if game.phase != 'lobby':
            emit('error_msg', "عذراً، اللعبة بدأت!", to=request.sid)
            return
        game.players.append({'name': username, 'role': None, 'is_alive': True, 'sid': request.sid})
        emit('log_message', f"انضم {username} للغرفة", room=room)
    
    emit('update_state', game.get_state(request.sid), room=room)

@socketio.on('start_game')
def on_start(data):
    room = data['room']
    if room in games:
        game = games[room]
        if len(game.players) < 3: # يمكنك تغيير هذا للعدد الأدنى
             emit('error_msg', "تحتاج 3 لاعبين على الأقل!", to=request.sid)
             return
        game.assign_roles()
        emit('update_state', game.get_state(), room=room)
        emit('log_message', "🔔 <span class='highlight'>بدأت اللعبة! حل الظلام...</span>", room=room)

@socketio.on('night_action')
def on_action(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'night': return
    
    action = data['action']
    target = data['target']
    
    # معرفة اللاعب الذي قام بالأكشن
    player = next((p for p in game.players if p['sid'] == request.sid), None)
    if not player or not player['is_alive']: return

    # تسجيل الأكشن
    if action == 'kill' and player['role'] == 'mafia': # في الكود استخدمت 'مافيا' بالعربي
        pass # سيتم التحقق بالأسفل
    
    # تحديث القوائم
    if action == 'kill': game.night_actions['kills'].append(target)
    elif action == 'save': game.night_actions['saves'].append(target)
    elif action == 'check': 
        # الشايب يحصل على نتيجة فورية (لكن لا ينتهي الليل)
        target_role = next((p['role'] for p in game.players if p['name'] == target), 'مواطن')
        result = "😈 هذا الشخص مافيا!" if target_role == 'مافيا' else "😇 هذا الشخص بريء."
        emit('check_result', result, to=request.sid)
    
    # تسجيل أن هذا اللاعب انتهى
    game.players_who_acted.add(player['name'])
    
    # إخبار اللاعب أنه تم قبول دوره
    emit('update_state', game.get_state(request.sid), to=request.sid)

    # التحقق: هل انتهى الليل؟
    # يجب أن يقوم المافيا (الأحياء) والدكتور (إذا حي) والشايب (إذا حي) بأدوارهم
    roles_needed = []
    for p in game.players:
        if p['is_alive']:
            if p['role'] == 'مافيا': roles_needed.append(p['name'])
            elif p['role'] == 'دكتور': roles_needed.append(p['name'])
            elif p['role'] == 'الشايب': roles_needed.append(p['name'])
    
    # هل جميع أصحاب الأدوار الخاصة قاموا باللعب؟
    # ملاحظة: المواطنون لا يلعبون في الليل، فلا ننتظرهم
    all_acted = all(name in game.players_who_acted for name in roles_needed)
    
    if all_acted:
        # انتظار درامي بسيط
        socketio.sleep(1)
        dead_person = game.process_night_results()
        
        msg = f"☀️ طلع الصباح! وللأسف وجدنا <span class='highlight'>{dead_person}</span> مقتولاً!" if dead_person else "☀️ طلع الصباح! ولم يمت أحد الليلة بفضل الدكتور!"
        emit('log_message', msg, room=room)
        
        # التحقق من الفوز بعد قتلة الليل
        winner = game.check_win_condition()
        if winner:
            end_msg = "🎉 فاز المواطنون!" if winner == 'citizens' else "😈 فازت المافيا وسيطرت على المدينة!"
            emit('log_message', end_msg, room=room)
            socketio.sleep(3)
            emit('game_over', end_msg, room=room)
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

    # تسجيل الصوت
    game.votes[voter['name']] = target
    
    # تحديث الواجهة للجميع ليظهر عداد الأصوات
    emit('update_state', game.get_state(), room=room)
    
    # حساب النتائج
    vote_counts = {}
    for t in game.votes.values():
        vote_counts[t] = vote_counts.get(t, 0) + 1
    
    alive_count = sum(1 for p in game.players if p['is_alive'])
    required_votes = (alive_count // 2) + 1
    
    current_target_votes = vote_counts.get(target, 0)
    
    emit('log_message', f"🗳️ {voter['name']} صوّت ضد {target}", room=room)

    if current_target_votes >= required_votes:
        # تنفيذ الإعدام
        executed_player = next((p for p in game.players if p['name'] == target), None)
        if executed_player:
            executed_player['is_alive'] = False
            emit('log_message', f"⚖️ قرار المحكمة: تم إعدام <span class='highlight'>{target}</span>!", room=room)
            
            winner = game.check_win_condition()
            if winner:
                end_msg = "🎉 فاز المواطنون!" if winner == 'citizens' else "😈 فازت المافيا!"
                emit('log_message', end_msg, room=room)
                emit('game_over', end_msg, room=room)
            else:
                # العودة لليل
                game.start_night()
                socketio.sleep(3)
                emit('log_message', "حل الظلام مرة أخرى... 🌑", room=room)
                emit('update_state', game.get_state(), room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
