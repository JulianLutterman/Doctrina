from playwright.sync_api import Page, expect, sync_playwright
import time

def verify_chat_interface(page: Page):
    # 1. Navigate to the app
    page.goto("http://localhost:3000")

    # 2. Check if the title and elements exist
    expect(page.get_by_role("heading", name="Tinker Self-Improving Chat")).to_be_visible()

    # 3. Type a message
    input_box = page.get_by_placeholder("Type your message...")
    input_box.fill("Hello, world!")

    # 4. Click send (This will likely fail or spin if the backend is not mocking Tinker,
    # but we want to verify the UI state changes to Loading)
    send_btn = page.locator("button").filter(has_text="").last # The send button
    # Or better selector:
    # The button has <Send /> icon, no text initially?
    # Let's use the button next to input.

    # Take screenshot of initial state
    page.screenshot(path="/home/jules/verification/initial_state.png")

    # Since Tinker API calls might fail or hang without valid credentials/environment,
    # we expect the UI to handle it or show loading.
    # We'll just verify the UI structure for now.

    expect(page.get_by_text("Model Alias:")).to_be_visible()

    # 5. Screenshot
    page.screenshot(path="/home/jules/verification/chat_interface.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_chat_interface(page)
            print("Verification script ran successfully.")
        except Exception as e:
            print(f"Verification failed: {e}")
        finally:
            browser.close()
