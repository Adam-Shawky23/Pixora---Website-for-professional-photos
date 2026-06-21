from flask import Blueprint, render_template, session, abort
from db import get_cursor, commit
from datetime import datetime

main_bp = Blueprint('main', __name__)


def _update_unread_count():
    """Update unread notification count in session."""
    if 'user_id' not in session:
        return
    cur = get_cursor()
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM notifications
        WHERE user_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    row = cur.fetchone()
    session['unread_count'] = row['cnt'] if row else 0


@main_bp.route('/')
def index():
    _update_unread_count()
    cur = get_cursor()

    cur.execute("""
        SELECT p.photo_id, p.caption,
               a.name  AS album_name,
               u.user_id AS owner_id,
               u.first_name || ' ' || u.last_name AS owner_name,
               COUNT(DISTINCT l.user_id) AS like_count
        FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        JOIN users  u ON a.owner_id = u.user_id
        LEFT JOIN likes l ON p.photo_id = l.photo_id
        WHERE a.visibility = 'public'
        GROUP BY p.photo_id, p.caption, a.name, u.user_id, owner_name
        ORDER BY like_count DESC, p.photo_id DESC
        LIMIT 12
    """)
    top_photos = cur.fetchall()

    cur.execute("""
        SELECT t.tag_name, COUNT(pt.photo_id) AS cnt
        FROM tags t
        JOIN photo_tags pt ON t.tag_id = pt.tag_id
        GROUP BY t.tag_name
        ORDER BY cnt DESC
        LIMIT 8
    """)
    popular_tags = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS cnt FROM photos")
    photo_count = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    user_count = cur.fetchone()['cnt']

    return render_template('index.html',
                           top_photos=top_photos,
                           popular_tags=popular_tags,
                           photo_count=photo_count,
                           user_count=user_count)


@main_bp.route('/activity')
def activity():
    _update_unread_count()
    cur = get_cursor()
    cur.execute("""
        SELECT u.user_id,
               u.first_name || ' ' || u.last_name AS full_name,
               u.hometown,
               COUNT(DISTINCT p.photo_id)   AS photo_count,
               COUNT(DISTINCT c.comment_id) AS comment_count,
               COUNT(DISTINCT p.photo_id) + COUNT(DISTINCT c.comment_id) AS score
        FROM users u
        LEFT JOIN albums  a  ON a.owner_id  = u.user_id
        LEFT JOIN photos  p  ON p.album_id  = a.album_id
        LEFT JOIN comments c ON c.user_id   = u.user_id
                             AND c.photo_id NOT IN (
                                 SELECT ph.photo_id
                                 FROM photos ph
                                 JOIN albums al ON ph.album_id = al.album_id
                                 WHERE al.owner_id = u.user_id
                             )
        GROUP BY u.user_id, full_name, u.hometown
        ORDER BY score DESC
        LIMIT 10
    """)
    top_users = cur.fetchall()
    return render_template('activity.html', top_users=top_users)


@main_bp.route('/browse')
def browse():
    _update_unread_count()
    cur = get_cursor()
    viewer_id = session.get('user_id')

    if viewer_id:
        cur.execute("""
            SELECT a.album_id, a.name, a.creation_date, a.visibility,
                   u.user_id AS owner_id,
                   u.first_name || ' ' || u.last_name AS owner_name,
                   COUNT(p.photo_id) AS photo_count
            FROM albums a
            JOIN users u ON a.owner_id = u.user_id
            LEFT JOIN photos p ON p.album_id = a.album_id
            WHERE a.visibility = 'public'
               OR a.owner_id = %s
               OR (a.visibility = 'friends' AND a.album_id IN (
                   SELECT album_id FROM album_access WHERE user_id = %s
               ))
            GROUP BY a.album_id, a.name, a.creation_date, a.visibility, u.user_id, owner_name
            ORDER BY a.creation_date DESC
        """, (viewer_id, viewer_id))
    else:
        cur.execute("""
            SELECT a.album_id, a.name, a.creation_date, a.visibility,
                   u.user_id AS owner_id,
                   u.first_name || ' ' || u.last_name AS owner_name,
                   COUNT(p.photo_id) AS photo_count
            FROM albums a
            JOIN users u ON a.owner_id = u.user_id
            LEFT JOIN photos p ON p.album_id = a.album_id
            WHERE a.visibility = 'public'
            GROUP BY a.album_id, a.name, a.creation_date, a.visibility, u.user_id, owner_name
            ORDER BY a.creation_date DESC
        """)

    albums = cur.fetchall()
    return render_template('browse.html', albums=albums)


@main_bp.route('/users/<int:user_id>')
def user_profile(user_id):
    _update_unread_count()
    cur = get_cursor()
    viewer_id = session.get('user_id')

    # Get user info
    cur.execute("""
        SELECT user_id, first_name, last_name, email, hometown, gender, dob
        FROM users WHERE user_id = %s
    """, (user_id,))
    profile_user = cur.fetchone()
    if not profile_user:
        abort(404)

    # Get their public albums (+ friends albums if viewer has access)
    cur.execute("""
        SELECT a.album_id, a.name, a.creation_date, a.visibility,
               COUNT(p.photo_id) AS photo_count
        FROM albums a
        LEFT JOIN photos p ON p.album_id = a.album_id
        WHERE a.owner_id = %s
          AND (
            a.visibility = 'public'
            OR %s = %s
            OR (a.visibility = 'friends' AND %s IS NOT NULL AND a.album_id IN (
                SELECT album_id FROM album_access WHERE user_id = %s
            ))
          )
        GROUP BY a.album_id, a.name, a.creation_date, a.visibility
        ORDER BY a.creation_date DESC
    """, (user_id, viewer_id, user_id, viewer_id, viewer_id))
    albums = cur.fetchall()

    # Stats
    cur.execute("""
        SELECT COUNT(DISTINCT p.photo_id) AS total_photos,
               COUNT(DISTINCT l.user_id)  AS total_likes_received
        FROM albums a
        LEFT JOIN photos p ON p.album_id = a.album_id
        LEFT JOIN likes  l ON l.photo_id = p.photo_id
        WHERE a.owner_id = %s
    """, (user_id,))
    stats = cur.fetchone()

    # Most liked photo
    cur.execute("""
        SELECT p.photo_id, p.caption, COUNT(l.user_id) AS like_count
        FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        LEFT JOIN likes l ON p.photo_id = l.photo_id
        WHERE a.owner_id = %s AND a.visibility = 'public'
        GROUP BY p.photo_id, p.caption
        ORDER BY like_count DESC
        LIMIT 1
    """, (user_id,))
    top_photo = cur.fetchone()

    # Are we friends?
    is_friend = False
    if viewer_id and viewer_id != user_id:
        cur.execute("""
            SELECT 1 FROM friends WHERE user_id = %s AND friend_id = %s
        """, (viewer_id, user_id))
        is_friend = cur.fetchone() is not None

    return render_template('profile.html',
                           profile_user=profile_user,
                           albums=albums,
                           stats=stats,
                           top_photo=top_photo,
                           is_friend=is_friend,
                           is_own_profile=(viewer_id == user_id))


@main_bp.route('/notifications')
def notifications():
    _update_unread_count()
    if 'user_id' not in session:
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    cur = get_cursor()
    cur.execute("""
        SELECT n.notif_id, n.type, n.message, n.is_read,
               n.created_at, n.link,
               u.first_name || ' ' || u.last_name AS actor_name,
               u.user_id AS actor_id
        FROM notifications n
        LEFT JOIN users u ON n.actor_id = u.user_id
        WHERE n.user_id = %s
        ORDER BY n.created_at DESC
        LIMIT 50
    """, (session['user_id'],))
    notifs = cur.fetchall()

    # Mark all as read
    cur.execute("""
        UPDATE notifications SET is_read = TRUE
        WHERE user_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    commit()
    session['unread_count'] = 0

    return render_template('notifications.html', notifs=notifs)