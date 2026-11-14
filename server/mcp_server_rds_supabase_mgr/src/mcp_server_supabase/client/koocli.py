"""KooCLI (hcloud) subprocess channel for native VPC operations the RDS origin does not serve.

Invocation contract follows Huawei Cloud's own huaweicloud-devkit runner: global
flags position-free, credentials injected per command from this server's
canonical environment, project resolution left to KooCLI (region default
project; a sub-project deployment must configure the hcloud profile because
KooCLI does not take cli-project-id per command).
"""
import asyncio
import hashlib
import json
import os
import re
import shutil
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.client.rest import error_detail

PRIVACY_SIGNATURES = ('同意并继续使用', '[USE_ERROR]您输入的是无效字符')


def locate_binary():
    override = os.getenv('HCLOUD_BIN', '')
    if override:
        return override if os.path.isfile(override) and os.access(override, os.X_OK) else None
    home = os.path.expanduser('~')
    for candidate in (os.path.join(home, '.local', 'bin', 'hcloud'),
                      '/usr/local/bin/hcloud',
                      os.path.join(home, 'hcloud', 'hcloud.exe')):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which('hcloud')


def region_from_env():
    region = os.getenv('HUAWEICLOUD_REGION', '')
    if region:
        return region
    match = re.search(r'([a-z]{2,4}-[a-z]+-\d+)', os.getenv('SUPABASE_RDS_ENDPOINT', ''))
    return match.group(1) if match else ''


def flatten_params(params):
    flags = []
    for key, value in (params or {}).items():
        if isinstance(value, dict):
            flags.extend(f'--{key}.{sub}={item}' for sub, item in value.items())
        elif isinstance(value, (list, tuple)):
            flags.extend(f'--{key}.{index}={item}' for index, item in enumerate(value, start=1))
        else:
            flags.append(f'--{key}={value}')
    return flags


def parse_payload(text):
    text = text.strip()
    if not text:
        return {}
    start = text.find('{')
    if start < 0:
        raise McpToolError('MCP_CLI_ERROR', 'KooCLI returned no JSON payload')
    for candidate in (text[start:], text[start:text.rfind('}') + 1]):
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    raise McpToolError('MCP_CLI_ERROR', 'KooCLI returned an unparseable payload')


class KoocliClient:
    def __init__(self, binary=None, region=None, ak=None, sk=None, security_token=None, timeout=60):
        self.binary = binary if binary is not None else locate_binary()
        self.region = region if region is not None else region_from_env()
        self._ak = ak if ak is not None else os.getenv('HUAWEICLOUD_ACCESS_KEY', '')
        self._sk = sk if sk is not None else os.getenv('HUAWEICLOUD_SECRET_KEY', '')
        self._security_token = security_token if security_token is not None else os.getenv('HUAWEICLOUD_SECURITY_TOKEN', '')
        self.timeout = timeout
        self.token = hashlib.sha256(json.dumps(['koocli', self._ak, self._sk, self._security_token, self.region]).encode()).hexdigest()

    def argv(self, service, operation, params=None):
        if not self.binary:
            raise McpToolError('MCP_CLI_MISSING', 'KooCLI (hcloud) is not available',
                               hint='Install KooCLI per the skill INSTALL.md section 4, or point HCLOUD_BIN at the binary.')
        argv = [self.binary, service, operation, *flatten_params(params)]
        if self.region:
            argv.append(f'--cli-region={self.region}')
        if self._ak and self._sk:
            argv.append(f'--cli-access-key={self._ak}')
            argv.append(f'--cli-secret-key={self._sk}')
            if self._security_token:
                argv.append(f'--cli-security-token={self._security_token}')
        return argv

    async def call(self, service, operation, params=None):
        argv = self.argv(service, operation, params)
        try:
            process = await asyncio.create_subprocess_exec(
                *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL)
        except (FileNotFoundError, PermissionError):
            raise McpToolError('MCP_CLI_MISSING', 'KooCLI (hcloud) is not executable',
                               hint='Install KooCLI per the skill INSTALL.md section 4, or point HCLOUD_BIN at the binary.') from None
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), self.timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise McpToolError('MCP_CLI_TIMEOUT', f'KooCLI {operation} timed out after {self.timeout}s',
                               hint='A timed-out call may still have been applied; reconcile the resource state before retrying.') from None
        if process.returncode != 0:
            self._raise_failure(operation, process.returncode,
                                (stdout or b'').decode('utf-8', 'replace') + (stderr or b'').decode('utf-8', 'replace'))
        return parse_payload((stdout or b'').decode('utf-8', 'replace'))

    def _raise_failure(self, operation, returncode, text):
        if any(signature in text for signature in PRIVACY_SIGNATURES):
            raise McpToolError('MCP_CLI_BLOCKED', 'KooCLI first-run privacy agreement has not been accepted',
                               hint='Run `hcloud version` in a terminal and accept the agreement once (y), then retry.')
        detail = error_detail(text[text.find('{'):]) if '{' in text else None
        message = f'KooCLI {operation} failed with exit code {returncode}'
        if detail:
            message += ' (backend: ' + ', '.join(f'{k}={v}' for k, v in detail.items()) + ')'
        else:
            snippet = ' '.join(text.split())[:200]
            if snippet:
                message += f': {snippet}'
        raise McpToolError('MCP_CLI_ERROR', message,
                           hint='Verify the parameters with `hcloud VPC <Operation> --help`, check credentials and region, then retry.')
