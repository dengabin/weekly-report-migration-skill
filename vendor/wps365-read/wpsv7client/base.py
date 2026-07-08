# -*- coding: utf-8 -*-
"""
WPS V7 客户端基类。
通过环境变量 WPS_SID 传入用户身份凭证，请求时以 Cookie（wps_sid）形式携带。
"""
import os
from typing import Optional

import requests


class WpsV7Client:
    """V7 API 统一客户端，认证依赖环境变量 WPS_SID。"""

    def __init__(self, base_url: Optional[str] = None, sid: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("WPS_API_BASE") or "https://api.wps.cn").rstrip("/")
        self.sid = sid or os.environ.get("WPS_SID")
        self._session = requests.Session()

    def _headers(self, content_type: str = "application/json") -> dict:
        if not self.sid:
            raise ValueError("缺少用户凭证: 请编辑 assets/config/auth.yaml 中的 wps.sid 字段或设置环境变量 WPS_SID")
        return {
            "Content-Type": content_type,
            "Origin": "https://365.kdocs.cn",
            "Referer": "https://365.kdocs.cn/woa/im/messages",
            "cookie": f"wps_sid={self.sid}; csrf={self.sid}",
        }

    def get(self, path: str, params: Optional[dict] = None, **kwargs) -> dict:
        """GET 请求，path 为相对路径，如 /v7/users/current。"""
        import json
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, headers=self._headers(), params=params, timeout=30, **kwargs)
        # resp.raise_for_status()
        if not resp.content:
            return {}
        try:
            return resp.json()
        except (ValueError, json.JSONDecodeError):
            return {"code": -1, "msg": "response is not json", "text": (resp.text or "")[:500]}

    def post(self, path: str, json: Optional[dict] = None, **kwargs) -> dict:
        """POST 请求。"""
        import json as _json
        url = f"{self.base_url}{path}"
        resp = self._session.post(url, headers=self._headers(), json=json, timeout=30, **kwargs)
        # resp.raise_for_status()
        if not resp.content:
            return {}
        try:
            return resp.json()
        except (ValueError, _json.JSONDecodeError):
            return {"code": -1, "msg": "response is not json", "text": (resp.text or "")[:500]}

    def post_multipart(self, path: str, files=None, data=None, **kwargs) -> dict:
        """POST multipart/form-data（附件上传等场景）。不手动设置 Content-Type，由 requests 自动生成 boundary。"""
        import json as _json
        url = f"{self.base_url}{path}"
        headers = self._headers()
        headers.pop("Content-Type", None)
        resp = self._session.post(url, headers=headers, files=files, data=data, timeout=60, **kwargs)
        if not resp.content:
            return {}
        try:
            return resp.json()
        except (ValueError, _json.JSONDecodeError):
            return {"code": -1, "msg": "response is not json", "text": (resp.text or "")[:500]}
