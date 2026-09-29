import streamlit as st
from datetime import date
from create_db import init_db
from functions import (
    login_member,
    register_member,
    search_books,
    issue_book,
    return_book,
    get_borrowed_books,
    is_admin,
    add_book,
)

# Create tables, starter admin and sample books if the database is new
init_db()

st.title("Library Management")

if "member" not in st.session_state:
    st.session_state.member = None

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
    st.write(f"Logged in as **{name}**")
    if st.button("Log out"):
        st.session_state.member = None
        st.rerun()

    # ----- Search -----
    st.header("Search for a book")
    keyword = st.text_input("Title, author or category")
    if keyword:
        books = search_books(keyword)
        if len(books) == 0:
            st.warning("No books found")
        else:
            for b in books:
                st.write(f"**{b[1]}** by {b[2]} | {b[3]} | Copies available: {b[4]}")

    # ----- Issue -----
    st.header("Issue a book")
    available = [b for b in search_books("") if b[4] > 0]
    if len(available) == 0:
        st.info("No books are available right now.")
    else:
        choice = st.selectbox(
            "Choose a book to borrow",
            available,
            format_func=lambda b: f"{b[1]} by {b[2]} ({b[4]} available)",
            key="issue_choice",
        )
        if st.button("Issue book"):
            ok, message = issue_book(member_id, choice[0])
            if ok:
                st.success(message)
            else:
                st.error(message)

    # ----- Return -----
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
            if ok:
                st.success(message)
            else:
                st.error(message)

    # ----- My borrowed books -----
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
    if is_admin(member_id):
        st.header("Admin: add a book")
        b_title = st.text_input("Title", key="b_title")
        b_author = st.text_input("Author", key="b_author")
        b_category = st.text_input("Category", key="b_category")
        b_copies = st.number_input("Copies", min_value=1, step=1, key="b_copies")

        if st.button("Add book"):
            ok, message = add_book(b_title, b_author, b_category, int(b_copies))
            if ok:
                st.success(message)
            else:
                st.error(message)
