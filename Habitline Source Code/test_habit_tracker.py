import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from habit_tracker import (
    DEFAULT_FOODS,
    DEFAULT_NUTRITION_GOALS,
    DEFAULT_WEEKLY_SCHEDULE,
    DEFAULT_XP_REWARDS,
    HabitStore,
    habit_stats,
    kickboxing_grade_xp,
    open_food_facts_product,
    parse_number,
    search_offline_foods,
    scaled_nutrients,
    usda_food_product,
    validate_food_entry,
    validate_body_entry,
    validate_meal,
    validate_nutrition_goals,
    validate_goal,
    validate_journal_entry,
    validate_kickboxing_session,
    validate_planner_event,
    validate_recovery_entry,
    validate_weekly_schedule_item,
    validate_workout,
    validate_workout_day,
    validate_workout_day_log,
)


class NumberParsingTests(unittest.TestCase):
    def test_parses_compact_values_and_units(self):
        self.assertEqual(parse_number("20k"), 20_000)
        self.assertEqual(parse_number("12.5k steps"), 12_500)
        self.assertEqual(parse_number("1,250"), 1_250)

    def test_rejects_invalid_and_negative_values(self):
        with self.assertRaises(ValueError):
            parse_number("lots")
        with self.assertRaises(ValueError):
            parse_number("-3")


class AnalyticsTests(unittest.TestCase):
    def test_numeric_average_counts_missing_days_as_zero(self):
        habit = {
            "type": "number",
            "target": 20_000,
            "entries": {
                "2026-06-01": 20_000,
                "2026-06-02": 10_000,
                "2026-06-03": 30_000,
            },
        }
        stats = habit_stats(habit, date(2026, 6, 4), "week")
        self.assertEqual(stats["average"], 15_000)
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["goal_rate"], 50)

    def test_checkbox_completion_rate(self):
        habit = {
            "type": "check",
            "target": 1,
            "entries": {
                "2026-06-01": True,
                "2026-06-02": False,
                "2026-06-03": True,
            },
        }
        stats = habit_stats(habit, date(2026, 6, 4), "week")
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["average"], 50)


class StorageTests(unittest.TestCase):
    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "habits.json"
            store = HabitStore(path)
            store.habits[0]["entries"]["2026-06-05"] = 21_000
            store.save()
            loaded = HabitStore(path)
            self.assertEqual(loaded.habits[0]["entries"]["2026-06-05"], 21_000)

    def test_exercise_and_workout_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            exercise = {
                "id": "exercise1",
                "name": "Bench press",
                "unit": "kg",
                "color": "#5B6CFF",
            }
            store.add_exercise(exercise)
            workout = {
                "id": "workout1",
                "exercise_id": "exercise1",
                "date": "2026-06-05",
                "weight": 80,
                "sets": 3,
                "reps": 8,
                "notes": "Solid",
            }
            store.add_workout(workout)
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.exercises[0]["name"], "Bench press")
            self.assertEqual(loaded.workouts[0]["reps"], 8)

    def test_workout_day_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.add_exercise(
                {"id": "ex1", "name": "Bench", "unit": "kg", "color": "#5B6CFF"}
            )
            store.add_workout_day(
                {"id": "day1", "name": "Push", "exercise_ids": ["ex1"]}
            )
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.workout_days[0]["name"], "Push")

    def test_deleting_exercise_deletes_its_workouts(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.add_exercise(
                {"id": "ex1", "name": "Squat", "unit": "kg", "color": "#5B6CFF"}
            )
            store.add_workout(
                {
                    "id": "wo1",
                    "exercise_id": "ex1",
                    "date": "2026-06-05",
                    "weight": 100,
                    "sets": 3,
                    "reps": 5,
                    "notes": "",
                }
            )
            self.assertTrue(store.delete_exercise("ex1"))
            self.assertEqual(store.workouts, [])

    def test_existing_file_is_migrated_with_food_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "habits.json"
            path.write_text('{"habits": [], "exercises": [], "workouts": []}')
            store = HabitStore(path)
            self.assertGreater(len(store.foods), 0)
            self.assertEqual(store.food_entries, [])
            self.assertEqual(store.nutrition_goals["calories"], 2000)

    def test_food_entry_round_trip_and_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            food = {
                "id": "customfood",
                "name": "Test food",
                "serving_name": "100 g",
                "nutrients": {"calories": 100},
            }
            store.add_food(food)
            store.add_food_entry(
                {
                    "id": "entry1",
                    "food_id": "customfood",
                    "date": "2026-06-05",
                    "amount_g": 250,
                }
            )
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.food_entries[0]["amount_g"], 250)
            self.assertTrue(loaded.delete_food("customfood"))
            self.assertEqual(loaded.food_entries, [])

    def test_new_collections_round_trip_restore_and_import(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            body = {
                "id": "body1",
                "date": "2026-06-05",
                "weight": 80,
                "body_fat": 15,
                "waist": 82,
                "chest": 100,
                "hips": 95,
                "arm": 36,
                "note": "",
                "photo": "",
            }
            store.add_item("body_entries", body)
            self.assertTrue(store.delete_item("body_entries", "body1"))
            self.assertEqual(store.body_entries, [])
            restored = store.restore_item(store.trash[-1]["id"])
            self.assertEqual(restored["weight"], 80)
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.body_entries[0]["id"], "body1")
            backup = loaded.all_data()
            imported = HabitStore(Path(folder) / "imported.json")
            imported.import_data(backup)
            self.assertEqual(imported.body_entries[0]["weight"], 80)

    def test_profile_and_weekly_schedule_are_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.update_settings(
                {
                    "profile": {
                        "age": 30,
                        "body_weight": 82,
                        "weight_unit": "kg",
                    }
                }
            )
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.settings["profile"]["age"], 30)
            self.assertEqual(loaded.settings["profile"]["body_weight"], 82)
            self.assertEqual(
                len(loaded.weekly_schedule), len(DEFAULT_WEEKLY_SCHEDULE)
            )

    def test_xp_rewards_and_reset_baseline_are_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            rewards = {**DEFAULT_XP_REWARDS, "habit": 30, "goal": 250}
            store.update_settings(
                {
                    "xp_rewards": rewards,
                    "xp_offset": 875,
                    "profile": {"xp_rewards": rewards, "xp_offset": 875},
                }
            )
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.settings["xp_rewards"]["habit"], 30)
            self.assertEqual(loaded.settings["xp_rewards"]["goal"], 250)
            self.assertEqual(loaded.settings["xp_offset"], 875)
            self.assertEqual(loaded.settings["profile"]["xp_offset"], 875)

    def test_xp_rewards_reject_negative_values(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            with self.assertRaises(ValueError):
                store.update_settings({"xp_rewards": {"habit": -1}})

    def test_xp_balance_awards_once_and_reset_stays_responsive(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            self.assertEqual(store.set_xp_award("habit:new:2026-06-06", 5), 5)
            self.assertEqual(store.settings["xp_balance"], 5)
            self.assertEqual(store.set_xp_award("habit:new:2026-06-06", 5), 0)
            store.update_settings({"reset_xp": True})
            self.assertEqual(store.settings["xp_balance"], 0)
            self.assertEqual(store.settings["xp_awards"], {})
            self.assertEqual(store.set_xp_award("habit:new:2026-06-06", 5), 5)
            self.assertEqual(store.settings["xp_balance"], 5)
            self.assertEqual(store.set_xp_award("habit:next:2026-06-07", 5), 5)
            self.assertEqual(store.settings["xp_balance"], 10)

    def test_zero_value_legacy_marker_does_not_block_future_award(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.settings["xp_awards"] = {
                "habit:old:2026-06-06": {"amount": 0, "active": True}
            }
            store.save()
            self.assertEqual(
                store.set_xp_award("habit:old:2026-06-06", 5, True),
                5,
            )
            self.assertEqual(store.settings["xp_balance"], 5)

    def test_zero_value_reset_markers_are_removed_when_store_reloads(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.settings["xp_balance"] = 0
            store.settings["xp_awards"] = {
                "habit:old:2026-06-06": {"amount": 0, "active": True},
                "workout:old": {"amount": 0, "active": False},
            }
            store.save()
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.settings["xp_awards"], {})

    def test_workout_improvement_uses_save_order_for_same_day(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.exercises = [{"id": "exercise", "name": "Press"}]
            first = {
                "id": "ffff",
                "exercise_id": "exercise",
                "date": "2026-06-06",
                "weight": 40,
                "sets": 3,
                "reps": 8,
            }
            improved = {
                "id": "aaaa",
                "exercise_id": "exercise",
                "date": "2026-06-06",
                "weight": 45,
                "sets": 3,
                "reps": 8,
            }
            store.workouts = [first, improved]
            self.assertEqual(store._workout_reward_key(first), "workout_first")
            self.assertEqual(
                store._workout_reward_key(improved),
                "workout_improvement",
            )

    def test_habit_and_workout_xp_workflow_uses_configured_values(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.settings["xp_rewards"].update(
                {"habit": 5, "workout_first": 5, "workout_improvement": 20}
            )
            habit = {
                "id": "habit1",
                "name": "Read",
                "type": "check",
                "target": 1,
                "unit": "",
                "color": "#5B6CFF",
                "entries": {},
            }
            exercise = {
                "id": "exercise1",
                "name": "Chest press",
                "unit": "kg",
                "color": "#5B6CFF",
            }
            store.habits = [habit]
            store.exercises = [exercise]
            store.set_entry(habit["id"], "2026-06-06", True)
            habit_change = store.set_xp_award(
                "habit:habit1:2026-06-06",
                store.settings["xp_rewards"]["habit"],
                True,
            )
            self.assertEqual(habit_change, 5)

            first = {
                "id": "workout1",
                "exercise_id": exercise["id"],
                "date": "2026-06-06",
                "weight": 40,
                "sets": 3,
                "reps": 8,
                "notes": "",
            }
            store.add_workout(first)
            first_key = store._workout_reward_key(first)
            first_change = store.set_xp_award(
                f"workout:{first['id']}",
                store.settings["xp_rewards"][first_key],
            )
            self.assertEqual(first_key, "workout_first")
            self.assertEqual(first_change, 5)

            improved = {
                "id": "workout2",
                "exercise_id": exercise["id"],
                "date": "2026-06-06",
                "weight": 40,
                "sets": 4,
                "reps": 8,
                "notes": "",
            }
            store.add_workout(improved)
            improved_key = store._workout_reward_key(improved)
            improved_change = store.set_xp_award(
                f"workout:{improved['id']}",
                store.settings["xp_rewards"][improved_key],
            )
            self.assertEqual(improved_key, "workout_improvement")
            self.assertEqual(improved_change, 20)
            self.assertEqual(store.settings["xp_balance"], 30)

    def test_kickboxing_grade_xp_per_repetition(self):
        expected = {
            "9th Kyu Red": 1,
            "8th Kyu Yellow": 2,
            "7th Kyu Orange": 3,
            "6th Kyu Green": 3,
            "5th Kyu Blue": 4,
            "4th Kyu Purple": 5,
        }
        for grade, value in expected.items():
            self.assertEqual(kickboxing_grade_xp(grade), value)

    def test_planner_has_no_xp_reward_and_default_schedule_has_no_steps(self):
        self.assertNotIn("planner", DEFAULT_XP_REWARDS)
        self.assertFalse(
            any("step" in item["title"].lower() for item in DEFAULT_WEEKLY_SCHEDULE)
        )

    def test_old_step_schedule_items_are_removed_on_load(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            payload["weekly_schedule"].append(
                {
                    "id": "schedule_steps_0",
                    "weekday": 0,
                    "title": "20k steps",
                    "start": "",
                    "end": "",
                    "type": "habit",
                    "color": "#5B6CFF",
                }
            )
            store.path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = HabitStore(store.path)
            self.assertFalse(
                any("step" in item["title"].lower() for item in loaded.weekly_schedule)
            )

    def test_legacy_xp_settings_are_cleaned_and_offset_is_migrated(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            payload["settings"]["xp_rewards"] = {
                "kickboxing_round": 37,
                "kickboxing_score_bonus": 9,
            }
            payload["settings"].pop("xp_offset", None)
            payload["settings"]["profile"]["xp_offset"] = 145
            store.path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = HabitStore(store.path)
            self.assertNotIn("kickboxing", loaded.settings["xp_rewards"])
            self.assertNotIn("kickboxing_score_bonus", loaded.settings["xp_rewards"])
            self.assertEqual(loaded.settings["xp_offset"], 145)

    def test_offline_food_search_finds_common_foods_and_aliases(self):
        chicken = search_offline_foods(DEFAULT_FOODS, "chicken breast")
        self.assertTrue(chicken)
        self.assertIn("chicken breast", chicken[0]["name"].lower())
        porridge = search_offline_foods(DEFAULT_FOODS, "porridge")
        self.assertTrue(porridge)
        self.assertIn("oats", porridge[0]["name"].lower())
        mince = search_offline_foods(DEFAULT_FOODS, "ground beef")
        self.assertTrue(mince)
        self.assertIn("mince", mince[0]["name"].lower())

    def test_existing_store_receives_new_bundled_foods(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            payload["foods"] = [
                food for food in payload["foods"] if food["id"] == "food_chicken_breast_cooked"
            ]
            store.path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = HabitStore(store.path)
            ids = {food["id"] for food in loaded.foods}
            self.assertIn("food_oats_dry", ids)
            self.assertIn("food_lentils_cooked", ids)
            self.assertGreaterEqual(len(loaded.foods), 25)

    def test_weekly_schedule_can_be_added_edited_deleted_and_restored(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            item = {
                "id": "repeat1",
                **validate_weekly_schedule_item(
                    {
                        "title": "Weightlifting",
                        "weekday": 3,
                        "start": "20:30",
                        "end": "21:30",
                        "type": "workout",
                        "color": "#8f18b5",
                    }
                ),
            }
            store.add_item("weekly_schedule", item)
            store.update_item(
                "weekly_schedule",
                "repeat1",
                validate_weekly_schedule_item({**item, "title": "Push workout"}),
            )
            self.assertEqual(
                next(row for row in store.weekly_schedule if row["id"] == "repeat1")[
                    "title"
                ],
                "Push workout",
            )
            self.assertTrue(store.delete_item("weekly_schedule", "repeat1"))
            restored = store.restore_item(store.trash[-1]["id"])
            self.assertEqual(restored["weekday"], 3)

    def test_weekly_schedule_rejects_end_before_start(self):
        with self.assertRaises(ValueError):
            validate_weekly_schedule_item(
                {
                    "title": "Bad time",
                    "weekday": 3,
                    "start": "21:30",
                    "end": "20:30",
                    "type": "workout",
                }
            )


class WorkoutValidationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = HabitStore(Path(self.folder.name) / "habits.json")
        self.store.add_exercise(
            {"id": "ex1", "name": "Deadlift", "unit": "kg", "color": "#5B6CFF"}
        )

    def tearDown(self):
        self.folder.cleanup()

    def test_validates_workout_numbers(self):
        result = validate_workout(
            {
                "exercise_id": "ex1",
                "date": "2026-06-05",
                "weight": "120.5",
                "sets": 3,
                "reps": 5,
            },
            self.store,
        )
        self.assertEqual(result["weight"], 120.5)
        self.assertEqual(result["sets"], 3)

    def test_rejects_zero_sets(self):
        with self.assertRaises(ValueError):
            validate_workout(
                {
                    "exercise_id": "ex1",
                    "date": "2026-06-05",
                    "weight": 100,
                    "sets": 0,
                    "reps": 5,
                },
                self.store,
            )

    def test_validates_workout_day_and_bulk_log(self):
        day = validate_workout_day(
            {"name": "Push", "exercise_ids": ["ex1", "missing", "ex1"]},
            self.store,
        )
        self.assertEqual(day["exercise_ids"], ["ex1"])
        self.store.add_workout_day({"id": "day1", **day})
        day_id, rows = validate_workout_day_log(
            {
                "workout_day_id": "day1",
                "date": "2026-06-05",
                "exercises": [
                    {
                        "exercise_id": "ex1",
                        "weight": 100,
                        "sets": 3,
                        "reps": 5,
                    }
                ],
            },
            self.store,
        )
        self.assertEqual(day_id, "day1")
        self.assertEqual(rows[0]["weight"], 100)


class WellnessValidationTests(unittest.TestCase):
    def test_body_and_recovery_validation(self):
        body = validate_body_entry(
            {"date": "2026-06-05", "weight": "80.5", "body_fat": 15}
        )
        recovery = validate_recovery_entry(
            {
                "date": "2026-06-05",
                "sleep_hours": 8,
                "sleep_quality": 4,
                "energy": 4,
                "soreness": 2,
                "stress": 2,
                "mood": 5,
            }
        )
        self.assertEqual(body["weight"], 80.5)
        self.assertEqual(recovery["mood"], 5)

    def test_meal_and_planner_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            meal = validate_meal(
                {
                    "name": "Steak meal",
                    "servings": 2,
                    "items": [
                        {
                            "food_id": "food_beef_steak_cooked",
                            "amount_g": 500,
                        }
                    ],
                },
                store,
            )
            event = validate_planner_event(
                {
                    "date": "2026-06-05",
                    "type": "meal",
                    "title": "Steak meal",
                    "reminder": "18:30",
                }
            )
            self.assertEqual(meal["servings"], 2)
            self.assertEqual(event["reminder"], "18:30")

    def test_journal_goal_and_kickboxing_validation(self):
        journal = validate_journal_entry(
            {
                "date": "2026-06-05",
                "title": "Good day",
                "content": "Training went well.",
                "mood": 4,
            }
        )
        goal = validate_goal(
            {
                "title": "Run 5K",
                "category": "running",
                "current_value": 2,
                "target_value": 5,
                "unit": "km",
            }
        )
        round_result = validate_kickboxing_session(
            {
                "date": "2026-06-05",
                "score": 1200,
                "attempts": 24,
                "hits": 20,
                "belt": "Orange",
            }
        )
        self.assertEqual(journal["mood"], 4)
        self.assertEqual(goal["target_value"], 5)
        self.assertEqual(round_result["accuracy"], 83.3)

    def test_new_tracking_collections_are_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            store.add_item(
                "journal_entries",
                {
                    "id": "journal1",
                    **validate_journal_entry(
                        {
                            "date": "2026-06-05",
                            "content": "Reflection",
                            "mood": 3,
                        }
                    ),
                },
            )
            store.add_item(
                "goals",
                {
                    "id": "goal1",
                    **validate_goal(
                        {
                            "title": "Reach 100 kg",
                            "target_value": 100,
                            "current_value": 90,
                        }
                    ),
                },
            )
            loaded = HabitStore(store.path)
            self.assertEqual(loaded.journal_entries[0]["content"], "Reflection")
            self.assertEqual(loaded.goals[0]["target_value"], 100)


class NutritionTests(unittest.TestCase):
    def test_250g_steak_scales_per_100g_nutrients(self):
        steak = next(food for food in DEFAULT_FOODS if "steak" in food["name"].lower())
        nutrients = scaled_nutrients(steak, 250)
        self.assertEqual(nutrients["calories"], 677.5)
        self.assertEqual(nutrients["protein"], 65)
        self.assertEqual(nutrients["iron"], 6.25)

    def test_validates_food_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            store = HabitStore(Path(folder) / "habits.json")
            result = validate_food_entry(
                {
                    "food_id": "food_beef_steak_cooked",
                    "date": "2026-06-05",
                    "amount_g": "250g",
                },
                store,
            )
            self.assertEqual(result["amount_g"], 250)

    def test_zero_nutrition_goal_means_no_target(self):
        goals = dict(DEFAULT_NUTRITION_GOALS)
        goals["protein"] = 0
        result = validate_nutrition_goals(goals)
        self.assertEqual(result["protein"], 0)

    def test_detailed_steak_nutrients_are_available(self):
        steak = next(food for food in DEFAULT_FOODS if "steak" in food["name"].lower())
        nutrients = scaled_nutrients(steak, 250)
        self.assertGreater(nutrients["leucine"], 5)
        self.assertGreater(nutrients["vitamin_b3"], 10)
        self.assertGreater(nutrients["selenium"], 60)

    def test_open_food_facts_product_maps_units(self):
        product = open_food_facts_product(
            {
                "code": "1234567890123",
                "product_name": "Test product",
                "brands": "Test brand",
                "nutriments": {
                    "energy-kcal_100g": 200,
                    "proteins_100g": 10,
                    "sodium_100g": 0.4,
                    "vitamin-c_100g": 0.03,
                    "vitamin-b12_100g": 0.000002,
                },
            }
        )
        self.assertEqual(product["nutrients"]["calories"], 200)
        self.assertEqual(product["nutrients"]["sodium"], 400)
        self.assertEqual(product["nutrients"]["vitamin_c"], 30)
        self.assertEqual(product["nutrients"]["vitamin_b12"], 2)
        self.assertEqual(product["barcode"], "1234567890123")

    def test_usda_product_maps_detailed_nutrients(self):
        product = usda_food_product(
            {
                "fdcId": 123,
                "description": "Chicken breast",
                "dataType": "Foundation",
                "foodNutrients": [
                    {
                        "nutrientName": "Energy (Atwater Specific Factors)",
                        "unitName": "KCAL",
                        "value": 165,
                    },
                    {"nutrientName": "Protein", "unitName": "G", "value": 31},
                    {"nutrientName": "Sodium, Na", "unitName": "MG", "value": 74},
                    {
                        "nutrientName": "Vitamin B-12",
                        "unitName": "UG",
                        "value": 0.3,
                    },
                ],
            }
        )
        self.assertEqual(product["nutrients"]["calories"], 165)
        self.assertEqual(product["nutrients"]["protein"], 31)
        self.assertEqual(product["nutrients"]["sodium"], 74)
        self.assertEqual(product["nutrients"]["vitamin_b12"], 0.3)
        self.assertIn("USDA FoodData Central", product["source"])


class InterfaceGuideTests(unittest.TestCase):
    def test_rank_guides_and_official_kickboxing_syllabus_are_included(self):
        html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
        grades = [
            "9th Kyu Red/White",
            "9th Kyu Red",
            "8th Kyu Yellow/White",
            "8th Kyu Yellow",
            "7th Kyu Orange/White",
            "7th Kyu Orange",
            "6th Kyu Green/White",
            "6th Kyu Green",
            "5th Kyu Blue/White",
            "5th Kyu Blue",
            "4th Kyu Purple/White",
            "4th Kyu Purple",
        ]
        for grade in grades:
            self.assertIn(grade, html)
        self.assertIn("How progress and ranks work", html)
        self.assertIn("Gym strength ranks", html)
        self.assertIn("What's included in Habitline", html)
        self.assertIn("Audio drill coach", html)
        self.assertNotIn("Kickboxing rhythm trainer", html)
        self.assertIn("Effective working sets per muscle group", html)
        self.assertIn("Overall muscle strength ranks", html)
        self.assertNotIn("<h2>Recovery trends</h2>", html)
        self.assertIn("function recoveryReadinessScore", html)
        self.assertIn("function weeklyMuscleSets", html)
        self.assertIn(
            'const WEEKLY_LIFTING_MUSCLES = ["Chest","Back","Shoulders","Biceps","Triceps","Forearms","Core"]',
            html,
        )
        self.assertIn("Target calories", html)
        self.assertIn("1-5 XP per completed repetition", html)
        self.assertIn("saveCompletedAudioDrill", html)
        self.assertIn('state.audioDrill.completed!==repeats', html)
        self.assertIn("kickboxingXpPerSet", html)
        self.assertIn("Stopping, restarting, closing the app or a voice error awards no XP", html)
        self.assertIn("Planner and food tracking do not award XP", html)
        self.assertNotIn('{key:"planner"', html)
        self.assertIn("SEARCH OFFLINE FOOD LIBRARY", html)
        self.assertIn("/api/foods/search", html)
        self.assertIn('name="apple-mobile-web-app-capable"', html)
        self.assertIn("Add to Home Screen", html)
        self.assertNotIn('label:"80% nutrition coverage day"', html)
        self.assertNotIn('{key:"kickboxing_score_bonus"', html)
        self.assertIn('id="audioVoice"', html)
        self.assertIn('id="audioVoiceStyle"', html)
        self.assertIn('id="previewAudioVoice"', html)
        self.assertIn("populateAudioVoices", html)
        self.assertIn("createCoachUtterance", html)
        self.assertIn("voiceQualityScore", html)
        self.assertIn("Reset level to F", html)
        self.assertIn("data-xp-reward", html)
        self.assertIn("state.settings.xp_balance", html)
        self.assertIn("state.settings.profile?.xp_rewards", html)
        self.assertNotIn("payload.app_version !==", html)
        self.assertNotIn("BELT_TESTS", html)


if __name__ == "__main__":
    unittest.main()
