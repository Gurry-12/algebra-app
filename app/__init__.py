import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY','change-me'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL','sqlite:///database.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'

    from .auth.routes import auth_bp
    from .algebra.routes import algebra_bp
    from .dashboard.routes import dashboard_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(algebra_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()
        # template filters
        from datetime import datetime
        def format_ts(ts):
            try:
                return datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return str(ts)
        app.jinja_env.filters['datetimeformat'] = format_ts

    return app
