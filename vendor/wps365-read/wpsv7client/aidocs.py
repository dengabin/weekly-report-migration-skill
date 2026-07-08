# -*- coding: utf-8 -*-
"""
AI 知识库 V7 API 封装。
参考 spec/internal/aidocs/api_aidocs.xidl：知识库列表、召回等。
参考 spec/internal/docqa/api.xidl：团队文档片段召回。
"""
from typing import List, Optional

from .base import WpsV7Client


def list_aidocs_spaces(
    page_size: int = 300,
    page_token: Optional[str] = None,
    roles: Optional[list] = None,
    filter_status: Optional[str] = "success",
    client: Optional[WpsV7Client] = None,
) -> dict:
    """获取 AI 知识库列表。GET /wiki/api/v1/doclib/list"""
    c = client or WpsV7Client(base_url="https://365.kdocs.cn")
    params: dict = {"page_size": page_size}
    if page_token:
        params["page_token"] = page_token
    if roles:
        params["roles"] = roles
    if filter_status:
        params["filter_status"] = filter_status
    return c.get("/wiki/api/v1/doclib/list", params=params)


def recall_rank(
    query: str,
    drives: List[dict],
    topk: int = 1,
    scene: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    client: Optional[WpsV7Client] = None,
) -> dict:
    """团队文档片段召回。POST /v7/docqa/instore/recall/rank

    根据关键字在指定知识库中召回原文相关片段。

    Args:
        query: 查询关键字。
        drives: 驱动器列表，每项为 {"drive_id": "...", "file_ids": [...]}。
        topk: 召回片段数量上限（<=100），默认 1。
        scene: 召回场景，传 "full_folder_recall" 表示所有库召回。
        start_time: 搜索起始时间戳（文档修改时间）。
        end_time: 搜索结束时间戳（文档修改时间）。
    """
    c = client or WpsV7Client()
    body: dict = {"query": query, "drives": drives, "topk": topk}
    if scene:
        body["scene"] = scene
    if start_time is not None:
        body["start_time"] = start_time
    if end_time is not None:
        body["end_time"] = end_time
    return c.post("/v7/docqa/instore/recall/rank", json=body)
