from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("HuaweiServiceStage")
token  = os.getenv("HW_AUTH_TOKEN")
project_id = "<你的项目id>"                        # 修改项目id
API_BASE = "<你的ServiceStage分区api-base-url>"    # 修改api_url

def get_auth_header():
    # token = os.getenv("AUTH_TOKEN")
    if not token:
        raise ValueError("缺少 AUTH_TOKEN 环境变量")
    return {"X-Auth-Token": token}

@mcp.tool()
async def get_environments(project_id: str, name: str = "", environment_id: str = "", enterprise_project_id: str = "") -> dict:
    """获取项目下环境列表"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments"
    headers = get_auth_header()
    params = {k: v for k, v in locals().items() if k not in ['project_id', 'url', 'headers'] and v}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, params=params)
        return resp.json()

@mcp.tool()
async def create_environment(project_id: str, env_data: dict) -> dict:
    """创建新的 ServiceStage 环境"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments"
    headers = get_auth_header() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(url, headers=headers, json=env_data)
        return resp.json()

@mcp.tool()
async def get_environment_detail(project_id: str, environment_id: str) -> dict:
    """获取指定环境的详细信息"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments/{environment_id}"
    headers = get_auth_header()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers)
        return resp.json()

@mcp.tool()
async def update_environment(project_id: str, environment_id: str, env_data: dict) -> dict:
    """修改指定环境的配置"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments/{environment_id}"
    headers = get_auth_header() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.put(url, headers=headers, json=env_data)
        return resp.json()

@mcp.tool()
async def delete_environment(project_id: str, environment_id: str) -> str:
    """删除指定环境"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments/{environment_id}"
    headers = get_auth_header()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.delete(url, headers=headers)
        return "✅ 删除成功" if resp.status_code == 204 else f"❌ 删除失败: {resp.status_code}"

@mcp.tool()
async def get_environment_logs(project_id: str, environment_id: str) -> dict:
    """获取环境的操作日志"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments/{environment_id}/logs"
    headers = get_auth_header()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers)
        return resp.json()

@mcp.tool()
async def change_environment_os(project_id: str, environment_id: str, os_body: dict) -> dict:
    """更换环境的基础操作系统"""
    url = f"{API_BASE}/v3/{project_id}/cas/environments/{environment_id}/change-os"
    headers = get_auth_header() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(url, headers=headers, json=os_body)
        return resp.json()

@mcp.tool()
async def list_component_auto_tunings(project_id: str, application_id: str, component_id: str) -> dict:
    """获取组件自动调优记录列表"""
    url = f"{API_BASE}/v3/{project_id}/cas/applications/{application_id}/components/{component_id}/auto-tunings"
    headers = get_auth_header()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers)
        return resp.json()

@mcp.tool()
async def show_component_auto_tuning_info(project_id: str, application_id: str, component_id: str) -> dict:
    """查看组件自动调优详细信息"""
    url = f"{API_BASE}/v3/{project_id}/cas/applications/{application_id}/components/{component_id}/auto-tunings/detail"
    headers = get_auth_header()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers)
        return resp.json()

@mcp.tool()
async def create_component_auto_tuning(project_id: str, application_id: str, component_id: str, tuning_data: dict) -> dict:
    """触发组件的自动调优任务"""
    url = f"{API_BASE}/v3/{project_id}/cas/applications/{application_id}/components/{component_id}/auto-tunings"
    headers = get_auth_header() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(url, headers=headers, json=tuning_data)
        return resp.json()

@mcp.tool()
async def cancel_component_auto_tuning(project_id: str, application_id: str, component_id: str) -> dict:
    """取消当前组件的自动调优任务"""
    url = f"{API_BASE}/v3/{project_id}/cas/applications/{application_id}/components/{component_id}/auto-tunings/cancel"
    headers = get_auth_header()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(url, headers=headers)
        return resp.json()

@mcp.tool()
async def post_autotuning_logs(project_id: str, application_id: str, component_id: str, logs: dict) -> dict:
    """上传自动调优日志"""
    url = f"{API_BASE}/v3/{project_id}/cas/applications/{application_id}/components/{component_id}/auto-tunings/logs"
    headers = get_auth_header() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(url, headers=headers, json=logs)
        return resp.json()

@mcp.tool()
async def post_autotuning_result(project_id: str, application_id: str, component_id: str, result: dict) -> dict:
    """上传调优结果"""
    url = f"{API_BASE}/v3/{project_id}/cas/applications/{application_id}/components/{component_id}/auto-tunings/result"
    headers = get_auth_header() | {"Content-Type": "application/json"}
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(url, headers=headers, json=result)
        return resp.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
