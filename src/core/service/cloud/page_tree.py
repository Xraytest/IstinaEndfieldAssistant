"""页面树 - 页面探索的数据结构

数据模型定义统一在 module.models 中，此处仅导入使用。
"""
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple

from core.foundation.models import (
    ElementType, PageState, UIElement, PageNode, PageEdge, PageTree
)


def hash_screenshot(image_data: bytes) -> str:
    """计算截图哈希"""
    return hashlib.md5(image_data).hexdigest()


def hash_element(element: UIElement) -> str:
    """计算元素哈希"""
    raw = f"{element.element_id}:{element.label}:{element.bbox}"
    return hashlib.md5(raw.encode()).hexdigest()


def page_node_to_dict(node: PageNode) -> Dict[str, Any]:
    """将 PageNode 序列化为字典"""
    return {
        "page_id": node.page_id,
        "name": node.name,
        "screenshot_hash": node.screenshot_hash,
        "elements": [e.to_dict() for e in node.elements],
        "parent_edge": node.parent_edge,
        "depth": node.depth,
        "state": node.state.value,
        "resolution": list(node.resolution),
        "timestamp": node.timestamp,
        "verification_count": node.verification_count,
    }


def page_node_from_dict(d: Dict[str, Any]) -> PageNode:
    """从字典反序列化 PageNode"""
    return PageNode(
        page_id=d["page_id"],
        name=d["name"],
        screenshot_hash=d["screenshot_hash"],
        elements=[UIElement.from_dict(e) for e in d.get("elements", [])],
        parent_edge=d.get("parent_edge"),
        depth=d.get("depth", 0),
        state=PageState(d.get("state", "unexplored")),
        resolution=tuple(d.get("resolution", [1280, 720])),
        timestamp=d.get("timestamp", 0.0),
        verification_count=d.get("verification_count", 0),
    )


def get_unexplored_elements(node: PageNode) -> List[UIElement]:
    """获取节点中未探索的元素"""
    return [e for e in node.elements if not e.explored and e.element_type != ElementType.TEXT]


def get_node_icon_name(state: PageState) -> str:
    """根据页面状态返回图标名称"""
    icons = {
        PageState.UNEXPLORED: " ",
        PageState.EXPLORING: " ",
        PageState.EXPLORED: " ",
        PageState.ERROR: " ",
    }
    return icons.get(state, " ")


def page_edge_to_dict(edge: PageEdge) -> Dict[str, Any]:
    """将 PageEdge 序列化为字典"""
    return {
        "edge_id": edge.edge_id,
        "from": edge.from_page_id,
        "to": edge.to_page_id,
        "element_id": edge.element_id,
        "action_type": edge.action_type,
        "params": edge.action_params,
    }


def page_tree_to_dict(tree: PageTree) -> Dict[str, Any]:
    """将 PageTree 序列化为字典"""
    return {
        "root_page_id": tree.root.page_id if tree.root else None,
        "nodes": {k: page_node_to_dict(v) for k, v in tree._nodes.items()},
        "edges": [page_edge_to_dict(e) for e in tree._edges],
        "stats": tree._stats,
    }


def page_tree_from_dict(data: Dict[str, Any]) -> PageTree:
    """从字典反序列化 PageTree"""
    tree = PageTree()
    tree._root_page_id = data.get("root_page_id")
    for pid, nd in data.get("nodes", {}).items():
        tree._nodes[pid] = page_node_from_dict(nd)
        tree._hash_index[nd["screenshot_hash"]] = pid
    for ed in data.get("edges", []):
        edge = PageEdge(
            edge_id=ed["edge_id"],
            from_page_id=ed["from"],
            to_page_id=ed["to"],
            element_id=ed["element_id"],
            action_type=ed["action_type"],
            action_params=ed.get("params", {}),
        )
        tree._edges.append(edge)
    tree._stats = data.get("stats", {"pages_discovered": 0, "elements_found": 0, "edges_created": 0})
    return tree


def save_page_tree(tree: PageTree, path: str) -> None:
    """保存 PageTree 到文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(page_tree_to_dict(tree), f, ensure_ascii=False, indent=2)


def load_page_tree(path: str) -> PageTree:
    """从文件加载 PageTree"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return page_tree_from_dict(data)


def hash_screenshot_b64(screenshot_b64: str) -> str:
    """计算 base64 截图哈希（兼容旧接口）"""
    return hashlib.sha256(screenshot_b64.encode()).hexdigest()[:16]


def hash_element_box(box_str: str) -> str:
    """计算元素框哈希（兼容旧接口）"""
    return hashlib.md5(box_str.encode()).hexdigest()[:8]
