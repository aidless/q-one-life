"""带类型的本地结果录入。一次任务点击或一条模型意见都不能当作结果标签。"""
import re
from copy import deepcopy
from datetime import timedelta

from qone_core.life import AdaptiveKernel, ModelError
from qone_core.life.model import fingerprint, instant, number


def preview(kernel, action_ids, observed_at, received_at):
    """在真正写入前，预览一次结果登记是否可接受。

    逐一检查每个必需测量的窗口起点状态：缺失/过期/冲突、事后被更正、
    预测器需要精确数量而只有区间等，都会记成 issue。有任何 issue 即视为不合格。
    返回预览结果（含事前基线、行动定义指纹等），供后续登记核对。
    """
    if not isinstance(kernel, AdaptiveKernel):
        raise ModelError('当前人生模型尚未定义历史学习与结果窗口')

    actions = kernel._actions(action_ids)
    end, received = instant(observed_at), instant(received_at)
    if end > received:
        raise ModelError('结果测量时刻不能在未来')

    start = end - timedelta(days=kernel.horizon)
    state = kernel.snapshot(start.isoformat())

    # 必需测量：特征与目标里出现过的测量 ID（去重、保序）。
    required = []
    for item in kernel.features + kernel.targets:
        if item['measure_id'] not in required:
            required.append(item['measure_id'])

    # 在接收时刻之前已被更正的事前观察，不能再作为学习证据。
    superseded = set()
    for o in kernel.model['observations']:
        if o.get('supersedes') and instant(o['recorded_at']) <= received:
            superseded.add(o['supersedes'])

    before, baselines, issues = {}, [], []
    for mid in required:
        row = state['measures'][mid]
        if row['status'] != 'known':
            issues.append(f"{row['name']}：窗口开始时的观察缺失、过期或冲突")
            continue
        refs = sorted(row['observation_ids'])
        if any(oid in superseded for oid in refs):
            issues.append(f"{row['name']}：事前观察后来被更正，不能作为当前学习证据")
            continue
        observation = kernel.index['observations'][refs[0]]
        try:
            value = kernel._point(observation['value'])
        except ModelError:
            issues.append(f"{row['name']}：当前预测器需要精确数量观察，不能取区间中点")
            continue
        before[mid] = observation['id']
        baselines.append({
            'measure_id': mid,
            'observation_id': observation['id'],
            'name': row['name'],
            'value': value,
            'unit': row['unit'],
            'observed_at': observation['observed_at'],
            'source': observation['source'],
        })

    # 结果窗口不能与已有学习记录重叠，避免重复登记同一段时间。
    for e in kernel.episodes:
        if start < instant(e['ended_at']) and end > instant(e['started_at']):
            issues.append('这个结果窗口与已有学习记录重叠，请核对时刻；不要重复登记同一段结果')
            break

    return {
        'eligible': not issues,
        'issues': issues,
        'started_at': start.isoformat(),
        'observed_at': end.isoformat(),
        'horizon_days': kernel.horizon,
        'before': before,
        'baselines': baselines,
        'action_ids': actions,
        'actions': [deepcopy(kernel.index['actions'][aid]) for aid in actions],
        'resources': [deepcopy(r) for r in kernel.index['resources'].values()],
        'action_definition_sha256': fingerprint([kernel.index['actions'][aid] for aid in actions]),
        'targets': [dict(kernel.index['measures'][d['measure_id']]) for d in kernel.targets],
        'source_kind': 'user_report',
        'independently_verified': False,
    }


def canonical_request(raw):
    """校验并规范化一次结果登记请求（字段、ID、确认标志、来源等）。"""
    fields = {'event_id', 'parent_revision', 'action_ids', 'observed_at', 'before',
              'outcomes', 'source', 'execution_confirmed', 'action_definition_sha256'}
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ModelError('结果登记字段不完整或包含不支持的字段；登记时间由服务端记录')
    if not isinstance(raw['event_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', raw['event_id']):
        raise ModelError('登记ID需要1到48位字母、数字、下划线或短横线')
    if raw['execution_confirmed'] is not True:
        raise ModelError('请先确认实际执行的行动、完整投入与未执行的行动；部分执行不能当作完整执行')
    if not isinstance(raw['source'], str) or not raw['source'].strip() or len(raw['source']) > 1000:
        raise ModelError('请说明结果来源，最多1000字')
    if not isinstance(raw['before'], dict) or not isinstance(raw['outcomes'], dict):
        raise ModelError('事前观察与结果需为按测量ID关联的对象')
    if not isinstance(raw['action_ids'], list):
        raise ModelError('行动ID需为文本列表')
    for a in raw['action_ids']:
        if not isinstance(a, str):
            raise ModelError('行动ID需为文本列表')
    if len(raw['action_ids']) != len(set(raw['action_ids'])):
        raise ModelError('行动ID不能重复')

    # 只做安全的可重试规范化（时区、数值表示），不改动实际取值。
    return {
        **raw,
        'action_ids': sorted(raw['action_ids']),
        'source': raw['source'].strip(),
        'observed_at': instant(raw['observed_at']).isoformat(),
        'outcomes': {mid: float(number(value)) for mid, value in raw['outcomes'].items()},
    }


def append_outcome(kernel, request, received_at):
    """把一次合格的结果登记追加到模型，并返回（新模型, episode_id）。"""
    receipt = preview(kernel, request['action_ids'], request['observed_at'], received_at)
    if not receipt['eligible']:
        raise ModelError('；'.join(receipt['issues']))
    if request['before'] != receipt['before']:
        raise ModelError('事前观察已变化或未按预览确认，请重新检查结果窗口')
    if request['action_definition_sha256'] != receipt['action_definition_sha256']:
        raise ModelError('行动定义或投入已变化，请重新核对实际执行版本')

    targets = {d['measure_id'] for d in kernel.targets}
    if set(request['outcomes']) != targets:
        raise ModelError('必须按原单位填写全部结果测量，不能用完成勾选或主观评分替代')

    model = deepcopy(kernel.model)
    eid = 'outcome:' + request['event_id']

    # 为每个结果测量生成一条事后观察。
    after = {}
    for mid, value in request['outcomes'].items():
        oid = eid + ':' + fingerprint(mid)[:16]
        after[mid] = oid
        model['observations'].append({
            'id': oid,
            'measure_id': mid,
            'value': value,
            'observed_at': receipt['observed_at'],
            'recorded_at': instant(received_at).isoformat(),
            'source_kind': 'user_report',
            'source': request['source'],
        })

    # 记录这次学习 episode（含事前/事后、请求指纹，便于幂等与审计）。
    request_hash = fingerprint({k: v for k, v in request.items() if k != 'parent_revision'})
    model.setdefault('episodes', []).append({
        'id': eid,
        'started_at': receipt['started_at'],
        'ended_at': receipt['observed_at'],
        'recorded_at': instant(received_at).isoformat(),
        'action_ids': receipt['action_ids'],
        'before': receipt['before'],
        'after': after,
        'source': request['source'],
        'action_definition_sha256': receipt['action_definition_sha256'],
        'execution_confirmed': True,
        'intake_request_sha256': request_hash,
        'intake_parent_revision': request['parent_revision'],
    })

    # 用 AdaptiveKernel 再整体校验一次（含域、量纲、单位、ID 冲突、容量与 episode 完整性）。
    validated = AdaptiveKernel(model)
    return validated.model, eid


def canonical_observations(raw):
    """校验并规范化一次"数量观察"登记请求。"""
    fields = {'event_id', 'parent_revision', 'observed_at', 'values', 'source'}
    if not isinstance(raw, dict) or set(raw) != fields or not isinstance(raw['values'], dict) or not raw['values']:
        raise ModelError('需要登记ID、当前版本、实际观察时刻、数量观察与来源；登记时间由服务端记录')
    if not isinstance(raw['event_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', raw['event_id']):
        raise ModelError('登记ID需要1到48位字母、数字、下划线或短横线')
    if not isinstance(raw['source'], str) or not raw['source'].strip() or len(raw['source']) > 1000:
        raise ModelError('请说明观察来源，最多1000字')
    return {
        **raw,
        'observed_at': instant(raw['observed_at']).isoformat(),
        'source': raw['source'].strip(),
        'values': {mid: float(number(value)) for mid, value in raw['values'].items()},
    }


def append_observations(kernel, request, received_at):
    """把一次数量观察登记追加到模型，返回新模型。"""
    if not isinstance(kernel, AdaptiveKernel):
        raise ModelError('当前人生模型尚未定义历史学习测量')
    if instant(request['observed_at']) > instant(received_at):
        raise ModelError('实际观察时刻不能在未来')

    allowed = {d['measure_id'] for d in kernel.features + kernel.targets}
    if not set(request['values']) <= allowed:
        raise ModelError('这里只登记已定义的学习数量观察；类别与原话不能转换成分数')

    model = deepcopy(kernel.model)
    digest = fingerprint({k: v for k, v in request.items() if k != 'parent_revision'})
    for mid, value in request['values'].items():
        model['observations'].append({
            'id': 'observation:' + request['event_id'] + ':' + fingerprint(mid)[:16],
            'measure_id': mid,
            'value': value,
            'observed_at': request['observed_at'],
            'recorded_at': instant(received_at).isoformat(),
            'source_kind': 'user_report',
            'source': request['source'],
            'intake_event_id': request['event_id'],
            'intake_request_sha256': digest,
        })
    return AdaptiveKernel(model).model
