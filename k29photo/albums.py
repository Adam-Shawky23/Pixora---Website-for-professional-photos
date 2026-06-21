from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, abort)
from db import get_cursor, commit, rollback
from utils import login_required

albums_bp = Blueprint('albums', __name__)


def _can_view(album, viewer_id, cur):
    if album['visibility'] == 'public':
        return True
    if viewer_id is None:
        return False
    if album['owner_id'] == viewer_id:
        return True
    if album['visibility'] == 'private':
        return False
    # friends
    cur.execute("""
        SELECT 1 FROM album_access
        WHERE album_id = %s AND user_id = %s
    """, (album['album_id'], viewer_id))
    return cur.fetchone() is not None


@albums_bp.route('/albums/<int:album_id>')
def view_album(album_id):
    cur = get_cursor()
    cur.execute("""
        SELECT a.album_id, a.name, a.creation_date, a.visibility,
               a.owner_id,
               u.first_name || ' ' || u.last_name AS owner_name
        FROM albums a
        JOIN users u ON a.owner_id = u.user_id
        WHERE a.album_id = %s
    """, (album_id,))
    album = cur.fetchone()
    if not album:
        abort(404)

    viewer_id = session.get('user_id')
    if not _can_view(album, viewer_id, cur):
        flash('This album is private.', 'error')
        return redirect(url_for('main.browse'))

    cur.execute("""
        SELECT p.photo_id, p.caption,
               COUNT(DISTINCT l.user_id) AS like_count
        FROM photos p
        LEFT JOIN likes l ON p.photo_id = l.photo_id
        WHERE p.album_id = %s
        GROUP BY p.photo_id, p.caption
        ORDER BY p.photo_id
    """, (album_id,))
    photos = cur.fetchall()

    is_owner = viewer_id == album['owner_id']
    return render_template('album.html', album=album, photos=photos, is_owner=is_owner)


@albums_bp.route('/albums/create', methods=['GET', 'POST'])
@login_required
def create_album():
    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        visibility = request.form.get('visibility', 'public')
        if visibility not in ('public', 'private', 'friends'):
            visibility = 'public'
        if not name:
            flash('Album name is required.', 'error')
            return render_template('create_album.html')

        cur = get_cursor()
        try:
            cur.execute("""
                INSERT INTO albums (name, owner_id, creation_date, visibility)
                VALUES (%s, %s, CURRENT_DATE, %s)
                RETURNING album_id
            """, (name, session['user_id'], visibility))
            album_id = cur.fetchone()['album_id']
            commit()
            flash('Album created!', 'success')
            # If friends visibility, go straight to sharing page
            if visibility == 'friends':
                return redirect(url_for('albums.manage_sharing', album_id=album_id))
            return redirect(url_for('albums.view_album', album_id=album_id))
        except Exception as e:
            rollback()
            flash(f'Error: {e}', 'error')

    return render_template('create_album.html')


@albums_bp.route('/albums/<int:album_id>/delete', methods=['POST'])
@login_required
def delete_album(album_id):
    cur = get_cursor()
    cur.execute('SELECT owner_id FROM albums WHERE album_id = %s', (album_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    if row['owner_id'] != session['user_id']:
        abort(403)
    try:
        cur.execute('DELETE FROM albums WHERE album_id = %s', (album_id,))
        commit()
        flash('Album deleted.', 'success')
    except Exception as e:
        rollback()
        flash(f'Error: {e}', 'error')
    return redirect(url_for('albums.my_albums'))


@albums_bp.route('/my-albums')
@login_required
def my_albums():
    cur = get_cursor()
    cur.execute("""
        SELECT a.album_id, a.name, a.creation_date, a.visibility,
               COUNT(p.photo_id) AS photo_count
        FROM albums a
        LEFT JOIN photos p ON p.album_id = a.album_id
        WHERE a.owner_id = %s
        GROUP BY a.album_id, a.name, a.creation_date, a.visibility
        ORDER BY a.creation_date DESC
    """, (session['user_id'],))
    albums = cur.fetchall()
    return render_template('my_albums.html', albums=albums)


@albums_bp.route('/albums/<int:album_id>/sharing', methods=['GET', 'POST'])
@login_required
def manage_sharing(album_id):
    cur = get_cursor()
    cur.execute("""
        SELECT album_id, name, owner_id, visibility
        FROM albums WHERE album_id = %s
    """, (album_id,))
    album = cur.fetchone()
    if not album:
        abort(404)
    if album['owner_id'] != session['user_id']:
        abort(403)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'set_visibility':
            vis = request.form.get('visibility', 'public')
            if vis not in ('public', 'private', 'friends'):
                vis = 'public'
            try:
                cur.execute('UPDATE albums SET visibility=%s WHERE album_id=%s',
                            (vis, album_id))
                commit()
                flash('Visibility updated.', 'success')
            except Exception as e:
                rollback()
                flash(f'Error: {e}', 'error')

        elif action == 'grant':
            uid = request.form.get('user_id')
            try:
                cur.execute("""
                    INSERT INTO album_access (album_id, user_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING
                """, (album_id, uid))
                commit()
                flash('Access granted.', 'success')
            except Exception as e:
                rollback()
                flash(f'Error: {e}', 'error')

        elif action == 'revoke':
            uid = request.form.get('user_id')
            try:
                cur.execute("""
                    DELETE FROM album_access
                    WHERE album_id=%s AND user_id=%s
                """, (album_id, uid))
                commit()
                flash('Access removed.', 'info')
            except Exception as e:
                rollback()
                flash(f'Error: {e}', 'error')

        return redirect(url_for('albums.manage_sharing', album_id=album_id))

    # Re-fetch fresh visibility after POST
    cur.execute('SELECT visibility FROM albums WHERE album_id=%s', (album_id,))
    album = dict(album)
    album['visibility'] = cur.fetchone()['visibility']

    # Users who already have access
    cur.execute("""
        SELECT u.user_id, u.first_name || ' ' || u.last_name AS full_name, u.email
        FROM album_access aa
        JOIN users u ON aa.user_id = u.user_id
        WHERE aa.album_id = %s ORDER BY full_name
    """, (album_id,))
    granted_users = cur.fetchall()

    # Friends not yet granted
    cur.execute("""
        SELECT u.user_id, u.first_name || ' ' || u.last_name AS full_name, u.email
        FROM friends f
        JOIN users u ON f.friend_id = u.user_id
        WHERE f.user_id = %s
          AND u.user_id NOT IN (
              SELECT user_id FROM album_access WHERE album_id = %s
          )
        ORDER BY full_name
    """, (session['user_id'], album_id))
    friends = cur.fetchall()

    return render_template('album_sharing.html',
                           album=album,
                           granted_users=granted_users,
                           friends=friends)