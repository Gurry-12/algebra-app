from flask import Blueprint, request, jsonify
from ..models import History
from .. import db
from sympy import simplify
from sympy.parsing.sympy_parser import parse_expr
import time, json
from flask_login import current_user

api_bp = Blueprint("api", __name__)

@api_bp.route("/simplify", methods=["POST"])
def api_simplify():
    data = request.get_json() or {}
    expr = data.get("expr", "").strip()

    if not expr:
        return jsonify({"ok": False, "error": "No expression provided"}), 400

    try:
        # Core simplification
        parsed_expr = parse_expr(expr, evaluate=True)
        out = str(simplify(parsed_expr))

        # Log in history
        try:
            h = History(
                user_id=current_user.get_id() if current_user and not current_user.is_anonymous else None,
                ts=int(time.time()),
                action="simplify",
                payload=json.dumps({"expr": expr}),
                result=json.dumps({"out": out}),
            )
            db.session.add(h)
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            print(f"[DB ERROR] Could not log history: {db_err}")

        return jsonify({"ok": True, "out": out})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
