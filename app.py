from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import uuid
import hmac

app = Flask(__name__)
# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
# Secure cookie settings for production
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Admin security configuration
# Obscure admin panel prefix
ADMIN_PREFIX = "/gag-panel-511"
# Access code required to even view the admin login (set in environment)
ADMIN_ACCESS_CODE = os.environ.get('ADMIN_ACCESS_CODE')

# Debug / Template reload
DEBUG = os.environ.get('FLASK_DEBUG', '0') in {'1', 'true', 'True'}
app.config['TEMPLATES_AUTO_RELOAD'] = DEBUG

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure upload folder and initialize DB once at import (works with Flask>=3)
def _setup_app():
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except Exception:
        pass
    try:
        init_db()
    except Exception:
        pass

# Run setup immediately at import time so WSGI servers are safe
_setup_app()

# Database initialization
def init_db():
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  excerpt TEXT,
                  content TEXT NOT NULL,
                  category TEXT,
                  image_filename TEXT,
                  image_class TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  views INTEGER DEFAULT 0,
                  is_deleted INTEGER DEFAULT 0,
                  deleted_at TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin_users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS media_files (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT NOT NULL,
                  original_name TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  file_size INTEGER,
                  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  category TEXT,
                  link TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  display_order INTEGER DEFAULT 0,
                  is_deleted INTEGER DEFAULT 0,
                  deleted_at TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS favorite_images (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  favorite_id INTEGER NOT NULL,
                  image_filename TEXT NOT NULL,
                  display_order INTEGER DEFAULT 0,
                  is_deleted INTEGER DEFAULT 0,
                  deleted_at TIMESTAMP,
                  FOREIGN KEY (favorite_id) REFERENCES favorites (id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS post_images (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER NOT NULL,
                  image_filename TEXT NOT NULL,
                  display_order INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_deleted INTEGER DEFAULT 0,
                  deleted_at TIMESTAMP,
                  FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
    )''')
    
    # Add soft-delete columns if missing (idempotent)
    for table in ['posts', 'favorites', 'favorite_images', 'post_images']:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN is_deleted INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass

    # media table is created in admin_media route as 'media'; ensure columns exist as well
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TIMESTAMP
    )''')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE media ADD COLUMN is_deleted INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE media ADD COLUMN deleted_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    # Check if admin user exists, if not create one
    c.execute("SELECT * FROM admin_users WHERE username = ?", ('admin',))
    if not c.fetchone():
        password_hash = generate_password_hash('admin123')
        c.execute("INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                 ('admin', password_hash))
    
    # Add missing column to favorites table if it doesn't exist
    try:
        c.execute("ALTER TABLE favorites ADD COLUMN image_filename TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Do not drop or clear data; keep existing records intact
    
    # Insert default posts if none exist
    c.execute("SELECT COUNT(*) FROM posts WHERE is_deleted = 0")
    if c.fetchone()[0] == 0:
        default_posts = [
            {
                'title': '5 Saatlik İş Günü',
                'excerpt': '8 saatlik iş günü modası geçti. Bu yüzden 5 saatlik iş gününü benimsemeyi seçtim.',
                'content': '''<p>8 saatlik iş günü modası geçti. Bu yüzden 5 saatlik iş gününü benimsemeyi seçtim.</p>

<h3>Neden 5 Saat?</h3>
<p>Geleneksel 8 saatlik iş gününün kökleri Sanayi Devrimine dayanıyor. O zamanlar fabrika işçileri için mantıklı olan bu sistem, bugünün bilgi çağında artık verimli değil.</p>

<p>Modern araştırmalar gösteriyor ki, ortalama bir bilgi işçisi günde sadece 2.5-3 saat verimli çalışabiliyor. Geri kalan zaman toplantılarda, e-postalar arasında ve dikkat dağınıklığı ile geçiyor.</p>

<h3>5 Saatlik İş Gününün Faydaları</h3>
<ul>
<li><strong>Daha yüksek verimlilik:</strong> Kısıtlı zaman, odaklanmayı artırıyor</li>
<li><strong>Daha iyi yaşam kalitesi:</strong> Ailene ve hobilerine daha fazla zaman</li>
<li><strong>Azalan stres:</strong> İş-yaşam dengesinde iyileşme</li>
<li><strong>Yaratıcılığın artması:</strong> Dinlenmiş beyin daha yaratıcı çözümler üretiyor</li>
</ul>

<h3>Nasıl Uygulanır?</h3>
<p>5 saatlik iş gününe geçiş kademeli olmalı. İlk olarak en önemli görevlerinizi belirleyin ve bunlara odaklanın. Toplantıları azaltın, dikkat dağıtıcı faktörleri ortadan kaldırın ve Pomodoro Tekniği gibi zaman yönetimi araçlarını kullanın.</p>

<p>Unutmayın: Amaç daha az çalışmak değil, daha akıllı çalışmaktır.</p>''',
                'category': 'article-1'
            },
            {
                'title': 'Gelecekteki Çocuklarıma Vereceğim Finansal Tavsiye: Sahip Ol',
                'excerpt': 'Finansal özgürlük yolunda vereceğim en önemli tavsiye basit ama güçlü: Sahip olmayı öğrenin.',
                'content': '''<p>Finansal özgürlük yolunda vereceğim en önemli tavsiye basit ama güçlü: <strong>Sahip olmayı öğrenin.</strong></p>

<h3>Sahiplik vs Çalışmak</h3>
<p>Geleneksel iş modelinde zamanınızı paraya çevirirsiniz. Ancak günde sadece 24 saat vardır ve bu sınırlama sizi kısıtlar. Sahiplik ise farklı bir oyun kuralı sunar.</p>

<p>Sahip olduğunuzda - hisse senetleri, emlak, işletme veya fikri mülkiyet - paranız sizin için çalışır. Bu, pasif gelir yaratmanın anahtarıdır.</p>

<h3>Sahiplik Türleri</h3>
<ul>
<li><strong>Hisse Senetleri:</strong> Şirketlerin bir parçasına sahip olmak</li>
<li><strong>Emlak:</strong> Kira geliri sağlayan mülkler</li>
<li><strong>İş Kurma:</strong> Kendi şirketinizi yaratmak</li>
<li><strong>Fikri Mülkiyet:</strong> Patent, telif hakkı, marka</li>
</ul>

<h3>Nasıl Başlanır?</h3>
<p>Sahiplik yolculuğu küçük adımlarla başlar. İlk olarak acil durum fonu oluşturun, sonra düşük maliyetli endeks fonlarına yatırım yapmaya başlayın. Zamanla portföyünüzü çeşitlendirin ve farklı sahiplik türlerini keşfedin.</p>

<p>Unutmayın: En önemli yatırım kendinizdir. Sürekli öğrenin, becerilerinizi geliştirin ve değer yaratmaya odaklanın.</p>''',
                'category': 'article-2'
            }
        ]
        
        for post in default_posts:
            c.execute("""INSERT INTO posts (title, excerpt, content, category) 
                        VALUES (?, ?, ?, ?)""",
                     (post['title'], post['excerpt'], post['content'], post['category']))
    
    conn.commit()
    conn.close()

# Frontend Routes
@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    try:
        posts_per_page = 5
        offset = (page - 1) * posts_per_page
        
        conn = sqlite3.connect('blog.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get total posts count
        c.execute("SELECT COUNT(*) FROM posts WHERE is_deleted=0")
        total_posts = c.fetchone()[0]
        
        # Get posts for current page
        c.execute("SELECT * FROM posts WHERE is_deleted=0 ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                 (posts_per_page, offset))
        posts = c.fetchall()
        
        # Get images for each post
        posts_with_images = []
        for post in posts:
            post_dict = dict(post)
            c.execute("SELECT * FROM post_images WHERE post_id = ? AND is_deleted=0 ORDER BY display_order LIMIT 1", (post['id'],))
            first_image = c.fetchone()
            post_dict['first_image'] = first_image['image_filename'] if first_image else None
            posts_with_images.append(post_dict)
        
        conn.close()
        
        # Calculate pagination info
        total_pages = (total_posts + posts_per_page - 1) // posts_per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        pagination = {
            'page': page,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_page': page - 1 if has_prev else None,
            'next_page': page + 1 if has_next else None
        }
        
        return render_template('index.html', posts=posts_with_images, pagination=pagination)
    except Exception as e:
        print(f"Database error in index: {e}")
        return render_template('index.html', posts=[], pagination=None)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Increment view count
    c.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
    
    # Get post
    c.execute("SELECT * FROM posts WHERE id = ? AND is_deleted=0", (post_id,))
    post = c.fetchone()
    
    if post:
        # Get all images for this post
        c.execute("SELECT * FROM post_images WHERE post_id = ? AND is_deleted=0 ORDER BY display_order", (post['id'],))
        images = c.fetchall()
        
        conn.commit()
        conn.close()
        
        return render_template('post_detail.html', post=post, images=images)
    else:
        conn.close()
        return "Post not found", 404

@app.route('/hakkimda')
def about():
    return render_template('about.html')

@app.route('/favoriler')
def favorites():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all favorites
    c.execute("SELECT * FROM favorites WHERE is_deleted=0 ORDER BY display_order ASC, created_at DESC")
    favorites_list = c.fetchall()
    
    # Get images for each favorite
    favorites_with_images = []
    for favorite in favorites_list:
        fav_dict = dict(favorite)
        c.execute("SELECT * FROM favorite_images WHERE favorite_id = ? AND is_deleted=0 ORDER BY display_order", (fav_dict['id'],))
        images = c.fetchall()
        fav_dict['images'] = images
        favorites_with_images.append(fav_dict)
    
    conn.close()
    return render_template('favorites.html', favorites=favorites_with_images)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        c.execute("""SELECT * FROM posts 
                    WHERE is_deleted=0 AND (title LIKE ? OR excerpt LIKE ? OR content LIKE ?) 
                    ORDER BY created_at DESC""",
                 (f'%{query}%', f'%{query}%', f'%{query}%'))
        posts = c.fetchall()
        conn.close()
        return render_template('search_results.html', posts=posts, query=query)
    return redirect(url_for('index'))

# Admin Routes
@app.route(f"{ADMIN_PREFIX}")
def admin_login():
    # If already authenticated as admin, go to dashboard
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))

    # Access code gate: if an access code is set and user has not passed the gate, show code form
    if ADMIN_ACCESS_CODE and not session.get('admin_gate_ok'):
        return render_template_string(
            """
            <!DOCTYPE html>
            <html lang="tr">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>Admin Erişim Kodu</title>
              <style>
                body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; background:#0f172a; color:#e2e8f0; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
                .card { background:#1e293b; padding:24px; border-radius:12px; width:100%; max-width:420px; box-shadow:0 10px 30px rgba(0,0,0,0.3); border:1px solid #334155; }
                h1 { margin:0 0 10px; font-size:20px; color:#f8fafc; }
                p { margin:0 0 16px; color:#94a3b8; font-size:14px; }
                input { width:100%; padding:12px 14px; border-radius:10px; background:#0f172a; color:#f8fafc; border:1px solid #334155; outline:none; }
                input:focus { border-color:#3b82f6; box-shadow:0 0 0 4px rgba(59,130,246,0.15); }
                .btn { margin-top:14px; width:100%; padding:12px 14px; background:linear-gradient(135deg,#3b82f6,#06b6d4); color:#fff; border:none; border-radius:10px; font-weight:700; letter-spacing:.3px; cursor:pointer; }
                .err { color:#fecaca; background:#7f1d1d; border:1px solid #b91c1c; padding:10px; border-radius:10px; margin-bottom:12px; }
              </style>
            </head>
            <body>
              <form class="card" method="post" action="{{ url_for('admin_access_gate') }}">
                <h1>Gizli Erişim</h1>
                <p>Admin paneline erişmek için erişim kodunu girin.</p>
                {% with messages = get_flashed_messages(with_categories=true) %}
                  {% if messages %}
                    {% for category, message in messages %}
                      {% if category in ['error','danger'] %}
                        <div class="err">{{ message }}</div>
                      {% endif %}
                    {% endfor %}
                  {% endif %}
                {% endwith %}
                <input type="password" name="code" placeholder="Erişim Kodu" required>
                <button class="btn" type="submit">Giriş</button>
              </form>
            </body>
            </html>
            """
        )

    # Otherwise show normal login page
    return render_template('admin/login.html')

@app.route(f"{ADMIN_PREFIX}/login", methods=['POST'])
def admin_login_post():
    username = request.form['username']
    password = request.form['password']
    
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute("SELECT * FROM admin_users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        session['admin_logged_in'] = True
        session['admin_username'] = username
        flash('Başarıyla giriş yaptınız!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Hatalı kullanıcı adı veya şifre!', 'error')
        return redirect(url_for('admin_login'))

@app.route(f"{ADMIN_PREFIX}/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('admin_gate_ok', None)
    flash('Başarıyla çıkış yaptınız!', 'info')
    return redirect(url_for('admin_login'))

@app.route(f"{ADMIN_PREFIX}/dashboard")
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get statistics (exclude deleted)
    c.execute("SELECT COUNT(*) FROM posts WHERE is_deleted=0")
    total_posts = c.fetchone()[0]
    
    c.execute("SELECT SUM(views) FROM posts WHERE is_deleted=0")
    total_views_row = c.fetchone()
    total_views = total_views_row[0] if total_views_row and total_views_row[0] is not None else 0
    
    # Get recent posts
    c.execute("SELECT * FROM posts WHERE is_deleted=0 ORDER BY created_at DESC LIMIT 5")
    recent_posts = c.fetchall()
    
    conn.close()
    
    stats = {
        'total_posts': total_posts,
        'total_views': total_views,
        'recent_posts': recent_posts
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route(f"{ADMIN_PREFIX}/posts")
def admin_posts():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE is_deleted=0 ORDER BY created_at DESC")
    posts = c.fetchall()
    conn.close()
    
    return render_template('admin/posts.html', posts=posts)

# Admin Post Create/Edit Routes
@app.route(f"{ADMIN_PREFIX}/posts/new")
def admin_new_post():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin/post_form.html', post=None, images=[])

@app.route(f"{ADMIN_PREFIX}/posts/edit/<int:post_id>")
def admin_edit_post(post_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = c.fetchone()
    if not post:
        conn.close()
        flash('Yazı bulunamadı!', 'error')
        return redirect(url_for('admin_posts'))
    c.execute("SELECT id, image_filename FROM post_images WHERE post_id = ? AND is_deleted=0 ORDER BY display_order", (post_id,))
    images = [{'id': row[0], 'image_filename': row[1]} for row in c.fetchall()]
    conn.close()
    return render_template('admin/post_form.html', post=post, images=images)

@app.route(f"{ADMIN_PREFIX}/posts/save", methods=['POST'])
def admin_save_post():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    title = request.form.get('title','').strip()
    excerpt = request.form.get('excerpt','').strip()
    content = request.form.get('content','').strip()
    category = request.form.get('category','').strip()
    post_id = request.form.get('post_id')
    if not title or not excerpt or not content:
        flash('Lütfen zorunlu alanları doldurun!', 'error')
        if post_id:
            return redirect(url_for('admin_edit_post', post_id=post_id))
        return redirect(url_for('admin_new_post'))
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    try:
        if post_id:
            c.execute("""UPDATE posts SET title=?, excerpt=?, content=?, category=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                      (title, excerpt, content, category, post_id))
            current_post_id = int(post_id)
            flash('Yazı güncellendi!', 'success')
        else:
            c.execute("""INSERT INTO posts (title, excerpt, content, category) VALUES (?, ?, ?, ?)""",
                      (title, excerpt, content, category))
            current_post_id = c.lastrowid
            flash('Yazı oluşturuldu!', 'success')
        # Handle images
        files = request.files.getlist('images')
        order = 0
        for file in files:
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4()}.{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                c.execute("""INSERT INTO post_images (post_id, image_filename, display_order) VALUES (?, ?, ?)""",
                          (current_post_id, filename, order))
                order += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Kaydetme sırasında hata: {str(e)}', 'error')
        if post_id:
            conn.close()
            return redirect(url_for('admin_edit_post', post_id=post_id))
        conn.close()
        return redirect(url_for('admin_new_post'))
    conn.close()
    return redirect(url_for('admin_posts'))

@app.route(f"{ADMIN_PREFIX}/posts/images/delete/<int:image_id>", methods=['DELETE'])
def admin_delete_post_image(image_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        c.execute("UPDATE post_images SET is_deleted=1, deleted_at=CURRENT_TIMESTAMP WHERE id = ?", (image_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Access code verification endpoint (runs before admin login)
@app.route(f"{ADMIN_PREFIX}/access", methods=['POST'])
def admin_access_gate():
    # If no access code configured, allow directly
    if not ADMIN_ACCESS_CODE:
        session['admin_gate_ok'] = True
        return redirect(url_for('admin_login'))

    submitted = request.form.get('code', '')
    # Use hmac.compare_digest for constant-time comparison
    if submitted and hmac.compare_digest(str(submitted), str(ADMIN_ACCESS_CODE)):
        session['admin_gate_ok'] = True
        return redirect(url_for('admin_login'))
    else:
        flash('Geçersiz erişim kodu!', 'error')
        return redirect(url_for('admin_login'))

# Trash Management Routes
@app.route(f"{ADMIN_PREFIX}/trash")
def admin_trash():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Collect trashed items
    c.execute("SELECT * FROM posts WHERE is_deleted=1 ORDER BY deleted_at DESC")
    trashed_posts = c.fetchall()
    c.execute("SELECT * FROM favorites WHERE is_deleted=1 ORDER BY deleted_at DESC")
    trashed_favorites = c.fetchall()
    c.execute("SELECT * FROM favorite_images WHERE is_deleted=1 ORDER BY deleted_at DESC")
    trashed_fav_images = c.fetchall()
    c.execute("SELECT * FROM post_images WHERE is_deleted=1 ORDER BY deleted_at DESC")
    trashed_post_images = c.fetchall()
    conn.close()
    return render_template('admin/trash.html',
                           trashed_posts=trashed_posts,
                           trashed_favorites=trashed_favorites,
                           trashed_fav_images=trashed_fav_images,
                           trashed_post_images=trashed_post_images)

def _validate_trash_type(item_type):
    return item_type in {'post','favorite','favorite_image','post_image'}

@app.route(f"{ADMIN_PREFIX}/trash/restore/<item_type>/<int:item_id>", methods=['POST'])
def admin_trash_restore(item_type, item_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if not _validate_trash_type(item_type):
        return jsonify({'error': 'Invalid type'}), 400
    table_map = {
        'post': 'posts',
        'favorite': 'favorites',
        'favorite_image': 'favorite_images',
        'post_image': 'post_images'
    }
    table = table_map[item_type]
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    c.execute(f"UPDATE {table} SET is_deleted=0, deleted_at=NULL WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route(f"{ADMIN_PREFIX}/trash/hard_delete/<item_type>/<int:item_id>", methods=['DELETE'])
def admin_trash_hard_delete(item_type, item_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if not _validate_trash_type(item_type):
        return jsonify({'error': 'Invalid type'}), 400
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    try:
        if item_type == 'favorite_image':
            c.execute("SELECT image_filename FROM favorite_images WHERE id=?", (item_id,))
            row = c.fetchone()
            if row:
                fname = row[0]
                if fname:
                    fp = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    if os.path.exists(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            c.execute("DELETE FROM favorite_images WHERE id=?", (item_id,))
        elif item_type == 'post_image':
            c.execute("SELECT image_filename FROM post_images WHERE id=?", (item_id,))
            row = c.fetchone()
            if row:
                fname = row[0]
                if fname:
                    fp = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    if os.path.exists(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            c.execute("DELETE FROM post_images WHERE id=?", (item_id,))
        elif item_type == 'favorite':
            c.execute("SELECT image_filename FROM favorite_images WHERE favorite_id=?", (item_id,))
            for (fname,) in c.fetchall():
                if fname:
                    fp = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    if os.path.exists(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            c.execute("DELETE FROM favorite_images WHERE favorite_id=?", (item_id,))
            c.execute("DELETE FROM favorites WHERE id=?", (item_id,))
        elif item_type == 'post':
            c.execute("SELECT image_filename FROM post_images WHERE post_id=?", (item_id,))
            for (fname,) in c.fetchall():
                if fname:
                    fp = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    if os.path.exists(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            c.execute("DELETE FROM post_images WHERE post_id=?", (item_id,))
            c.execute("DELETE FROM posts WHERE id=?", (item_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route(f"{ADMIN_PREFIX}/posts/delete/<int:post_id>", methods=['POST'])
def admin_delete_post(post_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    try:
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        
        # First get the post to check if it exists
        c.execute("SELECT title FROM posts WHERE id = ?", (post_id,))
        post = c.fetchone()
        
        if post:
            # Soft delete the post
            c.execute("UPDATE posts SET is_deleted=1, deleted_at=CURRENT_TIMESTAMP WHERE id = ?", (post_id,))
            conn.commit()
            flash(f'"{post[0]}" başlıklı yazı çöp kutusuna taşındı.', 'success')
        else:
            flash('Silinecek yazı bulunamadı.', 'error')
            
        conn.close()
        
    except Exception as e:
        flash(f'Yazı silinirken hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin_posts'))

@app.route(f"{ADMIN_PREFIX}/posts/favorite/<int:post_id>")
def admin_toggle_favorite(post_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Get current favorite status
    c.execute("SELECT is_favorite FROM posts WHERE id = ?", (post_id,))
    result = c.fetchone()
    
    if result:
        current_status = result[0] if result[0] is not None else 0
        new_status = 1 if current_status == 0 else 0
        
        c.execute("UPDATE posts SET is_favorite = ? WHERE id = ?", (new_status, post_id))
        conn.commit()
        
        status_text = "favorilere eklendi" if new_status == 1 else "favorilerden çıkarıldı"
        flash(f'Post {status_text}!', 'success')
    else:
        flash('Post bulunamadı!', 'error')
    
    conn.close()
    return redirect(url_for('admin_posts'))

# Admin Favorites Management Routes

@app.route(f"{ADMIN_PREFIX}/users")
def admin_users():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get admin users
    c.execute("SELECT * FROM admin_users ORDER BY created_at DESC")
    users = c.fetchall()
    
    # Get posts with their images
    c.execute("SELECT * FROM posts WHERE is_deleted=0 ORDER BY created_at DESC")
    posts = c.fetchall()
    
    # Get images for each post
    posts_with_images = []
    for post in posts:
        post_dict = dict(post)
        c.execute("SELECT * FROM post_images WHERE post_id = ? AND is_deleted=0 ORDER BY display_order", (post['id'],))
        images = c.fetchall()
        post_dict['images'] = images
        posts_with_images.append(post_dict)
    
    conn.close()
    
    return render_template('admin/users.html', users=users, posts=posts_with_images)

@app.route(f"{ADMIN_PREFIX}/favorites/manage")
def admin_favorites_manage():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch all favorites
    c.execute("SELECT * FROM favorites WHERE is_deleted=0 ORDER BY display_order ASC, created_at DESC")
    favorites_list = c.fetchall()

    favorites_with_images = []
    for favorite in favorites_list:
        fav_dict = dict(favorite)
        c.execute("SELECT * FROM favorite_images WHERE favorite_id = ? AND is_deleted=0 ORDER BY display_order", (fav_dict['id'],))
        images = c.fetchall()
        fav_dict['images'] = images
        favorites_with_images.append(fav_dict)

    conn.close()

    return render_template('admin/favorites_manage.html', favorites=favorites_with_images)

@app.route(f"{ADMIN_PREFIX}/favorites/add", methods=['POST'])
def admin_add_favorite():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    title = request.form['title']
    description = request.form.get('description', '')
    link = request.form.get('link', '')
    category = request.form.get('category', 'Genel')

    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Insert favorite item and get its ID
    c.execute("""INSERT INTO favorites (title, description, link, category) 
                 VALUES (?, ?, ?, ?)""",
              (title, description, link, category))
    favorite_id = c.lastrowid

    # Handle multiple image uploads
    files = request.files.getlist('images')
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Insert image record into favorite_images
            c.execute("""INSERT INTO favorite_images (favorite_id, image_filename) 
                         VALUES (?, ?)""", (favorite_id, filename))

    conn.commit()
    conn.close()
    
    flash('Favori başarıyla eklendi!', 'success')
    return redirect(url_for('admin_favorites_manage'))

@app.route(f"{ADMIN_PREFIX}/favorites/edit/<int:favorite_id>", methods=['GET', 'POST'])
def admin_edit_favorite(favorite_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        link = request.form.get('link', '')
        category = request.form.get('category', 'Genel')
        
        # Update favorite details
        c.execute("""UPDATE favorites SET title=?, description=?, link=?, category=? WHERE id=?""", 
                  (title, description, link, category, favorite_id))

        # Handle new image uploads
        files = request.files.getlist('images')
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                c.execute("INSERT INTO favorite_images (favorite_id, image_filename) VALUES (?, ?)", 
                          (favorite_id, filename))

        conn.commit()
        conn.close()
        flash('Favori başarıyla güncellendi!', 'success')
        return redirect(url_for('admin_favorites_manage'))

    # GET request: Fetch favorite and its images
    c.execute("SELECT * FROM favorites WHERE id = ?", (favorite_id,))
    favorite = c.fetchone()

    if favorite is None:
        conn.close()
        flash('Favori bulunamadı!', 'error')
        return redirect(url_for('admin_favorites_manage'))

    c.execute("SELECT * FROM favorite_images WHERE favorite_id = ? ORDER BY id DESC", (favorite_id,))
    images = c.fetchall()
    conn.close()

    return render_template('admin/favorite_edit.html', favorite=favorite, images=images)

@app.route(f"{ADMIN_PREFIX}/favorites/delete_image/<int:image_id>", methods=['POST'])
def admin_delete_favorite_image(image_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        
        # Soft delete favorite image
        c.execute("UPDATE favorite_images SET is_deleted=1, deleted_at=CURRENT_TIMESTAMP WHERE id = ?", (image_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f"{ADMIN_PREFIX}/favorites/delete/<int:favorite_id>", methods=['POST'])
def admin_delete_favorite(favorite_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        
        # Soft delete favorite and its images
        c.execute("UPDATE favorites SET is_deleted=1, deleted_at=CURRENT_TIMESTAMP WHERE id = ?", (favorite_id,))
        c.execute("UPDATE favorite_images SET is_deleted=1, deleted_at=CURRENT_TIMESTAMP WHERE favorite_id = ?", (favorite_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f"{ADMIN_PREFIX}/users/add", methods=['POST'])
def admin_add_user():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    
    # Validation
    if password != confirm_password:
        flash('Şifreler eşleşmiyor!', 'error')
        return redirect(url_for('admin_users'))
    
    if len(password) < 6:
        flash('Şifre en az 6 karakter olmalıdır!', 'error')
        return redirect(url_for('admin_users'))
    
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Check if username already exists
    c.execute("SELECT * FROM admin_users WHERE username = ?", (username,))
    if c.fetchone():
        flash('Bu kullanıcı adı zaten kullanılıyor!', 'error')
        conn.close()
        return redirect(url_for('admin_users'))
    
    # Create new user
    password_hash = generate_password_hash(password)
    c.execute("INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
             (username, password_hash))
    conn.commit()
    conn.close()
    
    flash(f'Kullanıcı "{username}" başarıyla eklendi!', 'success')
    return redirect(url_for('admin_users'))

@app.route(f"{ADMIN_PREFIX}/users/delete/<int:user_id>", methods=['DELETE'])
def admin_delete_user(user_id):
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Get user info
    c.execute("SELECT username FROM admin_users WHERE id = ?", (user_id,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent deleting the main admin user
    if user[0] == 'admin':
        conn.close()
        return jsonify({'error': 'Cannot delete main admin user'}), 403
    
    # Delete user
    c.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.after_request
def after_request(response):
    # Disable caching for dynamic content
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    # Apply HSTS only when behind HTTPS (e.g., via reverse proxy)
    if (request.headers.get('X-Forwarded-Proto', 'http') == 'https'):
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    return response

if __name__ == '__main__':
    # Development server only
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    try:
        port = int(os.environ.get('FLASK_PORT', '5000'))
    except ValueError:
        port = 5000
    app.run(debug=DEBUG, host=host, port=port)
