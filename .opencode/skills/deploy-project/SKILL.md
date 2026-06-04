---
name: deploy-project
description: Deploy a project to a VPS server with SSH user, GitHub Secrets, and CI/CD auto-deploy on push. Use when the user asks to deploy, set up CI/CD, or configure a server for auto-deployment.
license: MIT
metadata:
  author: dichenko
  version: "1.0"
---

Deploy a project from a GitHub repository to a Linux VPS server with automatic CI/CD.

**Prerequisites**: SSH access to the server (root or sudo), `gh` CLI authenticated with `repo` and `workflow` scopes, Docker and Docker Compose installed on the server.

**Input**: The user must provide or confirm:
- Server SSH alias (e.g., `vdska`)
- Target path on server (e.g., `/opt/project-name`)
- GitHub repository (e.g., `dichenko/project-name`)
- Branch to deploy (default: `master`)
- Deploy username (format: `deploy-<projectsuffix>`)

**Steps**

1. **Deploy project to server**

   Clone the repository directly on the server:
   ```bash
   ssh <alias> "git clone https://github.com/<owner>/<repo>.git <target_path>"
   ```

   If the project already exists, omit the clone step and use `git pull` instead.

   Copy `.env.example` to `.env` (if not present):
   ```bash
   ssh <alias> "cd <target_path> && cp -n .env.example .env 2>/dev/null"
   ```

2. **Create deploy user with SSH key**

   Create a dedicated user, generate an ed25519 key pair, add the public key to authorized_keys, add user to `docker` group:
   ```bash
   ssh <alias> "useradd -m -s /bin/bash <username>"
   ssh <alias> "mkdir -p /home/<username>/.ssh && chmod 700 /home/<username>/.ssh"
   ssh <alias> "ssh-keygen -t ed25519 -f /home/<username>/.ssh/id_ed25519 -N '' -C '<username>@<server>'"
   ssh <alias> "cat /home/<username>/.ssh/id_ed25519.pub >> /home/<username>/.ssh/authorized_keys"
   ssh <alias> "chmod 600 /home/<username>/.ssh/authorized_keys"
   ssh <alias> "chown -R <username>:<username> /home/<username>/.ssh"
   ssh <alias> "usermod -aG docker <username>"
   ssh <alias> "chown -R <username>:<username> <target_path>"
   ```

   Fix git dubious ownership for the deploy user:
   ```bash
   ssh <alias> "sudo -u <username> git config --global --add safe.directory <target_path>"
   ```

   Verify deploy user can access docker:
   ```bash
   ssh <alias> "sudo -u <username> docker ps"
   ```

3. **Configure GitHub Secrets**

   Get the private key content from the server:
   ```bash
   $privateKey = ssh <alias> "cat /home/<username>/.ssh/id_ed25519"
   ```

   Set GitHub Secrets using `gh` CLI:
   ```bash
   gh secret set SSH_PRIVATE_KEY -R <owner>/<repo> --body "$privateKey"
   gh secret set SSH_HOST -R <owner>/<repo> --body "<server_ip>"
   gh secret set SSH_USER -R <owner>/<repo> --body "<username>"
   gh secret set SSH_PORT -R <owner>/<repo> --body "22"
   ```

   Verify secrets are set:
   ```bash
   gh secret list -R <owner>/<repo>
   ```

4. **Create GitHub Actions workflow**

   Create `.github/workflows/deploy.yml`:
   ```yaml
   name: Deploy to <server>

   on:
     push:
       branches: [<branch>]

   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - name: Deploy via SSH
           uses: appleboy/ssh-action@v1
           with:
             host: ${{ secrets.SSH_HOST }}
             port: ${{ secrets.SSH_PORT }}
             username: ${{ secrets.SSH_USER }}
             key: ${{ secrets.SSH_PRIVATE_KEY }}
             script: |
               set -e
               cd <target_path>
               git checkout <branch>
               git pull origin <branch>
               cd infra
               docker compose up -d --build
   ```

   The `docker compose` command should match the project structure. Adjust the `cd` path as needed (e.g., `cd infra` if `docker-compose.yml` lives there).

5. **Commit and push the workflow**

   ```bash
   git add -A
   git commit -m "Add GitHub Actions CI/CD for auto-deploy on push"
   git push
   ```

6. **Verify**

   After push, check GitHub Actions tab for the running workflow. Verify containers are up:
   ```bash
   ssh <alias> "sudo -u <username> docker ps"
   ```

**Important notes**
- The server must have `git` and `docker compose` installed.
- The deploy user must be in the `docker` group to run docker commands.
- The `.env` file on the server must be filled with real values (bot token, DB credentials, etc.) — only `.env.example` is copied automatically.
- For private repos, the deploy user needs a GitHub token or SSH key added as a deploy key to the repo.
- Never store the private key in the repository — only in GitHub Secrets.
