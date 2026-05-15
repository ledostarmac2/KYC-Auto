import json
import os
import random
import sys
import time
import traceback
import urllib.error
import urllib.request
import ctypes
from datetime import datetime

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.webdriver import WebDriver as EdgeWebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# Configuration
APP_DATA_FOLDER = "KYCReminder"
KYC_URL = "https://app.hilton.kych.co/inspections"
KYC_BASE_URL = "https://app.hilton.kych.co/"
KYC_LOGIN_URL = "https://app.hilton.kych.co/login"
TEAM_MEMBERS = ["Hyun Song", "Eleanor Green", "Dakota Weglarz", "Brian Tarabocchia"]
YES_ITEMS = [1, 2, 4, 5, 6, 7, 8, 9, 20]  # Items to mark as "Yes"
NO_FLIP_CHANCE = 0.30
EXPECTED_CHECKLIST_ITEMS = 20
DESKTOP_WINDOW_WIDTH = 1440
DESKTOP_WINDOW_HEIGHT = 1000
BACKGROUND_WINDOW_X = -32000
BACKGROUND_WINDOW_Y = 0
DEBUG_PORTS = list(range(9222, 9230))
PLUS_BUTTON_LOCATOR = (
    By.CSS_SELECTOR,
    "button[aria-label*='add'], button.fab, [class*='add-btn'], .fab-button",
)
ADD_BUTTON_SCRIPT = r"""
const nodes = Array.from(document.querySelectorAll([
  'button',
  '[role="button"]',
  'a[href]',
  'input[type="button"]',
  'input[type="submit"]',
  '.fab',
  '.mat-fab',
  '.mat-mdc-fab',
  '.MuiFab-root',
  '[class*="fab"]',
  '[class*="add"]',
  '[aria-label]',
  '[title]'
].join(',')));

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 &&
    rect.height > 0 &&
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.pointerEvents !== 'none';
}

function textFor(el) {
  return [
    el.innerText,
    el.textContent,
    el.getAttribute('aria-label'),
    el.getAttribute('title'),
    el.getAttribute('id'),
    el.getAttribute('class'),
    el.getAttribute('name'),
    el.getAttribute('value'),
    el.getAttribute('data-testid'),
    el.getAttribute('data-cy'),
    el.getAttribute('data-test'),
    el.innerHTML
  ].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
}

const scored = nodes.filter(visible).map((el) => {
  const raw = textFor(el);
  const text = raw.toLowerCase();
  let score = 0;
  if (['+', 'add', 'new'].includes((el.innerText || '').trim().toLowerCase())) score += 100;
  if (text.includes('mdi-plus') || text.includes('fa-plus') || text.includes('plus')) score += 80;
  if (text.includes('add')) score += 70;
  if (text.includes('new')) score += 45;
  if (text.includes('create')) score += 45;
  if (text.includes('inspection')) score += 35;
  if (text.includes('fab')) score += 25;
  if (el.tagName.toLowerCase() === 'button') score += 10;
  return {el, score, raw: raw.slice(0, 180)};
}).filter((item) => item.score > 0)
  .sort((a, b) => b.score - a.score);

return scored.length ? scored[0].el : null;
"""
BUTTON_SUMMARY_SCRIPT = r"""
return Array.from(document.querySelectorAll('button,[role="button"],a[href],input[type="button"],input[type="submit"],[aria-label],[title]'))
  .filter((el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  })
  .slice(0, 40)
  .map((el) => [
    el.tagName.toLowerCase(),
    (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80),
    el.getAttribute('aria-label') || '',
    el.getAttribute('title') || '',
    el.getAttribute('class') || ''
  ].join(' | '));
"""
FIELD_SUMMARY_SCRIPT = r"""
return Array.from(document.querySelectorAll('input,select,textarea,button,[role="combobox"],[role="button"],[aria-label],[placeholder]'))
  .filter((el) => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  })
  .slice(0, 80)
  .map((el) => [
    el.tagName.toLowerCase(),
    el.getAttribute('type') || '',
    (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80),
    el.getAttribute('aria-label') || '',
    el.getAttribute('placeholder') || '',
    el.getAttribute('name') || '',
    el.getAttribute('id') || '',
    el.getAttribute('class') || ''
  ].join(' | '));
"""
CONTROL_NEAR_TEXT_SCRIPT = r"""
const needle = arguments[0].toLowerCase();
const all = Array.from(document.querySelectorAll('label,div,span,p,h1,h2,h3,h4,h5,h6'));

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
}

function findControl(root) {
  if (!root) return null;
  const selectors = 'select,input,textarea,button,[role="combobox"],[role="button"],.mat-select,.mat-mdc-select,[class*="select"],[class*="dropdown"]';
  const direct = root.matches && root.matches(selectors) ? root : root.querySelector(selectors);
  if (direct && visible(direct)) return direct;
  return null;
}

for (const label of all) {
  const text = (label.innerText || label.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  if (!text.includes(needle) || !visible(label)) continue;
  let node = label;
  for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
    const control = findControl(node);
    if (control && control !== label) return control;
    const next = node.nextElementSibling;
    const siblingControl = findControl(next);
    if (siblingControl) return siblingControl;
  }
}

return null;
"""
ACTIVE_TEXT_OPTION_SCRIPT = r"""
const wanted = arguments[0].toLowerCase();
const exactOnly = Boolean(arguments[1]);
const optionSelectors = [
  'button',
  '[role="button"]',
  '[role="option"]',
  '[role="menuitem"]',
  '[role="listitem"]',
  'a[href]',
  'div',
  'span',
  'li',
  '.v-list__tile',
  '.v-btn'
].join(',');

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
}

function norm(el) {
  return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
}

const roots = Array.from(document.querySelectorAll([
  '.v-menu__content',
  '.v-autocomplete__content',
  '.menuable__content__active',
  '[role="listbox"]',
  '.v-dialog--active',
  '.v-dialog__content--active',
  '[role="dialog"]'
].join(','))).filter(visible);
const searchRoots = roots.length ? roots : [document.body];
const nodes = [];
for (const root of searchRoots) {
  for (const el of Array.from(root.querySelectorAll(optionSelectors))) {
    nodes.push({el, root});
  }
}

const candidates = nodes.filter(({el}) => visible(el)).map(({el, root}) => {
  const text = norm(el);
  const lower = text.toLowerCase();
  const rootClass = (root.className || '').toString().toLowerCase();
  const className = (el.className || '').toString().toLowerCase();
  let score = 0;
  if (lower === wanted) score += 1000;
  if (!exactOnly && lower.includes(wanted)) score += 100;
  if (rootClass.includes('menu') || rootClass.includes('autocomplete') || root.getAttribute('role') === 'listbox') score += 300;
  if (rootClass.includes('dialog')) score += 120;
  if (['button', 'a'].includes(el.tagName.toLowerCase())) score += 20;
  if (el.getAttribute('role')) score += 15;
  if (className.includes('v-list__tile') || className.includes('v-list-item')) score += 25;
  if (className.includes('v-btn')) score += 10;
  return {el, score, text};
}).filter((item) => item.score > 0).sort((a, b) => b.score - a.score);

return candidates.length ? candidates[0].el : null;
"""
MAIN_ACTION_BUTTON_SCRIPT = r"""
const wanted = arguments[0].toLowerCase();
const root = document.querySelector('#main-action-button') || document.body;
const nodes = Array.from(root.querySelectorAll('button,[role="button"],a[href]'));

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 &&
    rect.height > 0 &&
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.pointerEvents !== 'none';
}

function norm(el) {
  return [
    el.innerText,
    el.textContent,
    el.getAttribute('aria-label'),
    el.getAttribute('title')
  ].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
}

const candidates = nodes.filter(visible).map((el) => {
  const text = norm(el);
  const lower = text.toLowerCase();
  const className = (el.className || '').toString().toLowerCase();
  let score = 0;
  if (lower === wanted) score += 1000;
  if (className.includes('action-button-list')) score += 250;
  if (className.includes('v-btn')) score += 20;
  return {el, score, text};
}).filter((item) => item.score > 0).sort((a, b) => b.score - a.score);

return candidates.length ? candidates[0].el : null;
"""
AUTOCOMPLETE_OPTION_SCRIPT = r"""
const wanted = arguments[0].toLowerCase();
const preferredClass = (arguments[1] || '').toLowerCase();

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 &&
    rect.height > 0 &&
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.pointerEvents !== 'none';
}

function norm(el) {
  return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
}

const roots = Array.from(document.querySelectorAll([
  '.v-menu__content',
  '.v-autocomplete__content',
  '.menuable__content__active',
  '[role="listbox"]'
].join(','))).filter(visible);

const candidates = [];
for (const root of roots) {
  const rootClass = (root.className || '').toString().toLowerCase();
  for (const node of Array.from(root.querySelectorAll([
    '[role="option"]',
    '[role="listitem"]',
    '.v-list__tile',
    '.v-list-item',
    'button',
    'div',
    'span',
    'li'
  ].join(',')))) {
    if (!visible(node)) continue;
    const text = norm(node);
    const lower = text.toLowerCase();
    let score = 0;
    if (lower === wanted) score += 1000;
    if (lower.includes(wanted)) score += 100;
    if (preferredClass && rootClass.includes(preferredClass)) score += 500;
    if (rootClass.includes('autocomplete')) score += 150;
    if ((node.className || '').toString().toLowerCase().includes('v-list')) score += 50;
    if (score <= 0) continue;
    const clickable = node.closest('button,[role="option"],[role="listitem"],.v-list__tile,.v-list-item,li,div') || node;
    candidates.push({el: clickable, score, text});
  }
}

candidates.sort((a, b) => b.score - a.score);
return candidates.length ? candidates[0].el : null;
"""
TEAM_MEMBER_FIELD_TEXT_SCRIPT = r"""
const input = document.querySelector('#employeeSearchId');
if (!input) return '';
const root = input.closest('.team-member-search') || input.closest('.v-input') || input.parentElement;
return [
  input.value || '',
  root ? (root.innerText || root.textContent || '') : ''
].join(' ').replace(/\s+/g, ' ').trim();
"""
COMPLETE_BUTTON_SCRIPT = r"""
const roots = Array.from(document.querySelectorAll('.v-dialog--active, .v-dialog__content--active, [role="dialog"]'));
const root = roots.find((el) => el.offsetParent !== null) || roots[0] || document.body;
const buttons = Array.from(root.querySelectorAll('button,[role="button"],.v-btn'));

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 &&
    rect.height > 0 &&
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.pointerEvents !== 'none' &&
    !el.disabled &&
    el.getAttribute('aria-disabled') !== 'true';
}

function norm(el) {
  return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
}

const candidates = buttons.filter(visible).map((el) => {
  const text = norm(el);
  const lower = text.toLowerCase();
  let score = 0;
  if (lower === 'complete') score += 1000;
  if (lower.includes('complete') && !lower.includes('incomplete')) score += 200;
  if ((el.className || '').toString().includes('primary')) score += 50;
  return {el, score, text};
}).filter((item) => item.score > 0).sort((a, b) => b.score - a.score);

return candidates.length ? candidates[0].el : null;
"""
OPEN_INSPECTION_SELECTOR_SCRIPT = r"""
const instance = window.app || (typeof app !== 'undefined' ? app : null);
if (instance && instance.$eventBus && typeof instance.$eventBus.$emit === 'function') {
  instance.$eventBus.$emit('show-inspection-checklist-dialog');
  return true;
}
return false;
"""
ACTIVE_DIALOG_TEXT_SCRIPT = r"""
const roots = Array.from(document.querySelectorAll('.v-dialog--active, .v-dialog__content--active, [role="dialog"]'));
const root = roots.find((el) => el.offsetParent !== null) || roots[0] || document.body;
return (root.innerText || root.textContent || '').replace(/\s+/g, ' ').trim();
"""
DEPARTMENT_CONTROL_SCRIPT = r"""
const roots = Array.from(document.querySelectorAll('.v-dialog--active, .v-dialog__content--active, [role="dialog"]'));
const root = roots.find((el) => (el.innerText || '').toLowerCase().includes('select inspection')) || document.body;
const labels = Array.from(root.querySelectorAll('label,div,span'));

function visible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
}

for (const label of labels) {
  const text = (label.innerText || label.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  if (!text.includes('department') || !visible(label)) continue;
  let node = label;
  for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
    const control = node.querySelector('input[role="combobox"],input,textarea,[role="combobox"],.v-select__slot,.v-input__slot');
    if (control && visible(control)) return control;
  }
}

return root.querySelector('input[aria-label*="Department"],input[aria-label*="department"],input[role="combobox"]');
"""
ACCOUNT_INPUT_LOCATOR = (
    By.XPATH,
    "//input[not(@type='password') and not(@type='hidden') and not(@disabled)]",
)
PASSWORD_INPUT_LOCATOR = (By.XPATH, "//input[@type='password']")
LOGIN_BUTTON_LOCATOR = (
    By.XPATH,
    "//button[@type='submit' or contains(translate(normalize-space(.), "
    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log') or "
    "contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
    "'abcdefghijklmnopqrstuvwxyz'), 'sign')]",
)


def app_dir():
    """Return the per-user runtime data directory."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = os.path.join(os.path.expanduser("~"), "AppData", "Local")

    path = os.path.join(local_app_data, APP_DATA_FOLDER)
    os.makedirs(path, exist_ok=True)
    return path


def log_dir():
    path = os.path.join(app_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def diagnostics_dir():
    path = os.path.join(log_dir(), "diagnostics")
    os.makedirs(path, exist_ok=True)
    return path


def team_member_history_path():
    return os.path.join(app_dir(), "team_member_history.json")


def no_flip_history_path():
    return os.path.join(app_dir(), "no_flip_history.json")


def resource_path(relative_path):
    """Return a path that works both from source and from a PyInstaller exe."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def installed_file_path(file_name):
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), file_name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)


def edgedriver_path():
    installed_driver = installed_file_path("msedgedriver.exe")
    if os.path.exists(installed_driver):
        return installed_driver
    return resource_path("msedgedriver.exe")


def log(message):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    print(line)
    try:
        with open(os.path.join(log_dir(), "kyc_automation.log"), "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except OSError:
        pass


def fail(message, exc=None):
    log(f"ERROR: {message}")
    if exc is not None:
        log(traceback.format_exc())
    return False, message


def find_edge_executable():
    """Find the Microsoft Edge executable path."""
    candidate_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]

    for edge_path in candidate_paths:
        if os.path.exists(edge_path):
            return edge_path

    return None


def automation_profile_dir():
    profile_dir = os.path.join(app_dir(), "EdgeAutomationProfile")
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir


def foreground_window_handle():
    if not sys.platform.startswith("win"):
        return None
    try:
        return ctypes.windll.user32.GetForegroundWindow()
    except Exception:
        return None


def restore_foreground_window(window_handle):
    if not window_handle or not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.user32.SetForegroundWindow(window_handle)
    except Exception as e:
        log(f"Could not restore previous foreground window: {e}")


def load_team_member_history():
    path = team_member_history_path()
    try:
        with open(path, "r", encoding="utf-8") as history_file:
            history = json.load(history_file)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(history, list):
        return []
    return [entry for entry in history if isinstance(entry, dict) and entry.get("name") in TEAM_MEMBERS]


def save_team_member_history(history):
    with open(team_member_history_path(), "w", encoding="utf-8") as history_file:
        json.dump(history, history_file, indent=2)


def load_last_no_flip_item():
    try:
        with open(no_flip_history_path(), "r", encoding="utf-8") as history_file:
            history = json.load(history_file)
    except (OSError, json.JSONDecodeError):
        return None

    item = history.get("item") if isinstance(history, dict) else None
    return item if isinstance(item, int) else None


def save_last_no_flip_item(item):
    with open(no_flip_history_path(), "w", encoding="utf-8") as history_file:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "item": item,
            },
            history_file,
            indent=2,
        )


def choose_team_member(available_team_members=None):
    available_team_members = [
        name for name in (available_team_members or TEAM_MEMBERS) if name in TEAM_MEMBERS
    ]
    if not available_team_members:
        available_team_members = list(TEAM_MEMBERS)

    history = load_team_member_history()
    recent_names = [
        entry.get("name") for entry in history[-2:] if entry.get("name") in available_team_members
    ]
    choices = list(available_team_members)

    if len(recent_names) == 2 and recent_names[0] == recent_names[1]:
        choices = [name for name in choices if name != recent_names[0]]
        if not choices:
            choices = list(available_team_members)

    chosen = random.choice(choices)
    history.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "name": chosen,
        }
    )
    try:
        save_team_member_history(history)
    except OSError as e:
        log(f"Could not write team member history: {e}")

    log(f"Chose team member from rotation: {chosen}")
    return chosen


def create_edge_service(msedgedriver_path):
    if os.path.exists(msedgedriver_path):
        log(f"Using msedgedriver at {msedgedriver_path}")
        return Service(msedgedriver_path)

    log("Using msedgedriver from PATH")
    return Service()


def create_edge_options(edge_path, user_data_dir, profile_directory=None):
    options = Options()
    options.binary_location = edge_path
    options.add_argument(f"--user-data-dir={user_data_dir}")
    if profile_directory:
        options.add_argument(f"--profile-directory={profile_directory}")
    options.add_argument("--new-window")
    options.add_argument(f"--window-size={DESKTOP_WINDOW_WIDTH},{DESKTOP_WINDOW_HEIGHT}")
    options.add_argument(f"--window-position={BACKGROUND_WINDOW_X},{BACKGROUND_WINDOW_Y}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-background-mode")
    return options


def create_attached_edge_options(debugger_address):
    options = Options()
    options.debugger_address = debugger_address
    return options


def devtools_targets(port):
    url = f"http://127.0.0.1:{port}/json/list"
    try:
        with urllib.request.urlopen(url, timeout=0.35) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def find_existing_kyc_target():
    for port in DEBUG_PORTS:
        targets = devtools_targets(port)
        if not targets:
            continue

        for target in targets:
            target_url = target.get("url", "")
            target_type = target.get("type", "")
            if target_type == "page" and target_url.startswith(KYC_BASE_URL):
                log(f"Found existing KYC tab on DevTools port {port}: {target_url}")
                return port, target

    return None, None


def choose_debug_port():
    for port in DEBUG_PORTS:
        if devtools_targets(port) is None:
            return port
    return None


def switch_to_existing_kyc_tab(driver, target_id=None):
    handles = driver.window_handles
    if target_id and target_id in handles:
        driver.switch_to.window(target_id)
        return True

    for handle in handles:
        driver.switch_to.window(handle)
        if driver.current_url.startswith(KYC_BASE_URL):
            return True

    return driver.current_url.startswith(KYC_BASE_URL)


def attach_to_existing_kyc_tab(msedgedriver_path):
    port, target = find_existing_kyc_target()
    if not target:
        return None, "No debuggable KYC tab found"

    debugger_address = f"127.0.0.1:{port}"
    target_id = target.get("id")
    try:
        log(f"Attaching to existing Edge tab through {debugger_address}")
        service = create_edge_service(msedgedriver_path)
        options = create_attached_edge_options(debugger_address)
        driver = EdgeWebDriver(service=service, options=options)
        if not switch_to_existing_kyc_tab(driver, target_id):
            driver.quit()
            return None, "Attached to Edge, but could not switch to the KYC tab"
        log(f"Attached to existing KYC tab: {driver.current_url}")
        return driver, "existing KYC tab"
    except Exception as e:
        return None, f"Could not attach to existing KYC tab: {e}"


def route_to_inspections(driver):
    try:
        current_url = driver.current_url
        log(f"Current URL: {current_url}")

        if current_url.startswith(KYC_BASE_URL):
            if current_url.rstrip("/") != KYC_URL.rstrip("/"):
                log("KYC tab found, routing to inspections")
                driver.get(KYC_URL)
            else:
                log("Already on inspections page")
        else:
            log(f"Navigating to {KYC_URL}")
            driver.get(KYC_URL)
    except Exception:
        log(f"Navigating to {KYC_URL}")
        driver.get(KYC_URL)


def wait_for_page_ready(driver, timeout=30):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )


def force_desktop_window(driver):
    try:
        driver.set_window_rect(
            width=DESKTOP_WINDOW_WIDTH,
            height=DESKTOP_WINDOW_HEIGHT,
            x=BACKGROUND_WINDOW_X,
            y=BACKGROUND_WINDOW_Y,
        )
        log("Moved automation Edge window off-screen with desktop viewport")
    except Exception as e:
        log(f"Could not set desktop browser size: {e}")


def log_browser_layout(driver):
    try:
        layout = driver.execute_script(
            """
            const mainButton = document.querySelector('#main-action-button');
            const rect = mainButton ? mainButton.getBoundingClientRect() : null;
            return {
              width: window.innerWidth,
              height: window.innerHeight,
              appMobile: Boolean(window.app && window.app.$isMobile && window.app.$isMobile()),
              actionButtonTop: rect ? Math.round(rect.top) : null,
              actionButtonRight: rect ? Math.round(window.innerWidth - rect.right) : null
            };
            """
        )
        log(
            "Browser layout: "
            f"{layout.get('width')}x{layout.get('height')}, "
            f"KYC mobile={layout.get('appMobile')}, "
            f"action button top={layout.get('actionButtonTop')}, "
            f"right={layout.get('actionButtonRight')}"
        )
    except Exception as e:
        log(f"Could not inspect browser layout: {e}")


def first_visible(driver, locator):
    for element in driver.find_elements(*locator):
        if element.is_displayed() and element.is_enabled():
            return element
    return None


def login_if_needed(driver, account_name=None, password=None):
    account_name = account_name or os.environ.get("KYC_ACCOUNT", "")
    password = password or os.environ.get("KYC_PASSWORD", "")

    try:
        password_input = first_visible(driver, PASSWORD_INPUT_LOCATOR)
        if password_input is None and "/login" not in driver.current_url:
            return True, None

        if password_input is None:
            password_input = WebDriverWait(driver, 8).until(
                lambda d: first_visible(d, PASSWORD_INPUT_LOCATOR)
            )
    except TimeoutException:
        if "/login" in driver.current_url:
            return False, "KYC login page opened, but the password field was not found."
        return True, None

    if not account_name or not password:
        return False, "KYC login page opened. Enter the account and password in the app, then click Run Now again."

    account_input = first_visible(driver, ACCOUNT_INPUT_LOCATOR)
    if account_input is None:
        return False, "KYC login page opened, but the account field was not found."

    log("KYC login page detected; submitting login form")
    account_input.clear()
    account_input.send_keys(account_name)
    password_input.clear()
    password_input.send_keys(password)

    login_button = first_visible(driver, LOGIN_BUTTON_LOCATOR)
    if login_button is not None:
        login_button.click()
    else:
        password_input.submit()

    try:
        WebDriverWait(driver, 45).until(
            lambda d: "/login" not in d.current_url or first_visible(d, PLUS_BUTTON_LOCATOR) is not None
        )
    except TimeoutException:
        return False, "KYC login did not complete within 45 seconds."

    if "/login" in driver.current_url:
        return False, "KYC login did not complete. Check the account/password and try again."

    log("KYC login completed")
    return True, None


def write_page_diagnostics(driver, reason):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(diagnostics_dir(), f"kyc_page_debug_{timestamp}.html")
    screenshot_path = os.path.join(diagnostics_dir(), f"kyc_page_debug_{timestamp}.png")
    try:
        with open(html_path, "w", encoding="utf-8") as html_file:
            html_file.write(driver.page_source)
        log(f"Wrote page HTML debug for {reason}: {html_path}")
    except OSError as e:
        log(f"Could not write page HTML debug: {e}")

    try:
        driver.save_screenshot(screenshot_path)
        log(f"Wrote page screenshot debug for {reason}: {screenshot_path}")
    except Exception as e:
        log(f"Could not write page screenshot debug: {e}")

    try:
        buttons = driver.execute_script(BUTTON_SUMMARY_SCRIPT)
        log("Visible button candidates: " + " || ".join(buttons[:20]))
    except Exception as e:
        log(f"Could not list visible button candidates: {e}")

    try:
        fields = driver.execute_script(FIELD_SUMMARY_SCRIPT)
        log("Visible field candidates: " + " || ".join(fields[:30]))
    except Exception as e:
        log(f"Could not list visible field candidates: {e}")


def xpath_literal(value):
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    return "concat(" + ', "\"", '.join(f"'{part}'" for part in value.split('"')) + ")"


def click_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
        time.sleep(0.15)
    except Exception:
        pass

    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def visible_elements(driver, locator):
    elements = []
    for element in driver.find_elements(*locator):
        try:
            if element.is_displayed() and element.is_enabled():
                elements.append(element)
        except Exception:
            pass
    return elements


def find_add_button(driver):
    for locator in (
        PLUS_BUTTON_LOCATOR,
        (By.XPATH, "//button[normalize-space(.)='+'] | //*[@role='button' and normalize-space(.)='+']"),
        (
            By.XPATH,
            "//*[self::button or @role='button' or self::a]"
            "[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add') "
            "or contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add') "
            "or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'fab') "
            "or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plus') "
            "or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'new') "
            "or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create')]",
        ),
    ):
        for element in driver.find_elements(*locator):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except Exception:
                pass

    return driver.execute_script(ADD_BUTTON_SCRIPT)


def click_add_button(driver, timeout):
    log(f"Looking for add/new/plus button for up to {timeout} seconds")
    try:
        add_button = WebDriverWait(driver, timeout).until(lambda d: find_add_button(d))
    except TimeoutException as e:
        write_page_diagnostics(driver, "missing add button")
        raise e

    click_element(driver, add_button)
    log("Clicked add/new/plus button")


def click_text_option(driver, text, timeout=10):
    literal = xpath_literal(text)
    option_xpath = (
        f"//*[self::button or self::div or self::span or self::li or self::mat-option "
        f"or self::md-option or self::option or @role='option' or @role='menuitem' or @role='button']"
        f"[contains(normalize-space(.), {literal})]"
    )

    element = WebDriverWait(driver, timeout).until(
        lambda d: next(iter(visible_elements(d, (By.XPATH, option_xpath))), None)
    )
    click_element(driver, element)
    return element


def click_main_action_button(driver, text, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(MAIN_ACTION_BUTTON_SCRIPT, text)
    )
    click_element(driver, element)
    log(f"Clicked main action button: {text}")
    return element


def click_active_text_option(driver, text, timeout=10, exact_only=False):
    element = WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(ACTIVE_TEXT_OPTION_SCRIPT, text, exact_only)
    )
    click_element(driver, element)
    return element


def click_autocomplete_option(driver, text, timeout=10, preferred_class=""):
    element = WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(AUTOCOMPLETE_OPTION_SCRIPT, text, preferred_class)
    )
    click_element(driver, element)
    return element


def active_dialog_text(driver):
    try:
        return driver.execute_script(ACTIVE_DIALOG_TEXT_SCRIPT)
    except Exception:
        return driver.find_element(By.TAG_NAME, "body").text


def reservation_prearrival_form_loaded(driver):
    text = active_dialog_text(driver)
    has_form_title = "New Inspection" in text or "Editing Inspection" in text
    has_template = "Reservation & Pre-Arrival" in text
    has_expected_checklist = "1/20" in text and "20/20" in text
    return has_form_title and has_template and has_expected_checklist


def team_member_field_text(driver):
    try:
        return driver.execute_script(TEAM_MEMBER_FIELD_TEXT_SCRIPT)
    except Exception:
        return ""


def close_active_dialog(driver):
    log("Closing the current inspection dialog")
    for locator in (
        (By.XPATH, "//*[contains(@class, 'v-dialog--active')]//*[normalize-space(.)='close']"),
        (By.XPATH, "//*[contains(@class, 'v-dialog--active')]//*[normalize-space(.)='CLOSE']"),
        (By.XPATH, "//*[contains(@class, 'v-dialog--active')]//*[contains(@class, 'primary--text') and normalize-space(.)='close']"),
    ):
        for element in visible_elements(driver, locator):
            click_element(driver, element)
            time.sleep(0.75)
            return


def ensure_reservations_department(driver):
    text = active_dialog_text(driver)
    if "Reservations" in text and "Reservation & Pre-Arrival" in text:
        log("Reservations department already selected")
        return

    control = WebDriverWait(driver, 10).until(
        lambda d: d.execute_script(DEPARTMENT_CONTROL_SCRIPT)
    )
    click_element(driver, control)
    time.sleep(0.25)

    try:
        control.send_keys(Keys.CONTROL, "a")
        control.send_keys(Keys.BACKSPACE)
    except Exception:
        pass

    try:
        control.send_keys("Reservations")
    except Exception:
        pass
    time.sleep(0.5)

    click_active_text_option(driver, "Reservations", timeout=10)
    WebDriverWait(driver, 10).until(
        lambda d: "Reservation & Pre-Arrival" in active_dialog_text(d)
    )
    log("Selected Reservations department")


def choose_reservation_prearrival_form(driver):
    WebDriverWait(driver, 15).until(
        lambda d: "Select Inspection" in active_dialog_text(d)
    )
    log("Select Inspection dialog opened")
    ensure_reservations_department(driver)
    click_active_text_option(driver, "Reservation & Pre-Arrival", timeout=10, exact_only=True)
    log("Selected Reservation & Pre-Arrival inspection form")


def open_inspection_selector(driver, timeout=10):
    try:
        if driver.execute_script(OPEN_INSPECTION_SELECTOR_SCRIPT):
            log("Opened Select Inspection dialog through KYC app event")
            return
    except Exception as e:
        log(f"KYC app event could not open Select Inspection dialog: {e}")

    click_main_action_button(driver, "Inspection", timeout=timeout)


def open_reservation_prearrival_inspection(driver, timeout=10):
    for attempt in range(1, 3):
        log(f"Selecting Inspection option, attempt {attempt}")
        open_inspection_selector(driver, timeout=timeout)

        try:
            choose_reservation_prearrival_form(driver)
            return
        except TimeoutException:
            text = active_dialog_text(driver)
            if "Editing Inspection" in text and "Reservation & Pre-Arrival" not in text:
                log("Wrong inspection form opened; closing it and retrying")
                close_active_dialog(driver)
                click_add_button(driver, 10)
                continue
            raise

    raise TimeoutException("Could not open Reservation & Pre-Arrival inspection form")


def find_labeled_control(driver, label_text):
    control = driver.execute_script(CONTROL_NEAR_TEXT_SCRIPT, label_text)
    if control is not None:
        try:
            if control.is_displayed() and control.is_enabled():
                return control
        except Exception:
            pass

    label_lower = label_text.lower()
    candidates = driver.find_elements(
        By.CSS_SELECTOR,
        "select,input,textarea,button,[role='combobox'],[aria-label],[placeholder],[class*='select'],[class*='dropdown']",
    )
    for element in candidates:
        try:
            text = " ".join(
                value
                for value in [
                    element.get_attribute("aria-label"),
                    element.get_attribute("placeholder"),
                    element.get_attribute("name"),
                    element.get_attribute("id"),
                    element.get_attribute("class"),
                    element.text,
                ]
                if value
            ).lower()
            if label_lower in text and element.is_displayed() and element.is_enabled():
                return element
        except Exception:
            pass

    return None


def select_team_member(driver, team_member):
    log(f"Selecting team member: {team_member}")

    employee_inputs = visible_elements(driver, (By.ID, "employeeSearchId"))
    if employee_inputs:
        employee_input = employee_inputs[0]
        click_element(driver, employee_input)
        try:
            employee_input.send_keys(Keys.CONTROL, "a")
            employee_input.send_keys(Keys.BACKSPACE)
        except Exception:
            pass
        employee_input.send_keys(team_member)
        time.sleep(1.0)
        try:
            click_autocomplete_option(
                driver,
                team_member,
                timeout=12,
                preferred_class="team-member-search-results",
            )
        except TimeoutException:
            log("Team member dropdown option was not found; using keyboard selection")
            employee_input.send_keys(Keys.ARROW_DOWN)
            employee_input.send_keys(Keys.ENTER)
        time.sleep(0.75)
        selected_text = team_member_field_text(driver)
        if team_member not in selected_text:
            log(f"Team member field after selection: {selected_text or '[empty]'}")
        log(f"Selected team member using employeeSearchId: {team_member}")
        return

    native_selects = driver.find_elements(By.TAG_NAME, "select")
    for select in native_selects:
        try:
            if not select.is_displayed() or not select.is_enabled():
                continue
            options_text = " | ".join(option.text for option in select.find_elements(By.TAG_NAME, "option"))
            attrs = " ".join(
                value
                for value in [
                    select.get_attribute("aria-label"),
                    select.get_attribute("name"),
                    select.get_attribute("id"),
                    options_text,
                ]
                if value
            ).lower()
            if "team" in attrs or "member" in attrs or team_member.lower() in attrs:
                Select(select).select_by_visible_text(team_member)
                log(f"Selected team member with native select: {team_member}")
                return
        except Exception as e:
            log(f"Native team member select attempt failed: {e}")

    control = WebDriverWait(driver, 15).until(lambda d: find_labeled_control(d, "Team Member"))
    click_element(driver, control)
    time.sleep(0.25)

    tag_name = control.tag_name.lower()
    control_type = (control.get_attribute("type") or "").lower()
    if tag_name == "input" and control_type not in ("button", "submit", "checkbox", "radio"):
        try:
            control.clear()
        except Exception:
            pass
        control.send_keys(team_member)
        time.sleep(1.0)

    try:
        click_autocomplete_option(driver, team_member, timeout=15, preferred_class="team-member")
    except TimeoutException:
        control.send_keys(Keys.ARROW_DOWN)
        control.send_keys(Keys.ENTER)
    log(f"Selected team member: {team_member}")


def clear_area_field(driver):
    try:
        area_input = first_visible(driver, (By.CSS_SELECTOR, "input[aria-label='Area']"))
        if area_input is None:
            return

        area_container = driver.execute_script(
            "return arguments[0].closest('.v-input') || arguments[0].parentElement;",
            area_input,
        )
        clear_icon = None
        if area_container is not None:
            clear_candidates = area_container.find_elements(By.CSS_SELECTOR, ".v-input__icon--clear, .v-icon")
            for candidate in clear_candidates:
                try:
                    if candidate.is_displayed() and "clear" in (candidate.text or "").lower():
                        clear_icon = candidate
                        break
                except Exception:
                    pass

        if clear_icon is not None:
            click_element(driver, clear_icon)
            log("Cleared Area field")

        area_input.send_keys(Keys.ESCAPE)
    except Exception as e:
        log(f"Area clear skipped: {e}")


def choose_random_no_item(yes_items):
    if random.random() >= NO_FLIP_CHANCE:
        return None

    choices = list(yes_items)
    last_no_item = load_last_no_flip_item()
    if len(choices) > 1 and last_no_item in choices:
        choices.remove(last_no_item)

    no_item = random.choice(choices)
    try:
        save_last_no_flip_item(no_item)
    except OSError as e:
        log(f"Could not write random No flip history: {e}")

    return no_item



def set_checklist_yes_items(driver, yes_items):
    groups = [
        group
        for group in driver.find_elements(By.CSS_SELECTOR, "[role='radiogroup']")
        if group.is_displayed()
    ]
    log(f"Found {len(groups)} visible checklist radio groups")

    if len(groups) != EXPECTED_CHECKLIST_ITEMS:
        write_page_diagnostics(driver, "unexpected checklist size")
        raise TimeoutException(
            f"Expected {EXPECTED_CHECKLIST_ITEMS} checklist groups for Reservation & Pre-Arrival, found {len(groups)}"
        )

    if len(groups) < max(yes_items):
        write_page_diagnostics(driver, "missing checklist radio groups")
        raise TimeoutException(f"Expected at least {max(yes_items)} checklist groups, found {len(groups)}")

    no_item = choose_random_no_item(yes_items)
    if no_item is None:
        log("Checklist random No flip skipped")
    else:
        log(f"Checklist item {no_item}: Randomly selected to flip from Yes to No")

    for item_num in yes_items:
        group = groups[item_num - 1]
        answer = "No" if item_num == no_item else "Yes"
        answer_inputs = group.find_elements(By.CSS_SELECTOR, f"input[aria-label='{answer}']")
        if not answer_inputs:
            raise NoSuchElementException(f"Could not find {answer} radio for checklist item {item_num}")

        click_element(driver, answer_inputs[0])
        log(f"Checklist item {item_num}: Set to {answer}")
        time.sleep(0.2)


def click_complete_button(driver, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(COMPLETE_BUTTON_SCRIPT)
    )
    click_element(driver, element)
    log("Clicked Complete button")


def launch_edge(edge_path, msedgedriver_path):
    debug_port = choose_debug_port()
    attempts = [
        ("dedicated automation profile", automation_profile_dir(), None),
    ]
    first_error = None

    for profile_label, user_data_dir, profile_directory in attempts:
        try:
            log(f"Launching Edge with {profile_label}: {user_data_dir}")
            service = create_edge_service(msedgedriver_path)
            options = create_edge_options(edge_path, user_data_dir, profile_directory)
            if debug_port is not None:
                options.add_argument(f"--remote-debugging-port={debug_port}")
                log(f"Using DevTools port {debug_port} for launched Edge")
            driver = EdgeWebDriver(service=service, options=options)
            log(f"Connected to Edge successfully using {profile_label}")
            return driver, profile_label
        except Exception as e:
            if first_error is None:
                first_error = e
            log(f"Could not launch Edge with {profile_label}: {e}")

    message = f"Failed to launch Edge with msedgedriver: {first_error}"
    return None, message


def run_kyc_inspection(account_name=None, password=None, available_team_members=None):
    """Run the automated KYC inspection."""
    driver = None
    keep_browser_open = False
    try:
        log("Starting KYC automation")

        edge_path = find_edge_executable()
        if not edge_path:
            return fail("Microsoft Edge was not found. Please install Edge from https://www.microsoft.com/edge")

        log(f"Found Edge at: {edge_path}")
        msedgedriver_path = edgedriver_path()
        previous_foreground_window = foreground_window_handle()

        driver, launch_result = launch_edge(edge_path, msedgedriver_path)
        if driver is None:
            return fail(launch_result)
        force_desktop_window(driver)
        restore_foreground_window(previous_foreground_window)
        profile_label = launch_result
        if profile_label == "existing KYC tab":
            keep_browser_open = True

        route_to_inspections(driver)
        wait_for_page_ready(driver)
        log_browser_layout(driver)

        time.sleep(3)
        login_success, login_message = login_if_needed(driver, account_name, password)
        if not login_success:
            keep_browser_open = True
            return fail(login_message)

        route_to_inspections(driver)
        wait_for_page_ready(driver)
        time.sleep(3)
        log_browser_layout(driver)

        add_wait_seconds = 45 if profile_label == "dedicated automation profile" else 20
        click_add_button(driver, add_wait_seconds)
        time.sleep(0.5)

        open_reservation_prearrival_inspection(driver)
        WebDriverWait(driver, 15).until(reservation_prearrival_form_loaded)
        log("Reservation & Pre-Arrival inspection form loaded")

        clear_area_field(driver)
        time.sleep(0.5)

        team_member = choose_team_member(available_team_members)
        select_team_member(driver, team_member)
        time.sleep(1)

        log("Filling out checklist")
        set_checklist_yes_items(driver, YES_ITEMS)

        log("Scrolling to Complete button")
        driver.execute_script(
            """
            const roots = Array.from(document.querySelectorAll('.v-dialog--active, .v-dialog__content--active, [role="dialog"]'));
            const root = roots.find((el) => el.offsetParent !== null) || roots[0] || document.scrollingElement || document.body;
            root.scrollTop = root.scrollHeight;
            window.scrollTo(0, document.body.scrollHeight);
            """
        )
        time.sleep(1)

        log("Clicking Complete button")
        click_complete_button(driver, timeout=10)

        time.sleep(3)
        log("KYC inspection completed successfully")
        return True, "KYC inspection completed successfully"

    except TimeoutException as e:
        if driver:
            write_page_diagnostics(driver, "timeout")
        return fail(f"Timed out waiting for a KYC page element: {e}", e)
    except Exception as e:
        return fail(f"Error during automation: {e}", e)
    finally:
        if driver and not keep_browser_open:
            driver.quit()
            log("Browser closed")
        elif driver:
            log("Leaving browser open for sign-in")


if __name__ == "__main__":
    run_kyc_inspection()
