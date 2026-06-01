# GitHub Actions 配置说明

这个文件专门说明 `Reminder` 项目的 GitHub Actions 部署参数应该怎么配。

## 一、进入配置页面

打开你的 GitHub 仓库：

`https://github.com/juemimgcd/agenticRAG`

然后进入：

`Settings -> Secrets and variables -> Actions`

这个页面里有两个你要用到的区域：

- `Secrets`
- `Variables`

---

## 二、Secrets 和 Variables 的区别

### 1. Secrets

用来保存敏感信息，值不会明文显示。

这个项目里，敏感信息主要是：

- `DEPLOY_SSH_KEY`
- `DEPLOY_PASSWORD`

### 2. Variables

用来保存普通配置，适合放不敏感的信息。

这个项目里，普通配置主要是：

- `DEPLOY_HOST`
- `DEPLOY_PORT`
- `DEPLOY_USER`
- `DEPLOY_APP_DIR`
- `DEPLOY_BRANCH`
- `DEPLOY_ENABLE_NGINX_SYNC`

---

## 三、推荐配置方式

### Repository variables

点击 `Variables` 区域里的 `New repository variable`，依次添加下面这些：

#### 1. DEPLOY_HOST

- Name: `DEPLOY_HOST`
- Value: `124.223.14.145`

#### 2. DEPLOY_PORT

- Name: `DEPLOY_PORT`
- Value: `22`

#### 3. DEPLOY_USER

- Name: `DEPLOY_USER`
- Value: `root`

#### 4. DEPLOY_APP_DIR

- Name: `DEPLOY_APP_DIR`
- Value: `/opt/reminder`

说明：这是你服务器上项目所在目录。  
如果你的项目不是放在 `/opt/reminder`，就改成你的真实目录。

#### 5. DEPLOY_BRANCH

- Name: `DEPLOY_BRANCH`
- Value: `master`

#### 6. DEPLOY_ENABLE_NGINX_SYNC

- Name: `DEPLOY_ENABLE_NGINX_SYNC`
- Value: `1`

说明：

- `1` 表示部署时会同步并重载 Nginx
- `0` 表示部署时跳过 Nginx 同步

---

### Repository secrets

点击 `Secrets` 区域里的 `New repository secret`，添加下面这些。

#### 1. DEPLOY_SSH_KEY

- Name: `DEPLOY_SSH_KEY`
- Secret: 你的 SSH 私钥全文

注意：

- 这里填的是私钥
- 不是 `.pub` 公钥
- 要把整个文件内容完整粘贴进去

如果你本机私钥文件是：

```powershell
$HOME\.ssh\reminder_actions_v2
```

可以先查看内容：

```powershell
Get-Content $HOME\.ssh\reminder_actions_v2
```

把完整输出复制到 `DEPLOY_SSH_KEY`。

#### 2. DEPLOY_PASSWORD

这个不是必须的。

只有在你想走“用户名 + 密码”登录服务器时才需要配置。

如果你已经切到 SSH key 登录，就不要再配这个，或者把它删掉。

---

## 四、你这台服务器的推荐最终配置

### Variables

```text
DEPLOY_HOST=124.223.14.145
DEPLOY_PORT=22
DEPLOY_USER=root
DEPLOY_APP_DIR=/opt/reminder
DEPLOY_BRANCH=master
DEPLOY_ENABLE_NGINX_SYNC=1
```

### Secrets

```text
DEPLOY_SSH_KEY=你的私钥全文
```

---

## 五、配置完成后怎么验证

配置完成后，重新推送代码或者手动触发 GitHub Actions。

注意：

- `push` 到 `master` 现在只会执行前端 / 后端检查，不会自动部署到服务器
- 如果你要真正执行远程部署，需要在 GitHub Actions 页面手动触发 workflow，并把 `run_deploy` 选成 `true`

仓库 Actions 页面：

`Actions -> reminder-deploy`

如果 workflow 读取成功，日志里会看到类似提示：

```text
DEPLOY_HOST loaded from repository variable.
DEPLOY_USER loaded from repository variable.
DEPLOY_PORT loaded from repository variable.
```

这说明 GitHub Actions 已经拿到你配置的参数了。

---

## 六、常见错误

### 1. 名字写错

必须完全一致，例如：

- `DEPLOY_HOST`
- `DEPLOY_USER`

不能写成：

- `deploy_host`
- `Deploy_Host`

### 2. 把公钥填进了 DEPLOY_SSH_KEY

错误：

- `reminder_actions_v2.pub`

正确：

- `reminder_actions_v2`

### 3. 配到了别的地方

要配在：

`Settings -> Secrets and variables -> Actions`

不是：

- Codespaces secrets
- Environment secrets
- 其他仓库

### 4. DEPLOY_APP_DIR 写错

如果服务器上项目实际不在 `/opt/reminder`，部署时会找不到：

```text
bash: /opt/reminder/github-actions.deploy.sh: No such file or directory
```

这时把 `DEPLOY_APP_DIR` 改成真实路径即可。

---

## 七、推荐做法

推荐你最终只保留：

- Variables: `DEPLOY_HOST`、`DEPLOY_PORT`、`DEPLOY_USER`、`DEPLOY_APP_DIR`、`DEPLOY_BRANCH`、`DEPLOY_ENABLE_NGINX_SYNC`
- Secrets: `DEPLOY_SSH_KEY`

不建议长期保留：

- `DEPLOY_PASSWORD`

因为 SSH key 更适合自动化部署，也更安全。
