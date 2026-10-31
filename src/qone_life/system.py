"""带版本的个人模型，以及它与每日推荐流之间的连接。"""
import json
import threading
from datetime import datetime, timezone

from qone_core.life import AdaptiveKernel, ModelError, ScenarioKernel
from qone_core.life.model import fingerprint, instant, number
from qone_core.life.state import resource_key

from .outcomes import append_observations, append_outcome, canonical_observations, canonical_request
from .outcomes import preview as outcome_preview
from .repository import now


def kernel_for(model):
    """根据模型是否带 learning 段，构造自适应核或声明式场景核。"""
    if not isinstance(model, dict):
        raise ModelError('人生模型应为JSON对象')
    if model.get('learning') is not None:
        return AdaptiveKernel(model)
    return ScenarioKernel(model)


class SystemService:
    """负责人生模型的版本存取、评估、回放与结果录入。"""

    def __init__(self, repository, lock=None):
        self.repo = repository
        self.lock = lock or threading.RLock()
        self.cached = None

    def current(self):
        """读取最新一版人生模型（无版本时返回 None）。"""
        with self.repo.connect() as db:
            row = db.execute(
                'SELECT payload FROM system_revisions ORDER BY rowid DESC LIMIT 1'
            ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def save(self, model, parent_revision):
        """保存一版新模型（先做完整语义校验，且要求父版本与当前一致）。

        如果新模型与当前模型内容完全相同，则返回 unchanged；
        退回旧版本也仍会生成一条新的版本记录（保证版本链完整可审计）。
        """
        # 触碰持久化之前，先做完整的语义校验。
        kernel = kernel_for(model)
        row = {
            'id': kernel.model_sha256,
            'created_at': now(),
            'parent_revision': parent_revision,
            'model': kernel.model,
        }

        with self.lock, self.repo.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current_row = db.execute(
                'SELECT id,payload FROM system_revisions ORDER BY rowid DESC LIMIT 1'
            ).fetchone()
            current = current_row[0] if current_row else None

            # 并发保护：父版本必须仍是当前版本。
            if current != parent_revision:
                raise ModelError('人生模型已被更新，请先重新读取当前版本')

            # 内容未变化则直接返回，不新增版本。
            if current_row and fingerprint(json.loads(current_row[1])['model']) == kernel.model_sha256:
                return {'revision': current, 'model_sha256': kernel.model_sha256, 'unchanged': True}

            # 退回旧版本也必须生成新的版本事件。
            row['id'] = fingerprint({
                'model': kernel.model_sha256,
                'parent': parent_revision,
                'created_at': row['created_at'],
            })
            db.execute(
                'INSERT INTO system_revisions(id,payload) VALUES(?,?)',
                (row['id'], json.dumps(row, ensure_ascii=False, allow_nan=False)),
            )
            self.cached = None

        return {'revision': row['id'], 'model_sha256': kernel.model_sha256, 'unchanged': False}

    def kernel(self):
        """返回（当前模型行, 对应核对象）；无模型时返回 (None, None)。

        核对象按版本 id 缓存，版本变化时才重建。
        """
        row = self.current()
        if row is None:
            return None, None
        if self.cached is None or self.cached[0] != row['id']:
            self.cached = (row['id'], kernel_for(row['model']))
        return row, self.cached[1]

    def evaluate(self, as_of, *, available_minutes=480, excluded_action_ids=(), max_actions=3, horizon_days=None):
        """在给定时刻评估并比较可选行动组合。"""
        revision, kernel = self.kernel()
        if kernel is None:
            return None
        if not 0 <= number(available_minutes) <= 480:
            raise ModelError('当前可安排时间应为0到480分钟')

        tasks = self.repo.all('tasks')

        # 汇总所有任务已声明的资源承诺。
        commitments = []
        for t in tasks:
            commitments.extend(t.get('system_commitments', []))

        # 已完成且行动定义指纹一致的任务，计为"已完成行动"。
        completed = []
        for t in tasks:
            if not t.get('done'):
                continue
            action_id = t.get('system_action_id')
            if action_id not in kernel.index['actions']:
                continue
            if t.get('system_action_sha256') == fingerprint(kernel.index['actions'][action_id]):
                completed.append(action_id)

        kwargs = {'commitments': commitments, 'completed_action_ids': completed}
        if horizon_days is not None:
            kwargs['horizon_days'] = horizon_days
        elif isinstance(kernel, AdaptiveKernel):
            kwargs['horizon_days'] = kernel.horizon

        comparison = kernel.propose(
            as_of, max_actions=max_actions, excluded_action_ids=excluded_action_ids, **kwargs
        )

        # 每日可用时间是"在已声明的资源账户之外"的额外约束。任何行动都不会被缩短
        # 以让组合看起来可行，这里只把超预算的组合剔除掉。
        over = []
        for scenario in comparison['scenarios']:
            minutes = 0
            for a in scenario['action_ids']:
                minutes += kernel.index['actions'][a]['minutes']
            if minutes > available_minutes:
                over.append(scenario['action_ids'])
        if over:
            portfolios = []
            for s in comparison['scenarios']:
                if s['action_ids'] not in over:
                    portfolios.append(s['action_ids'])
            comparison = kernel.compare(portfolios, as_of, **kwargs)

        return {
            'revision': revision['id'],
            'mode': 'adaptive' if isinstance(kernel, AdaptiveKernel) else 'declared_scenario',
            'synthetic': bool(kernel.model.get('synthetic')),
            'goals': kernel.model['goals'],
            'goal_order': kernel.model['goal_order'],
            'dimensions': kernel.model['dimensions'],
            'episode_count': len(kernel.model.get('episodes', [])),
            'state': kernel.snapshot(as_of, commitments=commitments),
            'comparison': comparison,
            'daily_capacity_excluded_portfolios': over,
        }

    def replay(self, candidate_calibration=None):
        """回放历史，评估预测表现（可选隔离地试算一个候选校准参数）。"""
        _, kernel = self.kernel()
        if kernel is None or not isinstance(kernel, AdaptiveKernel):
            raise ModelError('当前模型尚未配置历史学习记录')

        if candidate_calibration is not None:
            # 候选校准是隔离的：不改动任何版本、任务或生产设置。
            kernel = AdaptiveKernel(
                kernel.model | {'learning': kernel.config | {'calibration': candidate_calibration}}
            )

        result = kernel.replay()
        result['used_for_recommendations'] = False
        if candidate_calibration is not None:
            result['purpose'] = 'shadow_interval_evaluation'
        else:
            result['purpose'] = 'historical_prediction_review'
        return result

    def record_observations(self, raw):
        """登记一批数量观察（幂等：同 event_id 重复提交不覆盖）。"""
        request = canonical_observations(raw)
        with self.lock:
            revision, kernel = self.kernel()
            if not isinstance(kernel, AdaptiveKernel):
                raise ModelError('当前人生模型尚未定义历史学习测量')

            # 幂等检查：同一 event_id 若已登记，内容不同就拒绝，相同则原样返回。
            existing = []
            for o in kernel.model['observations']:
                if o.get('intake_event_id') == request['event_id']:
                    existing.append(o)
            if existing:
                digest = fingerprint({k: v for k, v in request.items() if k != 'parent_revision'})
                for o in existing:
                    if o.get('intake_request_sha256') != digest:
                        raise ModelError('这个登记ID已用于不同观察，不能覆盖已有记录')
                return {
                    'revision': revision['id'],
                    'unchanged': True,
                    'recorded_at': existing[0]['recorded_at'],
                }

            if revision['id'] != request['parent_revision']:
                raise ModelError('人生模型已被更新，请重新读取；本次观察尚未保存')

            received = datetime.now(timezone.utc).isoformat()
            result = self.save(append_observations(kernel, request, received), request['parent_revision'])
            return result | {
                'recorded_at': received,
                'evidence_status': 'user_report_not_independently_verified',
            }

    def preview_outcome(self, raw):
        """预览一次结果登记（不写入）。"""
        if not isinstance(raw, dict) or set(raw) != {'action_ids', 'observed_at'}:
            raise ModelError('需要行动选择与实际结果测量时刻')
        with self.lock:
            revision, kernel = self.kernel()
            if kernel is None:
                raise ModelError('请先导入并声明人生模型')
            result = outcome_preview(
                kernel, raw['action_ids'], raw['observed_at'], datetime.now(timezone.utc).isoformat()
            )
            return result | {
                'revision': revision['id'],
                'synthetic': bool(kernel.model.get('synthetic')),
            }

    def record_outcome(self, raw):
        """登记一次结果（幂等：同 event_id 重复提交不覆盖）。"""
        request = canonical_request(raw)
        with self.lock:
            revision, kernel = self.kernel()
            if not isinstance(kernel, AdaptiveKernel):
                raise ModelError('当前人生模型尚未定义历史学习与结果窗口')

            eid = 'outcome:' + request['event_id']
            existing = None
            for e in kernel.episodes:
                if e['id'] == eid:
                    existing = e
                    break
            if existing is not None:
                expected = fingerprint({k: v for k, v in request.items() if k != 'parent_revision'})
                if existing.get('intake_request_sha256') != expected:
                    raise ModelError('这个登记ID已用于不同结果，不能覆盖或重复写入')
                return {
                    'revision': revision['id'],
                    'episode_id': eid,
                    'unchanged': True,
                    'recorded_at': existing['recorded_at'],
                }

            if revision['id'] != request['parent_revision']:
                raise ModelError('人生模型已被更新，请重新预览；本次结果尚未保存')

            received = datetime.now(timezone.utc).isoformat()
            model, eid = append_outcome(kernel, request, received)
            result = self.save(model, request['parent_revision'])
            return result | {
                'episode_id': eid,
                'recorded_at': received,
                'evidence_status': 'user_report_not_independently_verified',
            }

    def planning_snapshot(self, *, today, available_minutes):
        """生成当日规划快照：在两次轮询间保持稳定，但不隐藏刚收到的证据。"""
        # 以"分钟起点"作为时间锚，避免每次轮询结果都变；同时把接收时刻不晚于当前
        # 的观察/结果纳入，保证刚录入的证据不会被分钟边界挡在外面。
        clock = datetime.now(timezone.utc)
        epoch = clock.replace(second=0, microsecond=0)

        revision, kernel = self.kernel()
        if kernel is None:
            return None

        received = []
        for row in kernel.model['observations'] + kernel.model.get('episodes', []):
            stamp = instant(row['recorded_at'])
            if stamp <= clock:
                received.append(stamp)
        at = max([epoch] + received).isoformat()

        tasks = self.repo.all('tasks')
        excluded = set()
        for t in tasks:
            if t.get('system_action_id') and t.get('focus_date') == today:
                excluded.add(t['system_action_id'])
        for row in self.repo.all('suggestions'):
            if (
                row.get('system_revision') == revision['id']
                and row.get('feedback_date') == today
                and row.get('status') in {'accepted', 'dismissed'}
            ):
                excluded.add(row.get('system_action_id'))

        evaluation = self.evaluate(at, available_minutes=available_minutes, excluded_action_ids=excluded)

        result = evaluation['comparison']
        selected = None
        for r in result['scenarios']:
            if r['id'] == result['preferred_id']:
                selected = r
                break

        candidates = []
        action_ids = selected['action_ids'] if selected else []
        for aid in action_ids:
            a = kernel.index['actions'][aid]

            # 把行动的成本换算成资源承诺（区间成本取上限）。
            commitments = []
            for c in a.get('costs', []):
                amount = c['amount']
                # 区间成本取上限。
                if isinstance(amount, dict):
                    amount = amount['upper']
                commitments.append({
                    'resource_key': resource_key(kernel.index['resources'][c['resource_id']]),
                    'amount': amount,
                })

            # 计算该行动涉及的维度名称（供展示），找不到则归为"跨维度"。
            dimension_name = '跨维度'
            for g in kernel.model['goals']:
                if g['id'] in a.get('goal_ids', []):
                    dimension_name = kernel.index['dimensions'][g['dimension_id']]['name']
                    break

            prefix = ''
            if evaluation['synthetic']:
                prefix = '合成示例。'
            basis = '显式影响假设'
            if evaluation['mode'] == 'adaptive':
                basis = '历史观察预测'

            candidates.append({
                'id': 'system:' + aid,
                'record_id': 'PS-' + fingerprint({'action': aid, 'revision': revision['id']})[:24],
                'kind': 'system',
                'title': a['title'],
                'reason': prefix + '根据已声明的目标取舍、完整资源消耗和' + basis + '比较方案；预测仍需后续核验。',
                'first_step': a['first_step'],
                'done_when': a['done_when'],
                'minutes': a['minutes'],
                'domain': 'other',
                'goal_id': None,
                'task_id': None,
                'revision': fingerprint(a),
                'system_revision': revision['id'],
                'system_action_id': aid,
                'system_action_sha256': fingerprint(a),
                'system_commitments': commitments,
                'system_scenario': selected['id'],
                'system_mode': evaluation['mode'],
                'system_goal_ids': a.get('goal_ids', []),
                'system_dimension_name': dimension_name,
                'system_forecast': selected.get('forecast'),
                'system_costs': selected['costs'],
            })

        return {
            'date': today,
            'available_minutes': available_minutes,
            'goals': kernel.model['goals'],
            'candidates': candidates,
            'evidence': [],
            'limits': {
                'goals_total': len(kernel.model['goals']),
                'goals_included': len(kernel.model['goals']),
            },
            'system': evaluation,
        }


def validate_revision_history(rows):
    """从最新到最旧校验版本链：父版本衔接、内容指纹一致。"""
    parent = None
    for row in reversed(rows):  # 仓库按最新在前导出。
        if row.get('parent_revision') != parent:
            raise ModelError('人生模型版本链不完整')
        kernel = kernel_for(row['model'])
        expected = fingerprint({
            'model': kernel.model_sha256,
            'parent': parent,
            'created_at': row['created_at'],
        })
        if row['id'] != expected:
            raise ModelError('人生模型版本内容校验失败')
        parent = row['id']
