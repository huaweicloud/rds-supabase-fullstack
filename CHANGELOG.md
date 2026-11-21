# Changelog

All notable user-visible changes are recorded here. This project follows
semantic versioning.

## [Unreleased]

### Changed

- SUPABASE_URL configuration normalized to the parameterized gateway form
  `http(s)://{rds_supabase_eip}:{rds_supabase_port}` (server **0.4.4**, skill
  `rds-supabase-mcp` **2.7.5**): every MCP client template now shows the
  parameterized URL followed by an explanation of both parameters
  ({rds_supabase_eip} = the EIP bound to the application, i.e. the
  application detail's public_ip; {rds_supabase_port} = the fixed 8443 Kong
  gateway port; http(s) follows the SSL switch) and a separate filled
  example (http://123.60.101.251:8443). Applied across README.md /
  README_zh.md quick start + client config + env tables,
  examples/mcp-client-stdio.json, and the skill's install.md /
  mcp-installation-guide.md.

- Data-plane MCP metadata and docs accuracy pass (server **0.4.3**, skill
  `rds-supabase-mcp` **2.7.4**):
  - pyproject summary and both READMEs now say data-plane (not
    "management"), distilled to the actual scenarios: SQL execution via the
    hardened RPC, schema inspection, auth-user management, storage and
    security checks behind three-tier guardrails
  - removed internal-decision narratives from user-facing Overview/Features
    ("38 of 43 upstream tools", "five tools removed in 0.2.0", "removed in
    0.4.0", "auto-deploy was removed") - READMEs now describe current
    behavior only; derivation credit stays in License/NOTICE
  - fixed a stale zh claim that auto-deploy of the execute_sql function
    still exists, and stale "service-role or direct connection" wording
    (direct is not supported); unified the WRITE-tool count to 7 (was 8/9
    in different places); deduplicated the doubled deploy paragraph
  - the Chinese link on the PyPI landing page now points at the absolute
    GitHub URL (relative README_zh.md links 404 on pypi.org)
  - all SUPABASE_URL examples switched to the RDS Supabase gateway shape
    `<protocol>://<rds-supabase-ip>:8443` with a filled example
    (`http://123.60.101.251:8443`), protocol-follows-SSL notes and the fixed
    8443 port, across READMEs, examples/mcp-client-stdio.json and the
    skill's install references
  - skill SKILL.md overview rewritten as current-capability statements
    (no upstream-diff framing); unavailable-tools row reworded to present
    tense

- uvx-first installation everywhere for the data-plane MCP (server 0.4.2,
  skill `rds-supabase-mcp` 2.7.3), mirroring the upstream
  mcp_huaweicloud_gaussdb README pattern now that the package is live on
  PyPI: `uvx mcp-server-huaweicloud-rds-supabase` with no --from/--subdirectory
  git scaffolding. Replaced across server README.md/README_zh.md (plus a
  gaussdb-style Installation section: uvx / pip / source-workspace
  channels), examples/mcp-client-stdio.json, and the skill's
  references/install.md + references/mcp-installation-guide.md (PyPI source
  note added; the source-workspace channel kept for development with the
  project-level isolation rule intact).

### Added

- Data-plane MCP (`mcp_server_rds_supabase`) prepared for standalone PyPI
  release as **mcp-server-huaweicloud-rds-supabase 0.4.1** (name verified
  free; both mcp-server-* and mcp-huaweicloud-* spellings were unclaimed,
  the mcp-server prefix chosen for MCP-ecosystem discoverability, entry
  point identical to the package name):
  - pyproject: explicit `pyasn1>=0.6.4` dependency - the local
    tool.uv override cannot propagate into published metadata, and
    huaweicloudsdkcore<=3.1.218 transitively pins pyasn1<=0.6.3 (3 DoS
    CVEs); the floor keeps the fix on the PyPI install path
  - pyproject: sdist converged via only-include (src + sql + READMEs;
    tests/examples/Dockerfile/uv.lock excluded), wheel unchanged
  - .github/workflows/publish-mcp-server-rds-supabase.yml: tag-triggered
    (mcp-server-rds-supabase-v*) release pipeline - uv sync + 241-case
    test gate, uv build, twine check, then `uv publish --trusted-publishing
    automatic --check-url` (Trusted Publishing, zero tokens; idempotent
    on re-runs). First release requires the PyPI pending publisher to be
    configured by the account owner
  - upstream core check: local libs/huaweicloud_mcp_core is byte-identical
    to the upstream HEAD (src + pyproject; upstream "Bump dependency
    versions" only refreshed dev uv.locks), version 1.0.0 on both sides
    - no sync needed, PyPI dependency chain intact

### Changed

- mgr-mcp INSTALL.md gains an installation-discipline block for the
  installing agent (mgr-mcp 2.16.1): the conversation request cap is
  32MB and accumulated screenshots/attachments abort the install with
  `request too large`; agents must stay on terminal commands, avoid
  browser/screenshot reads of the repo pages, avoid pulling the whole
  repo into the conversation, and skip large text files (uv.lock /
  CHANGELOG.md / docs/) the install never depends on. Prompted by a
  field report where a one-line install triggered the 32MB error on a
  browser-equipped agent - the repo itself ships no raster images
  (verified: 6.5MB of tracked text, largest object a 0.5MB lock file),
  so the accumulation came from page screenshots, not repo content.

- Skills aligned with the "华为云基础云服务 Skill 开发与管理规范 v2.0.0"
  (GitCode developer-skill discussion #13) under a capability-freeze
  discipline: a pre-change baseline (headings / 64 table tools / 38
  acceptance K-items / 11 scenario titles / links / version lines) was
  captured and must survive the change set. Applied, with the six-skill
  suite and the mgr skill passing all their own gates:
  - scripts/validate_skills.py upgraded first (gate-before-content):
    top-level `version`/`tags` allowed and enforced (semver, <=5 tags,
    top-level vs metadata anti-drift), A6 CHANGELOG baseline switched to
    the top-level version, description <=1024, per-package file count
    <=40 with a documented deviation registry (postgres-best-practices
    45 - its 38 rule files are the symptom-routing capability itself),
    46-entry extension whitelist scan, docstring/FORBIDDEN_FILES mismatch
    fixed
  - Tier 0 hygiene: .DS_Store / __pycache__ / *.pyc removed and ignored;
    bare LICENSE files renamed LICENSE.txt (web-build, usage,
    postgres-best-practices) with README/INSTALL links synced
  - All skills: frontmatter gains top-level version + tags (<=5), a
    description trailing line of English trigger words (all under 1024
    chars; existing Chinese trigger semantics untouched), overview
    architecture notes and 3-5 typical use cases distilled from existing
    content; write-capable skills (mcp, web-build, frontend,
    function-graph) gain a 安全硬约束与责任边界 chapter consolidating
    existing red lines (positioned before 前置条件); function-graph's
    nine references mentions upgraded to when-to-read semantics
  - mgr-mcp: security chapter renamed 安全硬约束与责任边界 and moved
    before 前置条件; the 58-tool command roster moved verbatim to the new
    references/commands.md (SKILL.md keeps a six-group map with
    when-to-read pointers); frontmatter metadata block replaced by
    top-level version 2.16.0 aligned with the prose declaration (fixing
    the stale 2.5.0); skill-lint grows a frontmatter-vs-prose version
    drift guard and expects five reference files; the stale
    '>= 0.4.0a8' test assertion replaced by a live-declaration mutation
    plus a new frontmatter-drift regression case
  - version increments per the spec's modify-must-bump rule:
    `rds-supabase-mgr-mcp` 2.16.0, `rds-supabase-mcp` 2.7.2,
    `rds-supabase-web-build` 0.12.4, `rds-supabase-frontend` 0.2.6,
    `rds-supabase-usage` 0.2.5, `rds-supabase-postgres-best-practices`
    0.3.2, `rds-supabase-function-graph` 0.1.3
  - explicit exemptions recorded (independent repo, not the GitCode
    developer-skill org): huawei-cloud-* directory renaming, SKILL.md
    body English conversion, quality-cli / VOD telemetry injection,
    three-level product-domain restructure, references renaming to the
    four-piece set - each deferred until an official-repo contribution
    event; usage's self-contained design and postgres-best-practices'
    38-file rule library kept as deliberate deviations

### Fixed

- `create_supabase_eip` surfaced `MCP_SDK_ERROR 'EIP write result unknown'`
  although the EIP was actually created (issue #24). The old catch-all folded
  four cloud end-states into one opaque unknown: a lost transport response,
  an unparsable creation response, a failed USAGE_FOR tag write (EIP created,
  untagged), and a request that never reached the cloud. Fixed in
  `mcp_server_rds_supabase_mgr` 0.4.0a66:
  - before every creation submission the service snapshots the visible EIP
    inventory (reconciliation baseline); on an ambiguous submission it
    reconciles by baseline set-difference plus attribute matching (alias /
    bandwidth size / charge mode - the fixed default alias collides across
    auto-created EIPs, so attributes alone cannot attribute)
  - exactly one new match returns the real `created` result with
    `reconciliation.verified` and re-applies the tag; no new match reports
    recovery category `verified_absent` with the plan marked failed (a fresh
    preview may retry); several new matches report `ambiguous_candidates`
    listing ids without auto-claiming; only an unreadable reconciliation
    (or an unavailable baseline) falls back to `submission_unknown`, now
    naming both failure codes
  - a failed tag write degrades to a `tag_warning` on the created result
    (the tag is advisory; provenance also lives in the resource ledger)
  - "never blindly repeat" preserved: CreatePublicip stays non-idempotent
    and every plan single-use
  - tests: reconciliation confirmed (transport loss + unparseable response),
    verified-absent, ambiguous candidates, unreadable list, unavailable
    baseline, tag-failure warning, baseline snapshot in the happy paths
  - follow-up candidate noted: the same reconcile-on-unknown pattern applies
    to the KooCLI delete tools (verify absence); not in this change set
  - skill 2.15.0 (server >= 0.4.0a66): scenario 4, README zh/en, acceptance K38

- `create_supabase_with_new_instance` / `create_supabase_link_exist_instance`
  demanded `security_group_id` in the request file while the docs promised it was
  injected automatically, the error named neither the expected location nor the
  right field, and a hand-filled value was silently overwritten by the
  auto-provisioned groups (issue #25). Fixed in `mcp_server_rds_supabase_mgr`
  0.4.0a65 by making absence the only valid state: `validate_creation` grows an
  orchestrated mode (used by both scenario tools) that REJECTS the request file
  when `security_group_id` appears at the top level or under `managed_instance` -
  with a hint to delete the field and to rebind own groups through
  `change_supabase_security_group` after creation - while the raw strict mode
  (service-level `create_reference`) keeps the field mandatory and now reports
  missing/unexpected fields with their full parent path
  (`managed_instance.security_group_id`), so callers never have to probe
  positions one by one. Contract migration note: earlier rounds accepted a
  top-level value, later rounds required `managed_instance.security_group_id` -
  both are now REJECTED for the scenario tools; the field is injected at
  confirmation as originally documented. `fields()` error messages carry the
  parent path everywhere. Skill 2.14.0 (server >= 0.4.0a65): SKILL scenarios
  1-2, scenarios.md request example, local-requests contract, README zh/en and
  acceptance K37 updated; the OBS bucket field is unaffected (bucket_name stays
  optional and user-provided buckets are reused, not overwritten).

- `bind_supabase_eip` rejected applications that `list_supabase_applications`
  returned, while `change_supabase_eip` accepted the same ID (issue #23).
  Three stacked defects, all fixed in `mcp_server_rds_supabase_mgr` 0.4.0a64:
  the ownership check consulted an ID-filtered inventory query and its
  catch-all swallowed every read failure (backend 4xx/5xx, contract mismatch)
  into a misleading "not managed by this environment" rejection - it now reads
  the authoritative application detail endpoint (the same source
  `change_supabase_eip` uses), maps a definitive 404 to MCP_NOT_FOUND with the
  verification source named in the hint, and propagates every other read
  failure unchanged; the submission channel was the instance-level RDS
  AttachEip API (`/v3/{project}/instances/{instance_id}/public-ip`) addressed
  with an application ID - a resource level no application ID can ever match -
  and now submits through the application-level public-eip endpoint
  (SwitchSupabaseApplicationEipBind) like the change tool; and the tool lacked
  the state guardrails of its sibling. New guardrails per the intended
  scenario split: bind is for first-time binding only (running applications
  with no in-flight actions and no EIP bound; an already-bound application is
  directed to `change_supabase_eip`), guards run before the plan claim, and
  the accepted response carries the job id with follow-up guidance. Skill
  2.13.0 (server >= 0.4.0a64): scenario 4, command table and README zh/en
  updated; `show_supabase_creation_progress` and
  `list_supabase_applications(application_id=...)` keep the filtered query
  (no masquerading path there; probe confirmed the parameters are accepted).

### Added

- Repo-wide wording rectification across all skills and the mgr server
  (`mcp_server_rds_supabase_mgr` 0.4.0a63). Full-scan audit of every skill's
  SKILL.md, references, INSTALL.md, README, showcase and rendered SVG plus
  the server's user-facing strings, removing jargon, colloquial connectors
  and command-tone phrasing in favor of plain formal Chinese:
  账本 -> 执行记录; 落盘 -> 写入/保存; 兜底 -> 例外/后备/保障(按语境);
  打标 -> 添加标签; 拉起 -> 启动; 干净收尾 -> 彻底收尾; 话术 -> 提示;
  硬试/硬删 -> 强行重试/强行删除; 顺带 -> 同时; 不许 -> 不得;
  点名 -> 指明; 怎么 -> 如何; 走场景X/走单项/走KooCLI -> 按场景X处理/
  使用单项工具/经KooCLI; 一句话安装 -> 单命令安装; 其实际/真的 ->
  其现有/实际; 对账(config sense) -> 逐项核对. Business-vocabulary usage kept
  (e.g. 对账/补单 as e-commerce timing-job examples). Stale tool counts fixed
  (53 -> 58 in seven places incl. the timeline SVG and showcase). Enforcement
  made permanent: the mgr skill lint blacklist extends to the new banned terms
  (plus 一句话 for its own tree) and scripts/validate_skills.py now fails on
  the core jargon list across every skill's markdown. Skill versions:
  `rds-supabase-mgr-mcp` 2.12.0 (server >= 0.4.0a63), `rds-supabase-mcp`
  2.7.1, `rds-supabase-web-build` 0.12.3, `rds-supabase-frontend` 0.2.5,
  `rds-supabase-usage` 0.2.4, `rds-supabase-function-graph` 0.1.2,
  `rds-supabase-postgres-best-practices` 0.3.1.
- `mcp_server_rds_supabase_mgr` 0.4.0a62 - scenario 7 (resource cleanup and
  retention) plus dashboard-credential and workspace-folder hardening.
  Full-flow protection mechanism: every create/reuse/bind/modify step records
  into a local SQLite resource ledger (EIP auto-created vs reused, OBS bucket
  auto-created vs integrated, the two dedicated security groups, the
  application-to-managed-instance mapping, the instance choice at deletion,
  security-group rebinding with detach of replaced auto-created groups);
  recording is advisory (faults surface as record_warnings, never fail a
  finished cloud write) and always injected by the tool layer. New READ tool
  show_supabase_residuals: the record-scoped, live-verified residual inventory
  across four categories with per-item recommendations, the high-risk
  storage-billing reminder when a bucket is retained, and the database
  security group blocked while the managed instance is retained. New
  DANGEROUS tool cleanup_supabase_residuals: the one-click batch cleanup with
  four mandatory boolean category switches, one confirmation and one plan for
  the whole set; per-item guard re-checks tolerate blocked items and
  per-item failures never abort the other categories; cleaned items update
  the record and every outcome is reported. clean_supabase_obs_ws now deletes
  the application-ID folder itself, not only its contents: the bucket-root
  directory named exactly the application ID is emptied and then the folder
  marker removed (a missing marker is tolerated), so the folder disappears
  entirely while the bucket and every other directory stay untouched.
  Dashboard-login hardening after a live test could not log in: creation
  previews warn when a password carries characters beyond
  letters/digits/-/_ (transcription, IME and URL/JSON escaping hazards - the
  recommended recipe is 12-16 chars of upper+lower+digits, no symbols needed
  for the cloud rule), and every creation preview/acceptance carries a
  dashboard_credential note stating the fixed login user (supabase), that the
  password is exactly the local request file's create.password, and that the
  creation path never generates or alters it; the existed-instance preview
  also drops a stale prepaid-order warning (the creation path produces no
  orders). User-facing wording switched from the jargon term to 资源记录
  (local resource record) across messages, response keys (ledger_warning(s)
  -> record_warning(s)) and docs, enforced by the skill jargon lint. Tool
  count 56 -> 58. Skills: `rds-supabase-mgr-mcp` 2.11.0 (server >=
  0.4.0a62; scenario 11 summary pointing at the server README scenario 7,
  password recipe and write-back-verify discipline, credential delivery in
  scenario 1, acceptance case K36) and `rds-supabase-web-build` 0.12.2 (the
  app-card table now shows the dashboard login account and password for
  newly created applications, sourced from the creation request file).
  Tests: 588 passed + 168 subtests (new: ledger suite, residual inventory,
  batch cleanup full/blocked/replay, folder-marker deletion, password
  advisory and credential-note cases).
- `mcp_server_rds_supabase_mgr` 0.4.0a61 - post-deletion resource cleanup
  family: three DANGEROUS tools for business-driven explicit use or automatic
  linked triggering after a Supabase application is deleted.
  delete_supabase_eip (KooCLI EIP ShowPublicIp + DeletePublicip) reads the
  EIP before submission to verify identity, optionally cross-checks the
  caller-recorded address, and sweeps the full application inventory to
  block an EIP still referenced by any live application's public address;
  bound EIPs are rejected by the backend itself (unbind first); deletion
  stops the IP retention fee immediately. clean_supabase_obs_ws (KooCLI
  embedded obsutil) clears exactly one application's OBS data directory -
  the bucket-root folder named exactly the application ID
  (obs://<bucket>/<application_id>/): the bucket and every other directory
  stay untouched, the deletion prefix is built solely from the validated
  bucket name and the in32-format application ID (no caller-supplied path
  fragment can widen the scope), a still-live application ID is blocked,
  and a missing or empty folder returns already_clean idempotently.
  delete_supabase_obs removes the bucket itself after every referencing
  application is gone: live-application storage_component references are
  blocked, non-empty buckets are blocked (clear per-application directories
  first, review anything else manually), and a missing bucket returns
  already_absent idempotently. All three follow the plan-ledger two-phase
  discipline; every guard runs immediately before the destructive call.
  Tool count 53 -> 56 (test_protocol updated); capabilities list extended.
  Skill `rds-supabase-mgr-mcp` 2.10.0 (server requirement >= 0.4.0a61):
  scenario-10 residual-disposal channel rewritten around the new tools,
  command table +3 rows, acceptance cases K33-K35, README zh/en updated
  (tool table, scenario-5 supplement). Tests: 566 passed + 168 subtests.
- `mcp_server_rds_supabase_mgr` 0.4.0a60 - deletion relaxes its status gate
  and instance billing follows the official on-demand contract.
  delete_supabase_application no longer requires the normal status: stopped
  and removed applications are deletable - only in-flight current_actions
  block the mutation (the guard message explains the relaxation). Direct
  instance deletion is now reserved for on-demand instances behind a
  billing-mode gate that runs before submission on both deletion tools
  (delete_supabase_application cascade branch and
  delete_supabase_managed_instance): yearly/monthly (prePaid) instances -
  including prepaid PG instances linked via the attach-existing scenario -
  cannot be deleted through the API; the cascade is rejected as a whole
  (the application stays readable, the hint steers to re-issuing with
  delete_managed_instance=False and unsubscribing console-side), and a
  charge_info that cannot be verified fails closed. The
  managed PG instance on the create-with-new-instance path is now on-demand
  only: prePaid and its period fields are removed from charge_info (unknown
  fields are rejected, prePaid fails with an explicit on-demand-only
  message), the creation path can no longer produce a payable order, and
  the order tools remain for console-side legacy orders. The billing rules
  are shown to the user on every creation surface - preview warnings,
  discovery charge_info field, arrangement module and the skill guide
  carry the fee composition (instance flavor + storage mandatory, backup
  beyond the 100% free allowance, optional public bandwidth / cross-region
  backup; per-second billing settled hourly from successful creation until
  deletion) with the official pricing doc linked
  (price-rds-pg/rds_00_0005). Dynamic pricing was investigated: KooCLI's
  RDS service has no pricing APIs (348 operations, none rating-related)
  and its BSS service is unsupported; the BSS SDK rating API rejects all
  probed RDS catalog-code combinations ("billing item does not exist") -
  dynamic pricing stays a future enhancement. Skill
  `rds-supabase-mgr-mcp` 2.9.0 (server requirement >= 0.4.0a60). Tests:
  542 passed + 168 subtests.
- `mcp_server_rds_supabase` 0.4.1 - execute_sql now documents its two
  typical batch uses in the tool description: deploying init.sql migration
  batches and executing their companion cleanup scripts for deletion
  scenarios (on user request, single transaction with automatic rollback).
  Skill `rds-supabase-mcp` 2.7.0 adds the matching discipline: whenever an
  init.sql migration script is finalized, strongly recommend producing the
  companion cleanup script (cleanup.sql) at the same time - reverse-order
  teardown, IF EXISTS for repeatability, covering tables/sequences/
  functions/triggers/policies/roles while platform built-ins stay
  untouchable - archived in pairs and executed on demand in deletion
  scenarios at a user-specified time, never auto-run at deploy. New
  init-sql-guide section 7, a verification recipe in verification-method,
  and README/SKILL/related-tools touch-ups. Tests: 241 passed (93.92%
  coverage).
- `mcp_server_rds_supabase_mgr` 0.4.0a59 - new-EIP billing follows the
  official on-demand contract. The purchase path is fixed to on-demand
  billing (prepaid periods are removed from create_supabase_eip along
  with its order flow), and the billing method becomes an explicit user
  choice with no default: bandwidth-based (peak x duration, unlimited
  traffic - best for steady traffic; tiered pricing with the official
  6Mbps ~0.565 CNY/hour example) or traffic-based (outbound GB only,
  the bandwidth acts as a peak speed cap - best for low or bursty
  traffic; official example 0.64 CNY/GB, per-EIP peak capped at
  300 Mbps with a 5 Gbps regional account-wide cap per the 2026-04
  official rule). The bandwidth size stays a user decision
  (bandwidth 5-1000 / traffic 5-300 peak cap). Every purchase surface
  shows the fee schedule before confirmation: bandwidth/traffic fee
  plus the IP retention fee (official example 0.02 CNY/hour while
  unbound and unreleased), with the scenario and pricing docs linked
  (eip_billing_0005 / eip_billing_0007) and the official pricing page
  as the exact-price source. The arrangement module, creation-flow
  automation note, EIP visual block and both READMEs carry the same
  contract. Skill `rds-supabase-mgr-mcp` 2.8.0 (server requirement
  >= 0.4.0a59). Tests: 534 passed + 168 subtests.
- `mcp_server_rds_supabase_mgr` 0.4.0a58 - the EIP bandwidth charge becomes
  a forced, explicit notice. The missing-bandwidth guard now states the
  bandwidth is a chargeable item (fixed-bandwidth billing, continuous from
  creation until release) and carries the fee reference; the purchase
  preview gains a structured `billing` block (charge item, unit price
  model, reference magnitude ~0.06 CNY/Mbps/hour with the official pricing
  calculator link, billing window) and the first warning spells out the
  charge and echoes the user-confirmed size; the arrangement's
  size_decision and the creation-flow EIP follow-up note carry the same
  charge notice. Skill guidance (scenario 4, command table, a new
  contract-table row for EIP bandwidth billing) instructs asking the user
  and stating the charge before purchasing. Dynamic rating was
  investigated live: the BSS ListOnDemandResourceRatings API exists in the
  already-installed SDK, but five catalog-code combinations were rejected
  ("billing item does not exist") and the SDK ships no product-catalog
  discovery API - dynamic pricing stays a future enhancement; the official
  pricing calculator URL is referenced everywhere instead. Skill
  `rds-supabase-mgr-mcp` 2.7.1 (server requirement >= 0.4.0a58).
- `mcp_server_rds_supabase_mgr` 0.4.0a57 - the new-EIP bandwidth is a user
  decision, not a default. `create_supabase_eip` drops the silent 300 Mbps
  default: `bandwidth_size_mbps` becomes optional-with-no-default and the
  new-purchase branch rejects the call when it is missing ("ask the user"),
  while the idle-reuse path stays bandwidth-free as before. The arrangement's
  public-access module replaces `recommended_size_mbps: 300` with an explicit
  `size_decision` ("user decides, 5-1000, no default"), the post-creation
  flow and the creation-flow EIP automation carry a user-decision
  placeholder, the EIP visual renders the bandwidth row as "用户决策" for
  the new shape (legacy payloads keep rendering their explicit size), and
  preview recommendations state "大小由用户决策（无默认推荐）". READMEs and
  the skill guide (Scenario 1 step 2, Scenario 4, command table,
  scenarios.md) instruct asking the user before purchasing. Skill
  `rds-supabase-mgr-mcp` 2.7.0 (server requirement >= 0.4.0a57).
- `mcp_server_rds_supabase_mgr` 0.4.0a56 - storage integration after
  creation is supported, not forbidden - and it is proactive. The
  "cannot be enabled after creation" claim is corrected everywhere it
  appeared (arrangement decision points, storage-option notes,
  new-bucket warnings, README/README_en, both skill guides and the
  web-build workflow stages), and the new discipline is
  integrate-on-identification: the moment a file-storage need is
  recognized, the integration flow runs immediately (existing-bucket
  list with private buckets first, or a new bucket, then
  `update_supabase_storage` with full credentials) - "can integrate
  later" is a fallback, never a reason to defer. In rds-supabase-web-build,
  when an existing Supabase application is selected and the requirement
  phase flagged storage, the agent must proactively probe that
  application's storage integration state (the storage component in
  `show_supabase_application`) and trigger the automatic OBS integration
  flow on the spot when it is absent. The guidance stays a strong
  recommendation to enable storage at creation time when the business
  scenario confirms it, to avoid omissions and longer flows. Skill
  `rds-supabase-mgr-mcp` 2.6.1, `rds-supabase-web-build` 0.12.1.
- Skill install guides: the ZIP channel now lands the download directly
  in the workspace project root and never asks the user for a download
  directory - real-world testing showed agents prompting for one, so
  the only interactive step left is the install-location choice; the
  agent resolves the skill target from that choice on its own. The
  rds-supabase-web-build guide now mandates the full skill family: the
  seven skills under skills/huaweicloud-supabase/ must be installed
  together in one pass with no skipping - repeated `--skill` flags are
  verified live against the skills CLI, methods B/C copy the whole
  category, and the install check fails on any missing directory. The
  mode-comparison report is renamed USER_GUIDE_REPORT.md -> showcase.md
  and marked as demo material that does not participate in skill
  operation.
- All seven skill INSTALL guides add a proactive environment probe before
  the download-method choice: `node --version` tests the npx skills add
  prerequisite and `git ls-remote` live-tests GitHub reachability over
  git (real-world environments with public-network restrictions on git
  fail exactly here). One probe run decides the channel - Node >= 22.20
  picks method A, git reachability picks B, and a double failure switches
  decisively to the ZIP channel (HTTPS 443 download plus automatic
  extraction, immune to the git restriction) with no retries of the dead
  paths; execution-time failures still degrade once A -> B -> C but skip
  channels the probe already ruled out.
- `rds-supabase-web-build` skill v0.12.0: the user-guide report gains a
  participant catalog and an end-to-end timeline. New section 7 catalogs
  the six specialist skills and both MCP planes (management plane 53
  tools / data plane 38 tools) with their roles and join points; new
  section 8 renders a swimlane timeline (assets/skill-mcp-timeline.svg)
  mapping every participant onto the nine pipeline stages with
  breakpoint markers, both loops (the step-7 L0 repair circuit back to
  step 5, the step-8 callback loop) and the inter-stage artifact chain
  (credential hand-off, init.sql batch, build artifacts, OBS upload,
  callback, launch delivery). The layout is machine-verified
  overlap-free against real font metrics (106 texts, zero overlaps,
  zero spills). Stale "29 tools" counts for the management-plane MCP
  are corrected to 53 across SKILL.md and INSTALL.md.
- `mcp_server_rds_supabase_mgr` 0.4.0a55 - account-aware enterprise-project
  selection. `discover_db_instance_for_create` (newly-instance scenario only)
  now queries the live enterprise-project list via KooCLI
  `EPS ListEnterpriseProject` (pinned to the global-service region cn-north-4):
  EPS-enabled accounts pick from the returned projects - the default is the
  project named "default", whatever its real ID - while query failures or empty
  lists degrade to an omittable field instead of blocking the flow.
  `managed_instance.enterprise_project_id` is no longer required by the creation
  contract: personal accounts omit it entirely and the backend assigns
  enterprise-project placement. The hard-coded "0" default is gone from
  baselines, fixtures, new-bucket specs and docs; the arrangement baseline
  carries the field only when the discovery step actually returned one.
- `mcp_server_rds_supabase_mgr` 0.4.0a54 - `npx skills add` becomes the
  primary skill-installation channel, verified end to end: the Vercel
  open-source skills CLI (npm `skills`, 75+ agents including OpenCode
  and Claude Code) discovers all eight skills in this repository
  through its standard catalog walk (`skills/<category>/<name>/
  SKILL.md`, three levels deep - the existing layout fits without any
  change), and a live `npx skills add huaweicloud/rds-supabase-
  fullstack --skill rds-supabase-usage -a opencode -y` run installed
  the complete skill folder with a skills-lock.json pinning the source
  commit. All seven skill INSTALL.md files restructure their
  installation section: method A is now `npx skills add` (primary,
  recommended - with the --skill/-a/-g flag guidance, lock-file and
  update/remove lifecycle), git clone becomes method B (fallback for
  CLI failure, missing Node.js >= 22.20, or exact copy control), and
  the ZIP archive becomes method C (network escape hatch); the stale
  "CLI/package-manager installation forbidden" statements - written
  when the skills were not yet on a CLI-servable channel - are
  removed everywhere. All fourteen skill READMEs (Chinese and the
  newly added English mirrors) gain a one-line quick-install command
  in their installation section.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a53 - concise tool descriptions,
  feature-overview restructure, and English READMEs for all seven skills:
  - All 53 MCP tool descriptions (the docstrings agents preview in
    tools/list) are rewritten to a uniform concise register: a one-line
    functional positioning, the strongest one or two constraints (two-
    phase confirmation, full-replacement semantics, strict managed-
    instance resolution, application-password scope, /0 rejection, tag
    gates, amount double-equality), and the special return semantics
    (job_id tracking, key values never in conversation). Average length
    drops from 431 to about 86 characters; parameter enumerations,
    value ranges, flow steps and billing detail now live only in
    preview responses and documentation.
  - The MCP READMEs' feature chapter becomes a feature overview:
    each capability group is split into focused sub-points - the
    arrangement entry separates baseline/flavor-interaction/disk
    labels/discovery families; the managed-instance entry separates
    detail query, strict resolution, stop-billing boundaries and the
    start-ordering rule - with zero fidelity loss. English mirror in
    step.
  - English READMEs (README_en.md) are added for all seven Supabase
    skills (mgr-mcp, mcp, frontend, function-graph, usage,
    postgres-best-practices, web-build): professional technical
    translation, structure mirrored one-to-one, terminology aligned
    with the codebase (two-phase confirmation, managed instance,
    local request file, checkpoint resumption), facts verified
    against the Chinese sources, each opening with an
    English | 中文 language switch.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a52 - documentation correction:
  the feature lists and the skill's applicable-scenario list are
  restored to their detailed narrative form (they had been wrongly
  compressed in 0.4.0a51) and now integrate every capability added
  through a47-a51 in full detail: grouped flavor discovery with the
  split two-question interaction and same-spec default in the
  arrangement entry, security-group rebinding with its three targets
  and full-replacement semantics in the network entry, and the
  password scope guard in the authentication entry. The
  twenty-character conciseness discipline the project intended is
  applied where it belongs: the scenario column of the available-tools
  tables - all 53 rows in the MCP README, its English mirror (noun
  phrases of at most six words) and the skill's core-command tables
  are compressed to at most twenty characters per cell, keeping the
  tables scannable while the detailed constraints remain in the
  business-scenario chapters.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a51 - security-group set tool,
  password scope guard and doc-wide operations consolidation
  (52 -> 53 tools, skill v2.5.0):
  - `change_supabase_security_group` (DANGEROUS, preview/confirm;
    SetSecurityGroup): one tool, three mutually exclusive targets -
    the application itself (addressed by its in32 id through the
    instance endpoint, same pattern as AttachEip), the application's
    managed instance (always resolved from managed_instance, never a
    bare instance id), or an attachable instance (must appear in the
    manageable-candidates list - serving the attach-existing-PG
    creation scenario's pre-creation group preparation). Multiple
    group ids are supported with full-replacement semantics: the
    submitted list is the final list, omitted groups are detached,
    and the preview impact states that losing 8443/5432 rules makes
    the application unreachable. Official constraint surfaced:
    creating, upgrading, resizing, and user create/delete states
    reject the call. The response's workflowId is tracked through
    show_operation_job_status like any other job id.
  - `change_supabase_application_password` scope guard: the tool
    docstring, preview warnings and all docs now state explicitly
    that only the application login password (dashboard user
    supabase) is changed - the managed instance's root login
    password is out of scope for this tool and is managed through
    the console's instance administration; sessions on the old
    password stop working once the change lands.
  - Documentation consolidation across the MCP READMEs and the
    skill (v2.5.0, server >= 0.4.0a51): the feature lists are
    rewritten as 18 core-point entries of at most 20 Chinese
    characters each (English mirrored as noun phrases), now covering
    every capability added through a47-a51 - grouped flavor
    discovery, SSL certificate purchase, application lifecycle,
    managed-instance operations and security-group rebinding. A new
    business-scenario chapter "application and managed-instance
    operations" aggregates start/stop/restart, security-group
    rebinding, password change and key reset under one rhythm:
    verify status and in-flight actions, preview/confirm, track the
    job to terminal state, recheck. The skill's scenario eight gains
    the same operations overview; acceptance reaches K32; stale
    38-tool counts in the skill's README/INSTALL are corrected.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a50 - managed-instance lifecycle
  tools (48 -> 52 tools, skill v2.4.0): four new tools for the managed
  PostgreSQL instance, all keyed by application_id - the target
  instance is always resolved from the application's managed_instance
  field, never a bare instance_id, so independent database instances
  cannot be touched by mistake; single instance per operation.
  `show_supabase_managed_instance` (READ) queries the live simplified
  detail (engine, instance_status with Chinese semantics, spec, disk,
  AZs, current actions) with billing and 15-day auto-start notes.
  `stop_supabase_managed_instance` (DANGEROUS, preview/confirm;
  StopInstance): on-demand instances with SSD-class disks only; VM
  stops billing while EIP/storage/backup continue; a stopped instance
  auto-starts in the next maintenance window after fifteen days;
  deleted-while-stopped skips the recycle bin; read replicas stop with
  the primary; server guardrail requires instance_status normal with
  no current actions. `start_supabase_managed_instance`
  (StartupInstance): shutdown instances only; replicas start with the
  primary; resource exhaustion may fail the start. `restart_supabase_
  managed_instance` (StartInstanceRestartAction): normal, unfrozen,
  action-free instances only; the instance is unavailable during
  restart. All three return job_id with the established
  show_operation_job_status follow-up discipline; docs state the
  ordering rule - start the instance before the application, and
  stopping the instance leaves the application failing requests.
  README/README_en (52-tool table) and the skill (v2.4.0, server >=
  0.4.0a50; scenario-eight rows, managed-instance contract row, K29-
  K30) updated in step; capabilities now list both lifecycle scopes.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a49 - application lifecycle tools
  and a universal job-tracking discipline (45 -> 48 tools, skill v2.3.0):
  - Three new DANGEROUS tools with preview/confirm: `start_supabase_`
    `application` (async start; only a stopped application can start;
    starting does not start the managed instance, whose state must be
    normal or the start may fail), `stop_supabase_application` (async
    stop; the managed instance keeps running and billing; functions
    unavailable while stopped; prefer low-traffic windows) and
    `restart_supabase_application` (async restart; running-state
    applications only - a stopped one must be started first, abnormal
    state may fail; internal components restart with brief
    interruption and cache release). All three call the official
    StartSupabaseApplication/StopSupabaseApplication/RestartSupabase-
    Application endpoints (POST /v3/{project}/ai-application/{id}/
    start|stop|restart, no /supabase segment, no body, 202 + job_id)
    and enforce server-side status guardrails before submission:
    stop/restart require status normal with no current actions, start
    requires a non-normal status with no current actions.
  - Universal job-tracking discipline: every operation tool whose
    response carries a job_id now returns an explicit job_follow_up
    instructing show_operation_job_status (or wait_operation_job_
    complete) until terminal state, then a resource recheck -
    application creation excepted, which keeps its dedicated
    show_supabase_creation_progress. Tool docstrings state the same.
  - README/README_en (48-tool table, lifecycle section) and the skill
    (v2.3.0, server >= 0.4.0a49: scenario-eight rows, lifecycle
    parameter-contract row, troubleshooting discipline, acceptance
    K27-K28) updated in step.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a48 - SSL certificates in MCP and
  independent SSL/EIP modules in the arrangement (43 -> 45 tools, skill
  v2.2.0):
  - Two new SCM SSL-certificate tools. KooCLI's SCM service (SSL
    certificate management, distinct from CCM private certificates)
    supports the full public-certificate lifecycle, and both tools run
    through it with the region pinned to cn-north-4 (SCM is a global
    service; only ap-southeast-1/cn-north-4/my-kualalumpur-1 are
    accepted). `list_ssl_certificates` (READ) inventories the account's
    certificates with an 11-field whitelist and explains that
    change_supabase_ssl's cert_id is this id. `purchase_supabase_ssl_cert`
    (DANGEROUS, preview/confirm with plan_id) subscribes a certificate
    (brand x type x domain-type x years x quantity; free tier
    DV_SSL_CERT_BASIC; paid tiers generate a pending order unless
    is_auto_pay) and can file the issuance application in the same
    request (domain + verification method DNS/File/Email + applicant
    contact; public-IP certificates support file verification only),
    locating the new certificate id from the subscribe response or a
    single list retry, degrading gracefully when it cannot.
  - `plan_supabase_creation_arrangement` now carries SSL and public
    access as two independent configuration modules alongside
    obs_integration: `ssl_configuration` (needs_ssl=true: three
    acquisition paths - reuse via list_ssl_certificates, purchase via
    the new tool (recommended), or import your own; domain/IP
    prerequisites; enable flow; interruption impact) and `public_access`
    (the former top-level eip_baseline migrated wholesale). The stale
    "CCM certificate purchase in the console / MCP has no certificate
    purchasing capability" statements are corrected everywhere.
  - Visual rendering adds certificate-list and purchase preview/confirm
    blocks plus SSL-configuration and public-access blocks in the
    arrangement; README/README_en (45-tool table, scenario updates) and
    the skill (v2.2.0, server >= 0.4.0a48) are updated in step, with
    acceptance items K24-K26.

### Added

- `mcp_server_rds_supabase_mgr` 0.4.0a47 - full flavor catalog with
  group_type classification, split flavor interaction and labeled
  storage types (skill v2.1.0):
  - `discover_db_instance_for_create` no longer truncates the managed
    PG flavor list to the first 20 entries; all saleable specs are
    returned and grouped by `group_type` into the ten official classes
    (general/dedicated/rapid/dedicatenormal/bigmem/normal/normal2/
    armFlavors/armlocalssd/normallocalssd, each with its Chinese label),
    every spec carrying vcpus, ram, instance_mode and its normal AZs.
    `volume.type` gains an `options` list mapping each storage name to
    its official Chinese name and constraint (ESSD = 极速型SSD for
    dedicated specs only, CLOUDSSD = SSD云盘 for general and dedicated,
    ULTRAHIGH = SSD, LOCALSSD = 本地SSD, GPSSD2 = 通用型SSD V2) plus
    the live `support_compute_group_type` compatibility list. The
    application-side discovery (`discover_supabase_create_basic_options`)
    mirrors the same full, grouped flavor structure.
  - `plan_supabase_creation_arrangement` now treats the Supabase
    application flavor and the managed PG instance flavor as two
    separate questions, each with an explicit interaction note. The
    instance baseline recommends by default the spec matching the
    application's (same group_type with same vcpus/ram, falling back to
    the smallest spec of the same group_type) and records the match in
    `flavor_match`; the storage type adapts to the matched group's live
    compatibility and records `type_basis`. All matching is defensive -
    old structures keep working unchanged.
  - Visual rendering adds grouped-flavor and storage-type tables to the
    discovery outputs and a flavor-match row plus interaction lines to
    the arrangement output; README/README_en tool rows and scenario
    sections, and skill SKILL.md/scenarios.md (v2.1.0, server >=
    0.4.0a47) are updated in step, including a new parameter-contract
    row for the split flavor interaction.

### Added

- `rds-supabase-mgr-mcp` skill v2.0.0 (server `mcp_server_rds_supabase_mgr` v0.4.0a46):
  the skill is deeply rewritten - not patched - to match the systematically
  rewritten MCP (43 tools), studying the GaussDB MCP skill's structure,
  register and layout. The frontmatter description now carries the capability
  summary, the full trigger-scenario list (from-zero creation, existing-PG
  attach, arrangement baseline, public access, OBS storage, auth/login,
  access info and key delivery, order payment, daily changes, deletion,
  troubleshooting) and NOT-for routing to the data-plane MCP, direct
  KooCLI and SQL. The body follows the GaussDB register: overview with
  invocation chain, no-session-state rule, scenario bullets and ten
  user-voice example quotes; a capability-boundary routing table;
  preconditions; a key-constraints chapter (read-only default,
  preview/confirm with plan_id, local request files only for secrets,
  KooCLI-only /0, storage-not-enrollable-after-creation, in32 binding
  validation, action-lock exclusion, tag-gated group cleanup); a common
  discipline; eleven scenario chapters (from-zero creation with the new
  auto-provisioning tools, existing-PG attach, arrangement baseline, EIP
  purchase and bind, OBS storage, auth/login/enhancement, access info and
  key delivery, daily changes, prepaid orders, deletion, troubleshooting);
  a grouped 43-tool command table; parameter-contract quick reference
  (charge_info string periods, whole-hour time_zone, naming rules,
  public_access_cidr three-way choice); output format (chart-rendered
  visual, structured error envelopes); verification; best practices; and
  version constraints. references/scenarios.md is rewritten as the per-
  scenario operational reference (step/tool/parameter/checkpoint tables,
  the creation request body, an 18-point pre-preview checklist, failure
  handling); acceptance.md gains scenario-level acceptance items
  including storage-not-enrollable-after-creation and the order
  double-equality amount check; install.md and local-requests.md are
  fact-corrected. skill-lint now guards the eleven new scenario headings.
- `rds-supabase-web-build` skill: the application-creation and resource-
  preparation exposition is removed and replaced with direct delegation to
  the rds-supabase-mgr-mcp skill - single source of truth, no duplication,
  no drift. Step three of the workflow now keeps only the interactive
  choice gates and web-specific constraints (project-scoped MCP
  registration, credentials into protected project files, the two-bucket
  boundary between the public-read frontend hosting bucket and the
  private backend storage bucket, and the ban on reusing the hosting
  bucket), while creation orchestration (plan_supabase_creation_
  arrangement), scenario tools (create_supabase_with_new_instance /
  create_supabase_link_exist_instance with automatic security-group and
  OBS provisioning), public access (EIP flow), key delivery and OBS
  storage all reference the mgr skill's chapters and tools. The stale
  post-hoc storage-enablement path is corrected: storage is enabled at
  creation time only and cannot be backfilled onto an existing
  application - the flow now tells the user so and routes to a new-
  application decision. references/workflow-stages.md mirrors the
  delegation; old tool names (create_supabase_application,
  plan_supabase_creation) are fully gone.

### Added

- `mcp_server_rds_supabase_mgr` v0.4.0a45: the creation timezone becomes a
  first-class field option with its official value range, and the README
  business scenarios gain purchase modes plus elevate the OBS integration.
  discover_db_instance_for_create adds basic_config.time_zone: 25 whole-hour
  values UTC-12:00~UTC+12:00 with UTC+08:00 (China Beijing) recommended,
  grounded in the official CreateInstance contract (PostgreSQL whole hours
  only; the SQL Server timezone/UTC-offset reference table is cited in the
  note). The creation validator tightens basic_config.time_zone from a loose
  text check to the same whole-hour rule; the configuration_id option note
  now states its value source (ListConfigurations ids). READMEs and skill
  guidance present the arrangement as three mandatory parameter modules plus
  the OBS bucket storage integration as a key optional module. A new
  Scenario 5 (purchase modes) inherits the GaussDB MCP order documentation
  and adapts it: the billing boundary is explicit (the application is free
  during public beta; only the managed instance is charged), pay-per-use is
  strongly recommended (charge_info: period_type is the string month/year,
  1-9 months or 1-3 years prepaid), prepaid payment walks get/pay_supabase_
  order (amount and currency verification, expected_amount must equal both
  official_amount and amount_after_discount so discounted orders are
  rejected, one submission without automatic retry, unknown outcomes are
  re-queried never repaid), and cancellation walks get/cancel_supabase_order
  (unpaid-only, permanent, idempotent, cancellation_verified follow-up).
  Verified live in cn-east-3: the field renders with UTC+08:00 recommended
  and the arrangement embeds it. Tool count unchanged (43); skill v0.9.16.

- `mcp_server_rds_supabase_mgr` v0.4.0a44: both READMEs are systematically
  rewritten, following the GaussDB MCP server README's layout, typography
  and register. The overview is one consolidated professional summary; the
  feature list is regrouped into terse capability statements; every
  tool-table scenario is compressed to one line with all 43 rows and 37
  API-doc links preserved; a new Business Scenarios chapter carries
  pre-creation preparation, the full application creation flow split into
  new-instance and existing-instance sub-sections, EIP creation and
  binding, and application deletion with the managed PG instance.
  Skill v0.9.15.

- `mcp_server_rds_supabase_mgr` v0.4.0a43: the scenario creation tools
  provision the OBS bucket too. create_supabase_with_new_instance and
  create_supabase_link_exist_instance ensure the storage_component bucket
  before submission (existing kept, missing created per the fixed private/
  standard/multi-AZ/block-public-access rules, short-uuid retry on global
  collision) and backfill the final bucket name so one submission succeeds.
  Previews carry obs_plan with the credential mode and warn on temporary
  credentials. This release also finalizes the scenario split of
  create_supabase_application (43 tools): the generic tool is removed, the
  arrangement's creation_flow routes through the two scenario tools with
  security-group and OBS preparation executed automatically inside the
  tool. Verified live in cn-east-3 against a temporary VPC/subnet (cleaned
  up after). Skill v0.9.14.

- `mcp_server_rds_supabase_mgr` v0.4.0a42: OBS storage tooling, developed in
  parallel by three agents (OBS service, storage visual renderer,
  documentation) plus integration fixes caught live.
  create_supabase_new_obs creates a brand-new private OBS bucket for the
  application's storage needs (the storage_component target) through the
  KooCLI embedded obsutil: the bucket name derives from the application
  name (sanitized, supabase- prefix, short-uuid retry on collision),
  storage class fixed to standard, bucket type fixed to private, data
  redundancy as a parameter (multi_az default, single_az optional), public
  access blocked (fixed, put-public-access-block with all four switches),
  region from the current project, enterprise project default.
  discover_supabase_storage presents the acquisition options once the
  storage need is confirmed - reuse (buckets listed, private first, public
  ones risk-flagged) or new (recommended/default, complete spec) - and
  detects temporary credentials (SecurityToken), explicitly prompting for
  persistent AK/SK with an OBS read test.
  plan_supabase_creation_arrangement gains the obs_integration module and
  two flow steps when needs_storage is confirmed, plus an
  update_supabase_storage credential-rotation post step.
  Live-caught integration fixes: the embedded obsutil rejects the JSON-API
  --cli-* flags (exit 3 with usage) - the obs channel now uses its native
  -i/-k/-t credentials and a -e=obs.<region> endpoint, with a per-bucket
  region override for bucket-local probes; the real ls bucket rows carry
  the obs:// prefix (the parser now matches the verified format and the
  live account lists its bucket correctly); get-bucket-public-status
  returns 405 on the current account, degrading to an explicit unknown
  status. Also fixed: the README version lines had been silently frozen
  at 0.4.0a23 for many releases (a replace chain broke unverified) -
  both now read 0.4.0a42. Tool count 40 -> 42; skill v0.9.13.

### Added

- `mcp_server_rds_supabase_mgr` v0.4.0a41: chart-rendered visualization for every
  discovery and arrangement response, plus two EIP tools developed in parallel
  by three agents (visual engine, EIP purchase service, EIP bind service).
  All discovery tools (discover_supabase_create_basic_options,
  discover_db_instance_for_create, discover_network_for_create) and
  plan_supabase_creation_arrangement now attach a `visual` field: CJK-aware
  box-drawing tables (network placement, security-group rule specs, action-lock
  candidate lists, parameter baselines) and a step-numbered flowchart of the
  creation flow, so agents can present results to users directly.
  `create_supabase_eip` provisions the public entry EIP via KooCLI, idle-first:
  prefer_idle=true lists unbound EIPs for the user to pick one (returned
  directly, nothing created); with none idle it falls through to the purchase
  baseline - pay-per-use recommended (prepaid documented with its console
  order), dedicated full-dynamic-BGP bandwidth (publicip.type=5_bgp,
  share_type PER) sized 5-1000M with 300M recommended; a newly created
  postPaid EIP is auto-tagged USAGE_FOR=Supabase应用公网访问，自动创建的.
  `bind_supabase_eip` binds via the RDS AttachEip API with triple validation
  to prevent mistaken and stray operations: the instance ID must end with
  in32 (Supabase application pattern) and exist in this environment's
  application list (a backend 400 on the exact-ID filter maps to the same
  ownership rejection - caught live), and the EIP ID/address must be a
  canonical UUID/IPv4. The arrangement's EIP baseline and post-creation flow
  now route through the two new tools. Agent contract discoveries: EIP v3
  names take publicip.alias (no name key), prepaid periods live under
  extendParam.*, and tag creation requires action=create. Tool count 38 -> 40.
  Verified live in cn-east-3: idle-first with an empty inventory falls to
  preview with plan_id, previews render the visual, suffix and ownership
  rejections behave correctly, and the arrangement returns a 111-line visual
  with the full flowchart. Skill v0.9.12.

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a40: plan_supabase_creation is
  thoroughly reworked into plan_supabase_creation_arrangement - a
  scenario-based, end-to-end creation orchestration design plus a fixed
  parameter baseline, assembled live from the three discovery tools.
  The managed-instance source is presented first as an explicit decision
  (newly_instance recommended and the default; existed_instance attaches
  an existing PG) and the user's definitive conclusion is required up
  front. Three step modules are consolidated live: Supabase basics
  (name suggestion, version, mode, flavor via
  discover_supabase_create_basic_options), managed instance (newly:
  engine/flavor/storage field options via discover_db_instance_for_create;
  existed: the attachable candidates listed paginated at 20 per page,
  each row carrying the complete basic information - version,
  deployment type, port, availability zones, created time - and its
  current action locks so instances mid-restart/upgrade/change can be
  excluded before submission, avoiding task conflicts), and network
  control (placement plus the specification-only security-group plan via
  discover_network_for_create). The EIP purchase baseline is fixed:
  pay-per-use recommended (prepaid documented with its order constraints),
  dedicated full-dynamic-BGP bandwidth 5-1000M with 300M recommended
  (KooCLI EIP CreatePublicip/CreatePrePaidPublicip verified in the
  CLI catalog; MCP binds via change_supabase_eip only). A step-numbered
  creation_flow (network ready -> security groups -> request file ->
  preview -> submit -> progress -> verify) and a conditioned
  post-creation flow are emitted for strict 1:1 execution; the response
  declares that nothing is created here. Offline diagnostics and the
  smoke test now validate the tool's registration and argument
  validation without triggering live discovery. Verified live in
  cn-east-3: an 11-step newly-instance arrangement with live-basics,
  PG-18 flavor and default-network modules, the detected egress
  117.88.75.25/32, and an empty paginated candidate inventory.
  Skill v0.9.11; tool count unchanged (38).

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a39: the discovery tools' security-group
  output is now an explicit, copy-ready specification contract. A code audit
  confirmed the discovery paths only ever call List/GET operations (RDS
  catalogs, VPC/subnet lists, attachable-candidate queries, the egress-IP
  echo); zero write paths - and the responses now say so explicitly.
  discover_network_for_create's security_group_plan gains plan_type
  "specification" and a declaration that nothing is created here, names the
  two dedicated groups concretely (supabase-app-sg / supabase-db-sg with
  their purpose descriptions), and adds apply_steps: an ordered list of
  {tool, args} pairs - create_supabase_security_group and
  add_supabase_security_group_rule with exact direction/protocol/port/CIDR
  arguments and group_id placeholders - so the later real creation follows
  the plan strictly and prepares quickly. The basic-options strategy
  carries the same declaration. Tool descriptions and READMEs state
  read-only/specification-only explicitly. Verified live in cn-east-3:
  the plan returns the five newly-scenario steps (three for existing
  instances) with the declaration and named groups. Skill v0.9.10; tool
  count unchanged (38).

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a38: the two creation-scenario discovery
  tools are renamed and restructured around the managed-instance source, with
  the security-group planning consolidated into the network tool.
  `discover_db_instance_create_options` becomes `discover_db_instance_for_create
  (scenario, mode?, instance_id?)`: newly_instance keeps the field-option logic
  (engine versions, flavors, storage) and drops the network input and
  security-group plan; existed_instance lists the attachable PG candidates
  (same source as list_supabase_manageable_instances - a live probe showed the
  empty inventory is {"total_count": 0} with no list key, now treated as a
  valid empty state) and, with instance_id, returns that instance's
  basic/configuration/network sections.
  `discover_available_network_for_create` becomes `discover_network_for_create
  (scenario, availability_zone?, instance_id?, detect_access_ip?)`:
  newly_instance keeps the VPC/subnet walk and default recommendation and now
  states both groups' creation configuration - application group 8443 ingress
  (three source options: default 0.0.0.0/0 via KooCLI, current-device CIDR
  via detect_access_ip with a best-effort probe fixed to use certifi's CA
  bundle - python.org macOS builds lack the system CA store, which failed
  every https probe - or custom) plus 5432 egress, database group 5432
  ingress, all CIDRs from the chosen subnet; existed_instance takes VPC/subnet
  from the given instance, leaves its security group untouched and applies
  the same application-group rules. Verified live in cn-east-3: empty
  candidate inventory, MCP_NOT_FOUND for unknown ids, default-recommendation
  plan with precondition, detected egress 117.88.75.25/32.
  `discover_supabase_create_basic_options` keeps its guidance-only strategy,
  now pointing at discover_network_for_create. Tool count unchanged (38);
  skill v0.9.9.

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a37: both discovery tools now carry
  the security-group knowledge their scenarios need, closing the gap left
  when group discovery was removed in a35.
  `discover_db_instance_create_options` gains an optional `network` input
  ({"scenario": "discovered"|"default_recommendation", "subnet_cidr":
  "..."}, taken from discover_available_network_for_create or its default
  recommendation). With it, the dedicated database group's rules are
  generated directly: 5432 ingress from that subnet (moves with the port
  field), egress left at the default allow-all, plus the apply steps and -
  for the default-recommendation scenario - the precondition to run the
  default_create block first. Without it, the response keeps the rule
  template and the method: the ingress source must be the selected
  subnet CIDR. Groups are still never discovered from the cloud.
  `discover_supabase_create_basic_options` gains a guidance-only
  security_group_strategy: at this stage the instance does not exist yet,
  so the subnet CIDR and the instance port cannot be pinned down. The
  strategy states the application group's shape (8443 ingress from the
  user CIDR; egress opening the managed instance's port, default 5432)
  and points the database group to the instance tool's generated plan.
  Verified live in cn-east-3 across all scenarios: template, discovered
  (10.0.1.0/24), default recommendation (192.168.0.0/24 with
  precondition), and invalid inputs rejected before any cloud call.
  Skill v0.9.8; tool count unchanged (38).

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a36: the name and password fields
  of `discover_supabase_create_basic_options` now carry their full
  contracts instead of one-line notes. name gains the complete rules
  (4-64 characters, at most 64 UTF-8 bytes when containing Chinese at 3
  bytes per character, must start with a letter or Chinese character,
  case-sensitive, letters/digits/hyphen/underscore/Chinese only) and a
  suggested value that is checked live against the existing application
  list for uniqueness (deterministic per-day base with a counter suffix
  on collision; a listing failure degrades to the rules without the
  cross-check, visible in probe_status). password states the fixed
  dashboard login user `supabase` and the full rule text: 8-32
  characters with at least three of uppercase/lowercase/digits/special
  characters ~ ! @ # $ % ^ * - _ = + ? ,. Verified live in cn-east-3:
  the suggestion `supabase-app-1115` was returned collision-free
  against the real application list. Skill v0.9.7; tool count
  unchanged (38).

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a29: `HUAWEICLOUD_PROJECT_ID`
  becomes optional, completing the GaussDB-style zero-config adoption.
  When absent, the regional project is discovered automatically via IAM
  `KeystoneListProjects(name=HUAWEICLOUD_REGION)` on first use - once,
  cached per (ak, sk, token, region) so credential rotation invalidates
  it - with an explicit environment value still short-circuiting with
  zero network calls. Sub-project accounts (not discoverable by region
  name) keep the explicit variable as their documented path. The sdk_core
  transport now resolves the project lazily on first request like the
  REST transport, and the plan-intent digest resolves it before binding,
  so previews and submissions sign the same identity. Combined with the
  earlier region-derived endpoint, a minimal AK/SK configuration is now
  three variables: HUAWEICLOUD_REGION + AK/SK. READMEs (zh/en) flip the
  variable to optional with the discovery default and drop it from the
  quick-start template; the skill shrinks the first-step checklist from
  five items to three, documents the automatic resolution, and the
  Token-mode limitation note now covers both the security-group tools
  and project discovery (both need AK/SK or an explicit project id).

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a28: README (zh/en) security-group
  section rewritten around the correct usage model: the six security-group
  tools already wrap the KooCLI capability and work out of the box - the
  agent uses the tools first and falls back to raw KooCLI commands only
  where the tools deliberately do not go (0.0.0.0/0 world ingress, edge
  operations). The old section read as if the tools were a KooCLI
  alternative the operator had to wire up; it now leads with the
  tools-first principle and a scenario table, and demotes the internal
  implementation details (binary location, credential injection,
  region/project resolution, error passthrough, origin tagging) to an
  operations-troubleshooting subsection. Cross-references, the feature
  heading, and the HUAWEICLOUD_REGION table row follow; the skill's
  step-zero and security-group guidance state the same tools-first
  division of labor.

### Fixed

- `mcp_server_rds_supabase_mgr` v0.4.0a27: prepaid charge_info validation
  matched an internal convention instead of the official CreateInstance
  contract, so prepaid creations with the documented values were rejected
  (or wrong values passed through) and live submissions failed. Per the
  API reference charge_info table: period_type is the STRING 'month' or
  'year' - not the numeric 2/3 the validator and the skill docs both
  taught; period_num stays 1-9 months / 1-3 years (the 5-year option is
  a MySQL-only privileged exception and stays out of scope for managed
  PG). The validator now accepts the string values, rejects the numeric
  2/3 with a message that names the correct type, and keeps the boolean
  checks for is_auto_renew/is_auto_pay. volume.size gains the documented
  40-40000 GB bounds in place of any-positive. The skill documentation
  (scenarios.md route-A field guide, local-requests.md, and the
  planning/create guidance strings) taught the same numeric mistake and
  is corrected in lockstep - that documentation was the source agents
  copied, which is why live prepaid attempts kept failing.

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a26: the README tool table (zh/en)
  gains an API-doc column linking each tool to the corresponding
  operation in Huawei Cloud API Explorer. Mapping verified against the
  live KooCLI 7.3.12 RDS operation catalog: the Supabase application
  surface (List/Show/Create/Delete SupabaseApplication, ApiKeys, Auth,
  Storage, Password, EipBind, Ssl, Flavors, ManageableInstances), the
  generic RDS instance deletion and task-center query (DeleteInstance,
  ListJobInfo), the VPC security-group operations behind the KooCLI
  channel, and the BSS order operations (ShowCustomerOrderDetails,
  PayOrders, CancelCustomerOrder). Purely local planning/analysis tools
  (capabilities, creation/SSL planning, creation-progress analysis)
  carry no cloud API and show a dash. A note points to the RDS API
  reference index and flags that newer Supabase APIs may not yet appear
  in the published catalog.

- `mcp_server_rds_supabase_mgr` v0.4.0a25: renamed
  `list_supabase_flavors` to `list_supabase_flavors_with_azs` - the name
  now says what the response carries: each flavor's supported
  availability-zone list. Per the analysis of Huawei Cloud's own
  GaussDB MCP (whose discover_create_options derives AZ availability
  from flavor az_status) and live RDS verification (no standalone
  ListAvailableZones API exists for RDS), this tool is the
  availability-zone query and selection source for RDS Supabase
  creation. Docstring and skill guidance state the dual use; planning
  prompts, SKILL.md, scenarios.md, TOOL_CONTRACTS, SIX_SCENARIO_MATRIX,
  and READMEs (zh/en) follow the rename. No behavior change.

- `mcp_server_rds_supabase_mgr` v0.4.0a24: endpoint resolution now follows
  the GaussDB MCP convention. `SUPABASE_RDS_ENDPOINT` becomes an explicit
  override rather than a hard requirement: when absent, the standard
  regional RDS origin `https://rds.<region>.myhuaweicloud.com` is derived
  from `HUAWEICLOUD_REGION` (the same variable the KooCLI channel already
  uses). Resolution order: constructor argument, then SUPABASE_RDS_
  ENDPOINT, then region derivation, then empty with an actionable error
  naming both variables. Applies uniformly to the REST and sdk_core
  transports via a shared resolve_endpoint helper; diagnostics discover
  is unchanged. README (zh/en) environment table updated: the variable is
  optional with region-derived default.

### Added

- `mcp_server_rds_supabase_mgr` v0.4.0a23: new tool
  `show_supabase_creation_progress` (READ) - one-call, scenario-aware
  analysis of application creation progress. Existing-instance scenario
  (application_id + application_job_id): reads the application
  inventory filtered by id, then the application job. New-instance
  scenario (adds instance_job_id + instance_id, both required together):
  checks the instance job FIRST and only queries the application job
  after the instance completed - the application is created after the
  instance succeeds, so its job does not exist before that point.
  Returns a single phase verdict (instance_creating / application_
  creating / succeeded / failed with the failed stage), per-resource
  job statuses, a plain-language summary, and the next action;
  completion_verified is true only on succeeded. create_supabase_
  application's docstring now documents the scenario-specific returns:
  attaching an existing instance returns the application job and
  application id; creating a new instance returns the instance job id
  and instance id alongside them, with the application job absent
  until the instance is ready. README (zh/en) details both return
  shapes under the managed-database-instance bullet in the creation
  feature group and lists the new tool; skill `rds-supabase-mgr-mcp`
  v0.9.0 wires the progress tool into the scenario-1 waiting cadence
  (five-phase verdict, instance-first ordering) and keeps
  show_operation_job_status for single-task detail. Tool count 32.

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a22: `delete_supabase_application`
  now supports deleting the managed PostgreSQL instance together with the
  application. A new mandatory `delete_managed_instance` boolean must be
  set explicitly - the preview is rejected until the user has chosen;
  defaulting this decision is an incident either way (silent data loss on
  one side, silent continued billing on the other). False keeps today's
  behavior: application-only deletion, instance retained. True runs every
  managed-instance guardrail - live binding verification, the
  no-shared-reference sweep, and the pre-delete inventory read - BEFORE
  either deletion is submitted (while the application is still readable),
  then submits both deletions together and returns both job ids
  (`job_id` for the application, `instance_job_id` for the instance);
  each deletion may fail independently and both must be tracked. If the
  application deletion is accepted but the instance submission outcome is
  unknown, the plan records accepted and a RecoveryError explains the
  partial state, preventing blind resubmission. Skill
  `rds-supabase-mgr-mcp` v0.8.3 makes the instance question a mandatory
  pre-deletion check in the teardown scenario.

- `mcp_server_rds_supabase_mgr` v0.4.0a21: security-group origin
  tagging and a tag-gated whole-group deletion. `create_supabase_
  security_group` now stamps every group with AUTO_CREATE=true and
  USE_FOR=Supabase tags at creation (KooCLI CreateSecurityGroup/v3
  inline tags; serialization verified live via dry-run, and the show
  response returns the tags as a list of key/value pairs).
  `delete_supabase_security_group` verifies the tag pair on the live
  group before submission - groups without the matching tags (list or
  dict shape) are rejected with MCP_GUARDRAIL_BLOCKED, so a group that
  was not created by this flow - especially one in active use - can no
  longer be deleted through the tool by mistake; such groups route to
  the console after manual review. The deletion preview carries the
  dedicated warning. Skill `rds-supabase-mgr-mcp` v0.8.2 documents the
  auto-tagging and the tag gate, and the group description wording is
  tightened to purpose-first per review: the application group as
  `Supabase应用（自动创建）`, the route-A database group as
  `数据库接入（自动创建）` (SKILL.md, scenarios.md, and planning.py
  guidance updated in lockstep).

- `mcp_server_rds_supabase_mgr` v0.4.0a20: tool-surface cleanup.
  Removed `inspect_supabase_plan`, `cancel_supabase_plan`, and
  `reconcile_supabase_auth_plan` - the local-ledger operation trio added
  a category unrelated to cloud resource management while providing
  little decision value: the failure envelope already carries the plan
  id and outcome category, previews expire on their own within ten
  minutes (not submitting is the cancellation), and the auth
  reconciliation tool was a long-flagged orphan affecting only local
  state. On ambiguous outcomes the guidance is now to verify directly
  against the operation task and the target resource. Renamed the job
  tools to their generic operation-task semantics:
  `show_supabase_job` -> `show_operation_job_status` and
  `wait_supabase_job` -> `wait_operation_job_complete` (they track any
  submitted operation task - creation, deletion, SSL, EIP - not a
  Supabase-specific job). The orphaned PlanStore.verify_auth/cancel
  methods and the reconciliation service/test module were removed with
  them; diagnostics now exercises the surviving preview flow. Tool
  count 31. README (zh/en) rewritten in kind: the access-control group
  drops the password bullet, the creation group drops the submission
  bullet and gains the billing note (RDS Supabase free public beta;
  managed instance pay-per-use or yearly/monthly, Single or Ha), and
  the tool table's scenario column was rebuilt end to end - plain
  scenario-first descriptions instead of parenthetical jargon such as
  "needs confirmation" or "via request_ref", with the two-phase
  confirmation and secret-by-alias rules stated once in the section
  preamble. Skill `rds-supabase-mgr-mcp` v0.8.1 follows the renames and
  rewritten error guidance.

### Added

- `mcp_server_rds_supabase_mgr` v0.4.0a19: order lifecycle tools for prepaid
  managed PostgreSQL instances, ported from Huawei Cloud's own GaussDB MCP
  reference implementation (huaweicloud-gaussdb-mcp, gaussdb-integration
  branch) and adapted to this server's conventions. New tools:
  `get_supabase_order` (READ; order status, amounts, currency, paginated
  line items via BSS `GET /v2/orders/customer-orders/details/{id}`),
  `pay_supabase_order` (DANGEROUS; balance payment via BSS
  `POST /v3/orders/customer-orders/pay` with use_coupon/use_discount=NO),
  and `cancel_supabase_order` (DANGEROUS; unpaid-order cancellation via BSS
  `PUT /v2/orders/customer-orders/cancel`). New dependency
  `huaweicloudsdkbss>=3.1.218,<4` (3.1.220 locked); BSS calls use global
  credentials against bss.myhuaweicloud.com with retry disabled so an
  ambiguous payment result is never retried automatically.
  The GaussDB defense chain is preserved in full: product-scope checks
  across the main order, sub-orders, and every line item on every page
  (default service type hws.service.type.rds, overridable via
  SUPABASE_ORDER_SERVICE_TYPE pending a live-order confirmation);
  expected_amount must match both official_amount and amount_after_discount
  (discounted orders are rejected - use the console); currency must match
  exactly; payment_time guards against stale status; a final refresh
  happens immediately before the single payment submission; already-paid
  orders return an idempotent already_processed result instead of a second
  submission. Adaptations on top: the one-use plan ledger binds
  (order_id, expected_amount, currency, endpoint, credential) - previews
  expire in ten minutes and submissions cannot be replayed; the
  SUPABASE_ENABLE_WRITES / HUAWEICLOUD_MCP_READ_ONLY gates apply; definite
  rejections record failed while ambiguous submission outcomes record
  unknown with a RecoveryError carrying the plan id; an in-process
  asyncio lock serializes payments. create_supabase_application's prepaid
  branch now routes to the order tools instead of telling the user to pay
  in the console. Skill `rds-supabase-mgr-mcp` v0.8.0 updates the billing
  guidance in SKILL.md and the scenario matrix; tool count 34.

- `mcp_server_rds_supabase_mgr` v0.4.0a18: new tool
  `delete_supabase_managed_instance` (DANGEROUS) - deletes the PostgreSQL
  instance managed by one Supabase application through the native RDS
  API `DELETE /v3/{project_id}/instances/{instance_id}` (the operation
  wrapped by the UniSDK `RdsClient.delete_instance`; response carries an
  async job_id tracked via show_supabase_job). Wrong-instance protection
  is enforced by a four-layer check chain before submission: (1) the
  caller must name both the application and the instance; (2) the live
  application detail must exist and its `managed_instance.id` must equal
  the provided instance ID (the only authoritative binding source); (3)
  an application-inventory sweep (bounded, fail-closed at 500
  applications) verifies no OTHER application references the same
  instance; (4) the instance must be uniquely present in the RDS
  inventory immediately before deletion. Protection guardrails apply to
  both the application and the instance identity. Boundary stated in
  the response: pay-per-use only (yearly/monthly must be unsubscribed
  in the console); applications already deleted cannot be verified, so
  that path stays with the console. Preview/confirm two-step flow, one-
  use plan ledger, read-only/write gates, and definite-rejection vs
  unknown outcome recording follow the house pattern.
  Skill `rds-supabase-mgr-mcp` v0.7.2 routes the teardown residual
  (database instance) through the new tool and bumps the tool count to
  31; server README (zh/en) updated in kind.

- `mcp_server_rds_supabase_mgr` v0.4.0a17: new tool
  `delete_supabase_security_group` (DANGEROUS) - removes an entire
  security group during teardown through the KooCLI channel, closing the
  gap where whole-group deletion required raw KooCLI or the console.
  Same safety envelope as the other write tools: preview/confirm
  two-step flow with the one-use plan ledger, group identity
  re-verification before submission, protected-group guardrail,
  read-only and write-enable gates. The preview carries a dedicated
  warning that deletion removes every rule in the group at once and
  that the backend rejects groups still referenced by instances or
  NICs - the agent must verify nothing uses the group first. Skill
  `rds-supabase-mgr-mcp` v0.7.1 updates the tool count (29 -> 30) and
  wires the tool into the teardown scenario's residual-cleanup channel.

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a15 security-group tool descriptions
  rewritten to lead with the RDS Supabase purpose instead of transport
  mechanics: each description now states what the tool does for an RDS
  Supabase application, with `add_supabase_security_group_rule`
  explaining that 8443 is the default public entry and 5432 the managed
  PostgreSQL port, while noting both follow the user's customized ports
  when an existing instance was attached at creation (verify the actual
  ports per deployment instead of assuming the defaults).

### Fixed

- Skill `rds-supabase-mgr-mcp` INSTALL.md verification row claimed five
  reference documents; the skill ships four (install/scenarios/
  local-requests/acceptance). Caught by executing the documented install
  flow live against a fresh project-level install.

### Added

- Skill `rds-supabase-mgr-mcp` deployment guidance from live install
  testing: (1) INSTALL.md section 4 probe step now handles the
  installed-but-not-on-PATH case (locate the binary in its install dir,
  add that dir to the shell PATH, or point HCLOUD_BIN at it - no
  reinstall); (2) references/install.md gains a slow-network fallback for
  the uvx health-check timeout (symptom: MCP panel shows failed -
  Operation timed out): pre-warm the uvx cache once (any reachable PyPI
  mirror via UV_DEFAULT_INDEX if needed) or pin the server with
  `uv tool install` and point the MCP command at the installed
  executable (location per `uv tool dir`) for zero-resolution startup.
  Guidance is location- and mirror-agnostic: it names the method and
  leaves the concrete path/mirror to the user's environment.

### Changed

- `mcp_server_rds_supabase_mgr` v0.4.0a15: the five security-group tools
  (list/show/create group, add/delete rule) now execute through the KooCLI
  (hcloud) channel instead of calling the VPC API on the RDS origin - live
  testing proved the RDS origin does not serve the VPC API, so the old direct
  path could never work. New `client/koocli.py` implements the invocation
  contract from Huawei Cloud's own huaweicloud-devkit runner: binary located
  via HCLOUD_BIN then fixed install dirs then PATH; region from
  HUAWEICLOUD_REGION (new variable) or derived from the RDS endpoint
  hostname; AK/SK injected per command only when both are present, otherwise
  the hcloud profile is used; VPC v3 operation names (CreateSecurityGroup/v3
  etc.) and nested `--security_group_rule.*` parameter serialization verified
  against a real KooCLI 7.3.12 in cn-east-3 (list/show/dry-run create group/
  dry-run create rule all passed live). Project resolution stays with KooCLI
  (region default project; sub-project accounts configure cli-project-id in
  the hcloud profile). Failure mapping mirrors the a12 error-passthrough
  spirit: backend error_code/error_msg/request_id pass through on non-zero
  exit, the first-run privacy agreement signature maps to a dedicated
  MCP_CLI_BLOCKED error with the one-time accept hint, and missing binary or
  timeout get MCP_CLI_MISSING / MCP_CLI_TIMEOUT. The plan ledger, confirm
  preview flow, read-only gates, duplicate-rule and ownership guardrails are
  unchanged; the intent digest now binds region and the KooCLI credential
  fingerprint. `add_supabase_security_group_rule` gains direction
  (ingress/egress) and protocol (tcp/udp) parameters - the 5432 egress rule
  no longer requires the agent to run raw KooCLI (known gap C2 closed);
  0.0.0.0/0 world rules remain intentionally rejected by the tool and still
  require explicit user confirmation via KooCLI. Skill `rds-supabase-mgr-mcp`
  v0.7.0 documents the new parameters, the KooCLI channel requirement
  (install per INSTALL.md section 4), HUAWEICLOUD_REGION, and the Token-mode
  limitation (security-group tools need AK/SK or a local hcloud profile).

### Removed

- Legacy validation artifacts carrying the retired `hw-rds-supabase` /
  `hw-rds-supabase-py` project name: `docs/validation/tool-availability.md`,
  `full-tool-test-report.md`, `run_full_tool_test.py`, and their result JSON
  (a v0.3.0-era snapshot of 38 tools, superseded by the current server and
  its 0.4.0 test suites). The live server has been named
  `mcp-server-huaweicloud-rds-supabase` for a long time; no remaining file
  references the old name. The other validation documents (e2e comparison,
  skill behavior eval) never used it and are retained.

### Changed

- Skill `rds-supabase-mgr-mcp` v0.6.2: KooCLI is now provisioned at install
  time. INSTALL.md gains a mandatory post-install step: immediately after the
  skill files land, the agent probes `hcloud version`; if missing it installs
  KooCLI on the spot using the official distribution (methods sourced from
  Huawei Cloud's own huaweicloud-devkit CLI skill - the official one-line
  install script as the main path, pinned-version downloads per platform as
  the reproducible path, with per-platform PATH placement). The step also
  handles the known first-run trap: a fresh KooCLI blocks on its privacy
  agreement and fails non-interactive runs with [USE_ERROR], so the agent
  detects those strings, asks the user, and feeds y via stdin once. The
  scope table lists KooCLI as arriving at install time; the completion
  report must state the KooCLI status (existing or newly installed version).
  Boundaries unchanged: tools only, no credentials at install time (the
  hcloud configure set command is explicitly forbidden - AK/SK would enter
  shell history), no session restart needed, CodeArts sandbox guidance
  included. SKILL.md adds a step-zero KooCLI recheck that points back at the
  INSTALL step.
- `mcp_server_rds_supabase_mgr` v0.4.0a14: auto-created resources are now
  marked for auditability. create_supabase_security_group accepts an optional
  description (VPC v3 contract: at most 255 characters, no angle brackets,
  validated locally); the skill prescribes the standard wording - the
  application group carries 自动创建的，用于Supabase应用 and the route-A
  database group carries 自动创建的，用于托管实例接入, so operators can
  tell agent-created dedicated groups from manually created shared ones in
  the console. Newly created EIPs (KooCLI path) must carry the tag
  USAGE_FOR=Supabase应用公网访问，自动创建的 per the skill's EIP step and
  quick-reference command; the planner's pre-creation and post-creation
  steps state both marking rules. Tests: description round-trips into the
  request body and preview, oversized/angle-bracket descriptions rejected
  locally.
- Skill `rds-supabase-mgr-mcp` v0.6.1: security-group creation now requires
  the purpose description (standard wording for the application group and
  the managed-PG access group, with the rationale: distinguishable in the
  console, auditable cleanup); EIP creation via KooCLI requires the
  USAGE_FOR tag with the exact value and a ready-to-copy tags JSON snippet
  in the quick-reference table. Server floor raised to 0.4.0a14.
- `mcp_server_rds_supabase_mgr` v0.4.0a13: three real-testing fixes.
  Application list/detail no longer fail with MCP_SDK_ERROR on rows without
  public_ip (absent until an EIP is bound) or private_ip (absent while the
  application is still creating): both now project as optional (None), with
  the backend authoritative for field presence per state - the previous
  mandatory check made a freshly created application unqueryable. The
  intent planner now emits a GitHub-login decision point (it only appeared
  in post-creation steps), and the storage decision point states that
  storage cannot be enabled after creation. Route-A pre-creation steps
  describe Ha AZ selection (one AZ for Single, two distinct AZs for Ha,
  top-level availability_zone carries the primary) and the deployment-mode
  probe: list_supabase_flavors with mode=Ha answering 400 means the
  environment supports Single only. Tests: public_ip-less list rows and
  private_ip-less creating-state detail rows project as None (mandatory
  regression now deletes a genuinely mandatory field).
- Skill `rds-supabase-mgr-mcp` v0.6.0: intent questions are now a hard
  gate. The scenario-one step-1 and the scenario handbook both open with a
  four-question table (database route, file storage, public access,
  https) with the explicit discipline that none may be skipped or
  defaulted on the user's behalf - omitting to ask is what sends the run
  off the rails, and storage cannot be enabled after creation, so the
  OBS question must be asked before creating. The deployment-mode row
  adds the probe rule (list_supabase_flavors mode=Ha: success means both
  modes, 400 means Single only, report honestly). The AZ row now requires
  two distinct AZs for Ha (the request's availability_zone carries the
  primary); the checklist and request-body notes were updated to match.
  Server floor raised to 0.4.0a13.
- `mcp_server_rds_supabase_mgr` v0.4.0a12: backend error codes and messages
  are now passed through on both transports, fixing a real-test blind spot.
  In sdk_core mode the Huawei Cloud SDK raises ServiceResponseException for
  every non-2xx response (its response hook parses the body and raises
  before our status check), and the client handler was discarding the
  exception's error_code/error_msg and raising a bare status failure -
  AK/SK users saw only "API returned HTTP 400" with no way to diagnose.
  The handler now builds the failure detail from the exception's
  error_code, error_msg and request_id (the SDK reads request_id from the
  X-Request-Id response header); the status-check fallback path also parses
  the raw error body via a shared error_detail helper extracted from the
  REST client (flat and nested error objects, bounded to 300 characters
  per field). http_failure now formats request_id into the backend detail
  line as well. This applies to all 29 tools - both transports funnel
  through the same http_failure, and the service layer's definite-vs-
  unknown routing (0.4.0a10) re-raises definite rejections with the full
  message. Tests: sdk_core error-body passthrough with category routing,
  nested error object, ServiceResponseException passthrough (174 passed).
- Skill `rds-supabase-mgr-mcp` v0.5.9: server floor raised to 0.4.0a12.
- Skill `rds-supabase-mgr-mcp` v0.5.8: the dynamic-install host matrix now
  covers CodeArts (Madao) and OfficeAce explicitly, verified against the
  CodeArts Agent user guide. CodeArts: the MCP config is mcp_settings.json
  (opened via Settings > MCP Tools > Configure MCP, project-level placement
  under .codeartsdoer/, mcpServers entries identical in shape to .mcp.json
  so the existing uvx template applies; server names limited to 64
  characters), saving starts the tool without an IDE restart, and the
  Installed tab is where enable/restart state is checked - the official
  docs note that editing an existing entry requires one click of that
  MCP's restart button because the IDE cache may not refresh itself.
  OfficeAce has no public documentation: the project-level config rule
  stands and enablement goes through the host's own MCP management entry,
  with the honest one-time-reload fallback where no in-session mechanism
  exists. The install manual's registration section now names the CodeArts
  config file and placement alongside the opencode V2 structure note.
- Skill `rds-supabase-mgr-mcp` v0.5.7: the management-plane MCP install
  step is now an agent-executed dynamic install that enables the server
  in the current session with no restart. After the environment check
  passes, the agent writes the project-level MCP config itself (uvx
  straight from this GitHub repository, no clone) and enables it
  in-session per host, verified against each host's official docs:
  opencode connects newly configured servers automatically (with the
  /mcps panel as the in-session fallback) and Claude Code shows its
  project-server approval prompt in-session (one approval connects it,
  /mcp for status). Hosts without hot-reload are handled honestly: the
  config is complete and the user performs one host reload. The install
  manual's opencode template was also corrected to the current V2
  structure (mcp.servers.* instead of servers directly under mcp) with
  the {env:NAME} reference noted, and a session-enablement subsection
  adds the per-host commands plus a troubleshooting order that
  distinguishes "not enabled in session" (fix enablement, do not
  reinstall) from config/credential errors. Verification step now
  starts from tool visibility in the current session.
- Skill `rds-supabase-mcp` v2.6.2: accuracy and packaging fixes plus a
  human-facing README. The tool table now matches the server (0.4.0):
  get_database_stats (pg_stat_database + bgwriter via RPC) and get_logs
  (analytics-to-CSV cascade that returns an empty list with an
  explanation when unconfigured) are documented as available under
  runtime diagnostics; the unavailable set is corrected to the four
  tools that actually fail without the removed direct-connection
  channel (list_storage_buckets, list_storage_objects,
  list_realtime_publications, generate_typescript_types). references/
  related-tools.md gained get_cron_job_history and the unavailable-tools
  group, and its server-README link now uses the absolute GitHub URL so
  links survive standalone skill installs. mcp-installation-guide.md:
  the local-clone alternative is now `uv run --directory` (the previous
  `pip install` suggestion violated the project-level isolation rule),
  the hardened execute_sql SQL is linked by absolute URL, and the stale
  "auto-deployed at startup" claim (impossible since direct connections
  were removed) was replaced with manual one-time deployment. New
  README.md: positioning, workflow and tool overview with guardrails,
  and a two-step quick install - natural-language skill install plus a
  natural-language MCP onboarding sentence pointing at
  references/install.md, with the stdio template, the three connection
  variables, and the project-level registration constraints.
- `mcp_server_rds_supabase_mgr` v0.4.0a11: creation options opened to the
  full product surface, verified against the API Explorer
  CreateSupabaseApplication contract. Deployment mode now accepts Single
  and Ha (the ha object follows: mode Single/Ha, replication async/sync);
  billing accepts postPaid and prepaid - charge_info reuses the common
  RDS ChargeInfo definition (prePaid requires period_type 2=month/3=year
  with period_num 1-9 months or 1-3 years, optional is_auto_renew/
  is_auto_pay booleans; postPaid carries charge_mode only). Prepaid
  submissions return an order instead of a job: the create flow now
  answers status=order_created with the order_id, marks the plan
  accepted (blocking duplicate orders), and states clearly that payment
  happens in the console and this MCP never pays. The route-B
  database_name is enforced as the fixed value "root". The top-level
  version is documented as "the highest available application version"
  (x.y.z) rather than a fixed value. list_supabase_flavors accepts
  mode=Ha. The intent planner's pre-creation steps and capabilities
  declarations updated accordingly (mode and billing are user choices;
  security groups must be newly created dedicated groups with rules
  configured at creation time). New tests: Ha+prepaid validation with
  field attribution, prepaid order flow, fixed-root enforcement,
  unexpected-shape handling.
- Skill `rds-supabase-mgr-mcp` v0.5.6: creation configuration aligned
  to the same product surface, plus a language pass. New rules:
  application version = the highest available (currently 1.0.0, no
  query API - check the console when unsure); deployment mode and
  billing are explicit user choices (Single/Ha, postPaid/prepaid with
  the period rules and the order-payment flow explained); the
  application security group must be a newly created dedicated group
  built automatically by the agent with both ingress (8443) and egress
  (5432) rules configured at creation time - the rules table moved from
  step 4 into step 2, and step 4 now covers only EIP binding and
  connectivity verification; the enterprise project defaults to the
  default project (ID "0"); route B database_name is fixed to root;
  the application password is documented as the default user
  supabase's password (also the Dashboard admin login). Wording
  de-jargonized throughout ("reference payload"/"copy verbatim" phrasing
  replaced with plain statements). Server floor raised to 0.4.0a11.
- `mcp_server_rds_supabase_mgr` v0.4.0a10: creation contract aligned to a
  real backend-accepted route-A payload, plus end-to-end error
  transparency. Contract: managed_instance now accepts the `ha` object
  (mode must be Single, replication_mode async/sync - the captured
  request carries Single+async and was previously rejected as an
  unknown field, the root cause of repeated creation failures); the
  top-level `version` is documented as the application version
  ("1.0.0"), not the PG engine version; port 5432 is accepted
  explicitly (matching the captured request) or omitted for the
  default; passwords (application and managed-instance) must be 8-32
  characters containing at least three of uppercase/lowercase/digits/
  special characters (~!@#$%^*-_+=?,). Error transparency: local
  validation failures now name the offending field (ha.mode,
  volume.size, password, unexpected/missing fields, request alias vs
  registry problems); the REST client parses and passes through the
  backend error body (error_code/error_msg) on non-2xx instead of
  dropping it; write submissions distinguish definitive rejections
  (clean 4xx - plan marked failed, original error re-raised with
  backend detail, re-preview and resubmit allowed) from genuinely
  unknown outcomes (transport/timeout/5xx - plan unknown, replay
  forbidden); the same split is applied to both create and mutate
  paths. Tests: the real payload is locked in as a fixture (passwords
  replaced), field-attribution, password-composition, failed-vs-unknown
  and repair-loop cases added; existing timeout simulations updated to
  the semantically correct RecoveryError transport form.
- Skill `rds-supabase-mgr-mcp` v0.5.5: scenario 1 creation section
  aligned to the same real payload. The config table gains the
  application-version row (fixed "1.0.0", explicitly not the PG engine
  version), the password rule (8-32 chars, three of four character
  classes, locally generated from the allowed set only), the ha fixed
  value, port-5432-or-omit guidance and the parameter-template caveat;
  the mislabeled "database password" row is renamed "application
  password" with the DB password getting its own route-A row. Step 3
  now requires a field-by-field pre-preview checklist against the
  20-item table added to scenarios.md (with the captured payload as
  the reference column) - the three most common real failures (wrong
  version, missing ha, non-compliant password) are caught before
  submission. Error-table guidance updated for the new semantics:
  field-level attribution, backend error pass-through, failed (fix and
  re-preview) vs unknown (never replay). Server floor raised to
  0.4.0a10.
- `mcp_server_rds_supabase_mgr` v0.4.0a9: `plan_supabase_creation`
  rebuilt from a static checklist into an intent-driven phase planner,
  aligned with the skill's creation scenario. New optional tri-state
  intents (needs_storage / needs_public_access / needs_ssl /
  needs_email_login / needs_github_login; omit = open decision point,
  true = plan the branch, false = plan the exclusion) join the now
  optional manage_type. Output is phase-structured: decision_points,
  pre_creation (route branch, OBS bucket decision with full-credential
  rule, security-group prep with the cannot-attach-later warning,
  KooCLI flavor/disk-type acquisition), creation (two-job wait for
  route A), post_creation (EIP + three security-group rules +
  mandatory api_external_url sync + probe; CCM certificate purchase as
  external dependency for https; email/GitHub setup with secret
  boundaries; access-info delivery), external_dependencies,
  security_notes and the honesty `missing` list. Dead fields
  (recommendation always None, discovery always offline stub) removed.
  Backward compatible: diagnostics/smoke/protocol probes keep passing
  (execution == not_executed preserved). Tests rewritten to cover the
  four intent combinations.
- Skill `rds-supabase-mgr-mcp` v0.5.4: scenario 1 step 1 retitled
  "route and intent"; the agent now asks four questions (database
  route, file storage, public access, https) and feeds the answers to
  plan_supabase_creation to get the phase-structured plan, with
  undecided intents surfaced as decision_points to follow up. Declared
  server floor raised to 0.4.0a9.
- Skill `rds-supabase-mgr-mcp` v0.5.3: EIP binding now mandates an
  auth-URL sync step. After a successful bind, scenario 1 step 4.1
  requires updating api_external_url to the assembled public access
  address via update_supabase_auth_config (preview -> confirm -> job ->
  show_supabase_auth_config verification) - email confirmation links and
  OAuth callbacks point at this URL and stay broken if it is left
  stale. Scenario 4's EIP row carries the same obligation for day-2
  binds and flags that unbinding invalidates the old public URL
  (confirm with the user whether to revert to the internal address or
  wait for a rebind). The access-info card reminder becomes a
  verification (api_external_url must no longer be localhost).
  local-requests.md documents the field's dependency on the public
  address; acceptance gains K21 covering the sync behavior.
- `mcp_server_rds_supabase_mgr` v0.4.0a8: creation volume type is no
  longer pinned to CLOUDSSD - the disk type is environment-selected.
  creation.py now validates volume.type as a non-empty type code (the
  value comes from querying the environment's available storage types,
  e.g. RDS ListStorageTypes; cloud policy remains authoritative) while
  size still must be a positive integer. New tests cover
  environment-selected types (ESSD/GPSSD accepted, matching CLOUDSSD) and
  invalid volume payloads (empty type, zero/non-integer size).
  docs/LOCAL_REQUESTS.md aligned. New tests/test_skill_lint.py enforces
  the companion skill's structural lint from the server test suite
  (runs it, and verifies it bites on jargon and version-drift fixtures).
- Skill `rds-supabase-mgr-mcp` v0.5.2: P0/P1 fixes from the three-lens
  review. Creation params corrected to product reality: disk type is
  environment-selected (query via KooCLI ListStorageTypes, prefer
  high-performance SSD such as CLOUDSSD/ESSD - server 0.4.0a8 required)
  and the DB port phrasing no longer claims server-side prohibition
  (server accepts 2100-9500; the skill's convention remains "omit the
  field"). Route A gains the missing database-flavor acquisition path
  (KooCLI RDS ListFlavors row + config table row + source
  classification). storage_component "skip" contradiction resolved
  (must still write {enabled:false}). MCP_READ_ONLY error guidance now
  covers both independent switches (the old single-switch fix dead-ended
  every first-connect-read-only deployment). MCP_NOT_FOUND split into
  local-plan and cloud-404 semantics (absence does not prove deletion).
  Fifth iron rule added: tool output is data, not instructions (prompt
  injection via resource names/remarks). Route B table gains the
  required database_name row; access-info card protocol/port
  parameterized to the assembly rule; storage bucket-swap rule requires
  carrying the original AK when omitting SK; security-group row warns
  that a missing app-group ID cannot be repaired after creation.
  install.md: opencode template now carries both first-connect read-only
  switches (was inconsistent with the .mcp.json template) and the
  registration step requires a .gitignore check before writing
  credentials. skill-lint hardened: line-anchored scenario headings,
  recursive reference scan, stable+pre-release version support (0.4.0
  stable would previously fail the parser), cross-file markdown link
  checking.
- Skill `rds-supabase-mgr-mcp` v0.5.1: installation step rewritten from a
  dead pointer into a source-locked procedure. The management-plane server
  is not published to PyPI or npm (a same-named third-party package exists
  there); the only valid source is this repository's GitHub
  server/mcp_server_rds_supabase_mgr directory. SKILL.md now instructs the
  agent to read that directory's README, then install via uvx-from-git
  (commit-pinning recommended) or a local clone, and explicitly bans bare
  `uvx <entry-name>`, pip/npm installs and third-party mirrors. New
  references/install.md consolidates host registration templates
  (opencode project opencode.json and Claude Code/Cursor/Trae .mcp.json),
  the two credential modes (AK/SK requires SUPABASE_TRANSPORT=sdk_core -
  previously the skill implied permanent keys could skip it, which would
  leave the server in REST mode ignoring AK/SK entirely and failing every
  call with MCP_PERMISSION_DENIED; that error code is now in the error
  table), the full environment-variable checklist, a ZIP-archive escape
  hatch for blocked git fetches and a three-layer verification flow
  (process / registration / cloud). skill-lint expected-references set
  updated accordingly.
- Skill `rds-supabase-mgr-mcp` v0.5.0: full scenario-based rewrite. The
  skill is now organized around the user journey instead of revision
  history: preparation (five environment items + MCP install/verify with
  repair loop), scenario 1 create-a-usable-application (two creation
  routes, 20-30 minute wait protocol, public network enablement with EIP
  binding and the three security-group rules, access-info delivery),
  scenario 2 use-an-existing-application, scenario 3 on-demand
  enhancements (storage/email/GitHub login with field-level interactive
  guidance), scenario 4 day-2 change quick reference, scenario 5
  access-info query (reusable sub-flow), scenario 6 deletion with a
  residual-resource checklist. Terminology overhauled (台账/账本 → 本地执行记录,
  对账 → 结果核验, 码道 removed, 未决 → 结果不明); the 12 scattered
  disclaimers collapsed into one results-boundary discipline. Eleven
  stale statements fixed against server 0.4.0a7, including the deleted
  SUPABASE_VPC_ENDPOINT guidance and the outdated key whitelist.
  References restructured: workflows.md, six-scenario-matrix.md and
  exception-dialogues.md merged into scenarios.md and acceptance.md;
  local-requests.md rewritten (self-contradiction removed, VPC section
  dropped); requirements.md and open-questions.md moved to docs/pm/ as
  project-management material. New scripts/skill-lint.py enforces the
  scenario structure, the jargon blacklist, the declared-server-version
  ceiling and reference integrity. Confirmed product decisions embedded:
  CLOUDSSD disk type, DB port omitted (backend default 5432), 8443
  full-open only via KooCLI after explicit user confirmation.
- `mcp_server_rds_supabase_mgr` v0.4.0a7: `list_supabase_api_keys` aligned with
  the real backend payload. The description now states the scope: id-bearing
  metadata records for service_role, anon, publishable and secret keys, with
  plaintext values never returned. The whitelist gains `remark` (a field the
  backend actually returns); id/name/status/type are promoted to mandatory
  fields that fail closed when missing; created_time/updated_time/remark are
  nullable; epoch-millisecond timestamps are normalized to RFC 3339 UTC.
  Unknown fields are still dropped rather than passed through — key records
  deliberately keep whitelist semantics, unlike the application projections'
  bounded passthrough. Tests lock the real four-key payload as the fixture
  contract.
- `mcp_server_rds_supabase_mgr` v0.4.0a6: `show_supabase_auth_config` returns a
  normalized configuration object aligned with the real backend payload. The
  description now states its scope: user registration settings, access
  control, identity providers (email and GitHub) and email template
  configuration. All nine top-level fields (enable_account_sign_up,
  enable_anonymous_users, api_external_url, site_url, allow_redirect_urls,
  github_oauth_provider, email_oauth_provider, email_template_config) are
  mandatory and fail closed when missing, with boolean/string/object type
  anchoring; nested sections (smtp_config, the six mailer templates) pass
  through the recursive bounded sanitizer; secrets (SMTP credentials, OAuth
  client secrets) are dropped at any depth while identifiers
  (oauth_client_id, smtp_user) remain; empty strings mean not configured.
  The return no longer echoes limit/offset and its note declares the object
  the baseline for update_supabase_auth_config previews and accepted-plan
  reconciliation. Tests lock the real payload as the fixture contract.
- `mcp_server_rds_supabase_mgr` v0.4.0a5: `show_supabase_application` now
  returns a normalized detail object aligned with the real backend payload.
  The description states its purpose: querying RDS Supabase application
  details — status, SSL, IP addresses and other specifics — from which the
  complete access address can be assembled (scheme from enable_ssl, host
  from public_ip/direct_eip publicly or private_ip/traffic_vip internally,
  port from port; the return note spells out the rule). Mandatory fields
  id/name/mode/status/port/enable_ssl/private_ip/created_time fail closed
  when missing; direct_eip is normalized to public_ip (null when no EIP is
  bound); traffic_vip/manage_ip/updated_time/remark are nullable;
  epoch-millisecond timestamps (including inside nodes[]) become RFC 3339
  UTC; nested objects (spec_flavor, data_volume, nodes, dnat, az_details,
  managed_instance, storage_component) pass through the recursive bounded
  sanitizer; the detail return no longer echoes the meaningless
  limit/offset pagination fields. The list and detail projections now share
  one projector where alias keys are skipped from passthrough only when
  actually consumed. Tests lock the real detail payload as the fixture
  contract.
- `mcp_server_rds_supabase_mgr` v0.4.0a4: `list_supabase_applications`
  response handling corrected against the real backend payload. The list
  envelope is `{total_count, data}` (same family as the api-keys endpoint),
  not `{applications, ...}` — the previous key was inferred from a discovery
  probe mock and is now rejected. The public IP field is `direct_eip` on the
  wire and is normalized to the canonical `public_ip`; `remark` is not
  guaranteed by the backend and becomes a nullable optional field (as is
  `updated_time`). Epoch-millisecond timestamps (`created_time`,
  `updated_time`) are normalized to RFC 3339 UTC with millisecond
  precision. Nested objects and arrays (`az_details`, `managed_instance`,
  `current_actions`, ...) now pass through a recursive bounded sanitizer
  (secret-marked keys dropped at every depth, arrays capped at 100, strings
  at 2000, depth at 8) instead of being silently dropped as non-scalars.
  Mandatory fields remain id/name/public_ip/port/flavor_ref/mode/
  created_time; missing mandatory fields and malformed envelopes still fail
  closed. Tests now lock the real payload as the fixture contract.
- `mcp_server_rds_supabase_mgr` v0.4.0a3: `list_supabase_applications` is now a
  full inventory query — paginated listing of all RDS Supabase applications in
  the current project with sorting and filtering, used to locate a target or
  an available application. New optional parameters: `name` (fuzzy filter),
  `application_id` (exact filter, mirrors the api-keys `key_id` pattern) and
  `sort_key`/`sort_dir` (default `created_time desc`). The `type` filter is
  fixed to `supabase` server-side and cannot be overridden. The response is
  normalized into `{total_count, data}` (mirroring the key metadata
  envelope) and each record is validated to carry the mandatory fields
  id/name/public_ip/port/flavor_ref/mode/created_time/remark — known backend
  aliases (flavor, description, gateway_port, public_ip_address, ...) are
  promoted to the canonical names, missing mandatory fields fail closed as
  `MCP_SDK_ERROR`, and other non-secret fields pass through bounded (arrays
  capped at 100, strings at 2000, secret-marked keys dropped). The tool
  return now echoes `offset` alongside `limit`. 7 new tests; TOOL_CONTRACTS
  records the 0.4.0a3 contract increment.
- `mcp_server_rds_supabase_mgr` v0.4.0a2: `get_supabase_capabilities` now
  describes its actual purpose — listing the available capability scope of
  the RDS Supabase management MCP (transport mode, execution policies,
  implemented operations, six scenario contracts) — instead of the
  narrower "six scenario contract states" wording. The constant
  `cloud_verified: false` field is removed from the payload: a hardcoded
  constant carries no decision-relevant information, and the "offline
  declaration, never cloud status" semantics remain in the tool
  description and the scenario pending items. The protocol test and the
  `diagnostics discover` self-check now validate the manifest shape (six
  scenario contracts, non-empty implemented operations) instead of the
  removed flag. README, README_en and TOOL_CONTRACTS aligned.
- Skills `rds-supabase-web-build` v0.11.6 + `rds-supabase-frontend` v0.2.4:
  uploaded static hosting objects (HTML/CSS/js/images/fonts) must now be
  set to public-read at the **object level** (`-acl=public-read` on every
  upload). OBS uploads default to private object ACLs, which previously
  left anonymous readability dependent on the bucket policy alone — a
  single point of failure that returns 403 at the entry or the CDN origin
  whenever the policy is missing, not yet applied, or overridden by a
  reused bucket's history. The upload discipline in obs-release.md now
  sets the ACL in the same single pass as MIME and Cache-Control and
  spot-checks the entry and representative asset objects via `stat`;
  hosting.md states the object-level hard constraint (distinct from the
  bucket-level public-read policy, and scoped to the hosting bucket —
  private Supabase storage buckets stay private). webapp.json gains
  `frontend.objects_acl`, required to be `public-read` from
  hosting_published onward and enforced by the gate at both the contract
  and stage levels. 3 new tests (79 total).
- Skill `rds-supabase-web-build` v0.11.5: the step-3 storage integration
  is now strictly condition-driven instead of a blanket bucket
  preparation. No backend OBS bucket is ever created unconditionally —
  creation happens only when the storage capability is required AND the
  selected instance is not yet connected. The decision chain: existing
  application selected → first verify its storage connection state via
  the management plane (app details/query tool; user confirmation when
  no direct query path) — already connected to OBS → reuse the existing
  connection, no new bucket, no duplicate integration
  (storage.source=existing); not connected (or a new instance was
  created) → the bucket-preparation flow with the interactive
  reuse/create choice (reuse requires the private-bucket policy
  assessment; creation is a dynamically created PRIVATE bucket with
  least privilege; both forbidden from reusing the frontend hosting
  bucket). State contract and gate follow (source enum gains
  existing); one new test.
- Skill `rds-supabase-web-build` v0.11.4: step 2 now clarifies the
  website's comprehensive design metrics through an interactive
  five-dimension card, confirmed item by item before anything is built
  — style (minimal-modern / business / playful / dark-tech / custom,
  recommended from the target users and context), UI design
  (navigation structure, responsive priority defaulting to
  mobile-first, component-library preference), aesthetics level
  (prototype / standard(default) / premium — motion and detail
  polish), complexity level (simple ≤3 pages / medium 4–8(default) /
  rich >8 with rich interactions, cross-checked against the page
  inventory), and functional interaction feedback (loading / error /
  empty states, full basic set by default). "You decide" answers adopt
  the defaults but are read back for confirmation. Recorded as
  project.design_requirements (style/aesthetics/complexity/ui_notes)
  and machine-enforced: the gate validates the enums and requires the
  object from requirements_confirmed onward; step 6 consumes the
  metrics when generating the frontend (aesthetics drives visual
  investment, complexity bounds page and interaction scale); premium/
  rich choices surface their effort impact in the cost estimate. Two
  new tests.
- Skill `rds-supabase-web-build` v0.11.3: step 1 ends with a five-item
  final verification before environment_ready is written — REGION,
  AK/SK, PROJECT_ID, RDS_ENDPOINT and OBS_ENDPOINT must all be proven
  correct, not merely present. One diagnostics-discover call validates
  four items at once (a response proves the credentials work, the
  region resolves, the project id appears, the RDS endpoint is
  reachable — --probe optional, sdk_core for AK/SK); the OBS endpoint
  is re-probed per the connection-test rules. Any failing item is fed
  back to the user with the measured symptom; the second-input round
  has the user correct just that item, which alone is re-tested —
  still failing means an honest report and NO environment_ready (no
  passing with a broken config). The final check is machine-enforced:
  environment_ready joins the trace-required stages. Also fixes a
  latent miss: local_verified was silently absent from TRACE_REQUIRED
  (indentation mismatch in the v0.9.5 edit) — both stages now enforced.
  One new test.
- Skill `rds-supabase-web-build` v0.11.2: deployment-timing and network
  discipline for the management-plane MCP. Hard install gate: the mgr
  MCP is dynamically installed only after credentials (AK/SK or token),
  endpoint, region and project_id are all correctly obtained and
  verified — any missing item loops back to step 1 instead of retrying
  the install against a broken config (the classic cause of endless
  credential/endpoint errors). Network rules: default is a DIRECT
  connection to the region — proxies are the fallback, never the
  default (forwarding chains are the common failure source in
  intranet/dedicated-line environments; configuring a proxy first is
  forbidden); after install, a connection check must confirm the MCP
  is connected and one query tool (get_supabase_capabilities preferred
  — one is enough) returns normally; only after a direct-connection
  failure is confirmed (network, credential mode, endpoint checked in
  order) may a proxy be explicitly configured, recorded, and re-verified.
  Step 4 carries the same network discipline via its existing
  verification items; the instance_ready whitelist admits get_* query
  tools; step-3 assertion and failure handling follow. One new test.
- Skill `rds-supabase-web-build` v0.11.1: the derived OBS endpoint in
  step 1 is now connection-tested before adoption. The derived
  obs.<region>.myhuaweicloud.com must pass DNS resolution (dig) and an
  HTTP probe (curl -sI, any status code counts as reachable —
  unauthenticated 4xx is expected; the test judges connectivity, not
  authorization). Only a passing endpoint is written back to the
  project config. Non-derivable regions or failed probes prompt the
  user to input the actual endpoint, which is re-tested the same way —
  adopted only on pass, reported honestly when unreachable. The step-1
  output assertion and state contract carry the tested-endpoint
  wording; the environment_ready whitelist admits the probe tools
  (dig/nslookup/curl). One new test.
- Skill `rds-supabase-web-build` v0.11.0: launched now concludes with an
  application card (应用名片) — the final deliverable, output in chat and
  persisted to .hwsupabase/app-card.md. Fields: application name,
  one-line function summary, access URL (with the temporary-mode
  local-only caveat), backend gateway URL, test accounts WITH passwords
  (created for the step-9 user-isolation checks, recorded as
  test_accounts — email/password/note; explicitly carved out of the
  credential red line as app-level demo accounts, not cloud
  credentials, with a reminder to change or remove them before real
  use), data model (tables/RPC from the latest deployment batch),
  tech stack (frontend framework, Supabase backend, hosting mode),
  version info (backend batch, launch time), project-management
  pointers, and usage triggers for update/rollback/decommission.
  webapp.json gains the test_accounts section; the gate validates its
  structure, requires >=2 accounts at launched when the auth capability
  is present, and requires app-card.md to exist at launched. Five new
  tests.
- Skills `rds-supabase-web-build` v0.10.2 + `rds-supabase-frontend` v0.2.3:
  the temporary-access scenario now uses a deterministic custom-domain
  procedure. The domain is fixed as <app-slug>.huaweicloud-rds.com
  (same slug rules as bucket names, short-uuid suffix on empty/conflict
  — reproducible, never random or asked). The flow: bind that domain to
  the hosting bucket via OBS domain management (command verified against
  hcloud obs --help / official docs, never guessed); resolve the OBS
  endpoint's A-record IP (dig / Resolve-DnsName); append an IP→domain
  mapping line to the OS-correct hosts file (Linux/macOS /etc/hosts,
  Windows %SystemRoot%\System32\drivers\etc\hosts) with strict
  safety rules — marker comment rds-supabase-web-build:<project> on
  every line we add, append-only, idempotent skip on same-IP,
  marker-line-only replacement on IP change, existing mappings never
  touched, backup before edit, exact diff shown for user confirmation
  before the privileged write. Verified with curl/browser; the callback
  loop uses this domain as site_url (protocol still follows instance
  SSL). Decommission removes only the marker lines and unbinds the
  custom domain; the gate whitelist admits the DNS/hosts tools
  (dig/nslookup/resolve-dns/curl/tee/printf/powershell) for
  hosting_published and cleanup tools for decommissioned.
- Skills `rds-supabase-web-build` v0.10.1 + `rds-supabase-frontend` v0.2.2:
  the hosting phase now demands an explicit user-confirmed hosting
  scenario, chosen interactively after asset upload and before entry
  configuration (skipping forbidden, no defaulting). temporary —
  prototype/test verification: bind a user-owned or ad-hoc custom
  domain to static website hosting, no domain purchase, no ICP filing,
  no CDN — a lean path to visible results, with its limits (not a
  commercial entry) and upgrade path stated up front. production —
  the full commercial chain: domain purchase, real-name
  authentication, ICP filing (mainland regions), custom-domain binding,
  CDN acceleration and HTTPS certificates. The choice is recorded as
  frontend.hosting_mode (temporary/production) and machine-verified by
  the gate from hosting_published onward; the launch report carries the
  scenario line; CDN refresh is production-only in the playbook; the
  frontend skill's entry prerequisites describe both scenarios. Three
  new tests.
- Skills `rds-supabase-web-build` v0.10.0 + `rds-supabase-frontend` v0.2.1:
  two refinements. (1) Credential resolution in step 1 is now a mandatory
  four-option interactive selection (skipping forbidden): A project
  secrets/ and B project-scoped devkit file are adopted on selection;
  C — any sensed system/user-level credential configuration (global
  devkit login, ~/.config/huaweicloud/, ~/.obsutilconfig, environment
  AK/SK variables) must NOT be used directly: each source is displayed
  (level, file/variable name, account identity — never the secret
  itself) and adopted only after explicit user confirmation, recorded
  as credential_source=external_confirmed; D lets the user designate a
  credential file or input AK/SK/token interactively, persisted into
  project secrets/ (0600, agent never echoes or logs the values).
  The gate enum follows (global_devkit_confirmed → external_confirmed).
  (2) The frontend skill now displays a bucket-creation configuration
  card before creating the OBS hosting bucket and verifies it after
  creation by reading back: storage class multi-AZ preferred (fallback
  single-AZ explained), block-public-access OFF (hard constraint —
  enabled, anonymous reads are denied and static hosting breaks), and
  bucket policy fixed to public-read (anonymous GetObject only, not
  modifiable). web-build step 3 references the same card in its
  create-bucket branch. One new test.
- Skill `rds-supabase-web-build` v0.9.9: the install trigger sentence in
  INSTALL.md now carries the document's full GitHub URL (按照 <INSTALL.md
  URL>，安装 rds-supabase 技能包) so agents without local context can
  fetch the guide directly, and states the post-install deliverables
  explicitly — 装完列出技能列表，并告诉我如何触发 (matching the
  step-3 completion report: installed skill list, trigger examples,
  convention notes).
- Skill `rds-supabase-web-build` v0.9.8: drop `npx skills add` from
  INSTALL.md — the repo is not published to that channel, so the command
  cannot work. It is now explicitly forbidden (agents must not attempt
  CLI/package-manager auto-install); the two install paths are git clone
  (primary) and the ZIP archive escape hatch. The npm prerequisite and
  CLI fallback rules are removed; update/uninstall and FAQ references
  follow the new A/B lettering.
- Skill `rds-supabase-web-build` v0.9.7: README/INSTALL restructure. The
  AI one-click install content now lives solely in INSTALL.md — rewritten
  as a lean agent-facing guide with a fixed structure: install scope
  (skills only; no MCP/credentials/cloud at install time), per-host
  install directories as a dedicated section (project-level paths only,
  forbidden personal-level twins, CLI-fallback rule), a three-step
  procedure (install via A/B/C incl. the ZIP network escape hatch into
  temp dirs, validate, report), update/uninstall, and a trimmed FAQ
  (incl. the multi-project isolation note). README.md shrinks to
  overview + framework diagram + install pointer (one natural-language
  sentence, details delegated to INSTALL.md) + MCP source table; the
  duplicated install steps, directory table, escape hatch and agent
  execution notes are removed from README. Stale counts fixed (six
  specialized skills, steps one-nine) across README, INSTALL and the
  SKILL.md frontmatter description, which also now reflects the
  declarative-backend, local-test and function-graph wording.
- Skill `rds-supabase-web-build` v0.9.6: fix a cross-project configuration
  leak reported in multi-project use — starting the skill in project B
  would find region / AK / SK already "configured", because step 1 never
  scoped WHERE those values come from. Root causes fixed: (1) "已配置 →
  采用" accepted same-named variables from the agent process / shell /
  global environment (values set by another project or the machine);
  step 1 now declares the project's .hwsupabase/ as the ONLY
  authoritative source and refuses process/global env reads — env var
  names are injected into MCP processes from project config only;
  (2) Region / endpoints / PROJECT_ID had no project-level persistence —
  webapp.json gains a mandatory environment section (region /
  rds_endpoint / obs_endpoint / project_id / credential_source), and
  diagnostics-discover results must be written back into it;
  (3) "devkit 优先" silently adopted the machine-global devkit login
  state (shared across projects) — credentials now resolve through a
  three-tier priority: project secrets/ → project-scoped devkit file
  (HUAWEICLOUD_DEVKIT_CREDENTIALS_FILE) → global devkit login ONLY after
  explicit user confirmation, recorded as global_devkit_confirmed;
  (4) MCP launch env in steps 3/4 now states the injection source
  (project config, process scope). webapp-gate machine-verifies the
  environment contract and requires the section from environment_ready
  onward. Four new tests.
- Skill `rds-supabase-web-build` v0.9.5: the pipeline is now nine steps — a
  local test & verification step (步骤七 本地测试验证, breakpoint local_verified)
  is inserted between frontend generation and hosting. The frontend runs
  locally (dev server or built-artifact preview) wired to the real deployed
  backend gateway via supabase-js; L0 basic-function cases are incubated
  from the step-2 confirmed scenarios (at least one positive plus a key
  negative per scenario, covering page rendering, core CRUD, auth flows,
  RLS visibility and error paths), confirmed by the user, then executed in
  a fix-and-rerun loop until every case passes (two consecutive failures
  of the same case aborts with a report; backend defects loop back through
  step 5 incremental batches). The artifact .hwsupabase/gates/
  5-local-test-report.md records one T-numbered line per case — gate
  check-gate --number 5 machine-verifies at least five passed lines and
  zero failed ones; check-stage --stage local_verified enforces the
  breakpoint with trace. All downstream steps renumbered (构建与托管 →
  step 8, 端到端上线 → step 9), including the --verify stages, progress
  board, skill-lint pipeline (now nine steps) and every cross-reference.
  Four new tests.
- Skills `rds-supabase-web-build` v0.9.4 + `rds-supabase-mgr-mcp` (doc): step 2 is
  now 需求澄清与设计 — multi-turn dialogue or SDD spec-driven design around
  scenario × function × boundary (no omissions, no divergence, focused),
  from which the RDS Supabase BaaS capability matrix is extracted and
  assessed per capability (CRUD / RPC / auth / Storage / Realtime /
  pgvector), recorded as project.baas_capabilities. When the scenario has
  file/image/video management needs, step 3 must prepare a DEDICATED
  private OBS storage bucket and connect it via update_supabase_storage —
  reuse of the frontend hosting bucket is forbidden (public-read bucket
  reuse is a privilege escalation and privacy exposure). Storage bucket
  selection follows the same interactive discipline (no skipping): reuse
  requires a bucket-policy safety assessment (private only — any public
  read / anonymous GetObject / public listing fails the assessment and
  stops the flow); creation is always a private bucket with least
  privilege. webapp.json gains a storage section (bucket_name / source /
  connected) and the capability list; webapp-gate machine-verifies the
  capability enum, the storage contract, bucket-name inequality against
  the hosting bucket, and enforces storage presence + connected=true from
  instance_ready onward when the storage capability is required. The
  mgr-mcp skill carries the same private-bucket baseline for
  update_supabase_storage. Five new tests.
- Skill `rds-supabase-web-build` v0.9.3: the hosted frontend entry protocol
  now follows the instance SSL state, mirroring the step-4 data-plane rule.
  ssl_enabled=true → stable_url must be HTTPS (domain and certificate
  ready); ssl_enabled=false → HTTP entry, no certificate, HTTPS forbidden —
  an HTTPS page calling the HTTP gateway is mixed content and gets blocked
  by browsers, leaving the site broken. The certificate prerequisite in
  step 3 applies only when the frontend publishes over HTTPS; step 7
  carries the rule at build/publish and callback-loop (site_url /
  redirect_uris follow the same protocol); the launch checklist gains an
  entry-protocol-consistency row and drops its blanket HTTPS wording.
  webapp-gate machine-verifies from hosting_published onward: reads the
  frontend record's stable_url via record_ref, requires the file and
  stable_url to exist, and rejects protocol mismatches (HTTPS entry with
  SSL disabled = mixed content; HTTP entry with SSL enabled). Four new
  tests cover the contract.
- Skills `rds-supabase-web-build` v0.9.2 + `rds-supabase-mcp` v2.6.1: the
  dynamically installed MCPs are now strictly project-scoped. Registration
  goes ONLY into the current project's project-level MCP config, adapted
  per host — Claude Code `<project>/.mcp.json` (mcpServers), CodeArts
  `<project>/.codeartsdoer/`, OfficeAce the host's project-level config
  (bounded by the project root), opencode `<project>/opencode.json` or
  `.opencode/` (mcp key) — with every user-level and system-level location
  explicitly forbidden (~/.claude.json user scope, Claude Desktop
  claude_desktop_config.json, ~/.config/opencode/ global config,
  ~/.codeartsdoer/ personal twin, system managed configs). User-level
  registration would expose this project's MCPs and credentials to every
  other project on the machine — a boundary leak. Hosts offering only
  user-level registration: stop and report, do not register. Hard rules
  added across install.md, SKILL.md, workflow-stages.md and lifecycle.md:
  verify the entry landed in project-level config and no user/system
  location was touched before client reload; credential-bearing config
  files go into .gitignore at 0600; uv tool install / pip install into
  user- or system-level environments are forbidden (uvx is a one-shot
  cached run, not an installation, leaving no registry entry or CLI
  binary); teardown of the registration at decommission. webapp.json
  gains a mandatory mcp section (registration_scope: project;
  config_paths.mgr/data as project-relative dot paths) — webapp-gate
  machine-verifies the scope enum and rejects absolute, '~' and '..'
  paths; mcp.config_paths.mgr is required from instance_ready onward and
  .data from mcp_connected onward. Five new tests cover the contract.
  install.md's old guidance (opencode.jsonc / claude_desktop_config.json /
  .cursor/mcp.json as "common locations") removed — those are user-level
  sinks.
- Skill `rds-supabase-web-build` v0.9.1: backend development now produces a
  one-click cleanup script alongside init.sql. Step 5 generates
  .hwsupabase/teardown.sql in the same pass as init.sql — single-transaction
  wrapped, fully idempotent (DROP ... IF EXISTS), dependency-safe ordering
  (policies → triggers → tables → functions/RPC → roles → schema), and
  covering only the objects recorded in the deployment manifest; it is
  refreshed after every incremental batch. webapp.json gains
  backend.teardown_ref (mandatory from backend_deployed onward); webapp-gate
  verifies the file exists and covers every object of the latest deployment;
  the decommissioned whitelist now admits execute_sql so the teardown can be
  executed via the data-plane MCP at decommission time (explicit user
  confirmation, per lifecycle.md — needless when the whole instance is
  deleted, essential when the PG instance is retained or reused). Four new
  tests cover the contract.
- Skill `rds-supabase-web-build` v0.9.0: resource acquisition in step 3 now
  requires explicit interactive selection, skipping forbidden, for BOTH
  resources. The Supabase application access method (use existing /
  create new) must be chosen by the user from a selection list before
  proceeding — no defaulting on the user's behalf. The OBS bucket access
  method follows the same rule: when reusing, only buckets qualifying for
  static hosting are presented as candidates (non-public buckets are
  filtered out of the list entirely); when creating, the bucket name
  defaults to the application name transliterated to a lowercase
  letter/digit/hyphen slug (3-63 chars), with a short uuid suffix appended
  on name conflict, and the final name is user-confirmed before creation.
  webapp.json gains a mandatory `obs` section from instance_ready onward
  (bucket_name / source / naming_basis); webapp-gate validates the bucket
  name pattern, the source enum, and the naming_basis coupling; six new
  tests cover the contract. Wording across SKILL.md and workflow-stages.md
  is professional and formal throughout.
- Skill `rds-supabase-web-build` v0.8.8: complete tool-docking audit of the
  managed side. Frontend lane now carries its tools: dev card names
  supabase-js (the SDK integration, usage-skill governed), deploy card
  names rds-supabase-frontend 技能 · KooCLI (bucket creation and artifact
  upload), and the runtime OBS card states its origin (由 frontend 技能 +
  KooCLI 创建托管). Backend dev-to-deploy transition is labeled
  best-practices 质量门 (the mandatory gate before generation); the backend
  deploy wording clarifies execute_sql as initialization. Report caption
  spells out the full docking chain. Geometry verified: zero overlaps.
- Skill `rds-supabase-web-build` v0.8.7: the backend dev card in the
  comparison canvas now speaks to general readers — the internal artifact
  name init.sql is replaced by 声明式后端 with its contents spelled out:
  数据建模（库表定义）, CRUD 自动生成 · Data-Function RPC, 权限配置 ·
  初始化数据. The report's value proposition, section-1 caption, work-item
  mapping row 1 and conclusion use the same declarative framing (init.sql
  kept only as the parenthetical artifact name in the detailed mapping).
  Geometry verified: zero overlaps.
- Skill `rds-supabase-web-build` v0.8.6: tool docking in the comparison
  canvas is now precise — the backend deployment card names both actors
  (rds-supabase-mgr-mcp · 创建实例, rds-supabase-mcp · execute_sql 单事务),
  the Supabase instance card states its origin (由 rds-supabase-mgr-mcp
  动态创建), and the tooling strip focuses on the skill orchestration
  (rds-supabase Skill 全程编排). The report caption spells out the same
  docking; geometry re-verified clean.
- Skill `rds-supabase-web-build` v0.8.5: the managed side of the comparison
  canvas now shows tool participation at the transitions — a tooling strip
  in the deployment row (rds-supabase Skill orchestration + control-plane
  and data-plane MCP), the backend dev-to-deploy arrow labeled 数据面 MCP,
  and the deploy-to-runtime transition labeled gate 机器核验. The report
  caption states the same. Geometry re-verified clean.
- Skill `rds-supabase-web-build` v0.8.4: the comparison diagrams are merged
  into ONE left-right canvas (assets/compare-modes.svg) — traditional mode
  on the left, managed mode on the right, both flowing through the same
  development/deployment/runtime rows. Small-print clutter is stripped
  (no English annotations, no badges, no extra components such as
  FunctionGraph or SLB): every card carries a title plus one keyword line
  only. Two bold color-coded conclusion strips state the four core
  differences directly (dev cycle, deploy steps, frontend servers, backend
  entities). The two per-mode SVGs are removed; the report embeds the
  single merged image.
- Skill `rds-supabase-web-build` v0.8.3: comparison diagrams restructured as
  integrated single canvases and de-colloquialized. Each SVG is now one
  large diagram with two entity lanes — frontend and backend — flowing
  through development (tooling and artifacts), deployment (ECS, network,
  microservices for the traditional mode) and runtime, with labeled
  interaction links on every arrow (build tools, deploy actions, user
  access paths for static assets and APIs). Band labels use formal terms
  (开发态/部署态/运行态 with English annotations; 自行运维 / 云托管 / 声明式
  chips replace colloquial wording). Layer headline metrics sit at each
  band's top-right corner (dev cycle, deploy steps). The report itself is
  word-swept for formal language (ten-item mapping title, entity-count
  table headers, value proposition and conclusion phrasing).
- Skill `rds-supabase-web-build` v0.8.2: the comparison report's topology
  diagrams are now rendered images (assets/compare-traditional.svg,
  assets/compare-managed.svg) replacing ASCII art. Each diagram is organized
  into three explicit layers — development (dev cycle headline), deployment
  (step-count headline) and runtime (entity composition). Frontend and
  backend each appear as a single entity: the traditional backend is a
  dashed group of two self-managed entities (backend services -> database),
  while the managed backend is one Supabase instance card (Kong gateway +
  Postgres + GoTrue/RLS built in) and the frontend is the OBS bucket with
  zero servers. Short connectors only — no long crossing lines; layout
  verified programmatically (text/line/card overlap checks) plus visual
  review. Embedded into USER_GUIDE_REPORT.md section 1.
- Skill `rds-supabase-web-build` v0.8.1: all repo download sites now land
  in a unique temporary directory. git clones, ZIP-archive downloads and
  unzip extractions (README escape hatch, INSTALL methods B/C, SKILL.md
  stage-3/4 escape blocks, workflow-stages stage-3/4 inline commands) run
  under `TMP=$(mktemp -d)` with quoted $TMP paths, so nothing pollutes the
  project directory or the home directory. Browser downloads of the ZIP
  URL must land in a temporary directory as well. Skill-pack installs
  clean up immediately (`rm -rf "$TMP"`); MCP escape-hatch directories
  stay retained while the server runs (uv run points into them) and are
  cleaned after the MCP stops.
- Skill `rds-supabase-web-build` v0.8.0: new human-facing deliverable
  USER_GUIDE_REPORT.md — a comparison report of the traditional
  frontend→backend→database self-built chain versus the Supabase+OBS
  fully managed chain orchestrated by this skill. Covers architecture
  topology diagrams (ASCII), a ten-item workload mapping (backend
  development, CICD building, initial microservices, ECS purchase,
  network configuration, deployment, frontend Node.js hosting — each
  mapped to its managed equivalent or elimination), a self-managed
  entity count (servers/runtimes/pipelines/nginx/auth all drop to zero),
  delivery-efficiency and security-model comparisons (GoTrue+RLS+advisors
  with machine-verified acceptance versus self-built auth), lifecycle
  operations (update/rollback/decommission), and an honest boundary
  statement. Linked from the README.
- Skill `rds-supabase-web-build` v0.7.7: per-host project-level skill paths
  are now pinned explicitly — CodeArts installs to
  <project>/.codeartsdoer/skills/ (mandatory), opencode to
  <project>/.opencode/skills/, Claude Code to <project>/.claude/skills/.
  The constraint is presented as a table pairing each allowed project-level
  directory with its forbidden personal-level twin, calling out that the
  CodeArts pair shares the same directory name with a different root
  (<project>/ vs ~/). System built-in/system-level directories remain
  forbidden; CLI results landing in personal-level locations are discarded
  in favor of manual copy into the pinned project-level paths.
- Skill `rds-supabase-web-build` v0.7.6: install-section wording polished —
  the README section is renamed from the noun-pile-up "一句话自然语言安装"
  to "一句话安装" (matching INSTALL.md), the short-form instruction now reads
  as a natural sentence (按本技能 README 的「一句话安装」指引…) instead of the
  awkward 「…」节 construct, and the redundant "所有 Skill 技能" is corrected
  to "所有技能" with the project-level directory spelled out.
- Skill `rds-supabase-web-build` v0.7.5: install location is now a hard
  constraint — the skill pack goes only into the current project's
  project-level skill directory (opencode <project>/.opencode/skills/,
  Claude Code <project>/.claude/skills/, CodeArts in-project skills dir).
  Installing into system built-in/system-level directories or personal-level
  directories (~/.config/opencode/skills/, ~/.claude/skills/,
  ~/.codeartsdoer/skills) is forbidden: skill versions travel with the
  project and must not affect or pollute other projects or the global
  machine environment — the same principle as the project-scoped credential
  isolation. The `npx skills add` path now requires verifying the landing
  directory and falling back to manual copy if it defaults to a
  personal-level location. Stated in INSTALL.md (constraint block + method
  B paths), the README execution notes, and the SKILL.md prerequisites.
- Skill `rds-supabase-web-build` v0.7.4: grammar fix in the README short-form
  install instruction — the section name is now properly delimited
  (「一句话自然语言安装」节) instead of a bare noun pile-up, and the sentence
  ends with a complete object (装完汇报安装结果) instead of a dangling
  并汇报.
- Skill `rds-supabase-web-build` v0.7.3: network escape hatch for downloads.
  When git access fails or stalls (proxy exhausted, two consecutive failures
  or 30s without progress), both the skill-pack install and the dynamic MCP
  installs switch immediately — no endless retries — to the repository ZIP
  archive (curl --fail --max-time 120, or a direct browser download which
  often rides a different accelerated path), then proceed with local
  `uv run --directory` for the MCP servers. The ZIP archive is an official
  source of this repository (commit-pinned form `.../archive/<commit>.zip`),
  so source locking is preserved and the PyPI ban stands. Stated in the
  README one-sentence install, INSTALL.md (new method C), SKILL.md stage-3/4
  command blocks and the source-lock note, and the stage-3/4 playbook.
- Skill `rds-supabase-web-build` v0.7.2: the stage-3 control-plane env spec
  now states the credential modes explicitly — REST token
  (HUAWEICLOUD_AUTH_TOKEN, default SUPABASE_TRANSPORT=rest) or AK/SK,
  which REQUIRES SUPABASE_TRANSPORT=sdk_core (reads
  HUAWEICLOUD_ACCESS_KEY/HUAWEICLOUD_SECRET_KEY, optional
  HUAWEICLOUD_SECURITY_TOKEN); starting with AK/SK but without sdk_core
  falls back to REST mode and fails on the missing token. The stage-1
  discover command carries the same requirement. Stage 4 states that the
  data-plane server has no SUPABASE_TRANSPORT parameter and never uses
  Huawei Cloud AK/SK (gateway triple only).
- Skill `rds-supabase-web-build` v0.7.1: project-scoped credential isolation
  is now a red line — login state and credentials live only inside the
  current project at `<project>/.hwsupabase/secrets/` (0600, owner-only,
  git-ignored; `SUPABASE_REQUESTS_FILE` registry at
  `.hwsupabase/requests.json`). Writing credentials into global or system
  environment variables (shell profiles, launchd, session exports) and into
  personal-level configs (`~/.config/huaweicloud/credentials.json`,
  `~/.obsutilconfig`) is forbidden — pre-existing personal files belong to
  other tooling and projects and are never migrated, deleted or overwritten;
  MCP credentials are injected at process scope only. Rotation affects this
  project's `.hwsupabase/` alone and cannot pollute other projects. Stated
  in the prerequisites, the red-line notes, stage-1/3/4 playbook actions and
  a new credentials-storage section of the project-state contract.
- Skill `rds-supabase-function-graph` v0.1.1: secret-management aligned with
  the same project-scoped isolation — protected files live under
  `<project>/.hwsupabase/secrets/` and never in global or personal-level
  locations.
- Skill `rds-supabase-web-build` v0.7.0: data-plane access scheme now follows
  the instance SSL state — when the RDS Supabase application has SSL disabled
  the gateway is accessed over plain HTTP and HTTPS is NOT forced. The rule
  is stated explicitly at the stage-4 install/enable points (SKILL.md and
  workflow-stages.md), recorded as the new optional `instance.ssl_enabled`
  field in the webapp.json contract (maintained by stage 3 and by
  `change_supabase_ssl`), and honored by `webapp-gate.py --verify`: HTTP is
  allowed when `ssl_enabled` is false, while HTTPS stays mandatory when the
  field is true or missing (loopback exemption for tests unchanged). Two
  new gate tests cover both branches.
- Skill `rds-supabase-web-build` v0.6.5: the complex-business-logic boundary is
  no longer "v2 later" — routing table, SKILL boundary row and stage-2
  edge detection now route to the dedicated function-graph skill; install
  expectations updated to eight skills.

### Added

- Skill `rds-supabase-function-graph` v0.1.0: new skill hosting custom
  server-side business code (transaction notifications, external-system
  integration, complex domain logic, high-security processing) on Huawei
  Cloud FunctionGraph. Six-stage workflow (env check with KooCLI command-
  surface self-calibration → logic decomposition → code generation →
  deployment → security verification & release → frontend integration),
  zero-dependency Node.js 18 template with in-function GoTrue JWT
  verification, exact-origin CORS, idempotency and a unified error
  contract; shared-APIG entry with `fgs-gate.py` as the independent
  verifier (unauthenticated 401 / invalid-JWT 401 / valid-JWT 200 /
  exact CORS origin machine-checked), functions.json artifact contract,
  per-stage KooCLI whitelist and 21 pytest cases with a local fake APIG.
  Secrets only ever live in function environment variables assembled via
  `--cli-json-file` by the user — the agent never sees plaintext.
- Skill `rds-supabase-usage` v0.2.3: the FunctionGraph routing row and the
  server-side computing section now point to the dedicated
  `rds-supabase-function-graph` skill instead of a "planned skill"
  placeholder.
- Skill `rds-supabase-frontend` v0.2.0: support public-read OBS with direct-domain
  or CDN hosting; add internal-cloud discovery, repeat-release fast path,
  policy coverage preflight and single-pass MIME/cache metadata uploads.
  Batch GET evidence collection and v3 acceptance records reduce baseline
  checks to entry/assets plus Supabase when required, retaining conditional
  route/cache/update/rollback checks and v2 history compatibility.


### Added

- `mcp_server_rds_supabase_mgr` v0.4.0a1: `diagnostics discover` — credential-driven
  context discovery. With only a REST token or AK/SK configured, the new CLI mode
  queries IAM (token project-scope self-check in REST mode, project listing in
  sdk_core mode), derives the standard regional RDS origin per project
  (`https://rds.{region}.myhuaweicloud.com`) and emits a per-candidate
  `suggested_env` block (`HUAWEICLOUD_PROJECT_ID` + `SUPABASE_RDS_ENDPOINT`) for
  selection; `--probe` adds one bounded read-only reachability check. An
  explicitly configured `SUPABASE_RDS_ENDPOINT` always wins; probes never echo
  resource values or credentials. Both transports now accept extra request
  headers (used for the IAM `X-Subject-Token` self-query) and sign IAM paths at
  domain scope. Removed the `SUPABASE_VPC_ENDPOINT` parameter: security-group
  tools share the same native RDS origin and project identity as the rest of the
  server (internal adaptation, no separate entry to configure). 136 tests at
  93.00% coverage.
- Skill `rds-supabase-web-build` v0.1.0: full-stack development orchestrator for
  RDS Supabase — a one-sentence triggered end-to-end pipeline (requirements →
  resource preparation with dynamic control-plane MCP bring-up and OBS bucket
  creation → data-plane MCP dynamic install → backend init.sql generation and
  five-step deployment behind the best-practices mandatory gate → frontend
  generation behind the usage mandatory gate → OBS+CDN build, hosting and the
  auth-callback loop → three-layer launch verification), plus lifecycle
  workflows (update / rollback / decommission / key rotation). Thick-workflow
  orchestrator: stage state machine with gates, resumability via
  .hwsupabase/webapp.json, routing-only integration with the five specialist
  skills. Credentials never touch the agent (devkit-first injection with a
  semi-automatic fallback). Explicit progressive document-loading strategy:
  SKILL.md stays resident; the five references load on stage/operation timing
  (manifest contract before first read/write, stage playbook on stage entry,
  routing matrix on demand, launch checklist at verification, lifecycle after
  launch). v1 backend boundary: data layer only; complex
  business logic (payments / third-party calls / long tasks) is out of scope;
  FunctionGraph routing deferred to v2.
- Skill `rds-supabase-web-build` v0.1.1: field-tested fixes from a Claude Code
  run — stage-1 configuration completeness check (control-plane credentials,
  project ID and endpoint; frontend/OBS AK/SK and region) with an explicit
  fill-in checklist instead of silent failure, endpoint fallback to explicit
  user specification when discovery cannot derive it, and hard MCP install
  source locking (repo-only uvx git template or local `uv run --directory`;
  never search PyPI or third-party registries for same-named packages). The
  install guide gains a per-MCP address and install-method table with the
  anti-drift warning; negative routing and stage playbooks updated to match.
- Skill `rds-supabase-web-build` v0.1.2: stage-1 instance sourcing made
  ask-first and leak-proof — the agent must explicitly ask whether to create a
  new RDS Supabase application or use an existing one; the existing-application
  path lists all available applications via the control-plane MCP
  (`list_supabase_applications`) for user selection, verifies status, and then
  immediately obtains the gateway URL plus both API keys (Anon and Service
  Role) through the control-plane key-delivery tool. Credential acquisition is
  marked as mandatory on both the create and select paths — missing any item
  blocks the stage-2 data-plane MCP dynamic install. The webapp.json instance
  contract gains a `source` field (`created` / `selected`).
- Skill `rds-supabase-web-build` v0.2.0: stability overhaul — stage completion
  moves from self-assertion to mechanical verification. New
  `scripts/webapp-gate.py` (stdlib-only, ships with the skill) validates the
  webapp.json contract, stage progression and ordering, credential-like value
  leakage, mandatory-gate artifacts and trace hygiene; stage playbooks
  restructured into input → action-sequence → output-assertion form with
  🤖(gate)/🔍(agent) assertion markers, per-stage tool allow/deny lists, and a
  golden-path example per stage. New execution discipline in SKILL.md: stage
  header declaration, one-stage-per-turn, wait protocol (30s polling cadence,
  20-attempt cap), two-strike failure escalation (no third blind retry), and
  per-action trace records in .hwsupabase/trace.jsonl. Mandatory gates ③④ are
  materialized as rule→location mapping checklists
  (.hwsupabase/gates/3-rules-checklist.md, 4-sdk-contract-checklist.md) that
  the gate script enforces.
- Skill `rds-supabase-web-build` v0.2.1: RLS verification semantics made
  precise — REST acceptance now requires anon data visibility to match the
  design (public tables return rows, protected tables return an empty set; RLS
  rejection is a restricted result, never a 4xx/5xx status code), and a
  mandatory multi-user isolation spot check joins the stage-6 connectivity
  layer (two test accounts created via data-plane user management must see
  none of each other's rows). The uvx install templates now carry a
  production pin recommendation (`@<commit>` on the `--from` git URL) in
  both the install guide and the stage-1 playbook.
- Skill `rds-supabase-web-build` v0.2.2: SKILL.md gains a self-bootstrapping
  natural-language install section — a single paste-ready sentence installs
  the whole suite (six skills from `skills/huaweicloud-supabase/` plus the
  control-plane MCP, repo-source-locked, credentials devkit-first with a
  fill-in checklist, data-plane MCP deliberately deferred to stage 2) without
  handing the agent any file first; a short variant covers the case where the
  skill is already in context, and a four-point execution digest links to
  INSTALL.md for the full guide and troubleshooting.
- Skill `rds-supabase-web-build` v0.2.3: complete URLs for the dynamically
  installed MCPs are now embedded wherever they are referenced — SKILL.md's
  tool section gains a canonical install-source table (per-MCP entry script,
  full GitHub README URL on the default branch, copy-ready uvx commands for
  both planes, and the note that skill packages contain no server/ directory
  so repo-relative paths must always resolve to these URLs). The stage-2
  playbook inlines the full data-plane uvx command and README URL, and the
  routing table's control-plane anchor becomes an absolute URL instead of a
  repo-relative path that dangles when the repo is not cloned.
- Skill `rds-supabase-web-build` v0.3.0: clean separation of concerns between
  the human-facing README and the agent-facing SKILL.md. The framework
  diagram, the one-sentence natural-language install section and the MCP
  install-source table (full URLs, copy-ready uvx commands) move to a new
  skill README.md; SKILL.md now focuses purely on the business workflow —
  scope, stage machine, execution discipline, gates, assertions and failure
  handling — with a single pointer to the README/INSTALL for install matters.
  The skills validator no longer forbids README.md in skill directories
  (INSTALLATION_GUIDE.md and QUICK_REFERENCE.md remain forbidden).
- Skill `rds-supabase-web-build` v0.3.1: the SKILL.md workflow is now rendered
  as explicit per-stage step blocks (### ⓪–⑥, numbered actions, breakpoint
  per stage, fixed stage cadence: declaration → actions → manifest write →
  gate → report) instead of a dense table. The two dynamic-MCP-install steps
  inline the complete copy-ready commands (git uvx template and local
  `uv run --directory`, plus the exact env variable names) at the exact point
  they are used, so the agent never has to search for how to install.
- Skill `rds-supabase-web-build` v0.3.2: workflow steps are now labelled
  explicitly as 步骤一–步骤七 (Step One through Step Seven) instead of the
  compact circled-number markers — headers, in-text stage references, the
  README/INSTALL guides, the reference playbooks and the SVG diagram badges
  all use the same explicit step numbering; the gate script's two messages
  that embedded circled numbers switch to enum-based wording.
- Skill `rds-supabase-web-build` v0.3.3: professional-language pass over the
  whole skill. Colloquial and AI-flavored wording is replaced with formal,
  precise terminology throughout SKILL.md, README, INSTALL and the reference
  playbooks — the orchestrator is described as a top-level orchestration
  skill (顶层编排技能) rather than a "commander"; stage assertions are
  通过条件 (pass conditions) instead of casual "thresholds"; credential
  handling speaks of configuration templates with placeholders and users
  copying real values, not "skeletons" and "fill-in"; the stage-header
  declaration, wait protocol, two-strike rule and other discipline items
  are reworded to formal specification language ("连续失败中止规则",
  "单次回复推进单一步骤", "暂不安装", "先询问后执行", "不得代用户默认选择",
  "不得遗漏"); all remaining stage-vs-step terminology is unified to
  步骤 (except the control-plane two-phase confirmation term 两阶段确认);
  the SVG's migrations chip reads 禁改 instead of the casual 不碰.
- Skill `rds-supabase-web-build` v0.4.0: the workflow now opens with a
  dedicated environment check-and-configuration step. New 步骤一 · 环境检查
  与配置 (breakpoint `environment_ready`) verifies and resolves credentials,
  Region, the RDS service endpoint (configured, or derived via
  diagnostics discover, or explicitly user-specified), the OBS endpoint
  (derived from Region by KooCLI/SDK) and PROJECT_ID (configured or selected
  via discovery) — any item that cannot be obtained produces an explicit
  missing-items checklist reminding the user to set it; no guessing, no
  skipping, no defaults. All seven business steps shift to 步骤二–步骤八
  across SKILL.md, the playbooks, README/INSTALL, routing table and project
  state contract; the stage machine and the gate script gain
  environment_ready as the first breakpoint. The framework SVG is re-laid
  out as an eight-stage pipeline (badges 一–八, new environment-check stage
  box and routing card) and re-verified with zero geometric overlaps.
- Skill `rds-supabase-web-build` v0.5.0: machine verification replaces
  self-assertion for cloud facts. webapp-gate.py gains --verify: the REST
  layer (always, using SUPABASE_URL/ANON/SERVICE_ROLE keys from the process
  environment) checks deployed-table visibility and reachability and
  hard-verifies that exposed tables answer 200 with the anon key; the
  optional MCP layer (--mcp-command) spawns the data-plane MCP read-only and
  verifies table inventory, RLS enablement with at least one policy per
  exposed table, and security advisors against deployed tables. The
  deployments contract gains an optional exposed field (subset of objects)
  that drives the anon-reachability hard check. Mandatory-gate 3 mappings
  must now cite real best-practices rule-file stems — the gate validates
  them against the sibling skill's references inventory (graceful skip with
  a note when the sibling skill is absent; WEBAPP_GATE_RULES_DIR overrides
  for tests). The gate script itself is now under test: 21 cases in
  tests/test_webapp_gate.py covering contract failures, stage ordering,
  gate artifacts, trace hygiene and --verify against local fake REST and
  MCP servers. Stage-5 and stage-8 playbooks require running
  check-stage --verify (with --mcp-command at stage 5), and the execution
  discipline forbids accepting agent self-reports for cloud facts.
- Skill `rds-supabase-web-build` v0.6.0: adherence materialization and
  interaction upgrades. Trace enforcement — check-stage now fails when a
  tool-active stage (instance_ready onward) claims passed without ok trace
  records for that stage; a new check-whitelist subcommand audits every trace
  record against per-stage tool allow-lists and surfaces out-of-stage tool
  use. A new scripts/skill-lint.py structurally lints the skill itself
  (eight sequential step headers with matching names and breakpoints in
  SKILL.md and the playbook, enum order in the project-state contract, gate
  STAGES equality, and reference-file existence) — its first run caught a
  real stage-name mismatch between SKILL.md and the playbook. Interaction:
  a progress board keeps an eight-item todo list in sync with the host todo
  tool (in-progress / completed / blocked per step, rebuilt from webapp.json
  on session re-entry), missing-configuration and requirement checklists are
  rendered as alignment cards (item | status ✅/❌/⏳ | how to obtain), and
  node bulletins announce long-running actions before and after
  (action · object · outcome). Trace contract documents tool naming and the
  two audits; 27 tests cover the gate suite including the new checks.
- Skill `rds-supabase-web-build` v0.6.1: install scope corrected to the skill
  pack only. The one-sentence natural-language install and INSTALL.md now
  install just the six skills from this GitHub repository — no MCP servers,
  no credentials and no mcpServers placeholders at install time. Both MCP
  servers are installed dynamically by the skill's own workflow steps
  (control plane → stage 3, data plane → stage 4), still repo-source-locked
  with copy-ready commands in the README/INSTALL reference table; the stage-1
  environment check gains a uv/uvx availability item (prerequisite for the
  dynamic MCP installs) with install guidance, and the prerequisites section
  states that the skill pack is the sole install artifact.
- Skill `rds-supabase-web-build` v0.6.2: residual install-time implications
  of the control-plane MCP removed — the frontmatter description, the ASCII
  pipeline overview and the dual-plane section now state uniformly that both
  MCP servers are loaded only when a scenario triggers the skill and are
  installed automatically inside the workflow steps (control plane → stage 3,
  data plane → stage 4, repo sources only), never with the skill package.
- Skill `rds-supabase-web-build` v0.6.3: the progress board becomes
  dual-track and always visible in chat. On top of the host todo-list
  integration, the skill must render a fixed-format full step overview
  table (all eight steps with breakpoints and status markers) in its
  first reply, and re-render the complete table at the head of every
  step report (current step ✅, next step 🔄), giving the user a direct,
  always-current perception of the whole flow.
- Skill `rds-supabase-web-build` v0.6.4: install wording no longer
  hardcodes the skill count — the one-sentence install now installs all
  skills under `skills/huaweicloud-supabase/` completely into the project
  skill directory; the count-free wording is applied consistently across
  the README install section, INSTALL.md and the SKILL.md prerequisites.

- Skill `rds-supabase-frontend` v0.1.0 (renamed from `huawei-supabase-frontend`):
  private OBS + CDN static frontend
  deployment, integration with existing Huawei Cloud RDS Supabase applications,
  build environment preparation, versioned updates and rollbacks. Includes
  self-contained operation references, the v2 release record contract, four
  JSON examples, and a read-only default prompt.

- Skills v2.5.0 (`rds-supabase-mcp`): added `references/install.md`, a one-shot
  AI-agent installation runbook — collect SUPABASE_URL, SUPABASE_ANON_KEY and
  SUPABASE_SERVICE_ROLE_KEY from the user, render the `mcpServers` config from
  the stdio / streamable-http templates, and verify; the skill description now
  also triggers on installation requests.
- Integrated the rds-supabase capability into `huaweicloud/rds-supabase-fullstack`:
  the MCP server now lives at `server/mcp_server_rds_supabase` consuming the
  repository-shared core at `libs/huaweicloud_mcp_core` (path dependency,
  standalone `uv.lock`, server-local `Dockerfile`); the three skills, validation
  docs, examples and the skills contract validator moved with it, and install
  URLs now point at the new repository home
  (`git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase`).

### Fixed

- `mcp_server_rds_supabase_mgr` `wait_supabase_job` timeout handling on Python
  3.10: `asyncio.TimeoutError` and the builtin `TimeoutError` are distinct
  classes before Python 3.11, so a transport-level builtin TimeoutError
  escaped the `except asyncio.TimeoutError` clause and the "retain
  uncertainty" contract of `test_poll_timeout_retains_uncertainty` broke on
  3.10 (the tested baseline was Python 3.12, where the two classes are
  unified). The handler now catches both; the declared
  `requires-python >= 3.10` is honored.

### Changed

- Restructured the control-plane server README to the repository-standard
  template (mcp_server_rc / mcp_server_rfs conventions): bilingual
  README.md + README_en.md with the standard sections (version, overview,
  category, features, tool list with risk levels, usage guide with per-OS uv
  install, environment-variable table, safety mechanisms, guardrails,
  uvx config, natural-language examples, docs index). The dense contract
  notes previously living in the README remain authoritative under docs/
  (TOOL_CONTRACTS, RECOVERY, LOCAL_REQUESTS, RECONCILIATION).
- Aligned the control-plane server delivery (`server/mcp_server_rds_supabase_mgr`)
  with the repository-wide uvx template: added the canonical console-script
  alias `mcp-huaweicloud-rds-supabase-mgr` (`mcp_server_supabase` retained
  for transition), rewrote USER_GUIDE.md around the cross-platform uvx
  install path, converted the MCP config examples to uvx form, and archived
  the Windows offline-bundle workflow docs (WORKSTATION*,
  NEXT_WORKSTATION_PROMPT, RELEASE_*, COMPATIBILITY) under docs/legacy/
  with an explanatory README. Personal-fork release download links were
  removed from organization docs; server README install/verification
  sections now use uv-based commands.
- Switched `mcp_server_rds_supabase` from the vendored 1.2.0 core to the
  repository-shared `libs/huaweicloud_mcp_core` (1.0.0) and deleted the
  vendor tree: the path dependency now points at ../../libs, `build_server`
  is called without the 1.2.0-only `version` kwarg, and the read-only
  interception test was adapted to the 1.0.0 wording. Re-validated: 241 tests
  at 93.92% coverage, ruff/mypy clean, stdio smoke (38 tools, MCP_READ_ONLY
  guard) passing. The Dockerfile now builds from the repository root
  (selective COPY of libs + server sources; root .dockerignore added,
  server-local .dockerignore removed). Known behavior change: boolean env
  vars (e.g. HUAWEICLOUD_MCP_READ_ONLY) are parsed leniently by the 1.0.0
  core — invalid values no longer fail fast at startup. SDK baseline pinned
  via constraint-dependencies (huaweicloudsdkcore/iam==3.1.220,
  typing-inspection==0.4.4) for reproducible offline resolution.
- Grouped the five rds-supabase-* skills under `skills/huaweicloud-supabase/`
  (`rds-supabase-usage`, `rds-supabase-frontend`, `rds-supabase-mcp`,
  `rds-supabase-mgr-mcp`, `rds-supabase-postgres-best-practices`); the
  `huaweicloud-mcp-dev` skill stays at the top level. Repo organization only:
  `scripts/validate_skills.py` now discovers skills recursively so grouped
  skills remain contract-checked, and README / README_en / UPSTREAM / mgr
  server doc paths were updated.
- Repositioned the `rds-supabase-mgr-mcp` skill as "RDS Supabase 全托管生命周期管理"
  (fully-managed lifecycle management): the SKILL.md title and description now
  state the creation / configuration / secure-access / deletion lifecycle
  scope explicitly; operational content is unchanged.
- Renamed the platform development skill `rds-supabase` to `rds-supabase-usage`
  (v0.2.2): directory, SKILL.md name field, both READMEs, the
  validate_skills EXPECTED_SKILLS entry and the unreleased CHANGELOG name
  mentions. Routing references in the `rds-supabase-mcp` and
  `rds-supabase-postgres-best-practices` descriptions now point at
  `rds-supabase-usage`; skill content is otherwise unchanged.
- Renamed the control-plane skill `huaweicloud-supabase` to `rds-supabase-mgr-mcp`
  (directory and SKILL.md name) to align with the renamed mgr server
  `mcp_server_rds_supabase_mgr`. Skill content is unchanged; README, the mgr
  server docs (USER_GUIDE, MIGRATION, RELEASE_0.3.8a1), MCP config example
  labels and the validate_skills exemption entry were updated. The server's
  local state directory default (`~/.local/state/huaweicloud-supabase`) is
  intentionally retained to preserve existing execution ledgers.
- Renamed the control-plane server directory `server/rds-supabase-mgr-mcp` to
  `server/mcp_server_rds_supabase_mgr` to match the `mcp_server_*` convention
  (management plane: RDS Supabase instance lifecycle — creation, configuration,
  secure access, deletion). Directory-only rename: the Python
  distribution/module/CLI (`mcp_server_supabase`) and its path dependency on
  `../../libs/huaweicloud_mcp_core` are unchanged; README and MIGRATION.md
  references updated.
- Skills v2.6.0 (`rds-supabase-mcp`): SKILL.md repositioned for the Web
  full-stack development pipeline. The description and overview now lead with
  the two-stage flow — dynamic installation once the RDS Supabase instance is
  created or selected (install.md), then backend development where backend
  code ships as init.sql migration scripts (DDL, GRANT and other
  initialization SQL); added an "instance onboarding" workflow section ahead
  of the general workflow and wired install.md into the prerequisites,
  triggers, boundary table and reference routing.
- Skills v0.2.0: professional skill-authoring pass (superpowers
  writing-skills + Anthropic best practices). `rds-supabase-usage`: removed
  workflow summary from the description (SDO shortcut trap), added
  overview and a skill-routing table, tightened RLS checklist items via
  cross-references to rule files, added a symptom-first debugging quick
  reference (42501, empty results, prepared-statement errors, 403 on new
  tables). `rds-supabase-postgres-best-practices`: description keyword
  coverage extended (N+1, OFFSET pagination, deadlock, upsert, FK
  indexes, JSONB, full-text search, pooling), added a 33-row
  symptom-to-rule-file index table and a grep hint for retrieval.

### Fixed

- Scheduled-task routing corrected: pg_cron is a platform capability (only
  the current test instance lacks it). `rds-supabase-usage` v0.2.1 routes
  scheduled jobs to pg_cron; FunctionGraph now covers serverless compute
  and webhooks only. `rds-supabase-postgres-best-practices` v0.3.0 adds
  the `rds-scheduled-jobs` rule (UTC scheduling, parameter-template
  precondition, job inspection) with description trigger and index row.
  `rds-supabase-mcp` v2.4.1 moves get_cron_job_history back to the
  available tool group (6 deployment-unavailable tools remain).

### Added

- Skill `rds-supabase-usage` v0.1.0: platform development skill adapted from
  supabase/agent-skills `supabase` (MIT, baseline c9be0e9) - agent discipline
  principles and security checklist adapted to the deployment, MCP-first
  workflows (execute_sql single-transaction batches), FunctionGraph routing
  for serverless compute, skill-feedback mechanism.
- Skill `rds-supabase-postgres-best-practices` v0.1.0: Postgres rule library
  adapted from supabase/agent-skills (MIT, baseline c9be0e9) - 31 upstream
  rules (17 verbatim, 9 link-replaced, 5 rewritten for the deployment:
  JWT-claims identity, RDS parameter template, UUIDv7 guidance) plus 3 new
  `rds-` rules (jwt-claims-rls, parameter-template, auth-helpers).
- Repo-level skills contract validator `scripts/validate_skills.py`
  (format contract A1-A7; includes the version-drift tripwire missing
  upstream).
- `UPSTREAM.md`: MIT attribution and derivation record for the two adapted
  skills; per-skill `LICENSE` files bundle the upstream MIT notice.

### Changed

- Skill `rds-supabase-mcp` v2.4.0: frontmatter `name` aligned with the
  directory rename (huawei-cloud-rds-supabase-manage -> rds-supabase-mcp),
  description now carries explicit trigger context and cross-routes to the
  new skills.

### Changed

- Skill v2.3.0: release-grade editorial pass over the skill and its
  references. Fixed a tool-name error (get_rls_policies ->
  list_rls_policies), completed the tool table with the seven
  deployment-unavailable tools, added explicit trigger conditions to the
  scope section, and documented the two-layer read-only mechanism
  (execute_sql read_only vs HUAWEICLOUD_MCP_READ_ONLY). Redundant and
  colloquial wording was removed throughout. execute_sql is documented
  with its hierarchy clear: the primary function is running arbitrary SQL;
  executing DDL/migration scripts (init.sql) to deploy the backend
  definition is its typical use. Positioning: an improvement of
  HenkDz/selfhosted-supabase-mcp managing the self-hosted Supabase BaaS
  platform on Huawei Cloud RDS.

## [0.4.0] - 2026-11-05

### Removed

- Direct database connections: `DATABASE_URL` (the upstream `--db-url`) is no
  longer accepted, and the psycopg dependency, the pg-first fallback chain,
  the transaction helpers and the startup auto-deploy of the `execute_sql`
  function were removed with it. The cloud instance is only reachable through
  the Kong gateway; `execute_sql` now requires the service-role key and runs
  exclusively over the hardened RPC channel.

### Changed

- `execute_sql` precheck message updated (service-role key only).
- `list_storage_buckets`, `list_storage_objects` and
  `list_realtime_publications` now report that direct connections are
  unsupported (RPC-channel rework pending).
- `generate_typescript_types` returns a structured failure explaining that
  direct connections are not supported (rework decision pending).

## [0.3.0] - 2026-11-05

### Changed

- The auth users tool group (`list_auth_users`, `get_auth_user`,
  `create_auth_user`, `update_auth_user`, `delete_auth_user`) now operates
  through the official GoTrue auth admin API (`/auth/v1/admin/users`) with the
  service-role key instead of requiring a direct database connection, making
  all five tools usable on the cloud-managed instance (verified end-to-end:
  full create/read/update/delete lifecycle, pagination cross-checked against
  the SQL channel).

### Added

- Client support for the auth admin API (GET/POST/PUT/DELETE with the
  service-role key, transport-error envelopes).

### Deprecated

- Upstream deviations kept for signature parity and documented: field names
  mapped back to the upstream shape (app_metadata -> raw_app_meta_data),
  timestamps in GoTrue ISO 8601 text, role create/update has no effect (the
  admin API always assigns 'authenticated'; role-only updates fail with a
  clear message).

## [0.2.0] - 2026-11-04

### Removed

- `apply_migration` and `list_migrations`: the cloud-managed instance has no
  direct database connection and no `supabase_migrations` bookkeeping table,
  so both tools could never succeed in this deployment. Schema changes go
  through `execute_sql`.
- `list_edge_functions`, `get_edge_function_details` and
  `list_edge_function_logs`: the Edge Functions runtime is not part of this
  deployment, so the tools had no data source.

  The tool surface now intentionally differs from the upstream TypeScript
  server (38 tools instead of 43); the E2E comparison driver records this as
  an intentional deviation. `generate_typescript_types` is retained pending a
  rework decision.

## [0.1.0] - 2026-11-04

### Added

- Python re-implementation of the TypeScript `rds-supabase-mcp` server with
  all 43 upstream tools: identical names, parameters, defaults, return shapes
  and error messages; upstream registration order preserved.
- Shared `huaweicloud_mcp_core` vendored into the workspace (config /
  credentials / errors / security guard / guardrails / output envelopes /
  standard runner), matching the `huaweicloud-gaussdb-mcp` repository form.
- Three-layer package structure: `tools` (thin registration with
  `@mcp.tool()` + `@guard(risk=...)`), `service` (upstream execute() logic,
  exact upstream error text), `client` (httpx PostgREST RPC, psycopg direct
  access, fallback chain, startup RPC probe and hardened auto-deploy).
- Risk lanes for every tool: 35 READ, 8 WRITE; read-only mode, guardrail
  rules, protected lists, JSONL audit and output masking from the shared core.
- Upstream tools-config whitelist (`RDS_SUPABASE_TOOLS_CONFIG`) with upstream
  fallback semantics and messages.
- Hardened `execute_sql` SQL asset (`sql/mcp-execute-sql.sql`): service_role
  only, in-database `read_only` statement whitelist, first-keyword dispatch;
  embedded verbatim in the client (drift-checked by tests).
- Bilingual READMEs (root and server), CONTRIBUTING, SECURITY, Dockerfile,
  CI workflow, examples, and the agent skill package
  `skills/rds-supabase-mcp`.
- Engineering trail under `docs/`: implementation plan, GaussDB case
  replication spec, upstream functional contract, and E2E validation evidence.

### Changed

- Auto-deployed `execute_sql` function upgraded from the upstream embedded
  v1 definition to the hardened v4.1 asset (identical call interface;
  `read_only` now enforced in-database) — a deliberate security carry-over
  from the upstream repository's hardened deployment.

### **Validation**

- 291 unit tests, 95.45% coverage (gate: 90%); ruff and mypy strict clean.
- E2E dual-server comparison against the TypeScript server on a live Huawei
  RDS Supabase instance; evidence in `docs/validation/`.
