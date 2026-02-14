import os
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.routes.api import api_bp

def create_app():
    app = Flask(__name__)

    # Enable CORS when frontend runs on a different server
    CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))

    app.register_blueprint(api_bp)

    # Serve static frontend at / when USE_STATIC is enabled (default: yes for single-server run)
    use_static = os.getenv("USE_STATIC", "1").strip().lower() in ("1", "true", "yes")
    project_root = Path(__file__).resolve().parents[1]
    public_dir = project_root / "public"
    if use_static and public_dir.is_dir():
        public_dir_str = str(public_dir)

        @app.get("/")
        def home():
            return send_from_directory(public_dir_str, "index.html")

        @app.get("/<path:filename>")
        def static_file(filename):
            return send_from_directory(public_dir_str, filename)

    return app

if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    # 0.0.0.0 so the app is reachable when deployed (e.g. Railway, Render)
    app.run(host="0.0.0.0", port=port, debug=debug)
