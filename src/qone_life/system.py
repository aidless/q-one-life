"""Versioned personal models and their connection to the daily recommendation feed."""
from datetime import datetime, timezone
import json
import threading

from qone_core.life import AdaptiveKernel, ScenarioKernel, ModelError
from qone_core.life.model import fingerprint, number
from qone_core.life.state import resource_key
from .repository import now


def kernel_for(model):
    if not isinstance(model,dict): raise ModelError('人生模型应为JSON对象')
    return AdaptiveKernel(model) if model.get('learning') is not None else ScenarioKernel(model)


class SystemService:
    def __init__(self, repository, lock=None):
        self.repo=repository; self.lock=lock or threading.RLock(); self.cached=None

    def current(self):
        with self.repo.connect() as db:
            row=db.execute('SELECT payload FROM system_revisions ORDER BY rowid DESC LIMIT 1').fetchone()
        return json.loads(row[0]) if row else None

    def save(self, model, parent_revision):
        kernel=kernel_for(model)  # Full semantic validation before touching persistence.
        row={'id':kernel.model_sha256,'created_at':now(),'parent_revision':parent_revision,'model':kernel.model}
        with self.lock, self.repo.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current_row=db.execute('SELECT id,payload FROM system_revisions ORDER BY rowid DESC LIMIT 1').fetchone()
            current=current_row[0] if current_row else None
            if current!=parent_revision:
                raise ModelError('人生模型已被更新，请先重新读取当前版本')
            if current_row and fingerprint(json.loads(current_row[1])['model'])==kernel.model_sha256:
                return {'revision':current,'model_sha256':kernel.model_sha256,'unchanged':True}
            # Reverting to a previous version must still create a new revision event.
            row['id']=fingerprint({'model':kernel.model_sha256,'parent':parent_revision,'created_at':row['created_at']})
            db.execute('INSERT INTO system_revisions(id,payload) VALUES(?,?)',(row['id'],json.dumps(row,ensure_ascii=False,allow_nan=False)))
            self.cached=None
        return {'revision':row['id'],'model_sha256':kernel.model_sha256,'unchanged':False}

    def kernel(self):
        row=self.current()
        if row is None: return None,None
        if self.cached is None or self.cached[0]!=row['id']:
            self.cached=(row['id'],kernel_for(row['model']))
        return row,self.cached[1]

    def evaluate(self, as_of, *, available_minutes=480, excluded_action_ids=(), max_actions=3, horizon_days=None):
        revision,kernel=self.kernel()
        if kernel is None: return None
        if not 0 <= number(available_minutes) <= 480:
            raise ModelError('当前可安排时间应为0到480分钟')
        tasks=self.repo.all('tasks')
        commitments=[c for t in tasks for c in t.get('system_commitments',[])]
        completed=[t['system_action_id'] for t in tasks if t.get('done') and t.get('system_action_id') in kernel.index['actions']
                   and t.get('system_action_sha256')==fingerprint(kernel.index['actions'][t['system_action_id']])]
        kwargs={'commitments':commitments,'completed_action_ids':completed}
        if horizon_days is not None: kwargs['horizon_days']=horizon_days
        elif isinstance(kernel,AdaptiveKernel): kwargs['horizon_days']=kernel.horizon
        comparison=kernel.propose(as_of,max_actions=max_actions,excluded_action_ids=excluded_action_ids,**kwargs)
        # Daily UI capacity is additional to the declared resource accounts. An action
        # is never shortened to make a portfolio appear feasible.
        over=[]
        for scenario in comparison['scenarios']:
            minutes=sum(kernel.index['actions'][a]['minutes'] for a in scenario['action_ids'])
            if minutes>available_minutes:
                over.append(scenario['action_ids'])
        if over:
            portfolios=[s['action_ids'] for s in comparison['scenarios'] if s['action_ids'] not in over]
            comparison=kernel.compare(portfolios,as_of,**kwargs)
        return {'revision':revision['id'],'mode':'adaptive' if isinstance(kernel,AdaptiveKernel) else 'declared_scenario',
                'synthetic':bool(kernel.model.get('synthetic')),'goals':kernel.model['goals'],'goal_order':kernel.model['goal_order'],
                'dimensions':kernel.model['dimensions'],'episode_count':len(kernel.model.get('episodes',[])),'state':kernel.snapshot(as_of,commitments=commitments),
                'comparison':comparison,'daily_capacity_excluded_portfolios':over}

    def planning_snapshot(self, *, today, available_minutes):
        # A stable decision epoch preserves reviewable proposals between UI polls.
        at=datetime.now(timezone.utc).replace(second=0,microsecond=0).isoformat()
        revision,kernel=self.kernel()
        if kernel is None: return None
        tasks=self.repo.all('tasks')
        excluded={t['system_action_id'] for t in tasks if t.get('system_action_id') and t.get('focus_date')==today}
        for row in self.repo.all('suggestions'):
            if row.get('system_revision')==revision['id'] and row.get('feedback_date')==today and row.get('status') in {'accepted','dismissed'}:
                excluded.add(row.get('system_action_id'))
        evaluation=self.evaluate(at,available_minutes=available_minutes,excluded_action_ids=excluded)
        result=evaluation['comparison']; selected=next((r for r in result['scenarios'] if r['id']==result['preferred_id']),None)
        candidates=[]
        for aid in selected['action_ids'] if selected else []:
            a=kernel.index['actions'][aid]
            commitments=[{'resource_key':resource_key(kernel.index['resources'][c['resource_id']]),'amount':c['amount']['upper'] if isinstance(c['amount'],dict) else c['amount']} for c in a.get('costs',[])]
            candidates.append({'id':'system:'+aid,'record_id':'PS-'+fingerprint({'action':aid,'revision':revision['id']})[:24],
                'kind':'system','title':a['title'],'reason':('合成示例。' if evaluation['synthetic'] else '')+'根据已声明的目标取舍、完整资源消耗和'+('历史观察预测' if evaluation['mode']=='adaptive' else '显式影响假设')+'比较方案；预测仍需后续核验。',
                'first_step':a['first_step'],'done_when':a['done_when'],'minutes':a['minutes'],'domain':'other','goal_id':None,'task_id':None,
                'revision':fingerprint(a),'system_revision':revision['id'],'system_action_id':aid,
                'system_action_sha256':fingerprint(a),'system_commitments':commitments,
                'system_scenario':selected['id'],'system_mode':evaluation['mode'],
                'system_goal_ids':a.get('goal_ids',[]),'system_dimension_name':next((kernel.index['dimensions'][g['dimension_id']]['name'] for g in kernel.model['goals'] if g['id'] in a.get('goal_ids',[])),'跨维度'),'system_forecast':selected.get('forecast'),
                'system_costs':selected['costs']})
        return {'date':today,'available_minutes':available_minutes,'goals':kernel.model['goals'],'candidates':candidates,
                'evidence':[],'limits':{'goals_total':len(kernel.model['goals']),'goals_included':len(kernel.model['goals'])},
                'system':evaluation}


def validate_revision_history(rows):
    parent=None
    for row in reversed(rows):  # Repository exports newest first.
        if row.get('parent_revision')!=parent:
            raise ModelError('人生模型版本链不完整')
        kernel=kernel_for(row['model'])
        expected=fingerprint({'model':kernel.model_sha256,'parent':parent,'created_at':row['created_at']})
        if row['id']!=expected:
            raise ModelError('人生模型版本内容校验失败')
        parent=row['id']
