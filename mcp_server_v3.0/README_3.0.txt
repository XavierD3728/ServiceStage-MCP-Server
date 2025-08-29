V3.0 面向 Agent 的“高层场景封装 + 工程化加强版”

该版本把“控制台里的核心用户旅程”打包成直观、高层的工具，适合自然语言调用。例如：

“创建环境并开通资源”

“导出环境模板/查询部署记录/回滚环境”

“（Bonus）在 CAE 创建应用与组件、扩容缩容”

“（Bonus）在 FunctionGraph 创建/调用函数”


===============================================================

bash
	export HW_AUTH_TOKEN="<你的token>"
	export SERVICESTAGE_BASE="https://servicestage.<你的分区id>.myhuaweicloud.com"
	export CAE_BASE="https://cae.<你的分区id>.myhuaweicloud.com"
	export FG_BASE="https://functiongraph.<你的分区id>.myhuaweicloud.com"
# 可选：代理 & 证书

	export HTTPS_PROXY="<你的proxy代理地址>"
	export HTTP_VERIFY=false   # 若你本地调试需要忽略证书

# 运行MCPserver
	python mcp_agent_ops.py
