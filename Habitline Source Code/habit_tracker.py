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
