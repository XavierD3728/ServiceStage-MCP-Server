# mcp_agent_ops.py
from mcp.server.fastmcp import FastMCP
import httpx, os, asyncio, time, random, atexit
from typing import Callable, Any, Dict

# -------------------- MCP 基础 --------------------
mcp = FastMCP("HuaweiServiceStageAgentOps")

SERVICESTAGE_BASE = os.getenv("SERVICESTAGE_BASE", "https://servicestage.cn-north-4.myhuaweicloud.com")
CAE_BASE          = os.getenv("CAE_BASE", "https://cae.cn-north-4.myhuaweicloud.com")
FG_BASE           = os.getenv("FG_BASE", "https://functiongraph.cn-north-4.myhuaweicloud.com")

VERIFY_TLS = os.getenv("HTTP_VERIFY", "true").lower() != "false"
PROXIES    = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
TIMEOUT_S  = int(os.getenv("HTTP_TIMEOUT", "60"))

def _auth() -> Dict[str, str]:
    token = os.getenv("HW_AUTH_TOKEN")
    if not token:
        raise ValueError("HW_AUTH_TOKEN is not set")
    return {"X-Auth-Token": token}

# -------------------- HTTP 客户端（共享 + 重试 + 统一返回） --------------------
class HTTP:
    def __init__(self):
        if PROXIES:
            os.environ.setdefault("HTTP_PROXY", PROXIES)
            os.environ.setdefault("HTTPS_PROXY", PROXIES)

        # 仍然保留证书与超时设置
        self.client = httpx.AsyncClient(
            verify=VERIFY_TLS,
            timeout=TIMEOUT_S,   # 可传 float/int 或 httpx.Timeout
        )
    async def request(self, method: str, url: str, max_retries: int = 2, **kwargs) -> tuple[int, dict]:
        """
        统一请求：
        - 网络错误指数退避重试（最多 max_retries 次）
        - 统一返回结构：2xx 返回 data；非 2xx 返回 {"error": True, "status_code": code, "data": data}
        """
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                r = await self.client.request(method, url, **kwargs)
                try:
                    data = r.json()
                except Exception:
                    data = {"status_code": r.status_code, "text": r.text}
                if r.is_error:
                    return r.status_code, {"error": True, "status_code": r.status_code, "data": data}
                return r.status_code, data
            except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                last_exc = e
                await asyncio.sleep(0.3 * (2 ** attempt) + random.random() * 0.1)
        return 599, {"error": True, "status_code": 599, "data": {"message": str(last_exc) if last_exc else "network error"}}

    async def close(self):
        await self.client.aclose()

_http_singleton = HTTP()
def _http() -> HTTP:
    return _http_singleton

@atexit.register
def _close_http():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # best-effort fire-and-forget
            loop.create_task(_http().close())
        else:
            loop.run_until_complete(_http().close())
    except Exception:
        pass

# -------------------- 通用轮询助手 --------------------
async def poll_until(
    fn: Callable[[], Any],
    interval: float = 2.0,
    timeout: float = 180.0,
    ok: Callable[[Any], bool] = lambda x: True
) -> dict:
    """
    周期调用 fn()，直到 ok(result) 为 True 或超时。
    - 若 fn 返回 {"error": True, ...}，则直接返回该错误。
    - 超时返回 {"error": True, "status_code": 408, "data": {"message": "poll timeout"}}
    """
    start = time.time()
    while True:
        res = await fn()
        if isinstance(res, dict) and res.get("error"):
            return res
        try:
            if ok(res):
                return res
        except Exception:
            # ok 判定异常视为未就绪
            pass
        if time.time() - start > timeout:
            return {"error": True, "status_code": 408, "data": {"message": "poll timeout"}}
        await asyncio.sleep(interval)

# ======================================================================
# ServiceStage 高层工具（按 console 用户旅程封装）
# ======================================================================

@mcp.tool()
async def ss_list_environments(project_id: str, name: str = "", limit: int = 100, offset: int = 0) -> dict:
    """列出环境（可按名称过滤）"""
    url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments"
    params = {"name": name, "limit": limit, "offset": offset}
    code, data = await _http().request("GET", url, headers=_auth(), params=params)
    return data

@mcp.tool()
async def ss_create_environment(project_id: str, environment_name: str, cluster_id: str, description: str = "") -> dict:
    """创建环境并绑定已有 CCE 集群"""
    url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments"
    body = {"name": environment_name, "description": description, "type": "cce", "cluster_id": cluster_id}
    headers = _auth() | {"Content-Type": "application/json"}
    code, data = await _http().request("POST", url, headers=headers, json=body)
    return data

@mcp.tool()
async def ss_add_env_resource(project_id: str, environment_id: str, resource_kind: str, spec: dict) -> dict:
    """向环境添加 IaC 资源（例如 'rds','dcs','cce-cluster' 等）"""
    url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments/{environment_id}/iac-resources"
    body = {"kind": resource_kind, "spec": spec}
    headers = _auth() | {"Content-Type": "application/json"}
    code, data = await _http().request("POST", url, headers=headers, json=body)
    return data

@mcp.tool()
async def ss_provision_env_resources(project_id: str, environment_id: str) -> dict:
    """开通环境内的真实资源"""
    url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments/{environment_id}/iac-resources/provision"
    code, data = await _http().request("POST", url, headers=_auth())
    return data

@mcp.tool()
async def ss_get_env_provision_logs(project_id: str, environment_id: str) -> dict:
    """查询最近一次开通的事件/日志"""
    url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments/{environment_id}/iac-resources/latest-provision/events"
    code, data = await _http().request("GET", url, headers=_auth())
    return data

@mcp.tool()
async def ss_snapshot_and_rollback(project_id: str, environment_id: str, action: str, record_id: str = "", template_uri: str = "") -> dict:
    """
    快照/回滚工具集合：action in ['list_records','rollback','export']
    - list_records: 获取部署记录/回滚点
    - rollback: 按 record_id 回滚
    - export: 导出环境模板（可传 template_uri 到 OBS 等）
    """
    headers = _auth() | {"Content-Type": "application/json"}
    if action == "list_records":
        url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments/{environment_id}/records"
        code, data = await _http().request("GET", url, headers=_auth())
    elif action == "rollback":
        url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments/{environment_id}/rollback"
        body = {"record_id": record_id}
        code, data = await _http().request("POST", url, headers=headers, json=body)
    elif action == "export":
        url = f"{SERVICESTAGE_BASE}/v3/{project_id}/cas/environments/{environment_id}/export"
        body = {"template_uri": template_uri} if template_uri else {}
        code, data = await _http().request("POST", url, headers=headers, json=body)
    else:
        data = {"error": True, "status_code": 400, "data": {"message": f"unknown action: {action}"}}
    return data

# -------- 高层“一键式”封装 --------

@mcp.tool()
async def ss_create_env_with_rds(project_id: str, env_name: str, cluster_id: str, rds_flavor: str = "db.m1.small") -> dict:
    """
    一键：创建环境 -> 添加 RDS 资源 -> 开通资源 -> 轮询日志至完成
    仅需核心参数：project_id, env_name, cluster_id, rds_flavor
    """
    # 1) 创建环境
    env = await ss_create_environment(project_id, env_name, cluster_id)
    if isinstance(env, dict) and env.get("error"):
        return env
    env_id = (env.get("id") or env.get("environment_id"))
    if not env_id:
        return {"error": True, "status_code": 500, "data": {"message": "missing environment id", "raw": env}}

    # 2) 添加 RDS 资源（根据实际 API schema 进一步扩充 spec）
    rds_spec = {"engine": "MySQL", "flavor": rds_flavor}
    add_res = await ss_add_env_resource(project_id, env_id, "rds", rds_spec)
    if isinstance(add_res, dict) and add_res.get("error"):
        return add_res

    # 3) 开通资源
    prov = await ss_provision_env_resources(project_id, env_id)
    if isinstance(prov, dict) and prov.get("error"):
        return prov

    # 4) 轮询日志直到成功（根据平台返回调整判断条件）
    async def _pull_logs():
        return await ss_get_env_provision_logs(project_id, env_id)
    logs = await poll_until(_pull_logs, interval=3, timeout=300, ok=lambda x: "SUCCESS" in str(x).upper())

    return {"environment_id": env_id, "add_resource": add_res, "provision": prov, "logs": logs}

@mcp.tool()
async def ss_rollback_env(project_id: str, environment_id: str, record_id: str) -> dict:
    """按指定记录 ID 回滚环境，并返回结果（如需可追加状态轮询）"""
    res = await ss_snapshot_and_rollback(project_id, environment_id, action="rollback", record_id=record_id)
    return res

# ======================================================================
# CAE（Cloud Application Engine）封装（Bonus）
# ======================================================================

@mcp.tool()
async def cae_create_application(project_id: str, environment_id: str, app_name: str, description: str = "") -> dict:
    """创建 CAE 应用（需在 Header 添加 X-Environment-ID）"""
    url = f"{CAE_BASE}/v1/{project_id}/cae/applications"
    headers = _auth() | {"Content-Type": "application/json", "X-Environment-ID": environment_id}
    body = {
        "apiVersion": "v1",
        "kind": "Application",
        "metadata": {"name": app_name, "annotations": {"description": description}}
    }
    code, data = await _http().request("POST", url, headers=headers, json=body)
    return data

@mcp.tool()
async def cae_create_component(project_id: str, application_id: str, comp_name: str, image: str, replicas: int = 1) -> dict:
    """在 CAE 应用下创建组件"""
    url = f"{CAE_BASE}/v1/{project_id}/cae/applications/{application_id}/components"
    headers = _auth() | {"Content-Type": "application/json"}
    body = {
        "apiVersion": "v1",
        "kind": "Component",
        "metadata": {"name": comp_name},
        "spec": {"replicas": replicas, "template": {"containers": [{"name": comp_name, "image": image}]}}
    }
    code, data = await _http().request("POST", url, headers=headers, json=body)
    return data

@mcp.tool()
async def cae_scale_component(project_id: str, application_id: str, component_id: str, replicas: int) -> dict:
    """调整 CAE 组件副本数"""
    url = f"{CAE_BASE}/v1/{project_id}/cae/applications/{application_id}/components/{component_id}"
    headers = _auth() | {"Content-Type": "application/json"}
    body = {"spec": {"replicas": replicas}}
    code, data = await _http().request("PUT", url, headers=headers, json=body)
    return data

# ======================================================================
# FunctionGraph（FG）封装（Bonus）
# ======================================================================

@mcp.tool()
async def fg_create_function(
    project_id: str,
    func_name: str,
    runtime: str,
    handler: str,
    code_type: str = "inline",   # "inline" | "obs"
    code: str = "",              # inline 时传源码；obs 时传 OBS 路径
    memory_size: int = 256,
    timeout: int = 30,
    package: str = "default"
) -> dict:
    """创建 FG 函数；当 code_type='obs' 时，code 传 OBS URL"""
    url = f"{FG_BASE}/v2/{project_id}/fgs/functions"
    headers = _auth() | {"Content-Type": "application/json"}
    body = {
        "func_name": func_name,
        "runtime": runtime,
        "handler": handler,
        "memory_size": memory_size,
        "timeout": timeout,
        "package": package,
        "code_type": "inline" if code_type == "inline" else "obs",
    }
    if code_type == "inline":
        body["func_code"] = {"file": "index.zip", "link": "", "code": code}
    else:
        body["code_url"] = code
    code_status, data = await _http().request("POST", url, headers=headers, json=body)
    return data

@mcp.tool()
async def fg_invoke(project_id: str, function_urn: str, payload: dict, async_invoke: bool = False) -> dict:
    """调用 FG 函数（同步或异步）"""
    suffix = "invocations-async" if async_invoke else "invocations"
    url = f"{FG_BASE}/v2/{project_id}/fgs/functions/{function_urn}/{suffix}"
    headers = _auth() | {"Content-Type": "application/json"}
    code, data = await _http().request("POST", url, headers=headers, json={"body": payload})
    return data

# -------------------- MCP 启动 --------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")


# Bash
# export HW_AUTH_TOKEN="你的token"
# export SERVICESTAGE_BASE="https://servicestage.cn-north-4.myhuaweicloud.com"
# export CAE_BASE="https://cae.cn-north-4.myhuaweicloud.com"
# export FG_BASE="https://functiongraph.cn-north-4.myhuaweicloud.com"
# # 可选：代理与证书
# export HTTPS_PROXY="http://your-proxy:port"
# export HTTP_VERIFY=false

# CherryStuodio 更改配置 ：python mcp_agent_ops.py