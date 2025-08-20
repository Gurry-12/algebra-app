from time import time
from flask import Blueprint, render_template, jsonify
from ..models import History, db
from flask_login import login_required, current_user
from collections import Counter

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates', url_prefix='')

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard view. Renders stats & history for the logged-in user.
    """
    history_rows = (
        History.query.filter_by(user_id=current_user.id)
        .order_by(History.ts.desc())   # ✅ use ts instead of timestamp
        .limit(10)
        .all()
    )
    return render_template('dashboard.html', history=history_rows)

@dashboard_bp.route('/_stats')
@login_required
def stats():
    """
    Returns JSON stats about user actions (for charts / graphs).
    """
    rows = History.query.filter_by(user_id=current_user.id).all()
    actions = [r.action for r in rows]
    c = Counter(actions)

    return jsonify({
        'counts': dict(c),
        'total': len(actions)
    })

# Utility function: log an action
def log_action(user_id, action, payload=None, result=None):
    """
    Store user activity (e.g., login, logout, solving an expression).
    """
    entry = History(
        user_id=user_id,
        ts=int(time.time()),     # ✅ required field
        action=action,
        payload=payload or "",
        result=result or ""
    )
    db.session.add(entry)
    db.session.commit()
