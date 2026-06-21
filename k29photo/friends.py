from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_cursor, commit, rollback
from utils import login_required

friends_bp = Blueprint('friends', __name__)


def _notify(cur, user_id, actor_id, notif_type, message, link):
    if user_id == actor_id:
        return
    cur.execute("""
        INSERT INTO notifications (user_id, actor_id, type, message, link)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, actor_id, notif_type, message, link))


@friends_bp.route('/friends')
@login_required
def friends_list():
    cur = get_cursor()

    cur.execute("""
        SELECT u.user_id,
               u.first_name || ' ' || u.last_name AS full_name,
               u.email, u.hometown
        FROM friends f
        JOIN users u ON f.friend_id = u.user_id
        WHERE f.user_id = %s
        ORDER BY full_name
    """, (session['user_id'],))
    my_friends = cur.fetchall()

    search_query = request.args.get('q', '').strip()
    search_results = []
    if search_query:
        cur.execute("""
            SELECT u.user_id,
                   u.first_name || ' ' || u.last_name AS full_name,
                   u.email, u.hometown
            FROM users u
            WHERE (u.first_name ILIKE %s OR u.last_name ILIKE %s OR u.email ILIKE %s)
              AND u.user_id != %s
              AND u.user_id NOT IN (
                  SELECT friend_id FROM friends WHERE user_id = %s
              )
        """, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%',
              session['user_id'], session['user_id']))
        search_results = cur.fetchall()

    return render_template('friends.html',
                           my_friends=my_friends,
                           search_results=search_results,
                           search_query=search_query)


@friends_bp.route('/friends/add/<int:friend_id>', methods=['POST'])
@login_required
def add_friend(friend_id):
    cur = get_cursor()
    try:
        cur.execute("""
            INSERT INTO friends (user_id, friend_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (session['user_id'], friend_id))

        actor_name = session.get('user_name', 'Someone')
        _notify(cur, friend_id, session['user_id'],
                'friend',
                f'{actor_name} started following you',
                url_for('main.user_profile', user_id=session['user_id']))

        commit()
        flash('Added!', 'success')
    except Exception as e:
        rollback()
        flash(str(e), 'error')
    return redirect(url_for('friends.friends_list'))


@friends_bp.route('/friends/remove/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    cur = get_cursor()
    try:
        cur.execute("""
            DELETE FROM friends WHERE user_id = %s AND friend_id = %s
        """, (session['user_id'], friend_id))
        commit()
        flash('Removed.', 'info')
    except Exception as e:
        rollback()
        flash(str(e), 'error')
    return redirect(url_for('friends.friends_list'))