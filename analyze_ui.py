#!/usr/bin/env python3
"""
Playwright script to analyze DeepResearch2 UI
"""
import asyncio
import subprocess
import time
import os
from playwright.async_api import async_playwright

async def analyze_deepresearch_ui():
    """Launch and analyze the DeepResearch2 Streamlit UI"""
    
    # First, let's launch the Streamlit app in the background
    env = os.environ.copy()
    env['PATH'] = f"{os.path.join(os.getcwd(), 'deepresearch_env', 'bin')}:{env['PATH']}"
    
    process = subprocess.Popen(
        [os.path.join(os.getcwd(), 'deepresearch_env', 'bin', 'python'), 
         'sr_screener/main.py', 'ui'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for the server to start
    print("Waiting for Streamlit server to start...")
    time.sleep(5)
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            # Navigate to the Streamlit app
            print("Navigating to http://localhost:8000")
            await page.goto("http://localhost:8000", wait_until="networkidle")
            
            # Wait for the app to fully load
            await page.wait_for_timeout(3000)
            
            # Take screenshots and analyze the UI
            print("\n📸 Capturing screenshots and analyzing UI elements...")
            
            # 1. Main page screenshot
            await page.screenshot(path="screenshots/01_main_page.png", full_page=True)
            print("✓ Captured main page screenshot")
            
            # 2. Look for key UI elements
            print("\n🔍 Analyzing UI Components:")
            
            # Check for title/header
            try:
                title = await page.locator("h1, [data-testid='stTitle']").first.text_content()
                print(f"✓ Title: {title}")
            except:
                print("✗ No title found")
            
            # Check for sidebar
            sidebar = page.locator("[data-testid='stSidebar']")
            if await sidebar.is_visible():
                print("✓ Sidebar detected")
                await page.screenshot(path="screenshots/02_sidebar.png", full_page=False)
                
                # Look for sidebar elements
                sidebar_items = await sidebar.locator("div").all_text_contents()
                print(f"  - Sidebar items: {len(sidebar_items)} elements found")
            
            # Check for file upload components
            file_uploaders = await page.locator("[data-testid='stFileUploadDropzone']").count()
            if file_uploaders > 0:
                print(f"✓ File upload components: {file_uploaders} found")
                await page.screenshot(path="screenshots/03_file_upload.png", full_page=False)
            
            # Check for buttons
            buttons = await page.locator("button").all()
            print(f"✓ Buttons found: {len(buttons)}")
            for i, button in enumerate(buttons[:5]):  # First 5 buttons
                text = await button.text_content()
                if text:
                    print(f"  - Button {i+1}: {text.strip()}")
            
            # Check for data tables
            tables = await page.locator("[data-testid='stDataFrame']").count()
            if tables > 0:
                print(f"✓ Data tables: {tables} found")
                await page.screenshot(path="screenshots/04_data_tables.png", full_page=False)
            
            # Check for tabs
            tabs = await page.locator("[data-baseweb='tab']").all()
            if tabs:
                print(f"✓ Tabs found: {len(tabs)}")
                for i, tab in enumerate(tabs):
                    text = await tab.text_content()
                    print(f"  - Tab {i+1}: {text}")
                    
            # Check for forms/inputs
            inputs = await page.locator("input[type='text'], textarea").count()
            if inputs > 0:
                print(f"✓ Input fields: {inputs} found")
            
            # 3. Interact with the UI (if possible)
            print("\n🎯 Testing UI Interactions:")
            
            # Try clicking on tabs if they exist
            if tabs:
                for i, tab in enumerate(tabs[:3]):  # Click first 3 tabs
                    await tab.click()
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path=f"screenshots/05_tab_{i+1}.png", full_page=False)
                    print(f"✓ Clicked tab {i+1} and captured screenshot")
            
            # Check for any error messages
            errors = await page.locator(".stAlert, [data-testid='stAlert']").count()
            if errors > 0:
                print(f"⚠️  Alert/Error messages found: {errors}")
                error_texts = await page.locator(".stAlert, [data-testid='stAlert']").all_text_contents()
                for error in error_texts:
                    print(f"   - {error.strip()}")
            
            # 4. Generate summary report
            print("\n📊 UI Analysis Summary:")
            print("=" * 50)
            print("DeepResearch2 UI Analysis Report")
            print("=" * 50)
            print(f"• Application Type: Streamlit Web App")
            print(f"• URL: http://localhost:8000")
            print(f"• Main Features Detected:")
            print(f"  - File Upload Capability: {'Yes' if file_uploaders > 0 else 'No'}")
            print(f"  - Data Tables: {'Yes' if tables > 0 else 'No'}")
            print(f"  - Interactive Tabs: {'Yes' if tabs else 'No'}")
            print(f"  - Form Inputs: {'Yes' if inputs > 0 else 'No'}")
            print(f"  - Sidebar Navigation: {'Yes' if await sidebar.is_visible() else 'No'}")
            print("\n• Purpose: Systematic Review Citation Management Tool")
            print("• Integration: MCP Server for ChatGPT Deep Research")
            print("=" * 50)
            
            # Keep browser open for manual inspection
            print("\n✅ Analysis complete! Browser will remain open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
            await browser.close()
            
    finally:
        # Terminate the Streamlit process
        process.terminate()
        process.wait()
        print("\n🛑 Streamlit server stopped")

if __name__ == "__main__":
    # Create screenshots directory
    os.makedirs("screenshots", exist_ok=True)
    
    # Run the analysis
    asyncio.run(analyze_deepresearch_ui())