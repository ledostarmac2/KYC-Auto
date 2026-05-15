import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "KYC Reminder"
APP_EXE_NAME = "KYCReminder.exe"
SETUP_TITLE = "KYC Reminder Setup Wizard"
PUBLISHER = "KYC Reminder"
EDGEDRIVER_ZIP_NAME = "edgedriver_win64.zip"


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def default_install_dir() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(local_app_data, "Programs", "KYCReminder")


def desktop_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop")


def start_menu_dir() -> str:
    return os.path.join(
        os.environ.get("APPDATA") or os.path.expanduser("~"),
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        APP_NAME,
    )


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def find_edge_version() -> str | None:
    candidate_roots = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application",
        r"C:\Program Files\Microsoft\Edge\Application",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application"),
    ]
    versions: list[str] = []
    for root in candidate_roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", name):
                versions.append(name)

    if not versions:
        return None
    return sorted(versions, key=version_tuple)[-1]


def create_shortcut(shortcut_path: str, target_path: str, working_dir: str, icon_path: str) -> None:
    os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "KYC_SHORTCUT_PATH": shortcut_path,
            "KYC_TARGET_PATH": target_path,
            "KYC_WORKING_DIR": working_dir,
            "KYC_ICON_LOCATION": icon_path,
        }
    )
    script = r"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($env:KYC_SHORTCUT_PATH)
$shortcut.TargetPath = $env:KYC_TARGET_PATH
$shortcut.WorkingDirectory = $env:KYC_WORKING_DIR
$shortcut.IconLocation = $env:KYC_ICON_LOCATION
$shortcut.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class SetupWizard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(SETUP_TITLE)
        self.root.geometry("660x500")
        self.root.minsize(660, 500)
        self.root.resizable(False, False)

        self.install_dir_var = tk.StringVar(value=default_install_dir())
        self.desktop_shortcut_var = tk.BooleanVar(value=True)
        self.start_menu_shortcut_var = tk.BooleanVar(value=True)
        self.update_driver_var = tk.BooleanVar(value=True)
        self.launch_after_install_var = tk.BooleanVar(value=True)
        self.installed_app_path: str | None = None
        self.install_failed = False

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        self.style.configure("Body.TLabel", font=("Segoe UI", 10))
        self.style.configure("Small.TLabel", font=("Segoe UI", 9))
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        self.style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#dfe8df",
            background="#1f8f3a",
            lightcolor="#1f8f3a",
            darkcolor="#17692c",
        )

        self.page = ttk.Frame(self.root, padding=24)
        self.page.pack(fill="both", expand=True)
        self.footer = ttk.Frame(self.root, padding=(24, 0, 24, 18))
        self.footer.pack(fill="x")

        self.back_button = ttk.Button(self.footer, text="Back", command=self.show_options)
        self.next_button = ttk.Button(self.footer, text="Next", style="Primary.TButton", command=self.show_options)
        self.cancel_button = ttk.Button(self.footer, text="Cancel", command=self.root.destroy)
        self.install_button = ttk.Button(self.footer, text="Install", style="Primary.TButton", command=self.start_install)
        self.finish_button = ttk.Button(self.footer, text="Finish", style="Primary.TButton", command=self.finish)

        self.show_welcome()

    def clear_page(self) -> None:
        for child in self.page.winfo_children():
            child.destroy()
        for child in self.footer.winfo_children():
            child.pack_forget()

    def show_welcome(self) -> None:
        self.clear_page()
        ttk.Label(self.page, text="KYC Reminder Setup Wizard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self.page,
            text=(
                "This single setup file installs KYC Reminder for the current Windows user. "
                "It does not write to Program Files and does not request administrator rights."
            ),
            style="Body.TLabel",
            wraplength=570,
            justify="left",
        ).pack(anchor="w", pady=(18, 0))
        ttk.Label(
            self.page,
            text=(
                "The setup file unpacks the app, bundled Python runtime, and Selenium automation pieces. "
                "The wizard can also download a matching Microsoft Edge WebDriver into the app folder."
            ),
            style="Body.TLabel",
            wraplength=570,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

        self.cancel_button.pack(side="right")
        self.next_button.pack(side="right", padx=(0, 10))

    def show_options(self) -> None:
        self.clear_page()
        ttk.Label(self.page, text="Installation Options", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.page, text="Install KYC Reminder to:", style="Body.TLabel").pack(anchor="w", pady=(20, 6))

        destination = ttk.Frame(self.page)
        destination.pack(fill="x")
        destination.columnconfigure(0, weight=1)
        ttk.Entry(destination, textvariable=self.install_dir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(destination, text="Browse...", command=self.choose_install_dir).grid(row=0, column=1, padx=(10, 0))

        checks = ttk.Frame(self.page)
        checks.pack(fill="x", pady=(20, 0))
        ttk.Checkbutton(
            checks,
            text="Create Desktop shortcut",
            variable=self.desktop_shortcut_var,
        ).pack(anchor="w", pady=4)
        ttk.Checkbutton(
            checks,
            text="Create Start Menu shortcut",
            variable=self.start_menu_shortcut_var,
        ).pack(anchor="w", pady=4)
        ttk.Checkbutton(
            checks,
            text="Download/update Microsoft Edge WebDriver for this computer",
            variable=self.update_driver_var,
        ).pack(anchor="w", pady=4)
        ttk.Checkbutton(
            checks,
            text="Launch KYC Reminder after installation",
            variable=self.launch_after_install_var,
        ).pack(anchor="w", pady=4)

        ttk.Label(
            self.page,
            text="Everything is installed under your Windows profile, so this setup can run without admin rights.",
            style="Small.TLabel",
            wraplength=570,
        ).pack(anchor="w", pady=(22, 0))

        self.cancel_button.pack(side="right")
        self.install_button.pack(side="right", padx=(0, 10))
        self.back_button.pack(side="right", padx=(0, 10))

    def choose_install_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=os.path.dirname(self.install_dir_var.get()))
        if chosen:
            self.install_dir_var.set(chosen)

    def show_installing(self) -> None:
        self.clear_page()
        ttk.Label(self.page, text="Installing", style="Title.TLabel").pack(anchor="w")
        self.status_label = ttk.Label(self.page, text="Preparing installation...", style="Body.TLabel")
        self.status_label.pack(anchor="w", pady=(22, 8))
        self.progress = ttk.Progressbar(
            self.page,
            mode="determinate",
            maximum=100,
            style="Green.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x")
        self.detail_label = ttk.Label(self.page, text="", style="Small.TLabel", wraplength=570)
        self.detail_label.pack(anchor="w", pady=(12, 0))
        self.cancel_button.config(state="disabled")
        self.cancel_button.pack(side="right")

    def start_install(self) -> None:
        install_dir = self.install_dir_var.get().strip()
        if not install_dir:
            messagebox.showerror("Install Folder Required", "Choose an install folder.")
            return
        self.show_installing()
        thread = threading.Thread(target=self.run_install, daemon=True)
        thread.start()

    def update_progress(self, percent: int, status: str, detail: str = "") -> None:
        self.progress["value"] = percent
        self.status_label.config(text=status)
        self.detail_label.config(text=detail)

    def run_install(self) -> None:
        steps = [
            ("Creating install folder", self.create_install_folder),
            ("Installing application files", self.copy_application_files),
            ("Installing Microsoft Edge WebDriver", self.install_edgedriver),
            ("Writing install manifest", self.write_manifest),
            ("Creating shortcuts", self.create_shortcuts),
            ("Verifying installation", self.verify_install),
        ]
        try:
            for index, (label, func) in enumerate(steps, start=1):
                percent = int(((index - 1) / len(steps)) * 100)
                self.root.after(0, self.update_progress, percent, label)
                detail = func()
                self.root.after(0, self.update_progress, int((index / len(steps)) * 100), label, detail or "")
            self.root.after(0, self.show_complete)
        except Exception as exc:
            self.install_failed = True
            self.root.after(0, self.show_failed, str(exc))

    def install_dir(self) -> str:
        return self.install_dir_var.get().strip()

    def payload_file(self, name: str) -> str:
        packaged_path = resource_path(os.path.join("payload", name))
        if os.path.exists(packaged_path):
            return packaged_path
        source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", name))
        return source_path

    def create_install_folder(self) -> str:
        os.makedirs(self.install_dir(), exist_ok=True)
        return self.install_dir()

    def copy_application_files(self) -> str:
        source = self.payload_file(APP_EXE_NAME)
        if not os.path.exists(source):
            raise FileNotFoundError(f"Could not find {APP_EXE_NAME}. Build the app before building the installer.")

        target = os.path.join(self.install_dir(), APP_EXE_NAME)
        shutil.copy2(source, target)
        self.installed_app_path = target

        for file_name in ("LICENSE", "EULA"):
            license_path = resource_path(os.path.join("licenses", file_name))
            if os.path.exists(license_path):
                shutil.copy2(license_path, os.path.join(self.install_dir(), file_name))

        return target

    def install_edgedriver(self) -> str:
        target = os.path.join(self.install_dir(), "msedgedriver.exe")
        bundled_driver = self.payload_file("msedgedriver.exe")
        if os.path.exists(bundled_driver):
            shutil.copy2(bundled_driver, target)

        if not self.update_driver_var.get():
            return "Using bundled Microsoft Edge WebDriver."

        edge_version = find_edge_version()
        if not edge_version:
            return "Microsoft Edge was not found; using bundled driver if available."

        url = f"https://msedgedriver.microsoft.com/{edge_version}/{EDGEDRIVER_ZIP_NAME}"
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, EDGEDRIVER_ZIP_NAME)
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, "r") as archive:
                    driver_member = next(
                        (name for name in archive.namelist() if name.lower().endswith("msedgedriver.exe")),
                        None,
                    )
                    if driver_member is None:
                        raise FileNotFoundError("Downloaded EdgeDriver package did not contain msedgedriver.exe.")
                    with archive.open(driver_member) as source, open(target, "wb") as destination:
                        shutil.copyfileobj(source, destination)
            return f"Downloaded EdgeDriver {edge_version}."
        except Exception as exc:
            if os.path.exists(target):
                return f"Could not update EdgeDriver; using bundled driver. Details: {exc}"
            raise

    def write_manifest(self) -> str:
        manifest = {
            "app": APP_NAME,
            "publisher": PUBLISHER,
            "installed_at": datetime.now().isoformat(timespec="seconds"),
            "install_dir": self.install_dir(),
            "admin_required": False,
        }
        manifest_path = os.path.join(self.install_dir(), "install.json")
        with open(manifest_path, "w", encoding="utf-8") as manifest_file:
            json.dump(manifest, manifest_file, indent=2)
        self.write_uninstaller()
        return manifest_path

    def write_uninstaller(self) -> None:
        uninstall_path = os.path.join(self.install_dir(), "Uninstall KYC Reminder.cmd")
        start_menu = start_menu_dir()
        desktop_shortcut = os.path.join(desktop_dir(), f"{APP_NAME}.lnk")
        script = f"""@echo off
set "INSTALL_DIR=%~dp0"
del "{desktop_shortcut}" >nul 2>nul
rmdir /S /Q "{start_menu}" >nul 2>nul
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 1; Remove-Item -LiteralPath '%INSTALL_DIR%' -Recurse -Force"
"""
        with open(uninstall_path, "w", encoding="utf-8") as uninstall_file:
            uninstall_file.write(script)

    def create_shortcuts(self) -> str:
        app_path = self.installed_app_path or os.path.join(self.install_dir(), APP_EXE_NAME)
        shortcuts: list[str] = []
        if self.desktop_shortcut_var.get():
            shortcut = os.path.join(desktop_dir(), f"{APP_NAME}.lnk")
            create_shortcut(shortcut, app_path, self.install_dir(), app_path)
            shortcuts.append("Desktop")

        if self.start_menu_shortcut_var.get():
            shortcut = os.path.join(start_menu_dir(), f"{APP_NAME}.lnk")
            create_shortcut(shortcut, app_path, self.install_dir(), app_path)
            uninstall_shortcut = os.path.join(start_menu_dir(), "Uninstall KYC Reminder.lnk")
            create_shortcut(
                uninstall_shortcut,
                os.path.join(self.install_dir(), "Uninstall KYC Reminder.cmd"),
                self.install_dir(),
                app_path,
            )
            shortcuts.append("Start Menu")

        return ", ".join(shortcuts) if shortcuts else "No shortcuts selected."

    def verify_install(self) -> str:
        app_path = self.installed_app_path or os.path.join(self.install_dir(), APP_EXE_NAME)
        if not os.path.exists(app_path):
            raise FileNotFoundError("KYC Reminder was not installed.")
        return "Installation verified."

    def show_complete(self) -> None:
        self.clear_page()
        ttk.Label(self.page, text="Installation Complete", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self.page,
            text="KYC Reminder has been installed for this Windows user.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(20, 0))
        ttk.Label(self.page, text=self.install_dir(), style="Small.TLabel", wraplength=570).pack(anchor="w", pady=(8, 0))
        self.finish_button.pack(side="right")

    def show_failed(self, message: str) -> None:
        self.clear_page()
        ttk.Label(self.page, text="Installation Failed", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.page, text=message, style="Body.TLabel", wraplength=570, justify="left").pack(anchor="w", pady=(20, 0))
        self.cancel_button.config(text="Close", state="normal")
        self.cancel_button.pack(side="right")

    def finish(self) -> None:
        app_path = self.installed_app_path or os.path.join(self.install_dir(), APP_EXE_NAME)
        should_launch = self.launch_after_install_var.get() and os.path.exists(app_path)
        self.root.destroy()
        if should_launch:
            subprocess.Popen([app_path], cwd=os.path.dirname(app_path))


def main() -> None:
    root = tk.Tk()
    icon_path = resource_path(os.path.join("assets", "KYCReminder.ico"))
    try:
        root.iconbitmap(icon_path)
    except tk.TclError:
        pass
    SetupWizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
