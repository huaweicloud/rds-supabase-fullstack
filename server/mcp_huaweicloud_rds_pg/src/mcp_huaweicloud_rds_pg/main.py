# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Huawei Cloud RDS for PostgreSQL MCP Server entrypoint."""

from huaweicloud_mcp_core.server import run_standard

from mcp_huaweicloud_rds_pg.server import mcp


def main() -> None:
    run_standard(mcp, service_name="rds-pg")


if __name__ == "__main__":
    main()
