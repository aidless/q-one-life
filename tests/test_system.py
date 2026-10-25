"""Acceptance of the actual learned kernel through API, persistence and planner."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from qone_life.web import create_app

AT='2026-10-25T00:00:00+00:00'
HEADERS={'X-QOne-Client':'web'}


class Frozen(datetime):
    @classmethod
    def now(cls,tz=None):
        return cls(2026,10,25,0,0,tzinfo=timezone.utc)


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.model=json.loads((Path(__file__).parents[1]/'examples/adaptive.synthetic.json').read_text())
        self.calls=[]
        def runner(*args):
            self.calls.append(args)
            raise AssertionError('Adaptive mode must not delegate decision authority to an LLM')
        self.app=create_app(self.temp.name,plan_runner=runner)
        self.client=TestClient(self.app,base_url='http://localhost',headers=HEADERS)
        self.addCleanup(self.client.close)
        for target in ['qone_life.system.datetime','qone_life.planner.datetime']:
            p=patch(target,Frozen); p.start(); self.addCleanup(p.stop)

    def load(self,model=None,parent=None,status=201):
        r=self.client.post('/api/system',json={'model':model or self.model,'parent_revision':parent})
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def feed(self):
        r=self.client.get('/api/planner'); self.assertEqual(r.status_code,200,r.text); return r.json()

    def test_actual_kernel_recommend_accept_reserve_and_restart(self):
        first=self.load(); repeat=self.load(parent=first['revision'])
        self.assertTrue(repeat['unchanged'])
        self.assertEqual(len(self.app.state.repository.all('system_revisions')),1)
        feed=self.feed()
        self.assertEqual(feed['system']['mode'],'adaptive')
        self.assertTrue(feed['system']['synthetic'])
        self.assertEqual(feed['items'][0]['system_action_id'],'study')
        self.assertEqual(feed['items'][0]['source'],'adaptive')
        self.app.state.planner.tick(); self.assertEqual(self.calls,[])
        card=feed['items'][0]
        r=self.client.post('/api/planner/'+card['id']+'/feedback',json={'action':'accept','proposal_sha256':card['proposal_sha256']})
        self.assertEqual(r.status_code,200,r.text)
        task=self.app.state.repository.all('tasks')[0]
        self.assertEqual(task['system_commitments'][0]['amount'],45)
        self.assertEqual(task['estimate_minutes'],45)
        self.assertEqual(self.feed()['system']['state']['resources']['time']['available'],15)
        with TestClient(create_app(self.temp.name),base_url='http://localhost',headers=HEADERS) as restart:
            self.assertEqual(restart.get('/api/planner').json()['system']['state']['resources']['time']['available'],15)

    def test_low_data_and_undeclared_preference_do_not_silently_fall_back(self):
        self.model['episodes']=self.model['episodes'][:4]
        first=self.load(); feed=self.feed()
        self.assertEqual(feed['items'],[])
        self.assertEqual(feed['status'],'needs_information')
        self.assertEqual(feed['system']['comparison']['choice_status'],'no_feasible_plan')
        self.model['goal_order']=[]
        self.load(parent=first['revision'])
        self.assertEqual(self.feed()['items'],[])
        self.assertEqual(self.calls,[])

    def test_revision_concurrency_stale_proposals_and_history_roundtrip(self):
        first=self.load(); card=self.feed()['items'][0]
        updated=deepcopy(self.model); updated['resources'][0]['budget']=10
        self.load(updated,parent=None,status=400)
        second=self.load(updated,parent=first['revision'])
        r=self.client.post('/api/planner/'+card['id']+'/feedback',json={'action':'accept','proposal_sha256':card['proposal_sha256']})
        self.assertEqual(r.status_code,400)
        self.assertEqual(self.app.state.repository.all('tasks'),[])
        backup=self.client.get('/api/backup').json()
        self.assertEqual(backup['format'],'q-one-backup-v3')
        with tempfile.TemporaryDirectory() as folder,TestClient(create_app(folder),base_url='http://localhost',headers=HEADERS) as restored:
            r=restored.post('/api/restore',json=backup); self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(restored.get('/api/system').json()['current']['id'],second['revision'])
            self.assertEqual(restored.get('/api/planner').json()['items'],[])
        backup['tables']['system_revisions'][0]['model']['title']='tampered'
        with tempfile.TemporaryDirectory() as folder,TestClient(create_app(folder),base_url='http://localhost',headers=HEADERS) as restored:
            self.assertEqual(restored.post('/api/restore',json=backup).status_code,400)

    def test_replay_and_v2_backup_compatibility(self):
        self.load(); r=self.client.post('/api/system/replay',json={})
        self.assertEqual(r.status_code,200,r.text)
        self.assertFalse(r.json()['policy_value_estimated'])
        for summary in r.json()['summary'].values(): self.assertLess(summary['mae'],summary['no_change_mae'])
        backup=self.client.get('/api/backup').json(); backup['format']='q-one-backup-v2'; backup['tables'].pop('system_revisions')
        with tempfile.TemporaryDirectory() as folder,TestClient(create_app(folder),base_url='http://localhost',headers=HEADERS) as restored:
            r=restored.post('/api/restore',json=backup); self.assertEqual(r.status_code,200,r.text)
            self.assertIsNone(restored.get('/api/system').json()['current'])

    def test_simultaneous_acceptance_cannot_spend_budget_twice(self):
        self.load(); card=self.feed()['items'][0]; results=[]
        def accept():
            try: results.append(self.app.state.planner.feedback(card['id'],'accept',card['proposal_sha256']))
            except ValueError: results.append('rejected')
        threads=[threading.Thread(target=accept) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(self.app.state.repository.all('tasks')),1)
        self.assertEqual(results.count('rejected'),1)

    def test_learning_validation_and_daily_capacity(self):
        self.model['learning']['context_features'][0]['scale']=0
        self.load(status=400)
        self.model['learning']['context_features'][0]['scale']=20
        self.load()
        r=self.client.post('/api/system/evaluate',json={'as_of':AT,'available_minutes':30})
        self.assertEqual(r.status_code,200,r.text)
        comparison=r.json()['comparison']
        self.assertEqual([s['action_ids'] for s in comparison['scenarios']],[[]])
        self.assertNotIn(['study'],[s['action_ids'] for s in comparison['scenarios']])
        self.assertEqual(self.client.post('/api/system/evaluate',json={'available_minutes':-1}).status_code,400)
