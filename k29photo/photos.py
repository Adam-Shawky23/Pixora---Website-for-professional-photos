from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, abort, Response)
from db import get_cursor, commit, rollback
from utils import login_required

photos_bp = Blueprint('photos', __name__)


def _notify(cur, user_id, actor_id, notif_type, message, link):
    """Insert a notification. Skip if user is notifying themselves."""
    if user_id == actor_id:
        return
    cur.execute("""
        INSERT INTO notifications (user_id, actor_id, type, message, link)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, actor_id, notif_type, message, link))


@photos_bp.route('/photos/<int:photo_id>')
def view_photo(photo_id):
    cur = get_cursor()
    cur.execute("""
        SELECT p.photo_id, p.caption, p.album_id,
               a.name AS album_name, a.visibility,
               u.user_id AS owner_id,
               u.first_name || ' ' || u.last_name AS owner_name,
               p.uploaded_at
        FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        JOIN users  u ON a.owner_id = u.user_id
        WHERE p.photo_id = %s
    """, (photo_id,))
    photo = cur.fetchone()
    if not photo:
        abort(404)

    # Privacy check
    viewer_id = session.get('user_id')
    if photo['visibility'] == 'private' and viewer_id != photo['owner_id']:
        abort(403)
    if photo['visibility'] == 'friends' and viewer_id != photo['owner_id']:
        cur.execute("""
            SELECT 1 FROM album_access
            WHERE album_id = %s AND user_id = %s
        """, (photo['album_id'], viewer_id))
        if not cur.fetchone():
            abort(403)

    cur.execute("""
        SELECT t.tag_id, t.tag_name FROM tags t
        JOIN photo_tags pt ON t.tag_id = pt.tag_id
        WHERE pt.photo_id = %s ORDER BY t.tag_name
    """, (photo_id,))
    tags = cur.fetchall()

    cur.execute("""
        SELECT c.comment_id, c.content, c.post_date,
               COALESCE(u.first_name || ' ' || u.last_name, c.guest_name) AS author,
               u.user_id AS author_id
        FROM comments c
        LEFT JOIN users u ON c.user_id = u.user_id
        WHERE c.photo_id = %s ORDER BY c.post_date ASC
    """, (photo_id,))
    comments = cur.fetchall()

    cur.execute("""
        SELECT u.user_id, u.first_name || ' ' || u.last_name AS full_name
        FROM likes l JOIN users u ON l.user_id = u.user_id
        WHERE l.photo_id = %s
    """, (photo_id,))
    likes = cur.fetchall()

    user_liked = False
    if viewer_id:
        cur.execute("SELECT 1 FROM likes WHERE user_id=%s AND photo_id=%s",
                    (viewer_id, photo_id))
        user_liked = cur.fetchone() is not None

    return render_template('photo.html',
                           photo=photo, tags=tags,
                           comments=comments, likes=likes,
                           user_liked=user_liked)


@photos_bp.route('/photos/<int:photo_id>/image')
def serve_image(photo_id):
    cur = get_cursor()
    cur.execute('SELECT data FROM photos WHERE photo_id = %s', (photo_id,))
    row = cur.fetchone()
    if not row or not row['data']:
        abort(404)
    data = bytes(row['data'])
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        mime = 'image/png'
    elif data[:3] == b'\xff\xd8\xff':
        mime = 'image/jpeg'
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        mime = 'image/gif'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        mime = 'image/webp'
    else:
        mime = 'image/jpeg'
    return Response(data, mimetype=mime)


@photos_bp.route('/photos/upload', methods=['GET', 'POST'])
@login_required
def upload_photo():
    cur = get_cursor()
    cur.execute("""
        SELECT album_id, name FROM albums
        WHERE owner_id = %s ORDER BY name
    """, (session['user_id'],))
    albums = cur.fetchall()

    if request.method == 'POST':
        album_id = request.form.get('album_id')
        caption  = request.form.get('caption', '').strip()
        tags_raw = request.form.get('tags', '').strip().lower()
        file     = request.files.get('photo')

        if not album_id or not file or file.filename == '':
            flash('Album and photo file are required.', 'error')
            return render_template('upload_photo.html', albums=albums)

        cur.execute('SELECT owner_id FROM albums WHERE album_id = %s', (album_id,))
        alb = cur.fetchone()
        if not alb or alb['owner_id'] != session['user_id']:
            abort(403)

        image_data = file.read()
        file_size  = len(image_data)

        try:
            from psycopg2 import Binary
            cur.execute("""
                INSERT INTO photos (album_id, caption, data, file_size)
                VALUES (%s, %s, %s, %s) RETURNING photo_id
            """, (album_id, caption, Binary(image_data), file_size))
            photo_id = cur.fetchone()['photo_id']

            if tags_raw:
                tag_list = [t.strip() for t in tags_raw.replace(',', ' ').split() if t.strip()]
                for tag_name in tag_list:
                    cur.execute("""
                        INSERT INTO tags (tag_name) VALUES (%s)
                        ON CONFLICT (tag_name) DO NOTHING
                    """, (tag_name,))
                    cur.execute('SELECT tag_id FROM tags WHERE tag_name = %s', (tag_name,))
                    tag_id = cur.fetchone()['tag_id']
                    cur.execute("""
                        INSERT INTO photo_tags (photo_id, tag_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (photo_id, tag_id))

            commit()
            flash('Photo uploaded!', 'success')
            return redirect(url_for('photos.view_photo', photo_id=photo_id))
        except Exception as e:
            rollback()
            flash(f'Upload failed: {e}', 'error')

    return render_template('upload_photo.html', albums=albums)


@photos_bp.route('/photos/<int:photo_id>/delete', methods=['POST'])
@login_required
def delete_photo(photo_id):
    cur = get_cursor()
    cur.execute("""
        SELECT a.owner_id, p.album_id FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        WHERE p.photo_id = %s
    """, (photo_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    if row['owner_id'] != session['user_id']:
        abort(403)
    album_id = row['album_id']
    try:
        cur.execute('DELETE FROM photos WHERE photo_id = %s', (photo_id,))
        commit()
        flash('Photo deleted.', 'success')
    except Exception as e:
        rollback()
        flash(f'Error: {e}', 'error')
    return redirect(url_for('albums.view_album', album_id=album_id))


@photos_bp.route('/photos/<int:photo_id>/like', methods=['POST'])
def like_photo(photo_id):
    if 'user_id' not in session:
        flash('Please log in to like photos.', 'error')
        return redirect(url_for('auth.login'))
    cur = get_cursor()
    try:
        from psycopg2 import Binary
        cur.execute("""
            INSERT INTO likes (user_id, photo_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (session['user_id'], photo_id))

        # Notify photo owner
        cur.execute("""
            SELECT a.owner_id, p.caption FROM photos p
            JOIN albums a ON p.album_id = a.album_id
            WHERE p.photo_id = %s
        """, (photo_id,))
        photo = cur.fetchone()
        if photo:
            actor_name = session.get('user_name', 'Someone')
            caption    = photo['caption'] or 'your photo'
            _notify(cur, photo['owner_id'], session['user_id'],
                    'like',
                    f'{actor_name} liked "{caption}"',
                    url_for('photos.view_photo', photo_id=photo_id))

        commit()
        flash('Liked!', 'success')
    except Exception as e:
        rollback()
        flash(str(e), 'error')
    return redirect(url_for('photos.view_photo', photo_id=photo_id))


@photos_bp.route('/photos/<int:photo_id>/unlike', methods=['POST'])
@login_required
def unlike_photo(photo_id):
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM likes WHERE user_id=%s AND photo_id=%s",
                    (session['user_id'], photo_id))
        commit()
        flash('Like removed.', 'info')
    except Exception as e:
        rollback()
        flash(str(e), 'error')
    return redirect(url_for('photos.view_photo', photo_id=photo_id))


@photos_bp.route('/search')
def search():
    query   = request.args.get('q', '').strip().lower()
    results = []
    suggestions = []
    cur = get_cursor()

    if query:
        tag_list = query.split()
        n = len(tag_list)
        cur.execute("""
            SELECT p.photo_id, p.caption,
                   a.name AS album_name,
                   u.user_id AS owner_id,
                   u.first_name || ' ' || u.last_name AS owner_name,
                   COUNT(DISTINCT l.user_id) AS like_count
            FROM photos p
            JOIN albums a ON p.album_id = a.album_id
            JOIN users  u ON a.owner_id = u.user_id
            LEFT JOIN likes l ON p.photo_id = l.photo_id
            WHERE a.visibility = 'public'
              AND p.photo_id IN (
                SELECT pt.photo_id FROM photo_tags pt
                JOIN tags t ON pt.tag_id = t.tag_id
                WHERE t.tag_name = ANY(%s)
                GROUP BY pt.photo_id
                HAVING COUNT(DISTINCT t.tag_name) = %s
            )
            GROUP BY p.photo_id, p.caption, a.name, u.user_id, owner_name
            ORDER BY like_count DESC
        """, (tag_list, n))
        results = cur.fetchall()

        # Suggestions if no results
        if not results:
            cur.execute("""
                SELECT tag_name FROM tags
                WHERE tag_name LIKE %s
                LIMIT 5
            """, (f'%{tag_list[0]}%',))
            suggestions = [r['tag_name'] for r in cur.fetchall()]

    cur.execute("""
        SELECT t.tag_name, COUNT(pt.photo_id) AS photo_count
        FROM tags t JOIN photo_tags pt ON t.tag_id = pt.tag_id
        GROUP BY t.tag_name ORDER BY photo_count DESC LIMIT 20
    """)
    tags = cur.fetchall()

    return render_template('search.html',
                           query=query, results=results,
                           tags=tags, suggestions=suggestions)