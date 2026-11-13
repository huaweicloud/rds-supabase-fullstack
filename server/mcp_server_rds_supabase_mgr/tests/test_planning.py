import unittest
from mcp_server_supabase.service.planning import PlanningService

class PlanningTests(unittest.IsolatedAsyncioTestCase):
    async def test_unspecified_intents_become_decision_points(self):
        result = await PlanningService().creation()
        self.assertEqual(result['execution'],'not_executed')
        self.assertIsNone(result['manage_type'])
        self.assertEqual(result['status'],'planning_only')
        for needle in ('database route','file storage requirement','public access requirement','https requirement','email login requirement','GitHub login requirement'):
            self.assertTrue(any(needle in d for d in result['decision_points']),needle)
        self.assertTrue(any('api_external_url' in s for s in result['post_creation']))
        self.assertTrue(any('CCM' in s for s in result['post_creation']))

    async def test_route_a_full_intent_plan(self):
        result = await PlanningService().creation('newly_instance',needs_storage=True,needs_public_access=True,needs_ssl=True,needs_email_login=False,needs_github_login=False)
        self.assertEqual(result['decision_points'],[])
        self.assertTrue(any('OBS' in s and 'SK omission is not available' in s for s in result['pre_creation']))
        self.assertTrue(any('ListFlavors' in s for s in result['pre_creation']))
        self.assertTrue(any('ListStorageTypes' in s for s in result['pre_creation']))
        self.assertTrue(any('deployment mode' in s for s in result['pre_creation']))
        self.assertTrue(any('prepaid' in s for s in result['pre_creation']))
        self.assertTrue(any('two jobs' in s for s in result['creation']))
        self.assertTrue(any('CCM' in s for s in result['post_creation']))
        self.assertTrue(any('api_external_url' in s for s in result['post_creation']))
        self.assertFalse(any('email login' in s for s in result['post_creation']))
        self.assertFalse(any('GitHub login' in s for s in result['post_creation']))

    async def test_route_b_internal_only(self):
        result = await PlanningService().creation('existed_instance',needs_storage=False,needs_public_access=False,needs_ssl=False)
        self.assertTrue(any('list_supabase_manageable_instances' in s for s in result['pre_creation']))
        self.assertTrue(any('database_name' in s for s in result['pre_creation']))
        self.assertTrue(any('{enabled:false}' in s for s in result['pre_creation']))
        self.assertTrue(any('internal access only' in s for s in result['post_creation']))
        self.assertFalse(any('bind an EIP' in s for s in result['post_creation']))
        self.assertFalse(any('CCM' in s for s in result['post_creation']))

    async def test_invalid_manage_type(self):
        self.assertIn('error',await PlanningService().creation('unknown'))

    async def test_ssl(self):
        service = PlanningService()
        self.assertEqual((await service.ssl(False))['status'],'planning_only')
        self.assertEqual((await service.ssl(True))['execution'],'not_executed')
        self.assertEqual(len(service.capabilities()['scenarios']),6)

    async def test_adapter(self):
        class FixtureClient:
            async def list_certificates(self):
                return {'source':'test_fixture','certificates':[]}
        result = await PlanningService(FixtureClient()).ssl(True)
        self.assertEqual(result['certificates']['source'],'test_fixture')
        self.assertEqual(result['execution'],'not_executed')
