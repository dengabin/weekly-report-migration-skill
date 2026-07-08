# -*- coding: utf-8 -*-
"""
Drive V7 API 封装。
云文档（Drive）相关接口：文件上传、列表、详情、创建 .otl 智能文档等。
"""
import hashlib
import os
from typing import Any, List, Optional

from .base import WpsV7Client
from .time_util import response_timestamps_to_iso


def _normalize_resp(resp: Any) -> dict:
    """保持 {code, msg, data} 结构，仅对 data 做时间字段转换。"""
    if resp is None:
        return {}
    if not isinstance(resp, dict):
        return resp if isinstance(resp, dict) else {}
    out = dict(resp)
    if "data" in out and out["data"] is not None:
        out["data"] = response_timestamps_to_iso(out["data"])
    return out


def request_upload(
    drive_id: str = "private",
    parent_id: str = "root",
    file_path: str = None,
    file_name: str = None,
    size: int = None,
    parent_path: list = None,
    file_id: str = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    请求文件上传地址。
    POST /v7/drives/{drive_id}/files/{parent_id}/request_upload
    drive_id: 云盘ID，private（我的云文档）、roaming（漫游箱）
    parent_id: 父目录ID，root表示根目录
    file_path: 本地文件路径（可选，若提供则自动计算size和name）
    file_name: 文件名（若file_path为空则必填）
    size: 文件大小（若file_path为空则必填）
    parent_path: 相对于父目录的路径，如 ["folder1", "folder2"]
    file_id: 要更新的文件ID（可选，传入则为更新现有文件）
    """
    c = client or WpsV7Client()
    
    # 将'root'转换为'0'
    if parent_id == 'root':
        parent_id = '0'
    
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        file_name = file_name or os.path.basename(file_path)
        size = file_size
        
        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
    
    if not file_name or not size:
        raise ValueError("file_name 和 size 不能为空")
    
    body = {
        "name": file_name,
        "size": size,
        "mode": "sequential",  # Required parameter discovered in testing
    }
    
    if parent_path:
        body["parent_path"] = parent_path
    
    # 传入 file_id 时为更新现有文件
    if file_id:
        body["file_id"] = file_id
    
    # Add hash if calculated - 使用'sum'而不是'value'（根据成功案例）
    if 'file_hash' in locals():
        body["hashes"] = [{"type": "sha256", "sum": file_hash}]
    
    resp = c.post(f"/v7/drives/{drive_id}/files/{parent_id}/request_upload", json=body)
    return _normalize_resp(resp)


def upload_file(
    upload_url: str,
    file_path: str,
    method: str = "PUT",
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    上传文件到获取的URL。
    upload_url: request_upload返回的上传地址
    file_path: 本地文件路径
    method: 上传方法，PUT或POST
    """
    if not os.path.exists(file_path):
        raise ValueError(f"文件不存在: {file_path}")
    
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    c = client or WpsV7Client()
    
    # 上传文件需要特定的头
    headers = {
        "Content-Type": "application/octet-stream",
        "Origin": "https://365.kdocs.cn",
        "Referer": "https://365.kdocs.cn/woa/im/messages",
        "cookie": f"wps_sid={c.sid}; csrf={c.sid}",
    }
    
    if method == "POST":
        resp = c._session.post(upload_url, data=file_data, headers=headers)
    else:
        resp = c._session.put(upload_url, data=file_data, headers=headers)
    
    return {"status_code": resp.status_code, "response_text": resp.text[:200] if resp.text else ""}


def upload_chunk(
    upload_url: str,
    file_path: str,
    chunk_size: int = 5 * 1024 * 1024,  # 5MB chunks
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    上传文件分块到指定的URL。
    upload_url: request_upload返回的上传地址
    file_path: 本地文件路径
    chunk_size: 分块大小，默认5MB
    """
    if not os.path.exists(file_path):
        raise ValueError(f"文件不存在: {file_path}")
    
    c = client or WpsV7Client()
    file_size = os.path.getsize(file_path)
    
    with open(file_path, "rb") as f:
        chunk_number = 1
        while True:
            chunk_data = f.read(chunk_size)
            if not chunk_data:
                break
                
            # Upload chunk - 需要认证头
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(chunk_data)),
                "Origin": "https://365.kdocs.cn",
                "Referer": "https://365.kdocs.cn/woa/im/messages",
                "cookie": f"wps_sid={c.sid}; csrf={c.sid}",
            }
            
            resp = c._session.put(upload_url, data=chunk_data, headers=headers)
            
            if resp.status_code != 200:
                return {
                    "status_code": resp.status_code,
                    "error": f"上传分块 {chunk_number} 失败",
                    "response": resp.text
                }
            
            chunk_number += 1
    
    return {"status_code": 200, "chunks_uploaded": chunk_number - 1}


def commit_upload(
    drive_id: str,
    parent_id: str,
    upload_id: str,
    file_name: str,
    size: int,
    store_request_keys: dict = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    确认文件上传完成。
    POST /v7/drives/{drive_id}/files/{parent_id}/commit_upload
    drive_id: 云盘ID
    parent_id: 父目录ID
    upload_id: request_upload返回的upload_id
    file_name: 文件名
    size: 文件大小
    store_request_keys: request_upload返回的store_request中的key信息
    """
    c = client or WpsV7Client()
    
    # 将'root'转换为'0'
    if parent_id == 'root':
        parent_id = '0'
    
    body = {
        "upload_id": upload_id,
        "file_name": file_name,
        "size": size,
    }
    
    if store_request_keys:
        body["file"] = store_request_keys
    
    resp = c.post(f"/v7/drives/{drive_id}/files/{parent_id}/commit_upload", json=body)
    return _normalize_resp(resp)


def upload_simple(
    file_path: str,
    drive_id: str = "private",
    parent_id: str = "root",
    parent_path: list = None,
    file_name: Optional[str] = None,
    file_id: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    简单上传文件到云端（单步上传）。
    自动完成请求地址、上传、确认三步。
    file_path: 本地文件路径
    drive_id: 云盘ID，private（我的云文档）、roaming（漫游箱）
    parent_id: 父目录ID，root表示根目录
    parent_path: 相对于父目录的路径
    file_name: 云端文件名，默认与本地文件名相同
    file_id: 要更新的文件ID（可选，传入则为更新现有文件版本）
    返回：云文档信息 {id, link_url, link_id}
    """
    if not os.path.exists(file_path):
        raise ValueError(f"文件不存在: {file_path}")
    
    cloud_name = (file_name or "").strip() or os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    req_resp = request_upload(
        drive_id=drive_id,
        parent_id=parent_id,
        file_path=file_path,
        file_name=cloud_name,
        parent_path=parent_path,
        file_id=file_id,
        client=client,
    )
    
    data = req_resp.get("data", {})
    if not data:
        raise ValueError(f"获取上传地址失败: {req_resp}")
    
    upload_id = data.get("upload_id")
    store_request = data.get("store_request", {})
    upload_url = store_request.get("url")
    method = store_request.get("method", "PUT")
    
    if not upload_id or not upload_url:
        raise ValueError(f"获取上传地址失败: {data}")
    
    # 上传文件
    upload_result = upload_file(upload_url, file_path, method, client)
    if upload_result.get("status_code") != 200:
        raise ValueError(f"上传文件失败: {upload_result}")
    
    # 从upload_url中提取key（最后一个路径部分）
    import urllib.parse
    parsed_url = urllib.parse.urlparse(upload_url)
    key = parsed_url.path.split('/')[-1]
    
    commit_resp = commit_upload(
        drive_id=drive_id,
        parent_id=parent_id,
        upload_id=upload_id,
        file_name=cloud_name,
        size=file_size,
        store_request_keys={'key': key},
        client=client,
    )
    
    return commit_resp


def update_file(
    file_id: str,
    file_path: str,
    drive_id: str = "private",
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    更新现有云文档文件（上传新版本覆盖）。
    file_id: 要更新的文件ID
    file_path: 本地文件路径
    drive_id: 云盘ID，默认 private
    返回：更新后的云文档信息
    """
    return upload_simple(
        file_path=file_path,
        drive_id=drive_id,
        file_id=file_id,
        client=client,
    )


def list_files(
    drive_id: str = "private",
    parent_id: str = "root",
    page_size: int = 50,
    page_token: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取文件列表。
    GET /v7/drives/{drive_id}/files/{parent_id}/children
    drive_id: 云盘ID
    parent_id: 目录ID
    """
    c = client or WpsV7Client()
    
    # 将'root'转换为'0'
    if parent_id == 'root':
        parent_id = '0'
    
    params = {
        "page_size": min(100, max(1, page_size)),
    }
    if page_token:
        params["page_token"] = page_token
    
    resp = c.get(f"/v7/drives/{drive_id}/files/{parent_id}/children", params=params)
    return _normalize_resp(resp)


def get_file(
    drive_id: str,
    file_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取文件详情（需 drive_id）。
    GET /v7/drives/{drive_id}/files/{file_id}/meta
    drive_id: 云盘ID
    file_id: 文件ID
    """
    c = client or WpsV7Client()
    resp = c.get(f"/v7/drives/{drive_id}/files/{file_id}/meta")
    return _normalize_resp(resp)


def get_file_directly(
    file_id: str,
    with_permission: Optional[bool] = None,
    with_link: Optional[bool] = None,
    with_ext_attrs: Optional[bool] = None,
    with_drive: Optional[bool] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    根据 file_id 直接获取文件信息（无需 drive_id，权限更广）。
    GET /v7/files/{file_id}/meta
    仅需 file_id 即可查询，适用于标签对象等场景。
    with_permission: 是否返回文件操作权限
    with_link: 是否返回文件分享信息（私有云适用）
    with_ext_attrs: 是否返回文件扩展属性
    with_drive: 是否返回文件所属 drive 信息（用于后续 download/extract 等操作）
    """
    c = client or WpsV7Client()
    params = {}
    if with_permission is not None:
        params["with_permission"] = "true" if with_permission else "false"
    if with_link is not None:
        params["with_link"] = "true" if with_link else "false"
    if with_ext_attrs is not None:
        params["with_ext_attrs"] = "true" if with_ext_attrs else "false"
    if with_drive is not None:
        params["with_drive"] = "true" if with_drive else "false"
    resp = c.get(f"/v7/files/{file_id}/meta", params=params if params else None)
    return _normalize_resp(resp)


def get_link_meta(
    link_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    根据 link_id 获取分享链接信息（含 file_id、drive_id），用于 link_id 换 file_id。
    GET /v7/links/{link_id}/meta
    link_id: 分享链接 ID（如云文档消息中的 link_id）
    返回：{ code, msg, data }，data 为 v7_link，含 id、url、drive_id、file_id 等。
    """
    c = client or WpsV7Client()
    resp = c.get(f"/v7/links/{link_id}/meta")
    return _normalize_resp(resp)


def get_file_download_url(
    drive_id: str,
    file_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取文件下载信息（含临时下载地址）。
    GET /v7/drives/{drive_id}/files/{file_id}/download
    drive_id: 云盘ID
    file_id: 文件ID
    返回 data 含 url、hashes 等。
    """
    c = client or WpsV7Client()
    resp = c.get(f"/v7/drives/{drive_id}/files/{file_id}/download")
    return _normalize_resp(resp)


def get_file_version_download_url(
    drive_id: str,
    file_id: str,
    version_num: int,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取文件历史版本下载信息（含临时下载地址）。
    GET /v7/drives/{drive_id}/files/{file_id}/versions/{version_num}/download
    drive_id: 云盘ID
    file_id: 文件ID
    version_num: 历史版本号
    返回 data 含 url、hashes 等。
    """
    c = client or WpsV7Client()
    resp = c.get(f"/v7/drives/{drive_id}/files/{file_id}/versions/{int(version_num)}/download")
    return _normalize_resp(resp)


def download_file_to_local(
    drive_id: str,
    file_id: str,
    output_dir: str = ".",
    file_name: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    下载云文档到本地目录。
    先调 get_file_download_url 获取临时 URL，再带 wps_sid Cookie 流式下载。
    file_name: 指定保存的文件名；不传则依次从下载接口响应、Content-Disposition 头中获取。
    返回 {"name": 文件名, "path": 本地绝对路径, "size": 字节数}。
    """
    import os
    import re

    resp = get_file_download_url(drive_id=drive_id, file_id=file_id, client=client)
    data = resp.get("data") or {}
    if resp.get("code") not in (0, None) or not data.get("url"):
        return resp

    url = data["url"]
    file_name = file_name or data.get("name") or None

    os.makedirs(output_dir, exist_ok=True)

    c = client or WpsV7Client()
    headers = {
        "cookie": f"wps_sid={c.sid}; csrf={c.sid}",
    }
    dl_resp = c._session.get(url, headers=headers, stream=True, timeout=120)
    dl_resp.raise_for_status()

    if not file_name:
        cd = dl_resp.headers.get("Content-Disposition", "")
        m = re.search(r"filename\*=UTF-8''(.+)", cd) or re.search(r'filename="?([^";]+)"?', cd)
        if m:
            from urllib.parse import unquote
            file_name = unquote(m.group(1)).strip()
    if not file_name:
        file_name = file_id

    local_path = os.path.join(os.path.abspath(output_dir), file_name)

    with open(local_path, "wb") as f:
        for chunk in dl_resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    file_size = os.path.getsize(local_path)
    return {
        "code": 0,
        "data": {
            "name": file_name,
            "path": local_path,
            "size": file_size,
        },
    }


def download_file_version_to_local(
    drive_id: str,
    file_id: str,
    version_num: int,
    output_dir: str = ".",
    file_name: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    下载文件某个历史版本到本地目录。
    先调 get_file_version_download_url 获取临时 URL，再带 wps_sid Cookie 流式下载。
    file_name: 指定保存的文件名；不传则依次从下载接口响应、Content-Disposition 头中获取。
    返回 {"name": 文件名, "path": 本地绝对路径, "size": 字节数}。
    """
    import os
    import re

    resp = get_file_version_download_url(
        drive_id=drive_id,
        file_id=file_id,
        version_num=version_num,
        client=client,
    )
    data = resp.get("data") or {}
    if resp.get("code") not in (0, None) or not data.get("url"):
        return resp

    url = data["url"]
    file_name = file_name or data.get("name") or None

    os.makedirs(output_dir, exist_ok=True)

    c = client or WpsV7Client()
    headers = {
        "cookie": f"wps_sid={c.sid}; csrf={c.sid}",
    }
    dl_resp = c._session.get(url, headers=headers, stream=True, timeout=120)
    dl_resp.raise_for_status()

    if not file_name:
        cd = dl_resp.headers.get("Content-Disposition", "")
        m = re.search(r"filename\*=UTF-8''(.+)", cd) or re.search(r'filename="?([^";]+)"?', cd)
        if m:
            from urllib.parse import unquote
            file_name = unquote(m.group(1)).strip()
    if not file_name:
        file_name = file_id

    local_path = os.path.join(os.path.abspath(output_dir), file_name)

    with open(local_path, "wb") as f:
        for chunk in dl_resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    file_size = os.path.getsize(local_path)
    return {
        "code": 0,
        "data": {
            "name": file_name,
            "path": local_path,
            "size": file_size,
        },
    }


def get_file_content_extract(
    drive_id: str,
    file_id: str,
    format: str = "plain",
    client: Optional[WpsV7Client] = None,
    **query,
) -> dict:
    """
    文档内容抽取：开放平台「获取文件内容」能力。
    GET /v7/drives/{drive_id}/files/{file_id}/content
    说明文档: https://365.kdocs.cn/3rd/open/documents/app-integration-dev/wps365/server/yundoc/file/get-file-content
    format: plain | markdown | html | kdc，默认 plain
    query: 可选 include_elements、mode、page_range、enable_upload_medias 等。
      enable_upload_medias=true 时，kdc medias 返回 KS3 图片 URL（而非 base64）。
    返回接口原始响应（含 data 内 plain / markdown / html / kdc 等字段）。
    """
    c = client or WpsV7Client()
    params = {"format": format, **query}
    resp = c.get(
        f"/v7/drives/{drive_id}/files/{file_id}/content",
        params=params,
    )
    return _normalize_resp(resp)


def _build_export_params(
    format: str,
    file_path: Optional[str],
    url: Optional[str],
    filename: Optional[str],
    include_elements: Optional[str],
    convert_options: Optional[dict],
) -> dict:
    """构造 exporter 公共参数（供同步/异步共用）。"""
    body: dict = {"format": format}
    if file_path:
        fname = filename or os.path.basename(file_path)
        body["filename"] = fname
    else:
        if url:
            body["url"] = url
        if filename:
            body["filename"] = filename
    if include_elements:
        body["include_elements"] = include_elements
    if convert_options:
        body["convert_options"] = convert_options
    return body


def async_export_create_job(
    format: str = "plain",
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    filename: Optional[str] = None,
    include_elements: Optional[str] = None,
    convert_options: Optional[dict] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    异步方式创建 KDC 文档解析任务。
    POST /v7/coop/asyn_export/create_job
    返回 task_id 用于后续轮询。
    """
    c = client or WpsV7Client()
    c._session.headers["KDC-Caller"] = "wps365-skill"
    endpoint = "/v7/coop/asyn_export/create_job"

    if file_path:
        fname = filename or os.path.basename(file_path)
        data = {"format": format, "filename": fname}
        if include_elements:
            data["include_elements"] = include_elements
        if convert_options:
            import json as _json
            data["convert_options"] = _json.dumps(convert_options)
        with open(file_path, "rb") as f:
            files = {"form_file": (fname, f)}
            resp = c.post_multipart(endpoint, files=files, data=data)
    else:
        body = _build_export_params(
            format, file_path, url, filename, include_elements, convert_options
        )
        resp = c.post(endpoint, json=body)

    return _normalize_resp(resp)


def async_export_query_job(
    task_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    查询异步解析任务进度与结果。
    GET /v7/coop/asyn_export/{task_id}/query_job
    返回 status: processing / finished / failed，finished 时 data 结构与同步接口一致。
    """
    c = client or WpsV7Client()
    c._session.headers["KDC-Caller"] = "wps365-skill"
    resp = c.get(f"/v7/coop/asyn_export/{task_id}/query_job")
    return _normalize_resp(resp)


def export_file_content_async(
    format: str = "plain",
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    filename: Optional[str] = None,
    include_elements: Optional[str] = None,
    convert_options: Optional[dict] = None,
    poll_interval: float = 2.0,
    max_wait: float = 300.0,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    异步解析文件内容：create_job → 轮询 query_job → 返回最终结果。
    poll_interval: 轮询间隔秒数（默认 2s）
    max_wait: 最大等待秒数（默认 300s）
    返回值结构与同步抽取一致。
    """
    import time

    c = client or WpsV7Client()
    create_resp = async_export_create_job(
        format=format,
        file_path=file_path,
        url=url,
        filename=filename,
        include_elements=include_elements,
        convert_options=convert_options,
        client=c,
    )

    code = create_resp.get("code")
    if code not in (None, 0):
        return create_resp

    data = create_resp.get("data") or create_resp
    task_id = data.get("task_id") or create_resp.get("task_id")
    if not task_id:
        return {"code": -1, "msg": "create_job 未返回 task_id", "raw": create_resp}

    elapsed = 0.0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        query_resp = async_export_query_job(task_id, client=c)
        status = query_resp.get("status", "")

        if status == "finished":
            if query_resp.get("code") is None:
                query_resp["code"] = 0
            return query_resp
        elif status == "failed":
            if query_resp.get("code") is None:
                query_resp["code"] = -1
            return query_resp

    return {"code": -1, "msg": f"异步解析超时（{max_wait}s），task_id={task_id}", "task_id": task_id}


def get_file_content(
    drive_id: str,
    file_id: str,
    encoding: str = "utf-8",
    client: Optional[WpsV7Client] = None,
) -> str:
    """
    获取云文档文件文本内容：优先通过下载链接拉取；失败时（如 .otl 无法下载）回退为内容抽取接口。
    drive_id: 云盘ID
    file_id: 文件ID
    encoding: 解码使用的编码，默认 utf-8
    """
    c = client or WpsV7Client()
    try:
        url_resp = get_file_download_url(drive_id, file_id, client=c)
        data = url_resp.get("data") or url_resp
        url = data.get("url") or data.get("download_url")
        if not url:
            raise ValueError("未获取到下载链接")
        r = c._session.get(url, headers=c._headers(), timeout=30)
        r.raise_for_status()
        return r.content.decode(encoding, errors="replace")
    except Exception:
        extract_resp = get_file_content_extract(
            drive_id, file_id, format="plain", client=c
        )
        data = extract_resp.get("data") or extract_resp
        if extract_resp.get("code") not in (None, 0):
            raise ValueError(
                extract_resp.get("msg") or extract_resp.get("message") or "内容抽取失败"
            )
        text = (data.get("plain") or data.get("markdown") or "").strip()
        if not text:
            raise ValueError("内容抽取未返回正文")
        return text


def create_file(
    drive_id: str,
    file_name: Optional[str] = None,
    parent_path: Optional[List[str]] = None,
    on_name_conflict: Optional[str] = "rename",
    client: Optional[WpsV7Client] = None,
    parent_id: str = "0",
    file_type: str = "file",
    file_id: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """
    统一创建入口：新建文件（夹）/快捷方式。POST /v7/drives/{drive_id}/files/{parent_id}/create。

    - file_name / name：目标名称（至少提供一个）
    - file_type：file / folder / shortcut，默认 file
    - parent_id：父目录 ID，默认 "0"
    - parent_path：相对父目录路径（可选）
    - on_name_conflict：重名处理策略（可选）
    - file_id：快捷方式引用 file_id（file_type=shortcut 时可选）
    """
    c = client or WpsV7Client()
    final_name = (name or file_name or "").strip()
    if not final_name:
        raise ValueError("file_name/name 不能为空")

    ft = str(file_type or "file").strip().lower()
    if ft not in ("file", "folder", "shortcut"):
        ft = "file"

    body = {"file_type": ft, "name": final_name}
    if on_name_conflict:
        body["on_name_conflict"] = str(on_name_conflict).strip()
    if parent_path:
        body["parent_path"] = [str(x).strip() for x in parent_path if str(x).strip()]
    if file_id:
        body["file_id"] = str(file_id).strip()

    pid = str(parent_id or "0").strip() or "0"
    resp = c.post(f"/v7/drives/{drive_id}/files/{pid}/create", json=body)
    return _normalize_resp(resp)


def create_otl_document(
    drive_id: str,
    file_name: str,
    parent_path: Optional[List[str]] = None,
    on_name_conflict: str = "rename",
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    在云盘下创建智能文档（.otl 文件）。POST /v7/drives/{drive_id}/files/0/create。
    file_name: 文件名（不含 .otl 则自动加后缀）。
    parent_path: 父路径列表，如 ["我的文档"]，默认 ["我的文档"]。
    返回 data：含 id、link_id、link_url。
    """
    name = f"{file_name}.otl" if not (file_name or "").strip().endswith(".otl") else file_name
    return create_file(
        drive_id=drive_id,
        file_name=name,
        parent_path=parent_path,
        on_name_conflict=on_name_conflict,
        client=client,
    )


def search_files(
    keyword: Optional[str] = None,
    search_type: str = "all",
    scope: Optional[List[str]] = None,
    file_type: Optional[str] = None,
    file_exts: Optional[List[str]] = None,
    exclude_file_exts: Optional[List[str]] = None,
    drive_ids: Optional[List[str]] = None,
    parent_ids: Optional[List[str]] = None,
    creator_ids: Optional[List[str]] = None,
    time_type: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    order: Optional[str] = None,
    order_by: Optional[str] = None,
    page_size: int = 20,
    page_token: Optional[str] = None,
    with_total: bool = True,
    with_link: bool = True,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    搜索云文档文件。GET /v7/files/search。

    keyword: 搜索关键词，不传则按类型/范围列举。
    search_type: file_name（仅文件名）/ content（仅正文）/ all（全部），默认 all。
    scope: 搜索范围列表，如 all、personal_drive、group_drive、latest、share_by_me、share_to_me、recycle 等。
    file_type: 文件类型过滤，folder / file / shortcut。
    file_exts: 文件后缀过滤列表，如 ["docx", "pdf"]。
    exclude_file_exts: 排除的文件后缀列表。
    drive_ids: 搜索盘 ID 列表。
    parent_ids: 搜索目录 ID 列表。
    creator_ids: 创建者 user_id 列表。
    time_type: 时间筛选维度，ctime（创建）/ mtime（修改）/ otime（打开）/ stime（分享）。
    start_time: 时间范围起始，Unix 秒级时间戳。
    end_time: 时间范围结束，Unix 秒级时间戳。
    order: 排序方式，desc / asc。
    order_by: 排序字段，ctime / mtime。
    """
    c = client or WpsV7Client()
    params = {
        "type": search_type,
        "page_size": min(500, max(1, page_size)),
        "with_total": "true" if with_total else "false",
        "with_link": "true" if with_link else "false",
    }
    if keyword:
        params["keyword"] = keyword
    if scope:
        params["scope"] = scope
    if file_type:
        params["file_type"] = file_type
    if file_exts:
        params["file_exts"] = file_exts
    if exclude_file_exts:
        params["exclude_file_exts"] = exclude_file_exts
    if drive_ids:
        params["drive_ids"] = drive_ids
    if parent_ids:
        params["parent_ids"] = parent_ids
    if creator_ids:
        params["creator_ids"] = creator_ids
    if time_type:
        params["time_type"] = time_type
    if start_time is not None:
        params["start_time"] = start_time
    if end_time is not None:
        params["end_time"] = end_time
    if order:
        params["order"] = order
    if order_by:
        params["order_by"] = order_by
    if page_token:
        params["page_token"] = page_token
    resp = c.get("/v7/files/search", params=params)
    return _normalize_resp(resp)


def convert_file(
    source_file_path: str,
    target_format: str,
    template_file_path: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    转换文件格式（如 Markdown → DOCX）。
    POST /v7/coop/convert_file
    source_file_path: 源文件路径（如 .md 文件）
    target_format: 目标格式（如 docx, pdf, pptx）
    template_file_path: 模板文件路径（可选，如 .docx 模板）
    返回：转换后的文件内容（二进制）
    """
    c = client or WpsV7Client()
    
    if not os.path.exists(source_file_path):
        raise ValueError(f"源文件不存在: {source_file_path}")
    
    # 准备 multipart/form-data
    files = {
        'form_file': (os.path.basename(source_file_path), open(source_file_path, 'rb')),
    }
    data = {
        'filename': os.path.basename(source_file_path),
        'target': target_format,
    }
    
    # 如果提供了模板文件
    if template_file_path and os.path.exists(template_file_path):
        files['template_file.form_file'] = (
            os.path.basename(template_file_path), 
            open(template_file_path, 'rb')
        )
        data['template_file.filename'] = os.path.basename(template_file_path)
    
    # 发送请求（不使用 json 参数，使用 data + files）
    url = f"{c.base_url}/v7/coop/convert_file"
    resp = c._session.post(
        url, 
        data=data, 
        files=files,
        headers={
            "Origin": "https://365.kdocs.cn",
            "Referer": "https://365.kdocs.cn/woa/im/messages",
            "cookie": f"wps_sid={c.sid}; csrf={c.sid}",
        },
        timeout=60
    )
    
    # 关闭文件句柄
    for f in files.values():
        if hasattr(f[1], 'close'):
            f[1].close()
    
    # 返回转换后的文件内容
    if resp.status_code == 200:
        return {"code": 0, "data": resp.content}
    else:
        try:
            error_data = resp.json()
            return error_data
        except:
            return {"code": -1, "msg": f"转换失败: HTTP {resp.status_code}", "text": resp.text[:500]}

def list_latest_items(
    with_permission: Optional[bool] = None,
    with_link: Optional[bool] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
    include_exts: Optional[List[str]] = None,
    exclude_exts: Optional[List[str]] = None,
    include_creators: Optional[List[str]] = None,
    exclude_creators: Optional[List[str]] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取最近列表。GET /v7/drive_latest/items
    with_permission: 是否返回文件操作权限
    with_link: 是否返回文件分享信息
    page_size: 分页大小（接口最大 500）
    page_token: 翻页 token
    include_exts / exclude_exts: 后缀过滤（字符串列表，逗号拼接）
    include_creators / exclude_creators: 创建者过滤（字符串列表，逗号拼接）
    """
    c = client or WpsV7Client()
    params = {
        "page_size": min(500, max(1, page_size)),
    }
    if with_permission is not None:
        params["with_permission"] = "true" if with_permission else "false"
    if with_link is not None:
        params["with_link"] = "true" if with_link else "false"
    if page_token:
        params["page_token"] = page_token
    if include_exts:
        params["include_exts"] = ",".join([str(x).strip() for x in include_exts if str(x).strip()])
    if exclude_exts:
        params["exclude_exts"] = ",".join([str(x).strip() for x in exclude_exts if str(x).strip()])
    if include_creators:
        params["include_creators"] = ",".join([str(x).strip() for x in include_creators if str(x).strip()])
    if exclude_creators:
        params["exclude_creators"] = ",".join([str(x).strip() for x in exclude_creators if str(x).strip()])

    resp = c.get("/v7/drive_latest/items", params=params)
    return _normalize_resp(resp)


def list_file_versions(
    drive_id: str,
    file_id: str,
    page_size: int = 50,
    page_token: Optional[str] = None,
    with_comment: Optional[bool] = None,
    with_ext_attrs: Optional[bool] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取文件版本列表。GET /v7/drives/{drive_id}/files/{file_id}/versions
    drive_id: 云盘 ID
    file_id: 文件 ID
    page_size: 分页大小，接口最大 500
    page_token: 分页 token
    with_comment: 是否返回版本备注
    with_ext_attrs: 是否返回版本扩展属性
    """
    c = client or WpsV7Client()
    params = {
        "page_size": min(500, max(1, int(page_size or 50))),
    }
    if page_token:
        params["page_token"] = str(page_token).strip()
    if with_comment is not None:
        params["with_comment"] = "true" if with_comment else "false"
    if with_ext_attrs is not None:
        params["with_ext_attrs"] = "true" if with_ext_attrs else "false"

    resp = c.get(f"/v7/drives/{drive_id}/files/{file_id}/versions", params=params)
    return _normalize_resp(resp)


def list_star_items(
    with_permission: Optional[bool] = None,
    with_link: Optional[bool] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
    order: Optional[str] = None,
    order_by: Optional[str] = None,
    include_exts: Optional[List[str]] = None,
    exclude_exts: Optional[List[str]] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取收藏列表。GET /v7/drive_star/items
    with_permission: 是否返回文件操作权限
    with_link: 是否返回文件分享信息
    page_size: 分页大小（接口最大 200）
    page_token: 翻页 token
    order: 排序方向，desc/asc
    order_by: 排序字段，常见 ctime/file_mtime/source/fname/fsize
    include_exts / exclude_exts: 后缀过滤（字符串列表，逗号拼接）
    """
    c = client or WpsV7Client()
    params = {
        "page_size": min(200, max(1, page_size)),
    }
    if with_permission is not None:
        params["with_permission"] = "true" if with_permission else "false"
    if with_link is not None:
        params["with_link"] = "true" if with_link else "false"
    if page_token:
        params["page_token"] = page_token
    if order:
        params["order"] = str(order).strip()
    if order_by:
        params["order_by"] = str(order_by).strip()
    if include_exts:
        params["include_exts"] = ",".join([str(x).strip() for x in include_exts if str(x).strip()])
    if exclude_exts:
        params["exclude_exts"] = ",".join([str(x).strip() for x in exclude_exts if str(x).strip()])

    resp = c.get("/v7/drive_star/items", params=params)
    out = _normalize_resp(resp)
    msg = str((out or {}).get("msg") or (out or {}).get("message") or "")
    if isinstance(out, dict) and out.get("code") not in (0, None) and "文件不存在" in msg:
        # 部分环境对 with_link/with_permission 参数不兼容，会错误返回“文件不存在”
        # 或 page_size>10 时也可能报该错误。
        # 兼容处理：去掉该类参数并下调 page_size 后重试，保证收藏列表可用。
        retry_params = dict(params)
        retry_params.pop("with_link", None)
        retry_params.pop("with_permission", None)
        if int(retry_params.get("page_size") or 0) > 10:
            retry_params["page_size"] = 10
        resp_retry = c.get("/v7/drive_star/items", params=retry_params)
        return _normalize_resp(resp_retry)
    return out


def batch_create_star_items(
    objects: Optional[List[Any]] = None,
    items: Optional[List[Any]] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    批量添加收藏项。
    POST /v7/drive_star/items/batch_create
    优先使用 objects；items 为兼容旧字段。
    """
    c = client or WpsV7Client()
    normalized = []
    for obj in (objects or []):
        if isinstance(obj, str) and obj.strip():
            normalized.append({"id": obj.strip(), "type": "file"})
        elif isinstance(obj, dict):
            item = dict(obj)
            if item.get("id") and not item.get("type"):
                item["type"] = "file"
            normalized.append(item)
    body: dict = {}
    if normalized:
        body["objects"] = normalized[:1024]
    elif isinstance(items, list):
        body["items"] = items[:1024]
    resp = c.post("/v7/drive_star/items/batch_create", json=body)
    return _normalize_resp(resp)


def batch_delete_star_items(
    objects: Optional[List[Any]] = None,
    item_ids: Optional[List[str]] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    批量移除收藏项。
    POST /v7/drive_star/items/batch_delete
    优先使用 objects；item_ids 为兼容旧字段。
    """
    c = client or WpsV7Client()
    normalized = []
    for obj in (objects or []):
        if isinstance(obj, str) and obj.strip():
            normalized.append({"id": obj.strip(), "type": "file"})
        elif isinstance(obj, dict):
            item = dict(obj)
            if item.get("id") and not item.get("type"):
                item["type"] = "file"
            normalized.append(item)
    body: dict = {}
    if normalized:
        body["objects"] = normalized[:1024]
    elif item_ids:
        body["item_ids"] = [str(x).strip() for x in item_ids if str(x).strip()][:1024]
    resp = c.post("/v7/drive_star/items/batch_delete", json=body)
    return _normalize_resp(resp)


def list_drive_labels(
    allotee_type: str = "user",
    allotee_id: Optional[str] = None,
    label_type: str = "custom",
    page_size: int = 20,
    page_token: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    分页获取自定义标签列表（v7）。
    GET /v7/drive_labels
    allotee_type: user / group / app
    allotee_id: 指定归属 ID；type 为 user 时可不传
    label_type: custom / system，默认 custom
    page_size: 分页大小，接口最大 500
    page_token: 分页 token
    """
    c = client or WpsV7Client()
    at = str(allotee_type or "user").strip().lower()
    if at not in ("user", "group", "app"):
        at = "user"
    lt = str(label_type or "custom").strip().lower()
    if lt not in ("custom", "system"):
        lt = "custom"
    params = {
        "allotee_type": at,
        "label_type": lt,
        "page_size": min(500, max(1, int(page_size))),
    }
    if allotee_id:
        params["allotee_id"] = str(allotee_id).strip()
    if page_token:
        params["page_token"] = str(page_token).strip()
    resp = c.get("/v7/drive_labels", params=params)
    return _normalize_resp(resp)


def get_drive_label_meta(
    label_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取单个标签信息。
    GET /v7/drive_labels/{label_id}/meta
    """
    c = client or WpsV7Client()
    resp = c.get(f"/v7/drive_labels/{label_id}/meta")
    return _normalize_resp(resp)


def list_drive_label_objects(
    label_id: str,
    page_size: int = 20,
    page_token: Optional[str] = None,
    include_exts: Optional[List[str]] = None,
    exclude_exts: Optional[List[str]] = None,
    file_type: str = "file",
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    分页获取标签下的全部对象。
    GET /v7/drive_labels/{label_id}/objects
    page_size: 分页大小，接口最大 100
    include_exts/exclude_exts: 扩展名过滤（逗号拼接）
    file_type: file/folder/short_cut
    """
    c = client or WpsV7Client()
    ft = str(file_type or "file").strip().lower()
    if ft not in ("file", "folder", "short_cut"):
        ft = "file"
    params = {
        "page_size": min(100, max(1, int(page_size))),
        "file_type": ft,
    }
    if page_token:
        params["page_token"] = str(page_token).strip()
    if include_exts:
        params["include_exts"] = ",".join([str(x).strip() for x in include_exts if str(x).strip()])
    if exclude_exts:
        params["exclude_exts"] = ",".join([str(x).strip() for x in exclude_exts if str(x).strip()])
    resp = c.get(f"/v7/drive_labels/{label_id}/objects", params=params)
    return _normalize_resp(resp)


def create_drive_label(
    name: str,
    allotee_type: str = "user",
    allotee_id: Optional[str] = None,
    label_type: str = "custom",
    attr: Optional[str] = None,
    rank: Optional[float] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    创建自定义标签。
    POST /v7/drive_labels/create
    """
    c = client or WpsV7Client()
    at = str(allotee_type or "user").strip().lower()
    if at not in ("user", "group", "app"):
        at = "user"
    lt = str(label_type or "custom").strip().lower()
    if lt not in ("custom", "system"):
        lt = "custom"
    body = {
        "name": str(name or "").strip(),
        "allotee_type": at,
        "label_type": lt,
    }
    if allotee_id:
        body["allotee_id"] = str(allotee_id).strip()
    if attr is not None:
        body["attr"] = str(attr)
    if rank is not None:
        body["rank"] = rank
    resp = c.post("/v7/drive_labels/create", json=body)
    return _normalize_resp(resp)


def batch_add_drive_label_objects(
    label_id: str,
    objects: List[Any],
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    批量添加标签对象。
    POST /v7/drive_labels/{label_id}/objects/batch_add
    objects: 1~100 个对象，支持传字符串 ID 列表或对象字典列表
    """
    c = client or WpsV7Client()
    normalized = []
    for obj in objects or []:
        if isinstance(obj, str) and obj.strip():
            normalized.append({"id": obj.strip(), "type": "file"})
        elif isinstance(obj, dict):
            item = dict(obj)
            if item.get("id") and not item.get("type"):
                item["type"] = "file"
            normalized.append(item)
    body = {"objects": normalized[:100]}
    resp = c.post(f"/v7/drive_labels/{label_id}/objects/batch_add", json=body)
    return _normalize_resp(resp)


def batch_remove_drive_label_objects(
    label_id: str,
    objects: List[Any],
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    批量移除标签对象。
    POST /v7/drive_labels/{label_id}/objects/batch_remove
    objects: 1~100 个对象，支持传字符串 ID 列表或对象字典列表
    """
    c = client or WpsV7Client()
    normalized = []
    for obj in objects or []:
        if isinstance(obj, str) and obj.strip():
            normalized.append({"id": obj.strip(), "type": "file"})
        elif isinstance(obj, dict):
            item = dict(obj)
            if item.get("id") and not item.get("type"):
                item["type"] = "file"
            normalized.append(item)
    body = {"objects": normalized[:100]}
    resp = c.post(f"/v7/drive_labels/{label_id}/objects/batch_remove", json=body)
    return _normalize_resp(resp)


def list_deleted_files(
    drive_id: Optional[str] = None,
    with_ext_attrs: Optional[bool] = None,
    page_size: int = 20,
    page_token: Optional[str] = None,
    with_drive: Optional[bool] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """获取回收站文件列表。GET /v7/deleted_files"""
    c = client or WpsV7Client()
    params = {"page_size": min(100, max(1, int(page_size)))}
    if drive_id:
        params["drive_id"] = str(drive_id).strip()
    if page_token:
        params["page_token"] = str(page_token).strip()
    if with_ext_attrs is not None:
        params["with_ext_attrs"] = "true" if with_ext_attrs else "false"
    if with_drive is not None:
        params["with_drive"] = "true" if with_drive else "false"
    resp = c.get("/v7/deleted_files", params=params)
    return _normalize_resp(resp)


def restore_deleted_file(
    file_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """还原回收站文件。POST /v7/deleted_files/{file_id}/restore"""
    c = client or WpsV7Client()
    resp = c.post(f"/v7/deleted_files/{file_id}/restore", json={})
    return _normalize_resp(resp)


def delete_file(
    drive_id: str,
    file_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """将文件移入回收站。POST /v7/drives/{drive_id}/files/{file_id}/delete"""
    c = client or WpsV7Client()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/delete", json={})
    return _normalize_resp(resp)


def move_file(
    drive_id: str,
    file_id: str,
    dst_drive_id: str,
    dst_parent_id: str,
    secure_type: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """移动文件。POST /v7/drives/{drive_id}/files/{file_id}/move"""
    c = client or WpsV7Client()
    body = {
        "dst_drive_id": str(dst_drive_id).strip(),
        "dst_parent_id": str(dst_parent_id).strip(),
    }
    if secure_type:
        body["secure_type"] = str(secure_type).strip()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/move", json=body)
    return _normalize_resp(resp)


def copy_file(
    drive_id: str,
    file_id: str,
    dst_drive_id: str,
    dst_parent_id: str,
    secure_type: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """复制文件。POST /v7/drives/{drive_id}/files/{file_id}/copy"""
    c = client or WpsV7Client()
    body = {
        "dst_drive_id": str(dst_drive_id).strip(),
        "dst_parent_id": str(dst_parent_id).strip(),
    }
    if secure_type:
        body["secure_type"] = str(secure_type).strip()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/copy", json=body)
    return _normalize_resp(resp)

def rename_file(
    drive_id: str,
    file_id: str,
    dst_name: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """重命名文件（夹）。POST /v7/drives/{drive_id}/files/{file_id}/rename"""
    c = client or WpsV7Client()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/rename", json={"dst_name": str(dst_name).strip()})
    return _normalize_resp(resp)


def save_as_file(
    drive_id: str,
    file_id: str,
    dst_drive_id: str,
    dst_parent_id: str,
    name: Optional[str] = None,
    on_name_conflict: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """文件另存为。POST /v7/drives/{drive_id}/files/{file_id}/save_as"""
    c = client or WpsV7Client()
    body = {
        "dst_drive_id": str(dst_drive_id).strip(),
        "dst_parent_id": str(dst_parent_id).strip(),
    }
    if name:
        body["name"] = str(name).strip()
    if on_name_conflict:
        body["on_name_conflict"] = str(on_name_conflict).strip()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/save_as", json=body)
    return _normalize_resp(resp)


def check_name_exists(
    drive_id: str,
    parent_id: str,
    name: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """检查文件名是否已存在。POST /v7/drives/{drive_id}/files/{parent_id}/check_name"""
    c = client or WpsV7Client()
    resp = c.post(f"/v7/drives/{drive_id}/files/{parent_id}/check_name", json={"name": str(name).strip()})
    return _normalize_resp(resp)


def open_file_link(
    drive_id: str,
    file_id: str,
    opts: Optional[dict] = None,
    role_id: Optional[str] = None,
    scope: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """开启文件分享。POST /v7/drives/{drive_id}/files/{file_id}/open_link"""
    c = client or WpsV7Client()
    body: dict = {}
    if opts is not None:
        body["opts"] = opts
    if role_id:
        body["role_id"] = str(role_id).strip()
    if scope:
        body["scope"] = str(scope).strip()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/open_link", json=body)
    return _normalize_resp(resp)


def close_file_link(
    drive_id: str,
    file_id: str,
    mode: str = "pause",
    client: Optional[WpsV7Client] = None,
) -> dict:
    """取消文件分享。POST /v7/drives/{drive_id}/files/{file_id}/close_link"""
    c = client or WpsV7Client()
    resp = c.post(f"/v7/drives/{drive_id}/files/{file_id}/close_link", json={"mode": str(mode).strip()})
    return _normalize_resp(resp)


def ai_search(
    keyword: str,
    doc_qa_recall_strategy: str = "all",
    page_size: int = 20,
    page_token: Optional[str] = None,
    file_exts: Optional[List[str]] = None,
    exclude_file_exts: Optional[List[str]] = None,
    drive_ids: Optional[List[str]] = None,
    parent_ids: Optional[List[str]] = None,
    scopes: Optional[List[str]] = None,
    with_total: bool = True,
    with_permission: Optional[bool] = None,
    with_drive: Optional[bool] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    知识库召回（文件智能搜索，多路召回）。
    POST /v7/files/ai_search
    keyword: 搜索关键词
    doc_qa_recall_strategy: 洞察接口召回策略，paragraph / paragraph_embedding / all，默认 all
    page_size: 每页条数，默认 20
    page_token: 翻页 token
    file_exts: 文件后缀过滤
    exclude_file_exts: 排除文件后缀
    drive_ids: 搜索盘列表
    parent_ids: 搜索目录列表
    scopes: 搜索范围
    with_total: 是否返回总条数
    with_permission: 是否返回文件操作权限
    with_drive: 是否返回驱动盘信息
    返回：{ code, msg, data: { items, next_page_token, total } }
    """
    c = client or WpsV7Client()
    body: dict = {
        "keyword": keyword,
        "doc_qa_recall_strategy": doc_qa_recall_strategy,
        "page_size": min(500, max(1, page_size)),
    }
    if page_token:
        body["page_token"] = page_token
    if file_exts:
        body["file_exts"] = [str(x).strip() for x in file_exts if str(x).strip()]
    if exclude_file_exts:
        body["exclude_file_exts"] = [str(x).strip() for x in exclude_file_exts if str(x).strip()]
    if drive_ids:
        body["drive_ids"] = [str(x).strip() for x in drive_ids if str(x).strip()]
    if parent_ids:
        body["parent_ids"] = [str(x).strip() for x in parent_ids if str(x).strip()]
    if scopes:
        body["scopes"] = [str(x).strip() for x in scopes if str(x).strip()]
    if with_total is not None:
        body["with_total"] = with_total
    if with_permission is not None:
        body["with_permission"] = with_permission
    if with_drive is not None:
        body["with_drive"] = with_drive
    resp = c.post("/v7/files/ai_search", json=body)
    return _normalize_resp(resp)


# ---------------------------------------------------------------------------
# 全文评论 (Document Comments) 走 gw_office：365.kdocs.cn/open/v7/documents/...
# ---------------------------------------------------------------------------

_COMMENTS_OPEN_BASE = "https://365.kdocs.cn/open"


def _comments_client(client: Optional[WpsV7Client] = None) -> WpsV7Client:
    """评论接口与主站 api.wps.cn 不同域，统一走 365.kdocs.cn/open。"""
    sid = client.sid if client is not None else None
    return WpsV7Client(base_url=_COMMENTS_OPEN_BASE, sid=sid)


def list_document_comments(
    file_id: str,
    origin_id: str = "0",
    page_size: int = 10,
    page_token: Optional[str] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取全文评论列表。
    GET https://365.kdocs.cn/open/v7/documents/{file_id}/comments/{origin_id}/list
    origin_id="0" 查根评论（page_size 最大 10，每条默认携带 2 条子评论）；
    传根评论 ID 查子评论（page_size 最大 100）。
    根评论按 id 倒序，子评论按 id 正序。
    """
    c = _comments_client(client)
    max_ps = 10 if str(origin_id) == "0" else 100
    params: dict = {"page_size": min(max_ps, max(1, page_size))}
    if page_token:
        params["page_token"] = page_token
    resp = c.get(
        f"/v7/documents/{file_id}/comments/{origin_id}/list",
        params=params,
    )
    return _normalize_resp(resp)


def create_document_comment(
    file_id: str,
    content: str,
    origin_id: Optional[int] = None,
    reply_id: Optional[int] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    创建全文评论。
    POST https://365.kdocs.cn/open/v7/documents/{file_id}/comments/create
    content: 评论内容（1-5000 字）。
    origin_id / reply_id: 可选，用于回复已有评论（两级结构）。
    """
    c = _comments_client(client)
    body: dict = {"content": content}
    if origin_id is not None:
        body["origin_id"] = int(origin_id)
    if reply_id is not None:
        body["reply_id"] = int(reply_id)
    resp = c.post(f"/v7/documents/{file_id}/comments/create", json=body)
    return _normalize_resp(resp)


def update_document_comment(
    file_id: str,
    comment_id: str,
    content: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    更新全文评论内容。
    POST https://365.kdocs.cn/open/v7/documents/{file_id}/comments/{comment_id}/update
    """
    c = _comments_client(client)
    resp = c.post(
        f"/v7/documents/{file_id}/comments/{comment_id}/update",
        json={"content": content},
    )
    return _normalize_resp(resp)


def delete_document_comment(
    file_id: str,
    comment_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    删除全文评论。
    POST https://365.kdocs.cn/open/v7/documents/{file_id}/comments/{comment_id}/delete
    无 request body，响应无 data。
    """
    c = _comments_client(client)
    resp = c.post(f"/v7/documents/{file_id}/comments/{comment_id}/delete", json={})
    return _normalize_resp(resp)


# ---------------------------------------------------------------------------
# 文档库（团队文档）Doclib
# ---------------------------------------------------------------------------

def list_doclibs(
    page_size: int = 100,
    page_token: Optional[str] = None,
    user_role: Optional[List[str]] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取文档库（团队文档）列表。GET /v7/doclibs。
    page_size: 分页大小，上限 100。
    page_token: 分页 token（上一页返回的 next_page_token）。
    user_role: 按用户角色筛选，可选值如 owner/admin/normal，最多 4 个。
    返回 data: {items: [{drive, group, user_role, pinned, secure}], next_page_token}
    """
    c = client or WpsV7Client()
    params: dict = {"page_size": min(page_size, 100)}
    if page_token:
        params["page_token"] = page_token
    if user_role:
        params["user_role"] = user_role
    resp = c.get("/v7/doclibs", params=params)
    return _normalize_resp(resp)


def get_doclib_meta(
    drive_id: str,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """
    获取单个文档库（团队文档）信息。GET /v7/doclib/meta?drive_id=xxx。
    drive_id: 文档库对应的驱动盘 ID。
    返回 data: {drive, group, user_role, pinned, secure}
    """
    c = client or WpsV7Client()
    resp = c.get("/v7/doclib/meta", params={"drive_id": drive_id})
    return _normalize_resp(resp)
