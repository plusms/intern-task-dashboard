import streamlit as st
import json
import base64
import urllib.request
import urllib.error
import html as html_mod

REPO = "plusms/intern-task-dashboard"
FILE_PATH = "tasks.json"
ROUTINES_FILE_PATH = "routines.json"
INTERNS = ["亀矢", "佐藤", "武田", "中村", "山田"]
ASSIGNEE_OPTIONS = ["全員"] + ["亀矢", "佐藤", "武田", "中村", "山田"]
FREQUENCY_OPTIONS = ["毎出勤時", "週1回", "隔週", "月1回", "その他"]
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


def github_read_routines():
    token = get_token()
    url = f"https://api.github.com/repos/{REPO}/contents/{ROUTINES_FILE_PATH}"
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
            return {"routines": []}, None
        st.error(f"GitHub読み込みエラー: {e.code}")
        st.stop()


def github_write_routines(content, sha, message="update routines"):
    token = get_token()
    url = f"https://api.github.com/repos/{REPO}/contents/{ROUTINES_FILE_PATH}"
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
        url, data=data, method="PUT",
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
            edit_task_key = f"edit_task_{task_id}"
            is_editing_task = st.session_state.get(edit_task_key, False)

            if not is_editing_task:
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
                c1, c2 = st.columns(2)
                with c1:
                    new_status = st.selectbox(
                        "ステータス", STATUSES,
                        index=STATUSES.index(task.get("status", "未着手")),
                        key=f"sel_{task_id}",
                    )
                    if st.button("保存", key=f"btn_{task_id}", type="primary", use_container_width=True):
                        latest_data, latest_sha = github_read()
                        for t in latest_data["tasks"]:
                            if t["id"] == task_id:
                                t["status"] = new_status
                                break
                        result = github_write(latest_data, latest_sha, f"status: {task['title']} → {new_status}")
                        if result:
                            st.success(f"✅ {new_status} に更新しました")
                            st.rerun()
                with c2:
                    st.write("")
                    if st.button("✏️ 編集", key=f"edit_task_btn_{task_id}", use_container_width=True):
                        st.session_state[edit_task_key] = True
                        st.rerun()
            else:
                e_title    = st.text_input("タイトル", value=task.get("title", ""), key=f"et_{task_id}")
                e_site     = st.text_input("サイト", value=task.get("site", ""), key=f"es_{task_id}")
                e_assignee = st.selectbox("担当", INTERNS, index=INTERNS.index(task.get("assignee", INTERNS[0])) if task.get("assignee") in INTERNS else 0, key=f"ea_{task_id}")
                e_priority = st.selectbox("優先度", ["ルーティン", "差し込み"], index=0 if task.get("priority") != "差し込み" else 1, key=f"ep_{task_id}")
                e_deadline = st.text_input("期限（YYYY-MM-DD、なければ空欄）", value=task.get("deadline", ""), key=f"ed_{task_id}")
                e_requester= st.text_input("依頼者", value=task.get("requester", ""), key=f"er_{task_id}")
                e_content  = st.text_area("作業内容", value=task.get("content", ""), key=f"ec_{task_id}", height=80)
                e_ref      = st.text_input("参照スキル", value=task.get("reference", ""), key=f"erf_{task_id}")
                e_notes    = st.text_input("補足", value=task.get("notes", ""), key=f"en_{task_id}")

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("💾 保存", key=f"save_task_{task_id}", type="primary", use_container_width=True):
                        latest_data, latest_sha = github_read()
                        for t in latest_data["tasks"]:
                            if t["id"] == task_id:
                                t.update({"title": e_title, "site": e_site, "assignee": e_assignee,
                                          "priority": e_priority, "deadline": e_deadline,
                                          "requester": e_requester, "content": e_content,
                                          "reference": e_ref, "notes": e_notes})
                                break
                        result = github_write(latest_data, latest_sha, f"edit task: {e_title}")
                        if result:
                            st.session_state[edit_task_key] = False
                            st.success("保存しました")
                            st.rerun()
                with c2:
                    if st.button("🗑️ 削除", key=f"del_task_{task_id}", use_container_width=True):
                        latest_data, latest_sha = github_read()
                        latest_data["tasks"] = [t for t in latest_data["tasks"] if t["id"] != task_id]
                        result = github_write(latest_data, latest_sha, f"delete task: {task.get('title','')}")
                        if result:
                            st.session_state[edit_task_key] = False
                            st.rerun()
                with c3:
                    if st.button("キャンセル", key=f"cancel_task_{task_id}", use_container_width=True):
                        st.session_state[edit_task_key] = False
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

    st.html("<br>")
    st.markdown("---")
    st.markdown("#### ＋ タスク追加")
    with st.container(border=True):
        import uuid as _uuid
        from datetime import datetime as _dt
        c1, c2 = st.columns(2)
        with c1:
            f_title    = st.text_input("タイトル", key="f_title")
            f_assignee = st.selectbox("担当", INTERNS, key="f_assignee")
            f_priority = st.selectbox("優先度", ["ルーティン", "差し込み"], key="f_priority")
            f_deadline = st.text_input("期限（YYYY-MM-DD、なければ空欄）", key="f_deadline")
        with c2:
            f_requester = st.text_input("依頼者", key="f_requester")
            f_site      = st.text_input("サイト", key="f_site")
            f_ref       = st.text_input("参照スキル", key="f_ref")
            f_notes     = st.text_input("補足", key="f_notes")
        f_content = st.text_area("作業内容", key="f_content", height=80)

        if st.button("登録する", type="primary", use_container_width=True, key="f_submit"):
            if not f_title:
                st.warning("タイトルを入力してください")
            else:
                new_task = {
                    "id": str(_uuid.uuid4())[:8],
                    "title": f_title, "site": f_site,
                    "priority": f_priority, "deadline": f_deadline,
                    "assignee": f_assignee, "requester": f_requester,
                    "status": "未着手", "content": f_content,
                    "reference": f_ref, "notes": f_notes,
                    "created_at": _dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
                }
                latest_data, latest_sha = github_read()
                latest_data["tasks"].append(new_task)
                result = github_write(latest_data, latest_sha, f"add task: {f_title}")
                if result:
                    st.success(f"「{f_title}」を登録しました")
                    st.rerun()


def render_routine_card(r, routines_data, r_sha):
    import uuid as _uuid
    rid = r["id"]
    edit_key = f"edit_routine_{rid}"
    is_editing = st.session_state.get(edit_key, False)

    assignee = r.get("assignee", "全員")
    assignee_color = "#6b7280" if assignee == "全員" else "#3b82f6"
    assignee_bg = "#f3f4f6" if assignee == "全員" else "#eff6ff"

    detail_key = f"detail_routine_{rid}"
    is_detail_open = st.session_state.get(detail_key, False)

    with st.container(border=True):
        if not is_editing:
            st.html(
                f"""
                <div style="padding:2px 0 4px;">
                    <div style="font-weight:700; font-size:14px; margin-bottom:8px;">{esc(r.get('title',''))}</div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <span style="font-size:11px; color:#6b7280;">
                            頻度: <strong style="color:#16a34a;">{esc(r.get('frequency',''))}</strong>
                        </span>
                        <span style="font-size:11px; color:#6b7280;">
                            担当: <strong style="color:{assignee_color};">{esc(assignee)}</strong>
                        </span>
                    </div>
                </div>
                """
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("▲ 閉じる" if is_detail_open else "▼ 詳細", key=f"detail_btn_{rid}", use_container_width=True):
                    st.session_state[detail_key] = not is_detail_open
                    st.rerun()
            with c2:
                if st.button("✏️ 編集", key=f"edit_btn_{rid}", use_container_width=True):
                    st.session_state[edit_key] = True
                    st.rerun()

            if is_detail_open:
                if r.get("command"):
                    st.markdown(f"**コマンド:** `{r.get('command')}`")
                if r.get("description"):
                    st.write(r.get("description"))
        else:
            new_title = st.text_input("業務タイトル", value=r.get("title", ""), key=f"t_{rid}")
            new_freq = st.selectbox("頻度", FREQUENCY_OPTIONS,
                index=FREQUENCY_OPTIONS.index(r.get("frequency", "毎出勤時")) if r.get("frequency") in FREQUENCY_OPTIONS else 0,
                key=f"f_{rid}")
            new_cmd = st.text_input("使用コマンド", value=r.get("command", ""), key=f"c_{rid}")
            new_desc = st.text_area("詳細", value=r.get("description", ""), key=f"d_{rid}", height=80)
            new_assignee = st.selectbox("担当", ASSIGNEE_OPTIONS,
                index=ASSIGNEE_OPTIONS.index(r.get("assignee", "全員")) if r.get("assignee") in ASSIGNEE_OPTIONS else 0,
                key=f"a_{rid}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存", key=f"save_{rid}", type="primary", use_container_width=True):
                    latest, latest_sha = github_read_routines()
                    for item in latest["routines"]:
                        if item["id"] == rid:
                            item["title"] = new_title
                            item["frequency"] = new_freq
                            item["command"] = new_cmd
                            item["description"] = new_desc
                            item["assignee"] = new_assignee
                            break
                    result = github_write_routines(latest, latest_sha, f"update routine: {new_title}")
                    if result:
                        st.session_state[edit_key] = False
                        st.success("保存しました")
                        st.rerun()
            with col2:
                if st.button("🗑️ 削除", key=f"del_{rid}", use_container_width=True):
                    latest, latest_sha = github_read_routines()
                    latest["routines"] = [item for item in latest["routines"] if item["id"] != rid]
                    result = github_write_routines(latest, latest_sha, f"delete routine: {r.get('title','')}")
                    if result:
                        st.session_state[edit_key] = False
                        st.rerun()
            if st.button("キャンセル", key=f"cancel_{rid}", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()


def render_routines():
    import uuid as _uuid
    routines_data, r_sha = github_read_routines()
    routines = routines_data.get("routines", [])

    if routines:
        cols = st.columns(3)
        for i, r in enumerate(routines):
            with cols[i % 3]:
                render_routine_card(r, routines_data, r_sha)
    else:
        st.info("ルーティンはまだありません。下のフォームから追加してください。")

    st.html("<br>")
    st.markdown("---")
    st.markdown("#### ＋ 新規ルーティン追加")

    with st.container(border=True):
        new_title = st.text_input("業務タイトル", key="new_r_title")
        col1, col2 = st.columns(2)
        with col1:
            new_freq = st.selectbox("頻度", FREQUENCY_OPTIONS, key="new_r_freq")
        with col2:
            new_assignee = st.selectbox("担当", ASSIGNEE_OPTIONS, key="new_r_assignee")
        new_cmd = st.text_input("使用コマンド（例: /knowhow-update）", key="new_r_cmd")
        new_desc = st.text_area("詳細", key="new_r_desc", height=80)

        if st.button("登録する", type="primary", use_container_width=True, key="new_r_submit"):
            if not new_title:
                st.warning("業務タイトルを入力してください")
            else:
                import uuid as _uuid
                new_r = {
                    "id": "r" + str(_uuid.uuid4())[:7],
                    "title": new_title,
                    "frequency": new_freq,
                    "command": new_cmd,
                    "description": new_desc,
                    "assignee": new_assignee,
                }
                latest, latest_sha = github_read_routines()
                latest["routines"].append(new_r)
                result = github_write_routines(latest, latest_sha, f"add routine: {new_title}")
                if result:
                    st.success(f"「{new_title}」を登録しました")
                    st.rerun()


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
        render_routines()


if __name__ == "__main__":
    main()
