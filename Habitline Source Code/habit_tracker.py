"""GitHub-ready Streamlit entry point for Habitline."""

from __future__ import annotations

import html
import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from habitline_core import (
    DEFAULT_COLORS,
    DEFAULT_NUTRITION_GOALS,
    DEFAULT_XP_REWARDS,
    NUTRIENT_KEYS,
    OPEN_FOOD_FACTS_BASE,
    OPEN_FOOD_FACTS_FIELDS,
    HabitStore,
    fetch_open_food_facts,
    fetch_usda_foods,
    habit_stats,
    kickboxing_grade_xp,
    open_food_facts_product,
    scaled_nutrients,
    search_offline_foods,
    validate_body_entry,
    validate_food,
    validate_food_entry,
    validate_goal,
    validate_journal_entry,
    validate_kickboxing_session,
    validate_meal,
    validate_nutrition_goals,
    validate_planner_event,
    validate_recovery_entry,
    validate_shopping_item,
    validate_weekly_schedule_item,
    validate_workout,
    validate_workout_day,
)


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "habits.json"
MUSCLES = ["Chest", "Back", "Shoulders", "Biceps", "Triceps", "Forearms", "Core", "Other"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
LEVELS = [
    ("F", 0), ("E", 250), ("D", 600), ("C", 1100), ("B", 1800),
    ("A", 2700), ("S", 3800), ("SS", 5100), ("SSS", 6600), ("G", 8500),
]
NUTRIENT_META = {
    "calories": ("Energy", "kcal", "General"),
    "water": ("Water", "g", "General"),
    "protein": ("Protein", "g", "Protein & Amino Acids"),
    "fat": ("Fat", "g", "Lipids"),
    "carbs": ("Carbs", "g", "Carbohydrates"),
    "net_carbs": ("Net carbs", "g", "Carbohydrates"),
    "fibre": ("Fibre", "g", "Carbohydrates"),
    "sugars": ("Sugars", "g", "Carbohydrates"),
    "added_sugars": ("Added sugars", "g", "Carbohydrates"),
    "saturated_fat": ("Saturated fat", "g", "Lipids"),
    "omega_3": ("Omega-3", "g", "Lipids"),
    "omega_6": ("Omega-6", "g", "Lipids"),
    "cholesterol": ("Cholesterol", "mg", "Lipids"),
    "vitamin_b1": ("B1 (Thiamine)", "mg", "Vitamins"),
    "vitamin_b2": ("B2 (Riboflavin)", "mg", "Vitamins"),
    "vitamin_b3": ("B3 (Niacin)", "mg", "Vitamins"),
    "vitamin_b5": ("B5 (Pantothenic acid)", "mg", "Vitamins"),
    "vitamin_b6": ("B6 (Pyridoxine)", "mg", "Vitamins"),
    "vitamin_b12": ("B12 (Cobalamin)", "mcg", "Vitamins"),
    "folate": ("Folate", "mcg", "Vitamins"),
    "vitamin_a": ("Vitamin A", "mcg", "Vitamins"),
    "vitamin_c": ("Vitamin C", "mg", "Vitamins"),
    "vitamin_d": ("Vitamin D", "mcg", "Vitamins"),
    "vitamin_e": ("Vitamin E", "mg", "Vitamins"),
    "vitamin_k": ("Vitamin K", "mcg", "Vitamins"),
    "calcium": ("Calcium", "mg", "Minerals"),
    "copper": ("Copper", "mg", "Minerals"),
    "iron": ("Iron", "mg", "Minerals"),
    "magnesium": ("Magnesium", "mg", "Minerals"),
    "manganese": ("Manganese", "mg", "Minerals"),
    "phosphorus": ("Phosphorus", "mg", "Minerals"),
    "potassium": ("Potassium", "mg", "Minerals"),
    "selenium": ("Selenium", "mcg", "Minerals"),
    "sodium": ("Sodium", "mg", "Minerals"),
    "zinc": ("Zinc", "mg", "Minerals"),
}
LIMIT_NUTRIENTS = {"added_sugars", "saturated_fat", "trans_fat", "cholesterol", "sodium"}
KICKBOXING = [
    ("9th Kyu Red/White", "Stance, movement and basic strikes", [
        "Jab > Cross > Lead Low Kick",
        "Jab > Cross > Lead Hook > Rear Low Kick > Check",
        "Jab > Lead Front Kick > Rear Front Kick",
    ]),
    ("9th Kyu Red", "Basic striking, defence and pivoting", [
        "Jab > Cross > Lead Low Kick",
        "Jab > Cross > Lead Hook > Rear Low Kick",
        "Jab > Rear Hook > Lead Uppercut > Rear Knee",
    ]),
    ("8th Kyu Yellow/White", "Add round kicks, parries and fluid movement", [
        "Jab > Rear Uppercut > Lead Round-Kick",
        "Jab > Lead Front Kick > Rear Front Kick",
        "Jab > Cross > Lead Hook > Rear Low Kick",
    ]),
    ("8th Kyu Yellow", "Head/body combinations, slipping and defence", [
        "Jab > Body Cross > Lead Hook > Rear Low Kick",
        "Jab > Cross > Lead Body Round Kick > Cross > Lead Hook > Rear Round-Kick",
    ]),
    ("7th Kyu Orange/White", "Add rolls and head/body round kicks", [
        "Jab > Cross > Roll > Cross > Lead Hook",
        "Switch Round-Kick > Cross > Lead Body Hook",
    ]),
    ("7th Kyu Orange", "Add switch kicks and pull-back defence", [
        "Switch Round-Kick > Cross > Lead Body Hook",
        "Body Jab > Rear Overhand > Lead Body Round-Kick",
    ]),
    ("6th Kyu Green/White", "Add rear overhand, checks and stronger defence", [
        "Body Jab > Rear Overhand > Lead Body Round-Kick",
        "Cross > Switch-Knee > Rear Hook > Shovel Hook",
    ]),
    ("6th Kyu Green", "Add shovel hook, switch knee and combinations", [
        "Cross > Switch-Knee > Rear Hook > Shovel Hook",
        "Lead Parry > Cross > Lead Hook > Spinning Back-fist",
    ]),
    ("5th Kyu Blue/White", "Power, accuracy and defensive exits", [
        "Lead Parry > Cross > Lead Hook > Spinning Back-fist",
        "Jab > Cross > Roll > Cross > Lead Hook",
    ]),
    ("5th Kyu Blue", "Add feints, cross-checks and step-off exits", [
        "Jab > Cross > Lead Low Kick > Cross-check",
        "Cross > Switch-Knee > Rear Hook > Shovel Hook > Frame and Exit",
    ]),
    ("4th Kyu Purple/White", "Add crescent kicks, axe kicks and long guard", [
        "Axe-Kick > Jab > Cross > Crescent Kick > Rear Axe Kick > Step-Back",
        "Lead Parry > Cross > Lead Hook > Spinning Back-fist > Slip and Exit",
    ]),
    ("4th Kyu Purple", "Advanced movement, jumping knee and bag-work", [
        "Check Hook > Jumping Knee > Long Frame and Exit",
        "Axe-Kick > Jab > Cross > Crescent Kick > Rear Axe Kick > Step-Back",
    ]),
]


st.set_page_config(
    page_title="Habitline Streamlit",
    page_icon=str(ROOT / "icon-192.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f5f7fb; color: #172033; }
    [data-testid="stSidebar"] { background: #121722; }
    [data-testid="stSidebar"] * { color: #f6f7fb; }
    .block-container { max-width: 1500px; padding-top: 1.4rem; }
    div[data-testid="stMetric"] {
      background: white; border: 1px solid #e2e7f0; border-radius: 18px;
      padding: 18px; box-shadow: 0 8px 24px rgba(24,32,52,.05);
    }
    .card {
      background: white; border: 1px solid #e2e7f0; border-radius: 18px;
      padding: 18px; margin-bottom: 14px;
    }
    .rank { display:inline-block; padding:5px 12px; border-radius:999px;
      background:#5b6cff; color:white; font-weight:800; }
    .muted { color:#718096; font-size:.9rem; }
    .good { color:#0f8b61; font-weight:700; }
    .warn { color:#c06b12; font-weight:700; }
    .bad { color:#ce4257; font-weight:700; }
    .nutrient-row { display:grid; grid-template-columns:190px 100px 1fr 60px;
      gap:12px; align-items:center; padding:6px 0; font-size:.9rem; }
    .bar { background:#edf0f6; height:9px; border-radius:20px; overflow:hidden; }
    .bar > span { display:block; height:100%; border-radius:20px; background:#5b6cff; }
    @media (prefers-color-scheme: dark) {
      .stApp { background:#0f131a; color:#f2f4f8; }
      div[data-testid="stMetric"], .card { background:#181e28; border-color:#2a3442; }
      .muted { color:#a8b3c5; } .bar { background:#2a3442; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_store() -> HabitStore:
    return HabitStore(DATA_FILE)


store = get_store()


def reload_store() -> None:
    store.load()


def rerun(message: str | None = None) -> None:
    if message:
        st.session_state["flash"] = message
    st.rerun()


def show_flash() -> None:
    message = st.session_state.pop("flash", None)
    if message:
        st.toast(message)


def day_key(value: date | str) -> str:
    return value if isinstance(value, str) else value.isoformat()


def level_stats() -> dict:
    xp = max(0, int(store.settings.get("xp_balance", 0)))
    index = max(i for i, (_, minimum) in enumerate(LEVELS) if xp >= minimum)
    name, minimum = LEVELS[index]
    if index == len(LEVELS) - 1:
        return {"xp": xp, "rank": name, "progress": 100, "next": None, "remaining": 0}
    next_name, next_minimum = LEVELS[index + 1]
    progress = (xp - minimum) / (next_minimum - minimum) * 100
    return {
        "xp": xp, "rank": name, "progress": min(100, max(0, progress)),
        "next": next_name, "remaining": next_minimum - xp,
    }


def selected_date() -> date:
    return st.session_state.get("selected_date", date.today())


def nutrition_totals(selected: date) -> dict[str, float]:
    totals = {key: 0.0 for key in NUTRIENT_KEYS}
    for entry in store.food_entries:
        if entry.get("date") != selected.isoformat():
            continue
        food = store.get_food(entry.get("food_id", ""))
        if not food:
            continue
        for key, value in scaled_nutrients(food, float(entry.get("amount_g", 0))).items():
            totals[key] += value
    return totals


def profile_energy() -> tuple[float, float] | None:
    profile = store.settings.get("profile", {})
    weight = float(profile.get("body_weight", 0) or 0)
    if profile.get("weight_unit") == "lb":
        weight /= 2.2046226218
    height = float(profile.get("height_cm", 0) or 0)
    age = int(profile.get("age", 0) or 0)
    if not weight or not height or not age:
        return None
    rmr = 10 * weight + 6.25 * height - 5 * age + (-161 if profile.get("sex") == "female" else 5)
    multiplier = {"inactive": 1.2, "low": 1.375, "active": 1.55, "very": 1.725}.get(
        profile.get("activity_level"), 1.55
    )
    adjustment = {"lose": -400, "maintain": 0, "recomposition": -100, "gain": 250, "performance": 150}.get(
        profile.get("goal_type"), -100
    )
    return rmr, max(1200, rmr * multiplier + adjustment)


def habit_done(habit: dict, selected: date) -> bool:
    return store._habit_met(habit, habit.get("entries", {}).get(selected.isoformat()))


def weekly_muscle_sets(selected: date | None = None) -> dict[str, float]:
    selected = selected or date.today()
    start = selected - timedelta(days=selected.weekday())
    end = start + timedelta(days=6)
    totals = {muscle: 0.0 for muscle in MUSCLES if muscle != "Other"}
    for workout in store.workouts:
        try:
            workout_date = date.fromisoformat(workout["date"])
        except (KeyError, ValueError):
            continue
        if not start <= workout_date <= end:
            continue
        exercise = store.get_exercise(workout.get("exercise_id", ""))
        if not exercise:
            continue
        primary = exercise.get("muscle_group", "Other")
        if primary in totals:
            totals[primary] += float(workout.get("sets", 0))
        for secondary in exercise.get("secondary_muscles", []):
            if secondary in totals:
                totals[secondary] += float(workout.get("sets", 0)) * 0.5
    return {key: value for key, value in totals.items() if value}


def readiness(entry: dict | None) -> int:
    if not entry:
        return 0
    sleep = min(100, float(entry.get("sleep_hours", 0)) / 8 * 100)
    wellbeing = (
        float(entry.get("sleep_quality", 3))
        + float(entry.get("energy", 3))
        + (6 - float(entry.get("soreness", 3)))
        + (6 - float(entry.get("stress", 3)))
        + float(entry.get("mood", 3))
    ) / 25 * 100
    return round(sleep * 0.4 + wellbeing * 0.6)


def add_xp_for_workout(workout: dict) -> tuple[int, str]:
    reward_key = store._workout_reward_key(workout)
    amount = store.settings["xp_rewards"][reward_key]
    return store.set_xp_award(f"workout:{workout['id']}", amount), reward_key


def strength_rating(exercise: dict, estimated_1rm: float) -> tuple[str, float] | None:
    profile = store.settings.get("profile", {})
    body_weight = float(profile.get("body_weight", 0) or 0)
    if profile.get("weight_unit") != exercise.get("unit", "kg"):
        body_weight = body_weight * 2.2046226218 if profile.get("weight_unit") == "kg" else body_weight / 2.2046226218
    if not body_weight or not estimated_1rm:
        return None
    age = int(profile.get("age", 0) or 0)
    age_adjustment = 1 if not age or age < 50 else .95 if age < 60 else .88 if age < 70 else .8
    thresholds = [.6, .9, 1.2, 1.5, 1.8] if exercise.get("muscle_group") == "Back" else [.4, .65, .9, 1.15, 1.4]
    adjusted_ratio = estimated_1rm / body_weight / age_adjustment
    tier_index = sum(adjusted_ratio >= threshold for threshold in thresholds)
    return ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond"][tier_index], estimated_1rm / body_weight


def nutrient_progress(totals: dict, goals: dict, keys: list[str]) -> None:
    rows = []
    for key in keys:
        if key not in NUTRIENT_META:
            continue
        label, unit, _ = NUTRIENT_META[key]
        value = float(totals.get(key, 0))
        goal = float(goals.get(key, 0))
        percent = value / goal * 100 if goal else 0
        colour = "#d14b5a" if key in LIMIT_NUTRIENTS and percent > 100 else "#19a974" if 80 <= percent <= 110 else "#5b6cff"
        rows.append(
            f'<div class="nutrient-row"><span>{html.escape(label)}</span>'
            f'<span>{value:.1f} {unit}</span><div class="bar"><span style="width:{min(percent,100):.1f}%;background:{colour}"></span></div>'
            f'<strong>{percent:.0f}%</strong></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def home_page() -> None:
    today = date.today()
    game = level_stats()
    habits_done = sum(habit_done(habit, today) for habit in store.habits)
    habit_percent = habits_done / len(store.habits) * 100 if store.habits else 0
    totals = nutrition_totals(today)
    goals = store.nutrition_goals
    latest_recovery = max(store.recovery_entries, key=lambda item: item.get("date", ""), default=None)
    energy = profile_energy()
    calorie_goal = energy[1] if energy and store.settings.get("profile", {}).get("auto_nutrition") else goals.get("calories", 0)

    st.title("Habitline")
    st.caption("Your habits, strength, nutrition, recovery and plan in one place.")
    cols = st.columns(5)
    cols[0].metric("Level", game["rank"], f"{game['xp']} XP")
    cols[1].metric("Today's habits", f"{habit_percent:.0f}%", f"{habits_done}/{len(store.habits)} complete")
    cols[2].metric("Calories", f"{totals['calories']:.0f}", f"of {calorie_goal:.0f} kcal")
    cols[3].metric("Recovery", f"{readiness(latest_recovery)}%", "latest check-in")
    cols[4].metric("Active goals", sum(not goal.get("completed") for goal in store.goals))
    st.progress(game["progress"] / 100, text=f"{game['remaining']} XP to level {game['next']}" if game["next"] else "Maximum level")

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Today")
        for habit in store.habits:
            value = habit.get("entries", {}).get(today.isoformat())
            status = "Complete" if habit_done(habit, today) else "Not completed"
            st.write(f"**{habit['name']}**  ·  {status}" + (f"  ·  {value} {habit.get('unit','')}" if value is not None and habit["type"] == "number" else ""))
        events = [
            item for item in store.planner_events if item.get("date") == today.isoformat()
        ]
        for item in sorted(events, key=lambda row: row.get("start", "")):
            st.write(f"**{item.get('start') or 'All day'}**  ·  {item['title']}")
    with right:
        st.subheader("Weekly lifting sets")
        sets = weekly_muscle_sets()
        if sets:
            st.bar_chart(pd.DataFrame({"sets": sets}))
            for muscle, count in sets.items():
                message = "too many" if count > 20 else "excellent" if count >= 13 else "good" if count >= 10 else "low"
                st.caption(f"{muscle}: {count:g}/20 sets · {message}")
        else:
            st.info("No lifting sets logged this week.")

    st.subheader("Nutrition snapshot")
    nutrient_progress(totals, goals, ["calories", "protein", "carbs", "fat", "fibre", "iron", "calcium", "potassium"])


def habits_page() -> None:
    st.title("Habits")
    selected = selected_date()
    st.session_state["selected_date"] = st.date_input("Tracking date", selected, key="habit_date")
    selected = selected_date()

    with st.expander("Add a habit"):
        with st.form("add_habit"):
            name = st.text_input("Habit name")
            habit_type = st.selectbox("Tracking type", ["check", "number"], format_func=lambda value: "Tick box" if value == "check" else "Number target")
            target = st.number_input("Daily target", min_value=0.01, value=1.0)
            unit = st.text_input("Unit", placeholder="steps, pages, minutes")
            colour = st.color_picker("Colour", DEFAULT_COLORS[0])
            if st.form_submit_button("Add habit", use_container_width=True):
                if not name.strip():
                    st.error("Give the habit a name.")
                else:
                    store.add({
                        "id": uuid.uuid4().hex, "name": name.strip(), "type": habit_type,
                        "target": target if habit_type == "number" else 1, "unit": unit.strip() if habit_type == "number" else "",
                        "color": colour, "entries": {},
                    })
                    rerun("Habit added")

    for habit in store.habits:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1.2, 0.35])
            c1.markdown(f"### {habit['name']}")
            current = habit.get("entries", {}).get(selected.isoformat())
            if habit["type"] == "check":
                value = c2.checkbox("Completed", value=bool(current), key=f"habit_{habit['id']}_{selected}")
            else:
                value = c2.number_input(
                    f"{habit.get('unit') or 'Value'} / {habit['target']:g}",
                    min_value=0.0, value=float(current or 0), key=f"habit_{habit['id']}_{selected}",
                )
            save, delete = c3.columns(2)
            if save.button("✓", key=f"save_habit_{habit['id']}", help="Save"):
                active = store._habit_met(habit, value)
                store.set_entry(habit["id"], selected.isoformat(), value)
                change = store.set_xp_award(
                    f"habit:{habit['id']}:{selected.isoformat()}",
                    store.settings["xp_rewards"]["habit"], active,
                )
                rerun(f"Habit saved · {change:+d} XP" if change else "Habit saved")
            if delete.button("×", key=f"delete_habit_{habit['id']}", help="Delete"):
                store.revoke_xp_prefix(f"habit:{habit['id']}:")
                store.delete(habit["id"])
                rerun("Habit deleted")

            days = [selected - timedelta(days=index) for index in range(13, -1, -1)]
            chart = []
            for day in days:
                entry = habit.get("entries", {}).get(day.isoformat())
                chart.append(100 if habit["type"] == "check" and entry else float(entry or 0))
            st.line_chart(pd.DataFrame({"value": chart}, index=days), height=170)
            week = habit_stats(habit, selected, "week")
            month = habit_stats(habit, selected, "month")
            a, b = st.columns(2)
            a.metric("Weekly average", f"{week['average']:.1f}" + ("%" if habit["type"] == "check" else f" {habit.get('unit','')}"))
            b.metric("Monthly average", f"{month['average']:.1f}" + ("%" if habit["type"] == "check" else f" {habit.get('unit','')}"))


def lifting_page() -> None:
    st.title("Strength training")
    add_tab, log_tab, plans_tab, history_tab = st.tabs(["Exercises", "Log workout", "Workout days", "Progress"])

    with add_tab:
        with st.form("add_exercise"):
            name = st.text_input("Exercise name")
            unit = st.selectbox("Weight unit", ["kg", "lb"])
            primary = st.selectbox("Primary muscle", MUSCLES)
            secondary = st.multiselect("Secondary muscles", [value for value in MUSCLES if value != primary and value != "Other"])
            colour = st.color_picker("Colour", DEFAULT_COLORS[0], key="exercise_colour")
            if st.form_submit_button("Save exercise"):
                if not name.strip():
                    st.error("Give the exercise a name.")
                else:
                    store.add_exercise({
                        "id": uuid.uuid4().hex, "name": name.strip(), "unit": unit,
                        "color": colour, "muscle_group": primary, "secondary_muscles": secondary,
                    })
                    rerun("Exercise added")
        if store.exercises:
            selected_id = st.selectbox("Edit or delete exercise", [item["id"] for item in store.exercises], format_func=lambda value: store.get_exercise(value)["name"])
            exercise = store.get_exercise(selected_id)
            with st.form("edit_exercise"):
                edited_name = st.text_input("Name", exercise["name"])
                edited_primary = st.selectbox("Primary muscle", MUSCLES, index=MUSCLES.index(exercise.get("muscle_group", "Other")))
                edited_secondary = st.multiselect("Secondary muscles", [value for value in MUSCLES if value != edited_primary and value != "Other"], default=[value for value in exercise.get("secondary_muscles", []) if value != edited_primary])
                save, remove = st.columns(2)
                if save.form_submit_button("Update"):
                    store.update_exercise(selected_id, {"name": edited_name.strip(), "muscle_group": edited_primary, "secondary_muscles": edited_secondary})
                    rerun("Exercise updated")
                if remove.form_submit_button("Delete"):
                    for workout in list(store.workouts):
                        if workout.get("exercise_id") == selected_id:
                            store.set_xp_award(f"workout:{workout['id']}", 0, False)
                    store.delete_exercise(selected_id)
                    rerun("Exercise deleted")

    with log_tab:
        if not store.exercises:
            st.info("Add an exercise first.")
        else:
            with st.form("log_workout"):
                exercise_id = st.selectbox("Exercise", [item["id"] for item in store.exercises], format_func=lambda value: store.get_exercise(value)["name"])
                previous = sorted([item for item in store.workouts if item["exercise_id"] == exercise_id], key=lambda item: (item["date"], item["id"]), reverse=True)
                if previous:
                    last = previous[0]
                    st.caption(f"Previous: {last['weight']:g} {store.get_exercise(exercise_id)['unit']} · {last['sets']} sets × {last['reps']} reps")
                workout_date = st.date_input("Date", date.today(), key="workout_date")
                c1, c2, c3 = st.columns(3)
                weight = c1.number_input("Weight", min_value=0.0, value=float(previous[0]["weight"]) if previous else 0.0)
                sets = c2.number_input("Sets", min_value=1, value=int(previous[0]["sets"]) if previous else 3)
                reps = c3.number_input("Reps", min_value=1, value=int(previous[0]["reps"]) if previous else 8)
                notes = st.text_input("Notes")
                if st.form_submit_button("Log workout", use_container_width=True):
                    workout = {"id": uuid.uuid4().hex, **validate_workout({
                        "exercise_id": exercise_id, "date": workout_date.isoformat(),
                        "weight": weight, "sets": sets, "reps": reps, "notes": notes,
                    }, store)}
                    store.add_workout(workout)
                    change, reward = add_xp_for_workout(workout)
                    reason = {
                        "workout_first": "first exercise session",
                        "workout_improvement": "weight, sets or reps improved",
                        "workout_standard": "workout completed",
                    }[reward]
                    rerun(f"Workout logged · +{change} XP · {reason}")

    with plans_tab:
        if not store.exercises:
            st.info("Add exercises before creating a workout day.")
        else:
            with st.form("add_workout_day"):
                plan_name = st.text_input("Workout day name", placeholder="Push, Pull, Upper")
                exercise_ids = st.multiselect("Exercises", [item["id"] for item in store.exercises], format_func=lambda value: store.get_exercise(value)["name"])
                if st.form_submit_button("Create workout day"):
                    plan = {"id": uuid.uuid4().hex, **validate_workout_day({"name": plan_name, "exercise_ids": exercise_ids}, store)}
                    store.add_workout_day(plan)
                    rerun("Workout day created")
            for plan in store.workout_days:
                with st.expander(plan["name"]):
                    rows = [store.get_exercise(value) for value in plan["exercise_ids"] if store.get_exercise(value)]
                    st.write(", ".join(item["name"] for item in rows))
                    with st.form(f"log_plan_{plan['id']}"):
                        plan_date = st.date_input("Date", date.today(), key=f"plan_date_{plan['id']}")
                        values = []
                        for exercise in rows:
                            previous = sorted([item for item in store.workouts if item["exercise_id"] == exercise["id"]], key=lambda item: (item["date"], item["id"]), reverse=True)
                            defaults = previous[0] if previous else {"weight": 0, "sets": 3, "reps": 8}
                            st.markdown(f"**{exercise['name']}**")
                            cols = st.columns(3)
                            values.append({
                                "exercise": exercise,
                                "weight": cols[0].number_input("Weight", min_value=0.0, value=float(defaults["weight"]), key=f"pw_{plan['id']}_{exercise['id']}"),
                                "sets": cols[1].number_input("Sets", min_value=1, value=int(defaults["sets"]), key=f"ps_{plan['id']}_{exercise['id']}"),
                                "reps": cols[2].number_input("Reps", min_value=1, value=int(defaults["reps"]), key=f"pr_{plan['id']}_{exercise['id']}"),
                            })
                        if st.form_submit_button(f"Log {plan['name']}"):
                            total_xp = 0
                            session_id = uuid.uuid4().hex
                            for row in values:
                                workout = {
                                    "id": uuid.uuid4().hex, "exercise_id": row["exercise"]["id"],
                                    "date": plan_date.isoformat(), "weight": row["weight"],
                                    "sets": row["sets"], "reps": row["reps"], "notes": "",
                                    "workout_day_id": plan["id"], "session_id": session_id,
                                }
                                store.add_workout(workout)
                                change, _ = add_xp_for_workout(workout)
                                total_xp += change
                            rerun(f"{plan['name']} logged · +{total_xp} XP")
                    if st.button("Delete workout day", key=f"delete_plan_{plan['id']}"):
                        store.delete_workout_day(plan["id"])
                        rerun("Workout day deleted")

    with history_tab:
        if not store.workouts:
            st.info("No workouts logged yet.")
        else:
            exercise_id = st.selectbox("View exercise", [item["id"] for item in store.exercises], format_func=lambda value: store.get_exercise(value)["name"], key="progress_exercise")
            exercise = store.get_exercise(exercise_id)
            workouts = sorted([item for item in store.workouts if item["exercise_id"] == exercise_id], key=lambda item: (item["date"], item["id"]))
            if workouts:
                frame = pd.DataFrame(workouts)
                frame["estimated 1RM"] = frame["weight"] * (1 + frame["reps"] / 30)
                frame["volume"] = frame["weight"] * frame["sets"] * frame["reps"]
                rating = strength_rating(exercise, float(frame["estimated 1RM"].max()))
                if rating:
                    st.markdown(f"<span class='rank'>{rating[0]}</span> &nbsp; **{rating[1]:.2f}× bodyweight**", unsafe_allow_html=True)
                    st.caption("Informal relative-strength benchmark based on your profile and best estimated one-rep maximum.")
                else:
                    st.info("Add age and bodyweight in Settings to calculate a strength rank.")
                st.line_chart(frame.set_index("date")[["weight", "estimated 1RM"]])
                st.dataframe(frame[["date", "weight", "sets", "reps", "volume", "estimated 1RM", "notes"]], use_container_width=True, hide_index=True)
                delete_id = st.selectbox("Delete a workout", [item["id"] for item in reversed(workouts)], format_func=lambda value: next(item for item in workouts if item["id"] == value)["date"])
                if st.button("Delete selected workout"):
                    store.set_xp_award(f"workout:{delete_id}", 0, False)
                    store.delete_workout(delete_id)
                    rerun("Workout deleted")
            st.subheader("Sets per muscle this week")
            sets = weekly_muscle_sets()
            if sets:
                st.bar_chart(pd.DataFrame({"sets": sets}))


def food_page() -> None:
    st.title("Food and nutrition")
    food_date = st.date_input("Food date", selected_date(), key="food_date")
    st.session_state["selected_date"] = food_date
    totals = nutrition_totals(food_date)
    goals = store.nutrition_goals
    c1, c2, c3, c4, c5 = st.columns(5)
    for column, key in zip((c1, c2, c3, c4, c5), ("calories", "protein", "carbs", "fat", "fibre")):
        label, unit, _ = NUTRIENT_META[key]
        column.metric(label, f"{totals[key]:.1f} {unit}", f"{totals[key] / goals[key] * 100:.0f}% of goal" if goals.get(key) else "No target")

    add_tab, detail_tab, library_tab, meals_tab = st.tabs(["Add food", "Daily nutrients", "Food library", "Meals & shopping"])
    with add_tab:
        query = st.text_input("Search offline food library")
        options = search_offline_foods(store.foods, query, 30) if query else store.foods[:30]
        if options:
            food_id = st.selectbox("Food", [item["id"] for item in options], format_func=lambda value: store.get_food(value)["name"])
            amount = st.number_input("Amount (g)", min_value=1.0, value=100.0)
            if st.button("Add food", type="primary"):
                entry = {"id": uuid.uuid4().hex, **validate_food_entry({"food_id": food_id, "date": food_date.isoformat(), "amount_g": amount}, store)}
                store.add_food_entry(entry)
                rerun("Food added")
        action_cols = st.columns(2)
        if action_cols[0].button("Repeat yesterday's food"):
            yesterday = food_date - timedelta(days=1)
            previous = [item for item in store.food_entries if item["date"] == yesterday.isoformat()]
            for item in previous:
                store.add_food_entry({
                    "id": uuid.uuid4().hex, "food_id": item["food_id"],
                    "date": food_date.isoformat(), "amount_g": item["amount_g"],
                })
            rerun(f"Repeated {len(previous)} food entries" if previous else "No food was logged yesterday")
        st.divider()
        st.subheader("Barcode lookup")
        barcode = st.text_input("UPC / EAN barcode")
        if st.button("Look up barcode"):
            cleaned = "".join(character for character in barcode if character.isdigit())
            existing = next((item for item in store.foods if item.get("barcode") == cleaned), None)
            if existing:
                st.session_state["barcode_food"] = existing
            elif cleaned:
                try:
                    payload = fetch_open_food_facts(
                        f"{OPEN_FOOD_FACTS_BASE}/api/v2/product/{cleaned}.json?fields={OPEN_FOOD_FACTS_FIELDS}"
                    )
                    st.session_state["barcode_food"] = open_food_facts_product(payload.get("product", {}))
                except ValueError as error:
                    st.error(str(error))
        barcode_food = st.session_state.get("barcode_food")
        if barcode_food:
            st.write(f"**{barcode_food['name']}** · {barcode_food.get('brand', '')}")
            if not store.get_food(barcode_food.get("id", "")) and st.button("Save barcode product"):
                saved = {"id": uuid.uuid4().hex, **validate_food(barcode_food)}
                store.add_food(saved)
                st.session_state.pop("barcode_food", None)
                rerun("Barcode product saved")
        st.divider()
        st.subheader("Optional online USDA search")
        online_query = st.text_input("USDA search", placeholder="chicken breast")
        if st.button("Search USDA"):
            try:
                st.session_state["usda_results"] = fetch_usda_foods(online_query, store.settings.get("usda_api_key", "DEMO_KEY"))
            except ValueError as error:
                st.error(str(error))
        results = st.session_state.get("usda_results", [])
        if results:
            result_index = st.selectbox("USDA result", range(len(results)), format_func=lambda index: results[index]["name"])
            if st.button("Save selected USDA food"):
                raw = results[result_index]
                existing = next((item for item in store.foods if item.get("fdc_id") == raw.get("fdc_id")), None)
                if existing:
                    rerun("That USDA food is already saved")
                food = {"id": uuid.uuid4().hex, **validate_food(raw)}
                food["fdc_id"] = raw.get("fdc_id", "")
                store.add_food(food)
                rerun("USDA food saved to your library")

        entries = [item for item in store.food_entries if item["date"] == food_date.isoformat()]
        if entries:
            st.subheader("Today's entries")
            for entry in entries:
                food = store.get_food(entry["food_id"])
                cols = st.columns([3, 1, .5])
                cols[0].write(f"**{food['name']}**")
                cols[1].write(f"{entry['amount_g']:g} g")
                if cols[2].button("Delete", key=f"delete_food_entry_{entry['id']}"):
                    store.delete_food_entry(entry["id"])
                    rerun("Food entry deleted")

    with detail_tab:
        for group in ["General", "Carbohydrates", "Lipids", "Protein & Amino Acids", "Vitamins", "Minerals"]:
            keys = [key for key, (_, _, nutrient_group) in NUTRIENT_META.items() if nutrient_group == group]
            st.subheader(group)
            nutrient_progress(totals, goals, keys)

    with library_tab:
        with st.expander("Create a custom food"):
            with st.form("custom_food"):
                name = st.text_input("Food name")
                brand = st.text_input("Brand")
                barcode = st.text_input("Barcode")
                macro_cols = st.columns(5)
                macro_keys = ["calories", "protein", "carbs", "fat", "fibre"]
                values = {key: macro_cols[index].number_input(NUTRIENT_META[key][0] + " / 100g", min_value=0.0) for index, key in enumerate(macro_keys)}
                if st.form_submit_button("Save custom food"):
                    nutrients = {key: 0 for key in NUTRIENT_KEYS}
                    nutrients.update(values)
                    store.add_food({"id": uuid.uuid4().hex, **validate_food({"name": name, "brand": brand, "barcode": barcode, "nutrients": nutrients})})
                    rerun("Custom food added")
        st.dataframe(pd.DataFrame([{
            "name": item["name"], "brand": item.get("brand", ""),
            "calories": item["nutrients"].get("calories", 0),
            "protein": item["nutrients"].get("protein", 0),
            "carbs": item["nutrients"].get("carbs", 0),
            "fat": item["nutrients"].get("fat", 0),
        } for item in store.foods]), use_container_width=True, hide_index=True)

    with meals_tab:
        st.subheader("Saved meals")
        if store.foods:
            with st.form("save_meal"):
                meal_name = st.text_input("Meal name")
                meal_food = st.selectbox("Food", [item["id"] for item in store.foods], format_func=lambda value: store.get_food(value)["name"], key="meal_food")
                meal_amount = st.number_input("Amount (g)", min_value=1.0, value=100.0, key="meal_amount")
                servings = st.number_input("Servings", min_value=1, value=1)
                instructions = st.text_area("Instructions")
                if st.form_submit_button("Save meal"):
                    meal = {"id": uuid.uuid4().hex, **validate_meal({"name": meal_name, "items": [{"food_id": meal_food, "amount_g": meal_amount}], "servings": servings, "instructions": instructions}, store)}
                    store.add_item("meals", meal)
                    rerun("Meal saved")
        for meal in store.meals:
            cols = st.columns([3, 1, 1])
            cols[0].write(f"**{meal['name']}** · {meal['servings']} serving(s)")
            if cols[1].button("Log today", key=f"log_meal_{meal['id']}"):
                for item in meal["items"]:
                    store.add_food_entry({"id": uuid.uuid4().hex, "food_id": item["food_id"], "date": food_date.isoformat(), "amount_g": item["amount_g"] / meal["servings"]})
                rerun("Meal logged")
            if cols[2].button("Delete", key=f"delete_meal_{meal['id']}"):
                store.delete_item("meals", meal["id"])
                rerun("Meal deleted")
        st.subheader("Shopping list")
        with st.form("shopping"):
            shopping_name = st.text_input("Item")
            shopping_amount = st.text_input("Amount")
            if st.form_submit_button("Add shopping item"):
                store.add_item("shopping_items", {"id": uuid.uuid4().hex, **validate_shopping_item({"name": shopping_name, "amount": shopping_amount})})
                rerun("Shopping item added")
        for item in store.shopping_items:
            checked = st.checkbox(f"{item['name']} · {item.get('amount','')}", value=item.get("checked", False), key=f"shop_{item['id']}")
            if checked != item.get("checked", False):
                store.update_item("shopping_items", item["id"], {"checked": checked})


def body_page() -> None:
    st.title("Body and recovery")
    body_tab, recovery_tab = st.tabs(["Body progress", "Recovery"])
    with body_tab:
        with st.form("body_entry"):
            body_date = st.date_input("Date", date.today(), key="body_date")
            cols = st.columns(3)
            weight = cols[0].number_input("Weight", min_value=1.0, value=float(store.settings.get("profile", {}).get("body_weight", 70) or 70))
            body_fat = cols[1].number_input("Body fat %", min_value=0.0)
            waist = cols[2].number_input("Waist", min_value=0.0)
            cols2 = st.columns(3)
            chest = cols2[0].number_input("Chest", min_value=0.0)
            hips = cols2[1].number_input("Hips", min_value=0.0)
            arm = cols2[2].number_input("Arm", min_value=0.0)
            note = st.text_input("Note")
            if st.form_submit_button("Save measurement"):
                entry = {"id": uuid.uuid4().hex, **validate_body_entry({
                    "date": body_date.isoformat(), "weight": weight, "body_fat": body_fat,
                    "waist": waist, "chest": chest, "hips": hips, "arm": arm, "note": note,
                })}
                store.add_item("body_entries", entry)
                rerun("Body measurement saved")
        if store.body_entries:
            frame = pd.DataFrame(sorted(store.body_entries, key=lambda item: item["date"]))
            st.line_chart(frame.set_index("date")[[key for key in ("weight", "body_fat", "waist") if key in frame]])
            st.dataframe(frame.drop(columns=["id", "photo"], errors="ignore"), use_container_width=True, hide_index=True)

    with recovery_tab:
        with st.form("recovery_entry"):
            recovery_date = st.date_input("Date", date.today(), key="recovery_date")
            sleep = st.number_input("Sleep hours", min_value=0.0, max_value=24.0, value=8.0, step=.25)
            cols = st.columns(5)
            quality = cols[0].slider("Sleep quality", 1, 5, 3)
            energy = cols[1].slider("Energy", 1, 5, 3)
            soreness = cols[2].slider("Soreness", 1, 5, 3)
            stress = cols[3].slider("Stress", 1, 5, 3)
            mood = cols[4].slider("Mood", 1, 5, 3)
            note = st.text_input("Recovery note")
            if st.form_submit_button("Save recovery check-in"):
                entry = {"id": uuid.uuid4().hex, **validate_recovery_entry({
                    "date": recovery_date.isoformat(), "sleep_hours": sleep,
                    "sleep_quality": quality, "energy": energy, "soreness": soreness,
                    "stress": stress, "mood": mood, "note": note,
                })}
                store.add_item("recovery_entries", entry)
                rerun("Recovery check-in saved")
        if store.recovery_entries:
            rows = sorted(store.recovery_entries, key=lambda item: item["date"])
            frame = pd.DataFrame([{"date": item["date"], "sleep": item["sleep_hours"], "energy": item["energy"], "readiness": readiness(item)} for item in rows])
            chart_cols = st.columns(3)
            chart_cols[0].line_chart(frame.set_index("date")[["sleep"]])
            chart_cols[1].line_chart(frame.set_index("date")[["energy"]])
            chart_cols[2].line_chart(frame.set_index("date")[["readiness"]])


def planner_page() -> None:
    st.title("Planner and timetable")
    once_tab, recurring_tab = st.tabs(["Calendar items", "Weekly timetable"])
    with once_tab:
        with st.form("planner_event"):
            title = st.text_input("Activity")
            event_date = st.date_input("Date", date.today(), key="event_date")
            cols = st.columns(3)
            event_type = cols[0].selectbox("Type", ["workout", "meal", "habit", "note"])
            start = cols[1].time_input("Start", datetime.strptime("09:00", "%H:%M").time())
            end = cols[2].time_input("End", datetime.strptime("10:00", "%H:%M").time())
            note = st.text_input("Note")
            if st.form_submit_button("Add calendar item"):
                item = {"id": uuid.uuid4().hex, **validate_planner_event({
                    "title": title, "date": event_date.isoformat(), "type": event_type,
                    "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "note": note,
                })}
                store.add_item("planner_events", item)
                rerun("Calendar item added")
        events = sorted(store.planner_events, key=lambda item: (item["date"], item.get("start", "")))
        for item in events:
            cols = st.columns([.5, 3, 1, .6])
            done = cols[0].checkbox("", value=item.get("done", False), key=f"event_done_{item['id']}")
            if done != item.get("done", False):
                store.update_item("planner_events", item["id"], {"done": done})
            cols[1].write(f"**{item['title']}** · {item['date']} · {item.get('start','')}-{item.get('end','')}")
            cols[2].write(item["type"])
            if cols[3].button("Delete", key=f"delete_event_{item['id']}"):
                store.delete_item("planner_events", item["id"])
                rerun("Calendar item deleted")
        st.caption("Planner completion does not award XP.")

    with recurring_tab:
        with st.form("schedule_item"):
            schedule_title = st.text_input("Repeating activity")
            cols = st.columns(4)
            weekday = cols[0].selectbox("Every", range(7), format_func=lambda value: WEEKDAYS[value])
            schedule_type = cols[1].selectbox("Type", ["workout", "meal", "habit", "note"])
            schedule_start = cols[2].time_input("Start", datetime.strptime("09:00", "%H:%M").time(), key="schedule_start")
            schedule_end = cols[3].time_input("End", datetime.strptime("10:00", "%H:%M").time(), key="schedule_end")
            colour = st.color_picker("Colour", DEFAULT_COLORS[0], key="schedule_colour")
            if st.form_submit_button("Add repeating activity"):
                item = {"id": uuid.uuid4().hex, **validate_weekly_schedule_item({
                    "title": schedule_title, "weekday": weekday, "type": schedule_type,
                    "start": schedule_start.strftime("%H:%M"), "end": schedule_end.strftime("%H:%M"), "color": colour,
                })}
                store.add_item("weekly_schedule", item)
                rerun("Repeating activity added")
        columns = st.columns(7)
        for day_index, column in enumerate(columns):
            column.markdown(f"**{WEEKDAYS[day_index][:3]}**")
            for item in sorted([row for row in store.weekly_schedule if row["weekday"] == day_index], key=lambda row: row.get("start", "")):
                column.markdown(
                    f"<div class='card' style='border-left:5px solid {item.get('color', DEFAULT_COLORS[0])};padding:10px'>"
                    f"<strong>{html.escape(item['title'])}</strong><br><span class='muted'>{item.get('start') or 'All day'}"
                    f"{' - ' + item.get('end') if item.get('end') else ''}</span></div>",
                    unsafe_allow_html=True,
                )
                if column.button("×", key=f"delete_schedule_{item['id']}"):
                    store.delete_item("weekly_schedule", item["id"])
                    rerun("Repeating activity deleted")


def journal_page() -> None:
    st.title("Journal and goals")
    journal_tab, goals_tab = st.tabs(["Journal", "Goals"])
    with journal_tab:
        with st.form("journal"):
            journal_date = st.date_input("Date", date.today(), key="journal_date")
            title = st.text_input("Title", "Daily reflection")
            mood = st.slider("Mood", 1, 5, 3)
            content = st.text_area("What happened today?")
            win = st.text_input("Today's win")
            gratitude = st.text_input("Grateful for")
            if st.form_submit_button("Save journal entry"):
                entry = {"id": uuid.uuid4().hex, **validate_journal_entry({
                    "date": journal_date.isoformat(), "title": title, "mood": mood,
                    "content": content, "win": win, "gratitude": gratitude,
                })}
                store.add_item("journal_entries", entry)
                change = store.set_xp_award(f"journal:{entry['id']}", store.settings["xp_rewards"]["journal"])
                rerun(f"Journal saved · +{change} XP")
        for entry in sorted(store.journal_entries, key=lambda item: item["date"], reverse=True):
            with st.expander(f"{entry['date']} · {entry['title']} · Mood {entry['mood']}/5"):
                st.write(entry["content"])
                if entry.get("win"):
                    st.success(f"Win: {entry['win']}")
                if entry.get("gratitude"):
                    st.info(f"Grateful for: {entry['gratitude']}")
                if st.button("Delete entry", key=f"delete_journal_{entry['id']}"):
                    store.set_xp_award(f"journal:{entry['id']}", 0, False)
                    store.delete_item("journal_entries", entry["id"])
                    rerun("Journal entry deleted")

    with goals_tab:
        with st.form("goal"):
            goal_title = st.text_input("Goal")
            category = st.selectbox("Category", ["body", "strength", "running", "nutrition", "habit", "personal"])
            cols = st.columns(3)
            current = cols[0].number_input("Current", min_value=0.0)
            target = cols[1].number_input("Target", min_value=0.0)
            unit = cols[2].text_input("Unit")
            deadline = st.date_input("Deadline", date.today() + timedelta(days=90))
            notes = st.text_area("Notes")
            if st.form_submit_button("Add goal"):
                goal = {"id": uuid.uuid4().hex, **validate_goal({
                    "title": goal_title, "category": category, "current_value": current,
                    "target_value": target, "unit": unit, "deadline": deadline.isoformat(),
                    "completed": False, "notes": notes,
                })}
                store.add_item("goals", goal)
                rerun("Goal added")
        for goal in store.goals:
            with st.container(border=True):
                cols = st.columns([3, 1, 1])
                cols[0].write(f"**{goal['title']}** · {goal['current_value']:g}/{goal['target_value']:g} {goal.get('unit','')}")
                completed = cols[1].checkbox("Complete", value=goal.get("completed", False), key=f"goal_complete_{goal['id']}")
                if completed != goal.get("completed", False):
                    store.update_item("goals", goal["id"], {"completed": completed})
                    change = store.set_xp_award(f"goal:{goal['id']}", store.settings["xp_rewards"]["goal"], completed)
                    rerun(f"Goal updated · {change:+d} XP" if change else "Goal updated")
                if cols[2].button("Delete", key=f"delete_goal_{goal['id']}"):
                    store.set_xp_award(f"goal:{goal['id']}", 0, False)
                    store.delete_item("goals", goal["id"])
                    rerun("Goal deleted")


def kickboxing_page() -> None:
    st.title("Kickboxing syllabus and audio coach")
    grade_name = st.selectbox("Grade", [item[0] for item in KICKBOXING])
    grade = next(item for item in KICKBOXING if item[0] == grade_name)
    st.markdown(f"**Focus:** {grade[1]}")
    combo = st.selectbox("Combination", grade[2])
    repeats = st.number_input("Repetitions", min_value=1, max_value=100, value=5)
    rate = kickboxing_grade_xp(grade_name)
    st.info(f"{rate} XP per completed repetition · {rate * repeats} XP if the complete audio drill is finished.")

    safe_combo = json.dumps(combo.replace(">", ","))
    audio_html = f"""
    <div style="font-family:system-ui;padding:12px;border:1px solid #dfe4ee;border-radius:14px">
      <button onclick="startDrill()" style="padding:10px 18px;border:0;border-radius:10px;background:#5b6cff;color:white;font-weight:700">Start audio</button>
      <button onclick="speechSynthesis.cancel()" style="padding:10px 18px;border:1px solid #ccd3df;border-radius:10px;background:white;font-weight:700">Stop</button>
      <p id="status">Ready</p>
    </div>
    <script>
    function speak(text) {{
      return new Promise(resolve => {{
        const voice = new SpeechSynthesisUtterance(text);
        voice.rate = 0.82;
        voice.pitch = 0.95;
        voice.onend = resolve;
        voice.onerror = resolve;
        speechSynthesis.speak(voice);
      }});
    }}
    async function startDrill() {{
      speechSynthesis.cancel();
      document.getElementById("status").textContent = "Running";
      for (let i=1; i<={int(repeats)}; i++) {{
        await speak({safe_combo});
        if (!speechSynthesis.speaking && i < {int(repeats)}) await new Promise(r => setTimeout(r, 700));
        document.getElementById("status").textContent = `Repetition ${{i}} of {int(repeats)}`;
      }}
      document.getElementById("status").textContent = "Complete. Confirm below to save XP.";
    }}
    </script>
    """
    components.html(audio_html, height=115)
    st.caption("Only confirm completion after the audio reaches the end. Stopped or interrupted drills should not be saved.")
    if st.button("Confirm completed drill", type="primary"):
        session = {"id": uuid.uuid4().hex, **validate_kickboxing_session({
            "date": date.today().isoformat(), "score": 0, "attempts": repeats,
            "hits": repeats, "belt": grade_name, "mode": "audio-drill", "combo": combo,
        })}
        session["xp_awarded"] = rate * int(repeats)
        store.add_item("kickboxing_sessions", session)
        change = store.set_xp_award(f"kickboxing:{session['id']}", session["xp_awarded"])
        rerun(f"Kickboxing drill complete · +{change} XP")
    if store.kickboxing_sessions:
        st.subheader("Practice history")
        st.dataframe(pd.DataFrame(sorted(store.kickboxing_sessions, key=lambda item: item["date"], reverse=True)), use_container_width=True, hide_index=True)


def settings_page() -> None:
    st.title("Profile, XP and data")
    profile_tab, xp_tab, nutrition_tab, data_tab = st.tabs(["Profile", "XP values", "Nutrition targets", "Backup"])
    profile = store.settings.get("profile", {})
    with profile_tab:
        with st.form("profile"):
            display_name = st.text_input("Name", profile.get("display_name", ""))
            cols = st.columns(4)
            age = cols[0].number_input("Age", min_value=0, max_value=100, value=int(profile.get("age", 0)))
            sex = cols[1].selectbox("Sex", ["male", "female"], index=1 if profile.get("sex") == "female" else 0)
            height = cols[2].number_input("Height (cm)", min_value=0.0, value=float(profile.get("height_cm", 0)))
            weight = cols[3].number_input("Bodyweight", min_value=0.0, value=float(profile.get("body_weight", 0)))
            cols2 = st.columns(4)
            weight_unit = cols2[0].selectbox("Weight unit", ["kg", "lb"], index=1 if profile.get("weight_unit") == "lb" else 0)
            activity = cols2[1].selectbox("Activity", ["inactive", "low", "active", "very"], index=["inactive", "low", "active", "very"].index(profile.get("activity_level", "active")))
            goal = cols2[2].selectbox("Goal", ["lose", "maintain", "recomposition", "gain", "performance"], index=["lose", "maintain", "recomposition", "gain", "performance"].index(profile.get("goal_type", "recomposition")))
            experience = cols2[3].selectbox("Training experience", ["beginner", "intermediate", "advanced"], index=["beginner", "intermediate", "advanced"].index(profile.get("training_experience", "beginner")))
            auto_nutrition = st.checkbox("Calculate nutrition targets from profile", value=profile.get("auto_nutrition", True))
            api_key = st.text_input("Optional USDA API key", store.settings.get("usda_api_key", "DEMO_KEY"))
            if st.form_submit_button("Save profile"):
                store.update_settings({"profile": {
                    "display_name": display_name.strip(), "age": int(age), "sex": sex,
                    "height_cm": height, "body_weight": weight, "weight_unit": weight_unit,
                    "activity_level": activity, "goal_type": goal,
                    "training_experience": experience, "auto_nutrition": auto_nutrition,
                }, "usda_api_key": api_key})
                rerun("Profile saved")
        energy = profile_energy()
        if energy:
            c1, c2 = st.columns(2)
            c1.metric("Estimated RMR", f"{energy[0]:.0f} kcal")
            c2.metric("Estimated daily target", f"{energy[1]:.0f} kcal")
            st.caption("Mifflin-St Jeor estimate. It is guidance, not medical advice.")

    with xp_tab:
        rewards = store.settings.get("xp_rewards", DEFAULT_XP_REWARDS)
        with st.form("xp_settings"):
            labels = {
                "habit": "Habit target met", "workout_first": "First exercise session",
                "workout_improvement": "Weight, sets or reps improved",
                "workout_standard": "Workout without improvement",
                "journal": "Journal entry", "goal": "Completed personal goal",
            }
            values = {}
            columns = st.columns(2)
            for index, key in enumerate(DEFAULT_XP_REWARDS):
                values[key] = columns[index % 2].number_input(labels[key], min_value=0, max_value=10000, value=int(rewards.get(key, DEFAULT_XP_REWARDS[key])), key=f"xp_{key}")
            if st.form_submit_button("Save XP values"):
                store.update_settings({"xp_rewards": values})
                rerun("XP values updated")
        st.caption("A workout receives one category: first session, improvement, or standard. Planner and food do not award XP.")
        if st.button("Reset level to F with 0 XP"):
            store.reset_xp()
            rerun("XP reset")

    with nutrition_tab:
        with st.form("nutrition_goals"):
            edited = {}
            for group in ["General", "Carbohydrates", "Lipids", "Protein & Amino Acids", "Vitamins", "Minerals"]:
                st.markdown(f"**{group}**")
                keys = [key for key, (_, _, nutrient_group) in NUTRIENT_META.items() if nutrient_group == group]
                cols = st.columns(3)
                for index, key in enumerate(keys):
                    label, unit, _ = NUTRIENT_META[key]
                    edited[key] = cols[index % 3].number_input(f"{label} ({unit})", min_value=0.0, value=float(store.nutrition_goals.get(key, DEFAULT_NUTRITION_GOALS[key])), key=f"goal_{key}")
            for key in NUTRIENT_KEYS:
                edited.setdefault(key, float(store.nutrition_goals.get(key, DEFAULT_NUTRITION_GOALS[key])))
            if st.form_submit_button("Save nutrient targets"):
                store.update_nutrition_goals(validate_nutrition_goals(edited))
                rerun("Nutrition targets saved")

    with data_tab:
        backup = json.dumps(store.all_data(), indent=2)
        st.download_button("Download complete backup", backup, file_name="habitline-streamlit-backup.json", mime="application/json")
        upload = st.file_uploader("Restore a Habitline backup", type=["json"])
        if upload and st.button("Import backup"):
            store.import_data(json.load(upload))
            rerun("Backup imported")
        st.caption(f"Streamlit data file: {DATA_FILE}")


PAGES = {
    "Home": home_page,
    "Habits": habits_page,
    "Lifting": lifting_page,
    "Food": food_page,
    "Body": body_page,
    "Planner": planner_page,
    "Journal": journal_page,
    "Kickboxing": kickboxing_page,
    "Settings": settings_page,
}

with st.sidebar:
    st.image(str(ROOT / "icon-192.png"), width=64)
    st.markdown("## Habitline")
    st.caption("Streamlit edition")
    page = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
    game = level_stats()
    st.markdown(f"<span class='rank'>Level {game['rank']}</span>", unsafe_allow_html=True)
    st.write(f"**{game['xp']} XP**")
    st.progress(game["progress"] / 100)
    dark_mode = st.toggle("Dark display", value=st.session_state.get("dark_mode", False))
    st.session_state["dark_mode"] = dark_mode
    if st.button("Reload saved data", use_container_width=True):
        reload_store()
        rerun("Data reloaded")

show_flash()
if st.session_state.get("dark_mode"):
    st.markdown(
        """
        <style>
        .stApp { background:#0f131a !important; color:#f2f4f8 !important; }
        div[data-testid="stMetric"], .card { background:#181e28 !important; border-color:#2a3442 !important; }
        [data-testid="stHeader"] { background:#0f131a !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
PAGES[page]()
