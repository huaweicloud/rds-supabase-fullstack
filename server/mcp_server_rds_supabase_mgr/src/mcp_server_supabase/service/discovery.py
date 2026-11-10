"""Credential-driven context discovery: resolve projects and a candidate RDS origin.

Runs before the MCP server is fully configured: uses the existing credentials to
verify the token scope (REST transport) or list IAM projects (sdk_core transport),
derives the standard regional RDS endpoint per project and optionally probes
reachability with one bounded read-only call. Never returns credentials or
resource values; project identifiers and names are returned for user selection.
"""
import os
import re

from mcp_server_supabase.client.rest import RestClient
from mcp_server_supabase.client.sdk_core import SdkCoreClient
from mcp_server_supabase.service.operations import ROOT

IAM_ORIGIN = 'https://iam.myhuaweicloud.com'
_REGION = re.compile(r'[a-z]{2,}-[a-z]+-\d+')


def derive_endpoint(region):
    """Standard regional RDS origin; only a successful probe confirms reachability."""
    return f'https://rds.{region}.myhuaweicloud.com'


def _region_of(name):
    return name if _REGION.fullmatch(name or '') else None


def _iam_client():
    """Client for the fixed global IAM origin; no project scoping is required."""
    transport = os.getenv('SUPABASE_TRANSPORT', 'rest')
    if transport == 'sdk_core':
        ak = os.getenv('HUAWEICLOUD_ACCESS_KEY', '')
        sk = os.getenv('HUAWEICLOUD_SECRET_KEY', '')
        if not ak or not sk or any(c in v for v in (ak, sk) for c in ('\r', '\n')):
            return None, 'Missing or invalid SDK credentials'
        return SdkCoreClient(endpoint=IAM_ORIGIN, project='', ak=ak, sk=sk, allow_loopback=True), None
    token = os.getenv('HUAWEICLOUD_AUTH_TOKEN', '')
    if not token or any(c in token for c in ('\r', '\n')):
        return None, 'Missing or invalid auth token'
    return RestClient(endpoint=IAM_ORIGIN, token=token, allow_loopback=True), None


async def _projects():
    """Return (projects, error, network_attempted); never raises, never echoes credentials."""
    transport = os.getenv('SUPABASE_TRANSPORT', 'rest')
    client, error = _iam_client()
    if error:
        return None, error, False
    try:
        if transport == 'sdk_core':
            _, data = await client.request('GET', '/v3/projects')
            projects = data.get('projects') if isinstance(data, dict) else None
            if not isinstance(projects, list) or not projects:
                return None, 'No projects are visible to these credentials', True
            return projects[:50], None, True
        token = os.getenv('HUAWEICLOUD_AUTH_TOKEN', '')
        _, data = await client.request('GET', '/v3/auth/tokens', headers={'X-Subject-Token': token})
        token_body = data.get('token') if isinstance(data, dict) else None
        project = token_body.get('project') if isinstance(token_body, dict) else None
        if not isinstance(project, dict) or not project.get('id'):
            return None, 'Token is not project-scoped; use a project-scoped token or switch to sdk_core with AK/SK', True
        return [project], None, True
    except Exception:
        return None, 'IAM query failed; verify credentials, IAM reachability and proxy/CA settings', True


async def _probe(endpoint, project_id):
    """One bounded read-only application-list call; response values are discarded."""
    transport = os.getenv('SUPABASE_TRANSPORT', 'rest')
    try:
        if transport == 'sdk_core':
            ak = os.getenv('HUAWEICLOUD_ACCESS_KEY', '')
            sk = os.getenv('HUAWEICLOUD_SECRET_KEY', '')
            client = SdkCoreClient(endpoint=endpoint, project=project_id, ak=ak, sk=sk,
                                   allow_loopback=True)
        else:
            client = RestClient(endpoint=endpoint, project=project_id,
                                token=os.getenv('HUAWEICLOUD_AUTH_TOKEN', ''), allow_loopback=True)
        status, _ = await client.request('GET', ROOT + '/applications',
                                         query={'limit': 1, 'offset': 0, 'type': 'supabase'})
        return {'reachable': bool(200 <= status < 300), 'verified': False}
    except Exception:
        return {'reachable': False, 'verified': False}


async def discover(probe=False):
    """Resolve selectable candidates (project + endpoint) from the configured credentials."""
    transport = os.getenv('SUPABASE_TRANSPORT', 'rest')
    if transport not in ('rest', 'sdk_core'):
        return {'mode': 'discover', 'passed': False, 'network_attempted': False,
                'error': 'Unsupported SUPABASE_TRANSPORT; use rest or sdk_core'}
    projects, error, attempted = await _projects()
    if error:
        return {'mode': 'discover', 'passed': False, 'network_attempted': attempted, 'error': error}
    explicit = os.getenv('SUPABASE_RDS_ENDPOINT', '').strip()
    candidates = []
    for project in projects:
        pid = str(project.get('id') or '')
        name = str(project.get('name') or '')
        region = _region_of(name)
        if explicit:
            endpoint, source = explicit, 'explicit'
        elif region:
            endpoint, source = derive_endpoint(region), 'derived'
        else:
            endpoint, source = None, 'manual'
        candidate = {'project_id': pid, 'project_name': name, 'region': region,
                     'endpoint': endpoint, 'endpoint_source': source,
                     'suggested_env': {'HUAWEICLOUD_PROJECT_ID': pid,
                                       'SUPABASE_RDS_ENDPOINT': endpoint} if endpoint else None}
        if probe and endpoint:
            candidate['probe'] = await _probe(endpoint, pid)
        candidates.append(candidate)
    return {'mode': 'discover', 'passed': bool(candidates), 'transport': transport,
            'network_attempted': True, 'explicit_endpoint_configured': bool(explicit),
            'candidates': candidates,
            'note': 'Pick one candidate and write its suggested_env into the MCP client '
                    'environment. Derived endpoints follow the standard regional RDS pattern; '
                    'only a successful probe confirms reachability, which is not permission '
                    'or production acceptance.'}
