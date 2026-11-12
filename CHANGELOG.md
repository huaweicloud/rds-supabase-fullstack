# Changelog

All notable user-visible changes are recorded here. This project follows
semantic versioning.

## [Unreleased]

### Changed

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
