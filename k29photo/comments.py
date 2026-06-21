from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from db import get_cursor, commit, rollback

comments_bp = Blueprint('comments', __name__)


def _notify(cur, user_id, actor_id, notif_type, message, link):
    if user_id == actor_id:
        return
    cur.execute("""
        INSERT INTO notifications (user_id, actor_id, type, message, link)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, actor_id, notif_type, message, link))


@comments_bp.route('/photos/<int:photo_id>/comment', methods=['POST'])
def add_comment(photo_id):
    content = request.form.get('content', '').strip()
    if not content:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('photos.view_photo', photo_id=photo_id))

    cur = get_cursor()

    # Get photo owner for notification
    cur.execute("""
        SELECT a.owner_id, p.caption FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        WHERE p.photo_id = %s
    """, (photo_id,))
    photo = cur.fetchone()
    if not photo:
        abort(404)

    try:
        if 'user_id' in session:
            cur.execute("""
                INSERT INTO comments (photo_id, user_id, content, post_date)
                VALUES (%s, %s, %s, CURRENT_DATE)
            """, (photo_id, session['user_id'], content))

            actor_name = session.get('user_name', 'Someone')
            caption    = photo['caption'] or 'your photo'
            _notify(cur, photo['owner_id'], session['user_id'],
                    'comment',
                    f'{actor_name} commented on "{caption}"',
                    url_for('photos.view_photo', photo_id=photo_id))
        else:
            guest_name = request.form.get('guest_name', '').strip() or 'Guest'
            cur.execute("""
                INSERT INTO comments (photo_id, guest_name, content, post_date)
                VALUES (%s, %s, %s, CURRENT_DATE)
            """, (photo_id, guest_name, content))

        commit()
        flash('Comment posted!', 'success')
    except Exception as e:
        rollback()
        flash(str(e), 'error')

    return redirect(url_for('photos.view_photo', photo_id=photo_id))


@comments_bp.route('/search/comments')
def search_comments():
    query   = request.args.get('q', '').strip()
    results = []
    if query:
        cur = get_cursor()
        cur.execute("""
            SELECT
                COALESCE(u.first_name || ' ' || u.last_name, c.guest_name) AS author,
                u.user_id,
                COUNT(*) AS match_count
            FROM comments c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.content = %s
            GROUP BY author, u.user_id
            ORDER BY match_count DESC
        """, (query,))
        results = cur.fetchall()

    return render_template('search_comments.html', query=query, results=results)