# KYC Reminder

KYC Reminder is a Windows desktop helper that runs the Hilton KYC inspection automation on a 15-minute reminder timer.

## What It Does

- Shows a timer for recurring KYC inspections.
- Lets the user enter KYC login credentials.
- Remembers the account number only when "Remember account on this computer" is checked.
- Lets the user select which team members are on phones today.
- Runs the Selenium/Microsoft Edge automation in the background.
- Shows a login-error popup when the KYC login fails.

## Project Layout

- `Files/kyc_reminder.py` - Tkinter desktop app.
- `Files/kyc_automation.py` - Selenium automation.
- `Files/build.bat` - builds `KYCReminder.exe`.
- `Files/setup_wizard.py` - no-admin installer wizard.
- `Files/build_installer.bat` - builds `KYCReminderSetup.exe`.
- `Files/download_edgedriver.py` - downloads Microsoft Edge WebDriver for build machines.
- `Files/requirements.txt` - Python dependencies.
- `Files/assets/` - app icon assets.

## Build Locally

From `Files`:

```bat
build.bat
build_installer.bat
```

The build outputs are copied to the project root:

- `KYCReminder.exe`
- `KYCReminderSetup.exe`

## No-Admin Installation

Send teammates this one file:

```text
KYCReminderSetup.exe
```

They do not need the source folder, Python, Selenium, or `msedgedriver.exe` separately. The setup wizard is a single executable that unpacks the application and installs it for the current Windows user.

The installer wizard installs to:

```text
%LOCALAPPDATA%\Programs\KYCReminder
```

It creates per-user shortcuts and does not write to `Program Files`, so it should not request administrator rights. When internet access is available, it also downloads a Microsoft Edge WebDriver matching that computer's installed Edge version. If the download fails, it falls back to the bundled driver.

## GitHub Builds

The included GitHub Actions workflow builds the app and installer on Windows and uploads both executables as workflow artifacts.

To make downloadable public releases, create a GitHub release or push a tag named like `v1.0.0`; the workflow will attach the built executables to that release.
