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
        lowered = line_clean.lower()
        # Check for INR salary format like ₹3L – ₹5L, 8-10 LPA, or 12 - 18 Lacs
        if any(tok in lowered for tok in ["₹", "lpa", "lakh", "lakhs", "lac", "lacs"]) and len(line_clean) < 100:
            lpa_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?|l\b)", lowered)
            range_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?|l\b)", lowered)
            nums = []
            if lpa_matches:
                nums.extend([float(n) for n in lpa_matches])
            for r1, r2 in range_matches:
                nums.extend([float(r1), float(r2)])
            if nums:
                return max(nums), line_clean
        # Check for Equity Only / Unpaid
        if "equity only" in lowered and len(line_clean) < 60:
            return 0.0, line_clean
        # Check for USD rates (e.g. $40k – $60k)
        if "$" in line_clean and len(line_clean) < 60:
            usd_matches = re.findall(r"\$(\d+)(?:k)?", lowered)
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

    def handle_google_oauth(
        self,
        page: Page,
        trigger_locator=None,
        target_domain: str = "",
        timeout_ms: int = 25000,
    ) -> bool:
        """
        Handles Google OAuth single sign-on when prompted on Cutshort, Instahyre, etc.
        Leverages the persistent browser profile where the user's Google account is already logged in.
        Handles both popup-based OAuth and direct in-page redirection.
        """
        try:
            popup_page = None
            if trigger_locator:
                print(f"🔑 Clicking Google Sign-In button...")
                try:
                    with page.expect_popup(timeout=5000) as popup_info:
                        trigger_locator.click()
                    popup_page = popup_info.value
                except Exception:
                    # If no popup opened, trigger may have initiated in-page redirect or direct API auth
                    pass

            target_page = popup_page if popup_page else page

            # Wait for either accounts.google.com or redirect back
            start_t = time.time()
            while time.time() - start_t < (timeout_ms / 1000):
                curr_url = target_page.url.lower()

                if "accounts.google.com" in curr_url:
                    print("🔑 In Google OAuth flow...")
                    target_page.wait_for_timeout(2000)

                    # 1. Look for candidate account in account chooser:
                    candidate_account = None
                    for sel in [
                        "div[data-identifier*='jkfrancis2003']",
                        "div[data-email*='jkfrancis2003']",
                        "div:has-text('jkfrancis2003@gmail.com')",
                        "div:has-text('Kaushal Francis')",
                        "div[role='link'][data-identifier]",
                        "li[data-identifier]",
                        "div[data-authuser]",
                    ]:
                        loc = target_page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            candidate_account = loc
                            break

                    if candidate_account:
                        account_label = candidate_account.inner_text().strip().split("\n")[0]
                        print(f"👉 Selecting Google Account: {account_label[:40]}...")
                        candidate_account.click()
                        target_page.wait_for_timeout(2500)

                    # 2. Check for 'Continue' / 'Allow' / 'Confirm' consent button
                    for consent_sel in [
                        "button:has-text('Continue')",
                        "button:has-text('Allow')",
                        "button:has-text('Confirm')",
                        "#submit_approve_access",
                        "button:has-text('Agree')",
                    ]:
                        c_btn = target_page.locator(consent_sel).first
                        if c_btn.count() > 0 and c_btn.is_visible():
                            print("👉 Approving Google OAuth consent ('Continue')...")
                            c_btn.click()
                            target_page.wait_for_timeout(2000)
                            break

                # If popup was closed or page redirected back to target_domain
                if popup_page:
                    if popup_page.is_closed():
                        print("🔑 Google OAuth popup completed.")
                        page.wait_for_timeout(2500)
                        return True
                    elif target_domain and target_domain in popup_page.url.lower():
                        popup_page.close()
                        page.wait_for_timeout(2500)
                        return True
                else:
                    if target_domain and target_domain in target_page.url.lower() and "accounts.google.com" not in target_page.url.lower():
                        print(f"🔑 Successfully authenticated with Google on {target_domain}.")
                        return True

                time.sleep(1)

            return True
        except Exception as e:
            logger.warning(f"[OAuth] Google OAuth flow handling note: {e}")
            return False

    def ensure_cutshort_logged_in(self, page: Page) -> bool:
        """
        Verifies Cutshort login session, performing Google OAuth login if needed.
        """
        try:
            page_content = page.content().lower()
            if any(k in page_content for k in ["my applications", "candidate/discover", "logout", "log out"]) or page.locator("a[href*='/candidate/'], a[href*='/profile']").count() > 0:
                logger.info("[Cutshort] Already authenticated.")
                return True

            logger.info("[Cutshort] Checking login status...")
            login_url = "https://cutshort.io/login"
            if "cutshort.io/login" not in page.url:
                page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)

            # Check Cloudflare
            if self.check_cloudflare_challenge(page, "cutshort", login_url):
                return False

            # Find Google OAuth button
            google_btn = None
            for sel in [
                "button:has-text('Continue with Google')",
                "button:has-text('Sign in with Google')",
                "button:has-text('Log in with Google')",
                "button:has-text('Google')",
                "a:has-text('Continue with Google')",
                "a:has-text('Sign in with Google')",
                "div[data-provider='google']",
                "[aria-label*='Google']",
            ]:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    google_btn = loc
                    break

            if google_btn:
                print("🔑 Initiating Google OAuth sign-in on Cutshort...")
                self.handle_google_oauth(page, trigger_locator=google_btn, target_domain="cutshort.io")
                page.wait_for_timeout(3000)
                return True
            else:
                logger.info("[Cutshort] Already on authenticated page or Google button omitted.")
                return True
        except Exception as e:
            logger.error(f"[Cutshort] Login check note: {e}")
            return False

    def apply_cutshort(
        self,
        url: str,
        pitch_note: str,
        resume_path: Optional[Path] = None,
        min_salary_lpa: float = 10.0,
    ) -> Tuple[bool, str]:
        """
        Executes live application on Cutshort (cutshort.io):
        1. Navigates to job URL
        2. Detects Cloudflare / anti-bot
        3. Scrapes and validates live compensation from DOM (aborts if < min_salary_lpa)
        4. Verifies Cutshort session; performs Google OAuth if unauthenticated
        5. Checks if already applied
        6. Clicks Apply / Interested button
        7. Injects tailored pitch note into message/pitch field
        8. Uploads resume PDF if requested
        9. Submits application
        """
        context = self.start()
        page = context.new_page()
        try:
            logger.info(f"[Cutshort Live] Navigating to {url}...")
            print(f"🌐 Navigating to Cutshort: {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Check Cloudflare
            if self.check_cloudflare_challenge(page, "cutshort", url):
                page.close()
                return False, "CLOUDFLARE"

            # Check if job is expired or closed
            page_content = page.content().lower()
            page_title = page.title().lower()
            if any(k in page_content or k in page_title for k in [
                "no longer accepting applications",
                "this job has expired",
                "job is closed",
                "this job is closed",
                "page not found",
                "404 not found",
            ]):
                print(f"🚫 Listing is expired or closed: {url}")
                page.close()
                return False, "EXPIRED"

            # Validate Live Compensation from DOM
            try:
                page_text = page.locator("body").inner_text()
                parsed = parse_live_salary(page_text)
                if parsed:
                    max_lpa, raw_sal = parsed
                    logger.info(f"[Cutshort Live] Detected live compensation: '{raw_sal}' (~{max_lpa:.1f} LPA)")
                    if max_lpa < min_salary_lpa:
                        print(f"🚫 Live compensation '{raw_sal}' is below target threshold ({min_salary_lpa} LPA). Aborting.")
                        page.close()
                        return False, f"FILTERED_OUT: Live salary '{raw_sal}' is below threshold of {min_salary_lpa} LPA"
            except Exception as e:
                logger.warning(f"[Cutshort Live] Salary check warning: {e}")

            # Check / Ensure Cutshort authentication via Google OAuth
            login_needed = False
            for login_sel in ["button:has-text('Sign In')", "button:has-text('Log In')", "a:has-text('Sign In')", "a:has-text('Log In')"]:
                if page.locator(login_sel).first.is_visible():
                    login_needed = True
                    break

            if login_needed:
                self.ensure_cutshort_logged_in(page)
                if "cutshort.io/job" not in page.url:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)

            # Check if already applied
            already_applied = page.locator(
                "button:has-text('View conversation'), button:has-text('Applied'), button:has-text('Application sent'), button:has-text('Already Applied'), div:has-text('Application sent'), button:has-text('Contacted')"
            )
            if already_applied.count() > 0 and already_applied.first.is_visible():
                logger.info(f"[Cutshort Live] Already applied to {url}.")
                print(f"ℹ️ Already applied to Cutshort role: {url}")
                page.close()
                return True, "ALREADY_APPLIED"

            # Find Apply / Interested button
            apply_btn = None
            for selector in [
                "button:has-text('Apply to this job')",
                "button:has-text('Apply now')",
                "button:has-text('Interested & Apply')",
                "button:has-text('Apply')",
                "button:has-text('I am interested')",
                "button:has-text('Send message')",
                "button:has-text('Quick Apply')",
                "[data-testid*='apply']",
            ]:
                loc = page.locator(selector).first
                if loc.count() > 0 and loc.is_visible() and "applied" not in loc.inner_text().strip().lower():
                    apply_btn = loc
                    break

            if not apply_btn:
                # Check for external apply link
                ext_link = page.locator("a:has-text('Apply on company website'), a:has-text('Apply externally')").first
                if ext_link.count() > 0 and ext_link.is_visible():
                    href = ext_link.get_attribute("href")
                    print(f"⚠️ External apply link: {href}")
                    page.close()
                    return False, f"EXTERNAL_LINK: {href}"
                else:
                    logger.warning(f"[Cutshort Live] Could not find Apply button on {url}.")
                    page.close()
                    return False, "NO_APPLY_BUTTON"

            print(f"🖱️ Clicking Apply / Interested button on Cutshort ({url})...")
            try:
                apply_btn.click(timeout=3000)
            except Exception:
                apply_btn.dispatch_event("click")
            page.wait_for_timeout(2500)

            # If clicking 'Apply to this job' redirected to candidate card with 'Apply now'
            apply_now_card = page.locator("button:has-text('Apply now')").first
            if apply_now_card.count() > 0 and apply_now_card.is_visible():
                print(f"🖱️ Clicking 'Apply now' on Cutshort card...")
                try:
                    apply_now_card.click(timeout=3000)
                except Exception:
                    apply_now_card.dispatch_event("click")
                page.wait_for_timeout(2500)

            # If clicking Apply triggered a Google Sign In prompt
            google_prompt = page.locator("button:has-text('Continue with Google'), button:has-text('Sign in with Google')").first
            if google_prompt.count() > 0 and google_prompt.is_visible():
                self.handle_google_oauth(page, trigger_locator=google_prompt, target_domain="cutshort.io")
                page.wait_for_timeout(2500)

            # Check if an application dialog/modal or message input opened
            textareas = page.locator("textarea[placeholder*='message'], textarea, div[contenteditable='true']").all()
            if textareas:
                print(f"✍️ Injecting tailored pitch note into Cutshort recruiter message...")
                for ta in textareas:
                    try:
                        if ta.is_visible() and ta.is_enabled():
                            if ta.get_attribute("contenteditable") == "true":
                                ta.fill(pitch_note)
                            else:
                                ta.fill(pitch_note, timeout=3000)
                            page.wait_for_timeout(500)
                    except Exception as e:
                        logger.warning(f"[Cutshort Live] Textarea fill warning: {e}")

            # Upload resume if file input is present
            if resume_path and resume_path.exists():
                file_inputs = page.locator("input[type='file']").all()
                for fi in file_inputs:
                    try:
                        print(f"📎 Attaching resume PDF: {resume_path.name}")
                        fi.set_input_files(str(resume_path.resolve()))
                        page.wait_for_timeout(1000)
                    except Exception as e:
                        logger.warning(f"[Cutshort Live] Resume upload skipped: {e}")

            # Locate and click submit button
            submit_btn = None
            for sub_sel in [
                "button:has-text('Send')",
                "button:has-text('Send application')",
                "button:has-text('Submit')",
                "button:has-text('Submit application')",
                "button:has-text('Confirm')",
                "button[type='submit']",
            ]:
                loc = page.locator(sub_sel).first
                if loc.count() > 0 and loc.is_visible():
                    submit_btn = loc
                    break

            if submit_btn:
                print("🚀 Submitting Cutshort application...")
                submit_btn.click()
                page.wait_for_timeout(4000)
                print(f"🎉 Successfully submitted live application to Cutshort: {url}!")
                page.close()
                return True, "APPLIED"
            else:
                # Some Cutshort applications complete immediately upon clicking Interested with pre-stored profile
                page.wait_for_timeout(2000)
                if page.locator("button:has-text('Applied'), div:has-text('Application sent')").count() > 0:
                    print(f"🎉 Application confirmed on Cutshort: {url}!")
                    page.close()
                    return True, "APPLIED"

                print("⚠️ Submit button not found in Cutshort modal.")
                page.close()
                return False, "ACTION_REQUIRED: Submit button not accessible"

        except Exception as e:
            logger.error(f"[Cutshort Live] Error during application: {e}")
            print(f"❌ Error during Cutshort application: {e}")
            page.close()
            return False, f"ERROR: {e}"

    def ensure_instahyre_logged_in(self, page: Page) -> bool:
        """
        Verifies Instahyre login session, performing Google OAuth login if needed.
        """
        try:
            page_content = page.content().lower()
            if any(k in page_content for k in ["candidate/opportunities", "candidate/profile", "logout", "log out"]) or page.locator("a[href*='/candidate/opportunities']").count() > 0:
                logger.info("[Instahyre] Already authenticated.")
                return True

            logger.info("[Instahyre] Checking login status...")
            login_url = "https://www.instahyre.com/login/"
            if "instahyre.com/login" not in page.url:
                page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)

            # Check Cloudflare
            if self.check_cloudflare_challenge(page, "instahyre", login_url):
                return False

            # Find Google OAuth button
            google_btn = None
            for sel in [
                "a:has-text('Sign in with Google')",
                "button:has-text('Sign in with Google')",
                "a:has-text('Continue with Google')",
                "button:has-text('Continue with Google')",
                "a[href*='google']",
                "button[data-provider='google']",
                "[aria-label*='Google']",
            ]:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    google_btn = loc
                    break

            if google_btn:
                print("🔑 Initiating Google OAuth sign-in on Instahyre...")
                self.handle_google_oauth(page, trigger_locator=google_btn, target_domain="instahyre.com")
                page.wait_for_timeout(3000)
                return True
            else:
                logger.info("[Instahyre] Already on authenticated page or Google button omitted.")
                return True
        except Exception as e:
            logger.error(f"[Instahyre] Login check note: {e}")
            return False

    def apply_instahyre(
        self,
        url: str,
        pitch_note: str,
        resume_path: Optional[Path] = None,
        min_salary_lpa: float = 10.0,
    ) -> Tuple[bool, str]:
        """
        Executes live application on Instahyre (instahyre.com):
        1. Navigates to job URL
        2. Detects Cloudflare / anti-bot
        3. Scrapes and validates live compensation from DOM (aborts if < min_salary_lpa)
        4. Verifies Instahyre session; performs Google OAuth if unauthenticated
        5. Checks if already applied
        6. Clicks Apply button
        7. Injects tailored pitch note into optional note field
        8. Uploads resume PDF if requested
        9. Submits application
        """
        context = self.start()
        page = context.new_page()
        try:
            logger.info(f"[Instahyre Live] Navigating to {url}...")
            print(f"🌐 Navigating to Instahyre: {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Check Cloudflare
            if self.check_cloudflare_challenge(page, "instahyre", url):
                page.close()
                return False, "CLOUDFLARE"

            # Check if job is expired or closed
            page_content = page.content().lower()
            page_title = page.title().lower()
            if any(k in page_content or k in page_title for k in [
                "this opportunity is closed",
                "opportunity is closed",
                "job is closed",
                "this job is no longer active",
                "page not found",
                "404 not found",
            ]):
                print(f"🚫 Listing is expired or closed: {url}")
                page.close()
                return False, "EXPIRED"

            # Validate Live Compensation from DOM
            try:
                page_text = page.locator("body").inner_text()
                parsed = parse_live_salary(page_text)
                if parsed:
                    max_lpa, raw_sal = parsed
                    logger.info(f"[Instahyre Live] Detected live compensation: '{raw_sal}' (~{max_lpa:.1f} LPA)")
                    if max_lpa < min_salary_lpa:
                        print(f"🚫 Live compensation '{raw_sal}' is below target threshold ({min_salary_lpa} LPA). Aborting.")
                        page.close()
                        return False, f"FILTERED_OUT: Live salary '{raw_sal}' is below threshold of {min_salary_lpa} LPA"
            except Exception as e:
                logger.warning(f"[Instahyre Live] Salary check warning: {e}")

            # Check / Ensure Instahyre authentication via Google OAuth
            login_needed = False
            for login_sel in ["a:has-text('Log in')", "button:has-text('Log in')", "a:has-text('Sign In')", "button:has-text('Sign In')"]:
                if page.locator(login_sel).first.is_visible():
                    login_needed = True
                    break

            if login_needed:
                self.ensure_instahyre_logged_in(page)
                if "instahyre.com/job" not in page.url:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)

            # Check if already applied
            already_applied = page.locator(
                "button:has-text('Applied'), button:has-text('Already Applied'), div:has-text('Applied'), span:has-text('Applied')"
            )
            if already_applied.count() > 0 and already_applied.first.is_visible():
                logger.info(f"[Instahyre Live] Already applied to {url}.")
                print(f"ℹ️ Already applied to Instahyre role: {url}")
                page.close()
                return True, "ALREADY_APPLIED"

            # If on opportunities feed, click 'View job' to open opportunity modal
            view_job_btn = page.locator("button:has-text('View job')").first
            if view_job_btn.count() > 0 and view_job_btn.is_visible():
                print(f"🖱️ Clicking 'View job »' on Instahyre opportunities feed...")
                try:
                    view_job_btn.click(timeout=3000)
                except Exception:
                    view_job_btn.dispatch_event("click")
                page.wait_for_timeout(2500)

            # Find Apply button
            apply_btn = None
            for selector in [
                "button#apply-btn",
                "button:has-text('Apply')",
                "button:has-text('Easy Apply')",
                "button:has-text('Apply on Instahyre')",
                "button:has-text('Interested')",
                "a:has-text('Apply')",
            ]:
                loc = page.locator(selector).first
                if loc.count() > 0 and loc.is_visible() and "applied" not in loc.inner_text().strip().lower():
                    apply_btn = loc
                    break

            if not apply_btn:
                # Check for external apply link
                ext_link = page.locator("a:has-text('Apply externally'), a:has-text('Company Website')").first
                if ext_link.count() > 0 and ext_link.is_visible():
                    href = ext_link.get_attribute("href")
                    print(f"⚠️ External apply link: {href}")
                    page.close()
                    return False, f"EXTERNAL_LINK: {href}"
                else:
                    logger.warning(f"[Instahyre Live] Could not find Apply button on {url}.")
                    page.close()
                    return False, "NO_APPLY_BUTTON"

            print(f"🖱️ Clicking Apply button on Instahyre ({url})...")
            apply_btn.click()
            page.wait_for_timeout(2500)

            # If clicking Apply triggered a Google Sign In prompt
            google_prompt = page.locator("button:has-text('Sign in with Google'), a:has-text('Sign in with Google')").first
            if google_prompt.count() > 0 and google_prompt.is_visible():
                self.handle_google_oauth(page, trigger_locator=google_prompt, target_domain="instahyre.com")
                page.wait_for_timeout(2500)

            # Check if note or cover letter modal popped up
            textareas = page.locator("textarea#note, textarea[name='note'], textarea").all()
            if textareas:
                print(f"✍️ Injecting tailored pitch note into Instahyre recruiter note...")
                for ta in textareas:
                    try:
                        if ta.is_visible() and ta.is_enabled():
                            ta.fill(pitch_note, timeout=3000)
                            page.wait_for_timeout(500)
                    except Exception as e:
                        logger.warning(f"[Instahyre Live] Textarea fill warning: {e}")

            # Upload resume if file input is present
            if resume_path and resume_path.exists():
                file_inputs = page.locator("input[type='file']").all()
                for fi in file_inputs:
                    try:
                        print(f"📎 Attaching resume PDF: {resume_path.name}")
                        fi.set_input_files(str(resume_path.resolve()))
                        page.wait_for_timeout(1000)
                    except Exception as e:
                        logger.warning(f"[Instahyre Live] Resume upload skipped: {e}")

            # Locate and click confirm/submit button if in modal
            submit_btn = None
            for sub_sel in [
                "button:has-text('Send')",
                "button:has-text('Apply')",
                "button:has-text('Submit')",
                "button:has-text('Confirm')",
                "button[type='submit']",
            ]:
                loc = page.locator(sub_sel).first
                if loc.count() > 0 and loc.is_visible():
                    submit_btn = loc
                    break

            if submit_btn:
                print("🚀 Submitting Instahyre application...")
                submit_btn.click()
                page.wait_for_timeout(4000)
                print(f"🎉 Successfully submitted live application to Instahyre: {url}!")
                page.close()
                return True, "APPLIED"
            else:
                page.wait_for_timeout(2000)
                if page.locator("button:has-text('Applied'), span:has-text('Applied')").count() > 0:
                    print(f"🎉 Application confirmed on Instahyre: {url}!")
                    page.close()
                    return True, "APPLIED"

                print("⚠️ Submit confirmation not found in modal.")
                page.close()
                return False, "ACTION_REQUIRED: Submit button not accessible"

        except Exception as e:
            logger.error(f"[Instahyre Live] Error during application: {e}")
            print(f"❌ Error during Instahyre application: {e}")
            page.close()
            return False, f"ERROR: {e}"
