直接运行容器
docker run -d \\
  --name html-tools \\
  -p 5000:5000 \\
  -e ADMIN_PASSWORD=admin123 \\
  -v $(pwd)/data:/app/tools \\
  ghcr.io/primeldy88/html-tools:latest
🔑 访问信息
项目
值
访问地址
http://localhost:5000
工具首页
无需登录，直接访问
管理后台
http://localhost:5000/admin
默认账号
admin
默认密码
admin123
📖 使用说明
1. 登录管理后台
点击首页右上角 「⚙️ 管理」，进入登录页面，输入账号密码。
2. 上传新工具
进入管理后台
填写工具名称（选填）
填写工具描述（选填）
选择 HTML 文件
选择 图标（选填，支持 PNG/JPG/GIF/SVG/ICO）
点击 「上传并添加工具」
3. 修改/替换工具
在已上传工具列表中找到目标工具：
修改名称或描述
选择新图标文件替换旧的
点击 「更新」
4. 删除工具
点击工具卡片右下角的 「删除」 按钮，确认后删除。
5. 修改主题
在管理后台的「基本设置」中：
修改导航栏标题
选择主题颜色
点击 「保存设置」
🔧 环境变量
变量
默认值
说明
ADMIN_PASSWORD
admin123
登录密码
NAVBAR_TITLE
LDY Tools Portal
导航标题
PORTAL_COLOR
#3b82f6
主题颜色（HEX）
TOOLS_DIR
/app/tools
工具存储目录
📁 目录结构
html-tools/
├── app.py                 # Flask 主程序
├── Dockerfile             # Docker 镜像构建
├── docker-compose.yml     # Docker Compose 配置
├── requirements.txt       # Python 依赖
└── data/                  # 工具文件持久化目录（需手动创建）
    ├── tool1.html
    ├── tool2.html
    └── .metadata.json     # 工具元数据（自动生成）
🐳 本地开发
# 克隆代码
git clone https://github.com/primeldy88/html-tools.git
cd html-tools

# 安装依赖
pip install -r requirements.txt

# 运行
python app.py

访问 http://localhost:5000
📝 License
MIT License © 2026 LDY Tools
如果对你有帮助，欢迎 ⭐ Star！
"""

repo.update_file("README.md", "docs: enhance README with detailed usage and deployment guide", new_readme, readme.sha)
print("README updated!")
PYEOF</parameter>
</invoke>
