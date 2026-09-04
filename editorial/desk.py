#!/usr/bin/env python3
"""The Micro Wrapped desk: a local page for writing an edition.

    python3 editorial/desk.py

Opens http://localhost:8765. The left side is material: your Micro.blog
bookmarks (save a link anywhere during the week, it shows up here) and the
recent Discover posts for books, TV, movies, music and podcasts. The right
side is the edition. Tick a bookmark to make it a link, tap a post's title
to add it as a pick, write the note, drop in the artwork, then Save writes
editorial/issues/DATE.md, builds and validates the feed, and Publish
commits and pushes to main.

Needs your Micro.blog app token (Account → App tokens) the first time;
it is kept in ~/.micro-social-desk-token on this Mac and used only to read
your bookmarks and Discover. pip3 install pyyaml pillow
"""
import base64, html, json, os, re, subprocess, sys, time, webbrowser
from datetime import date, datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
ISSUES = ROOT / "issues"
ART = REPO / "static" / "images" / "issues"
CACHE = ROOT / ".desk-cache.json"
TOKEN_FILE = Path.home() / ".micro-social-desk-token"
PORT = 8765
COLLECTIONS = [("books", "Books"), ("tv", "TV"), ("movies", "Movies"), ("music", "Music"), ("podcasts", "Podcasts")]
CACHE_TTL = 30 * 60


# ---------- Micro.blog ----------

def token():
    value = os.environ.get("MICROBLOG_TOKEN")
    if value:
        return value.strip()
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None


def save_token(value):
    TOKEN_FILE.write_text(value.strip() + "\n")
    os.chmod(TOKEN_FILE, 0o600)


def api(path):
    request = Request("https://micro.blog" + path, headers={"Authorization": "Bearer " + token(), "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


TAGS = re.compile(r"<[^>]+>")
ISBN_LINK = re.compile(r"micro\.blog/books/(\d{10,13})")
BOOK_TITLE = re.compile(r'<a href="https://micro\.blog/books/\d+"[^>]*>([^<]+)</a>')


def strip_html(text):
    return html.unescape(TAGS.sub("", text or "")).strip()


def post_summary(item):
    author = item.get("author") or {}
    meta = author.get("_microblog") or {}
    return {
        "id": item.get("id"),
        "url": item.get("url"),
        "date": item.get("date_published"),
        "author": author.get("name"),
        "username": meta.get("username"),
        "text": strip_html(item.get("content_html"))[:400],
        "html": item.get("content_html") or "",
    }


def material():
    if CACHE.exists() and time.time() - CACHE.stat().st_mtime < CACHE_TTL:
        return json.loads(CACHE.read_text())
    out = {"fetched": datetime.now().isoformat(timespec="minutes"), "bookmarks": [], "collections": {}, "books": []}
    try:
        for item in api("/posts/bookmarks").get("items", []):
            summary = post_summary(item)
            summary["title"] = summary["text"].split("\n")[0][:120]
            out["bookmarks"].append(summary)
    except (HTTPError, URLError) as error:
        out["bookmarks_error"] = str(error)
    seen_isbns = {}
    for collection, label in COLLECTIONS:
        try:
            items = api(f"/posts/discover/{collection}").get("items", [])
        except (HTTPError, URLError) as error:
            out["collections"][collection] = {"label": label, "error": str(error), "posts": []}
            continue
        posts = [post_summary(item) for item in items]
        out["collections"][collection] = {"label": label, "posts": posts}
        if collection == "books":
            for post in posts:
                for match in ISBN_LINK.finditer(post["html"]):
                    isbn = match.group(1)
                    title = None
                    title_match = re.search(r'micro\.blog/books/' + isbn + r'"[^>]*>([^<]+)</a>', post["html"])
                    if title_match:
                        title = html.unescape(title_match.group(1)).strip()
                    entry = seen_isbns.setdefault(isbn, {"isbn": isbn, "title": title, "count": 0, "by": []})
                    entry["count"] += 1
                    if post.get("username") and post["username"] not in entry["by"]:
                        entry["by"].append(post["username"])
                    if title and not entry["title"]:
                        entry["title"] = title
    out["books"] = sorted(seen_isbns.values(), key=lambda b: -b["count"])
    for collection in out["collections"].values():
        for post in collection["posts"]:
            post.pop("html", None)
    for post in out["bookmarks"]:
        post.pop("html", None)
    CACHE.write_text(json.dumps(out, indent=1))
    return out


# ---------- Writing the issue ----------

def yaml_str(value):
    text = str(value)
    if text == "" or re.search(r'[:#\[\]{}&*!|>\'"%@`,]|^\s|\s$|^-', text) or text.lower() in ("yes", "no", "true", "false", "null", "~") or re.match(r"^[\d.]+$", text):
        return json.dumps(text, ensure_ascii=False)
    return text


def emit_list(name, items, keys):
    if not items:
        return []
    lines = [f"{name}:"]
    for item in items:
        first = True
        for key in keys:
            value = item.get(key)
            if value in (None, "", []):
                continue
            prefix = "  - " if first else "    "
            first = False
            if isinstance(value, list):
                lines.append(f"{prefix}{key}: [" + ", ".join(yaml_str(v) for v in value) + "]")
            else:
                lines.append(f"{prefix}{key}: {yaml_str(value)}")
        if first:
            continue
    return lines


def write_issue(payload):
    issue_date = payload["date"]
    datetime.strptime(issue_date, "%Y-%m-%d")
    lines = ["---", f"title: {yaml_str(payload['title'])}", f"date: {issue_date}"]
    if payload.get("artwork"):
        lines.append(f"artwork: {yaml_str(payload['artwork'])}")
    if payload.get("summary"):
        lines.append(f"summary: {yaml_str(payload['summary'])}")
    lines += emit_list("reads", payload.get("reads") or [], ["title", "url", "source", "author", "blurb"])
    lines += emit_list("books", payload.get("books") or [], ["isbn", "title", "authors", "reason"])
    lines += emit_list("people", payload.get("people") or [], ["username", "name", "reason"])
    for key in ("watching", "playing", "listening"):
        lines += emit_list(key, payload.get(key) or [], ["title", "subtitle"])
    tip = payload.get("tip") or {}
    if tip.get("title"):
        lines.append("tip:")
        for key in ("label", "title", "body", "username", "url", "glyph"):
            if tip.get(key):
                lines.append(f"  {key}: {yaml_str(tip[key])}")
    lines.append("---")
    ISSUES.mkdir(exist_ok=True)
    path = ISSUES / f"{issue_date}.md"
    path.write_text("\n".join(lines) + "\n" + (payload.get("note") or "").strip() + "\n")
    return path


def save_artwork(issue_date, data_url):
    header, encoded = data_url.split(",", 1)
    raw = base64.b64decode(encoded)
    ART.mkdir(parents=True, exist_ok=True)
    name = f"{issue_date}.jpg"
    path = ART / name
    try:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        target = (1200, 675)
        scale = max(target[0] / image.width, target[1] / image.height)
        image = image.resize((round(image.width * scale), round(image.height * scale)))
        left = (image.width - target[0]) // 2
        top = (image.height - target[1]) // 2
        image = image.crop((left, top, left + target[0], top + target[1]))
        image.save(path, "JPEG", quality=88)
    except ImportError:
        path.write_bytes(raw)
    return name


def run(*args):
    result = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def build():
    code, out = run(sys.executable, "editorial/build.py")
    if code != 0:
        return code, out
    code2, out2 = run(sys.executable, "editorial/validate.py", "editorial/feed.json")
    return code2, out + "\n" + out2


def publish(issue_date):
    steps = [
        ("git", "add", "editorial", "static/images/issues"),
        ("git", "commit", "-m", f"Edition {issue_date}"),
        ("git", "push", "origin", "main"),
    ]
    log = []
    for step in steps:
        code, out = run(*step)
        log.append("$ " + " ".join(step) + "\n" + out)
        if code != 0 and not (step[1] == "commit" and "nothing to commit" in out):
            return 1, "\n\n".join(log)
    return 0, "\n\n".join(log)


def existing_issues():
    out = []
    for path in sorted(ISSUES.glob("*.md"), reverse=True):
        out.append({"date": path.stem, "text": path.read_text()})
    return out


def next_saturday():
    today = date.today()
    days = (5 - today.weekday()) % 7
    return (today + timedelta(days=days or 7)).isoformat()


# ---------- Server ----------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = PAGE.replace("__NEXT_DATE__", next_saturday()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/api/material"):
            if not token():
                return self.send_json({"needs_token": True})
            if "refresh" in self.path and CACHE.exists():
                CACHE.unlink()
            try:
                self.send_json(material())
            except Exception as error:
                self.send_json({"error": str(error)}, 500)
        elif self.path == "/api/issues":
            self.send_json(existing_issues())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        try:
            if self.path == "/api/token":
                save_token(payload["token"])
                self.send_json({"ok": True})
            elif self.path == "/api/save":
                if payload.get("artwork_data"):
                    payload["artwork"] = save_artwork(payload["date"], payload["artwork_data"])
                path = write_issue(payload)
                code, out = build()
                self.send_json({"ok": code == 0, "path": str(path.relative_to(REPO)), "log": out, "artwork": payload.get("artwork")})
            elif self.path == "/api/publish":
                code, out = publish(payload["date"])
                self.send_json({"ok": code == 0, "log": out})
            else:
                self.send_json({"error": "unknown"}, 404)
        except Exception as error:
            self.send_json({"ok": False, "error": str(error)}, 500)


PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Micro Wrapped desk</title>
<style>
:root{--accent:#7c3aed;--tint:#f3ecfd;--line:#e6e6ea;--muted:#6b6b73}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,system-ui,sans-serif;color:#111;background:#fafafa}
header{display:flex;align-items:center;gap:14px;padding:14px 22px;background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
header h1{font-size:18px;margin:0}header .spacer{flex:1}
button{font:inherit;border:0;border-radius:999px;padding:8px 14px;background:var(--tint);color:var(--accent);font-weight:600;cursor:pointer}
button.primary{background:var(--accent);color:#fff}button:disabled{opacity:.5;cursor:default}
main{display:grid;grid-template-columns:1fr 1fr;gap:0;min-height:calc(100vh - 57px)}
.col{padding:20px 22px;overflow:auto;max-height:calc(100vh - 57px)}
.col.material{border-right:1px solid var(--line);background:#fff}
h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin:22px 0 10px}
h2:first-child{margin-top:0}
.item{padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:flex-start}
.item .t{flex:1;min-width:0}.item .t b{display:block}.item .t small{color:var(--muted);display:block;white-space:pre-wrap}
.item a{color:var(--accent);text-decoration:none;font-size:13px}
.item .add{white-space:nowrap}
label{display:block;font-size:12px;color:var(--muted);margin:14px 0 4px}
input[type=text],input[type=date],textarea{width:100%;font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:10px;background:#fff}
textarea{min-height:220px;resize:vertical;font-family:ui-monospace,Menlo,monospace;font-size:13px;line-height:1.5}
.picks .row{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;margin-bottom:8px}
.picks .row.two{grid-template-columns:1fr 1fr auto}
.picks .row.reads{grid-template-columns:1fr 1.4fr 1fr auto}
.picks .row input{width:100%}
.picks .x{background:none;color:var(--muted);padding:6px 8px}
.log{white-space:pre-wrap;font:12px ui-monospace,Menlo,monospace;background:#111;color:#eee;padding:12px;border-radius:10px;margin-top:14px;max-height:220px;overflow:auto}
.ok{color:#1a7f37}.bad{color:#b3261e}
.art{display:flex;gap:12px;align-items:center}.art img{width:160px;height:90px;object-fit:cover;border-radius:8px;background:#ddd}
.count{color:var(--muted);font-weight:400}
.tokenbox{padding:40px;max-width:560px;margin:auto}
.muted{color:var(--muted);font-size:13px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.tabs button{padding:6px 12px}.tabs button.on{background:var(--accent);color:#fff}
</style></head><body>
<header><h1>🌯 Micro Wrapped desk</h1><span id="fetched" class="muted"></span><span class="spacer"></span>
<button id="refresh">Refresh material</button><button id="load">Open an edition…</button><button id="save" class="primary">Save &amp; build</button><button id="publish">Publish</button></header>
<main>
<section class="col material" id="material"><p class="muted">Loading your bookmarks and Discover…</p></section>
<section class="col edition">
  <label>Title</label><input type="text" id="title" placeholder="Slow reads and a new challenge">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div><label>Goes live (a Saturday)</label><input type="date" id="date" value="__NEXT_DATE__"></div>
    <div><label>Artwork (1200×675, no text)</label><div class="art"><img id="artpreview" alt=""><input type="file" id="art" accept="image/*"></div></div>
  </div>
  <label>Summary (one line under the title)</label><input type="text" id="summary">
  <label>The note · Markdown. "## Links", "## Books", "## Watching", "## Playing", "## Listening", "## Tip" put text under that section.</label>
  <textarea id="note">Hello, and welcome to this week's Micro Wrapped.

## Links

## Books

## Tip
</textarea>
  <div class="picks">
    <h2>Interesting links <span class="count" id="readsCount"></span></h2><div id="reads"></div><button onclick="addRow('reads')">+ link</button>
    <h2>Books</h2><div id="books"></div><button onclick="addRow('books')">+ book</button>
    <h2>Watching</h2><div id="watching"></div><button onclick="addRow('watching')">+ title</button>
    <h2>Playing</h2><div id="playing"></div><button onclick="addRow('playing')">+ title</button>
    <h2>Listening</h2><div id="listening"></div><button onclick="addRow('listening')">+ title</button>
    <h2>Tip</h2>
    <div class="row two"><input type="text" id="tipTitle" placeholder="Micro.blog runs community challenges"><input type="text" id="tipBody" placeholder="Photo and writing prompts from @challenges"><span></span></div>
    <div class="row two"><input type="text" id="tipUser" placeholder="username to open (challenges)"><input type="text" id="tipGlyph" placeholder="SF Symbol (trophy.fill)"><span></span></div>
  </div>
  <div class="log" id="log" hidden></div>
</section>
</main>
<script>
const state = {reads:[], books:[], watching:[], playing:[], listening:[]};
const fields = {reads:['title','url','source','blurb'], books:['isbn','title','authors','reason'], watching:['title','subtitle'], playing:['title','subtitle'], listening:['title','subtitle']};
const placeholders = {title:'Title', url:'https://…', source:'Source', blurb:'Why it is worth their time', isbn:'ISBN', authors:'Author, Author', reason:'Why it is here', subtitle:'Apple TV+ / Podcast'};
let artworkData = null, artworkName = null;

function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function render(key){
  const box = document.getElementById(key);
  box.innerHTML = state[key].map((item,i)=>`<div class="row ${key==='reads'?'reads':(fields[key].length===2?'two':'')}">`+
    fields[key].map(f=>`<input type="text" placeholder="${placeholders[f]||f}" value="${esc(item[f]||'')}" oninput="state['${key}'][${i}]['${f}']=this.value">`).join('')+
    `<button class="x" onclick="state['${key}'].splice(${i},1);render('${key}')">✕</button></div>`).join('');
  if(key==='reads') document.getElementById('readsCount').textContent = state.reads.length?`· ${state.reads.length}`:'';
}
function addRow(key, item){state[key].push(item||{});render(key);}
function addPick(key,title,subtitle){if(!state[key].some(p=>p.title===title)) addRow(key,{title,subtitle});}
function addRead(title,url){if(!state.reads.some(r=>r.url===url)) addRow('reads',{title,url,source:'',blurb:''});}
function addBook(isbn,title){if(!state.books.some(b=>b.isbn===isbn)) addRow('books',{isbn,title,authors:'',reason:''});}
Object.keys(state).forEach(render);

document.getElementById('art').addEventListener('change', e=>{
  const f=e.target.files[0]; if(!f) return; const r=new FileReader();
  r.onload=()=>{artworkData=r.result; document.getElementById('artpreview').src=r.result}; r.readAsDataURL(f);
});

async function loadMaterial(refresh){
  const box=document.getElementById('material');
  box.innerHTML='<p class="muted">Loading…</p>';
  const m = await (await fetch('/api/material'+(refresh?'?refresh=1':''))).json();
  if(m.needs_token){ box.innerHTML=`<div class="tokenbox"><h2>Micro.blog app token</h2><p class="muted">From micro.blog → Account → App tokens. Kept on this Mac only; used to read your bookmarks and Discover.</p><input type="text" id="tok" placeholder="paste token"><p><button class="primary" onclick="saveToken()">Save</button></p></div>`; return; }
  if(m.error){ box.innerHTML=`<p class="bad">${esc(m.error)}</p>`; return; }
  document.getElementById('fetched').textContent = 'material as of '+m.fetched.replace('T',' ');
  let h='';
  h+=`<h2>Bookmarks <span class="count">· save a link on Micro.blog during the week and it lands here</span></h2>`;
  if(m.bookmarks_error) h+=`<p class="bad">${esc(m.bookmarks_error)}</p>`;
  if(!m.bookmarks.length) h+=`<p class="muted">No bookmarks.</p>`;
  for(const b of m.bookmarks){ h+=`<div class="item"><div class="t"><b>${esc(b.title)}</b><small>${esc(b.text.slice(0,240))}</small><a href="${esc(b.url)}" target="_blank">${esc(b.url)}</a></div><button class="add" onclick='addRead(${JSON.stringify(b.title)},${JSON.stringify(b.url)})'>+ link</button></div>`; }
  if(m.books.length){ h+=`<h2>Books people are posting about</h2>`;
    for(const b of m.books){ h+=`<div class="item"><div class="t"><b>${esc(b.title||('ISBN '+b.isbn))}</b><small>${b.count} post${b.count===1?'':'s'}${b.by.length?' · @'+b.by.join(', @'):''} · ISBN ${b.isbn}</small></div><button class="add" onclick='addBook(${JSON.stringify(b.isbn)},${JSON.stringify(b.title||'')})'>+ book</button></div>`; } }
  const tabs = Object.entries(m.collections);
  h+=`<h2>Discover</h2><div class="tabs">`+tabs.map(([k,c],i)=>`<button class="${i===0?'on':''}" onclick="showTab('${k}',this)">${esc(c.label)}</button>`).join('')+`</div>`;
  for(const [k,c] of tabs){ h+=`<div class="tab" id="tab-${k}" ${k!==tabs[0][0]?'hidden':''}>`;
    if(c.error) h+=`<p class="bad">${esc(c.error)}</p>`;
    const pickKey = {tv:'watching',movies:'watching',music:'listening',podcasts:'listening'}[k];
    for(const p of c.posts){ const first=(p.text.split('\n')[0]||'').slice(0,90);
      h+=`<div class="item"><div class="t"><b>@${esc(p.username||p.author||'')}</b><small>${esc(p.text.slice(0,300))}</small><a href="${esc(p.url)}" target="_blank">open</a></div>`+
        (pickKey?`<button class="add" onclick='addPick(${JSON.stringify(pickKey)},${JSON.stringify(first)},"")'>+ ${pickKey}</button>`:'')+`</div>`; }
    h+=`</div>`; }
  box.innerHTML=h;
}
function showTab(k,btn){document.querySelectorAll('.tab').forEach(t=>t.hidden=t.id!=='tab-'+k);document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b===btn));}
async function saveToken(){await fetch('/api/token',{method:'POST',body:JSON.stringify({token:document.getElementById('tok').value})});loadMaterial(true);}

function payload(){
  const split=v=>v?v.split(',').map(s=>s.trim()).filter(Boolean):[];
  return {
    title:document.getElementById('title').value.trim(), date:document.getElementById('date').value, summary:document.getElementById('summary').value.trim(),
    note:document.getElementById('note').value, artwork_data:artworkData, artwork:artworkName,
    reads:state.reads.filter(r=>r.title&&r.url), books:state.books.filter(b=>b.title).map(b=>({...b,authors:split(b.authors)})),
    watching:state.watching.filter(p=>p.title), playing:state.playing.filter(p=>p.title), listening:state.listening.filter(p=>p.title),
    tip:{title:document.getElementById('tipTitle').value.trim(), body:document.getElementById('tipBody').value.trim(), username:document.getElementById('tipUser').value.trim(), glyph:document.getElementById('tipGlyph').value.trim()}
  };
}
function log(text, ok){const el=document.getElementById('log');el.hidden=false;el.textContent=text;el.className='log '+(ok?'ok':'bad');}
document.getElementById('save').onclick=async()=>{
  const p=payload(); if(!p.title){alert('Give it a title');return;} if(!p.date){alert('Pick the date');return;}
  const r=await (await fetch('/api/save',{method:'POST',body:JSON.stringify(p)})).json();
  if(r.artwork){artworkName=r.artwork; artworkData=null;}
  log((r.ok?'Saved '+r.path+'\n\n':'Problem\n\n')+(r.log||r.error||''), r.ok);
};
document.getElementById('publish').onclick=async()=>{
  const d=document.getElementById('date').value; if(!confirm('Commit and push the edition dated '+d+' to main?')) return;
  const r=await (await fetch('/api/publish',{method:'POST',body:JSON.stringify({date:d})})).json();
  log(r.log||r.error||'', r.ok);
};
document.getElementById('refresh').onclick=()=>loadMaterial(true);
document.getElementById('load').onclick=async()=>{
  const issues=await (await fetch('/api/issues')).json(); if(!issues.length){alert('No editions yet');return;}
  const pick=prompt('Open which edition?\n'+issues.map(i=>i.date).join('\n'), issues[0].date); const it=issues.find(i=>i.date===pick); if(!it) return;
  const m=it.text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/); if(!m){alert('Could not read it');return;}
  document.getElementById('note').value=m[2].trim()+'\n'; document.getElementById('date').value=it.date;
  const fm=m[1]; const get=k=>{const r=fm.match(new RegExp('^'+k+':\\s*(.*)$','m'));return r?r[1].replace(/^"(.*)"$/,'$1'):''};
  document.getElementById('title').value=get('title'); document.getElementById('summary').value=get('summary'); artworkName=get('artwork')||null;
  alert('Loaded the note, title, summary and date. Re-add the picks below from the material; the saved lists are not read back yet.');
};
loadMaterial(false);
</script></body></html>
"""


def main():
    ISSUES.mkdir(exist_ok=True)
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"Micro Wrapped desk at {url}  (Ctrl-C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
