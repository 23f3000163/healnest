import os
from app import app

if __name__ == "__main__":
    # This is for local development only
    # In production, Render will use gunicorn to serve the app
    debug = os.environ.get("FLASK_ENV") == "development"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
