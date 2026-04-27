import streamlit as st
import json
import base64
import urllib.request
import urllib.error
import html as html_mod

REPO = "plusms/intern-task-dashboard"
FILE_PATH = "tasks.json"
INTERNS = ["亀矢", "佐藤", "武田", "中村", "山田"]
STATUSES = ["未着手", "進行中", "確認待ち", "完了"]

STATUS_STYLE = {
    "未着手":  {"bg": "#f3f4f6", "border": "#9ca3af", "text": "#374151"},
    "進行中":  {"bg": "#dbeafe", "border": "#3b82f6", "text": "#1d4ed8"},
    "確認待ち": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e"},
    "完了":    {"bg": "#d1fae5", "border": "#10b981", "text": "#065f46"},
}
PRIORITY_STYLE = {
    "差し込み":   {"bg": "#fee2e2", "text": "#dc2626"},
    "ルーティン": {"bg": "#f3f4f6", "text": "#6b7280"},
}


def get_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        st.error("GITHUB_TOKEN が Streamlit Secrets に設定されていません")
        st.stop()


def github_read():
    token = get_token()
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read())
        content = json.loads(base64.b64decode(res["content"]).decode("utf-8"))
        return content, res["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"tasks": []}, None
        st.error(f"GitHub読み込みエラー: {e.code}")
        st.stop()


def github_write(content, sha, message="update tasks"):
    token = get_token()
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    body = {
        "message": message,
        "content": base64.b64encode(
            json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8"),
    }
    if sha:
        body["sha"] = sha
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 409:
            st.warning("他の人が同時に更新しました。ページを更新してから再試行してください。")
        else:
            st.error(f"GitHub書き込みエラー: {e.code}")
        return None


def esc(s):
    return html_mod.escape(str(s))


def render_card(task, tasks_data, sha):
    priority = task.get("priority", "ルーティン")
    ps = PRIORITY_STYLE.get(priority, PRIORITY_STYLE["ルーティン"])
    deadline = task.get("deadline") or ""
    task_id = task["id"]
    is_expanded = task_id in st.session_state.get("expanded", set())

    with st.container(border=True):
        st.html(
            f"""
            <div style="padding:2px 0 4px;">
                <div style="font-weight:600; font-size:13px; margin-bottom:6px; line-height:1.4;">
                    {esc(task.get('title', ''))}
                </div>
                <div style="font-size:11px; color:#6b7280; margin-bottom:6px;">
                    📍 {esc(task.get('site', ''))}
                </div>
                <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-bottom:4px;">
                    <span style="
                        background:{ps['bg']}; color:{ps['text']};
                        border-radius:4px; padding:2px 7px; font-size:10px; font-weight:600;
                    ">{esc(priority)}</span>
                    {f'<span style="font-size:11px; color:#ef4444;">⏰ {esc(deadline)}</span>' if deadline else ''}
                </div>
                <div style="font-size:10px; color:#9ca3af;">依頼: {esc(task.get('requester', ''))}</div>
            </div>
            """
        )

        if st.button(
            "▲ 閉じる" if is_expanded else "▼ 詳細",
            key=f"toggle_{task_id}",
            use_container_width=True,
        ):
            if "expanded" not in st.session_state:
                st.session_state.expanded = set()
            if is_expanded:
                st.session_state.expanded.discard(task_id)
            else:
                st.session_state.expanded.add(task_id)
            st.rerun()

        if is_expanded:
            st.markdown("**📝 作業内容**")
            st.write(task.get("content", ""))
            if task.get("reference"):
                st.markdown("**📎 参照スキル**")
                st.write(task.get("reference", ""))
            if task.get("notes"):
                st.markdown("**💬 補足**")
                st.write(task.get("notes", ""))
            st.caption(f"作成日: {str(task.get('created_at', ''))[:10]}")

            st.divider()
            new_status = st.selectbox(
                "ステータス",
                STATUSES,
                index=STATUSES.index(task.get("status", "未着手")),
                key=f"sel_{task_id}",
            )
            if st.button("保存", key=f"btn_{task_id}", type="primary"):
                latest_data, latest_sha = github_read()
                for t in latest_data["tasks"]:
                    if t["id"] == task_id:
                        t["status"] = new_status
                        break
                result = github_write(
                    latest_data, latest_sha,
                    f"status: {task['title']} → {new_status}"
                )
                if result:
                    st.success(f"✅ {new_status} に更新しました")
                    st.rerun()


def render_board(tasks, tasks_data, sha, selected_interns):
    # サマリー
    cols = st.columns(4)
    for i, status in enumerate(STATUSES):
        count = sum(1 for t in tasks if t.get("status") == status)
        s = STATUS_STYLE[status]
        with cols[i]:
            st.html(
                f"""<div style="
                    background:{s['bg']}; border:2px solid {s['border']};
                    border-radius:8px; padding:10px 14px; text-align:center;
                ">
                    <div style="font-size:22px; font-weight:700; color:{s['text']};">{count}</div>
                    <div style="font-size:12px; color:{s['text']};">{status}</div>
                </div>"""
            )

    st.html("<br>")

    interns_to_show = selected_interns if selected_interns else INTERNS
    header = st.columns([0.6] + [1] * 4)
    with header[0]:
        st.markdown("")
    for i, status in enumerate(STATUSES):
        s = STATUS_STYLE[status]
        with header[i + 1]:
            st.html(
                f"""<div style="
                    background:{s['bg']}; border:2px solid {s['border']};
                    border-radius:6px; padding:6px; text-align:center;
                    font-weight:700; font-size:13px; color:{s['text']};
                ">{status}</div>"""
            )

    st.html("<hr style='margin:8px 0;'>")

    for intern in interns_to_show:
        row = st.columns([0.6] + [1] * 4)
        with row[0]:
            st.html(
                f"""<div style="
                    padding:12px 4px; font-weight:600; font-size:13px;
                    color:#374151; text-align:center;
                ">👤<br>{esc(intern)}</div>"""
            )
        for i, status in enumerate(STATUSES):
            with row[i + 1]:
                cell_tasks = [
                    t for t in tasks
                    if t.get("assignee") == intern and t.get("status") == status
                ]
                if cell_tasks:
                    for task in cell_tasks:
                        render_card(task, tasks_data, sha)
                else:
                    st.html(
                        "<div style='min-height:44px; border:1px dashed #e5e7eb; border-radius:6px; margin-bottom:8px;'></div>"
                    )

        st.html("<hr style='margin:4px 0; border-color:#f3f4f6;'>")

    if not tasks:
        st.info("該当するタスクがありません。")


def render_routines(tasks, tasks_data, sha):
    routine_tasks = [t for t in tasks if t.get("assignee") == "共通"]

    if not routine_tasks:
        st.info("共通ルーティンはまだありません。`/task` で担当「共通」として登録してください。")
        return

    # サマリー
    cols = st.columns(4)
    for i, status in enumerate(STATUSES):
        count = sum(1 for t in routine_tasks if t.get("status") == status)
        s = STATUS_STYLE[status]
        with cols[i]:
            st.html(
                f"""<div style="
                    background:{s['bg']}; border:2px solid {s['border']};
                    border-radius:8px; padding:10px 14px; text-align:center;
                ">
                    <div style="font-size:22px; font-weight:700; color:{s['text']};">{count}</div>
                    <div style="font-size:12px; color:{s['text']};">{status}</div>
                </div>"""
            )

    st.html("<br>")

    # ステータスごとに縦並びで表示
    for status in STATUSES:
        status_tasks = [t for t in routine_tasks if t.get("status") == status]
        if not status_tasks:
            continue
        s = STATUS_STYLE[status]
        st.html(
            f"""<div style="
                display:inline-block; background:{s['bg']}; border:1px solid {s['border']};
                border-radius:4px; padding:3px 10px; font-size:12px;
                font-weight:700; color:{s['text']}; margin-bottom:8px;
            ">{status}</div>"""
        )
        cols = st.columns(3)
        for j, task in enumerate(status_tasks):
            with cols[j % 3]:
                render_card(task, tasks_data, sha)
        st.html("<br>")


def main():
    st.set_page_config(page_title="インターン依頼ボード", layout="wide", page_icon="📋")

    if "expanded" not in st.session_state:
        st.session_state.expanded = set()

    c1, c2 = st.columns([9, 1])
    with c1:
        st.title("📋 インターン依頼ボード")
    with c2:
        st.write("")
        if st.button("🔄 更新"):
            st.rerun()

    with st.spinner("読み込み中..."):
        tasks_data, sha = github_read()

    tasks = tasks_data.get("tasks", [])

    # サイドバーフィルター（ボードタブのみ有効）
    with st.sidebar:
        st.markdown("### 🔍 フィルター")
        st.caption("ボードタブに適用されます")

        selected_interns = st.multiselect(
            "インターン",
            options=INTERNS,
            default=[],
            placeholder="全員",
        )

        all_requesters = sorted(set(t.get("requester", "") for t in tasks if t.get("requester")))
        selected_requesters = st.multiselect(
            "依頼者",
            options=all_requesters,
            default=[],
            placeholder="全員",
        )

        all_sites = sorted(set(t.get("site", "") for t in tasks if t.get("site")))
        selected_sites = st.multiselect(
            "サイト",
            options=all_sites,
            default=[],
            placeholder="全サイト",
        )

    # フィルター適用（共通ルーティンは除外）
    board_tasks = [t for t in tasks if t.get("assignee") != "共通"]
    if selected_interns:
        board_tasks = [t for t in board_tasks if t.get("assignee") in selected_interns]
    if selected_requesters:
        board_tasks = [t for t in board_tasks if t.get("requester") in selected_requesters]
    if selected_sites:
        board_tasks = [t for t in board_tasks if t.get("site") in selected_sites]

    # タブ
    tab_board, tab_routine = st.tabs(["📋 ボード", "🔄 共通ルーティン"])

    with tab_board:
        render_board(board_tasks, tasks_data, sha, selected_interns)

    with tab_routine:
        render_routines(tasks, tasks_data, sha)


if __name__ == "__main__":
    main()
