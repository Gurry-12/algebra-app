from flask import Blueprint, render_template, request, flash
from ..models import History
from .. import db
from flask_login import current_user, login_required
from sympy import symbols, simplify, factor, expand, Eq, solve, Matrix
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)
import time, json

# ---------------------- Blueprint ---------------------- #
algebra_bp = Blueprint('algebra', __name__, template_folder='templates', url_prefix='')


# ---------------------- DB Helper ---------------------- #
def add_history_db(action, payload, result):
    try:
        h = History(
            user_id=current_user.get_id() if current_user and not current_user.is_anonymous else None,
            ts=int(time.time()),
            action=action,
            payload=json.dumps(payload, ensure_ascii=False),
            result=json.dumps(result, ensure_ascii=False),
        )
        db.session.add(h)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ---------------------- Forms ---------------------- #
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField


class SolverForm(FlaskForm):
    tool = SelectField(
        'Tool',
        choices=[
            ('expression', 'Expression'),
            ('equation', 'Equation'),
            ('polynomial', 'Polynomial'),
            ('matrix', 'Matrix')
        ]
    )

    # Expression
    expression = StringField('Expression')
    expr_action = SelectField(
        'Expression Action',
        choices=[('simplify', 'Simplify'), ('factor', 'Factor'), ('expand', 'Expand')]
    )

    # Equation
    equation = StringField('Equation')
    var = StringField('Variable')

    # Polynomial
    coeffs = StringField('Coefficients (comma-separated)')
    poly_action = SelectField(
        'Polynomial Action',
        choices=[('roots', 'Roots'), ('notimpl', 'Not Implemented')]
    )

    # Matrix
    A = StringField('Matrix A (rows with ;, cols with ,)')
    B = StringField('Matrix B (optional)')
    mat_action = SelectField(
        'Matrix Action',
        choices=[('det', 'Determinant'), ('inv', 'Inverse'),
                 ('rank', 'Rank'), ('mul', 'Multiply'), ('solve', 'Solve')]
    )

    submit = SubmitField('Solve')


# ---------------------- Parser Config ---------------------- #
transformations = (
    standard_transformations
    + (implicit_multiplication_application, convert_xor)
)


def safe_parse(expr: str):
    """Safely parse expression with SymPy, handling ^ as power and implicit multiplication."""
    return parse_expr(expr.replace("^", "**"), transformations=transformations, evaluate=True)


# ---------------------- Matrix Helper ---------------------- #
def parse_matrix(s):
    rows = [r for r in s.split(";") if r.strip()]
    return Matrix([
        [safe_parse(x) for x in r.replace(",", " ").split()]
        for r in rows
    ])


# ---------------------- Routes ---------------------- #
@algebra_bp.route('/')
def home():
    return render_template('home.html')


@algebra_bp.route("/solver", methods=["GET", "POST"])
def solver():
    form = SolverForm()
    result = None
    error = None

    if request.method == "POST" and form.validate_on_submit():
        tool = form.tool.data.strip()

        try:
            # ---------------- Expression ----------------
            if tool == "expression":
                expr_input = form.expression.data.strip()
                action = form.expr_action.data

                expr = safe_parse(expr_input)
                if action == "simplify":
                    result = str(simplify(expr))
                elif action == "factor":
                    result = str(factor(expr))
                elif action == "expand":
                    result = str(expand(expr))
                else:
                    error = "Unknown expression action."

            # ---------------- Equation ----------------
            elif tool == "equation":
                eqn_input = form.equation.data.strip()
                if "=" not in eqn_input:
                    raise ValueError("Equation must contain '='")
                left, right = eqn_input.split("=")
                var = form.var.data.strip() or "x"
                sol = solve(Eq(safe_parse(left), safe_parse(right)), symbols(var), dict=True)
                result = str(sol)

            # ---------------- Polynomial ----------------
            elif tool == "polynomial":
                coeffs = [safe_parse(c) for c in form.coeffs.data.split(",") if c.strip()]
                poly_action = form.poly_action.data
                x = symbols("x")

                if poly_action == "roots":
                    # Construct polynomial from coefficients
                    poly_expr = sum(c * x**i for i, c in enumerate(reversed(coeffs)))
                    result = str(solve(poly_expr, x))
                else:
                    error = "Polynomial action not implemented."

            # ---------------- Matrix ----------------
            elif tool == "matrix":
                A = parse_matrix(form.A.data)
                action = form.mat_action.data

                if action == "det":
                    result = str(A.det())
                elif action == "inv":
                    result = str(A.inv())
                elif action == "rank":
                    result = str(A.rank())
                elif action == "mul":
                    B = parse_matrix(form.B.data)
                    result = str(A * B)
                elif action == "solve":
                    B = parse_matrix(form.B.data)
                    result = str(A.gauss_jordan_solve(B))
                else:
                    error = "Invalid matrix action."

            else:
                error = "Invalid tool selected."

            # ---------------- Save history ----------------
            if result:
                add_history_db(tool, {"input": request.form.to_dict()}, {"out": result})

        except Exception as e:
            error = str(e)

        if error:
            flash(error, "danger")
        elif result:
            flash("Operation successful!", "success")

    return render_template("solver.html", form=form, result=result)


@algebra_bp.route('/history')
@login_required
def my_history():
    rows = History.query.filter_by(user_id=current_user.id).order_by(History.id.desc()).limit(200).all()
    return render_template('my_history.html', rows=rows)
