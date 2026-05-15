import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import json
import os
import sys
import threading
from kyc_automation import TEAM_MEMBERS, app_dir, run_kyc_inspection

# Configuration
REMINDER_MINUTES = 15
APP_TITLE = "KYC Inspection Reminder"
APP_ICON_PATH = os.path.join("assets", "KYCReminder.ico")
SETTINGS_FILE_NAME = "settings.json"


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def settings_path() -> str:
    return os.path.join(app_dir(), SETTINGS_FILE_NAME)


def load_settings() -> dict:
    try:
        with open(settings_path(), "r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except (OSError, json.JSONDecodeError):
        return {}

    return settings if isinstance(settings, dict) else {}


def save_settings(settings: dict) -> None:
    with open(settings_path(), "w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, indent=2)


class KYCReminderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("560x600")
        self.root.minsize(560, 600)

        self.style = ttk.Style()
        self._configure_style()

        self.next_due = None
        self.timer_running = False
        self.automation_running = False
        self.reset_timer_when_automation_finishes = False
        self.last_automation_error = None
        self.settings = load_settings()
        saved_account = self.settings.get("account") if self.settings.get("remember_account") else ""
        self.account_var = tk.StringVar(value=os.environ.get("KYC_ACCOUNT", saved_account or ""))
        self.password_var = tk.StringVar(value=os.environ.get("KYC_PASSWORD", ""))
        self.remember_account_var = tk.BooleanVar(value=bool(self.settings.get("remember_account")))
        saved_phone_team = self.settings.get("phone_team_members")
        if not isinstance(saved_phone_team, list):
            saved_phone_team = TEAM_MEMBERS
        self.team_member_vars = {
            name: tk.BooleanVar(value=name in saved_phone_team)
            for name in TEAM_MEMBERS
        }

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()

    def _configure_style(self) -> None:
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        self.style.configure("Body.TLabel", font=("Segoe UI", 11))
        self.style.configure("Small.TLabel", font=("Segoe UI", 10))
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        self.style.configure("Danger.TLabel", foreground="#b00020", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="KYC Inspection Reminder", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Start the timer to receive KYC inspection reminders every 15 minutes.",
            style="Body.TLabel",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", pady=(8, 20))

        info_frame = ttk.Frame(container)
        info_frame.pack(fill="x", pady=(0, 20))
        info_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(info_frame, text="Status: Idle", style="Body.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w", pady=4)

        self.next_due_label = ttk.Label(info_frame, text="", style="Body.TLabel")
        self.next_due_label.grid(row=1, column=0, sticky="w", pady=4)
        self.next_due_label.grid_remove()

        self.countdown_label = ttk.Label(info_frame, text="", style="Danger.TLabel")
        self.countdown_label.grid(row=2, column=0, sticky="w", pady=4)
        self.countdown_label.grid_remove()

        self.automation_label = ttk.Label(info_frame, text="", style="Body.TLabel")
        self.automation_label.grid(row=3, column=0, sticky="w", pady=4)
        self.automation_label.grid_remove()

        credentials_frame = ttk.LabelFrame(container, text="KYC Login", padding=12)
        credentials_frame.pack(fill="x", pady=(0, 16))
        credentials_frame.columnconfigure(1, weight=1)

        ttk.Label(credentials_frame, text="Account", style="Small.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(credentials_frame, textvariable=self.account_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 0),
        )

        ttk.Label(credentials_frame, text="Password", style="Small.TLabel").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0),
        )
        ttk.Entry(credentials_frame, textvariable=self.password_var, show="*").grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=(8, 0),
        )
        ttk.Checkbutton(
            credentials_frame,
            text="Remember account on this computer",
            variable=self.remember_account_var,
        ).grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

        team_frame = ttk.LabelFrame(container, text="On Phones Today", padding=12)
        team_frame.pack(fill="x", pady=(0, 16))

        for index, name in enumerate(TEAM_MEMBERS):
            ttk.Checkbutton(
                team_frame,
                text=name,
                variable=self.team_member_vars[name],
            ).grid(row=index, column=0, sticky="w", pady=(0 if index == 0 else 6, 0))

        button_frame = ttk.Frame(container)
        button_frame.pack(fill="x", pady=(10, 0))

        self.start_button = ttk.Button(
            button_frame,
            text="Start Timer",
            style="Primary.TButton",
            command=self.start_timer
        )
        self.start_button.pack(side="left")

        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            style="Primary.TButton",
            command=self.cancel_timer,
            state="disabled"
        )
        self.cancel_button.pack(side="left", padx=(10, 0))

        self.run_now_button = ttk.Button(
            button_frame,
            text="Run Now",
            style="Primary.TButton",
            command=self.run_automation_now
        )
        self.run_now_button.pack(side="left", padx=(10, 0))

        ttk.Label(
            container,
            text="When the timer expires, the KYC inspection will run automatically in the background.",
            style="Small.TLabel",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", pady=(20, 0))

    def reset_timer(self) -> None:
        self.next_due = datetime.now() + timedelta(minutes=REMINDER_MINUTES)
        self.update_labels()

    def start_timer(self) -> None:
        self._save_settings()
        self.timer_running = True
        self.next_due = datetime.now() + timedelta(minutes=REMINDER_MINUTES)
        self.status_label.config(text="Status: Running")
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.update_labels()

    def cancel_timer(self) -> None:
        self.timer_running = False
        self.next_due = None
        self.reset_timer_when_automation_finishes = False
        self.status_label.config(text="Status: Idle")
        self.next_due_label.config(text="")
        self.countdown_label.config(text="")
        self.next_due_label.grid_remove()
        self.countdown_label.grid_remove()
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

    def update_labels(self) -> None:
        if self.next_due is None:
            return

        now = datetime.now()
        remaining = self.next_due - now

        if remaining.total_seconds() < 0:
            remaining = timedelta(seconds=0)

        minutes, seconds = divmod(int(remaining.total_seconds()), 60)

        self.next_due_label.config(
            text=f"Next reminder: {self.next_due.strftime('%I:%M:%S %p')}"
        )
        self.countdown_label.config(
            text=f"Time remaining: {minutes:02d}:{seconds:02d}"
        )
        self.next_due_label.grid()
        self.countdown_label.grid()

    def _tick(self) -> None:
        self.update_labels()

        if self.timer_running and self.next_due is not None and datetime.now() >= self.next_due:
            if self.automation_running:
                self.next_due_label.grid()
                self.countdown_label.grid()
                self.next_due_label.config(text="Next reminder: waiting for automation to finish")
                self.countdown_label.config(text="Time remaining: 00:00")
            else:
                self.start_automation(reset_timer_after_completion=True)

        self.root.after(1000, self._tick)

    def _set_automation_status(self, text: str, color: str) -> None:
        self.automation_label.config(text=text, foreground=color)
        if text:
            self.automation_label.grid()
        else:
            self.automation_label.grid_remove()

    def _selected_team_members(self) -> list[str]:
        return [name for name, var in self.team_member_vars.items() if var.get()]

    def _save_settings(self) -> None:
        remember_account = self.remember_account_var.get()
        settings = {
            "remember_account": remember_account,
            "account": self.account_var.get().strip() if remember_account else "",
            "phone_team_members": self._selected_team_members(),
        }
        try:
            save_settings(settings)
        except OSError:
            pass

    def _on_close(self) -> None:
        self._save_settings()
        self.root.destroy()

    def _is_login_error(self, message: str | None) -> bool:
        message = (message or "").lower()
        login_terms = ("login", "account", "password", "sign-in", "sign in")
        credential_terms = ("incorrect", "check", "did not complete", "not complete")
        return any(term in message for term in login_terms) and any(
            term in message for term in credential_terms
        )

    def _finish_automation(self, success: bool, message: str | None = None) -> None:
        if success:
            self._set_automation_status("Status: Automation complete!", "#388E3C")
        else:
            message = message or "KYC automation returned a failure"
            self._set_automation_status(f"Status: Automation failed - {message}", "#b00020")
            if self._is_login_error(message):
                messagebox.showerror(
                    "Login Error",
                    "Login error, username and password are incorrect",
                )
        self.automation_running = False
        if self.reset_timer_when_automation_finishes and self.timer_running:
            self.reset_timer_when_automation_finishes = False
            self.next_due = datetime.now() + timedelta(minutes=REMINDER_MINUTES)
            self.update_labels()
        else:
            self.reset_timer_when_automation_finishes = False

    def start_automation(self, reset_timer_after_completion: bool = False) -> None:
        """Start the KYC automation in a separate thread."""
        if self.automation_running:
            return
        
        self.automation_running = True
        self.reset_timer_when_automation_finishes = reset_timer_after_completion
        self._set_automation_status("Status: Running automation...", "#b00020")
        account_name = self.account_var.get().strip()
        password = self.password_var.get()
        selected_team_members = self._selected_team_members()

        if not selected_team_members:
            messagebox.showerror(
                "Team Member Required",
                "Select at least one team member who is on phones today.",
            )
            self.automation_running = False
            self.reset_timer_when_automation_finishes = False
            self._set_automation_status("", "#000000")
            return

        self._save_settings()
        
        def run_automation():
            try:
                result = run_kyc_inspection(
                    account_name=account_name,
                    password=password,
                    available_team_members=selected_team_members,
                )
                if isinstance(result, tuple):
                    success, message = result
                else:
                    success = bool(result)
                    message = None if success else "KYC automation returned a failure"
                self.root.after(0, self._finish_automation, bool(success), message)
            except Exception as e:
                self.root.after(0, self._finish_automation, False, str(e))
        
        thread = threading.Thread(target=run_automation, daemon=True)
        thread.start()

    def run_automation_now(self) -> None:
        """Run automation immediately without waiting for timer."""
        self.start_automation(reset_timer_after_completion=False)


def main() -> None:
    root = tk.Tk()
    try:
        root.iconbitmap(resource_path(APP_ICON_PATH))
    except tk.TclError:
        pass
    app = KYCReminderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
