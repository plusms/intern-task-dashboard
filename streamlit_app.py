import streamlit as st
import json
import base64
import urllib.request
import urllib.error

# ── 定数 ──────────────────────────────────────────────────────────────────
REPO = "plusms/intern-claudeprojects"
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
    "差し込み": {"bg": "#fee2e2", "text": "#dc2626"},
    "ルーティン": {"bg": "#f3f4f6", "text": "#6b7280"},
}


# ── GitHub API ──────────────────────────────────────────────────────────────
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


# ── カード描画 ──────────────────────────────────────────────────────────────
def render_card(task, tasks_data, sha):
    priority = task.get("priority", "ルーティン")
    ps = PRIORITY_STYLE.get(priority, PRIORITY_STYLE["ルーティン"])
    deadline = task.get("deadline") or ""
    task_id = task["id"]

    st.markdown(
        f"""
        <div style="
            background: white;
            border: 1px solid #e5e7eb;
            border-left: 4px solid {PRIORITY_STYLE['差し込み']['text'] if priority == '差し込み' else '#d1d5db'};
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 8px;
        ">
            <div style="font-weight:600; font-size:13px; margin-bottom:6px; line-height:1.4;">
                {task['title']}
            </div>
            <div style="font-size:11px; color:#6b7280; margin-bottom:6px;">
                📍 {task.get('site', '')}
            </div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
                <span style="
                    background:{ps['bg']}; color:{ps['text']};
                    border-radius:4px; padding:2px 7px; font-size:10px; font-weight:600;
                ">{priority}</span>
                {f'<span style="font-size:11px; color:#ef4444;">⏰ {deadline}</span>' if deadline else ''}
            </div>
            <div style="font-size:10px; color:#9ca3af; margin-top:6px;">依頼: {task.get('requester', '')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("詳細 / ステータス変更"):
        st.markdown(f"**📝 作業内容**")
        st.markdown(task.get("content", ""))
        if task.get("reference"):
            st.markdown(f"**📎 参照スキル**")
            st.markdown(task.get("reference", ""))
        if task.get("notes"):
            st.markdown(f"**💬 補足**")
            st.markdown(task.get("notes", ""))
        st.markdown(f"*作成日: {str(task.get('created_at', ''))[:10]}*")

        st.divider()
        new_status = st.selectbox(
            "ステータス",
            STATUSES,
            index=STATUSES.index(task.get("status", "未着手")),
            key=f"sel_{task_id}",
        )
        if st.button("保存", key=f"btn_{task_id}", type="primary"):
            # 最新SHAで再取得してから書き込む（競合対策）
            latest_data, latest_sha = github_read()
            for t in latest_data["tasks"]:
                if t["id"] == task_id:
                    t["status"] = new_status
                    break
            result = github_write(latest_data, latest_sha, f"status: {task['title']} → {new_status}")
            if result:
                st.success(f"✅ {new_status} に更新しました")
                st.rerun()


# ── メイン ──────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="インターン依頼ボード", layout="wide", page_icon="📋")

    # ヘッダー
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
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("status") == "完了")

    # サマリー
    cols = st.columns(4)
    for i, status in enumerate(STATUSES):
        count = sum(1 for t in tasks if t.get("status") == status)
        s = STATUS_STYLE[status]
        cols[i].markdown(
            f"""<div style="
                background:{s['bg']}; border:2px solid {s['border']};
                border-radius:8px; padding:10px 14px; text-align:center;
            ">
                <div style="font-size:22px; font-weight:700; color:{s['text']};">{count}</div>
                <div style="font-size:12px; color:{s['text']};">{status}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 列ヘッダー
    header = st.columns([1.2] + [1] * 4)
    header[0].markdown("")
    for i, status in enumerate(STATUSES):
        s = STATUS_STYLE[status]
        header[i + 1].markdown(
            f"""<div style="
                background:{s['bg']}; border:2px solid {s['border']};
                border-radius:6px; padding:6px; text-align:center;
                font-weight:700; font-size:13px; color:{s['text']};
            ">{status}</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

    # インターンごとの行
    for intern in INTERNS:
        row = st.columns([1.2] + [1] * 4)
        with row[0]:
            st.markdown(
                f"""<div style="
                    padding:12px 8px; font-weight:600; font-size:14px; color:#374151;
                ">👤 {intern}</div>""",
                unsafe_allow_html=True,
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
                    st.markdown(
                        "<div style='min-height:44px; border:1px dashed #e5e7eb; border-radius:6px; margin-bottom:8px;'></div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("<hr style='margin:4px 0; border-color:#f3f4f6;'>", unsafe_allow_html=True)

    if total == 0:
        st.info("タスクがまだありません。Claude Codeで `/task` を実行して登録してください。")


if __name__ == "__main__":
    main()
