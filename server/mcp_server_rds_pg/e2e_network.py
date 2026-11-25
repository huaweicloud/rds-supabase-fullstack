# E2E driver for network/EIP module (run via: uv run python e2e_network.py <phase>)
# Phases: read | create | eip | plan
import asyncio, json, os, sys, time

AK = "HPUAQ7RIEWIUJTO98UVW"
SK = "UCFOACM0ohu51hsShY1aAqQy2MOIzt8Y0kC90Er5"
REGION = "cn-north-4"
CWD = "/Users/tianjia/Desktop/pg mcp/mcp_server_rds_pg"
TEST01 = "2a942f4a987c4b38aa3c6ed4434742fcin03"

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def env():
    return {
        **os.environ,
        "HUAWEICLOUD_ACCESS_KEY": AK,
        "HUAWEICLOUD_SECRET_KEY": SK,
        "HUAWEICLOUD_REGION": REGION,
        "RDS_PG_ENABLE_WRITES": "true",
    }


async def call(session, tool, args=None):
    result = await session.call_tool(tool, args or {})
    return json.loads(result.content[0].text)


def brief(obj, keys):
    out = {}
    for k in keys:
        out[k] = obj.get(k)
    return out


async def main():
    phase = sys.argv[1]
    ts = str(int(time.time()) % 10000)
    params = StdioServerParameters(command="uv", args=["run", "mcp-huaweicloud-rds-pg"], cwd=CWD, env=env())
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if phase == "read":
                print("== 1 discover_pg_network ==")
                d = await call(session, "discover_pg_network")
                print(json.dumps({k: d.get(k) for k in
                    ["enterprise_projects", "placement_recommendation", "security_group_plan"]}, ensure_ascii=False))
                print("vpcs:", json.dumps(d.get("vpcs"), ensure_ascii=False))
                print("subnets:", json.dumps(d.get("subnets"), ensure_ascii=False))
                print("security_groups:", json.dumps(d.get("security_groups"), ensure_ascii=False))

                print("== 2 list_pg_vpcs ==")
                v = await call(session, "list_pg_vpcs")
                print(json.dumps(v, ensure_ascii=False))

                # find default vpc
                items = v.get("items") or v.get("vpcs") or []
                dv = next((x for x in items if x.get("name") == "default_vpc"), None)
                print("default_vpc:", json.dumps(dv, ensure_ascii=False))

                print("== 3 list_pg_subnets(default_vpc) ==")
                s = await call(session, "list_pg_subnets", {"vpc_id": dv["id"]})
                print(json.dumps(s, ensure_ascii=False))

                print("== 4 list_pg_security_groups ==")
                g = await call(session, "list_pg_security_groups")
                print(json.dumps(g, ensure_ascii=False))

                print("== 5 list_pg_enterprise_projects ==")
                e = await call(session, "list_pg_enterprise_projects")
                print(json.dumps(e, ensure_ascii=False))

            elif phase == "create":
                print(f"== 6 create_pg_vpc e2e-vpc-{ts} ==")
                p = await call(session, "create_pg_vpc", {"name": f"e2e-vpc-{ts}", "cidr": "172.20.0.0/16", "confirm": False})
                print(json.dumps(p, ensure_ascii=False))
                plan_id = p.get("plan_id")
                r = await call(session, "create_pg_vpc", {"name": f"e2e-vpc-{ts}", "cidr": "172.20.0.0/16", "confirm": True, "plan_id": plan_id})
                print(json.dumps(r, ensure_ascii=False))
                vpc_id = (r.get("result") or {}).get("vpc", {}).get("id") or (r.get("vpc") or {}).get("id")
                # also check envelope keys
                print("VPC_ID:", vpc_id)

                print(f"== 7 create_pg_subnet e2e-subnet-{ts} ==")
                p = await call(session, "create_pg_subnet", {"vpc_id": vpc_id, "name": f"e2e-subnet-{ts}", "cidr": "172.20.1.0/24", "availability_zone": "cn-north-4a", "confirm": False})
                print(json.dumps(p, ensure_ascii=False))
                plan_id = p.get("plan_id")
                r = await call(session, "create_pg_subnet", {"vpc_id": vpc_id, "name": f"e2e-subnet-{ts}", "cidr": "172.20.1.0/24", "availability_zone": "cn-north-4a", "confirm": True, "plan_id": plan_id})
                print(json.dumps(r, ensure_ascii=False))

                print("== 8 create_pg_security_group e2e-sg ==")
                sg_name = f"e2e-sg-{ts}"
                p = await call(session, "create_pg_security_group", {"name": sg_name, "open_5432_from": "172.21.0.0/24", "confirm": False})
                print(json.dumps(p, ensure_ascii=False))
                plan_id = p.get("plan_id")
                r = await call(session, "create_pg_security_group", {"name": sg_name, "open_5432_from": "172.21.0.0/24", "confirm": True, "plan_id": plan_id})
                print(json.dumps(r, ensure_ascii=False))

                # verify via list
                print("== verify lists ==")
                v = await call(session, "list_pg_vpcs")
                items = v.get("items") or v.get("vpcs") or []
                print("vpc visible:", [x for x in items if x.get("name") == f"e2e-vpc-{ts}"])
                s = await call(session, "list_pg_subnets", {"vpc_id": vpc_id})
                print("subnet visible:", json.dumps(s, ensure_ascii=False))
                g = await call(session, "list_pg_security_groups")
                gi = g.get("items") or g.get("security_groups") or []
                print("sg visible:", [x for x in gi if x.get("name") == sg_name])

            elif phase == "eip":
                print(f"== 10 create_pg_eip e2e-eip-{ts} traffic ==")
                p = await call(session, "create_pg_eip", {"billing_type": "traffic", "name": f"e2e-eip-{ts}", "confirm": False})
                print(json.dumps(p, ensure_ascii=False))
                plan_id = p.get("plan_id")
                r = await call(session, "create_pg_eip", {"billing_type": "traffic", "name": f"e2e-eip-{ts}", "confirm": True, "plan_id": plan_id})
                print(json.dumps(r, ensure_ascii=False))
                eip = (r.get("result") or {}).get("eip") or r.get("eip") or {}
                print("EIP_ID:", eip.get("id"), "ADDR:", eip.get("public_ip_address"))

                print("== 11 bind_pg_instance_eip(test01) ==")
                p = await call(session, "bind_pg_instance_eip", {"instance_id": TEST01, "public_ip_id": eip["id"], "confirm": False})
                print(json.dumps(p, ensure_ascii=False))
                plan_id = p.get("plan_id")
                r = await call(session, "bind_pg_instance_eip", {"instance_id": TEST01, "public_ip_id": eip["id"], "confirm": True, "plan_id": plan_id})
                print(json.dumps(r, ensure_ascii=False))

                print("== show_pg_instance check ==")
                inst = await call(session, "show_pg_instance", {"instance_id": TEST01})
                print("public_ips:", json.dumps((inst.get("instance") or inst).get("public_ips"), ensure_ascii=False))

                print("== 12 unbind_pg_instance_eip(test01) ==")
                p = await call(session, "unbind_pg_instance_eip", {"instance_id": TEST01, "confirm": False})
                print(json.dumps(p, ensure_ascii=False))
                plan_id = p.get("plan_id")
                r = await call(session, "unbind_pg_instance_eip", {"instance_id": TEST01, "confirm": True, "plan_id": plan_id})
                print(json.dumps(r, ensure_ascii=False))

                inst = await call(session, "show_pg_instance", {"instance_id": TEST01})
                print("public_ips after unbind:", json.dumps((inst.get("instance") or inst).get("public_ips"), ensure_ascii=False))

            elif phase == "plan":
                print("== 15 plan_pg_instance_creation(needs_public_access=true) ==")
                r = await call(session, "plan_pg_instance_creation", {"needs_public_access": True})
                print(json.dumps(r, ensure_ascii=False))


asyncio.run(main())
