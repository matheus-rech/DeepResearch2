#!/usr/bin/env python3
"""
Enhanced Playwright script for comprehensive DeepResearch2 UI analysis
"""
import asyncio
import subprocess
import time
import os
import json
from playwright.async_api import async_playwright

async def analyze_streamlit_app():
    """Enhanced analysis of the Streamlit application"""
    
    # Set up environment
    env = os.environ.copy()
    env['PATH'] = f"{os.path.join(os.getcwd(), 'deepresearch_env', 'bin')}:{env['PATH']}"
    
    # Start the test Streamlit app first
    print("🚀 Starting test Streamlit app...")
    process = subprocess.Popen(
        [os.path.join(os.getcwd(), 'deepresearch_env', 'bin', 'streamlit'), 
         'run', 'test_streamlit.py', '--server.port=8000'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    print("⏳ Waiting for Streamlit server to start...")
    time.sleep(8)
    
    try:
        async with async_playwright() as p:
            # Launch browser in non-headless mode so you can see the analysis
            browser = await p.chromium.launch(
                headless=False,
                args=['--start-maximized']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            print("🌐 Navigating to Streamlit app...")
            await page.goto("http://localhost:8000", wait_until="networkidle", timeout=30000)
            
            # Wait for the app to fully load
            await page.wait_for_timeout(3000)
            
            print("\n📸 Starting comprehensive UI analysis...")
            
            # 1. Take full page screenshot
            await page.screenshot(path="screenshots/test_app_main.png", full_page=True)
            print("✅ Captured main page screenshot")
            
            # 2. Analyze page structure
            print("\n🏗️ Analyzing page structure...")
            
            # Get page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Check for Streamlit elements
            streamlit_elements = {
                'header': await page.locator("h1").count(),
                'subheaders': await page.locator("h2, h3").count(),
                'buttons': await page.locator("button").count(),
                'inputs': await page.locator("input").count(),
                'selects': await page.locator("select").count(),
                'file_uploads': await page.locator("[data-testid*='fileUpload']").count(),
                'metrics': await page.locator("[data-testid='metric']").count(),
                'dataframes': await page.locator("[data-testid='stDataFrame']").count(),
                'charts': await page.locator("[data-testid='stVegaLiteChart']").count()
            }
            
            print("📊 UI Elements found:")
            for element, count in streamlit_elements.items():
                print(f"  - {element.title()}: {count}")
            
            # 3. Test sidebar
            print("\n📋 Analyzing sidebar...")
            sidebar = page.locator("[data-testid='stSidebar']")
            if await sidebar.is_visible():
                print("✅ Sidebar is visible")
                await page.screenshot(path="screenshots/sidebar_view.png")
                
                # Check sidebar content
                sidebar_buttons = await sidebar.locator("button").count()
                sidebar_selects = await sidebar.locator("select").count()
                sidebar_sliders = await sidebar.locator("[data-testid='stSlider']").count()
                print(f"   - Sidebar buttons: {sidebar_buttons}")
                print(f"   - Sidebar selects: {sidebar_selects}")
                print(f"   - Sidebar sliders: {sidebar_sliders}")
            else:
                print("❌ No sidebar found")
            
            # 4. Test tabs functionality
            print("\n🗂️ Testing tabs...")
            tabs = await page.locator("[data-baseweb='tab']").all()
            if tabs:
                print(f"✅ Found {len(tabs)} tabs")
                for i, tab in enumerate(tabs):
                    tab_text = await tab.text_content()
                    print(f"   - Tab {i+1}: {tab_text}")
                    
                    # Click each tab and take screenshot
                    await tab.click()
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path=f"screenshots/tab_{i+1}_{tab_text.replace(' ', '_')}.png")
                    print(f"     ✅ Clicked and captured tab {i+1}")
            else:
                print("❌ No tabs found")
            
            # 5. Test interactive elements
            print("\n🎮 Testing interactive elements...")
            
            # Test button clicks
            buttons = await page.locator("button").all()
            clickable_buttons = []
            for i, button in enumerate(buttons[:3]):  # Test first 3 buttons
                button_text = await button.text_content()
                if button_text and button_text.strip():
                    try:
                        await button.click()
                        await page.wait_for_timeout(500)
                        clickable_buttons.append(button_text.strip())
                        print(f"   ✅ Successfully clicked button: {button_text.strip()}")
                    except Exception:
                        print(f"   ❌ Could not click button: {button_text.strip()}")
            
            # Test file upload
            file_upload = page.locator("input[type='file']")
            if await file_upload.count() > 0:
                print("   ✅ File upload component found")
                await page.screenshot(path="screenshots/file_upload_area.png")
            
            # Test text input
            text_inputs = await page.locator("input[type='text']").all()
            if text_inputs:
                try:
                    await text_inputs[0].fill("Test input text")
                    await page.wait_for_timeout(500)
                    print("   ✅ Successfully entered text in input field")
                except Exception as e:
                    print(f"   ❌ Could not enter text: {e}")
            
            # 6. Check for any errors or warnings
            print("\n⚠️ Checking for errors...")
            error_elements = await page.locator(".stAlert, [data-testid='stAlert'], .error").count()
            if error_elements > 0:
                print(f"   ⚠️ Found {error_elements} error/alert elements")
                await page.screenshot(path="screenshots/errors_detected.png")
            else:
                print("   ✅ No errors detected")
            
            # 7. Performance analysis
            print("\n⚡ Performance analysis...")
            performance_data = await page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        loadTime: timing.loadEventEnd - timing.navigationStart,
                        domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
                        resourcesLoaded: performance.getEntriesByType('resource').length
                    };
                }
            """)
            
            print(f"   - Page load time: {performance_data['loadTime']}ms")
            print(f"   - DOM ready time: {performance_data['domReady']}ms")
            print(f"   - Resources loaded: {performance_data['resourcesLoaded']}")
            
            # 8. Generate final report
            report = {
                "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "page_info": {
                    "title": title,
                    "url": "http://localhost:8000",
                    "application": "DeepResearch2 Test Interface"
                },
                "ui_elements": streamlit_elements,
                "functionality": {
                    "tabs_working": len(tabs) > 0,
                    "sidebar_present": await sidebar.is_visible() if 'sidebar' in locals() else False,
                    "interactive_buttons": len(clickable_buttons),
                    "file_upload_available": await file_upload.count() > 0 if 'file_upload' in locals() else False
                },
                "performance": performance_data,
                "screenshots_captured": [
                    "test_app_main.png",
                    "sidebar_view.png" if await sidebar.is_visible() else None,
                    *[f"tab_{i+1}_{tab.text_content().replace(' ', '_')}.png" for i, tab in enumerate(tabs)]
                ]
            }
            
            # Save report
            with open("screenshots/analysis_report.json", "w") as f:
                json.dump(report, f, indent=2)
            
            print("\n📊 ANALYSIS COMPLETE!")
            print("=" * 60)
            print("DeepResearch2 Streamlit App Analysis Report")
            print("=" * 60)
            print(f"✅ Application: {report['page_info']['application']}")
            print(f"🌐 URL: {report['page_info']['url']}")
            print(f"📄 Page Title: {report['page_info']['title']}")
            print("\n🏗️ UI Components:")
            for element, count in report['ui_elements'].items():
                status = "✅" if count > 0 else "❌"
                print(f"   {status} {element.title()}: {count}")
            
            print("\n🎮 Functionality:")
            print(f"   {'✅' if report['functionality']['tabs_working'] else '❌'} Tabs: {'Working' if report['functionality']['tabs_working'] else 'Not found'}")
            print(f"   {'✅' if report['functionality']['sidebar_present'] else '❌'} Sidebar: {'Present' if report['functionality']['sidebar_present'] else 'Not found'}")
            print(f"   {'✅' if report['functionality']['interactive_buttons'] > 0 else '❌'} Interactive Buttons: {report['functionality']['interactive_buttons']}")
            print(f"   {'✅' if report['functionality']['file_upload_available'] else '❌'} File Upload: {'Available' if report['functionality']['file_upload_available'] else 'Not available'}")
            
            print("\n⚡ Performance:")
            print(f"   📊 Load Time: {report['performance']['loadTime']}ms")
            print(f"   🏗️ DOM Ready: {report['performance']['domReady']}ms")
            print(f"   📦 Resources: {report['performance']['resourcesLoaded']}")
            
            print("\n📸 Screenshots saved to screenshots/ directory")
            print("📋 Full report saved to screenshots/analysis_report.json")
            print("=" * 60)
            
            # Keep browser open for manual inspection
            print("\n👀 Browser will remain open for 15 seconds for manual inspection...")
            await page.wait_for_timeout(15000)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        process.terminate()
        process.wait()
        print("\n🛑 Streamlit server stopped")

if __name__ == "__main__":
    # Ensure screenshots directory exists
    os.makedirs("screenshots", exist_ok=True)
    
    # Run the enhanced analysis
    asyncio.run(analyze_streamlit_app())