import os, secrets, json
from flask import Flask, send_from_directory, request, flash, render_template_string, redirect, url_for, session, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))

TOOLS_DIR = os.environ.get('TOOLS_DIR', '/app/tools')
NAVBAR_TITLE = os.environ.get('NAVBAR_TITLE', 'LDY Tools Portal')
PORTAL_COLOR = os.environ.get('PORTAL_COLOR', '#3b82f6')

os.makedirs(TOOLS_DIR, exist_ok=True)

def get_meta_path():
    return os.path.join(TOOLS_DIR, '.metadata.json')

def load_meta():
    path = get_meta_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_meta(meta):
    with open(get_meta_path(), 'w') as f:
        json.dump(meta, f, indent=2)

def get_tool_list():
    tools = []
    if os.path.isdir(TOOLS_DIR):
        for f in sorted(os.listdir(TOOLS_DIR)):
            if f.endswith('.html') and f != '.metadata.json':
                meta = load_meta()
                info = meta.get(f, {})
                tools.append({
                    'name': info.get('name', f.replace('.html','').replace('-',' ').replace('_',' ').title()),
                    'file': f,
                    'path': f'/tools/{f}',
                    'icon': info.get('icon', ''),
                    'description': info.get('description', '')
                })
    return tools

def is_logged_in():
    return session.get('logged_in', False)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def save_env(key, value):
    env_path = '/app/.env'
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = [l for l in f if not l.startswith(key+'=')]
    with open(env_path, 'w') as f:
        f.write('\n'.join(lines) + ('\n' if lines else '') + f"{key}={value}\n")

def allowed_icon(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in {'png','jpg','jpeg','gif','svg','ico'}

# ========== Routes ==========

@app.route('/')
def index():
    tools = get_tool_list()
    return render_template_string(TEMPLATE_HOME, tools=tools, navbar_title=NAVBAR_TITLE, portal_color=PORTAL_COLOR)

@app.route('/tools/<path:filename>')
def serve_tool(filename):
    return send_from_directory(TOOLS_DIR, filename)

@app.route('/icons/<path:filename>')
def serve_icon(filename):
    return send_from_directory(TOOLS_DIR, filename)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')
        if user == ADMIN_USER and check_password_hash(ADMIN_PASSWORD_HASH, pw):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('用户名或密码错误', 'error')
    return render_template_string(TEMPLATE_LOGIN, navbar_title=NAVBAR_TITLE, portal_color=PORTAL_COLOR)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    tools = get_tool_list()
    meta = load_meta()
    return render_template_string(TEMPLATE_ADMIN, tools=tools, meta=meta,
        navbar_title=NAVBAR_TITLE, portal_color=PORTAL_COLOR, username=ADMIN_USER)

@app.route('/admin/update', methods=['POST'])
@login_required
def admin_update():
    global NAVBAR_TITLE, PORTAL_COLOR, ADMIN_USER, ADMIN_PASSWORD_HASH
    NAVBAR_TITLE = request.form.get('navbar_title', NAVBAR_TITLE)
    PORTAL_COLOR = request.form.get('portal_color', PORTAL_COLOR)
    save_env('NAVBAR_TITLE', NAVBAR_TITLE)
    save_env('PORTAL_COLOR', PORTAL_COLOR)
    if request.form.get('admin_password'):
        new_hash = generate_password_hash(request.form.get('admin_password'))
        ADMIN_PASSWORD_HASH = new_hash
        save_env('ADMIN_PASSWORD', request.form.get('admin_password'))
        flash('设置已保存，密码已更新', 'success')
    else:
        flash('设置已保存', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_tool():
    file = request.files.get('tool_file')
    tool_name = request.form.get('tool_name', '').strip()
    tool_desc = request.form.get('tool_description', '').strip()
    icon_file = request.files.get('icon_file')
    
    if not file or not file.filename:
        flash('请选择文件', 'error')
        return redirect(url_for('admin'))
    
    filename = secure_filename(file.filename)
    if not filename.endswith('.html'):
        flash('只允许上传 .html 文件', 'error')
        return redirect(url_for('admin'))
    
    path = os.path.join(TOOLS_DIR, filename)
    file.save(path)
    
    meta = load_meta()
    icon_name = ''
    if icon_file and allowed_icon(icon_file.filename):
        ext = icon_file.filename.rsplit('.',1)[1].lower()
        icon_name = f"icon_{secure_filename(filename.rsplit('.',1)[0])}.{ext}"
        icon_path = os.path.join(TOOLS_DIR, icon_name)
        icon_file.save(icon_path)
    
    meta[filename] = {
        'name': tool_name or filename.replace('.html','').replace('-',' ').replace('_',' ').title(),
        'description': tool_desc,
        'icon': icon_name
    }
    save_meta(meta)
    
    flash(f'{filename} 上传成功', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit/<filename>', methods=['POST'])
@login_required
def edit_tool(filename):
    safe = secure_filename(filename)
    tool_name = request.form.get('tool_name', '').strip()
    tool_desc = request.form.get('tool_description', '').strip()
    icon_file = request.files.get('icon_file')
    
    meta = load_meta()
    info = meta.get(safe, {'name': safe.replace('.html','').replace('-',' ').replace('_',' ').title(), 'icon': '', 'description': ''})
    
    if tool_name:
        info['name'] = tool_name
    if tool_desc:
        info['description'] = tool_desc
    
    if icon_file and allowed_icon(icon_file.filename):
        ext = icon_file.filename.rsplit('.',1)[1].lower()
        icon_name = f"icon_{safe.rsplit('.',1)[0]}.{ext}"
        if info.get('icon'):
            old = os.path.join(TOOLS_DIR, info['icon'])
            if os.path.exists(old):
                os.remove(old)
        icon_path = os.path.join(TOOLS_DIR, icon_name)
        icon_file.save(icon_path)
        info['icon'] = icon_name
    
    meta[safe] = info
    save_meta(meta)
    
    flash(f'{safe} 已更新', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete/<filename>', methods=['POST'])
@login_required
def delete_tool(filename):
    safe = secure_filename(filename)
    path = os.path.join(TOOLS_DIR, safe)
    if os.path.exists(path):
        os.remove(path)
    
    meta = load_meta()
    if safe in meta:
        icon = meta[safe].get('icon')
        if icon:
            icon_path = os.path.join(TOOLS_DIR, icon)
            if os.path.exists(icon_path):
                os.remove(icon_path)
        del meta[safe]
        save_meta(meta)
    
    flash(f'{filename} 已删除', 'success')
    return redirect(url_for('admin'))

# ========== Templates ==========

TEMPLATE_LOGIN = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - {{ navbar_title }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', system-ui, sans-serif; }
        .login-bg { background: linear-gradient(135deg, {{ portal_color }}, #1e40af); }
    </style>
</head>
<body class="login-bg min-h-screen flex items-center justify-center">
    <div class="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div class="text-center mb-8">
            <h1 class="text-2xl font-bold text-gray-800">{{ navbar_title }}</h1>
            <p class="text-gray-500 text-sm mt-1">请登录管理后台</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
          <div class="mb-4 p-3 rounded-lg {% if category == 'error' %}bg-red-100 text-red-700{% endif %}">{{ message }}</div>
          {% endfor %}
        {% endwith %}
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                <input type="text" name="username" required class="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
                <input type="password" name="password" required class="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
            </div>
            <button type="submit" class="w-full py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition font-medium">登录</button>
        </form>
    </div>
</body>
</html>'''

TEMPLATE_HOME = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ navbar_title }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', system-ui, sans-serif; }
        .tool-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.15); }
        .portal-header { background: linear-gradient(135deg, {{ portal_color }}, #1e40af); }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <header class="portal-header text-white shadow-lg">
        <div class="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
            <div><h1 class="text-2xl font-bold">{{ navbar_title }}</h1>
                <p class="text-blue-200 text-sm mt-1">硬件工程师工具集</p></div>
            <a href="{{ url_for('admin') }}" class="px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30 transition text-sm">⚙️ 管理</a>
        </div>
    </header>
    <main class="max-w-6xl mx-auto px-6 py-8">
        <div class="mb-6"><h2 class="text-xl font-semibold text-gray-700">可用工具 ({{ tools|length }})</h2></div>
        {% if tools %}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for tool in tools %}
            <a href="{{ tool.path }}" target="_blank" class="tool-card block bg-white rounded-2xl shadow-md p-6 border border-gray-100 transition-all duration-200 hover:border-blue-200">
                <div class="flex items-center gap-3 mb-3">
                    {% if tool.icon %}
                    <img src="/icons/{{ tool.icon }}" class="w-12 h-12 rounded-xl object-cover" style="background: {{ portal_color }}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="w-12 h-12 rounded-xl flex items-center justify-center text-white text-xl" style="background: {{ portal_color }}; display:none">🔧</div>
                    {% else %}
                    <div class="w-12 h-12 rounded-xl flex items-center justify-center text-white text-xl" style="background: {{ portal_color }}">🔧</div>
                    {% endif %}
                    <div>
                        <h3 class="font-semibold text-gray-800">{{ tool.name }}</h3>
                        {% if tool.description %}
                        <p class="text-xs text-gray-500 mt-0.5">{{ tool.description }}</p>
                        {% endif %}
                    </div>
                </div>
                <p class="text-sm text-gray-500">{{ tool.file }}</p>
            </a>
            {% endfor %}
        </div>
        {% else %}
        <div class="text-center py-16 bg-white rounded-2xl shadow">
            <div class="text-5xl mb-4">🛠️</div>
            <h3 class="text-lg font-semibold text-gray-700 mb-2">暂无工具</h3>
            <a href="{{ url_for('admin') }}" class="text-blue-500 hover:text-blue-700">去设置页面上传 →</a>
        </div>
        {% endif %}
    </main>
</body>
</html>'''

TEMPLATE_ADMIN = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理后台</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <header class="bg-white shadow-sm border-b">
        <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <h1 class="text-xl font-bold text-gray-800">⚙️ 管理后台</h1>
            <div class="flex items-center gap-4">
                <a href="{{ url_for('index') }}" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-sm">← 返回首页</a>
                <a href="{{ url_for('logout') }}" class="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition text-sm">退出登录</a>
                <span class="text-gray-500 text-sm">{{ username }}</span>
            </div>
        </div>
    </header>
    <main class="max-w-5xl mx-auto px-6 py-8">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
          <div class="mb-4 p-4 rounded-lg {% if category == 'success' %}bg-green-100 text-green-800{% else %}bg-red-100 text-red-800{% endif %}">{{ message }}</div>
          {% endfor %}
        {% endwith %}

        <!-- 上传工具 -->
        <div class="bg-white rounded-2xl shadow p-8 mb-8">
            <h2 class="text-lg font-semibold text-gray-700 mb-6">📤 上传工具</h2>
            <form method="POST" action="{{ url_for('upload_tool') }}" enctype="multipart/form-data" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">工具名称</label>
                    <input type="text" name="tool_name" placeholder="输入工具名称（选填）" class="w-full px-4 py-3 border rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">工具描述</label>
                    <input type="text" name="tool_description" placeholder="工具简短描述（选填）" class="w-full px-4 py-3 border rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">选择 HTML 文件</label>
                    <input type="file" name="tool_file" accept=".html" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">工具图标（选填）</label>
                    <input type="file" name="icon_file" accept=".png,.jpg,.jpeg,.gif,.svg,.ico" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100">
                </div>
                <button type="submit" class="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition font-medium">上传并添加工具</button>
            </form>
        </div>

        <!-- 已上传工具 -->
        <div class="bg-white rounded-2xl shadow p-8 mb-8">
            <h2 class="text-lg font-semibold text-gray-700 mb-4">已上传工具 ({{ tools|length }})</h2>
            {% if tools %}
            <div class="space-y-4">
                {% for tool in tools %}
                {% set info = meta.get(tool.file, {}) %}
                <div class="p-4 bg-gray-50 rounded-xl">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-3">
                            {% if tool.icon %}
                            <img src="/icons/{{ tool.icon }}" class="w-10 h-10 rounded-lg object-cover" onerror="this.style.display='none'">
                            {% endif %}
                            <div>
                                <div class="font-medium text-gray-800">{{ tool.name }}</div>
                                <div class="text-xs text-gray-500">{{ tool.file }}</div>
                                {% if info.description %}
                                <div class="text-xs text-gray-400 mt-0.5">{{ info.description }}</div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <a href="{{ tool.path }}" target="_blank" class="px-3 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200">打开</a>
                        </div>
                    </div>
                    <!-- Edit form -->
                    <form method="POST" action="{{ url_for('edit_tool', filename=tool.file) }}" enctype="multipart/form-data" class="space-y-2">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <input type="text" name="tool_name" value="{{ tool.name }}" placeholder="修改名称" class="px-3 py-2 border rounded text-sm">
                            <input type="text" name="tool_description" value="{{ info.description or '' }}" placeholder="修改描述" class="px-3 py-2 border rounded text-sm">
                        </div>
                        <div class="flex gap-2 items-center">
                            <input type="file" name="icon_file" accept=".png,.jpg,.jpeg,.gif,.svg,.ico" class="text-xs border rounded px-2 py-1 flex-1">
                            <button type="submit" class="px-3 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200">更新</button>
                            <button type="submit" formaction="{{ url_for('delete_tool', filename=tool.file) }}" formmethod="post" onclick="return confirm('确定删除 {{ tool.file }}？')" class="px-3 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200">删除</button>
                        </div>
                    </form>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p class="text-center py-8 text-gray-500">暂无工具</p>
            {% endif %}
        </div>

        <!-- 基本设置 -->
        <div class="bg-white rounded-2xl shadow p-8">
            <h2 class="text-lg font-semibold text-gray-700 mb-6">基本设置</h2>
            <form method="POST" action="{{ url_for('admin_update') }}" class="space-y-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">导航栏标题</label>
                    <input type="text" name="navbar_title" value="{{ navbar_title }}" class="w-full px-4 py-3 border rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">主题颜色</label>
                    <div class="flex gap-3">
                        <input type="color" name="portal_color" value="{{ portal_color }}" class="w-12 h-12 rounded border cursor-pointer">
                        <input type="text" name="portal_color_text" value="{{ portal_color }}" class="flex-1 px-4 py-3 border rounded-lg" onchange="document.querySelector('input[type=color]').value=this.value">
                    </div>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">新 Admin 密码（留空则不变）</label>
                    <input type="password" name="admin_password" placeholder="输入新密码以更改" class="w-full px-4 py-3 border rounded-lg">
                </div>
                <div class="pt-4">
                    <button type="submit" class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition font-medium">保存设置</button>
                </div>
            </form>
        </div>
    </main>
</body>
</html>'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
