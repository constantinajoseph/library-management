import streamlit as st
from datetime import date
from create_db import init_db
from functions import (
    login,
    register_student,
    search_books,
    add_book,
    request_book,
    get_my_requests,
    get_my_loans,
    get_pending_requests,
    decide_request,
    get_all_loans,
    return_book,
    MAX_BOOKS,
)

st.set_page_config(page_title="Library Management System", page_icon="📚")

# Create the tables, the starter admin and sample books if the database is new
init_db()

st.title("📚 Library Management System")

if "user" not in st.session_state:
    st.session_state.user = None
if "flash" not in st.session_state:
    st.session_state.flash = None


def flash(ok, message):
    """Save a message, then reload the page so the screen shows fresh data."""
    st.session_state.flash = (ok, message)
    st.rerun()


def show_flash():
    if st.session_state.flash:
        ok, message = st.session_state.flash
        st.session_state.flash = None
        if ok:
            st.success(message)
        else:
            st.error(message)


user = st.session_state.user

# =====================================================
#  Not logged in: Log in / Create account
# =====================================================
if user is None:
    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    with tab_login:
        reg = st.text_input("Register number (admin: username)", key="login_reg")
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Log in"):
            found = login(reg, pw)
            if found is None:
                st.error("Wrong register number or password.")
            else:
                st.session_state.user = found
                st.rerun()

    with tab_signup:
        st.caption("Use a NEW password for this website. Do not use your ERP password.")
        s_reg = st.text_input("Register number", key="signup_reg")
        s_name = st.text_input("Full name", key="signup_name")
        s_pw = st.text_input("Password (at least 6 characters)", type="password", key="signup_pw")
        if st.button("Create account"):
            ok, message = register_student(s_reg, s_name, s_pw)
            if ok:
                st.success(message)
            else:
                st.error(message)

    st.stop()

# =====================================================
#  Logged in
# =====================================================
role = "Admin" if user["is_admin"] else "Student"
col_who, col_out = st.columns([4, 1])
col_who.write(f"Logged in as **{user['name']}** ({role})")
if col_out.button("Log out"):
    st.session_state.user = None
    st.rerun()

show_flash()

# =====================================================
#  Student profile
# =====================================================
if not user["is_admin"]:
    tab_search, tab_requests, tab_loans = st.tabs(
        ["Search and request", "My requests", "My borrowed books"])

    with tab_search:
        keyword = st.text_input("Search by title, author or category (leave empty to see all)")
        books = search_books(keyword)
        if len(books) == 0:
            st.warning("No books found")
        for b in books:
            col_info, col_btn = st.columns([4, 1])
            col_info.write(f"**{b[1]}** by {b[2]} | {b[3] or '-'} | Copies available: {b[4]}")
            if col_btn.button("Request", key=f"req_{b[0]}", disabled=(b[4] < 1)):
                ok, message = request_book(user["member_id"], b[0])
                flash(ok, message)

    with tab_requests:
        rows = get_my_requests(user["member_id"])
        if len(rows) == 0:
            st.write("You have not requested any books yet.")
        for req_id, title, status, requested_on, note in rows:
            line = f"**{title}** | {status} | Requested on {requested_on}"
            if status == "Rejected" and note:
                line += f" | Reason: {note}"
            st.write(line)

    with tab_loans:
        rows = get_my_loans(user["member_id"])
        st.write(f"Books borrowed: {len(rows)} of {MAX_BOOKS}")
        today = date.today().isoformat()
        for loan_id, title, issue_date, due_date in rows:
            line = f"**{title}** | Issued: {issue_date} | Due: {due_date}"
            if due_date < today:
                st.error(line + " (OVERDUE)")
            else:
                st.write(line)

# =====================================================
#  Admin profile
# =====================================================
else:
    tab_pending, tab_loans, tab_book = st.tabs(
        ["Pending requests", "Current loans", "Add book"])

    with tab_pending:
        pending = get_pending_requests()
        if len(pending) == 0:
            st.write("No pending requests.")
        for req_id, reg_no, s_name, title, copies, requested_on in pending:
            st.write(f"**{title}** | {s_name} ({reg_no}) | "
                     f"Requested on {requested_on} | Copies available: {copies}")
            note = st.text_input("Reason (optional, used if you reject)", key=f"note_{req_id}")
            col_a, col_r = st.columns(2)
            if col_a.button("Approve and issue", key=f"app_{req_id}", disabled=(copies < 1)):
                ok, message = decide_request(req_id, True)
                flash(ok, message)
            if col_r.button("Reject", key=f"rej_{req_id}"):
                ok, message = decide_request(req_id, False, note)
                flash(ok, message)
            st.divider()

    with tab_loans:
        rows = get_all_loans()
        if len(rows) == 0:
            st.write("No books are currently issued.")
        today = date.today().isoformat()
        for loan_id, reg_no, s_name, title, issue_date, due_date in rows:
            line = f"**{title}** | {s_name} ({reg_no}) | Issued: {issue_date} | Due: {due_date}"
            if due_date < today:
                st.error(line + " (OVERDUE)")
            else:
                st.write(line)
            if st.button("Mark as returned", key=f"ret_{loan_id}"):
                ok, message = return_book(loan_id)
                flash(ok, message)

    with tab_book:
        b_title = st.text_input("Title", key="b_title")
        b_author = st.text_input("Author", key="b_author")
        b_category = st.text_input("Category", key="b_category")
        b_copies = st.number_input("Copies", min_value=1, step=1, key="b_copies")
        if st.button("Add book"):
            ok, message = add_book(b_title, b_author, b_category, int(b_copies))
            flash(ok, message)
