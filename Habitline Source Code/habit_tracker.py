import streamlit as st
from datetime import datetime

# 1. Set up the mobile page view
st.set_page_config(page_title="Habitline", page_icon="📈", layout="centered")

st.title("📈 Habitline Tracker")
st.write("Track your daily habits directly from your phone!")

# 2. Initialize browser memory (Session State) to hold habits
if "habits" not in st.session_state:
    st.session_state.habits = {
        "Exercise": {"completed": False, "streak": 5, "history": []},
        "Read 15 Mins": {"completed": True, "streak": 12, "history": []},
        "Drink Water": {"completed": False, "streak": 3, "history": []}
    }

# 3. Sidebar section to ADD new habits
st.sidebar.header("Add a New Habit")
new_habit_name = st.sidebar.text_input("Habit Name:")
if st.sidebar.button("Add Habit"):
    if new_habit_name.strip() != "":
        if new_habit_name not in st.session_state.habits:
            st.session_state.habits[new_habit_name] = {"completed": False, "streak": 0, "history": []}
            st.sidebar.success(f"Added '{new_habit_name}'!")
            st.rerun()
        else:
            st.sidebar.warning("That habit already exists!")

# 4. Main App Interface: Display and track current habits
st.subheader("Today's Progress")

# Calculate percentage complete for a progress bar
total_habits = len(st.session_state.habits)
if total_habits > 0:
    completed_count = sum(1 for h in st.session_state.habits.values() if h["completed"])
    progress_percent = completed_count / total_habits
    st.progress(progress_percent)
    st.write(f"Completed {completed_count} out of {total_habits} habits today.")
else:
    st.write("No habits added yet! Use the sidebar menu to add some.")

st.divider()

# List out the habits with toggle check-boxes
for habit, data in list(st.session_state.habits.items()):
    col1, col2, col3 = st.columns([4, 2, 1])
    
    with col1:
        # Checkbox to complete habit
        is_checked = st.checkbox(habit, value=data["completed"], key=f"check_{habit}")
        if is_checked != data["completed"]:
            st.session_state.habits[habit]["completed"] = is_checked
            if is_checked:
                st.session_state.habits[habit]["streak"] += 1
            else:
                st.session_state.habits[habit]["streak"] = max(0, st.session_state.habits[habit]["streak"] - 1)
            st.rerun()
            
    with col2:
        # Display the current streak
        st.write(f"🔥 {data['streak']} day streak")
        
    with col3:
        # Delete button to remove a habit
        if st.button("🗑️", key=f"del_{habit}"):
            del st.session_state.habits[habit]
            st.rerun()

# 5. Reset button at the bottom for a new day
st.divider()
if st.button("Reset Everything for Tomorrow"):
    for habit in st.session_state.habits:
        st.session_state.habits[habit]["completed"] = False
    st.success("All habits reset to uncompleted!")
    st.rerun()
