from http.server import BaseHTTPRequestHandler
import json
import os
from typing import List

# Mock or Import Tinker
try:
    import tinker
    from tinker import types
    TINKER_AVAILABLE = True
except ImportError:
    TINKER_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not TINKER_AVAILABLE:
             self.send_response(500)
             self.end_headers()
             self.wfile.write(json.dumps({"error": "Tinker library not found"}).encode())
             return

        try:
            # This needs to be async? Vercel Python functions are sync by default unless using ASGI?
            # Tinker SDK is async.
            # We can use asyncio.run()
            import asyncio

            async def list_models():
                service_client = tinker.ServiceClient()
                capabilities = await service_client.get_server_capabilities_async()
                return [m.model_name for m in capabilities.supported_models]

            models = asyncio.run(list_models())

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"models": models}).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
