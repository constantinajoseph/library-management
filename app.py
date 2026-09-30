
import streamlit as st
from datetime import date
from create_db import init_db
from functions import (
    login_admin,
    search_books,
    add_book,
    get_student,
    add_student,
    count_active_loans,
    issue_book,
    return_book,
    get_student_loans,
    get_all_loans,
    MAX_BOOKS,
)

# Initialize database
init_db()

st.set_page_config(
    page_title="Library Management System",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Library Management System")
st.caption("Finite State Machine based Book Issuing System")

# FSM transitions
DELTA = {
    ("LOGIN", "login_ok"): "SEARCH",
    ("LOGIN", "login_fail"): "LOGIN",
    ("SEARCH", "book_available"): "VERIFY_ID",
    ("SEARCH", "book_unavailable"): "SEARCH",
    ("VERIFY_ID", "id_valid"): "ID_VERIFIED",
    ("VERIFY_ID", "id_invalid"): "VERIFY_ID",
    ("VERIFY_ID", "cancel"): "SEARCH",
    ("ID_VERIFIED", "confirm"): "CHECK_LIMIT",
    ("ID_VERIFIED", "wrong_student"): "VERIFY_ID",
    ("ID_VERIFIED", "cancel"): "SEARCH",
    ("CHECK_LIMIT", "can_issue"): "ISSUED",
    ("CHECK_LIMIT", "cannot_issue"): "REJECTED",
    ("ISSUED", "new_search"): "SEARCH",
    ("REJECTED", "new_search"): "SEARCH",
}

# Initialize session state
defaults = {
    "state": "LOGIN",
    "history": ["LOGIN"],
    "admin": None,
    "book": None,
    "student": None,
    "result": "",
    "flash": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def move(event):
    current = st.session_state.state
    next_state = DELTA.get((current, event))

    if next_state is not None:
        st.session_state.state = next_state
        st.session_state.history.append(next_state)


def reset_flow():
    st.session_state.book = None
    st.session_state.student = None


def show_flash(ok, message):
    st.session_state.flash = (ok, message)
    st.rerun()


state = st.session_state.state

# ================= LOGIN =================
if state == "LOGIN":
    st.subheader("🔐 Admin Login")

    username = st.text_input("Username", key="login_user")
    password = st.text_input(
        "Password",
        type="password",
        key="login_password"
    )

    if st.button("Login", type="primary"):
        admin = login_admin(username, password)

        if admin is None:
            st.error("Invalid username or password.")
        else:
            st.session_state.admin = admin[1]
            move("login_ok")
            st.rerun()

# ================= ADMIN DASHBOARD =================
else:
    col1, col2 = st.columns([4, 1])

    with col1:
        st.write(f"**Admin:** {st.session_state.admin}")

    with col2:
        if st.button("Logout"):
            st.session_state.state = "LOGIN"
            st.session_state.history = ["LOGIN"]
            st.session_state.admin = None
            reset_flow()
            st.session_state.flash = None
            st.rerun()

    # Display messages
    if st.session_state.flash:
        ok, message = st.session_state.flash
        st.session_state.flash = None

        if ok:
            st.success(message)
        else:
            st.error(message)

    st.divider()

    # Current FSM state
    st.write(f"**Current FSM State:** `{state}`")
    st.write(
        "**Transition History:** "
        + " → ".join(st.session_state.history)
    )

    st.divider()

    # ================= SEARCH BOOK =================
    if state == "SEARCH":
        st.subheader("🔎 Step 1: Search for a Book")

        keyword = st.text_input(
            "Enter book title, author or category"
        )

        books = search_books(keyword)

        if not books:
            st.info("No books found.")

        for book in books:
            col1, col2 = st.columns([4, 1])

            with col1:
                st.write(f"### {book[1]}")
                st.write(f"Author: {book[2]}")
                st.write(f"Category: {book[3]}")
                st.write(
                    f"Available copies: **{book[4]}**"
                )

            with col2:
                st.write("")

                if st.button(
                    "Select Book",
                    key=f"book_{book[0]}"
                ):
                    if book[4] > 0:
                        st.session_state.book = book
                        move("book_available")
                        st.rerun()
                    else:
                        st.warning(
                            "This book is currently unavailable."
                        )

            st.divider()

    # ================= VERIFY STUDENT ID =================
    elif state == "VERIFY_ID":
        book = st.session_state.book

        st.subheader("🪪 Step 2: Student ID Verification")

        st.success(
            f"Book available: {book[1]} by {book[2]}"
        )

        reg_no = st.text_input(
            "Enter Student Register Number",
            key="verify_reg"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Verify ID", type="primary"):
                student = get_student(reg_no)

                if student is None:
                    st.error(
                        "Invalid register number. "
                        "Student not found."
                    )
                    move("id_invalid")
                else:
                    st.session_state.student = student
                    move("id_valid")
                    st.rerun()

        with col2:
            if st.button("Cancel"):
                reset_flow()
                move("cancel")
                st.rerun()

    # ================= STUDENT VERIFIED =================
    elif state == "ID_VERIFIED":
        book = st.session_state.book
        student = st.session_state.student

        st.subheader("✅ Step 3: Confirm Student")

        st.success("Student ID verified successfully.")

        st.write(f"**Student Name:** {student[1]}")
        st.write(f"**Register Number:** {student[0]}")
        st.write(f"**Selected Book:** {book[1]}")

        borrowed = count_active_loans(student[0])

        st.write(
            f"**Books currently borrowed:** "
            f"{borrowed} / {MAX_BOOKS}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(
                "Issue Book",
                type="primary"
            ):
                move("confirm")

                ok, message = issue_book(
                    student[0],
                    book[0]
                )

                move(
                    "can_issue" if ok else "cannot_issue"
                )

                st.session_state.result = message
                st.rerun()

        with col2:
            if st.button("Not This Student"):
                st.session_state.student = None
                move("wrong_student")
                st.rerun()

        with col3:
            if st.button("Cancel"):
                reset_flow()
                move("cancel")
                st.rerun()

    # ================= BOOK ISSUED =================
    elif state == "ISSUED":
        st.subheader("🎉 Book Issued Successfully")

        st.success(st.session_state.result)

        if st.button("Serve Next Student"):
            reset_flow()
            move("new_search")
            st.rerun()

    # ================= BOOK REJECTED =================
    elif state == "REJECTED":
        st.subheader("❌ Book Issuing Rejected")

        st.error(st.session_state.result)

        if st.button("Serve Next Student"):
            reset_flow()
            move("new_search")
            st.rerun()

    # ================= OTHER ADMIN TOOLS =================
    st.divider()
    st.subheader("⚙️ Admin Tools")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Return Book",
        "Current Loans",
        "Add Book",
        "Add Student"
    ])

    # ================= RETURN BOOK =================
    with tab1:
        st.subheader("Return a Book")

        reg = st.text_input(
            "Student Register Number",
            key="return_reg"
        )

        if reg:
            student = get_student(reg)

            if student is None:
                st.warning("Student not found.")
            else:
                st.success(
                    f"Verified: {student[1]} ({student[0]})"
                )

                loans = get_student_loans(student[0])

                if not loans:
                    st.info("No active borrowed books.")
                else:
                    choice = st.selectbox(
                        "Select Book to Return",
                        loans,
                        format_func=lambda loan: (
                            f"{loan[1]} | Due: {loan[3]}"
                        ),
                        key="return_choice"
                    )

                    if st.button("Return Book"):
                        ok, message = return_book(
                            student[0],
                            choice[0]
                        )
                        show_flash(ok, message)

    # ================= CURRENT LOANS =================
    with tab2:
        st.subheader("Currently Issued Books")

        loans = get_all_loans()

        if not loans:
            st.info("No books are currently issued.")
        else:
            today = date.today().isoformat()

            for reg, name, title, issued, due in loans:
                st.write(f"**Book:** {title}")
                st.write(f"**Student:** {name}")
                st.write(f"**Register Number:** {reg}")
                st.write(f"**Issue Date:** {issued}")
                st.write(f"**Due Date:** {due}")

                if due < today:
                    st.error("Overdue")
                else:
                    st.success("Active")

                st.divider()

    # ================= ADD BOOK =================
    with tab3:
        st.subheader("Add a New Book")

        title = st.text_input("Book Title", key="new_title")
        author = st.text_input("Author", key="new_author")
        category = st.text_input(
            "Category",
            key="new_category"
        )

        copies = st.number_input(
            "Number of Copies",
            min_value=1,
            step=1,
            value=1,
            key="new_copies"
        )

        if st.button("Add Book"):
            ok, message = add_book(
                title,
                author,
                category,
                int(copies)
            )
            show_flash(ok, message)

    # ================= ADD STUDENT =================
    with tab4:
        st.subheader("Add a Demo Student")

        reg_no = st.text_input(
            "Register Number",
            key="new_reg"
        )

        name = st.text_input(
            "Student Name",
            key="new_student_name"
        )

        if st.button("Add Student"):
            ok, message = add_student(reg_no, name)
            show_flash(ok, message)
