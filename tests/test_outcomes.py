"""Real local intake through API, revision storage, learner and backup; synthetic data."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from qone_core.life import AdaptiveKernel
from qone_life.web import create_app

NOW = '2026-10-26T00:00:00+00:00'
BEFORE = '2026-10-25T00:00:00+00:00'
HEADERS = {'X-QOne-Client': 'web'}


class Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 26, tzinfo=timezone.utc)


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.app = create_app(self.temp.name, plan_runner=lambda *a: (_ for _ in ()).throw(AssertionError('No model calls')))
        self.client = TestClient(self.app, base_url='http://localhost', headers=HEADERS)
        self.addCleanup(self.client.close)
        for target in ['qone_life.system.datetime', 'qone_life.planner.datetime']:
            p = patch(target, Frozen); p.start(); self.addCleanup(p.stop)
        self.model = json.loads((Path(__file__).parents[1] / 'examples/adaptive.synthetic.json').read_text())
        self.model['resources'][0]['valid_until'] = '2026-10-27T00:00:00+00:00'
        self.import_model(self.model, None)

    def import_model(self, model, parent):
        r = self.client.post('/api/system', json={'model': model, 'parent_revision': parent})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def current(self):
        return self.client.get('/api/system').json()['current']

    def preview(self, at=NOW):
        r = self.client.post('/api/system/outcomes/preview', json={'action_ids': ['study'], 'observed_at': at})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def request(self, eid='sample-1'):
        p = self.preview()
        self.assertTrue(p['eligible'], p['issues'])
        return {'event_id': eid, 'parent_revision': p['revision'], 'action_ids': p['action_ids'],
                'observed_at': p['observed_at'], 'before': p['before'],
                'action_definition_sha256': p['action_definition_sha256'], 'outcomes': {'practice': 62, 'work': 41},
                'source': 'SYNTHETIC explicit fixed-window measurement', 'execution_confirmed': True}

    def test_read_only_preview_and_confirmed_result_feed_actual_learner_without_past_leak(self):
        initial = self.current()
        p = self.preview()
        self.assertEqual(self.current(), initial)
        self.assertEqual(p['started_at'], BEFORE)
        self.assertEqual(p['before']['practice'], 'current-practice')
        self.assertEqual(p['actions'][0]['minutes'], 45)
        before = AdaptiveKernel(initial['model']).forecast(['study'], BEFORE)
        response = self.client.post('/api/system/outcomes', json=self.request())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertFalse(response.json()['unchanged'])
        current = self.current(); episode = current['model']['episodes'][-1]
        self.assertEqual(episode['recorded_at'], NOW)
        self.assertEqual(len(current['model']['episodes']), 97)
        self.assertEqual(episode['after'].keys(), {'practice', 'work'})
        kernel = AdaptiveKernel(current['model'])
        self.assertEqual(len(kernel.fitted(NOW)['episodes']), 97)
        self.assertEqual(kernel.forecast(['study'], BEFORE)['predictions'], before['predictions'])
        self.assertEqual(len(initial['model']['episodes']), 96)
        self.assertTrue(all(o['recorded_at'] == NOW and o['source_kind'] == 'user_report'
                            for o in current['model']['observations'][-2:]))

    def test_invalid_payloads_do_not_write_and_server_time_cannot_be_spoofed(self):
        body = self.request(); initial = self.current()
        bad = [body | {'recorded_at': BEFORE}, body | {'confidence': .99},
               body | {'execution_confirmed': False}, body | {'action_definition_sha256': 'changed'},
               body | {'outcomes': {'practice': True, 'work': 1}},
               body | {'outcomes': {'practice': -1, 'work': 1}},
               body | {'outcomes': {'practice': 62}}, body | {'before': {'practice': 'unknown'}},
               body | {'source': ''}, body | {'observed_at': '2026-10-27T00:00:00Z'}]
        for value in bad:
            with self.subTest(value=value):
                r = self.client.post('/api/system/outcomes', json=value)
                self.assertEqual(r.status_code, 400, r.text)
                self.assertEqual(self.current(), initial)

    def test_missing_expired_interval_and_corrected_before_evidence_cannot_be_invented(self):
        variants = []
        m = deepcopy(self.model)
        m['observations'] = [o for o in m['observations'] if not o['id'].startswith('current-')]
        variants.append(m)
        m = deepcopy(self.model)
        next(o for o in m['observations'] if o['id'] == 'current-energy')['value'] = {'lower': 59, 'upper': 61}
        variants.append(m)
        m = deepcopy(self.model)
        old = next(o for o in m['observations'] if o['id'] == 'current-practice')
        m['observations'].append(old | {'id': 'corrected', 'supersedes': old['id'], 'value': 49,
                                       'recorded_at': '2026-10-25T12:00:00Z'})
        variants.append(m)
        for model in variants:
            self.import_model(model, self.current()['id'])
            self.assertFalse(self.preview()['eligible'])
            before = self.current()
            p = self.preview()
            r = self.client.post('/api/system/outcomes', json={
                'event_id': 'invalid', 'parent_revision': p['revision'], 'action_ids': ['study'],
                'observed_at': NOW, 'before': p['before'], 'outcomes': {'practice': 62, 'work': 41},
                'source': 'SYNTHETIC', 'execution_confirmed': True,
                'action_definition_sha256': p['action_definition_sha256']})
            self.assertEqual(r.status_code, 400, r.text)
            self.assertEqual(self.current(), before)

    def test_retry_is_idempotent_but_changed_or_overlapping_result_is_rejected(self):
        body = self.request()
        first = self.client.post('/api/system/outcomes', json=body)
        self.assertEqual(first.status_code, 201, first.text)
        current = self.current()
        again = self.client.post('/api/system/outcomes', json=body)
        self.assertEqual(again.status_code, 201, again.text)
        self.assertTrue(again.json()['unchanged'])
        self.assertEqual(self.current(), current)
        changed = self.client.post('/api/system/outcomes', json=body | {'outcomes': {'practice': 63, 'work': 41}})
        self.assertEqual(changed.status_code, 400)
        overlap = self.client.post('/api/system/outcomes', json=body | {'event_id': 'another-id', 'parent_revision': current['id']})
        self.assertEqual(overlap.status_code, 400)
        self.assertFalse(self.preview()['eligible'])
        self.assertEqual(self.current(), current)

    def test_concurrent_writes_preserve_one_complete_revision_and_no_partial_observations(self):
        body = self.request(); results = []
        def save(eid):
            try:
                results.append(self.app.state.planner.system.record_outcome(body | {'event_id': eid}))
            except ValueError:
                results.append('rejected')
        threads = [threading.Thread(target=save, args=(str(i),)) for i in range(2)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(len(self.current()['model']['episodes']), 97)
        self.assertEqual(len(self.current()['model']['observations']), len(self.model['observations']) + 2)
        self.assertEqual(len(self.app.state.repository.all('system_revisions')), 2)

    def test_backup_restart_resources_and_task_completion_do_not_create_fake_labels(self):
        feed = self.client.get('/api/planner').json(); card = feed['items'][0]
        r = self.client.post('/api/planner/' + card['id'] + '/feedback', json={
            'action': 'accept', 'proposal_sha256': card['proposal_sha256']})
        self.assertEqual(r.status_code, 200, r.text)
        task = self.app.state.repository.all('tasks')[0]
        self.client.patch('/api/tasks/' + task['id'], json={'done': True})
        self.assertEqual(len(self.current()['model']['episodes']), 96)
        body = self.request(); self.assertEqual(self.client.post('/api/system/outcomes', json=body).status_code, 201)
        self.assertEqual(self.client.get('/api/planner').json()['system']['state']['resources']['time']['available'], 15)
        current = self.current()
        backup = self.client.get('/api/backup').json()
        with tempfile.TemporaryDirectory() as folder, TestClient(create_app(folder), base_url='http://localhost', headers=HEADERS) as restored:
            response = restored.post('/api/restore', json=backup)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(restored.get('/api/system').json()['current'], current)
            self.assertTrue(restored.post('/api/system/outcomes', json=body).json()['unchanged'])
        with TestClient(create_app(self.temp.name), base_url='http://localhost', headers=HEADERS) as restarted:
            self.assertEqual(restarted.get('/api/system').json()['current'], current)

    def test_stale_parent_and_action_version_cannot_be_silently_rebased(self):
        body = self.request()
        updated = deepcopy(self.model); updated['title'] += ' updated'
        self.import_model(updated, body['parent_revision'])
        before = self.current()
        self.assertEqual(self.client.post('/api/system/outcomes', json=body).status_code, 400)
        self.assertEqual(self.current(), before)

    def test_fresh_observation_then_later_outcome_works_without_editing_model_data(self):
        model = deepcopy(self.model); model['observations'] = []; model['episodes'] = []
        self.import_model(model, self.current()['id'])
        initial = {'event_id': 'baseline', 'parent_revision': self.current()['id'], 'observed_at': NOW,
                   'values': {'energy': 60, 'practice': 50, 'work': 40}, 'source': 'SYNTHETIC baseline measurement'}
        r = self.client.post('/api/system/observations', json=initial)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(len(self.current()['model']['episodes']), 0)
        self.assertTrue(self.client.post('/api/system/observations', json=initial).json()['unchanged'])
        self.assertEqual(len(self.current()['model']['observations']), 3)
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 27, tzinfo=timezone.utc)
        with patch('qone_life.system.datetime', Later):
            p = self.preview('2026-10-27T00:00:00+00:00')
            self.assertTrue(p['eligible'], p['issues'])
            body = {'event_id': 'next-day', 'parent_revision': p['revision'], 'observed_at': p['observed_at'],
                    'action_ids': ['study'], 'before': p['before'], 'outcomes': {'practice': 62, 'work': 41},
                    'execution_confirmed': True, 'action_definition_sha256': p['action_definition_sha256'],
                    'source': 'SYNTHETIC next-day measurement'}
            self.assertEqual(self.client.post('/api/system/outcomes', json=body).status_code, 201)
        kernel = AdaptiveKernel(self.current()['model'])
        self.assertEqual(len(kernel.fitted('2026-10-27T00:00:00Z')['episodes']), 1)
        self.assertEqual(kernel.forecast(['study'], '2026-10-27T00:00:00Z')['status'], 'abstain')

    def test_observation_intake_rejects_forecast_fields_categories_and_invalid_values(self):
        body = {'event_id': 'obs', 'parent_revision': self.current()['id'], 'observed_at': NOW,
                'values': {'energy': 60}, 'source': 'SYNTHETIC observation'}
        initial = self.current()
        for invalid in [body | {'recorded_at': BEFORE}, body | {'observed_at': '2026-10-27T00:00:00Z'},
                        body | {'values': {'meaning': 10}}, body | {'values': {'energy': True}},
                        body | {'values': {'energy': -1}}]:
            self.assertEqual(self.client.post('/api/system/observations', json=invalid).status_code, 400)
            self.assertEqual(self.current(), initial)

    def test_new_observation_is_visible_immediately_without_unstable_polling(self):
        class Seconds(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 26, 0, 0, 17, tzinfo=timezone.utc)
        with patch('qone_life.system.datetime', Seconds):
            body = {'event_id': 'same-minute', 'parent_revision': self.current()['id'], 'observed_at': NOW,
                    'values': {'practice': 62, 'work': 41}, 'source': 'SYNTHETIC immediate visibility'}
            self.assertEqual(self.client.post('/api/system/observations', json=body).status_code, 201)
            first = self.client.get('/api/bootstrap').json()['planner']
            self.assertEqual(first['system']['state']['measures']['practice']['value']['lower'], 62)
            second = self.client.get('/api/bootstrap').json()['planner']
            self.assertEqual(first['input_sha256'], second['input_sha256'])
            self.assertEqual([c['proposal_sha256'] for c in first['items']], [c['proposal_sha256'] for c in second['items']])
