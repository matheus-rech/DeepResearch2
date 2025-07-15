#!/usr/bin/env python3
"""
Comprehensive End-to-End Tests for DeepResearch2 using Playwright
Covers all user flows and captures screenshots of each page/state
"""
import os
import sys
import time
import json
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
import pytest
from playwright.async_api import async_playwright, expect
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e2e_test_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001"
SCREENSHOT_DIR = Path("e2e_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Sample test data
SAMPLE_RIS_CONTENT = """TY  - JOUR
T1  - Effects of continuous glucose monitoring on glycemic control in type 2 diabetes
AU  - Smith, John
AU  - Doe, Jane
PY  - 2023
JO  - Diabetes Care
VL  - 46
IS  - 8
SP  - 1234
EP  - 1245
AB  - This randomized controlled trial examined the effects of continuous glucose monitoring (CGM) on glycemic control in adults with type 2 diabetes. Participants (n=200) were randomly assigned to CGM or standard blood glucose monitoring for 6 months. The CGM group showed significant improvements in HbA1c levels compared to the control group (mean difference -0.5%, p<0.001). Secondary outcomes including time in range and hypoglycemia episodes also favored the CGM group. These findings suggest CGM is an effective tool for improving glycemic control in type 2 diabetes management.
KW  - type 2 diabetes
KW  - continuous glucose monitoring
KW  - glycemic control
KW  - randomized controlled trial
DO  - 10.1234/diabetes.2023.001
ER  - 

TY  - JOUR
T1  - Traditional blood glucose monitoring versus CGM: A meta-analysis
AU  - Johnson, Mary
AU  - Williams, Robert
PY  - 2022
JO  - Journal of Diabetes Research
VL  - 2022
AB  - Background: This meta-analysis compared continuous glucose monitoring (CGM) with traditional self-monitoring of blood glucose (SMBG) in type 2 diabetes management. Methods: We searched multiple databases for randomized controlled trials comparing CGM with SMBG. Primary outcome was change in HbA1c. Results: 15 studies (n=3,456) were included. CGM was associated with greater HbA1c reduction (mean difference -0.35%, 95% CI -0.45 to -0.25). Subgroup analysis showed greater benefits in patients with baseline HbA1c >8%. Conclusion: CGM provides superior glycemic control compared to SMBG in type 2 diabetes, particularly in those with poor baseline control.
KW  - meta-analysis
KW  - continuous glucose monitoring
KW  - type 2 diabetes
KW  - systematic review
ER  -

TY  - JOUR
T1  - Cost-effectiveness of continuous glucose monitoring in diabetes management
AU  - Brown, Lisa
AU  - Davis, Michael
PY  - 2023
JO  - Health Economics Review
VL  - 13
IS  - 1
SP  - 45
AB  - Objective: To evaluate the cost-effectiveness of continuous glucose monitoring (CGM) versus standard care in type 2 diabetes. Methods: A Markov model was developed to estimate lifetime costs and quality-adjusted life years (QALYs) from a healthcare payer perspective. Model inputs were derived from published literature and real-world data. Results: CGM was associated with an incremental cost-effectiveness ratio (ICER) of $32,500 per QALY gained. Sensitivity analyses showed results were most sensitive to CGM device costs and HbA1c improvement magnitude. Conclusions: CGM appears cost-effective for type 2 diabetes management at conventional willingness-to-pay thresholds, though device cost reductions would improve value.
KW  - cost-effectiveness
KW  - economic evaluation
KW  - continuous glucose monitoring
KW  - type 2 diabetes
KW  - Markov model
ER  -
"""


class TestServers:
    """Manage test servers lifecycle"""
    
    def __init__(self):
        self.processes = []
        
    def start_servers(self):
        """Start both MCP and Streamlit servers"""
        logger.info("Starting test servers...")
        
        # Start the combined server
        main_py_path = Path(__file__).parent / "main.py"
        process = subprocess.Popen(
            [sys.executable, str(main_py_path), "sr-ui"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.processes.append(process)
        
        # Wait for servers to be ready
        logger.info("Waiting for servers to start...")
        time.sleep(5)
        
        # Verify servers are running
        import requests
        max_retries = 10
        for i in range(max_retries):
            try:
                # Check Streamlit
                resp = requests.get(BASE_URL)
                if resp.status_code == 200:
                    logger.info("Streamlit server is ready")
                    break
            except:
                if i == max_retries - 1:
                    raise Exception("Streamlit server failed to start")
                time.sleep(2)
                
    def stop_servers(self):
        """Stop all test servers"""
        logger.info("Stopping test servers...")
        for process in self.processes:
            process.terminate()
            process.wait(timeout=5)


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="session")
def test_servers():
    """Start and stop test servers"""
    servers = TestServers()
    servers.start_servers()
    yield servers
    servers.stop_servers()


async def take_screenshot(page, name):
    """Take a screenshot and save it"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = SCREENSHOT_DIR / f"{timestamp}_{name}.png"
    await page.screenshot(path=str(filename), full_page=True)
    logger.info(f"Screenshot saved: {filename}")
    return filename


async def wait_for_streamlit(page):
    """Wait for Streamlit to fully load"""
    await page.wait_for_load_state("networkidle")
    # Wait for Streamlit-specific elements
    await page.wait_for_selector('[data-testid="stApp"]', timeout=30000)
    await page.wait_for_timeout(1000)  # Additional wait for dynamic content


class TestSystematicReviewFlow:
    """Test the complete systematic review workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, browser, test_servers):
        """Test the entire user flow from upload to results"""
        logger.info("Starting complete workflow test")
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1024}
        )
        page = await context.new_page()
        
        try:
            # 1. Navigate to home page
            logger.info("1. Testing home page")
            await page.goto(BASE_URL)
            await wait_for_streamlit(page)
            await take_screenshot(page, "01_home_page")
            
            # Verify we're on the upload step
            await expect(page.locator('text="Step 1: Load Citations"')).to_be_visible()
            
            # 2. Test file upload
            logger.info("2. Testing citation upload")
            
            # Create a temporary RIS file
            ris_file = Path("test_citations.ris")
            ris_file.write_text(SAMPLE_RIS_CONTENT)
            
            # Upload the file
            file_input = page.locator('input[type="file"]')
            await file_input.set_files(str(ris_file))
            await take_screenshot(page, "02_file_uploaded")
            
            # Click parse button
            await page.click('button:has-text("Parse & Load")')
            await page.wait_for_timeout(3000)
            await take_screenshot(page, "03_parsing_results")
            
            # Verify citations were loaded
            await expect(page.locator('text="Successfully parsed"')).to_be_visible(timeout=10000)
            
            # Browse citations
            await page.wait_for_selector('text="Browse Your Citations"')
            await take_screenshot(page, "04_browse_citations")
            
            # Expand a citation to see details
            citation_expanders = page.locator('[data-testid="stExpander"]')
            if await citation_expanders.count() > 0:
                await citation_expanders.first.click()
                await page.wait_for_timeout(500)
                await take_screenshot(page, "05_citation_details")
            
            # Continue to criteria
            await page.click('button:has-text("Continue to Define Criteria")')
            await wait_for_streamlit(page)
            
            # 3. Test criteria configuration
            logger.info("3. Testing criteria configuration")
            await take_screenshot(page, "06_criteria_page")
            
            # Load sample criteria
            await page.click('button:has-text("Load Sample Criteria")')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "07_sample_criteria_loaded")
            
            # Verify fields are populated
            await expect(page.locator('textarea').first).not_to_be_empty()
            
            # Configure additional criteria
            await page.click('label:has-text("English language")')
            await page.click('label:has-text("Peer-reviewed publications")')
            await take_screenshot(page, "08_criteria_configured")
            
            # Save and continue
            await page.click('button:has-text("Save & Continue")')
            await wait_for_streamlit(page)
            
            # 4. Test screening setup
            logger.info("4. Testing screening setup")
            await take_screenshot(page, "09_screening_setup")
            
            # Expand advanced options
            advanced_expander = page.locator('text="Advanced Options"').locator('..')
            await advanced_expander.click()
            await page.wait_for_timeout(500)
            
            # Enable multi-agent mode
            await page.click('label:has-text("Use Multi-Agent Architecture")')
            await take_screenshot(page, "10_advanced_options")
            
            # Start screening
            await page.click('button:has-text("Start Screening")')
            await page.wait_for_timeout(2000)
            await take_screenshot(page, "11_screening_in_progress")
            
            # Wait for screening to complete (with timeout)
            logger.info("Waiting for screening to complete...")
            await expect(page.locator('text="Screening completed"')).to_be_visible(timeout=120000)
            await wait_for_streamlit(page)
            
            # 5. Test results page
            logger.info("5. Testing results page")
            await take_screenshot(page, "12_results_overview")
            
            # Check different tabs
            # Included citations
            await page.click('button[role="tab"]:has-text("Included Citations")')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "13_included_citations")
            
            # Expand an included citation
            included_expanders = page.locator('[data-testid="stExpander"]')
            if await included_expanders.count() > 0:
                await included_expanders.first.click()
                await page.wait_for_timeout(500)
                await take_screenshot(page, "14_included_citation_details")
            
            # Excluded citations
            await page.click('button[role="tab"]:has-text("Excluded Citations")')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "15_excluded_citations")
            
            # ICE Analysis
            await page.click('button[role="tab"]:has-text("ICE Analysis")')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "16_ice_analysis_tab")
            
            # Run ICE analysis
            await page.click('button:has-text("Run ICE Analysis")')
            await page.wait_for_timeout(3000)
            await take_screenshot(page, "17_ice_analysis_results")
            
            # Export results
            await page.click('button[role="tab"]:has-text("Export Results")')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "18_export_options")
            
            # Test different export formats
            export_select = page.locator('select').first
            await export_select.select_option("CSV")
            await take_screenshot(page, "19_export_csv_selected")
            
            logger.info("Complete workflow test finished successfully")
            
        finally:
            # Cleanup
            if ris_file.exists():
                ris_file.unlink()
            await context.close()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, browser, test_servers):
        """Test error handling and edge cases"""
        logger.info("Starting error handling tests")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            await wait_for_streamlit(page)
            
            # Test empty file upload
            logger.info("Testing empty file upload")
            empty_file = Path("empty.ris")
            empty_file.write_text("")
            
            file_input = page.locator('input[type="file"]')
            await file_input.set_files(str(empty_file))
            await page.click('button:has-text("Parse & Load")')
            await page.wait_for_timeout(2000)
            await take_screenshot(page, "20_empty_file_error")
            
            # Test invalid criteria
            logger.info("Testing invalid criteria")
            await page.reload()
            await wait_for_streamlit(page)
            
            # Try to skip upload step
            await page.goto(f"{BASE_URL}?current_step=criteria")
            await page.wait_for_timeout(2000)
            await take_screenshot(page, "21_invalid_navigation")
            
        finally:
            if empty_file.exists():
                empty_file.unlink()
            await context.close()
    
    @pytest.mark.asyncio
    async def test_database_search(self, browser, test_servers):
        """Test academic database search functionality"""
        logger.info("Starting database search test")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(BASE_URL)
            await wait_for_streamlit(page)
            
            # Click on search tab
            await page.click('button[role="tab"]:has-text("Search Academic Databases")')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "22_search_tab")
            
            # Note: Actual search might fail without API keys, but we can test the UI
            
        finally:
            await context.close()


async def generate_test_report():
    """Generate a comprehensive test report"""
    logger.info("Generating test report...")
    
    report = {
        "test_run": datetime.now().isoformat(),
        "screenshots": sorted([str(f) for f in SCREENSHOT_DIR.glob("*.png")]),
        "total_screenshots": len(list(SCREENSHOT_DIR.glob("*.png"))),
        "log_file": "e2e_test_log.txt"
    }
    
    report_file = Path("e2e_test_report.json")
    report_file.write_text(json.dumps(report, indent=2))
    
    # Create HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>E2E Test Report - DeepResearch2</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .screenshot {{ margin: 20px 0; border: 1px solid #ddd; padding: 10px; }}
            .screenshot img {{ max-width: 100%; height: auto; }}
            .info {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>End-to-End Test Report</h1>
        <div class="info">
            <p><strong>Test Run:</strong> {report['test_run']}</p>
            <p><strong>Total Screenshots:</strong> {report['total_screenshots']}</p>
            <p><strong>Log File:</strong> <a href="{report['log_file']}">{report['log_file']}</a></p>
        </div>
        
        <h2>Screenshots</h2>
    """
    
    for screenshot in report['screenshots']:
        name = Path(screenshot).name
        html_content += f"""
        <div class="screenshot">
            <h3>{name}</h3>
            <img src="{screenshot}" alt="{name}">
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    report_html = Path("e2e_test_report.html")
    report_html.write_text(html_content)
    logger.info(f"Test report generated: {report_html}")


if __name__ == "__main__":
    # Run the tests
    logger.info("Starting E2E test suite for DeepResearch2")
    
    # Run pytest with detailed output
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "--log-cli-level=INFO"
    ])
    
    # Generate report
    asyncio.run(generate_test_report())
    
    logger.info(f"E2E tests completed with exit code: {exit_code}")
    print(f"\nTest screenshots saved to: {SCREENSHOT_DIR}")
    print(f"Test report available at: e2e_test_report.html")
    print(f"Test logs available at: e2e_test_log.txt")