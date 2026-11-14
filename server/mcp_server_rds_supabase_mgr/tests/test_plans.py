import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from mcp_server_supabase.service.plans import PlanStore
from huaweicloud_mcp_core.errors import McpToolError

class PlansTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'plans.db';self.store=PlanStore(self.path)
    def test_expiry_binding(self):
        p=self.store.issue('a',ttl=-1)
        with self.assertRaises(McpToolError):self.store.claim(p['plan_id'],'a')
        p=self.store.issue('a')
        with self.assertRaises(McpToolError):self.store.claim(p['plan_id'],'changed')
    def test_restart_and_equivalent_intent(self):
        p=self.store.issue('a');self.store.claim(p['plan_id'],'a');self.store.finish(p['plan_id'],'unknown')
        fresh=PlanStore(self.path)
        with self.assertRaises(McpToolError):fresh.claim(p['plan_id'],'a')
        q=fresh.issue('a')
        with self.assertRaises(McpToolError):fresh.claim(q['plan_id'],'a')
        self.assertEqual(fresh.inspect(p['plan_id'])['state'],'unknown')
    def test_concurrent_claim(self):
        p=self.store.issue('a')
        def claim(_):
            try:self.store.claim(p['plan_id'],'a');return True
            except McpToolError:return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(claim,range(2))),1)
