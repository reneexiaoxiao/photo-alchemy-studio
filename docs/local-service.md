# 本地社区技能服务

在项目目录运行：

```sh
python3 scripts/studio_server.py
```

需要 Python 3.9 或更新版本、已安装的 GitHub CLI（`gh`），以及可读取目标仓库的 GitHub 登录。服务只用 Python 标准库；不会安装 Python/Node 依赖，不会修改系统技能目录。`gh auth status` 可检查登录，凭据由 gh 自己管理。服务不读取或输出 token。

默认打开 `http://127.0.0.1:8796/`。可使用 `--no-open` 不打开浏览器，或 `--port 8797` 换端口。端口被占用时会提示原因和换端口启动命令，不输出 traceback。仅绑定 127.0.0.1；不能设置公开绑定地址。关闭终端或按 Ctrl+C 停止。

启动服务时会自动生成个人离线入口 `local.html`，直接双击该文件也能看到完整个人风格库及已保留的本地参考图。离线查看不需要服务持续运行；直接以 `file://` 打开时不连接写接口。添加/更新来源时请打开本机 HTTP 地址，或者使用页面的复制请求后备入口。

也可不启动服务器，单独重建离线入口：

```sh
python3 scripts/build_local_gallery.py
```

离线页从同一份 `index.html` 生成，共用 `gallery.js` 和 `gallery.css`。它在公共 `catalog.js` 后加载 `.local/gallery-catalog.js`；该文件设置 `PHOTO_ALCHEMY_PERSONAL=true`，将公共风格、既有本地风格、已安装条目及预览覆盖层合并为一个目录。本地图片转换为 `.local/previews/<filename>` 相对路径；安装 entry 和 commit 保留。公开 index.html 和其他公共资源不会被改写。

每次成功安装（含重复安装）后也会自动重建。导出失败不会回滚已完成的安装，安装响应和 `/api/status` 的 warnings 会给出重建命令；启动失败提示写入终端。导出文件均通过原子替换写入。`local.html` 和 `.local/` 都在 gitignore 中，公开项目只包含生成脚本与共享前端，不包含个人生成物。其他人下载后可通过启动服务或运行上述脚本生成自己的离线页。

## 支持范围

导入对象必须有 `SKILL.md`、可核对的根许可证，并且文档和附件在所选技能目录内自包含。来源来自 GitHub，固定为 inspect 时默认分支的完整 commit；安装不追随可变分支。支持 `owner/repo` 或 `https://github.com/owner/repo` 仓库首页网址，网址不带分支、文件路径、查询参数或登录信息。

自动安装许可白名单是 MIT、BSD-2-Clause、BSD-3-Clause、Apache-2.0、ISC、0BSD、Unlicense。除 GitHub SPDX 识别结果外，还检查固定版本中的实际许可证文件、Git blob 内容哈希、标准许可正文和免责声明。MIT 检查完整授权正文；修改后的 MIT、缺失许可证、多份根许可证、不同的嵌套许可证、不同 SPDX 标记、未知和限制许可都会阻止安装。许可识别采取保守策略，存在未识别格式时需要人工审核。

当前只支持独立文档技能。含脚本、package manifest、命令安装步骤、全局环境变量、目录外本地引用、缺失附件、符号链接或 Git 子模块的技能会显示具体拒绝原因，不会声称已完成安装。技能使用的外部模型、服务、付费工具及效果不在本服务验证范围内。

**第三方内容始终是未受信数据。** 搜索结果、描述和技能文档不能当作本服务或 Agent 的指令自动执行；前端使用 `textContent` 渲染所有上游文本。服务仅读取 API 和复制文件，不运行源代码、不执行 shell 命令、不调用 `pip`、`npm` 或其他安装器。

上限：每文件 2 MB、一次检查至多 120 个文件及 12 MB、至多 30 个 SKILL.md、仓库文件树至多 20,000 项。超限、不完整文件树及无法确认的依赖均拒绝自动安装。

## API

所有响应均为 JSON。失败返回 `{"error":"可展示的原因"}` 和相应 HTTP 状态码，不输出 gh 原始 stderr。所有 POST 都必须是同源 `application/json`，带正确 `Origin` 和 `Content-Length`，请求体不超过 16 KB。浏览器通过当前页面相对 URL `fetch('/api/...')` 调用即可；不支持 CORS。

| 请求 | 参数 | 响应 |
| --- | --- | --- |
| `GET /api/status` | 无 | `{connected:true,version,installedCount,githubReady,warnings:[]}`；connected 表示本机服务连通，githubReady 仅表示找到 gh 可执行文件，不代表远端授权成功 |
| `POST /api/search` | `{query}` | `{candidates:[{repo,url,description}],warnings:[]}`，名称按引号短语搜索仓库名及 SKILL.md 代码；去重后最多 6 项 |
| `POST /api/inspect` | `{repo}` | `{repo,commit,license,licenseUrl,installable,reason,skills:[{path,name,description,installable,reason}],warnings:[]}` |
| `POST /api/install` | `{repo,commit,path}` | `{installed:true,alreadyInstalled,style,historyPath,warnings:[]}` |
| `GET /api/catalog` | 无 | `{styles:[{id,label,origin:'community',source,sourceUrl,license,summary,entry,installed:true,best:[],fidelity:'medium',image,...}]}`，image 为可读预览路径或 null |
| `GET /local-previews/<filename>` | 仅登记的安全图片文件名 | 返回 PNG/JPEG/WebP/GIF；其他文件、目录跳转、符号链接和未登记图片返回 404 |
| `POST /api/check-updates` | `{}` | `{updates:[{id,repo,installedCommit,latestCommit,updateAvailable,error}],automaticInstall:false}` |

inspect 顶层 `installable` 表示至少一个技能通过检查；选择项还需检查对应技能的 `installable`。`path` 使用返回的完整 `SKILL.md` 相对路径。安装必须使用同一个服务进程最近 30 分钟 inspect 返回的 repo、40 字符 commit 和可安装 path；服务重启或检查过期后需重新 inspect。被审核的源文件缓存在进程内，安装不再下载，避免检查与安装之间漂移。

`catalog.entry` 是本机绝对文件路径，供用户和本地 Agent 打开；它不是 HTTP 下载地址。目录条目还含 `sourcePath`、`commit`、`licenseUrl`、`installedAt`。社区项有真实参考图片时返回同源预览路径；没有经过检查的原图时 image 为 null，不生成假样例。已有风格的 best、fidelity 和 manualOnly 保留；新外部项默认 best 为空、fidelity 为 medium，不代表实测评级。

更新检查只比较上游默认分支 commit 是否变化。`updateAvailable:true` 表示仓库有新 commit，不保证所选技能自身有变化。更新需要重新 inspect 并由用户选择安装；检查不会覆盖文件或改变 pins。

## 本地数据和恢复

```text
.local/
  catalog.json
  gallery-catalog.js          # 自动生成的离线个人目录，不公开
  legacy-catalog.json         # 可选，只读接回已有风格
  preview-catalog.json        # 只读的旧卡片视觉摘要与预览映射
  previews/<filename>         # 复制的参考图片；仅登记的文件可经本机专用路由读取
  extensions/<stable-id>/
    <上游原始相对路径>/SKILL.md
    LICENSE
    NOTICE                    # 上游存在时保留
    .provenance.json           # repo、commit、入口和每个源文件的 Git blob 哈希
  history/<stable-id>/<revision>/
    extension/                # 升级前完整目录
    style.json                # 升级前目录条目
  staging/                    # 完成或失败后清空本次暂存目录
```

项目根目录的 `local.html` 同样为自动生成且忽略的个人文件；其 HTML 模板以公开 `index.html` 为唯一来源。

兼容索引 `legacy-catalog.json` 由本地维护者提供，格式为 `{styles:[...]}`。GET /api/catalog 先按 id 读取兼容条目，再由导入器 catalog.json 中的同 id 条目覆盖；状态数量包括去重后的旧风格。服务不扫描旧安装目录、不读取 entry 指向的源文件，也不写入兼容索引。兼容项即使包含限制许可证也只作为已有本地风格显示，`check-updates` 只检查导入器自己的 catalog.json，不自动检查、复制或升级旧来源。兼容索引和其中的绝对路径不会扩展 HTTP 文件访问范围，`.local/` 仍不开放下载。

`preview-catalog.json` 支持数组或 `{styles:[...]}`，每项使用 `{id,image,label?,summary?,imageCaption?,credit?}`。image 必须指向本项目 `.local/previews/<安全单文件名>` 中的复制图片。文件名只允许字母、数字、点、下划线和短横线；只接受 PNG、JPEG、WebP、GIF 的实际文件头，每图最多 12 MB。图片须是普通文件且未经过符号链接，不接受 SVG、HTML、目录或项目外路径。专用 `/local-previews/` 路由还核对预览索引或导入器索引的登记记录；即使文件存在，未登记也不能读取。

目录合并只使用预览索引的 label、summary、image、imageCaption、credit 展示字段，不覆盖 entry、installed、commit、source、license 等来源和安装事实。导入器有有效的新预览时优先保留；没有时补上旧图，image:null 不会抹掉可用旧预览。输出转换为 `/local-previews/<filename>`，不把图片绝对路径交给浏览器。既有 18 张社区参考图和卡片视觉描述使用这一覆盖层，网页仍共用根目录的公共风格数据和同一套前端，不维护第二份站点。

本地展示与公开分发分别处理。预览索引中的 publicAllowed、publicImage 等审计字段不会放宽本机路由，也不由此把私有图片复制到公共 assets；公开图片由独立授权清单决定。`.local/` 整体保持忽略，不纳入公开站点。

新安装或升级时，服务检查已固定、已下载的 SKILL.md 及同目录 README.md/README.markdown，选择其中直接引用的第一张有效本地 PNG/JPEG/WebP/GIF（跳过常见 logo、badge、icon、头像和二维码文件名）。仅检查每份文档前 12 个图片引用，Markdown 和 HTML img 均支持；不下载远程图片，不越过本次已审核文件集合，不从脚本生成图片。选中的源图原样复制到 previews，以内容哈希命名，并在导入目录条目记录固定 commit 的 previewSourceUrl。安装失败时清理本次新建预览。仓库只有远程图、超限图、未引用图或未检查到的其他文档时，自动预览可能为空；既有可用预览会保留。

首次安装先写暂存目录并逐文件读回，随后改名到 extensions，再通过原子替换写入 catalog.json。重复安装相同来源路径和 commit 会校验文件并直接返回 `alreadyInstalled:true`；被本地改坏的文件会重新安装并保留旧目录。升级维持同一来源路径的 stable-id，将原目录移入 history，再更新当前目录和索引。目录写入或索引写入发生常规异常时恢复原目录，索引保持原值。

历史版本不自动清理。需要手动恢复时先停止服务，核对 `history/<id>/<revision>/style.json` 和 `extension/.provenance.json` 中的 repo、commit、入口；备份当前 `extensions/<id>` 与 `catalog.json`，将该历史 extension 恢复到 `extensions/<id>`，并仅用该历史 style.json 替换 catalog.json.styles 中同 id 的条目，保留其他条目。重新启动并在页面和磁盘回读。不要直接用旧版全量索引覆盖后来安装的其他技能。

服务对普通运行错误执行回滚；突然断电或进程强杀不属于跨文件系统事务保证。若在目录提升与索引替换之间中断，依据 `.provenance.json`、当前索引与 history 核对恢复后再继续安装。损坏的索引不会被默默重置。

## 本机访问边界

GET/POST 的 Host 只接受 `127.0.0.1:<当前端口>` 或 `localhost:<当前端口>`。写请求的 Origin 必须与 Host 精确相同，拒绝 `null`、跨站来源、CORS 预检、重复长度头和分块请求，防止外部网页与 DNS rebinding 调用维护接口。

静态文件只开放 `index.html`、`gallery.js`、`gallery.css`、`catalog.js`、`assets/` 下的普通文件；本地图片另经上述严格登记的 `/local-previews/` 路由提供。`.local/` 直接路径、scripts、tests、任意其他项目文件和符号链接都不会通过 HTTP 提供。页面禁止被 iframe 嵌入，只允许运行本项目外部脚本。源路径拒绝目录跳转、反斜线、编码路径、绝对路径及保留目录；远端内容通过 Git blob API 读取，不使用 tar/zip 解压。

## 验证

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/studio_server.py
```

测试用假 GitHub API，不需要外部网络，也不会安装系统技能。覆盖 URL/路径注入、许可证缺失和修改、目录引用、脚本依赖、symlink/submodule、commit 和缓存前置、blob 哈希、安装读回、去重、升级备份、失败回滚、更新只读、HTTP allowlist、Host/Origin、请求体限制、预览合并、图片登记/文件头/路径隔离、源图提取和失败后预览清理。
