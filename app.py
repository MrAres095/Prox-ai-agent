import os, sqlite3, secrets, subprocess, time
from pathlib import Path
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
import requests
BASE=Path(__file__).resolve().parent; DATA=Path(os.getenv('AGENT_DATA_DIR','/var/lib/proxmox-ai-agent')); DATA.mkdir(parents=True,exist_ok=True); DB=DATA/'agent.db'
app=Flask(__name__); app.secret_key=os.getenv('AGENT_SECRET_KEY') or secrets.token_hex(32); app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax')
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.execute('CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY,v TEXT NOT NULL)'); c.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY,role TEXT,content TEXT,ts REAL)'); c.execute('CREATE TABLE IF NOT EXISTS repos (id INTEGER PRIMARY KEY,name TEXT,url TEXT,path TEXT,ts REAL)'); c.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY,cmd TEXT,out TEXT,ts REAL)')
  if not c.execute("SELECT 1 FROM settings WHERE k='password_hash'").fetchone(): c.execute('INSERT INTO settings VALUES(?,?)',('password_hash',generate_password_hash(os.getenv('AGENT_ADMIN_PASSWORD','change-this-password'))))
def get(k,d=''):
 with conn() as c: r=c.execute('SELECT v FROM settings WHERE k=?',(k,)).fetchone(); return r['v'] if r else d
def put(k,v):
 with conn() as c: c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,v))
def auth(f):
 @wraps(f)
 def w(*a,**kw): return f(*a,**kw) if session.get('ok') else redirect(url_for('login'))
 return w
@app.after_request
def headers(r): r.headers['X-Content-Type-Options']='nosniff'; r.headers['X-Frame-Options']='DENY'; r.headers['Referrer-Policy']='same-origin'; return r
@app.route('/health')
def health(): return {'ok':True,'app':'Prox AI Agent'}
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  with conn() as c: row=c.execute("SELECT v FROM settings WHERE k='password_hash'").fetchone()
  if row and check_password_hash(row['v'],request.form.get('password','')): session.clear(); session['ok']=True; return redirect(url_for('home'))
  flash('Neispravna lozinka.')
 return render_template('login.html')
@app.post('/logout')
@auth
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
@auth
def home():
 with conn() as c: msgs=c.execute('SELECT role,content FROM messages ORDER BY id DESC LIMIT 60').fetchall(); repos=c.execute('SELECT * FROM repos ORDER BY id DESC').fetchall(); logs=c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 10').fetchall()
 return render_template('index.html',messages=list(reversed(msgs)),repos=repos,logs=logs,api_base=get('api_base'),model=get('model'),key_set=bool(get('api_key')))
def model_reply(text,history):
 base=get('api_base').rstrip('/'); model=get('model'); key=get('api_key')
 if not base or not model: return 'Agent je pokrenut, ali AI model nije konfiguriran. Otvori Postavke i upiši API base URL i naziv modela. Nije uključen nikakav model; lokalni Ollama ili kompatibilan API može se konfigurirati.'
 url=base if base.endswith('/chat/completions') else base+'/chat/completions'; messages=[{'role':'system','content':'Ti si privatni AI coding agent. Odgovaraj hrvatski kad korisnik piše hrvatski. Nemoj tvrditi da si izvršio zadatke koje nisi izvršio. Trenutno nemaš pravo izvršavati proizvoljne naredbe niti pristup udaljenim terminalima.'}]+[{'role':x['role'],'content':x['content']} for x in history]+[{'role':'user','content':text}]; headers={'Content-Type':'application/json'}
 if key: headers['Authorization']='Bearer '+key
 try:
  r=requests.post(url,headers=headers,json={'model':model,'messages':messages[-22:],'temperature':0.2},timeout=120); r.raise_for_status(); return r.json()['choices'][0]['message']['content']
 except Exception as e: return f'Greška pri pozivu AI modela: {type(e).__name__}: {e}'
@app.post('/chat')
@auth
def chat():
 text=request.form.get('message','').strip()
 if text:
  with conn() as c: hist=list(reversed(c.execute('SELECT role,content FROM messages ORDER BY id DESC LIMIT 20').fetchall())); c.execute('INSERT INTO messages(role,content,ts) VALUES(?,?,?)',('user',text,time.time()))
  ans=model_reply(text,hist)
  with conn() as c: c.execute('INSERT INTO messages(role,content,ts) VALUES(?,?,?)',('assistant',ans,time.time()))
 return redirect(url_for('home')+'#chat')
@app.post('/clear')
@auth
def clear():
 with conn() as c: c.execute('DELETE FROM messages')
 flash('Razgovor obrisan.'); return redirect(url_for('home')+'#chat')
@app.post('/settings')
@auth
def settings():
 for k in ('api_base','model'):
  put(k,request.form.get(k,'').strip())
 if request.form.get('api_key','').strip(): put('api_key',request.form['api_key'].strip())
 flash('Postavke spremljene.'); return redirect(url_for('home')+'#settings')
@app.post('/repos')
@auth
def add_repo():
 name=request.form.get('name','').strip(); url=request.form.get('url','').strip()
 if not name or not url.startswith(('https://','ssh://','git@')): flash('Upiši naziv i HTTPS/SSH Git URL.'); return redirect(url_for('home')+'#repos')
 root=DATA/'repos'; root.mkdir(exist_ok=True); safe=''.join(ch if ch.isalnum() or ch in '-_.' else '-' for ch in name)[:64]; path=root/safe
 if path.exists(): flash('Mapa već postoji.'); return redirect(url_for('home')+'#repos')
 try:
  r=subprocess.run(['git','clone','--',url,str(path)],capture_output=True,text=True,timeout=300); out=(r.stdout+'\n'+r.stderr).strip()[-5000:]
  with conn() as c: c.execute('INSERT INTO repos(name,url,path,ts) VALUES(?,?,?,?)',(name,url,str(path),time.time())); c.execute('INSERT INTO logs(cmd,out,ts) VALUES(?,?,?)',('git clone '+url,out or 'Clone uspješan',time.time()))
  flash('Repo preuzet.' if r.returncode==0 else 'Clone nije uspio; pogledaj zapis naredbi.')
 except Exception as e: flash(f'Git greška: {e}')
 return redirect(url_for('home')+'#repos')
@app.post('/pull/<int:rid>')
@auth
def pull(rid):
 with conn() as c: repo=c.execute('SELECT * FROM repos WHERE id=?',(rid,)).fetchone()
 if not repo: flash('Repo nije pronađen.'); return redirect(url_for('home')+'#repos')
 try:
  r=subprocess.run(['git','-C',repo['path'],'pull','--ff-only'],capture_output=True,text=True,timeout=180); out=(r.stdout+'\n'+r.stderr).strip()[-5000:]
 except Exception as e: r=type('R',(),{'returncode':1})(); out=str(e)
 with conn() as c: c.execute('INSERT INTO logs(cmd,out,ts) VALUES(?,?,?)',('git pull --ff-only '+repo['name'],out,time.time()))
 flash('Git pull završen.' if r.returncode==0 else 'Git pull nije uspio.'); return redirect(url_for('home')+'#repos')
@app.post('/terminal')
@auth
def terminal():
 cmd=request.form.get('command',''); allowed={'hostname':['hostname'],'uptime':['uptime'],'free -h':['free','-h'],'df -h':['df','-h'],'whoami':['whoami']}
 if cmd not in allowed: flash('Dopuštene su samo read-only naredbe iz izbornika.'); return redirect(url_for('home')+'#terminal')
 try: r=subprocess.run(allowed[cmd],capture_output=True,text=True,timeout=15); out=(r.stdout+'\n'+r.stderr).strip()[-5000:]
 except Exception as e: out=str(e)
 with conn() as c: c.execute('INSERT INTO logs(cmd,out,ts) VALUES(?,?,?)',(cmd,out,time.time()))
 flash('Naredba završena.'); return redirect(url_for('home')+'#terminal')
init()
if __name__=='__main__': app.run(host='127.0.0.1',port=8088)
