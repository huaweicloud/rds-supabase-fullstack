import unittest
from unittest.mock import AsyncMock

from huaweicloud_mcp_core.errors import McpToolError

from mcp_server_supabase.service.operations import Operations

APP = 'app-1'
INST = 'inst-1'
JOB_APP = 'job-app'
JOB_INST = 'job-inst'


def app_row(status='normal', managed=None):
    return {'id': APP, 'name': 'a', 'type': 'supabase', 'status': status,
            'port': 8443, 'enable_ssl': False, 'created_time': 1794025857392,
            'managed_instance': managed if managed is not None else {'id': INST, 'name': 'pg'}}


def jobs_payload(app=None, inst=None):
    def one(job_id, status):
        return {'job': {'id': job_id, 'status': status}} if job_id else {}
    return [one(*app) if app else {}, one(*inst) if inst else {}]


class CreationProgressTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.client.endpoint = 'https://example.invalid'; self.client.project = 'project'; self.client.token = 'fixture'
        self.ops = Operations(self.client)

    def feed(self, app_page, *jobs):
        reads = [(200, {'total_count': 1 if app_page else 0, 'data': [app_page] if app_page else []})]
        reads += [(200, {'job': {'id': j[0], 'status': j[1]}}) for j in jobs]
        self.client.request.side_effect = reads

    async def test_existing_instance_running(self):
        self.feed(app_row(status='creating'), ('job-app', 'Running'))
        result = await self.ops.creation_progress(APP, JOB_APP)
        self.assertEqual(result['phase'], 'application_creating')
        self.assertEqual(result['scenario'], 'existing_instance')
        self.assertEqual(result['application']['job_status'], 'running')
        self.assertIsNone(result.get('instance'))

    async def test_existing_instance_completed(self):
        self.feed(app_row(), ('job-app', 'Completed'))
        result = await self.ops.creation_progress(APP, JOB_APP)
        self.assertEqual(result['phase'], 'succeeded')
        self.assertEqual(result['application']['application_status'], 'normal')

    async def test_new_instance_still_creating_application_not_started(self):
        # application list has no row yet; instance job running -> app job must NOT be queried
        self.client.request.side_effect = [
            (200, {'total_count': 0, 'data': []}),
            (200, {'job': {'id': JOB_INST, 'status': 'Running'}}),
        ]
        result = await self.ops.creation_progress(APP, JOB_APP, JOB_INST, INST)
        self.assertEqual(result['phase'], 'instance_creating')
        self.assertEqual(result['scenario'], 'new_instance')
        self.assertEqual(result['instance']['job_status'], 'running')
        self.assertEqual(result['application']['job_status'], 'not_started')
        # exactly two calls: application list + instance job
        self.assertEqual(self.client.request.await_count, 2)

    async def test_new_instance_completed_application_running(self):
        self.client.request.side_effect = [
            (200, {'total_count': 0, 'data': []}),
            (200, {'job': {'id': JOB_INST, 'status': 'Completed'}}),
            (200, {'job': {'id': JOB_APP, 'status': 'Running'}}),
        ]
        result = await self.ops.creation_progress(APP, JOB_APP, JOB_INST, INST)
        self.assertEqual(result['phase'], 'application_creating')
        self.assertEqual(result['instance']['job_status'], 'completed')
        self.assertEqual(result['application']['job_status'], 'running')

    async def test_new_instance_failed_blocks_application(self):
        self.client.request.side_effect = [
            (200, {'total_count': 0, 'data': []}),
            (200, {'job': {'id': JOB_INST, 'status': 'Failed'}}),
        ]
        result = await self.ops.creation_progress(APP, JOB_APP, JOB_INST, INST)
        self.assertEqual(result['phase'], 'failed')
        self.assertTrue(result['failed_stage'], 'instance')
        self.assertEqual(self.client.request.await_count, 2)

    async def test_new_instance_done_application_succeeded(self):
        self.client.request.side_effect = [
            (200, {'total_count': 1, 'data': [app_row()]}),
            (200, {'job': {'id': JOB_INST, 'status': 'Completed'}}),
            (200, {'job': {'id': JOB_APP, 'status': 'Completed'}}),
        ]
        result = await self.ops.creation_progress(APP, JOB_APP, JOB_INST, INST)
        self.assertEqual(result['phase'], 'succeeded')

    async def test_instance_failed_then_app_never_started(self):
        # instance failed AND the application never appears: overall failed
        self.client.request.side_effect = [
            (200, {'total_count': 0, 'data': []}),
            (200, {'job': {'id': JOB_INST, 'status': 'Failed'}}),
        ]
        result = await self.ops.creation_progress(APP, JOB_APP, JOB_INST, INST)
        self.assertEqual(result['phase'], 'failed')

    async def test_job_failure_reported(self):
        self.feed(app_row(status='creating'), ('job-app', 'Failed'))
        result = await self.ops.creation_progress(APP, JOB_APP)
        self.assertEqual(result['phase'], 'failed')
        self.assertEqual(result['failed_stage'], 'application')

    async def test_new_instance_requires_instance_args(self):
        with self.assertRaises(McpToolError):
            await self.ops.creation_progress(APP, JOB_APP, instance_job_id=JOB_INST, instance_id=None)
        with self.assertRaises(McpToolError):
            await self.ops.creation_progress(APP, JOB_APP, instance_job_id=None, instance_id=INST)

    async def test_unreadable_application_list_fails_closed(self):
        self.client.request.return_value = (200, {'total_count': 0, 'data': []})
        # existing-instance scenario with no job payload -> unknown job status surfaces
        result = await self.ops.creation_progress(APP, JOB_APP)
        self.assertIn(result['phase'], ('failed', 'application_creating'))


if __name__ == '__main__':
    unittest.main()
