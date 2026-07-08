#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 知识库：列表查询等操作，调用 V7 AI 知识库接口，输出 Markdown。
需在 wps365-skill 根目录执行，并设置环境变量 WPS_SID。
用法: python skills/ai-docs/run.py <子命令> [参数...]
"""
import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from wpsv7client import list_aidocs_spaces, recall_rank, list_files  # noqa: E402
if os.environ.get("WPS_DISABLE_EVAL_MARKER") == "1":
    def create_marker_hooks():
        return (lambda **kwargs: None), (lambda: None)
else:
    try:
        from eval_marker import create_marker_hooks  # noqa: E402
    except ImportError:
        def create_marker_hooks():
            return (lambda **kwargs: None), (lambda: None)

_set_marker, _finalize_marker = create_marker_hooks()


def _out(md_lines, data):
    lines = [""] + md_lines
    print("\n".join(lines))
    _finalize_marker()
    sys.stdout.flush()


def _err(msg):
    _set_marker(ERROR_EXIT=True, ERROR_MESSAGE=str(msg))
    _finalize_marker()
    print("## 错误\n\n" + msg, file=sys.stderr)
    sys.exit(1)


def _check_resp(resp):
    code = resp.get("code")
    if code == 0:
        d = resp.get("data")
        return d if d is not None else {}
    _err(resp.get("msg") or resp.get("message") or "未知错误")

class _DriveAction(argparse.Action):
    """遇到 --drive-id 时，在 namespace.drive_groups 中新增一条 [drive_id, []] 条目。"""

    def __call__(self, parser, namespace, values, option_string=None):
        groups = getattr(namespace, "drive_groups", None) or []
        groups.append([values, []])
        namespace.drive_groups = groups


class _DirPathAction(argparse.Action):
    """遇到 --dir-path 时，将值追加到最近一个 drive_group 的目录列表中。"""

    def __call__(self, parser, namespace, values, option_string=None):
        groups = getattr(namespace, "drive_groups", None) or []
        if not groups:
            parser.error("--dir-path 必须跟在 --drive-id 之后")
        groups[-1][1].append(values)
        namespace.drive_groups = groups

def _normalize_path(p):
    """将任意格式的路径统一为 'a/b/c' 形式。

    处理反斜杠、连续斜杠、首尾斜杠等情况：
    /a/b/c, a\\b\\c, //a//b//c, a/b\\c/ 均规范为 a/b/c
    """
    import re
    p = p.replace("\\", "/")
    p = re.sub(r"/+", "/", p)
    return p.strip("/")


def _normalize_and_merge_paths(paths):
    """规范化目录路径并合并父子关系。

    - 统一路径分隔符，去除冗余斜杠与首尾斜杠
    - 若 A 是 B 的前缀（B 是 A 的子目录），只保留 A
    """
    normed = list(dict.fromkeys(_normalize_path(p) for p in paths))
    normed = [p for p in normed if p]
    if not normed:
        return []
    normed.sort()
    merged = [normed[0]]
    for p in normed[1:]:
        prev = merged[-1]
        if p == prev or p.startswith(prev + "/"):
            continue
        merged.append(p)
    return merged

def _list_all_children(drive_id, parent_id):
    """分页拉取指定目录下的全部直接子节点。"""
    items = []
    page_token = None
    while True:
        resp = list_files(
            drive_id=drive_id,
            parent_id=parent_id,
            page_size=100,
            page_token=page_token,
        )
        data = resp.get("data") or resp
        if resp.get("code") not in (0, None):
            break
        items.extend((data if isinstance(data, dict) else {}).get("items") or [])
        page_token = (data if isinstance(data, dict) else {}).get("next_page_token") or ""
        if not page_token:
            break
    return items

def _collect_all_file_ids(drive_id, folder_id):
    """递归收集目录下所有文件（非文件夹）的 id。"""
    file_ids = []
    children = _list_all_children(drive_id, folder_id)
    for item in children:
        if item.get("type") == "folder":
            file_ids.extend(_collect_all_file_ids(drive_id, item["id"]))
        else:
            file_ids.append(item["id"])
    return file_ids


def _resolve_dir_to_file_ids(drive_id, dir_path):
    """将规范化后的目录路径解析为该目录下所有文件的 id 列表。

    逐级遍历：从根目录按路径段匹配文件夹名称，定位到目标目录后递归收集。
    """
    segments = [s for s in dir_path.split("/") if s]
    parent_id = "root"
    for seg in segments:
        children = _list_all_children(drive_id, parent_id)
        match = next(
            (c for c in children if c.get("type") == "folder" and c.get("name") == seg),
            None,
        )
        if match is None:
            print(f"警告: 知识库 {drive_id} 中未找到目录 '{seg}'（路径: {dir_path}），跳过", file=sys.stderr)
            return []
        parent_id = match["id"]
    return _collect_all_file_ids(drive_id, parent_id)


def cmd_list_spaces(args):
    _set_marker(ACTION_SELECTED="ai-docs.list-spaces")
    resp = list_aidocs_spaces(
        page_size=args.page_size,
        page_token=args.page_token,
        filter_status=args.filter_status,
    )
    data = _check_resp(resp)
    items = data.get("items", []) if isinstance(data, dict) else []
    next_token = data.get("next_page_token", "") if isinstance(data, dict) else ""
    md = ["## AI 知识库列表", "", f"共 {len(items)} 条（当前页）"]
    if items:
        md.append("")
        for s in items:
            name = s.get("doclib_name") or "(无名称)"
            group_id = s.get("group_id", "")
            drive_id = s.get("drive_id", "")
            md.append(f"- **{name}**  group_id=`{group_id}`  drive_id=`{drive_id}`")
    if next_token:
        md.append("")
        md.append(f"下一页 token: `{next_token}`")
    _out(md, data)


def cmd_recall(args):
    _set_marker(ACTION_SELECTED="ai-docs.recall")

    drives = []
    for drive_id, dir_paths in (args.drive_groups or []):
        if not dir_paths:
            drives.append({"drive_id": drive_id})
        else:
            merged = _normalize_and_merge_paths(dir_paths)
            all_file_ids = []
            for dp in merged:
                fids = _resolve_dir_to_file_ids(drive_id, dp)
                all_file_ids.extend(fids)
            all_file_ids = list(dict.fromkeys(all_file_ids))
            if all_file_ids:
                drives.append({"drive_id": drive_id, "file_ids": all_file_ids})
            else:
                print(f"警告: 知识库 {drive_id} 下指定目录未找到文件，跳过", file=sys.stderr)

    if not drives:
        _err("没有有效的知识库目标可用于召回")

    resp = recall_rank(
        query=args.query,
        drives=drives,
        topk=args.topk,
        scene=args.scene,
    )
    data = resp.get("data", [])
    if not isinstance(data, list):
        data = []
    md = ["## 知识库召回结果", "", f"query: `{args.query}`　topk: {args.topk}　共 {len(data)} 条片段"]
    for i, chunk in enumerate(data, 1):
        fname = chunk.get("file_name", "")
        score = chunk.get("ref_score", 0)
        content = chunk.get("content", "")
        link = chunk.get("link_url", "")
        md.append("")
        md.append(f"### {i}. {fname}（score={score:.4f}）")
        if link:
            md.append(f"链接: {link}")
        md.append("")
        md.append(content)
    _out(md, data)


def main():
    parser = argparse.ArgumentParser(description="AI 知识库操作（V7）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list-spaces", help="知识库列表")
    p.add_argument("--page-size", type=int, default=300, dest="page_size", help="页面大小，默认 300")
    p.add_argument("--page-token", default=None, dest="page_token", help="翻页 token")
    p.add_argument("--filter-status", default="success", dest="filter_status", help="过滤条件，默认 success")
    p.set_defaults(func=cmd_list_spaces)

    p = sub.add_parser("recall", help="知识库召回")
    p.add_argument("query", help="查询关键字")
    p.add_argument("--drive-id", required=True, action=_DriveAction, dest="drive_groups",
                   help="驱动器 ID（可多次指定，每个后面可跟 --dir-path）")
    p.add_argument("--dir-path", action=_DirPathAction, dest="drive_groups",
                   help="目录路径，限定当前 --drive-id 的召回范围（可多次指定）")
    p.add_argument("--topk", type=int, default=1, help="召回片段数量，默认 1")
    p.add_argument("--scene", default=None, help="召回场景，如 full_folder_recall")
    p.set_defaults(func=cmd_recall)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as e:
        _err(str(e))
    except Exception as e:
        _err("请求失败: " + str(e))


if __name__ == "__main__":
    main()
