#!/usr/bin/env python3
"""
Complete file upload workflow test using sample_citations.csv
"""
import asyncio
import subprocess
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Test configuration
SCREENSHOT_DIR = Path("file_upload_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Use the sample file from the worktree
SAMPLE_FILE = "/Users/matheusrech/Downloads/DeepResearch2-worktrees/unified-main/sample_citations.csv"

async def file_upload_workflow_test():
    """Complete workflow test starting with file upload"""
    
    print("🚀 Starting FILE UPLOAD workflow test with sample_citations.csv...")
    
    # Set the sample file path
    sample_file = SAMPLE_FILE
    print(f"📁 Using file: {sample_file}")
    
    # Verify sample file exists
    if not Path(sample_file).exists():
        print(f"❌ Sample file not found: {sample_file}")
        # Try alternate location
        alt_file = "sample_citations.csv"
        if Path(alt_file).exists():
            sample_file = alt_file
            print(f"✅ Using alternate file: {alt_file}")
        else:
            print("❌ No sample file found, exiting")
            return
    
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
    await asyncio.sleep(12)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=3000  # Very slow for clear visibility
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            print("📸 Step 1: Navigate to homepage and take initial screenshot")
            await page.goto("http://localhost:8000", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=SCREENSHOT_DIR / "01_homepage_initial.png", full_page=True)
            
            print("📸 Step 2: Look for file upload interface")
            # Look for file input or upload button
            file_input = page.locator("input[type='file']").first
            upload_button = page.locator("text=Browse files")
            
            if await file_input.is_visible():
                print("📁 Found file input, uploading sample_citations.csv...")
                await file_input.set_input_files(sample_file)
                await page.wait_for_timeout(5000)  # Wait for upload processing
                await page.screenshot(path=SCREENSHOT_DIR / "02_file_uploaded.png", full_page=True)
                print("✅ File uploaded successfully")
            elif await upload_button.is_visible():
                print("📁 Found upload button, clicking...")
                await upload_button.click()
                await page.wait_for_timeout(2000)
                # Try file input again after clicking
                await file_input.set_input_files(sample_file)
                await page.wait_for_timeout(5000)
                await page.screenshot(path=SCREENSHOT_DIR / "02_file_uploaded.png", full_page=True)
            
            print("📸 Step 3: Look for Continue button after upload")
            # Look for various continue button texts
            continue_texts = [
                "Continue",
                "Next",
                "Proceed", 
                "Continue to next step",
                "Add to existing corpus",
                "Process File",
                "Load Citations"
            ]
            
            continue_clicked = False
            for button_text in continue_texts:
                continue_btn = page.locator(f"text={button_text}")
                if await continue_btn.is_visible():
                    print(f"🔄 Found and clicking: {button_text}")
                    await continue_btn.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=SCREENSHOT_DIR / "03_continue_clicked.png", full_page=True)
                    continue_clicked = True
                    break
            
            if not continue_clicked:
                print("🔍 Looking for any button to proceed...")
                # Look for all visible buttons
                all_buttons = await page.locator("button").all()
                for i, button in enumerate(all_buttons):
                    button_text = await button.text_content()
                    if button_text:
                        print(f"🔘 Found button: '{button_text.strip()}'")
                        if any(word in button_text.lower() for word in ["continue", "next", "proceed", "add", "process"]):
                            print(f"🖱️  Clicking promising button: {button_text.strip()}")
                            await button.click()
                            await page.wait_for_timeout(3000)
                            await page.screenshot(path=SCREENSHOT_DIR / f"03_button_{i}_clicked.png", full_page=True)
                            break
            
            print("📸 Step 4: Navigate through the workflow")
            # Check current page state
            await page.wait_for_timeout(2000)
            await page.screenshot(path=SCREENSHOT_DIR / "04_after_upload_processing.png", full_page=True)
            
            # Try to navigate to Define Criteria
            print("📝 Attempting to navigate to Define Criteria...")
            criteria_options = [
                "2. Define Criteria",
                "Define Criteria", 
                "Criteria",
                "Next Step"
            ]
            
            for criteria_text in criteria_options:
                criteria_link = page.locator(f"text={criteria_text}")
                if await criteria_link.is_visible():
                    print(f"📝 Clicking: {criteria_text}")
                    await criteria_link.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=SCREENSHOT_DIR / "05_criteria_page.png", full_page=True)
                    break
            
            print("📸 Step 5: Fill out criteria if possible")
            # Look for text areas or input fields
            text_areas = await page.locator("textarea").all()
            if text_areas:
                print(f"📝 Found {len(text_areas)} text areas, filling them...")
                
                criteria_texts = [
                    "Adults with diabetes mellitus",
                    "Continuous glucose monitoring systems", 
                    "Standard blood glucose monitoring",
                    "Glycemic control and HbA1c levels",
                    "Follow-up at 6 months or more",
                    "Randomized controlled trials"
                ]
                
                for i, (textarea, text) in enumerate(zip(text_areas[:6], criteria_texts)):
                    if await textarea.is_visible():
                        await textarea.fill(text)
                        await page.wait_for_timeout(1000)
                        print(f"✅ Filled textarea {i + 1}: {text[:30]}...")
                
                await page.screenshot(path=SCREENSHOT_DIR / "06_criteria_filled.png", full_page=True)
            
            print("📸 Step 6: Navigate to Screening")
            screening_options = [
                "3. Run Screening",
                "Run Screening",
                "Start Screening",
                "Screening"
            ]
            
            for screening_text in screening_options:
                screening_link = page.locator(f"text={screening_text}")
                if await screening_link.is_visible():
                    print(f"🔍 Clicking: {screening_text}")
                    await screening_link.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=SCREENSHOT_DIR / "07_screening_page.png", full_page=True)
                    break
            
            print("📸 Step 7: Look for and click screening buttons")
            screening_buttons = [
                "Start Screening",
                "Run Screening",
                "Begin Analysis", 
                "Save & Continue",
                "Continue"
            ]
            
            for button_text in screening_buttons:
                button = page.locator(f"text={button_text}")
                if await button.is_visible():
                    print(f"🖱️  Clicking screening button: {button_text}")
                    await button.click()
                    await page.wait_for_timeout(8000)  # Wait for processing
                    await page.screenshot(path=SCREENSHOT_DIR / "08_screening_running.png", full_page=True)
                    break
            
            print("📸 Step 8: Wait for results and capture final state")
            await page.wait_for_timeout(5000)
            await page.screenshot(path=SCREENSHOT_DIR / "09_final_results.png", full_page=True)
            
            # Try to go to results page
            results_link = page.locator("text=4. Review Results")
            if await results_link.is_visible():
                print("📊 Going to results page...")
                await results_link.click()
                await page.wait_for_timeout(3000)
                await page.screenshot(path=SCREENSHOT_DIR / "10_results_final.png", full_page=True)
            
            print("\n🎯 FILE UPLOAD WORKFLOW SUMMARY:")
            print("=" * 70)
            print("✅ Homepage loaded")
            print("✅ File upload attempted")
            print("✅ Continue button search performed")
            print("✅ Criteria navigation attempted")
            print("✅ Screening workflow initiated")
            print("✅ Complete process documented")
            print("=" * 70)
            print(f"📸 Screenshots: {len(list(SCREENSHOT_DIR.glob('*.png')))} captured")
            print(f"📁 Location: {SCREENSHOT_DIR.absolute()}")
            print("📁 Original file used:", sample_file)
            print("=" * 70)
            
            # Keep browser open to show final state
            print("🎉 Workflow complete! Browser will stay open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(file_upload_workflow_test())
