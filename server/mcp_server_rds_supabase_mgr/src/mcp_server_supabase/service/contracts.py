"""Pure request validation and conservative asynchronous response normalization.
No transport, credentials, internal endpoints or job terminal-state assumptions.
"""
import re
from typing import Any


def ssl_body(enable_ssl: bool, cert_id: str | None = None) -> dict[str, object]:
    if type(enable_ssl) is not bool:
        raise ValueError('enable_ssl must be boolean')
    if enable_ssl:
        if not isinstance(cert_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{3,64}', cert_id):
            raise ValueError('A valid certificate identifier is required')
    elif cert_id is not None:
        raise ValueError('Certificate must be null when disabling SSL')
    return {'enable_ssl': enable_ssl, 'cert_id': cert_id}


def api_key_query(limit: int = 10, offset: int = 0, status: str | None = None,
                  key_type: str | None = None, sort_key: str = 'created_time',
                  sort_dir: str = 'desc', key_id: str | None = None) -> dict[str, object]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be an integer from 1 to 100')
    if type(offset) is not int or offset < 0:
        raise ValueError('offset must be a non-negative integer')
    if status is not None and status not in ('normal', 'creating', 'createfail', 'deleted'):
        raise ValueError('Unsupported status')
    if key_type is not None and key_type not in ('publishable', 'secret', 'anon', 'service_role'):
        raise ValueError('Unsupported key type')
    if sort_key not in ('name','status','type','created_user','updated_user','created_time','updated_time') or sort_dir not in ('asc','desc'):
        raise ValueError('Unsupported sort')
    query: dict[str, object] = {'limit':limit, 'offset':offset, 'sort_key':sort_key, 'sort_dir':sort_dir}
    if status is not None:
        query['status'] = status
    if key_type is not None:
        query['type'] = key_type
    if key_id is not None:
        if not isinstance(key_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key_id):
            raise ValueError('Invalid key identifier')
        query['id'] = key_id
    return query


APPLICATION_SORT_KEYS = ('name', 'status', 'mode', 'created_time', 'updated_time')
APPLICATION_MANDATORY_FIELDS = ('id', 'name', 'public_ip', 'port', 'flavor_ref', 'mode',
                                'created_time')
_APPLICATION_OPTIONAL_FIELDS = ('updated_time', 'remark')
APPLICATION_DETAIL_MANDATORY_FIELDS = ('id', 'name', 'mode', 'status', 'port', 'enable_ssl',
                                       'private_ip', 'created_time')
_APPLICATION_DETAIL_OPTIONAL_FIELDS = ('public_ip', 'traffic_vip', 'manage_ip', 'updated_time',
                                       'remark')
_APPLICATION_ALIASES = {
    'id': ('id', 'application_id'),
    'name': ('name',),
    'public_ip': ('public_ip', 'direct_eip', 'public_ip_address', 'eip_address'),
    'port': ('port', 'gateway_port'),
    'flavor_ref': ('flavor_ref', 'flavor'),
    'mode': ('mode', 'deploy_mode'),
    'created_time': ('created_time', 'created_at', 'create_time'),
    'updated_time': ('updated_time', 'updated_at'),
    'remark': ('remark', 'description'),
}
_SECRET_MARKERS = ('password', 'pwd', 'secret', 'token', 'api_key', 'credential')
_TIME_FIELDS = ('created_time', 'updated_time')


def _epoch_ms_to_rfc3339(value: int) -> str:
    from datetime import datetime, timezone
    seconds, millis = divmod(value, 1000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc)
    return stamp.strftime('%Y-%m-%dT%H:%M:%S') + '.%03dZ' % millis


def _normalize_value(key: str, value, depth: int = 0):
    """Bounded sanitize: drop secret-marked keys, cap arrays/strings/depth; normalize epoch-ms times."""
    if depth > 8:
        return None
    if key in _TIME_FIELDS and isinstance(value, int) and not isinstance(value, bool):
        try:
            return _epoch_ms_to_rfc3339(value)
        except (ValueError, OSError, OverflowError):
            return value
    if isinstance(value, dict):
        return {k: _normalize_value(k, v, depth + 1) for k, v in value.items()
                if not any(marker in k.lower() for marker in _SECRET_MARKERS)
                and k.lower() not in ('ak', 'sk')}
    if isinstance(value, list):
        return [_normalize_value(key, entry, depth + 1) for entry in value[:100]]
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return None


def application_query(limit: int = 10, offset: int = 0, application_id: str | None = None,
                      name: str | None = None, sort_key: str = 'created_time',
                      sort_dir: str = 'desc') -> dict[str, object]:
    """Applications are always scoped to type=supabase; the type filter is not configurable."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be an integer from 1 to 100')
    if type(offset) is not int or offset < 0:
        raise ValueError('offset must be a non-negative integer')
    if sort_key not in APPLICATION_SORT_KEYS or sort_dir not in ('asc', 'desc'):
        raise ValueError('Unsupported sort')
    if name is not None and (not isinstance(name, str) or not 1 <= len(name) <= 128):
        raise ValueError('Invalid name filter')
    query: dict[str, object] = {'limit': limit, 'offset': offset, 'type': 'supabase',
                                'sort_key': sort_key, 'sort_dir': sort_dir}
    if name is not None:
        query['name'] = name
    if application_id is not None:
        if not isinstance(application_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', application_id):
            raise ValueError('Invalid application identifier')
        query['id'] = application_id
    return query


def _project(row: dict, mandatory: tuple, optional: tuple) -> dict[str, object]:
    """Project one record: promote aliases, enforce mandatory fields, bounded passthrough.

    Alias keys are skipped from passthrough only when actually consumed as the
    source of a projected field.
    """
    item: dict[str, object] = {}
    consumed = set()
    for field in mandatory + optional:
        source = next((alias for alias in _APPLICATION_ALIASES.get(field, (field,)) if alias in row),
                      None)
        if source is not None:
            value = row[source]
            if field in mandatory and value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValueError('Invalid application field: ' + field)
            item[field] = _normalize_value(field, value)
            consumed.add(source)
        elif field in mandatory:
            raise ValueError('Mandatory application field missing: ' + field)
        else:
            item[field] = None
    for key, value in row.items():
        if key in item or key in consumed:
            continue
        if any(marker in key.lower() for marker in _SECRET_MARKERS) or key.lower() in ('ak', 'sk'):
            continue
        item[key] = _normalize_value(key, value)
    return item


def application_metadata(body: dict[str, Any]) -> dict[str, object]:
    """Accept the confirmed applications envelope; enforce mandatory fields with bounded passthrough."""
    rows, total = body.get('data'), body.get('total_count')
    if not isinstance(rows, list) or type(total) is not int or total < len(rows):
        raise ValueError('Unrecognized application metadata envelope')
    result = []
    for row in rows[:100]:
        if not isinstance(row, dict):
            raise ValueError('Invalid application record')
        result.append(_project(row, APPLICATION_MANDATORY_FIELDS, _APPLICATION_OPTIONAL_FIELDS))
    return {'total_count': total, 'data': result}


def application_detail(body: dict[str, Any]) -> dict[str, object]:
    """Accept the application detail object; enforce mandatory fields with bounded passthrough."""
    if not isinstance(body, dict):
        raise ValueError('Unrecognized application detail response')
    return _project(body, APPLICATION_DETAIL_MANDATORY_FIELDS, _APPLICATION_DETAIL_OPTIONAL_FIELDS)


AUTH_CONFIG_MANDATORY_FIELDS = ('enable_account_sign_up', 'enable_anonymous_users',
                                'api_external_url', 'site_url', 'allow_redirect_urls',
                                'github_oauth_provider', 'email_oauth_provider',
                                'email_template_config')
_AUTH_FLAG_FIELDS = ('enable_account_sign_up', 'enable_anonymous_users')
_AUTH_STRING_FIELDS = ('api_external_url', 'site_url', 'allow_redirect_urls')
_AUTH_OBJECT_FIELDS = ('github_oauth_provider', 'email_oauth_provider', 'email_template_config')


def auth_config_detail(body: dict[str, Any]) -> dict[str, object]:
    """Accept the auth configuration object; enforce the documented schema shape.

    Secrets (SMTP credentials, OAuth client secrets) are dropped at any depth;
    identifiers such as oauth_client_id and smtp_user remain. Empty strings
    mean "not configured".
    """
    if not isinstance(body, dict):
        raise ValueError('Unrecognized auth configuration response')
    item: dict[str, object] = {}
    for field in AUTH_CONFIG_MANDATORY_FIELDS:
        if field not in body:
            raise ValueError('Mandatory auth configuration field missing: ' + field)
        value = body[field]
        if field in _AUTH_FLAG_FIELDS and type(value) is not bool:
            raise ValueError('Auth configuration flag must be boolean: ' + field)
        if field in _AUTH_STRING_FIELDS and not isinstance(value, str):
            raise ValueError('Auth configuration URL field must be a string: ' + field)
        if field in _AUTH_OBJECT_FIELDS and not isinstance(value, dict):
            raise ValueError('Auth configuration section must be an object: ' + field)
        item[field] = _normalize_value(field, value)
    for key, value in body.items():
        if key in item:
            continue
        if any(marker in key.lower() for marker in _SECRET_MARKERS) or key.lower() in ('ak', 'sk'):
            continue
        item[key] = _normalize_value(key, value)
    return item



def key_metadata(body: dict[str, Any]) -> dict[str, object]:
    """Accept the confirmed list envelope and expose only bounded metadata."""
    rows, total = body.get('data'), body.get('total_count')
    if not isinstance(rows, list) or type(total) is not int or total < len(rows):
        raise ValueError('Unrecognized key metadata envelope')
    allowed = ('id', 'name', 'status', 'type', 'created_time', 'updated_time')
    result = []
    for row in rows[:100]:
        if not isinstance(row, dict):
            raise ValueError('Invalid key metadata record')
        item = {}
        for field in allowed:
            if field not in row:
                continue
            value = row[field]
            if value is not None and type(value) not in (str, int):
                raise ValueError('Invalid key metadata field')
            item[field] = value[:2000] if isinstance(value, str) else value
        result.append(item)
    return {'total_count': total, 'data': result}


def accepted_job(http_status: int, body: dict[str, Any]) -> dict[str, object]:
    job_id = body.get('job_id')
    if http_status != 202 or not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', job_id):
        raise ValueError('Unrecognized acceptance response; reconcile before retrying')
    return {'status':'accepted', 'job_id':job_id, 'complete':False}
