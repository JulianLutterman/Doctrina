from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
from api.lib.models_handler import handle_models
from api.lib.chat_handler import handle_chat
from api.lib.feedback_handler import handle_feedback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.route()

    def do_POST(self):
        self.route()

    def route(self):
        parsed = urlparse(self.path)
        # Vercel passes the path as is. Next.js rewrites will map /api/chat/completions to /api?path=... if configured or just pass path.
        # But since I will rewrite /api/:path* -> /api/index in next.config.js, I need to check the path.

        # Path logic:
        # If I call /api/models, path is /api/models
        # If I call /api/chat/completions, path is /api/chat/completions

        if parsed.path.endswith("/api/models"):
            handle_models(self)
        elif parsed.path.endswith("/api/chat/completions"):
            handle_chat(self)
        elif parsed.path.endswith("/api/feedback"):
            handle_feedback(self)
        else:
            self.send_response(404)
            self.end_headers()
