import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'falcons_secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Game State ---
# تخزين بيانات الغرف واللاعبين
games = {}

# --- HTML Template (الواجهة الأمامية) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مافيا فالكونز 🦅</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; color: #fff; text-align: center; padding: 20px; }
        .card { background: #2d2d2d; padding: 20px; border-radius: 10px; margin: 10px auto; max-width: 500px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        button { background: #27ae60; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 5px; }
        button:hover { background: #219150; }
        button.vote-btn { background: #c0392b; }
        input { padding: 10px; border-radius: 5px; border: 1px solid #444; background: #333; color: white; }
        .role-reveal { font-size: 24px; font-weight: bold; color: #f1c40f; margin: 20px 0; }
        .status { color: #aaa; font-size: 14px; }
        #game-area { display: none; }
        .hidden { display: none; }
        .player-item { padding: 10px; background: #333; margin: 5px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <h1>🦅 مافيا فالكونز: النسخة الرمضانية</h1>

    <!-- Login Area -->
    <div id="login-area" class="card">
        <h3>تسجيل الدخول</h3>
        <input type="text" id="username" placeholder="اسمك (مثال: عادل)" />
        <input type="text" id="room" placeholder="اسم الغرفة (مثال: RM1)" />
        <br><br>
        <button onclick="joinGame()">دخول اللعبة</button>
    </div>

    <!-- Game Area -->
    <div id="game-area">
        <div class="card">
            <h2>غرفة: <span id="room-name"></span></h2>
            <div id="game-status" class="status">في انتظار اللاعبين...</div>
            <div id="my-role" class="role-reveal hidden"></div>
            <div id="action-area"></div>
            <button id="start-btn" onclick="startGame()" class="hidden">بدء اللعبة (للمشرف)</button>
        </div>

        <div class="card">
            <h3>اللاعبون المتواجدون</h3>
            <div id="players-list"></div>
        </div>
        
        <div class="card" id="log-area">
            <h3>سجل الأحداث</h3>
            <ul id="game-logs" style="list-style: none; padding: 0;"></ul>
        </div>
    </div>

    <script>
        const socket = io();
        let myName = "";
        let myRoom = "";
        let myRole = "";

        function joinGame() {
            myName = document.getElementById('username').value;
            myRoom = document.getElementById('room').value;
            if (!myName || !myRoom) return alert("أدخل الاسم والغرفة");
            
            socket.emit('join', {username: myName, room: myRoom});
            document.getElementById('login-area').style.display = 'none';
            document.getElementById('game-area').style.display = 'block';
            document.getElementById('room-name').innerText = myRoom;
        }

        function startGame() {
            socket.emit('start_game', {room: myRoom});
        }

        function sendAction(target, actionType) {
            socket.emit('night_action', {room: myRoom, target: target, action: actionType});
        }
        
        function votePlayer(target) {
            socket.emit('day_vote', {room: myRoom, target: target});
        }

        socket.on('update_state', (data) => {
            const list = document.getElementById('players-list');
            list.innerHTML = "";
            const isHost = data.players[0].name === myName; 
            
            if (isHost && data.phase === 'lobby') {
                document.getElementById('start-btn').classList.remove('hidden');
            } else {
                document.getElementById('start-btn').classList.add('hidden');
            }

            document.getElementById('game-status').innerText = `المرحلة الحالية: ${data.phase_display}`;

            // Role Reveal
            const me = data.players.find(p => p.name === myName);
            if (me && me.role && data.phase !== 'lobby') {
                const roleDiv = document.getElementById('my-role');
                roleDiv.classList.remove('hidden');
                roleDiv.innerText = `أنت: ${me.role}`;
                myRole = me.role;
            }

            // Action Area Logic
            const actionArea = document.getElementById('action-area');
            actionArea.innerHTML = "";
            
            if (me && !me.is_alive) {
                 actionArea.innerHTML = "<h3 style='color:red'>لقد تم اغتيالك 💀</h3>";
            } else if (data.phase === 'night') {
                actionArea.innerHTML = "<h3>🌙 الليل: قم بتنفيذ مهمتك</h3>";
                
                // Mafia Logic
                if (myRole === 'مافيا') {
                    actionArea.innerHTML += "<p>اختر ضحية:</p>";
                    data.players.forEach(p => {
                        if (p.is_alive && p.name !== myName) { // Mafia can kill anyone else
                            actionArea.innerHTML += `<button class='vote-btn' onclick="sendAction('${p.name}', 'kill')">${p.name}</button>`;
                        }
                    });
                }
                // Doctor Logic
                else if (myRole === 'دكتور') {
                    actionArea.innerHTML += "<p>اختر شخصاً لإنقاذه:</p>";
                    data.players.forEach(p => {
                        if (p.is_alive) {
                            actionArea.innerHTML += `<button onclick="sendAction('${p.name}', 'save')">${p.name}</button>`;
                        }
                    });
                }
                // Shaib Logic
                else if (myRole === 'الشايب') {
                    actionArea.innerHTML += "<p>اختر شخصاً للتحقيق عنه:</p>";
                    data.players.forEach(p => {
                        if (p.is_alive && p.name !== myName) {
                            actionArea.innerHTML += `<button onclick="sendAction('${p.name}', 'check')">${p.name}</button>`;
                        }
                    });
                } else {
                    actionArea.innerHTML += "<p>نم قرير العين أيها المواطن...</p>";
                }

            } else if (data.phase === 'voting') {
                actionArea.innerHTML = "<h3>☀️ النهار: تصويت للإخراج</h3>";
                data.players.forEach(p => {
                    if (p.is_alive && p.name !== myName) {
                        actionArea.innerHTML += `<button class='vote-btn' onclick="votePlayer('${p.name}')">${p.name}</button>`;
                    }
                });
            }

            // Render Players List
            data.players.forEach(p => {
                const item = document.createElement('div');
                item.className = 'player-item';
                item.innerHTML = `<span>${p.name} ${p.is_alive ? '💚' : '💀'}</span>`;
                list.appendChild(item);
            });
        });

        socket.on('log_message', (msg) => {
            const logs = document.getElementById('game-logs');
            const li = document.createElement('li');
            li.innerText = msg;
            logs.prepend(li); // Add to top
        });
        
        socket.on('check_result', (msg) => {
            alert(msg); // For the detective
        });
    </script>
</body>
</html>
"""

# --- Backend Logic ---

class Game:
    def __init__(self):
        self.players = [] # List of dicts
        self.phase = 'lobby' # lobby, night, day, voting
        self.roles_map = {}
        self.night_actions = {'kills': [], 'saves': [], 'checks': []}
        self.votes = {}

    def get_state(self):
        # إخفاء الأدوار عن العامة وإرسال الحالة
        public_players = []
        for p in self.players:
            public_players.append({
                'name': p['name'],
                'is_alive': p['is_alive'],
                # Role is hidden here, sent specifically to client only if needed
                'role': p['role'] # In prod, hide this and send individual events
            })
        
        phase_ar = {
            'lobby': 'الانتظار في اللوبي',
            'night': 'الليل (المافيا والدكتور والشايب يستيقظون)',
            'day': 'النهار (نقاش)',
            'voting': 'التصويت'
        }
        
        return {
            'players': public_players,
            'phase': self.phase,
            'phase_display': phase_ar.get(self.phase, self.phase)
        }

    def assign_roles(self):
        names = [p['name'] for p in self.players]
        random.shuffle(names)
        
        # توزيع الأدوار حسب عدد اللاعبين (تقريبي)
        # مثال: 1 مافيا، 1 دكتور، 1 شايب، والباقي مواطن
        roles = {}
        roles[names[0]] = 'مافيا'
        if len(names) > 2: roles[names[1]] = 'دكتور'
        if len(names) > 3: roles[names[2]] = 'الشايب'
        # إذا العدد كبير نضيف مافيا ثاني
        if len(names) > 6: roles[names[3]] = 'مافيا'
        
        for p in self.players:
            p['role'] = roles.get(p['name'], 'مواطن')
            p['is_alive'] = True
        
        self.phase = 'night'
        self.night_actions = {'kills': [], 'saves': [], 'checks': []}

    def process_night(self):
        killed = None
        # منطق بسيط: إذا المافيا اختاروا شخص ولم ينقذه الدكتور
        # نأخذ آخر شخص تم اختياره من المافيا (للبساطة)
        if self.night_actions['kills']:
            target = self.night_actions['kills'][-1]
            if target not in self.night_actions['saves']:
                killed = target
                for p in self.players:
                    if p['name'] == killed:
                        p['is_alive'] = False
        
        self.phase = 'voting' # انتقال للنهار والتصويت
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
    
    # Check if player exists
    if not any(p['name'] == username for p in games[room].players):
        games[room].players.append({'name': username, 'role': None, 'is_alive': True, 'sid': request.sid})
    
    emit('update_state', games[room].get_state(), room=room)
    emit('log_message', f"دخل {username} إلى الغرفة", room=room)

@socketio.on('start_game')
def on_start(data):
    room = data['room']
    if room in games:
        games[room].assign_roles()
        emit('update_state', games[room].get_state(), room=room)
        emit('log_message', "بدأت اللعبة! حل الظلام... 🌙", room=room)

@socketio.on('night_action')
def on_action(data):
    room = data['room']
    game = games.get(room)
    if not game or game.phase != 'night': return
    
    action = data['action']
    target = data['target']
    
    # تخزين الأكشن
    if action == 'kill':
        game.night_actions['kills'].append(target)
        emit('log_message', "المافيا اختارت ضحية...", room=room) # رسالة غامضة
        
    elif action == 'save':
        game.night_actions['saves'].append(target)
        emit('log_message', "الدكتور قام بزيارة أحدهم...", room=room)
        
    elif action == 'check':
        # الشايب يحصل على نتيجة فورية
        target_role = next((p['role'] for p in game.players if p['name'] == target), 'مواطن')
        is_mafia = "نعم، هو مافيا 😈" if target_role == 'مافيا' else "لا، هو بريء 😇"
        emit('check_result', f"الشايب سأل عن {target}: {is_mafia}", to=request.sid)

    # هنا يمكن إضافة شرط لإنهاء الليل (مثلا بعد وقت أو بعد اكتمال الأكشن)
    # للتبسيط سننهي الليل بعد 3 أكشنات أو بضغط زر (غير مضاف هنا)
    # سنقوم بإنهاء الليل يدوياً عبر زر "النتائج" (محاكاة) أو تلقائي لو أردت
    
    # *تعديل بسيط*: دعنا نجعل النتيجة تظهر بعد قليل أو نجعل زر "الصباح" للمشرف.
    # للتبسيط في هذا الكود: إذا قام المافيا بالقتل، ينتهي الليل.
    if action == 'kill': 
        dead_person = game.process_night()
        msg = f"طلع الصباح! ☀️ وللأسف مات: {dead_person}" if dead_person else "طلع الصباح! ☀️ ولم يمت أحد الليلة!"
        emit('log_message', msg, room=room)
        emit('update_state', game.get_state(), room=room)

@socketio.on('day_vote')
def on_vote(data):
    room = data['room']
    game = games.get(room)
    target = data['target']
    
    emit('log_message', f"تم التصويت ضد {target}", room=room)
    # هنا يمكن إضافة منطق خروج اللاعب عند وصول عدد معين من الأصوات
    # للتبسيط: مجرد تسجيل لوج

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
