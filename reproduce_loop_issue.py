
import asyncio
from api._lib.models_handler import handle_models
import io

class MockHandler:
    def __init__(self):
        self.command = "GET"
        self.wfile = io.BytesIO()
        self.headers = {}
        self.response_buffer = []

    def send_response(self, code, message=None):
        print(f"Response Code: {code}")
        self.response_buffer.append(f"HTTP/1.0 {code} {message or ''}")

    def send_header(self, keyword, value):
        self.response_buffer.append(f"{keyword}: {value}")

    def end_headers(self):
        self.response_buffer.append("")

async def main():
    # This simulates running in an async environment
    handler = MockHandler()
    # This should crash if asyncio.run() is called directly without thread wrapper
    handle_models(handler)
    print(handler.wfile.getvalue().decode())

if __name__ == "__main__":
    asyncio.run(main())
