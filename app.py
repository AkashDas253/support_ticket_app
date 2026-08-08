import streamlit as st
import pandas as pd
import db

st.set_page_config(
    page_title="AI Support System",
    page_icon="🎫",
    layout="wide"
)

st.title("🎫 AI Support System (Lakebase)")

# -----------------------------------------------------------------------------
# Sidebar: Navigation & Ticket Creation
# -----------------------------------------------------------------------------
st.sidebar.header("Navigation & Actions")
status_filter = st.sidebar.selectbox("Filter Tickets by Status", ["All", "open", "in_progress", "resolved"])

with st.sidebar.expander("➕ Create New Ticket"):
    with st.form("create_ticket_form", clear_on_submit=True):
        new_ticket_id = st.text_input("Ticket ID", value=f"t-{int(pd.Timestamp.now().timestamp())}")
        new_title = st.text_input("Title")
        new_status = st.selectbox("Status", ["open", "in_progress", "resolved"])
        new_author = st.text_input("Created By (Email)", value="user@company.com")
        submit_ticket = st.form_submit_button("Submit Ticket")
        
        if submit_ticket:
            if not new_ticket_id or not new_title or not new_author:
                st.error("All fields are required.")
            else:
                db.create_ticket(new_ticket_id, new_title, new_status, new_author)
                st.success(f"Ticket {new_ticket_id} created successfully!")
                st.rerun()

# -----------------------------------------------------------------------------
# Main View: Split Layout for Tickets & Messages
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 1])

try:
    tickets_df = db.fetch_tickets(status_filter)
except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

# Column 1: Ticket List
with col1:
    st.subheader("Support Tickets")
    if tickets_df.empty:
        st.info("No tickets found.")
    else:
        st.dataframe(
            tickets_df,
            column_config={
                "ticket_id": "ID",
                "title": "Title",
                "status": "Status",
                "created_by": "Author",
                "created_at": "Created At"
            },
            hide_index=True,
            use_container_width=True
        )

# Column 2: Ticket Thread Details
with col2:
    st.subheader("Ticket Details & Thread")
    if not tickets_df.empty:
        selected_ticket_id = st.selectbox("Select Ticket ID to View", tickets_df["ticket_id"].tolist())
        
        selected_ticket = tickets_df[tickets_df["ticket_id"] == selected_ticket_id].iloc[0]
        st.write(f"**Title:** {selected_ticket['title']}")
        st.write(f"**Created By:** {selected_ticket['created_by']}")
        
        # Update Status
        current_status = selected_ticket['status']
        status_options = ["open", "in_progress", "resolved"]
        new_status = st.selectbox(
            "Update Status", 
            status_options, 
            index=status_options.index(current_status)
        )
        if new_status != current_status:
            if st.button("Update Status"):
                db.update_ticket_status(selected_ticket_id, new_status)
                st.success(f"Status updated to {new_status}")
                st.rerun()

        st.divider()
        st.markdown("### Messages")
        messages_df = db.fetch_messages(selected_ticket_id)
        
        if messages_df.empty:
            st.info("No messages in this ticket yet.")
        else:
            for _, msg in messages_df.iterrows():
                role = "user" if msg['author'] == selected_ticket['created_by'] else "assistant"
                with st.chat_message(role):
                    st.write(f"**{msg['author']}** *({msg['created_at']})*")
                    st.write(msg['message_text'])

        # Reply Form
        with st.form("add_message_form", clear_on_submit=True):
            msg_id = f"m-{int(pd.Timestamp.now().timestamp())}"
            msg_text = st.text_area("Add a Reply")
            msg_author = st.text_input("Your Name/Email", value="support_agent@company.com")
            submit_msg = st.form_submit_button("Send Message")
            
            if submit_msg:
                if not msg_text or not msg_author:
                    st.error("Message text and author are required.")
                else:
                    db.add_message(msg_id, selected_ticket_id, msg_text, msg_author)
                    st.success("Message added.")
                    st.rerun()