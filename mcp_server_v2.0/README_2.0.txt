代码生成器：gen_from_openapi.py

	该脚本读取 ss_environment_api.yaml，按每个 operationId 动态生成 MCP 工具函数，自动拼装 Path/Query/Body，并通过 X-Auth-Token 鉴权。生成出来的是一个可运行的 MCP 服务器。

=============================================================================================================
bash

# 准备环境变量
    	export HW_AUTH_TOKEN="<你的Token>"
	export SERVICESTAGE_BASE="https://servicestage.<分区id>.myhuaweicloud.com"

# 运行生成器，输出到 mcp_server_generated.py
	python gen_from_openapi.py > mcp_server_generated.py

# 以 stdio 方式运行 MCP
	python mcp_server_generated.py
