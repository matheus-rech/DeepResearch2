#!/usr/bin/env python3
"""
Simplified screenshot capture using Playwright
Captures screenshots of the application in different states
"""
import asyncio
import subprocess
import time
import sys
from pathlib import Path
from playwright.async_api import async_playwright
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("e2e_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def capture_screenshots():
    """Capture screenshots of the application"""
    
    # Start the application
    logger.info("Starting application...")
    process = subprocess.Popen(
        [sys.executable, "main.py", "sr-ui"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    logger.info("Waiting for server to start...")
    time.sleep(8)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 1024}
            )
            page = await context.new_page()
            
            # 1. Homepage
            logger.info("Capturing homepage...")
            await page.goto("http://localhost:8000")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCREENSHOT_DIR / "01_homepage.png"), full_page=True)
            
            # 2. File upload area
            logger.info("Capturing file upload section...")
            await page.wait_for_selector('input[type="file"]', timeout=5000)
            await page.screenshot(path=str(SCREENSHOT_DIR / "02_file_upload.png"), full_page=True)
            
            # 3. Try to navigate through tabs if available
            try:
                # Click on academic search tab if exists
                await page.click('button[role="tab"]:has-text("Search Academic Databases")')
                await page.wait_for_timeout(1000)
                await page.screenshot(path=str(SCREENSHOT_DIR / "03_academic_search.png"), full_page=True)
            except:
                logger.info("Academic search tab not found")
            
            # 4. Try sample data workflow
            logger.info("Testing with sample data...")
            
            # Create and upload a test file
            test_ris = """TY  - JOUR
T1  - Sample Article for Testing
AU  - Test Author
PY  - 2023
JO  - Test Journal
AB  - This is a test abstract for the screenshot demo.
ER  - 
"""
            test_file = Path("test_screenshot.ris")
            test_file.write_text(test_ris)
            
            # Go back to file upload tab
            await page.reload()
            await page.wait_for_timeout(2000)
            
            # Upload file
            file_input = await page.wait_for_selector('input[type="file"]')
            await file_input.set_files(str(test_file))
            await page.screenshot(path=str(SCREENSHOT_DIR / "04_file_selected.png"), full_page=True)
            
            # Parse if button is available
            try:
                await page.click('button:has-text("Parse")', timeout=3000)
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(SCREENSHOT_DIR / "05_parse_results.png"), full_page=True)
            except:
                logger.info("Parse button not found or clickable")
            
            # Clean up test file
            test_file.unlink()
            
            await browser.close()
            
    finally:
        # Stop the server
        logger.info("Stopping server...")
        process.terminate()
        process.wait(timeout=5)
    
    logger.info(f"Screenshots saved to {SCREENSHOT_DIR}")
    
    # List all screenshots
    screenshots = sorted(SCREENSHOT_DIR.glob("*.png"))
    logger.info(f"Total screenshots captured: {len(screenshots)}")
    for screenshot in screenshots:
        logger.info(f"  - {screenshot.name}")


async def generate_html_report():
    """Generate HTML report with screenshots"""
    screenshots = sorted(SCREENSHOT_DIR.glob("*.png"))
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>DeepResearch2 - Application Screenshots</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .screenshot-container {
            background: white;
            margin: 20px auto;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 1200px;
        }
        .screenshot-container img {
            width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .screenshot-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #555;
        }
        .info {
            background: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin: 20px auto;
            max-width: 1200px;
        }
    </style>
</head>
<body>
    <h1>DeepResearch2 - Application Screenshots</h1>
    
    <div class="info">
        <p><strong>Application:</strong> DeepResearch2 - Systematic Review Screener</p>
        <p><strong>Description:</strong> MCP Server for ChatGPT Deep Research Integration with Streamlit UI</p>
        <p><strong>Features:</strong> Citation management, PICO criteria configuration, AI-powered screening, multi-format export</p>
        <p><strong>Total Screenshots:</strong> """ + str(len(screenshots)) + """</p>
    </div>
"""
    
    # Add each screenshot
    for i, screenshot in enumerate(screenshots, 1):
        title = screenshot.stem.replace("_", " ").title()
        html_content += f"""
    <div class="screenshot-container">
        <div class="screenshot-title">{i}. {title}</div>
        <img src="{screenshot.name}" alt="{title}">
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    report_path = SCREENSHOT_DIR / "screenshot_report.html"
    report_path.write_text(html_content)
    logger.info(f"HTML report generated: {report_path}")


if __name__ == "__main__":
    logger.info("=== DeepResearch2 Screenshot Capture ===")
    
    # Run screenshot capture
    asyncio.run(capture_screenshots())
    
    # Generate report
    asyncio.run(generate_html_report())
    
    print("\n✓ Screenshots captured successfully!")
    print(f"📁 Screenshots directory: {SCREENSHOT_DIR}")
    print(f"📄 HTML report: {SCREENSHOT_DIR}/screenshot_report.html")
    print(f"\nTo view the report, open: {SCREENSHOT_DIR.absolute()}/screenshot_report.html")