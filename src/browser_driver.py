"""
Live Playwright Browser Automation Driver.
Controls Chrome with the user's persistent profile to execute real, live job applications.
Detects Cloudflare challenges, fills tailored pitch notes, and uploads the resume PDF.
"""
import logging
from pathlib import Path
import re
import time
from typing import Optional, Tuple

from playwright.sync_api import BrowserContext, Page, sync_playwright

logger = logging.getLogger("browser_driver")


def parse_live_salary(text: str) -> Optional[Tuple[float, str]]:
    """
    Extracts compensation string and maximum LPA from header text.
    Returns (max_lpa, raw_salary_string) or None.
    """
    for line in text.split("\n"):
        line_clean = line.strip()
        if not line_clean:
            continue
        # Check for INR salary format like ₹3L – ₹5L or 8-10 LPA
        if ("₹" in line_clean or "lpa" in line_clean.lower() or "lakh" in line_clean.lower()) and len(line_clean) < 80:
            lpa_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lac|l\b)", line_clean.lower())
            if lpa_matches:
                nums = [float(n) for n in lpa_matches]
                return max(nums), line_clean
        # Check for Equity Only / Unpaid
        if "equity only" in line_clean.lower() and len(line_clean) < 60:
            return 0.0, line_clean
        # Check for USD rates (e.g. $40k – $60k)
        if "$" in line_clean and len(line_clean) < 60:
            usd_matches = re.findall(r"\$(\d+)(?:k)?", line_clean.lower())
            if usd_matches:
                nums = [float(n) for n in usd_matches]
                max_usd = max(nums)
                # Convert $k USD to approx LPA (1k USD ~ 0.83 LPA)
                approx_lpa = max_usd * 0.83
                return approx_lpa, line_clean
    return None


class PlaywrightDriver:
    def __init__(self, user_data_dir: Path, headless: bool = False, notifier=None):
        self.user_data_dir = user_data_dir.resolve()
        self.headless = headless
        self.notifier = notifier
        self._playwright = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> BrowserContext:
        if self._context is None:
            if self._playwright is None:
                self._playwright = sync_playwright().start()
            logger.info(f"[BrowserDriver] Launching Chromium with profile: {self.user_data_dir} (headless={self.headless})")
            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=self.headless,
                    slow_mo=100,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
            except Exception as e:
                self.close()
                raise e
        return self._context

    def close(self):
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def check_cloudflare_challenge(self, page: Page, platform: str, url: str) -> bool:
        """Detects if page is blocked by Cloudflare verification."""
        page_title = page.title()
        if "Just a moment..." in page_title or "Cloudflare" in page_title:
            logger.warning(f"[BrowserDriver] Cloudflare verification detected on {platform} ({url})!")
            if self.notifier:
                self.notifier.notify_cloudflare_challenge(platform, url)
            
            # Wait up to 60s for human intervention
            print(f"⚠️ [Cloudflare Alert] Please solve the verification on your screen. Waiting up to 60s...")
            for _ in range(30):
                time.sleep(2)
                if "Just a moment..." not in page.title():
                    logger.info("[BrowserDriver] Cloudflare challenge passed!")
                    return False
            return True
        return False

    def apply_wellfound(
        self,
        url: str,
        pitch_note: str,
        resume_path: Optional[Path] = None,
        min_salary_lpa: float = 10.0,
    ) -> Tuple[bool, str]:
        """
        Executes genuine live application on Wellfound:
        1. Navigates to job URL
        2. Detects Cloudflare
        3. Scrapes and validates live compensation from DOM (aborts if < min_salary_lpa)
        4. Checks if the job itself was already applied (button text 'Applied')
        5. Clicks 'Apply' / 'Apply now' button
        6. Injects tailored pitch note into recruiter note/question textarea
        7. Uploads resume PDF if requested
        8. Clicks 'Send application'
        """
        context = self.start()
        page = context.new_page()
        try:
            logger.info(f"[Wellfound Live] Navigating to {url}...")
            print(f"🌐 Navigating to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Check Cloudflare
            if self.check_cloudflare_challenge(page, "wellfound", url):
                page.close()
                return False, "CLOUDFLARE"

            # Check if job is expired or page not found
            page_content = page.content().lower()
            page_title = page.title().lower()
            if any(k in page_content or k in page_title for k in [
                "no longer available",
                "no longer accepting applications",
                "job has closed",
                "this job is closed",
                "page couldn't be found",
                "404 not found",
            ]):
                print(f"🚫 Listing is expired or closed: {url}")
                page.close()
                return False, "EXPIRED"

            # Check for location/timezone constraint banners
            if any(k in page_content for k in [
                "not accepting applications from your current location",
                "timezone or relocation constraints",
                "cannot accept applications from your country",
            ]):
                print(f"🚫 Ineligible: Recruiter set relocation or timezone constraints ({url}).")
                page.close()
                return False, "INELIGIBLE"

            # Validate Live Compensation from DOM before applying
            h1 = page.locator("h1").first
            if h1.count() > 0:
                try:
                    header_container = h1.locator("xpath=../..")
                    header_text = header_container.inner_text()
                    parsed = parse_live_salary(header_text)
                    if parsed:
                        max_lpa, raw_sal = parsed
                        logger.info(f"[Wellfound Live] Detected live compensation: '{raw_sal}' (~{max_lpa:.1f} LPA)")
                        if max_lpa < min_salary_lpa:
                            print(f"🚫 Live compensation '{raw_sal}' is below target threshold ({min_salary_lpa} LPA). Aborting.")
                            page.close()
                            return False, f"FILTERED_OUT: Live salary '{raw_sal}' is below threshold of {min_salary_lpa} LPA"
                except Exception as e:
                    logger.warning(f"[Wellfound Live] Could not parse header salary: {e}")

            # Check if this specific job was already applied (button says 'Applied')
            already_applied = page.locator("button.styles_applyButton__7gnpI:has-text('Applied'), button:has-text('Applied to this role')")
            if already_applied.count() > 0 and already_applied.first.is_visible():
                logger.info(f"[Wellfound Live] Button says 'Applied'. Already applied to {url}.")
                print(f"ℹ️ Already applied to {url} previously.")
                page.close()
                return True, "ALREADY_APPLIED"

            # Find real Apply button
            apply_btn = None
            for selector in [
                "button.styles_applyButton__7gnpI",
                "button:has-text('Apply now')",
                "button:has-text('Apply')",
            ]:
                loc = page.locator(selector).first
                if loc.is_visible() and "applied" not in loc.inner_text().strip().lower():
                    apply_btn = loc
                    break

            if not apply_btn:
                # Check for external apply link
                ext_link = page.locator("a:has-text('Apply')").first
                if ext_link.is_visible():
                    href = ext_link.get_attribute("href")
                    logger.info(f"[Wellfound Live] External apply link detected: {href}")
                    print(f"⚠️ External apply link: {href}")
                    page.close()
                    return False, f"EXTERNAL_LINK: {href}"
                else:
                    logger.warning(f"[Wellfound Live] Could not find Apply button on {url}.")
                page.close()
                return False, "NO_APPLY_BUTTON"

            print(f"🖱️ Clicking Apply button on Wellfound ({url})...")
            apply_btn.click()
            page.wait_for_timeout(2000)

            # Check inside modal for location/timezone constraint
            dialog = page.locator("div.ReactModal__Content, div[role='dialog']:not([aria-label*='Help Scout'])").first
            modal_content = dialog.inner_text().lower() if (dialog.count() > 0 and dialog.is_visible()) else ""
            if any(k in modal_content for k in [
                "not accepting applications from your current location",
                "timezone or relocation constraints",
                "cannot accept applications",
            ]):
                print(f"🚫 Modal: Ineligible due to location/timezone constraints ({url}).")
                page.close()
                return False, "INELIGIBLE"

            # Modal inspection: fill note textarea
            textareas = page.locator("textarea").all()
            if textareas:
                print(f"✍️ Injecting tailored pitch note into eligible fields...")
                for ta in textareas:
                    try:
                        if ta.is_visible() and ta.is_enabled():
                            ta.fill(pitch_note, timeout=3000)
                            page.wait_for_timeout(500)
                        elif ta.is_visible() and not ta.is_enabled():
                            print("ℹ️ Note field is disabled (custom screening questions require manual answers).")
                            page.close()
                            return False, "ACTION_REQUIRED: Screening questionnaire"
                    except Exception as e:
                        print(f"⚠️ Textarea fill error: {e}")
                        page.close()
                        return False, f"TEXTAREA_ERROR: {e}"

            # Upload resume if file input is present
            if resume_path and resume_path.exists():
                file_inputs = page.locator("input[type='file']").all()
                for fi in file_inputs:
                    try:
                        print(f"📎 Attaching resume PDF: {resume_path.name}")
                        fi.set_input_files(str(resume_path.resolve()))
                        page.wait_for_timeout(1000)
                    except Exception as e:
                        logger.warning(f"[Wellfound Live] Resume upload skipped: {e}")

            # Locate and click 'Send application' / 'Submit application'
            submit_btn = None
            for sub_sel in [
                "button:has-text('Send application')",
                "button:has-text('Submit application')",
                "div[role='dialog'] button:has-text('Send')",
                "div[role='dialog'] button[type='submit']",
            ]:
                loc = page.locator(sub_sel).first
                if loc.is_visible():
                    submit_btn = loc
                    break

            if submit_btn:
                print("🚀 Submitting application ('Send application')...")
                submit_btn.click()
                page.wait_for_timeout(4000)
                print(f"🎉 Successfully submitted live application to {url}!")
                page.close()
                return True, "APPLIED"
            else:
                print("⚠️ Submit button not found in modal.")
                page.close()
                return False, "ACTION_REQUIRED: Submit button not accessible"

        except Exception as e:
            logger.error(f"[Wellfound Live] Error during application: {e}")
            print(f"❌ Error during application: {e}")
            page.close()
            return False, f"ERROR: {e}"
