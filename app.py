import streamlit as st
from datetime import date
from create_db import init_db
from functions import (
    login_member,
    register_member,
    search_books,
    return_book,
    get_borrowed_books,
    is_admin,
    add_book,
    request_book,
    get_member_requests,
    get_pending_requests,
    approve_request,
    reject_request,
)

# Create tables, starter admin and sample books if the database is new
init_db()

st.title("Library Management")

if "member" not in st.session_state:
    st.session_state.member = None


def flash(ok, message):
    st.session_state.flash = (ok, message)
    st.rerun()


# ---------- Login / Create account ----------
if st.session_state.member is None:
    tab_login, tab_signup = st.tabs(["Login", "Create account"])

    with tab_login:
        reg_no = st.text_input("Registration number", key="login_reg")
        password = st.text_input("Password", type="password", key="login_pw")

        if st.button("Log in"):
            member = login_member(reg_no, password)
            if member is None:
                st.error("Wrong registration number or password")
            else:
                st.session_state.member = member
                st.rerun()

    with tab_signup:
        new_reg = st.text_input("Registration number", key="signup_reg")
        new_name = st.text_input("Full name", key="signup_name")
        new_pw = st.text_input("Password", type="password", key="signup_pw")

        if st.button("Create account"):
            result = register_member(new_reg, new_name, new_pw)
            message = result[-1] if isinstance(result, tuple) else str(result)
            st.info(message)

# ---------- Logged-in pages ----------
else:
    member_id, name = st.session_state.member
    admin = is_admin(member_id)

    st.write(f"Logged in as **{name}**" + (" (Admin)" if admin else ""))
    if st.button("Log out"):
        st.session_state.member = None
        st.rerun()

    # Show the result of the last button click (survives the rerun)
    if "flash" in st.session_state:
        ok, message = st.session_state.pop("flash")
        if ok:
            st.success(message)
        else:
            st.error(message)

    # ----- Search (students can request from here) -----
    st.header("Search for a book")
    keyword = st.text_input("Title, author or category")
    if keyword:
        books = search_books(keyword)
        if len(books) == 0:
            st.warning("No books found")
        else:
            for b in books:
                col_info, col_btn = st.columns([4, 1])
                col_info.write(f"**{b[1]}** by {b[2]} | {b[3]} | Copies available: {b[4]}")
                if not admin:
                    if col_btn.button("Request", key=f"req_{b[0]}"):
                        ok, message = request_book(member_id, b[0])
                        flash(ok, message)

    # ---------- Student pages ----------
    if not admin:
        st.header("My requests")
        my_requests = get_member_requests(member_id)
        if len(my_requests) == 0:
            st.write("You have not requested any books.")
        else:
            for request_id, title, status, requested_on, note in my_requests:
                line = f"**{title}** | Requested: {requested_on} | Status: {status}"
                if status == "Rejected" and note:
                    line += f" | Reason: {note}"
                if status == "Approved":
                    st.success(line)
                elif status == "Rejected":
                    st.error(line)
                else:
                    st.info(line)

        st.header("Return a book")
        to_return = get_borrowed_books(member_id)
        if len(to_return) == 0:
            st.info("You have no books to return.")
        else:
            return_choice = st.selectbox(
                "Choose a book to return",
                to_return,
                format_func=lambda b: f"{b[1]} (due {b[3]})",
                key="return_choice",
            )
            if st.button("Return book"):
                ok, message = return_book(member_id, return_choice[0])
                flash(ok, message)

        st.header("My borrowed books")
        borrowed = get_borrowed_books(member_id)
        if len(borrowed) == 0:
            st.write("You have no borrowed books.")
        else:
            today = date.today().isoformat()
            for book_id, title, issue_date, due_date in borrowed:
                line = f"**{title}** | Issued: {issue_date} | Due: {due_date}"
                if due_date < today:
                    st.error(line + " (OVERDUE)")
                else:
                    st.write(line)

    # ---------- Admin only ----------
    if admin:
        st.header("Admin: pending requests")
        pending = get_pending_requests()
        if len(pending) == 0:
            st.info("No pending requests.")
        else:
            for request_id, reg, student, title, copies, requested_on in pending:
                st.write(
                    f"**{title}** | {student} ({reg}) | Requested: {requested_on} "
                    f"| Copies available: {copies}"
                )
                col_a, col_r, col_note = st.columns([1, 1, 2])
                note = col_note.text_input(
                    "Reason (optional)", key=f"note_{request_id}",
                    label_visibility="collapsed", placeholder="Reason if rejecting")
                if col_a.button("Approve & issue", key=f"ok_{request_id}", disabled=copies < 1):
                    ok, message = approve_request(request_id)
                    flash(ok, message)
                if col_r.button("Reject", key=f"no_{request_id}"):
                    ok, message = reject_request(request_id, note)
                    flash(ok, message)
                if copies < 1:
                    st.caption("No copies available, so this can only be rejected for now.")
                st.divider()

        st.header("Admin: add a book")
        b_title = st.text_input("Title", key="b_title")
        b_author = st.text_input("Author", key="b_author")
        b_category = st.text_input("Category", key="b_category")
        b_copies = st.number_input("Copies", min_value=1, step=1, key="b_copies")

        if st.button("Add book"):
            ok, message = add_book(b_title, b_author, b_category, int(b_copies))
            flash(ok, message)
