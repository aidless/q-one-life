# 来源纠正与独立验证

本目录保留新的补充证据，不覆盖旧报告、旧回执、预注册或 closure。
`correction.json` 是本次纠正的入口，绑定旧 cloud A3 回执、closure
读取器及其输出的 SHA-256。

纠正后的证据口径为：

> numerical results recorded but repository provenance unverified
>
> closure field checks not fresh reruns

旧 cloud A3 回执记载了数值结果；旧报告承认给不含 Git 历史的目录建立 ref 桩。
仅有 `rev-parse HEAD` 的文本不证明 commit 对象存在，也不证明远端来源。
旧 closure 读取已有回执并比较字段，不能充当一次新的实验执行。
本次没有访问远端，没有重跑 cloud A3 或模型，也没有追认旧执行环境。

## 本次补充证据

- `native-git-manifest.json` / `native-git-audit.json`：只读核验本机原 native
  中钉住的真实 commit 对象、对象摘要和 tree 对象，并校验九个清单文件。
  对象存在不等于仓库远端身份认证，也不等于整个工作树与 commit 一致。
- `native-file-commit-binding.json`：独立逐文件读取钉住 commit 的 blob，
  记录其 SHA-256 与预注册哈希、此次快照是否相等。这是本机当前补证，
  不能证明历史 cloud 目录的对象存在。
- `native-files/` / `native-files-manifest.json` / `native-files-audit.json`：
  仅包含预注册的九个源码和证据文件，采用显式 `hash_pinned_archive` 模式，
  不含 `.git`、其他工作文件或 Git 配置。使用文件哈希快照避免携带整个
  native 历史及无关内容；本目录没有生成 Git bundle。
- `alias-root-rejection.json`：工作目录别名本身为符号链接，按审计规则拒绝；
  快照通过记录使用真实物理路径。
- `regression.json`：本次短回归命令、退出码、输出和测试代码的 SHA-256。
- `SHA256SUMS.txt`：此目录交付文件的哈希清单，不包含其自身。

## 独立 CLI

从 `/home/liuzewen/qone-life-work` 运行（`python3` 需为 Python 3.10+）：

```bash
python3 -I -B src/qone_life/research_factory/provenance_audit.py \
  --root research/validation-20261106/provenance/native-files \
  --manifest research/validation-20261106/provenance/native-files-manifest.json \
  --manifest-sha256 '<correction.json 中的 archive_manifest_canonical_sha256>'
```

该工作目录是符号链接。上例从工作目录使用相对路径，进程会以物理目录
解析审计根。API 调用方应传可信的物理目录；不要对不可信的清单文件路径
先调用 `resolve()` 来消除符号链接检查。

`--manifest-sha256` 接受规范 JSON 的摘要，不是格式化 JSON 文件的字节摘要。
格式为 UTF-8、`sort_keys=True`、`ensure_ascii=False`、
`separators=(",", ":")`、`allow_nan=False`。
从可信渠道固定该摘要；同时替换文件和未固定的 manifest 不属于哈希验证
能识别的情况。CLI 标准输出 JSON，成功退出 0，失败退出 1。
可用 `--output` 新建报告，已有文件会被拒绝覆盖。

原 native 的对象存在核验：

```bash
python3 -I -B src/qone_life/research_factory/provenance_audit.py \
  --root '/home/liuzewen/F:\deepseek' \
  --manifest research/validation-20261106/provenance/native-git-manifest.json
```

## 未来 runner API

```python
from qone_life.research_factory.provenance_audit import require_provenance

evidence = require_provenance(
    external_root,
    manifest,
    expected_manifest_sha256=trusted_manifest_digest,
)
```

调用失败抛 `ProvenanceError`，其 `.report` 保留失败证据。调用方应在执行
实验前放置此门，并把返回证据绑定到新回执；本次没有修改旧 runner。
需要真实 Git 身份契约时必须使用 `git_commit`，不能把 archive 的
`passed` 解读为 Git 来源通过。无 Git 元数据的来源必须明确选用
`hash_pinned_archive`；有 ref 桩的目录不能冒充 archive。
仅验证清单内文件，未列出的依赖、历史云端目录和实验正确性均未核验。

archive 文件读取逐层使用 `O_NOFOLLOW`，拒绝根目录或路径分量的符号链接、
绝对路径、`..`、非规范路径、重复路径及非常规文件。
Git 核验不接受缩写/ref，禁用替换对象、环境注入对象目录和自动网络取回；
不创建分支、提交或修改已有 Git 配置。

## 短回归

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_provenance_audit.py
```

测试使用临时目录和最小合法的压缩 Git 对象夹具，不调用提交或建分支命令，
不接触现有仓库历史。覆盖假 HEAD、真实对象、blob 冒充、外层仓库继承、
Git 环境重定向/替换对象、文件哈希不符、缺失、逃逸、符号链接、
FIFO、空清单和 CLI 退出码/禁止覆盖。
