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

# Create tables, starter admin, sample books and demo students if the database is new
init_db()

st.title("Library Management using FSM")

# =====================================================
#  The Finite State Machine
#  Q  = {LOGIN, SEARCH, VERIFY_ID, ID_VERIFIED, CHECK_LIMIT, ISSUED, REJECTED}
#  q0 = LOGIN            F = {ISSUED}
#  delta(state, event) -> next state
# =====================================================
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

for key, default in [
    ("state", "LOGIN"),
    ("history", ["LOGIN"]),
    ("admin", None),
    ("book", None),
    ("student", None),
    ("result", ""),
    ("flash", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def move(event):
    """Apply one transition of the FSM."""
    nxt = DELTA.get((st.session_state.state, event))
    if nxt is None:
        return
    st.session_state.state = nxt
    st.session_state.history.append(nxt)


def flash(ok, message):
    st.session_state.flash = (ok, message)
    st.rerun()


def fsm_diagram(current):
    dot = [
        "digraph FSM {",
        "rankdir=LR;",
        'bgcolor="white";',
        'node [shape=circle, style=filled, fillcolor="white", fontcolor="black", fontsize=10];',
        "edge [fontsize=9];",
        'START [shape=point, fillcolor="black"];',
        "START -> LOGIN;",
        "ISSUED [shape=doublecircle];",
        f'{current} [fillcolor="#FFD54F"];',
    ]
    for (s, e), t in DELTA.items():
        dot.append(f'{s} -> {t} [label="{e}"];')
    dot.append("}")
    return "\n".join(dot)


def reset_flow():
    st.session_state.book = None
    st.session_state.student = None


state = st.session_state.state

# ---------- State: LOGIN ----------
if state == "LOGIN":
    st.subheader("Librarian login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pw")

    if st.button("Log in"):
        admin = login_admin(username, password)
        if admin is None:
            move("login_fail")
            st.error("Wrong username or password")
        else:
            st.session_state.admin = admin[1]
            move("login_ok")
            st.rerun()

# ---------- Logged in ----------
else:
    col_who, col_out = st.columns([4, 1])
    col_who.write(f"Logged in as **{st.session_state.admin}** (Admin)")
    if col_out.button("Log out"):
        st.session_state.state = "LOGIN"
        st.session_state.history = ["LOGIN"]
        st.session_state.admin = None
        reset_flow()
        st.rerun()

    if st.session_state.flash:
        ok, message = st.session_state.flash
        st.session_state.flash = None
        if ok:
            st.success(message)
        else:
            st.error(message)

    # ----- FSM status -----
    st.write(f"**Current state:** `{state}`")
    st.write("**Path so far:** " + " → ".join(st.session_state.history))
    with st.expander("Show FSM diagram", expanded=False):
        st.graphviz_chart(fsm_diagram(state))
    st.divider()

    # ---------- State: SEARCH ----------
    if state == "SEARCH":
        st.subheader("Step 1: Search for the book the student wants")
        keyword = st.text_input("Title, author or category (leave empty to see all)")
        books = search_books(keyword)
        if len(books) == 0:
            st.warning("No books found")
        for b in books:
            col_info, col_btn = st.columns([4, 1])
            col_info.write(f"**{b[1]}** by {b[2]} | {b[3]} | Copies available: {b[4]}")
            if col_btn.button("Select", key=f"sel_{b[0]}"):
                if b[4] > 0:
                    st.session_state.book = b
                    move("book_available")
                    st.rerun()
                else:
                    move("book_unavailable")
                    flash(False, f"'{b[1]}' is not available right now.")

    # ---------- State: VERIFY_ID ----------
    elif state == "VERIFY_ID":
        book = st.session_state.book
        st.subheader("Step 2: Verify the student's ID")
        st.success(f"Yes, the book is available: **{book[1]}** by {book[2]}")
        reg = st.text_input("Student register number", key="reg_input")

        col_v, col_c = st.columns(2)
        if col_v.button("Verify ID"):
            student = get_student(reg)
            if student is None:
                move("id_invalid")
                flash(False, f"Invalid register number: '{reg.strip()}' is not in the student list.")
            st.session_state.student = student
            move("id_valid")
            st.rerun()
        if col_c.button("Cancel"):
            reset_flow()
            move("cancel")
            st.rerun()

    # ---------- State: ID_VERIFIED ----------
    elif state == "ID_VERIFIED":
        book = st.session_state.book
        student = st.session_state.student
        st.subheader("Step 3: Confirm the student")
        st.success(f"ID verified: **{student[1]}** (Register number: {student[0]})")
        st.write(f"Book to issue: **{book[1]}** by {book[2]}")
        st.write(f"Books currently borrowed: {count_active_loans(student[0])} of {MAX_BOOKS}")

        col_ok, col_wrong, col_c = st.columns(3)
        if col_ok.button("Confirm and issue book"):
            move("confirm")                                   # -> CHECK_LIMIT
            ok, message = issue_book(student[0], book[0])
            move("can_issue" if ok else "cannot_issue")       # -> ISSUED or REJECTED
            st.session_state.result = message
            st.rerun()
        if col_wrong.button("Not this student"):
            st.session_state.student = None
            move("wrong_student")
            st.rerun()
        if col_c.button("Cancel"):
            reset_flow()
            move("cancel")
            st.rerun()

    # ---------- State: ISSUED ----------
    elif state == "ISSUED":
        st.subheader("Book issued")
        st.success(st.session_state.result)
        if st.button("Serve the next student"):
            reset_flow()
            move("new_search")
            st.rerun()

    # ---------- State: REJECTED ----------
    elif state == "REJECTED":
        st.subheader("Book not issued")
        st.error(st.session_state.result)
        if st.button("Serve the next student"):
            reset_flow()
            move("new_search")
            st.rerun()

    # ---------- Other admin tools ----------
    st.divider()
    st.subheader("Other admin tools")
    tab_ret, tab_loans, tab_book, tab_stud = st.tabs(
        ["Return a book", "Current loans", "Add book", "Add student"])

    with tab_ret:
        r_reg = st.text_input("Student register number", key="ret_reg")
        if r_reg:
            r_student = get_student(r_reg)
            if r_student is None:
                st.warning("Invalid register number")
            else:
                st.success(f"ID verified: {r_student[1]} ({r_student[0]})")
                loans = get_student_loans(r_student[0])
                if len(loans) == 0:
                    st.info(f"{r_student[1]} has no borrowed books.")
                else:
                    choice = st.selectbox(
                        "Book to return",
                        loans,
                        format_func=lambda l: f"{l[1]} (due {l[3]})",
                        key="ret_choice",
                    )
                    if st.button("Return book"):
                        ok, message = return_book(r_student[0], choice[0])
                        flash(ok, message)

    with tab_loans:
        rows = get_all_loans()
        if len(rows) == 0:
            st.write("No books are currently issued.")
        else:
            today = date.today().isoformat()
            for reg_no, s_name, title, issue_date, due_date in rows:
                line = f"**{title}** | {s_name} ({reg_no}) | Issued: {issue_date} | Due: {due_date}"
                if due_date < today:
                    st.error(line + " (OVERDUE)")
                else:
                    st.write(line)

    with tab_book:
        b_title = st.text_input("Title", key="b_title")
        b_author = st.text_input("Author", key="b_author")
        b_category = st.text_input("Category", key="b_category")
        b_copies = st.number_input("Copies", min_value=1, step=1, key="b_copies")
        if st.button("Add book"):
            ok, message = add_book(b_title, b_author, b_category, int(b_copies))
            flash(ok, message)

    with tab_stud:
        st.caption("Adds a student to the demo ERP list.")
        s_reg = st.text_input("Register number", key="s_reg")
        s_name = st.text_input("Student name", key="s_name")
        if st.button("Add student"):
            ok, message = add_student(s_reg, s_name)
            flash(ok, message)
