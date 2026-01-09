import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'falcons_secret_key_123'
# مهم جداً: تفعيل CORS و async_mode ليعمل مع Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- Game State ---
# تخزين البيانات في الذاكرة (يتم مسحها عند إعادة تشغيل السيرفر)
games = {}

# --- HTML Template ---
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
        button { background: #27ae60; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 5px; transition: all 0.3s; font-weight: bold; }
        button:hover { background: #219150; transform: translateY(-2px); }
        button:disabled { background: #555; cursor: not-allowed; transform: none; }
        button.vote-btn { background: #c0392b; }
        button.vote-btn:hover { background: #a93226; }
        button.action-btn { background: #f39c12; color: #000; }
        input { padding: 12px; border-radius: 8px; border: 1px solid #444; background: #2c2c2c; color: white; width: 80%; margin-bottom: 10px; font-size: 16px; }
        .role-reveal { font-size: 28px; font-weight: bold; color: #f1c40f; margin: 20px 0; padding: 10px; background: rgba(241, 196, 15, 0.1); border-radius: 8px; }
        .status { color: #aaa; font-size: 14px; margin-bottom: 10px; }
        #game-area { display: none; }
        .hidden { display: none; }
        .player-item { padding: 12px; background: #2c2c2c; margin: 8px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #555; }
        .player-item.alive { border-left-color: #27ae60; }
        .player-item.dead { border-left-color: #c0392b; opacity: 0.7; }
        #logs-container { max-height: 200px; overflow-y: auto; text-align: right; background: #000; padding: 10px; border-radius: 5px; font-size: 13px; font-family: monospace; }
        .log-entry { margin-bottom: 5px; border-bottom: 1px solid #333; padding-bottom: 2px; }
    </style>
</head>
<body>
    <h1>🦅 مافيا فالكونز</h1>

    <!-- Login Area -->
    <div id="login-area" class="card">
        <h3>تسجيل الدخول</h3>
        <input type="text" id="username" placeholder="اسمك (مثال: عادل)" />
        <input type="text" id="room" placeholder="اسم الغرفة (مثال: RM1)" />
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
            <h3>👥 اللاعبون</h3>
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
        const socket = io({transports: ['websocket', 'polling']}); // Force robust connection
        let myName = "";
        let myRoom = "";
        let myRole = "";

        // استرجاع البيانات المحفوظة عند فتح الصفحة
        window.onload = function() {
            if(localStorage.getItem('mafia_name')) document.getElementById('username').value = localStorage.getItem('mafia_name');
            if(localStorage.getItem('mafia_room')) document.getElementById('room').value = localStorage.getItem('mafia_room');
        };

        function joinGame() {
            myName = document.getElementById('username').value.trim();
            myRoom = document.getElementById('room').value.trim();
            if (!myName || !myRoom) return alert("الرجاء إدخال الاسم واسم الغرفة");
            
            // حفظ البيانات
            localStorage.setItem('mafia_name', myName);
            localStorage.setItem('mafia_room', myRoom);

            socket.emit('join', {username: myName, room: myRoom});
            document.getElementById('login-area').style.display = 'none';
            document.getElementById('game-area').style.display = 'block';
            document.getElementById('room-name').innerText = myRoom;
        }

        function startGame() {
            if(confirm("هل أنت متأكد من بدء اللعبة؟ سيتم توزيع الأدوار.")) {
                socket.emit('start_game', {room: myRoom});
            }
        }

        function sendAction(target, actionType) {
            socket.emit('night_action', {room: myRoom, target: target, action: actionType});
            // إخفاء الأزرار مؤقتاً لمنع التكرار
            document.getElementById('action-area').innerHTML = "<h3>⏳ تم إرسال أمرك... في انتظار البقية</h3>";
        }
        
        function votePlayer(target) {
            if(confirm(`هل تريد التصويت ضد ${target}؟`)) {
                socket.emit('day_vote', {room: myRoom, target: target});
            }
        }

        socket.on('error_msg', (msg) => {
            alert(msg);
            location.reload(); // إعادة تحميل عند الخطأ الجسيم
        });

        socket.on('update_state', (data) => {
            const list = document.getElementById('players-list');
            list.innerHTML = "";
            
            // تحديد المشرف (أول لاعب)
            const isHost = data.players.length > 0 && data.players[0].name === myName; 
            
            if (isHost && data.phase === 'lobby') {
                document.getElementById('start-btn').classList.remove('hidden');
            } else {
                document.getElementById('start-btn').classList.add('hidden');
            }

            document.getElementById('game-status').innerText = `المرحلة: ${data.phase_display}`;

            // Role Reveal Logic
            const me = data.players.find(p => p.name === myName);
            const roleDiv = document.getElementById('my-role');
            
            if (me && me.role && data.phase !== 'lobby') {
                roleDiv.classList.remove('hidden');
                roleDiv.innerText = `أنت: ${me.role}`;
                myRole = me.role;
            } else {
                roleDiv.classList.add('hidden');
            }

            // Action Area Logic
            const actionArea = document.getElementById('action-area');
            actionArea.innerHTML = "";
            
            if (me && !me.is_alive) {
                 actionArea.innerHTML = "<h3 style='color:#e74c3c'>💀 لقد تم إقصاؤك (ميت)</h3>";
            } else if (data.phase === 'night') {
                actionArea.innerHTML = "<h3>🌙 الليل: قم بمهمتك السرية</h3>";
                
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
                    actionArea.innerHTML += "<p>نم قرير العين أيها المواطن، لا يوجد شيء لتفعله.</p>";
                }

            } else if (data.phase === 'voting') {
                actionArea.innerHTML = "<h3>☀️ النهار: من تشك فيه؟</h3>";
                data.players.forEach(p => {
                    if (p.is_alive && p.name !== myName) {
                        actionArea.innerHTML += `<button class='vote-btn' onclick="votePlayer('${p.name}')">🗳️ ${p.name}</button>`;
                    }
                });
            }

            // Render Players List
            data.players.forEach(p => {
                const item = document.createElement('div');
                item.className = `player-item ${p.is_alive ? 'alive' : 'dead'}`;
                let statusIcon = p.is_alive ? '💚' : '💀';
                // إظهار الأدوار عند انتهاء اللعبة فقط (لم يطبق هنا بالكامل للتبسيط)
                item.innerHTML = `<strong>${p.name}</strong> <span>${statusIcon}</span>`;
                list.appendChild(item);
            });
        });

        socket.on('log_message', (msg) => {
            const logs = document.getElementById('game-logs');
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerText = `> ${msg}`;
            logs.prepend(div);
        });
        
        socket.on('check_result', (msg) => {
            alert(`🔍 نتيجة التحقيق:\n${msg}`);
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
        self.votes = {}

    def get_state(self):
        # تصفية البيانات المرسلة (لا نرسل أدوار الآخرين)
        public_players = []
        for p in self.players:
            public_players.append({
                'name': p['name'],
                'is_alive': p['is_alive'],
                'role': p['role'] # يتم استخدامه في الفرونت إند لفلترة العرض للشخص نفسه فقط
            })
        
        phase_ar = {
            'lobby': 'الانتظار في اللوبي',
            'night': 'الليل 🌑',
            'day': 'النهار ☀️',
            'voting': 'وقت التصويت 🗳️'
        }
        
        return {
            'players': public_players,
            'phase': self.phase,
            'phase_display': phase_ar.get(self.phase, self.phase)
        }

    def assign_roles(self):
        names = [p['name'] for p in self.players]
        random.shuffle(names)
        
        roles_dist = {}
        # توزيع الأدوار
        if len(names) > 0: roles_dist[names[0]] = 'مافيا'
        if len(names) > 2: roles_dist[names[1]] = 'دكتور'
        if len(names) > 3: roles_dist[names[2]] = 'الشايب'
        if len(names) > 6: roles_dist[names[3]] = 'مافيا'
        
        for p in self.players:
            p['role'] = roles_dist.get(p['name'], 'مواطن')
            p['is_alive'] = True
        
        self.phase = 'night'
        self.night_actions = {'kills': [], 'saves': [], 'checks': []}

    def process_night(self):
        killed = None
        # منطق بسيط: آخر شخص تم اختياره من المافيا يموت إذا لم يتم إنقاذه
        if self.night_actions['kills']:
            target = self.night_actions['kills'][-1]
            if target not in self.night_actions['saves']:
                killed = target
                for p in self.players:
                    if p['name'] == killed:
                        p['is_alive'] = False
        
        self.phase = 'voting'
        return killed

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
    
    # --- منطق إعادة الاتصال الذكي ---
    # البحث عن اللاعب هل هو موجود مسبقاً؟
    existing_player = next((p for p in game.players if p['name'] == username), None)
    
    if existing_player:
        # اللاعب موجود، نقوم بتحديث الـ SID الخاص به ليعود للتحكم
        existing_player['sid'] = request.sid
        emit('log_message', f"مرحباً بعودتك يا {username}!", to=request.sid)
    else:
        # لاعب جديد
        if game.phase != 'lobby':
            emit('error_msg', "عذراً، اللعبة بدأت بالفعل!", to=request.sid)
            return

        game.players.append({'name': username, 'role': None, 'is_alive': True, 'sid': request.sid})
        emit('log_message', f"انضم {username} للغرفة", room=room)
    
    emit('update_state', game.get_state(), room=room)

@socketio.on('start_game')
def on_start(data):
    room = data['room']
    if room in games:
        games[room].assign_roles()
        emit('update_state', games[room].get_state(), room=room)
        emit('log_message', "🔔 بدأت اللعبة! حل الظلام... أغمضوا أعينكم", room=room)

@socketio.on('night_action')
def on_action(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'night': return
    
    action = data['action']
    target = data['target']
    
    if action == 'kill':
        game.night_actions['kills'].append(target)
        emit('log_message', "🔪 سمع صوت حركة مريبة في الظلام...", room=room)
        
    elif action == 'save':
        game.night_actions['saves'].append(target)
        emit('log_message', "💉 الدكتور خرج لتفقد المرضى...", room=room)
        
    elif action == 'check':
        target_role = next((p['role'] for p in game.players if p['name'] == target), 'مواطن')
        result = "😈 هذا الشخص مافيا!" if target_role == 'مافيا' else "😇 هذا الشخص بريء."
        emit('check_result', result, to=request.sid)
        return # الشايب لا ينهي الدور

    # فحص هل انتهى الدور (تبسيط: إذا قام المافيا والدكتور باللعب)
    # ملاحظة: في اللعب الحقيقي يفضل وجود زر "إنهاء الليلة" للمشرف، هنا سنجعلها أوتوماتيكية بعد القتل
    if action == 'kill': 
        socketio.sleep(2) # انتظار بسيط للتشويق
        dead_person = game.process_night()
        
        msg = f"☀️ طلع الصباح! وللأسف وجدنا {dead_person} مقتولاً!" if dead_person else "☀️ طلع الصباح! ولم يمت أحد الليلة بفضل الدكتور!"
        emit('log_message', msg, room=room)
        emit('update_state', game.get_state(), room=room)

@socketio.on('day_vote')
def on_vote(data):
    room = data['room']
    target = data['target']
    emit('log_message', f"🗳️ قام أحدهم بالتصويت ضد {target}", room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
