"""Implemented operations only; unsupported actions stay explicit."""
import os
import asyncio
import re
import time
from mcp_server_supabase.service.jobs import job_result
from mcp_server_supabase.failures import RecoveryError
from mcp_server_supabase.service.plans import PlanStore, fingerprint
from mcp_server_supabase.service.network_contracts import ssl_followup
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.client.rest import segment
from mcp_server_supabase.client.sdk_core import configured_client
from mcp_server_supabase.service.contracts import (api_key_query, application_detail,
                                                   application_metadata, application_query,
                                                   auth_config_detail, key_metadata, ssl_body,
                                                   accepted_job)

ROOT = "/v3/{project}/ai-application"
# Recovery categories that prove the request was definitively rejected (never
# accepted): a clean 4xx from the gateway/backend. Everything else (transport,
# 429/5xx, unparseable responses) leaves the write result genuinely unknown.
_DEFINITE_REJECTIONS = {"invalid_request", "authentication", "permission", "not_found", "state_conflict"}


def safe(value, depth=0):
    if depth > 8:
        return "[truncated]"
    if isinstance(value, dict):
        return {k: safe(v, depth+1) for k,v in value.items() if not any(s in k.lower() for s in ("password", "pwd", "secret", "token", "api_key")) and k.lower() not in ("ak", "sk")}
    if isinstance(value, list):
        return [safe(v, depth+1) for v in value[:100]]
    if isinstance(value, str):
        return value[:2000]
    return value


class Operations:
    def __init__(self, client=None, plans=None):
        self.client = client or configured_client()
        self.plans = plans or PlanStore()

    def app(self, application_id):
        return ROOT + "/" + segment(application_id) + "/supabase"

    def intent_digest(self, method, path, body):
        return fingerprint({"endpoint":self.client.endpoint,"project":self.client.project,
                            "credential":fingerprint(self.client.token if self.client.token is not None else os.getenv("HUAWEICLOUD_AUTH_TOKEN", "")),
                            "method":method,"path":path,"body":body})

    async def deliver_key(self,application_id,key_id,delivery_ref,confirm=False,plan_id=None):
        from mcp_server_supabase.service.key_delivery import deliver
        return await deliver(self,application_id,key_id,delivery_ref,confirm,plan_id)

    async def delete_application(self, application_id, delete_managed_instance=None, confirm=False, plan_id=None):
        """Delete one Supabase application, optionally together with its managed PG instance.

        The instance choice is mandatory: delete_managed_instance must be an explicit True
        (both deletions are submitted together, two job ids) or False (application only,
        the instance is retained and keeps billing). All managed-instance guardrails -
        live binding verification, no-shared-reference sweep, pre-delete inventory read -
        run BEFORE either deletion is submitted, while the application is still readable.
        """
        application_id = segment(application_id)
        if type(delete_managed_instance) is not bool:
            raise McpToolError('MCP_INVALID_ARGS',
                               'delete_managed_instance is required: pass True to delete the managed PG instance together with the application, or False to keep it',
                               hint='Ask the user which outcome they want; this choice cannot be defaulted.')
        path = self.app(application_id)
        digest = self.intent_digest('DELETE', path, {'delete_managed_instance': delete_managed_instance})
        if delete_managed_instance:
            notices = {'completion_verified': False,
                       'warnings': ['The application and its managed PostgreSQL instance are deleted simultaneously; the instance deletion destroys all its data irreversibly - export first if anything must survive.',
                                    'Both deletions run as separate cloud tasks with separate job ids; either may fail independently - track both.',
                                    'Pay-per-use instances only: yearly/monthly instances are rejected here and must be unsubscribed in the console.'],
                       'follow_up': 'Track both job ids with show_operation_job_status, then re-read the application list and the instance inventory to confirm removal.'}
        else:
            notices = {'completion_verified': False,
                       'warnings': ['Deleting this application interrupts its services; the managed PostgreSQL instance is retained and may continue to incur charges.',
                                    'Deletion is not automatically reversible.'],
                       'follow_up': 'Track the job with show_operation_job_status and re-read the application list to confirm removal.'}
        if not confirm:
            return {'status': 'confirmation_required', 'execution': 'not_executed',
                    'application_id': application_id, 'action': 'delete',
                    'delete_managed_instance': delete_managed_instance,
                    'resource_path': path, **notices, **self.plans.issue(digest)}
        if os.getenv('SUPABASE_ENABLE_WRITES') != 'true' or os.getenv('HUAWEICLOUD_MCP_READ_ONLY', 'false').lower() == 'true':
            raise McpToolError('MCP_READ_ONLY', 'Writes are disabled')
        # Read the real target immediately before mutation. Unknown/active states fail closed.
        _, target = await self.client.request('GET', path)
        if target.get('id') != application_id or target.get('status') != 'normal' or target.get('current_actions'):
            raise McpToolError('MCP_GUARDRAIL_BLOCKED', 'Target is not demonstrably ready for mutation')
        from huaweicloud_mcp_core.guardrails import assert_not_protected
        assert_not_protected(target)
        instance_id = None
        if delete_managed_instance:
            managed = target.get('managed_instance')
            if not isinstance(managed, dict) or not managed.get('id'):
                raise McpToolError('MCP_GUARDRAIL_BLOCKED', 'This application has no verifiable managed instance',
                                   hint='Delete the application alone (delete_managed_instance=False), or verify the instance in the console.')
            instance_id = segment(managed['id'])
            assert_not_protected({'id': instance_id, 'name': managed.get('name')})
            await self._assert_instance_unshared(instance_id, application_id)
            _, listing = await self.client.request('GET', '/v3/{project}/instances', query={'id': instance_id})
            rows = listing.get('instances') if isinstance(listing, dict) else None
            if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict) or rows[0].get('id') != instance_id:
                raise McpToolError('MCP_NOT_FOUND', 'Instance not found or not unique in the inventory',
                                   hint='A missing instance does not prove deletion; inspect the console before any retry.')
        self.plans.claim(plan_id, digest)
        unknown = RecoveryError('MCP_SDK_ERROR', 'Deletion result unknown', 'submission_unknown',
                                'Query the operation task and the target resources directly; do not resubmit - previews and the recorded intent are single-use.', plan_id)
        try:
            status, data = await self.client.request('DELETE', path)
        except RecoveryError as error:
            if error.recovery.get('category') in _DEFINITE_REJECTIONS:
                self.plans.finish(plan_id, 'failed'); raise
            self.plans.finish(plan_id, 'unknown'); raise unknown from None
        except McpToolError:
            self.plans.finish(plan_id, 'failed'); raise
        except BaseException:
            self.plans.finish(plan_id, 'unknown'); raise unknown from None
        try:
            result = accepted_job(status, data)
            job_id = result['job_id']
        except BaseException:
            self.plans.finish(plan_id, 'unknown'); raise unknown from None
        instance_job_id = None
        if delete_managed_instance:
            try:
                _, payload = await self.client.request('DELETE', '/v3/{project}/instances/' + instance_id)
                instance_job_id = payload.get('job_id') if isinstance(payload, dict) else None
                if not isinstance(instance_job_id, str) or not 1 <= len(instance_job_id) <= 128:
                    raise ValueError()
            except BaseException:
                # Application deletion was accepted; the instance submission is unknown.
                self.plans.finish(plan_id, 'accepted', job_id)
                raise RecoveryError('MCP_SDK_ERROR', 'Instance deletion result unknown', 'submission_unknown',
                                    'The application deletion was accepted; the instance deletion result is unknown. '
                                    'Re-verify the instance inventory before any retry - never resubmit blindly.', plan_id) from None
        self.plans.finish(plan_id, 'accepted', job_id)
        result = {**result, **notices, 'plan_id': plan_id}
        if delete_managed_instance:
            result['instance_id'] = instance_id
            result['instance_job_id'] = instance_job_id
        return result

    async def creation_progress(self, application_id, application_job_id,
                                instance_job_id=None, instance_id=None):
        """One-call creation progress analysis for either creation scenario.

        Existing-instance scenario (no instance ids): checks the application inventory
        (filtered by application id) and the application creation job. New-instance
        scenario (both instance ids): checks the instance job FIRST - the application
        is only created after the instance succeeds, so its job is queried only then -
        then the application inventory and the application job.
        """
        application_id = segment(application_id); application_job_id = segment(application_job_id)
        new_instance = instance_job_id is not None or instance_id is not None
        if new_instance and (instance_job_id is None or instance_id is None):
            raise McpToolError('MCP_INVALID_ARGS',
                               'The new-instance scenario requires both instance_job_id and instance_id, or neither')
        instance_job_id = segment(instance_job_id) if instance_job_id else None
        instance_id = segment(instance_id) if instance_id else None

        _, listing = await self.client.request('GET', ROOT + '/applications',
                                               query=application_query(1, 0, application_id=application_id))
        rows = listing.get('data') if isinstance(listing, dict) else None
        app_row = rows[0] if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict) else None

        instance = None
        if new_instance:
            instance_job = await self.job(instance_job_id)
            instance = {'instance_id': instance_id, 'job_id': instance_job_id,
                        'job_status': instance_job['task_status']}
            if instance_job['task_status'] != 'completed':
                # The application has not started yet (or the instance failed): its job
                # does not exist at this stage - do not query it.
                app_job_status = 'not_started' if instance_job['task_status'] == 'running' else None
                phase = 'instance_creating' if instance_job['task_status'] == 'running' else 'failed'
                return self._progress_result(phase, 'new_instance', app_row, app_job_status, instance,
                                             failed_stage='instance' if phase == 'failed' else None)

        app_job = await self.job(application_job_id)
        phase = {'completed': 'succeeded', 'failed': 'failed'}.get(app_job['task_status'], 'application_creating')
        failed_stage = 'application' if phase == 'failed' else None
        if app_row is not None and app_row.get('status') == 'normal' and app_job['task_status'] == 'completed':
            phase = 'succeeded'
        return self._progress_result(phase, 'new_instance' if new_instance else 'existing_instance',
                                     app_row, app_job['task_status'], instance, failed_stage=failed_stage)

    def _progress_result(self, phase, scenario, app_row, app_job_status, instance, failed_stage=None):
        application = {'application_id': app_row['id'] if app_row else None,
                       'application_status': app_row.get('status') if app_row else 'not_created',
                       'job_status': app_job_status}
        summaries = {
            'succeeded': 'Creation completed: the application is ready. Complete post-creation steps (public access, key delivery) if pending.',
            'application_creating': 'The application creation task is running.' if scenario == 'existing_instance'
                                    else 'The managed instance is ready; the application creation task is running.',
            'instance_creating': 'The managed instance is still creating; the application has not started yet - wait and query again.',
            'failed': 'Creation failed; check the failed stage and the task details before any retry.',
        }
        return {'phase': phase, 'scenario': scenario, 'application': application,
                'instance': instance, 'failed_stage': failed_stage,
                'summary': summaries[phase],
                'next_action': 'Query again after a reasonable interval; do not resubmit the creation.' if phase in ('instance_creating', 'application_creating')
                               else 'On failure, inspect the task details; a retry needs a fresh preview and confirmation.',
                'completion_verified': phase == 'succeeded'}

    async def delete_managed_instance(self, application_id, instance_id, confirm=False, plan_id=None):
        # Native RDS instance deletion (DELETE /v3/{project}/instances/{id}). The live
        # application detail is the only authoritative binding source: the named
        # instance must be that application's managed_instance, and no other
        # application may reference it.
        application_id = segment(application_id); instance_id = segment(instance_id)
        path = '/v3/{project}/instances/' + instance_id
        digest = self.intent_digest('DELETE', path, {'application_id': application_id})
        notices = {'warnings': ['Deleting the managed PostgreSQL instance destroys all its data irreversibly; export first if anything must survive.',
                                'If the Supabase application still exists it loses its database - delete the application first when possible; the backend may reject a bound instance.',
                                'Pay-per-use instances only: yearly/monthly instances are rejected here and must be unsubscribed in the console.'],
                   'completion_verified': False,
                   'follow_up': 'Track the returned job with show_operation_job_status; a completed job still requires re-reading the instance inventory to confirm removal. This record remains non-replayable.'}
        if not confirm:
            return {'status': 'confirmation_required', 'execution': 'not_executed',
                    'application_id': application_id, 'instance_id': instance_id,
                    'action': 'delete_instance', 'resource_path': path, **notices, **self.plans.issue(digest)}
        if os.getenv('SUPABASE_ENABLE_WRITES') != 'true' or os.getenv('HUAWEICLOUD_MCP_READ_ONLY', 'false').lower() == 'true':
            raise McpToolError('MCP_READ_ONLY', 'Writes are disabled')
        _, target = await self.client.request('GET', self.app(application_id))
        if not isinstance(target, dict) or target.get('id') != application_id:
            raise McpToolError('MCP_NOT_FOUND', 'Application not found; the managed-instance binding cannot be verified',
                               hint='This tool only deletes instances whose binding to the named application is verifiable now. For an already-deleted application, verify residuals and delete the instance from the console.')
        from huaweicloud_mcp_core.guardrails import assert_not_protected
        assert_not_protected(target)
        managed = target.get('managed_instance')
        if not isinstance(managed, dict) or managed.get('id') != instance_id:
            raise McpToolError('MCP_GUARDRAIL_BLOCKED', 'Instance is not managed by this application',
                               hint='Read the application detail and pass its managed_instance.id exactly.')
        assert_not_protected({'id': instance_id, 'name': managed.get('name')})
        await self._assert_instance_unshared(instance_id, application_id)
        _, listing = await self.client.request('GET', '/v3/{project}/instances', query={'id': instance_id})
        rows = listing.get('instances') if isinstance(listing, dict) else None
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict) or rows[0].get('id') != instance_id:
            raise McpToolError('MCP_NOT_FOUND', 'Instance not found or not unique in the inventory',
                               hint='A missing instance does not prove deletion; inspect the console before any retry.')
        self.plans.claim(plan_id, digest)
        unknown = RecoveryError('MCP_SDK_ERROR', 'Instance deletion result unknown', 'submission_unknown',
                                'Inspect the plan and the instance inventory; never blindly repeat the deletion.', plan_id)
        try:
            status, data = await self.client.request('DELETE', path)
        except RecoveryError as error:
            if error.recovery.get('category') in _DEFINITE_REJECTIONS:
                self.plans.finish(plan_id, 'failed'); raise
            self.plans.finish(plan_id, 'unknown'); raise unknown from None
        except McpToolError:
            self.plans.finish(plan_id, 'failed'); raise
        except BaseException:
            self.plans.finish(plan_id, 'unknown'); raise unknown from None
        try:
            job_id = data.get('job_id') if isinstance(data, dict) else None
            if status != 200 or not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', job_id):
                raise ValueError()
            self.plans.finish(plan_id, 'accepted', job_id)
            return {'status': 'accepted', 'job_id': job_id, 'application_id': application_id,
                    'instance_id': instance_id, 'instance_name': rows[0].get('name'),
                    'plan_id': plan_id, **notices}
        except BaseException:
            self.plans.finish(plan_id, 'unknown'); raise unknown from None

    async def _assert_instance_unshared(self, instance_id, application_id):
        seen = 0
        for page in range(5):
            _, listing = await self.client.request('GET', ROOT + '/applications', query=application_query(100, page * 100))
            rows = listing.get('data') if isinstance(listing, dict) else None
            total = listing.get('total_count') if isinstance(listing, dict) else None
            if not isinstance(rows, list) or not isinstance(total, int):
                raise McpToolError('MCP_SDK_ERROR', 'Application inventory unreadable; instance sharing cannot be verified')
            seen += len(rows)
            for row in rows:
                if not isinstance(row, dict) or row.get('id') == application_id:
                    continue
                managed = row.get('managed_instance')
                if isinstance(managed, dict) and managed.get('id') == instance_id:
                    raise McpToolError('MCP_GUARDRAIL_BLOCKED', 'Another application also references this instance',
                                       hint='Resolve the sharing first; deleting now would interrupt the other application.')
            if seen >= total or not rows:
                break
        else:
            raise McpToolError('MCP_GUARDRAIL_BLOCKED', 'Too many applications to verify instance sharing',
                               hint='Verify manually that no other application references the instance before retrying.')

    async def create_reference(self,request_ref,confirm=False,plan_id=None):
        from mcp_server_supabase.service.request_refs import load_request,preview_request
        from mcp_server_supabase.service.creation import validate_creation
        body=validate_creation(load_request(request_ref))
        path=ROOT+'/supabases';digest=self.intent_digest('POST',path,body)
        notices={'completion_verified':False,'warnings':[
            'Review application and PG credentials, network, ownership, quota and ongoing charges before confirming.',
            'Single or Ha mode; postPaid or prepaid (period_type is the string month/year, period_num 1-9 months or 1-3 years). Prepaid returns an order paid via the order tools - no automatic payment.',
            'Structural validation only: backend password, version, capacity and sale policies remain authoritative.'],
            'follow_up':'Observe application job and any PG job separately, query both resources and validate login. Partial success never authorizes automatic resource deletion.'}
        if not confirm:
            return {'status':'confirmation_required','execution':'not_executed','changes':preview_request(body),**notices,**self.plans.issue(digest)}
        if os.getenv('SUPABASE_ENABLE_WRITES')!='true' or os.getenv('HUAWEICLOUD_MCP_READ_ONLY','false').lower()=='true':
            raise McpToolError('MCP_READ_ONLY','Writes are disabled')
        self.plans.claim(plan_id,digest)
        unknown=RecoveryError('MCP_SDK_ERROR','Creation result unknown','submission_unknown',
                              'Inspect the plan and application/PG inventories. An unexpected order must be reconciled manually; do not pay, replay or auto-delete.',plan_id)
        try:
            status,data=await self.client.request('POST',path,body=body)
        except RecoveryError as error:
            if error.recovery.get('category') in _DEFINITE_REJECTIONS:
                self.plans.finish(plan_id,'failed');raise
            self.plans.finish(plan_id,'unknown');raise unknown from None
        except McpToolError:
            self.plans.finish(plan_id,'failed');raise
        except BaseException:
            self.plans.finish(plan_id,'unknown');raise unknown from None
        try:
            if data.get('job_id'):
                result=accepted_job(status,data)
                result['application_id']=segment(data.get('application_id'))
                for key in ('instance_id','instance_job_id'):
                    if data.get(key):result[key]=segment(data[key])
                if data.get('order_id'):result['order_id']=segment(data['order_id'])
                self.plans.finish(plan_id,'accepted',result['job_id'])
                return {**result,**notices,'plan_id':plan_id}
            if data.get('order_id'):
                # Prepaid flow: the backend answers with an order, not a job. The
                # order was created (accepted); payment follows the guarded order tools.
                result={'status':'order_created','order_id':segment(data['order_id']),'job_id':None}
                self.plans.finish(plan_id,'accepted',None)
                return {**result,**notices,'warnings':notices['warnings']+[
                    'A prepaid order was created; it must be paid before the resource is provisioned.',
                    'Query the order with get_supabase_order, obtain approval for the exact amount and currency, then pay with pay_supabase_order (or cancel with cancel_supabase_order if abandoned).',
                    'Resource creation starts after payment - re-verify resources once a job appears.'],
                    'plan_id':plan_id}
            raise ValueError()
        except BaseException:
            self.plans.finish(plan_id,'unknown');raise unknown from None

    async def mutate_reference(self, application_id, action, request_ref, confirm=False, plan_id=None):
        from mcp_server_supabase.service.request_refs import load_request, validate_request
        body=validate_request(action,load_request(request_ref))
        return await self.mutate(application_id,action,body,confirm,plan_id)

    async def creation_candidates(self, kind, az_code=None, mode=None):
        if kind=='flavors':
            az_code=segment(az_code)
            if mode not in ('Single','Ha'):
                raise McpToolError('MCP_INVALID_ARGS','mode must be Single or Ha')
            path=ROOT+'/supabase/flavors';query={'az_code':az_code,'mode':mode}
        elif kind=='manageable':
            path=ROOT+'/manageable-instances';query={'application_type':'supabase'}
        else:
            raise McpToolError('MCP_INVALID_ARGS','Unsupported creation discovery')
        _,data=await self.client.request('GET',path,query=query)
        return {'data':safe(data),'creation_ready':False,
                'note':'Live candidates only, capped at 100 entries per array. This is not a complete inventory, price quote or validated creation plan.'}

    async def read(self, kind, application_id=None, limit=10, offset=0, **key_filters):
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise McpToolError("MCP_INVALID_ARGS", "Invalid pagination")
        query = None
        if kind == "applications":
            path = ROOT + "/applications"
            try:
                query = application_query(limit, offset, application_id=application_id, **key_filters)
            except (ValueError, TypeError):
                raise McpToolError("MCP_INVALID_ARGS", "Invalid application filters",
                                   hint="Use the supported filter and sort values.") from None
        else:
            path = self.app(application_id)
            if kind == "keys":
                path += "/api-keys"
                try:
                    query = api_key_query(limit, offset, **key_filters)
                except (ValueError, TypeError):
                    raise McpToolError("MCP_INVALID_ARGS", "Invalid key filters",
                                       hint="Use the supported metadata filter values.") from None
            elif kind == "auth":
                path += "/auth-config"
            elif kind != "application":
                raise McpToolError("MCP_INVALID_ARGS", "Unsupported query")
        _, data = await self.client.request("GET", path, query=query)
        if kind == "applications":
            try:
                data = application_metadata(data)
            except ValueError:
                raise McpToolError("MCP_SDK_ERROR", "Unrecognized application metadata response",
                                   hint="Verify the endpoint response contract before continuing.") from None
        if kind == "application":
            try:
                data = application_detail(data)
            except ValueError:
                raise McpToolError("MCP_SDK_ERROR", "Unrecognized application detail response",
                                   hint="Verify the endpoint response contract before continuing.") from None
        if kind == "auth":
            try:
                data = auth_config_detail(data)
            except ValueError:
                raise McpToolError("MCP_SDK_ERROR", "Unrecognized auth configuration response",
                                   hint="Verify the endpoint response contract before continuing.") from None
        if kind == "application":
            return {"data": safe(data),
                    "note": "Access address assembly: scheme from enable_ssl (true->https, "
                            "false->http), host from public_ip (public; null when no EIP is bound) "
                            "or private_ip/traffic_vip (internal), port from port. "
                            "Secret fields excluded; nested objects bounded."}
        if kind == "auth":
            return {"data": safe(data),
                    "note": "Baseline for update_supabase_auth_config previews and accepted-plan "
                            "reconciliation. Secrets (SMTP credentials, OAuth client secrets) are "
                            "excluded; identifiers (oauth_client_id, smtp_user) remain. Empty "
                            "strings mean not configured."}
        if kind == "keys":
            try:
                data = key_metadata(data)
            except ValueError:
                raise McpToolError("MCP_SDK_ERROR", "Unrecognized key metadata response",
                                   hint="Verify the endpoint response contract before continuing.") from None
        return {"data":safe(data), "limit":limit, "offset":offset, "note":"Output capped at 100 entries per array; use pagination. Secret fields excluded."}

    async def job(self, job_id):
        job_id = segment(job_id)
        _, data = await self.client.request("GET", "/v3/{project}/jobs", query={"id":job_id})
        return job_result(data, job_id)

    async def wait_job(self, job_id, max_attempts=3, interval_seconds=2, sleep=asyncio.sleep):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 10 or type(interval_seconds) is not int or not 1 <= interval_seconds <= 5:
            raise McpToolError("MCP_INVALID_ARGS", "Use 1-10 observations and a 1-5 second interval")
        job_id = segment(job_id)
        deadline = time.monotonic() + 50
        result = job_result({}, job_id)
        attempts = 0
        exhausted = False
        for index in range(max_attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                exhausted = True
                break
            attempts += 1
            try:
                result = await asyncio.wait_for(self.job(job_id), timeout=remaining)
            except (asyncio.TimeoutError, TimeoutError):
                exhausted = True
                break
            if result['task_status'] != 'running':
                break
            if index == max_attempts - 1:
                exhausted = True
                break
            await sleep(min(interval_seconds, max(0, deadline - time.monotonic())))
        return {**result, 'attempts':attempts, 'observation_exhausted':exhausted,
                'cloud_writes_performed':False}

    async def mutate(self, application_id, action, body, confirm=False, plan_id=None):
        path = self.app(application_id)
        reset_key_id = None
        if action == "ssl":
            try:
                body = ssl_body(**body)
            except (ValueError, TypeError):
                raise McpToolError("MCP_INVALID_ARGS", "Invalid SSL arguments") from None
            method, suffix = "POST", "/switch-ssl"
        elif action == "eip":
            if type(body.get("is_bind")) is not bool:
                raise McpToolError("MCP_INVALID_ARGS", "is_bind must be boolean")
            if body["is_bind"]:
                import ipaddress
                segment(body.get("public_ip_id"))
                try:
                    ipaddress.IPv4Address(body.get("public_ip_address"))
                except Exception:
                    raise McpToolError("MCP_INVALID_ARGS", "A valid public IPv4 address is required") from None
            else:
                if body.get("public_ip_id") is not None or body.get("public_ip_address") is not None:
                    raise McpToolError("MCP_INVALID_ARGS", "Unbinding must not include binding parameters",
                                       hint="Use is_bind=false with null or omitted EIP ID and address.")
                body = {"is_bind":False}
            method, suffix = "PUT", "/public-eip"
        elif action in ("password", "storage", "auth_config"):
            from mcp_server_supabase.service.request_refs import validate_request
            body=validate_request(action,body)
            method, suffix = "PUT", {"password":"/password","storage":"/storage","auth_config":"/auth-config"}[action]
        elif action == "delete":
            method, suffix, body = "DELETE", "", None
        elif action == "reset_key":
            reset_key_id = segment(body["key_id"])
            method, suffix = "PUT", "/api-key/" + reset_key_id + "/reset"
            body = None
        elif action == "auth_flags":
            if not body or any(k not in ("enable_account_sign_up", "enable_anonymous_users") or type(v) is not bool for k,v in body.items()):
                raise McpToolError("MCP_INVALID_ARGS", "Only explicit registration boolean changes supported")
            method, suffix = "PUT", "/auth-config"
        else:
            raise McpToolError("MCP_INVALID_ARGS", "Unsupported mutation")
        notices = ssl_followup(body["enable_ssl"]) if action == "ssl" else {}
        if action == "delete":
            notices = {"warnings":["Deleting this application interrupts its services; PG is retained and may continue to incur charges.",
                                   "Deletion is not automatically reversible; no PG cascade is performed."]}
        if action == "eip":
            notices = {"warnings":["Public connectivity changes may interrupt clients; binding does not prove end-to-end access.",
                                   "EIP charges and release are separate; unbinding does not release the EIP or guarantee billing stops."]}
        if action == "auth_flags":
            notices = {"warnings":["Auth changes may briefly interrupt application functions; prefer a low-traffic window."]}
        if action == "reset_key":
            notices = {
                "warnings":["Existing clients can lose access after the asynchronous reset succeeds."],
                "follow_up":[
                    "After agent success, backend atomically marks the old key deleted and a new key normal.",
                    "Query the job and refresh metadata; key transition does not prove later recovery steps completed.",
                    "Do not use the old key ID to retrieve the new value; correlate the new record before trusted delivery.",
                    "Update downstream credentials through a trusted channel; never return plaintext to the model.",
                ],
                "completion_verified":False,
            }
        if action in ("password","storage","auth_config"):
            notices={"warnings":["Review all changed fields and dependent applications; secrets are supplied locally.",
                                 "Disabling a provider may clear its nested configuration; omitted Auth fields remain unchanged.",
                                 "First Storage enable requires SK; omission on an enabled component retains its SK only with the same AK."],
                     "validation_scope":"Known structural contract only; backend policy and live acceptance remain required."}
        digest = self.intent_digest(method, path+suffix, body)
        from mcp_server_supabase.service.request_refs import preview_request
        preview_body=preview_request(body)
        if not confirm:
            return {"status":"confirmation_required", "application_id":application_id, "action":action, "changes":preview_body, "resource_path":path+suffix, "execution":"not_executed", **notices, **self.plans.issue(digest)}
        if os.getenv("SUPABASE_ENABLE_WRITES") != "true" or os.getenv("HUAWEICLOUD_MCP_READ_ONLY", "false").lower() == "true":
            raise McpToolError("MCP_READ_ONLY", "Writes are disabled")
        # Read the real target immediately before mutation. Unknown/active states fail closed.
        _, target = await self.client.request("GET", path)
        if target.get("id") != application_id or target.get("status") != "normal" or target.get("current_actions"):
            raise McpToolError("MCP_GUARDRAIL_BLOCKED", "Target is not demonstrably ready for mutation")
        from huaweicloud_mcp_core.guardrails import assert_not_protected
        assert_not_protected(target)
        if reset_key_id is not None:
            # Scope the lookup to this application and exact ID. Backend auth remains authoritative.
            _, metadata = await self.client.request("GET", path + "/api-keys",
                                                   query=api_key_query(key_id=reset_key_id))
            try:
                page = key_metadata(metadata)
                records = page["data"]
                ready = (page["total_count"] == 1 and len(records) == 1
                         and records[0].get("id") == reset_key_id
                         and records[0].get("status") == "normal")
            except ValueError:
                ready = False
            if not ready:
                raise McpToolError("MCP_GUARDRAIL_BLOCKED", "Key is not demonstrably normal in this application",
                                   hint="Refresh key metadata and verify its ID and state before resetting.")
        if action=='storage' and body['enabled'] and 'sk' not in body:
            current=target.get('storage_component')
            if not isinstance(current,dict) or current.get('enabled') is not True or current.get('ak')!=body['ak']:
                raise McpToolError('MCP_GUARDRAIL_BLOCKED','Omitted SK requires already enabled Storage with the same AK',
                                   hint='For first enable or credential identity change, provision complete credentials locally and preview again.')
        self.plans.claim(plan_id, digest)
        unknown=RecoveryError("MCP_SDK_ERROR", "Write result unknown", "submission_unknown",
                              "Query the operation task and the target resource directly; do not resubmit - previews and the recorded intent are single-use.", plan_id)
        try:
            status, data = await self.client.request(method, path + suffix, body=body)
        except RecoveryError as error:
            if error.recovery.get('category') in _DEFINITE_REJECTIONS:
                self.plans.finish(plan_id, "failed");raise
            self.plans.finish(plan_id, "unknown");raise unknown from None
        except McpToolError:
            self.plans.finish(plan_id, "failed");raise
        except BaseException:
            self.plans.finish(plan_id, "unknown");raise unknown from None
        try:
            result = accepted_job(status, data)
            self.plans.finish(plan_id, "accepted", result["job_id"])
            return {**result, **notices, "plan_id":plan_id}
        except BaseException:
            self.plans.finish(plan_id, "unknown");raise unknown from None
