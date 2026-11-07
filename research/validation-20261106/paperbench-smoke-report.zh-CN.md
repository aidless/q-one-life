# PaperBench dev 容器冒烟报告

日期：2026-11-06。结论：**任务包与上游代码已准备好；容器启动阶段被
Docker Hub 拉取 `pb-env:latest` 阻断。没有 PaperBench 分数。**

## 已完成

1. 上游 `frontier-evals` 固定 revision：
   `b78dab1da774a6456b1ed9c48c9ff194ee3ff36d`
2. 上游代码 checkout 成功。
3. `uv` 环境安装成功，入口命令可运行。
4. dev split 的 3 篇论文必要文本已补齐：
   - `semantic-self-consistency`
   - `self-expansion`
   - `self-composing-policies`
5. `paper.md` / `addendum.md` 逐文件 SHA-256 与 Git LFS OID 校验一致。
6. DirectSubmission + dummy judge + code-only 配置通过参数校验。
7. 使用本地非空占位 `GRADER_OPENAI_API_KEY` 通过入口环境校验；
   dummy judge 不会发起付费模型调用。
8. 进程进入 Alcatraz 容器启动阶段，卡在 `_pull_image("pb-env:latest")`。

## 阻断

```
docker.errors.APIError:
500 Server Error for http+docker://localhost/v1.56/images/create?...fromImage=pb-env
failed to resolve reference "docker.io/library/pb-env:latest"
``+

原因：

1. 上游要求先构建本地镜像 `pb-env:latest`。
2. 当前本机没有 `pb-env:latest`。
3. 构建脚本从 `ubuntu:24.04` 开始。
4. Docker daemon 访问 `registry-1.docker.io` 超时。
5. 本机有 14 个正在运行的容器，不能重启 Docker daemon 配置代理。

## 不能声称

- 不能声称 PaperBench 已跑通。
- 不能声称 `pb-env` 已构建。
- 不能声称任何 PaperBench 分数。
- 不能声称 direct submission 链路已端到端完成。

## 最小恢复路径

1. 在一台可重启 Docker、且没有业务容器运行的机器上构建 `pb-env:latest`。
2. 导出 `pb-env:latest` 镜像 tarball，传回本机。
3. 在本机 `docker load` 后重跑 DirectSubmission + dummy judge。
4. 仍不产生真实 PaperBench 分数；它只是基础设施冒烟。

## 相关命令

```bash
cd /tmp/paperbench-upstream/project/paperbench

# 构建基础镜像
bash paperbench/scripts/build-docker-images.sh

# 基础设施冒烟（不是 benchmark 分数）
GRADER_OPENAI_API_KEY=<local-nonempty-placeholder> uv run \
  python -m paperbench.nano.entrypoint \
  paperbench.paper_split=dev \
  paperbench.solver=paperbench.solvers.direct_submission.solver:PBDirectSubmissionSolver \
  paperbench.solver.submissions_dir=/tmp/pb-submissions \
  paperbench.reproduction.skip_reproduction=true \
  paperbench.judge.code_only=true \
  paperbench.judge.scaffold=dummy \
  runner.recorder=nanoeval.json_recorder:json_recorder
```
