# gen_openapi_to_mcp.py
# gen_openapi_to_mcp.py  (fixed)
import os, yaml, re, copy, sys
from mcp.server.fastmcp import FastMCP
import httpx

# -------------------- 运行时配置（全部用环境变量） --------------------
# proxy_url ="http://z50053326:ZzX201228%40@canpqwg00153.huawei.com:8080"
SPEC_PATH   = os.getenv("SS_SPEC_PATH", "ss_environment_api.yaml")  # 不再硬编码绝对路径
API_BASE    = os.getenv("SERVICESTAGE_BASE", "https://servicestage.cn-north-4.myhuaweicloud.com")
VERIFY_TLS  = os.getenv("HTTP_VERIFY", "true").lower() != "false"   # 调试才设 false
TIMEOUT_S   = int(os.getenv("HTTP_TIMEOUT", "60"))
PROXIES     = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

mcp = FastMCP("HuaweiServiceStageAuto")


def get_auth_header() -> dict:
    token = os.getenv("HW_AUTH_TOKEN")
    if not token:
        raise ValueError("Missing HW_AUTH_TOKEN")
    return {"X-Auth-Token": token}

# -------------------- 加载 OpenAPI 规范 --------------------
if not os.path.exists(SPEC_PATH):
    raise FileNotFoundError(f"SS_SPEC_PATH not found: {SPEC_PATH}")

with open(SPEC_PATH, "r", encoding="utf-8") as f:
    spec = yaml.safe_load(f)

components = spec.get("components", {})

# -------------------- 工具函数：$ref 解引用 / allOf 合并 / 参数合并 --------------------
def resolve_ref(node):
    """递归解引用 $ref；返回深拷贝后的可直接使用节点。"""
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/"):
                raise ValueError(f"Unsupported external $ref: {ref}")
            parts = ref[2:].split("/")
            target = spec
            for p in parts:
                target = target[p]
            return resolve_ref(copy.deepcopy(target))
        # 继续下钻
        return {k: resolve_ref(v) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve_ref(x) for x in node]
    return node

def merge_allOf(schema_list):
    """最常见场景：对象 allOf 合并 properties/required。"""
    out = {"type": "object", "properties": {}, "required": []}
    for s in schema_list:
        s = resolve_ref(s)
        if isinstance(s, dict) and s.get("type") == "object":
            out["properties"].update(s.get("properties", {}))
            out["required"] += s.get("required", [])
    if not out["required"]:
        out.pop("required", None)
    return out

def unique_params(path_params, op_params):
    """合并 path-level 与 operation-level 参数；以 operation-level 覆盖同名(in,name)"""
    key = lambda p: (p.get("in"), p.get("name"))
    merged = {}
    for p in path_params + op_params:
        p = resolve_ref(p)
        merged[key(p)] = p
    return list(merged.values())

# -------------------- 提取 operation & 生成工具 --------------------
HTTP_METHODS = {"GET","POST","PUT","DELETE","PATCH"}

def extract_operation(path, method, meta):
    op = {
        "method": method.upper(),
        "path": path,
        "operationId": meta.get("operationId") or re.sub(r"[^a-zA-Z0-9_]", "_", f"{method}_{path}"),
        "summary": (meta.get("summary") or "").strip(),
        "parameters": [],
        "requestBody": None,
        "requestBodyRequired": False,
    }
    # 参数合并
    path_level = spec["paths"][path].get("parameters", []) or []
    op_level   = meta.get("parameters", []) or []
    op["parameters"] = unique_params(path_level, op_level)

    # 处理 requestBody
    if "requestBody" in meta:
        rb = resolve_ref(meta["requestBody"])
        op["requestBodyRequired"] = bool(rb.get("required", False))
        content = rb.get("content", {})
        # 优先 application/json；否则挑第一个
        schema = None
        if "application/json" in content:
            schema = content["application/json"].get("schema")
        elif content:
            first_ct = sorted(content.keys())[0]
            schema = content[first_ct].get("schema")
        if schema is None:
            op["requestBody"] = {}
        else:
            schema = resolve_ref(schema)
            if "allOf" in schema:
                schema = merge_allOf(schema["allOf"])
            op["requestBody"] = schema
    return op

operations = []
for path, methods in spec.get("paths", {}).items():
    for method, meta in methods.items():
        if method.upper() in HTTP_METHODS:
            operations.append(extract_operation(path, method, meta))

def make_tool(op):
    method   = op["method"]
    path_tpl = op["path"]
    opid     = op["operationId"]
    tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", opid) or f"op_{abs(hash(opid))}"

    # 分类参数
    path_vars = []
    query_vars = []  # (name, required)
    for p in op.get("parameters", []):
        loc = p.get("in")
        name = p.get("name")
        if not name or not loc:
            continue
        pyname = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if loc == "path":
            if pyname not in path_vars:
                path_vars.append(pyname)
        elif loc == "query":
            query_vars.append((pyname, bool(p.get("required", False))))

    # 常见模板里有 {project_id}
    if "{project_id}" in path_tpl and "project_id" not in path_vars:
        path_vars = ["project_id"] + path_vars

    # 是否有 body
    has_body = (op.get("requestBody") is not None)
    body_required = op.get("requestBodyRequired", False)

    # ---- 函数签名 ----
    sig_required, sig_optional = [], []
    for pv in path_vars:
        sig_required.append(f"{pv}: str")
    for qv, req in query_vars:
        if req:
            sig_required.append(f"{qv}: str")
        else:
            sig_optional.append(f"{qv}: str = ''")
    if has_body:
        if body_required:
            sig_required.append("body: dict")
        else:
            sig_optional.append("body: dict | None = None")
    sig_str = ", ".join(sig_required + sig_optional)

    # 路径占位替换
    path_fill = "path = \"" + path_tpl + "\"\n"
    if path_vars:
        path_fill += "    path_params = {" + ", ".join([f"'{pv}': {pv}" for pv in path_vars]) + "}\n"
        path_fill += "    for k, v in path_params.items():\n"
        path_fill += "        path = path.replace('{' + k + '}', str(v))\n"

    # query 参数
    qp_lines = ""
    if query_vars:
        qp_lines = "\n    ".join(
            [f"if ({qv} is not None) and ({qv} != ''): params['{qv}'] = {qv}"
             for qv, _ in query_vars]
        )

    # headers
    headers_expr = (
        "get_auth_header() | {'Content-Type': 'application/json'}"
        if has_body else "get_auth_header()"
    )

    # ---- 生成函数源码 ----
    src = f'''
@mcp.tool(name="{tool_name}")
async def {tool_name}({sig_str}) -> dict:
    """{op.get("summary") or tool_name}"""
    headers = {headers_expr}
    {path_fill}    url = API_BASE + path
    params = {{}}
    {qp_lines if qp_lines else ""}

    # 兼容 httpx 0.27 (proxies) 和 httpx 0.28+ (proxy)
    _proxy = PROXIES or None
    try:
        _client = httpx.AsyncClient(
            verify=VERIFY_TLS,
            proxy=_proxy,              # httpx >= 0.28
            timeout={TIMEOUT_S}
        )
    except TypeError:
        _client = httpx.AsyncClient(
            verify=VERIFY_TLS,
            proxies=_proxy,            # httpx <= 0.27
            timeout={TIMEOUT_S}
        )

    async with _client as client:
        resp = await client.request(
            "{method}",
            url,
            headers=headers,
            params=params,
            json={( "body" if has_body else "None")}
        )
        try:
            data = resp.json()
        except Exception:
            data = {{"status_code": resp.status_code, "text": resp.text}}
        if resp.is_error:
            return {{"error": True, "status_code": resp.status_code, "data": data}}
        return data
'''
    return src


# 动态注册到当前进程
globs = {
    "mcp": mcp,
    "httpx": httpx,
    "API_BASE": API_BASE,
    "VERIFY_TLS": VERIFY_TLS,
    "PROXIES": PROXIES,
    "TIMEOUT_S": TIMEOUT_S,
    "get_auth_header": get_auth_header,
}
for op in operations:
    exec(make_tool(op), globs)

if __name__ == "__main__":
    mcp.run(transport="stdio")



# Bash
# export HW_AUTH_TOKEN="你的token"
# export SERVICESTAGE_BASE="https://servicestage.cn-north-4.myhuaweicloud.com"
# export SS_SPEC_PATH="/path/to/ss_environment_api.yaml"
# # 可选：
# export HTTPS_PROXY="http://proxy:port"
# export HTTP_VERIFY=false