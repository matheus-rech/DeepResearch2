#!/usr/bin/env python3
"""
Comprehensive UI test with Playwright - captures every step with screenshots
"""
import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Test configuration
SCREENSHOT_DIR = Path("test_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

print("🚀 Starting comprehensive DeepResearch2 UI test with screenshots...")

async def comprehensive_ui_test():
    """Complete end-to-end UI test with detailed screenshots"""
    
    # Start the Streamlit server
    print("📡 Starting Streamlit server...")
    server_process = subprocess.Popen(
        [sys.executable, "sr_screener/main.py", "ui"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    # Wait for server to start
    print("⏳ Waiting for server to be ready...")
    await asyncio.sleep(8)  # Give server time to start
    
    try:
        async with async_playwright() as p:
            # Launch browser with visible UI
            print("🌐 Launching browser...")
            browser = await p.chromium.launch(
                headless=False,  # Show the browser!
                slow_mo=1000     # Slow down actions for visibility
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            print("📸 Step 1: Navigate to DeepResearch2 UI")
            await page.goto("http://localhost:8000")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path=SCREENSHOT_DIR / "01_homepage.png", full_page=True)
            print("✅ Screenshot 1: Homepage captured")
            
            print("📸 Step 2: Check main interface elements")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=SCREENSHOT_DIR / "02_main_interface.png", full_page=True)
            print("✅ Screenshot 2: Main interface captured")
            
            # Check for title
            title = await page.locator("h1").first.text_content()
            print(f"📝 Page title: {title}")
            
            # Look for tabs
            print("📸 Step 3: Explore navigation tabs")
            tabs = await page.locator("[data-baseweb='tab']").all()
            if tabs:
                print(f"🏷️  Found {len(tabs)} tabs")
                for i, tab in enumerate(tabs[:4]):  # Click first 4 tabs
                    tab_text = await tab.text_content()
                    print(f"🖱️  Clicking tab: {tab_text}")
                    await tab.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=SCREENSHOT_DIR / f"03_tab_{i+1}_{tab_text.replace(' ', '_').lower()}.png", full_page=True)
                    print(f"✅ Screenshot 3.{i+1}: Tab '{tab_text}' captured")
            
            # Test file upload interface
            print("📸 Step 4: Test file upload interface")
            file_upload = page.locator("input[type='file']")
            if await file_upload.count() > 0:
                print("📁 File upload component found")
                await page.screenshot(path=SCREENSHOT_DIR / "04_file_upload.png", full_page=True)
                print("✅ Screenshot 4: File upload interface captured")
            
            # Look for sample data or example content
            print("📸 Step 5: Check for data display")
            await page.wait_for_timeout(3000)
            
            # Check for any data tables
            tables = await page.locator("[data-testid='stDataFrame']").count()
            if tables > 0:
                print(f"📊 Found {tables} data table(s)")
                await page.screenshot(path=SCREENSHOT_DIR / "05_data_tables.png", full_page=True)
                print("✅ Screenshot 5: Data tables captured")
            
            # Test sidebar if present
            print("📸 Step 6: Check sidebar functionality")
            sidebar = page.locator("[data-testid='stSidebar']")
            if await sidebar.is_visible():
                print("🔧 Sidebar detected")
                await page.screenshot(path=SCREENSHOT_DIR / "06_sidebar.png", full_page=True)
                print("✅ Screenshot 6: Sidebar captured")
                
                # Try to interact with sidebar elements
                sidebar_buttons = await sidebar.locator("button").all()
                if sidebar_buttons:
                    print(f"🔘 Found {len(sidebar_buttons)} sidebar buttons")
                    for i, button in enumerate(sidebar_buttons[:3]):  # Test first 3 buttons
                        button_text = await button.text_content()
                        if button_text and button_text.strip():
                            print(f"🖱️  Clicking sidebar button: {button_text.strip()}")
                            try:
                                await button.click()
                                await page.wait_for_timeout(2000)
                                await page.screenshot(path=SCREENSHOT_DIR / f"07_sidebar_action_{i+1}.png", full_page=True)
                                print(f"✅ Screenshot 7.{i+1}: Sidebar action captured")
                            except Exception as e:
                                print(f"⚠️  Could not click button: {e}")
            
            # Test main content area interactions
            print("📸 Step 8: Test main content interactions")
            buttons = await page.locator("button").all()
            interactive_buttons = []
            
            for button in buttons[:5]:  # Test first 5 buttons
                button_text = await button.text_content()
                if button_text and button_text.strip():
                    try:
                        await button.click()
                        await page.wait_for_timeout(1500)
                        interactive_buttons.append(button_text.strip())
                        print(f"🖱️  Successfully clicked: {button_text.strip()}")
                    except Exception:
                        print(f"⚠️  Could not click: {button_text.strip()}")
            
            if interactive_buttons:
                await page.screenshot(path=SCREENSHOT_DIR / "08_interactive_elements.png", full_page=True)
                print("✅ Screenshot 8: Interactive elements captured")
            
            # Final overview screenshot
            print("📸 Step 9: Final comprehensive overview")
            await page.wait_for_timeout(2000)
            await page.screenshot(path=SCREENSHOT_DIR / "09_final_overview.png", full_page=True)
            print("✅ Screenshot 9: Final overview captured")
            
            # Generate summary report
            print("\n📋 UI Test Summary:")
            print("=" * 50)
            print(f"🌐 Application URL: http://localhost:8000")
            print(f"📝 Page Title: {title if title else 'Not detected'}")
            print(f"🏷️  Navigation Tabs: {len(tabs) if tabs else 0}")
            print(f"📁 File Upload: {'Available' if await file_upload.count() > 0 else 'Not found'}")
            print(f"📊 Data Tables: {tables}")
            print(f"🔧 Sidebar: {'Present' if await sidebar.is_visible() else 'Not found'}")
            print(f"🖱️  Interactive Buttons: {len(interactive_buttons)}")
            print(f"📸 Screenshots Captured: 9+ images in {SCREENSHOT_DIR}/")
            print("=" * 50)
            
            # Keep browser open for a moment to show it's working
            print("✨ Test complete! Browser will remain open for 5 seconds...")
            await page.wait_for_timeout(5000)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop the server
        print("🛑 Stopping Streamlit server...")
        server_process.terminate()
        server_process.wait()
        print("✅ Server stopped")

if __name__ == "__main__":
    asyncio.run(comprehensive_ui_test())