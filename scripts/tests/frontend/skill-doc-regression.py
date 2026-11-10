"""Static structure and record-contract checks for the bundled skill."""
import copy
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / 'skills' / 'huaweicloud-supabase' / 'rds-supabase-frontend'
REFERENCES = SKILL / 'references'
EXAMPLES = REFERENCES / 'examples'
CONTRACT = (REFERENCES / 'record-contract.md').read_text()
PROVISIONING = (REFERENCES / 'domain-provisioning.md').read_text()
LINK_RE = re.compile(r'!?\[[^]]*\]\(([^)]+)\)')
HEADING_RE = re.compile(r'^#{1,6}\s+(.+?)\s*#*\s*$', re.MULTILINE)
SHA256_RE = re.compile(r'^[0-9a-f]{64}$')
CHECK_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')
CODE_LINE_RE = re.compile(r'^[a-z][a-z0-9_]*$')
BASE_REQUIRED_CHECKS = {'entry', 'domain_probe', 'assets', 'routes', 'cache'}
HOSTING_ROUTES = {'obs-domain': 'OBS', 'obs-cdn': 'OBS+CDN'}
BLOCKING_REASONS = {
    'icp_filing_missing', 'dns_not_hosted', 'domain_ownership_unverified',
    'certificate_unavailable',
}
REPAIRABLE_REASONS = {
    'dns_record_missing', 'cname_mismatch', 'bucket_policy_denies_anonymous',
    'website_hosting_disabled', 'entry_object_missing', 'certificate_not_bound',
    'cache_stale',
}
PENDING_REASONS = {
    'cdn_deploying', 'dns_propagating', 'certificate_issuing',
    'tls_handshake_timeout',
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def require_documented(fields):
    for field in fields:
        require(f'`{field}`' in CONTRACT, f'Undocumented field: {field}')


def expect_invalid(data, validator, label):
    try:
        validator(data, label)
    except AssertionError:
        return
    raise AssertionError(f'{label}: invalid fixture was accepted')


def slugify(title):
    title = re.sub(r'`([^`]+)`', r'\1', title.strip().lower())
    title = re.sub(r'[^\w\- ]', '', title, flags=re.UNICODE)
    return title.replace(' ', '-')


def anchors(text):
    counts = defaultdict(int)
    result = set()
    for title in HEADING_RE.findall(text):
        slug = slugify(title)
        suffix = counts[slug]
        counts[slug] += 1
        result.add(slug if suffix == 0 else f'{slug}-{suffix}')
    return result


def check_links():
    files = [path for path in SKILL.rglob('*.md') if '.git' not in path.parts]
    count = 0
    for file in files:
        text = file.read_text()
        local_anchors = anchors(text)
        for raw_target in LINK_RE.findall(text):
            target = raw_target.split()[0].strip('<>')
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target):
                continue
            count += 1
            path_part, separator, anchor = target.partition('#')
            if path_part:
                destination = (file.parent / unquote(path_part)).resolve()
                require(destination.exists(), f'Missing link: {file}: {target}')
            else:
                destination = file
            if file.is_relative_to(SKILL):
                require(destination.is_relative_to(SKILL),
                        f'Skill link escapes standalone package: {file}: {target}')
            if separator:
                target_anchors = local_anchors if destination == file else anchors(destination.read_text())
                require(unquote(anchor) in target_anchors,
                        f'Missing anchor: {file}: {target}')
    require(count > 0, 'No local Markdown links found')
    return len(files), count


def failure_reasons():
    blocks = re.findall(r'```text\n(.*?)```', PROVISIONING, re.DOTALL)
    codes = {
        line.strip() for block in blocks for line in block.splitlines()
        if CODE_LINE_RE.fullmatch(line.strip())
    }
    require(codes, 'domain-provisioning: missing failure_reason enumeration')
    require(codes == BLOCKING_REASONS | REPAIRABLE_REASONS | PENDING_REASONS,
            f'failure_reason enumeration drifted: {sorted(codes)}')
    return codes


FAILURE_REASONS = failure_reasons()


for _code in sorted(FAILURE_REASONS):
    require(f'`{_code}`' in CONTRACT, f'Contract does not document failure_reason: {_code}')
require('domain-provisioning.md#失败原因枚举' in CONTRACT, 'Contract: missing failure_reason pointer')
require('domain-provisioning.md#失败原因枚举' in (REFERENCES / 'deployment.md').read_text(),
        'deployment.md: missing failure_reason pointer')


def string_array(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_build(build, label):
    if build is None:
        return
    fields = {
        'location', 'method', 'os', 'arch', 'node_version', 'package_manager',
        'constraint_sources', 'image_digest', 'last_build_result',
    }
    require(isinstance(build, dict) and fields <= build.keys(), f'{label}: missing build fields')
    require_documented(fields)
    require(build['location'] in (None, 'local', 'ci'), label)
    require(build['method'] in (None, 'native', 'docker'), label)
    for field in fields - {'constraint_sources'}:
        require(build[field] is None or isinstance(build[field], str), f'{label}: invalid {field}')
    require(build['constraint_sources'] is None or string_array(build['constraint_sources']),
            f'{label}: invalid constraint_sources')


def validate_environment(data, label):
    required = {
        'schema_version', 'environment', 'hosting_kind', 'provider', 'service',
        'account_id', 'stable_url', 'supabase_application_id', 'supabase_https_url',
        'current_service_version', 'current_success_version', 'previous_success_version',
        'remote_release_status', 'last_completed_stage', 'updated_at', 'build',
    }
    require(required <= data.keys(), f'{label}: missing environment fields')
    require_documented(required)
    require(type(data['schema_version']) is int and data['schema_version'] in (2, 3), f'{label}: wrong schema version')
    require(data['hosting_kind'] in HOSTING_ROUTES, f'{label}: unsupported hosting route')
    require(data['provider'] == 'huawei-cloud', f'{label}: unsupported provider')
    require(data['service'] == HOSTING_ROUTES[data['hosting_kind']],
            f'{label}: service does not match hosting route')
    require(data['remote_release_status'] in {
        'not_published', 'publishing', 'published', 'failed', 'unknown',
    }, label)
    require(data['last_completed_stage'] in {
        'initialized', 'preflighted', 'built', 'candidate_verified',
        'production_switched', 'production_verified', 'rollback_switched',
        'rollback_verified',
    }, label)
    require('obs_cdn' in data and 'external' not in data, f'{label}: route mismatch')
    route_fields = {
        'profile', 'obs_region', 'rds_region', 'project_id', 'bucket',
        'entry_domain', 'website_hosting', 'cdn_id', 'cdn_cname', 'dns_record_id',
        'certificate_id', 'certificate_expires_at', 'certificate_level',
    }
    require(route_fields <= data['obs_cdn'].keys(), f'{label}: missing route fields')
    require('delegation_scope' not in data['obs_cdn'], f'{label}: private origin delegation removed')
    require_documented(route_fields)
    route = data['obs_cdn']
    require(route['website_hosting'] in {None, 'enabled', 'disabled', 'unknown'},
            f'{label}: invalid website_hosting')
    require(route['certificate_level'] in {None, 'obs', 'cdn'},
            f'{label}: invalid certificate_level')
    if data['hosting_kind'] == 'obs-domain':
        require(route['website_hosting'] == 'enabled', f'{label}: obs-domain needs website hosting')
        require(route['cdn_id'] is None, f'{label}: obs-domain has no acceleration resource')
    if route['certificate_level'] is not None:
        require(route['certificate_id'] is not None, f'{label}: certificate level without certificate')
    require(route['entry_domain'] is None
            or (isinstance(route['entry_domain'], str) and '.' in route['entry_domain']),
            f'{label}: invalid entry_domain')
    validate_build(data['build'], label)
    stage = data['last_completed_stage']
    if stage in {'production_verified', 'rollback_verified'}:
        require(data['remote_release_status'] == 'published', f'{label}: unverified publish state')
        require(data['current_service_version'] is not None, label)
        require(data['current_service_version'] == data['current_success_version'], label)
    if stage in {'production_switched', 'rollback_switched'}:
        require(data['current_service_version'] is not None, f'{label}: missing switched version')
        require(data['remote_release_status'] in {'published', 'failed', 'unknown'}, label)
    return data


def check_environment(path):
    return validate_environment(json.loads(path.read_text()), path.name)


def validate_manifest(data, label):
    required = {
        'schema_version', 'version', 'source_commit', 'built_at', 'build',
        'build_command', 'output_directory', 'lockfile_sha256', 'files', 'routes',
        'entry_backup_path', 'config_backup_path', 'previous_version',
        'refresh_scope',
    }
    require(required <= data.keys(), 'manifest: missing fields')
    require_documented(required)
    require(type(data['schema_version']) is int and data['schema_version'] in (2, 3) and data['files'], 'manifest: invalid version or files')
    require(data['lockfile_sha256'] is None or (isinstance(data['lockfile_sha256'], str)
            and SHA256_RE.fullmatch(data['lockfile_sha256'])), 'manifest: invalid lockfile SHA-256')
    validate_build(data['build'], label)
    require(isinstance(data['files'], list), 'manifest: files must be an array')
    file_fields = {'path', 'size', 'sha256', 'mime', 'cache_control'}
    require_documented(file_fields)
    for item in data['files']:
        require(isinstance(item, dict) and file_fields <= item.keys(), 'manifest: incomplete file entry')
        require(isinstance(item['path'], str) and item['path'].startswith('/'), 'manifest: file path must be absolute URL path')
        require(type(item['size']) is int and item['size'] >= 0, 'manifest: invalid size')
        require(isinstance(item['sha256'], str) and SHA256_RE.fullmatch(item['sha256']), 'manifest: invalid file SHA-256')
    require(isinstance(data['routes'], dict) and {'pages', 'assets', 'api'} <= data['routes'].keys(), 'manifest: incomplete routes')
    require_documented({'pages', 'assets', 'api'})
    for field in ['pages', 'assets', 'api']:
        require(string_array(data['routes'][field]), f'manifest: invalid routes {field}')
    require(string_array(data['refresh_scope']), 'manifest: invalid refresh scope')
    return data


def required_check_names(data):
    required = set(BASE_REQUIRED_CHECKS) if data['schema_version'] == 2 else {'entry', 'assets'}
    if data['schema_version'] == 3:
        for flag, check in [('routes_required', 'routes'), ('cache_required', 'cache')]:
            require(type(data.get(flag)) is bool, f'Missing boolean {flag}')
            if data[flag]:
                required.add(check)
    if data['hosting_kind'] == 'obs-cdn':
        required.add('negative_paths')
    if data['supabase_required']:
        required.add('supabase')
    if data['operation'] in {'update', 'rollback'}:
        required.add('update_rollback')
    return required


def validate_checks(data, label):
    required = {
        'schema_version', 'check_id', 'version', 'checked_at', 'operation',
        'hosting_kind', 'supabase_required', 'overall_status', 'checks',
    }
    require(required <= data.keys(), f'{label}: missing fields')
    require_documented(required)
    require(type(data['schema_version']) is int and data['schema_version'] in (2, 3), f'{label}: wrong schema version')
    require(CHECK_ID_RE.fullmatch(data['check_id']), f'{label}: invalid check_id')
    require(data['operation'] in {'initial_release', 'update', 'rollback', 'recheck'}, label)
    require(data['hosting_kind'] in HOSTING_ROUTES, f'{label}: unsupported hosting route')
    require(isinstance(data['supabase_required'], bool), f'{label}: invalid supabase_required')
    require(data['overall_status'] in {'passed', 'failed', 'partial', 'unknown'}, label)
    require(isinstance(data['checks'], list) and data['checks'], f'{label}: empty results')
    item_fields = {
        'name', 'status', 'target_url', 'request_method', 'final_url', 'access_mode',
        'final_status', 'content_type', 'content_disposition', 'body_summary',
        'browser_status', 'task_id', 'failure_reason', 'reason',
    }
    require_documented(item_fields)
    names = []
    for item in data['checks']:
        require(item_fields <= item.keys(), f'{label}: incomplete check entry')
        require(item['status'] in {'passed', 'failed', 'unverified', 'not_applicable'}, label)
        require(item['access_mode'] in {'normal', 'resolve-diagnostic'}, label)
        if item['status'] == 'passed':
            require(item['reason'] is None, f'{label}: passed item has failure reason')
            require(item['failure_reason'] is None, f'{label}: passed item has failure_reason')
            if item['name'] in {'entry', 'assets', 'domain_probe'}:
                require(item['request_method'] == 'GET', f'{label}: passed evidence requires GET')
                require(type(item['final_status']) is int and 200 <= item['final_status'] < 300,
                        f'{label}: passed evidence requires a successful HTTP status')
                disposition = item['content_disposition']
                require(disposition is None or (isinstance(disposition, str)
                        and disposition.split(';', 1)[0].strip().lower() != 'attachment'),
                        f'{label}: passed evidence cannot be an attachment')
                require(item['browser_status'] == 'passed', f'{label}: browser must pass')
                for field in ['target_url', 'final_url', 'content_type', 'body_summary']:
                    require(isinstance(item[field], str) and item[field].strip(),
                            f'{label}: missing {field} evidence')
        else:
            require(item['reason'], f'{label}: non-passed item needs a reason')
            if item['failure_reason'] is not None:
                require(item['failure_reason'] in FAILURE_REASONS,
                        f'{label}: unknown failure_reason {item["failure_reason"]}')
            if item['name'] == 'domain_probe' and item['status'] in {'failed', 'unverified'}:
                require(item['failure_reason'] in FAILURE_REASONS,
                        f'{label}: probe failure needs a failure_reason')
        names.append(item['name'])
    require(len(names) == len(set(names)), f'{label}: duplicate check name')

    by_name = {item['name']: item for item in data['checks']}
    required_names = required_check_names(data)
    missing = required_names - set(names)
    required_incomplete = any(
        by_name[name]['status'] == 'not_applicable'
        or by_name[name]['access_mode'] != 'normal'
        for name in required_names if name in by_name
    )
    if data['hosting_kind'] == 'obs-domain':
        negative = by_name.get('negative_paths')
        require(negative is None or negative['status'] == 'not_applicable',
                f'{label}: obs-domain error document cannot prove negative paths')
        require(by_name.get('domain_probe', by_name.get('entry', {})).get('status') != 'not_applicable',
                f'{label}: obs-domain still requires the entry probe')
    any_failed = any(item['status'] == 'failed' for item in data['checks'])
    unverified = [item for item in data['checks'] if item['status'] == 'unverified']
    pending_only = bool(unverified) and all(
        item['failure_reason'] in PENDING_REASONS for item in unverified)
    expected = ('failed' if any_failed else
                'partial' if missing or required_incomplete else
                'unknown' if pending_only else
                'partial' if unverified else 'passed')
    require(data['overall_status'] == expected,
            f'{label}: overall status should be {expected}, got {data["overall_status"]}')
    return data


def check_checks(path):
    return validate_checks(json.loads(path.read_text()), path.name)


def check_state_examples(obs):
    failed_candidate = copy.deepcopy(obs)
    failed_candidate.update({
        'current_success_version': 'release-1',
        'previous_success_version': None,
        'remote_release_status': 'failed',
        'last_completed_stage': 'production_switched',
    })
    validate_environment(failed_candidate, 'OBS failed candidate')
    require(failed_candidate['current_service_version'] != failed_candidate['current_success_version'],
            'Failed candidate replaced the last successful version')

    pending = copy.deepcopy(obs)
    pending.update({
        'current_service_version': 'release-1',
        'current_success_version': 'release-2',
        'previous_success_version': 'release-1',
        'remote_release_status': 'published',
        'last_completed_stage': 'rollback_switched',
    })
    validate_environment(pending, 'rollback pending')
    for status in ['failed', 'unknown']:
        case = copy.deepcopy(pending)
        case['remote_release_status'] = status
        validate_environment(case, f'rollback {status}')

    restored = copy.deepcopy(pending)
    restored.update({
        'current_success_version': 'release-1',
        'previous_success_version': 'release-2',
        'last_completed_stage': 'rollback_verified',
    })
    validate_environment(restored, 'rollback verified')
    invalid = copy.deepcopy(pending)
    invalid['last_completed_stage'] = 'rollback_verified'
    expect_invalid(invalid, validate_environment, 'rollback without verification')

    for status in ['failed', 'unknown']:
        before_switch = copy.deepcopy(obs)
        before_switch['remote_release_status'] = status
        before_switch['last_completed_stage'] = 'candidate_verified'
        validate_environment(before_switch, f'before switch {status}')


def check_acceptance_examples(valid):
    for name in ['entry', 'assets']:
        for field, values in {
            'request_method': ['HEAD', None],
            'final_status': [500, 404, 302, True, '200', 200.0, None],
            'content_disposition': ['attachment', ' Attachment; filename="page.html"'],
            'browser_status': ['failed', 'unverified', None],
            'body_summary': [None, ''],
        }.items():
            for value in values:
                case = copy.deepcopy(valid)
                next(item for item in case['checks'] if item['name'] == name)[field] = value
                expect_invalid(case, validate_checks, f'{name}: false pass {field}={value}')
    for status in [403, 404]:
        case = copy.deepcopy(valid)
        next(item for item in case['checks'] if item['name'] == 'negative_paths')['final_status'] = status
        validate_checks(case, 'expected negative path')
    print('PASS GET/status/attachment/browser evidence counterexamples and expected 4xx')

    all_na = copy.deepcopy(valid)
    for item in all_na['checks']:
        item['status'] = 'not_applicable'
        item['reason'] = 'Negative fixture: no acceptance performed'
    all_na['overall_status'] = 'passed'
    expect_invalid(all_na, validate_checks, 'all N/A passed')
    all_na['overall_status'] = 'partial'
    validate_checks(all_na, 'all N/A partial')

    missing = copy.deepcopy(valid)
    missing['checks'] = [item for item in missing['checks'] if item['name'] != 'entry']
    missing['overall_status'] = 'passed'
    expect_invalid(missing, validate_checks, 'missing required entry')
    missing['overall_status'] = 'partial'
    validate_checks(missing, 'missing required entry partial')

    failed = copy.deepcopy(valid)
    failed['checks'][0]['status'] = 'failed'
    failed['checks'][0]['failure_reason'] = 'icp_filing_missing'
    failed['checks'][0]['reason'] = 'Negative fixture: entry failed'
    failed['overall_status'] = 'failed'
    validate_checks(failed, 'failed acceptance')

    unverified = copy.deepcopy(valid)
    unverified['checks'][-1]['status'] = 'unverified'
    unverified['checks'][-1]['reason'] = 'Negative fixture: cache not checked'
    unverified['overall_status'] = 'partial'
    validate_checks(unverified, 'unverified acceptance')

    diagnostic = copy.deepcopy(valid)
    diagnostic['checks'][0]['access_mode'] = 'resolve-diagnostic'
    diagnostic['overall_status'] = 'passed'
    expect_invalid(diagnostic, validate_checks, 'diagnostic-only acceptance')
    diagnostic['overall_status'] = 'partial'
    validate_checks(diagnostic, 'diagnostic partial')

    domain = copy.deepcopy(valid)
    domain['hosting_kind'] = 'obs-domain'
    domain['checks'] = [item for item in domain['checks'] if item['name'] != 'negative_paths']
    domain['overall_status'] = 'passed'
    validate_checks(domain, 'obs-domain without negative paths')
    domain_na = copy.deepcopy(domain)
    negative = copy.deepcopy(valid['checks'][0])
    negative.update({'name': 'negative_paths', 'status': 'not_applicable',
                     'reason': 'Error document falls back to the entry HTML'})
    domain_na['checks'].append(negative)
    validate_checks(copy.deepcopy(domain_na), 'obs-domain negative paths are not applicable')
    skipped_probe = copy.deepcopy(domain)
    next(item for item in skipped_probe['checks'] if item['name'] == 'domain_probe').update(
        {'status': 'not_applicable', 'reason': 'Negative fixture: probe skipped'})
    skipped_probe['overall_status'] = 'partial'
    expect_invalid(skipped_probe, validate_checks, 'obs-domain without an entry probe')
    domain_pass = copy.deepcopy(domain)
    negative_passed = copy.deepcopy(valid['checks'][4])
    domain_pass['checks'].append(negative_passed)
    expect_invalid(domain_pass, validate_checks, 'obs-domain claims negative path proof')

    for reason, expected in [('dns_propagating', 'unknown'), ('dns_record_missing', 'partial')]:
        pending = copy.deepcopy(valid)
        probe = next(item for item in pending['checks'] if item['name'] == 'domain_probe')
        probe.update({'status': 'unverified', 'failure_reason': reason,
                      'reason': 'Negative fixture: entry not ready'})
        pending['overall_status'] = expected
        validate_checks(pending, f'probe {reason} maps to {expected}')
    missing_reason = copy.deepcopy(valid)
    missing_probe = next(item for item in missing_reason['checks'] if item['name'] == 'domain_probe')
    missing_probe.update({'status': 'failed', 'failure_reason': None, 'reason': 'Negative fixture'})
    missing_reason['overall_status'] = 'failed'
    expect_invalid(missing_reason, validate_checks, 'probe failure without failure_reason')

    supabase = copy.deepcopy(valid)
    supabase['supabase_required'] = True
    supabase['overall_status'] = 'passed'
    expect_invalid(supabase, validate_checks, 'missing required Supabase checks')
    supabase['overall_status'] = 'partial'
    validate_checks(supabase, 'incomplete Supabase acceptance')
    supabase_check = copy.deepcopy(supabase['checks'][0])
    supabase_check['name'] = 'supabase'
    supabase['checks'].append(supabase_check)
    supabase['overall_status'] = 'passed'
    validate_checks(supabase, 'complete Supabase acceptance')

    for operation in ['update', 'rollback']:
        operation_event = copy.deepcopy(valid)
        operation_event['operation'] = operation
        operation_event['overall_status'] = 'passed'
        expect_invalid(operation_event, validate_checks, f'{operation} missing update_rollback')
        operation_event['overall_status'] = 'partial'
        validate_checks(operation_event, f'incomplete {operation}')
        operation_check = copy.deepcopy(operation_event['checks'][0])
        operation_check['name'] = 'update_rollback'
        operation_event['checks'].append(operation_check)
        operation_event['overall_status'] = 'passed'
        validate_checks(operation_event, f'complete {operation}')


def check_contract_counterexamples(manifest, environment):
    nullable = copy.deepcopy(manifest)
    nullable['lockfile_sha256'] = None
    nullable['build'] = None
    validate_manifest(nullable, 'reused artifact without lockfile or build')
    for validator, original in [(validate_manifest, manifest), (validate_environment, environment)]:
        source = copy.deepcopy(original)
        source['build'] = copy.deepcopy(manifest['build'])
        case = copy.deepcopy(source)
        case['build'] = {key: None for key in source['build']}
        validator(case, 'unknown build fields')
        for build in [{}, [], {'location': 'ci'}]:
            case = copy.deepcopy(source)
            case['build'] = build
            expect_invalid(case, validator, 'incomplete build')
        for field in source['build']:
            case = copy.deepcopy(source)
            del case['build'][field]
            expect_invalid(case, validator, f'missing build {field}')
        for value in ['package.json', [False], {}]:
            case = copy.deepcopy(source)
            case['build']['constraint_sources'] = value
            expect_invalid(case, validator, 'invalid constraint array')
        for value in [2.0, True, '2']:
            case = copy.deepcopy(source)
            case['schema_version'] = value
            expect_invalid(case, validator, 'non-integer schema version')
    for value in [True, 1.5, -1, '128', None]:
        case = copy.deepcopy(manifest)
        case['files'][0]['size'] = value
        expect_invalid(case, validate_manifest, 'invalid file size')
    for field in ['pages', 'assets', 'api', 'refresh_scope']:
        for value in ['/', [123], {}, None]:
            case = copy.deepcopy(manifest)
            target = case if field == 'refresh_scope' else case['routes']
            target[field] = value
            expect_invalid(case, validate_manifest, f'invalid {field} array')
    print('PASS nullable fields, shared build validation, strict integers and string arrays')


def main():
    skill_text = (SKILL / 'SKILL.md').read_text()
    require(skill_text.startswith('---\n'), 'SKILL.md: missing frontmatter')
    frontmatter = skill_text.split('---', 2)[1]
    require(re.search(r'^name:\s+rds-supabase-frontend$', frontmatter, re.MULTILINE),
            'SKILL.md: wrong name')
    description = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
    require(description, 'SKILL.md: missing description')
    require('references/record-contract.md' in skill_text, 'SKILL.md: missing record contract pointer')
    require('references/domain-provisioning.md' in skill_text, 'SKILL.md: missing domain provisioning pointer')
    require('checks/<版本>/<check_id>.json' in CONTRACT, 'Contract: checks must use event files')
    print('PASS skill frontmatter and record pointers')

    require('仅 `obs-cdn`' in (REFERENCES / 'deployment.md').read_text(),
            'deployment.md: negative paths must be route-scoped')
    require('delegation_scope' not in (REFERENCES / 'hosting.md').read_text(),
            'hosting.md: private origin delegation must be gone')
    print('PASS route wording, removed evidence files and route-scoped acceptance')

    ui = (SKILL / 'agents' / 'openai.yaml').read_text()
    for field in ['display_name', 'short_description', 'default_prompt']:
        require(re.search(rf'^  {field}:\s*".+"$', ui, re.MULTILINE), f'openai.yaml: missing {field}')
    print('PASS UI metadata fields')

    markdown_files, link_count = check_links()
    print(f'PASS {link_count} local links and anchors across {markdown_files} Markdown files')
    print('PASS standalone skill links stay inside the package')

    obs = check_environment(EXAMPLES / 'environment.obs.json')
    require(obs['last_completed_stage'] == 'production_verified', 'OBS example: wrong success stage')
    print('PASS OBS environment example and verified-state invariants')
    domain = check_environment(EXAMPLES / 'environment.domain.json')
    require(domain['hosting_kind'] == 'obs-domain', 'Domain example: wrong route')
    require(domain['obs_cdn']['website_hosting'] == 'enabled', 'Domain example: needs website hosting')
    broken_domain = copy.deepcopy(domain)
    broken_domain['obs_cdn']['website_hosting'] = 'disabled'
    expect_invalid(broken_domain, validate_environment, 'obs-domain without website hosting')
    leaky_domain = copy.deepcopy(domain)
    leaky_domain['obs_cdn']['cdn_id'] = 'cdn-should-not-exist'
    expect_invalid(leaky_domain, validate_environment, 'obs-domain with acceleration resource')
    print('PASS obs-domain environment example and its route invariants')
    unsupported = copy.deepcopy(obs)
    unsupported.update({
        'hosting_kind': 'external',
        'provider': 'legacy-provider',
        'service': 'legacy-static-hosting',
        'external': {'project_id': 'legacy-project', 'production_deployment_id': 'legacy-release'},
    })
    del unsupported['obs_cdn']
    unchanged = copy.deepcopy(unsupported)
    expect_invalid(unsupported, validate_environment, 'Unsupported historical route')
    require(unsupported == unchanged, 'Unsupported history was rewritten')
    print('PASS unsupported hosting history is rejected without rewriting it')
    check_state_examples(obs)
    print('PASS OBS candidate failure, rollback pending/failed/unknown/success and pre-switch states')

    legacy = json.loads((EXAMPLES / 'environment.legacy.json').read_text())
    require('schema_version' not in legacy, 'Legacy example must remain unversioned')
    require({'bucket', 'cdn_id'} <= legacy.keys(), 'Legacy example: missing route clues')
    print('PASS legacy example does not invent v2 fields')

    manifest = json.loads((EXAMPLES / 'manifest.example.json').read_text())
    validate_manifest(manifest, 'manifest')
    check_contract_counterexamples(manifest, obs)
    print('PASS manifest example, file hashes, routes, and required fields')
    valid_checks = check_checks(EXAMPLES / 'checks.example.json')
    check_acceptance_examples(valid_checks)
    check_checks(EXAMPLES / 'checks.v3.json')
    v3 = copy.deepcopy(valid_checks)
    v3.update(schema_version=3, hosting_kind='obs-domain', operation='initial_release', supabase_required=False, routes_required=False, cache_required=False)
    v3['checks'] = [item for item in v3['checks'] if item['name'] in {'entry', 'assets'}]
    validate_checks(v3, 'v3 minimal')
    v3['routes_required'] = True
    expect_invalid(v3, validate_checks, 'v3 missing conditional routes')
    print('PASS required coverage and passed/failed/partial/N/A/diagnostic/update cases')


if __name__ == '__main__':
    main()
