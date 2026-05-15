# GitHub Setup

## Do Not Share Passwords

You do not need to give anyone your GitHub password. GitHub ownership works through your GitHub account, repository permissions, and browser-based authorization.

## Recommended Ownership Setup

1. Sign in to GitHub as your own account.
2. Create a new repository, for example:

   ```text
   ledostarmac2/KYC-Auto
   ```

3. Keep the repository under your account if you want to be the owner.
4. Add collaborators later only if you want other people to work on it.
5. Use GitHub Releases or Actions artifacts to download the latest build from any computer.

## How I Can Publish It For You

This workspace is already connected to GitHub as:

```text
ledostarmac2
```

Right now, no repositories are exposed to the connector. To let me publish directly:

1. Open the GitHub connector/app authorization page from ChatGPT/Codex.
2. Install or configure the GitHub app for your account.
3. Choose either "All repositories" or select this repository:

   ```text
   ledostarmac2/KYC-Auto
   ```

4. Come back and tell me it is authorized.

After that, I can upload the project files, create branches, and open pull requests through the connector.

## If You Want To Publish Manually

Install Git for Windows or use GitHub Desktop. Then from this folder:

```bat
git init
git branch -M main
git add .
git commit -m "Initial KYC Reminder project"
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## What Gets Stored In GitHub

The repository should store the source code, build scripts, icon assets, installer source, and workflow files.

Generated executables are ignored locally and should be downloaded from GitHub Actions artifacts or GitHub Releases instead of being committed to the repository.
