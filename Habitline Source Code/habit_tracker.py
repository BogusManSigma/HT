from __future__ import annotations

import argparse
import json
import os
import re
import socket
import threading
import time
import uuid
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


APP_NAME = "Habitline"
APP_VERSION = "4.6"
DEFAULT_PORT = 8779
DEFAULT_COLORS = ["#5B6CFF", "#19A974", "#F59E45", "#D65DB1", "#3E9DD6", "#7357C8"]
OPEN_FOOD_FACTS_BASE = "https://world.openfoodfacts.org"
USDA_FDC_BASE = "https://api.nal.usda.gov/fdc/v1"
OPEN_FOOD_FACTS_FIELDS = (
    "code,product_name,product_name_en,brands,quantity,"
    "image_front_small_url,image_front_url,nutriments"
)
NUTRIENT_KEYS = (
    "calories",
    "alcohol",
    "caffeine",
    "oxalate",
    "phytate",
    "water",
    "protein",
    "fat",
    "carbs",
    "net_carbs",
    "fibre",
    "insoluble_fibre",
    "soluble_fibre",
    "starch",
    "sugars",
    "added_sugars",
    "monounsaturated_fat",
    "polyunsaturated_fat",
    "omega_3",
    "ala",
    "dha",
    "epa",
    "omega_6",
    "arachidonic_acid",
    "linoleic_acid",
    "saturated_fat",
    "trans_fat",
    "cholesterol",
    "cystine",
    "histidine",
    "isoleucine",
    "leucine",
    "lysine",
    "methionine",
    "phenylalanine",
    "threonine",
    "tryptophan",
    "tyrosine",
    "valine",
    "vitamin_b1",
    "vitamin_b2",
    "vitamin_b3",
    "vitamin_b5",
    "vitamin_b6",
    "vitamin_b12",
    "folate",
    "vitamin_a",
    "vitamin_c",
    "vitamin_d",
    "vitamin_e",
    "vitamin_k",
    "calcium",
    "copper",
    "iron",
    "magnesium",
    "manganese",
    "phosphorus",
    "potassium",
    "selenium",
    "sodium",
    "zinc",
)
DEFAULT_WEEKLY_SCHEDULE = [
    {"id": "schedule_mon_run", "weekday": 0, "title": "C25K Run", "start": "06:20", "end": "07:05", "type": "workout", "color": "#12A35B"},
    {"id": "schedule_wed_run", "weekday": 2, "title": "C25K Run", "start": "06:20", "end": "07:05", "type": "workout", "color": "#12A35B"},
    {"id": "schedule_fri_run", "weekday": 4, "title": "C25K Run", "start": "06:20", "end": "07:05", "type": "workout", "color": "#12A35B"},
    *[
        {"id": f"schedule_work_{day}", "weekday": day, "title": "Work", "start": "07:30", "end": "17:00", "type": "note", "color": "#5B82A9"}
        for day in range(5)
    ],
    {"id": "schedule_mon_kickboxing", "weekday": 0, "title": "Kickboxing", "start": "18:00", "end": "20:00", "type": "workout", "color": "#D91515"},
    {"id": "schedule_wed_kickboxing", "weekday": 2, "title": "Kickboxing", "start": "18:00", "end": "20:00", "type": "workout", "color": "#D91515"},
    {"id": "schedule_thu_kickboxing", "weekday": 3, "title": "Kickboxing", "start": "18:00", "end": "20:00", "type": "workout", "color": "#D91515"},
    {"id": "schedule_mon_push", "weekday": 0, "title": "Gym (Push)", "start": "20:30", "end": "21:30", "type": "workout", "color": "#8F18B5"},
    {"id": "schedule_tue_pull", "weekday": 1, "title": "Gym (Pull)", "start": "20:30", "end": "21:30", "type": "workout", "color": "#8F18B5"},
    {"id": "schedule_thu_push", "weekday": 3, "title": "Gym (Push)", "start": "20:30", "end": "21:30", "type": "workout", "color": "#8F18B5"},
    {"id": "schedule_fri_pull", "weekday": 4, "title": "Gym (Pull)", "start": "20:30", "end": "21:30", "type": "workout", "color": "#8F18B5"},
    {"id": "schedule_sat_rest", "weekday": 5, "title": "Rest day", "start": "", "end": "", "type": "note", "color": "#7A8491"},
    {"id": "schedule_sun_rest", "weekday": 6, "title": "Rest day", "start": "", "end": "", "type": "note", "color": "#7A8491"},
]

DEFAULT_XP_REWARDS = {
    "habit": 10,
    "workout_first": 10,
    "workout_improvement": 20,
    "workout_standard": 5,
    "journal": 15,
    "goal": 100,
}


def kickboxing_grade_xp(grade: str) -> int:
    match = re.search(r"\b(9|8|7|6|5|4)(?:th|st|nd|rd)?\s+kyu\b", grade.lower())
    if not match:
        return 1
    return {9: 1, 8: 2, 7: 3, 6: 3, 5: 4, 4: 5}[int(match.group(1))]


def default_settings() -> dict:
    return {
        "profile": {
            "age": 0,
            "display_name": "",
            "body_weight": 0,
            "weight_unit": "kg",
            "height_cm": 0,
            "sex": "male",
            "activity_level": "active",
            "goal_type": "recomposition",
            "training_experience": "beginner",
            "auto_nutrition": True,
        },
        "usda_api_key": os.environ.get("FDC_API_KEY", "DEMO_KEY"),
        "sync_token": uuid.uuid4().hex[:16],
        "xp_rewards": dict(DEFAULT_XP_REWARDS),
        "xp_offset": 0,
        "xp_balance": 0,
        "xp_awards": {},
    }
DEFAULT_NUTRITION_GOALS = {
    "calories": 2000,
    "alcohol": 0,
    "caffeine": 0,
    "oxalate": 0,
    "phytate": 0,
    "water": 3700,
    "protein": 50,
    "fat": 78,
    "carbs": 275,
    "net_carbs": 275,
    "fibre": 28,
    "insoluble_fibre": 0,
    "soluble_fibre": 0,
    "starch": 0,
    "sugars": 0,
    "added_sugars": 50,
    "monounsaturated_fat": 0,
    "polyunsaturated_fat": 0,
    "omega_3": 1.6,
    "ala": 1.6,
    "dha": 0.25,
    "epa": 0.25,
    "omega_6": 17,
    "arachidonic_acid": 0,
    "linoleic_acid": 17,
    "saturated_fat": 20,
    "trans_fat": 0,
    "cholesterol": 300,
    "cystine": 0.3,
    "histidine": 0.7,
    "isoleucine": 1.4,
    "leucine": 2.7,
    "lysine": 2.1,
    "methionine": 0.7,
    "phenylalanine": 1.75,
    "threonine": 1.05,
    "tryptophan": 0.28,
    "tyrosine": 1.75,
    "valine": 1.82,
    "vitamin_b1": 1.2,
    "vitamin_b2": 1.3,
    "vitamin_b3": 16,
    "vitamin_b5": 5,
    "vitamin_b6": 1.7,
    "vitamin_b12": 2.4,
    "folate": 400,
    "vitamin_a": 900,
    "vitamin_c": 90,
    "vitamin_d": 20,
    "vitamin_e": 15,
    "vitamin_k": 120,
    "calcium": 1300,
    "copper": 0.9,
    "iron": 18,
    "magnesium": 420,
    "manganese": 2.3,
    "phosphorus": 1250,
    "potassium": 4700,
    "selenium": 55,
    "sodium": 2300,
    "zinc": 11,
}
DEFAULT_FOODS = [
    {
        "id": "food_beef_steak_cooked",
        "name": "Beef steak, cooked",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 271,
            "water": 55.0,
            "protein": 26.0,
            "fat": 18.0,
            "carbs": 0,
            "net_carbs": 0,
            "fibre": 0,
            "monounsaturated_fat": 7.2,
            "polyunsaturated_fat": 0.7,
            "omega_3": 0.08,
            "omega_6": 0.55,
            "saturated_fat": 7.2,
            "trans_fat": 0.7,
            "cholesterol": 89,
            "cystine": 0.34,
            "histidine": 0.96,
            "isoleucine": 1.20,
            "leucine": 2.02,
            "lysine": 2.14,
            "methionine": 0.66,
            "phenylalanine": 1.00,
            "threonine": 1.03,
            "tryptophan": 0.24,
            "tyrosine": 0.82,
            "valine": 1.28,
            "vitamin_b1": 0.07,
            "vitamin_b2": 0.20,
            "vitamin_b3": 4.8,
            "vitamin_b5": 0.6,
            "vitamin_b6": 0.4,
            "vitamin_a": 0,
            "calcium": 12,
            "copper": 0.08,
            "iron": 2.5,
            "magnesium": 21,
            "manganese": 0.01,
            "phosphorus": 200,
            "potassium": 315,
            "selenium": 25,
            "sodium": 55,
            "zinc": 5.5,
            "vitamin_c": 0,
            "vitamin_d": 0.1,
            "vitamin_e": 0.3,
            "vitamin_k": 1.5,
            "vitamin_b12": 2.5,
            "folate": 9,
        },
    },
    {
        "id": "food_chicken_breast_cooked",
        "name": "Chicken breast, cooked",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 165,
            "protein": 31.0,
            "fat": 3.6,
            "carbs": 0,
            "fibre": 0,
            "calcium": 15,
            "iron": 1.0,
            "magnesium": 29,
            "phosphorus": 220,
            "potassium": 256,
            "sodium": 74,
            "zinc": 1.0,
            "vitamin_c": 0,
            "vitamin_d": 0.1,
            "vitamin_b12": 0.3,
            "folate": 4,
        },
    },
    {
        "id": "food_salmon_cooked",
        "name": "Salmon, cooked",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 206,
            "protein": 22.0,
            "fat": 12.0,
            "carbs": 0,
            "fibre": 0,
            "calcium": 12,
            "iron": 0.3,
            "magnesium": 30,
            "phosphorus": 252,
            "potassium": 384,
            "sodium": 61,
            "zinc": 0.6,
            "vitamin_c": 0,
            "vitamin_d": 13.0,
            "vitamin_b12": 3.2,
            "folate": 26,
        },
    },
    {
        "id": "food_white_rice_cooked",
        "name": "White rice, cooked",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 130,
            "protein": 2.7,
            "fat": 0.3,
            "carbs": 28.2,
            "fibre": 0.4,
            "calcium": 10,
            "iron": 0.2,
            "magnesium": 12,
            "phosphorus": 43,
            "potassium": 35,
            "sodium": 1,
            "zinc": 0.5,
            "vitamin_c": 0,
            "vitamin_d": 0,
            "vitamin_b12": 0,
            "folate": 3,
        },
    },
    {
        "id": "food_broccoli_cooked",
        "name": "Broccoli, cooked",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 35,
            "protein": 2.4,
            "fat": 0.4,
            "carbs": 7.2,
            "fibre": 3.3,
            "calcium": 40,
            "iron": 0.7,
            "magnesium": 21,
            "phosphorus": 67,
            "potassium": 293,
            "sodium": 41,
            "zinc": 0.5,
            "vitamin_c": 65,
            "vitamin_d": 0,
            "vitamin_b12": 0,
            "folate": 108,
        },
    },
    {
        "id": "food_egg_whole_cooked",
        "name": "Whole egg, cooked",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 155,
            "protein": 12.6,
            "fat": 10.6,
            "carbs": 1.1,
            "fibre": 0,
            "calcium": 50,
            "iron": 1.2,
            "magnesium": 10,
            "phosphorus": 172,
            "potassium": 126,
            "sodium": 124,
            "zinc": 1.1,
            "vitamin_c": 0,
            "vitamin_d": 2.2,
            "vitamin_b12": 1.1,
            "folate": 44,
        },
    },
    {
        "id": "food_banana",
        "name": "Banana",
        "serving_name": "100 g",
        "nutrients": {
            "calories": 89,
            "protein": 1.1,
            "fat": 0.3,
            "carbs": 22.8,
            "fibre": 2.6,
            "calcium": 5,
            "iron": 0.3,
            "magnesium": 27,
            "phosphorus": 22,
            "potassium": 358,
            "sodium": 1,
            "zinc": 0.2,
            "vitamin_c": 8.7,
            "vitamin_d": 0,
            "vitamin_b12": 0,
            "folate": 20,
        },
    },
]

# A compact common-food catalogue is bundled so everyday logging and search do
# not depend on the USDA API. Values are per 100 g and use common USDA-style
# reference values; online search remains available for branded products.
DEFAULT_FOODS.extend(
    [
        {
            "id": "food_oats_dry",
            "name": "Oats, rolled, dry",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 379, "protein": 13.2, "fat": 6.5, "carbs": 67.7,
                "fibre": 10.1, "calcium": 52, "iron": 4.3, "magnesium": 138,
                "phosphorus": 410, "potassium": 362, "sodium": 6, "zinc": 3.6,
                "vitamin_b1": 0.46, "folate": 32,
            },
        },
        {
            "id": "food_potato_baked",
            "name": "Potato, baked, flesh and skin",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 93, "protein": 2.5, "fat": 0.1, "carbs": 21.2,
                "fibre": 2.2, "calcium": 15, "iron": 1.1, "magnesium": 28,
                "phosphorus": 70, "potassium": 535, "sodium": 10, "zinc": 0.4,
                "vitamin_c": 9.6, "vitamin_b6": 0.31, "folate": 28,
            },
        },
        {
            "id": "food_sweet_potato_baked",
            "name": "Sweet potato, baked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 90, "protein": 2.0, "fat": 0.2, "carbs": 20.7,
                "fibre": 3.3, "calcium": 38, "iron": 0.7, "magnesium": 27,
                "phosphorus": 54, "potassium": 475, "sodium": 36, "zinc": 0.3,
                "vitamin_a": 961, "vitamin_c": 19.6, "vitamin_b6": 0.29,
            },
        },
        {
            "id": "food_pasta_cooked",
            "name": "Pasta, spaghetti, cooked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 158, "protein": 5.8, "fat": 0.9, "carbs": 30.9,
                "fibre": 1.8, "calcium": 7, "iron": 1.3, "magnesium": 18,
                "phosphorus": 58, "potassium": 44, "sodium": 1, "zinc": 0.5,
                "folate": 73,
            },
        },
        {
            "id": "food_bread_whole_wheat",
            "name": "Bread, whole wheat",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 247, "protein": 13.0, "fat": 4.2, "carbs": 41.0,
                "fibre": 7.0, "calcium": 107, "iron": 2.4, "magnesium": 82,
                "phosphorus": 239, "potassium": 230, "sodium": 400, "zinc": 1.7,
                "folate": 42,
            },
        },
        {
            "id": "food_greek_yogurt_plain",
            "name": "Greek yogurt, plain, nonfat",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 59, "protein": 10.3, "fat": 0.4, "carbs": 3.6,
                "sugars": 3.2, "calcium": 110, "iron": 0.1, "magnesium": 11,
                "phosphorus": 135, "potassium": 141, "sodium": 36, "zinc": 0.5,
                "vitamin_b12": 0.8,
            },
        },
        {
            "id": "food_milk_semi_skimmed",
            "name": "Milk, semi-skimmed, 2% fat",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 50, "protein": 3.3, "fat": 2.0, "carbs": 4.8,
                "sugars": 4.8, "calcium": 120, "magnesium": 11,
                "phosphorus": 92, "potassium": 140, "sodium": 47, "zinc": 0.4,
                "vitamin_b12": 0.5, "vitamin_d": 1.2,
            },
        },
        {
            "id": "food_tuna_canned_water",
            "name": "Tuna, canned in water, drained",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 116, "protein": 25.5, "fat": 0.8, "carbs": 0,
                "calcium": 11, "iron": 1.2, "magnesium": 27,
                "phosphorus": 163, "potassium": 237, "sodium": 247, "zinc": 0.8,
                "selenium": 80, "vitamin_b12": 2.5, "vitamin_d": 2.0,
            },
        },
        {
            "id": "food_turkey_breast_cooked",
            "name": "Turkey breast, cooked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 147, "protein": 30.1, "fat": 2.1, "carbs": 0,
                "calcium": 14, "iron": 1.2, "magnesium": 28,
                "phosphorus": 230, "potassium": 249, "sodium": 63, "zinc": 1.7,
                "selenium": 32, "vitamin_b12": 0.4,
            },
        },
        {
            "id": "food_beef_mince_lean_cooked",
            "name": "Beef mince, lean, cooked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 250, "protein": 26.0, "fat": 15.0, "carbs": 0,
                "saturated_fat": 5.8, "cholesterol": 88, "calcium": 18,
                "iron": 2.6, "magnesium": 21, "phosphorus": 180,
                "potassium": 318, "sodium": 72, "zinc": 6.3,
                "selenium": 21, "vitamin_b12": 2.6,
            },
        },
        {
            "id": "food_lentils_cooked",
            "name": "Lentils, cooked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 116, "protein": 9.0, "fat": 0.4, "carbs": 20.1,
                "fibre": 7.9, "calcium": 19, "iron": 3.3, "magnesium": 36,
                "phosphorus": 180, "potassium": 369, "sodium": 2, "zinc": 1.3,
                "folate": 181,
            },
        },
        {
            "id": "food_chickpeas_cooked",
            "name": "Chickpeas, cooked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 164, "protein": 8.9, "fat": 2.6, "carbs": 27.4,
                "fibre": 7.6, "calcium": 49, "iron": 2.9, "magnesium": 48,
                "phosphorus": 168, "potassium": 291, "sodium": 7, "zinc": 1.5,
                "folate": 172,
            },
        },
        {
            "id": "food_kidney_beans_cooked",
            "name": "Kidney beans, cooked",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 127, "protein": 8.7, "fat": 0.5, "carbs": 22.8,
                "fibre": 6.4, "calcium": 28, "iron": 2.9, "magnesium": 45,
                "phosphorus": 142, "potassium": 403, "sodium": 2, "zinc": 1.1,
                "folate": 130,
            },
        },
        {
            "id": "food_spinach_raw",
            "name": "Spinach, raw",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 23, "protein": 2.9, "fat": 0.4, "carbs": 3.6,
                "fibre": 2.2, "calcium": 99, "iron": 2.7, "magnesium": 79,
                "phosphorus": 49, "potassium": 558, "sodium": 79, "zinc": 0.5,
                "vitamin_a": 469, "vitamin_c": 28, "vitamin_k": 483,
                "folate": 194,
            },
        },
        {
            "id": "food_avocado",
            "name": "Avocado, raw",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 160, "protein": 2.0, "fat": 14.7, "carbs": 8.5,
                "fibre": 6.7, "monounsaturated_fat": 9.8,
                "polyunsaturated_fat": 1.8, "saturated_fat": 2.1,
                "calcium": 12, "iron": 0.6, "magnesium": 29,
                "phosphorus": 52, "potassium": 485, "sodium": 7, "zinc": 0.6,
                "vitamin_c": 10, "vitamin_e": 2.1, "folate": 81,
            },
        },
        {
            "id": "food_apple",
            "name": "Apple, raw, with skin",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.8,
                "sugars": 10.4, "fibre": 2.4, "calcium": 6, "iron": 0.1,
                "magnesium": 5, "phosphorus": 11, "potassium": 107, "sodium": 1,
                "vitamin_c": 4.6, "folate": 3,
            },
        },
        {
            "id": "food_orange",
            "name": "Orange, raw",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 47, "protein": 0.9, "fat": 0.1, "carbs": 11.8,
                "sugars": 9.4, "fibre": 2.4, "calcium": 40, "iron": 0.1,
                "magnesium": 10, "phosphorus": 14, "potassium": 181, "sodium": 0,
                "vitamin_c": 53.2, "folate": 30,
            },
        },
        {
            "id": "food_blueberries",
            "name": "Blueberries, raw",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 57, "protein": 0.7, "fat": 0.3, "carbs": 14.5,
                "sugars": 10.0, "fibre": 2.4, "calcium": 6, "iron": 0.3,
                "magnesium": 6, "phosphorus": 12, "potassium": 77, "sodium": 1,
                "vitamin_c": 9.7, "vitamin_k": 19.3, "folate": 6,
            },
        },
        {
            "id": "food_almonds",
            "name": "Almonds",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 579, "protein": 21.2, "fat": 49.9, "carbs": 21.6,
                "fibre": 12.5, "monounsaturated_fat": 31.6,
                "polyunsaturated_fat": 12.3, "saturated_fat": 3.8,
                "calcium": 269, "iron": 3.7, "magnesium": 270,
                "phosphorus": 481, "potassium": 733, "sodium": 1, "zinc": 3.1,
                "vitamin_e": 25.6, "folate": 44,
            },
        },
        {
            "id": "food_peanut_butter",
            "name": "Peanut butter, smooth",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 588, "protein": 25.1, "fat": 50.4, "carbs": 20.0,
                "fibre": 6.0, "sugars": 9.2, "monounsaturated_fat": 24.4,
                "polyunsaturated_fat": 15.6, "saturated_fat": 10.1,
                "calcium": 43, "iron": 1.9, "magnesium": 154,
                "phosphorus": 358, "potassium": 649, "sodium": 459, "zinc": 2.5,
                "vitamin_e": 9.1, "folate": 74,
            },
        },
        {
            "id": "food_olive_oil",
            "name": "Olive oil",
            "serving_name": "100 g",
            "nutrients": {
                "calories": 884, "protein": 0, "fat": 100, "carbs": 0,
                "monounsaturated_fat": 73.0, "polyunsaturated_fat": 10.5,
                "saturated_fat": 13.8, "vitamin_e": 14.4, "vitamin_k": 60.2,
            },
        },
    ]
)

OFFLINE_FOOD_ALIASES = {
    "chicken": "chicken breast",
    "mince": "beef mince",
    "ground beef": "beef mince",
    "yoghurt": "yogurt",
    "porridge": "oats",
    "spaghetti": "pasta spaghetti",
    "beans": "kidney beans",
}


def search_offline_foods(foods: list[dict], query: str, limit: int = 20) -> list[dict]:
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", query.lower()).strip()
    cleaned = OFFLINE_FOOD_ALIASES.get(cleaned, cleaned)
    terms = [term for term in cleaned.split() if term]
    if not terms:
        return []

    ranked = []
    for food in foods:
        searchable = " ".join(
            str(food.get(key, "")) for key in ("name", "brand", "barcode")
        ).lower()
        matched = sum(term in searchable for term in terms)
        if not matched:
            continue
        all_terms = matched == len(terms)
        starts = searchable.startswith(cleaned)
        ranked.append(
            (
                0 if all_terms and starts else 1 if all_terms else 2,
                -matched,
                food.get("name", "").lower(),
                food,
            )
        )
    ranked.sort(key=lambda item: item[:3])
    return [item[3] for item in ranked[:limit]]


def parse_number(value: str | int | float) -> float:
    """Parse values such as 12500, 12.5k, 2m, or '20k steps'."""
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        cleaned = value.strip().lower().replace(",", "").replace("_", "")
        match = re.fullmatch(
            r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([km]?)\s*(?:[a-z%]+)?",
            cleaned,
        )
        if not match:
            raise ValueError("Enter a number, for example 12500 or 12.5k.")
        result = float(match.group(1)) * {"": 1, "k": 1_000, "m": 1_000_000}[
            match.group(2)
        ]
    if result < 0:
        raise ValueError("The value cannot be negative.")
    return result


def period_dates(selected: date, period: str) -> list[date]:
    if period == "week":
        start = selected - timedelta(days=selected.weekday())
    elif period == "month":
        start = selected.replace(day=1)
    else:
        raise ValueError("Period must be 'week' or 'month'.")
    return [start + timedelta(days=index) for index in range((selected - start).days + 1)]


def habit_stats(habit: dict, selected: date, period: str) -> dict:
    days = period_dates(selected, period)
    entries = habit.get("entries", {})
    if habit["type"] == "check":
        completed = sum(bool(entries.get(day.isoformat(), False)) for day in days)
        percentage = completed / len(days) * 100
        return {
            "average": percentage,
            "goal_rate": percentage,
            "completed": completed,
            "days": len(days),
        }

    values = [float(entries.get(day.isoformat(), 0) or 0) for day in days]
    target = float(habit["target"])
    reached = sum(value >= target for value in values)
    return {
        "average": sum(values) / len(days),
        "goal_rate": reached / len(days) * 100,
        "completed": reached,
        "days": len(days),
    }


def scaled_nutrients(food: dict, amount_g: float) -> dict:
    factor = amount_g / 100
    return {
        key: float(food.get("nutrients", {}).get(key, 0) or 0) * factor
        for key in NUTRIENT_KEYS
    }


def _off_value(nutriments: dict, source: str, factor: float = 1) -> float:
    try:
        return max(float(nutriments.get(f"{source}_100g", 0) or 0) * factor, 0)
    except (TypeError, ValueError):
        return 0


def open_food_facts_product(product: dict) -> dict | None:
    name = (
        product.get("product_name")
        or product.get("product_name_en")
        or ""
    ).strip()
    barcode = re.sub(r"\D", "", str(product.get("code", "")))
    if not name or not barcode:
        return None
    source_map = {
        "calories": ("energy-kcal", 1),
        "alcohol": ("alcohol", 1),
        "caffeine": ("caffeine", 1000),
        "water": ("water", 1),
        "protein": ("proteins", 1),
        "fat": ("fat", 1),
        "carbs": ("carbohydrates", 1),
        "fibre": ("fiber", 1),
        "starch": ("starch", 1),
        "sugars": ("sugars", 1),
        "added_sugars": ("added-sugars", 1),
        "monounsaturated_fat": ("monounsaturated-fat", 1),
        "polyunsaturated_fat": ("polyunsaturated-fat", 1),
        "omega_3": ("omega-3-fat", 1),
        "ala": ("alpha-linolenic-acid", 1),
        "dha": ("docosahexaenoic-acid", 1),
        "epa": ("eicosapentaenoic-acid", 1),
        "omega_6": ("omega-6-fat", 1),
        "arachidonic_acid": ("arachidonic-acid", 1),
        "linoleic_acid": ("linoleic-acid", 1),
        "saturated_fat": ("saturated-fat", 1),
        "trans_fat": ("trans-fat", 1),
        "cholesterol": ("cholesterol", 1000),
        "cystine": ("cystine", 1),
        "histidine": ("histidine", 1),
        "isoleucine": ("isoleucine", 1),
        "leucine": ("leucine", 1),
        "lysine": ("lysine", 1),
        "methionine": ("methionine", 1),
        "phenylalanine": ("phenylalanine", 1),
        "threonine": ("threonine", 1),
        "tryptophan": ("tryptophan", 1),
        "tyrosine": ("tyrosine", 1),
        "valine": ("valine", 1),
        "vitamin_b1": ("vitamin-b1", 1000),
        "vitamin_b2": ("vitamin-b2", 1000),
        "vitamin_b3": ("vitamin-pp", 1000),
        "vitamin_b5": ("pantothenic-acid", 1000),
        "vitamin_b6": ("vitamin-b6", 1000),
        "vitamin_b12": ("vitamin-b12", 1_000_000),
        "folate": ("folates", 1_000_000),
        "vitamin_a": ("vitamin-a", 1_000_000),
        "vitamin_c": ("vitamin-c", 1000),
        "vitamin_d": ("vitamin-d", 1_000_000),
        "vitamin_e": ("vitamin-e", 1000),
        "vitamin_k": ("vitamin-k", 1_000_000),
        "calcium": ("calcium", 1000),
        "copper": ("copper", 1000),
        "iron": ("iron", 1000),
        "magnesium": ("magnesium", 1000),
        "manganese": ("manganese", 1000),
        "phosphorus": ("phosphorus", 1000),
        "potassium": ("potassium", 1000),
        "selenium": ("selenium", 1_000_000),
        "sodium": ("sodium", 1000),
        "zinc": ("zinc", 1000),
    }
    nutriments = product.get("nutriments") or {}
    nutrients = {key: 0.0 for key in NUTRIENT_KEYS}
    for target, (source, factor) in source_map.items():
        nutrients[target] = _off_value(nutriments, source, factor)
    nutrients["net_carbs"] = nutrients["carbs"]
    return {
        "barcode": barcode,
        "name": name,
        "brand": str(product.get("brands", "")).strip(),
        "quantity": str(product.get("quantity", "")).strip(),
        "image_url": product.get("image_front_small_url")
        or product.get("image_front_url")
        or "",
        "source": "Open Food Facts",
        "source_url": f"{OPEN_FOOD_FACTS_BASE}/product/{barcode}",
        "serving_name": "100 g",
        "nutrients": nutrients,
    }


def fetch_open_food_facts(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": "Habitline/1.0 (local desktop nutrition tracker)",
            "Accept": "application/json",
        },
    )
    last_error = None
    for attempt in range(2):
        try:
            with urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == 0:
                time.sleep(0.5)
    raise ValueError(
        "The online food database could not be reached. Check your internet connection and try again."
    ) from last_error


USDA_NUTRIENT_NAMES = {
    "energy": "calories",
    "energy (atwater general factors)": "calories",
    "energy (atwater specific factors)": "calories",
    "water": "water",
    "protein": "protein",
    "total lipid (fat)": "fat",
    "carbohydrate, by difference": "carbs",
    "fiber, total dietary": "fibre",
    "fiber, insoluble": "insoluble_fibre",
    "fiber, soluble": "soluble_fibre",
    "starch": "starch",
    "sugars, total including nlea": "sugars",
    "sugars, total": "sugars",
    "sugars, added": "added_sugars",
    "fatty acids, total monounsaturated": "monounsaturated_fat",
    "fatty acids, total polyunsaturated": "polyunsaturated_fat",
    "fatty acids, total saturated": "saturated_fat",
    "fatty acids, total trans": "trans_fat",
    "cholesterol": "cholesterol",
    "caffeine": "caffeine",
    "alcohol, ethyl": "alcohol",
    "cystine": "cystine",
    "histidine": "histidine",
    "isoleucine": "isoleucine",
    "leucine": "leucine",
    "lysine": "lysine",
    "methionine": "methionine",
    "phenylalanine": "phenylalanine",
    "threonine": "threonine",
    "tryptophan": "tryptophan",
    "tyrosine": "tyrosine",
    "valine": "valine",
    "thiamin": "vitamin_b1",
    "riboflavin": "vitamin_b2",
    "niacin": "vitamin_b3",
    "pantothenic acid": "vitamin_b5",
    "vitamin b-6": "vitamin_b6",
    "vitamin b-12": "vitamin_b12",
    "folate, total": "folate",
    "vitamin a, rae": "vitamin_a",
    "vitamin c, total ascorbic acid": "vitamin_c",
    "vitamin d (d2 + d3)": "vitamin_d",
    "vitamin e (alpha-tocopherol)": "vitamin_e",
    "vitamin k (phylloquinone)": "vitamin_k",
    "calcium, ca": "calcium",
    "copper, cu": "copper",
    "iron, fe": "iron",
    "magnesium, mg": "magnesium",
    "manganese, mn": "manganese",
    "phosphorus, p": "phosphorus",
    "potassium, k": "potassium",
    "selenium, se": "selenium",
    "sodium, na": "sodium",
    "zinc, zn": "zinc",
    "18:3 n-3 c,c,c (ala)": "ala",
    "20:5 n-3 (epa)": "epa",
    "22:6 n-3 (dha)": "dha",
    "18:2 n-6 c,c": "linoleic_acid",
    "20:4 undifferentiated": "arachidonic_acid",
}
NUTRIENT_TARGET_UNITS = {
    **{key: "g" for key in NUTRIENT_KEYS},
    "calories": "kcal",
    "caffeine": "mg",
    "cholesterol": "mg",
    "vitamin_b1": "mg",
    "vitamin_b2": "mg",
    "vitamin_b3": "mg",
    "vitamin_b5": "mg",
    "vitamin_b6": "mg",
    "vitamin_b12": "mcg",
    "folate": "mcg",
    "vitamin_a": "mcg",
    "vitamin_c": "mg",
    "vitamin_d": "mcg",
    "vitamin_e": "mg",
    "vitamin_k": "mcg",
    "calcium": "mg",
    "copper": "mg",
    "iron": "mg",
    "magnesium": "mg",
    "manganese": "mg",
    "phosphorus": "mg",
    "potassium": "mg",
    "selenium": "mcg",
    "sodium": "mg",
    "zinc": "mg",
}


def convert_nutrient_unit(value: float, source: str, target: str) -> float:
    source = source.lower().replace("µ", "u")
    target = target.lower()
    if source == "kj" and target == "kcal":
        return value / 4.184
    aliases = {"ug": "mcg", "µg": "mcg"}
    source = aliases.get(source, source)
    factors = {"g": 1_000_000, "mg": 1_000, "mcg": 1}
    if source in factors and target in factors:
        return value * factors[source] / factors[target]
    return value


def usda_food_product(food: dict) -> dict | None:
    name = str(food.get("description") or "").strip()
    fdc_id = food.get("fdcId")
    if not name or not fdc_id:
        return None
    nutrients = {key: 0 for key in NUTRIENT_KEYS}
    for row in food.get("foodNutrients") or []:
        nutrient = row.get("nutrient") or {}
        nutrient_name = str(
            row.get("nutrientName") or nutrient.get("name") or ""
        ).strip().lower()
        key = USDA_NUTRIENT_NAMES.get(nutrient_name)
        if not key:
            continue
        value = row.get("value", row.get("amount", 0))
        unit = str(row.get("unitName") or nutrient.get("unitName") or "")
        try:
            nutrients[key] = round(
                convert_nutrient_unit(
                    float(value or 0), unit, NUTRIENT_TARGET_UNITS[key]
                ),
                6,
            )
        except (TypeError, ValueError):
            continue
    nutrients["net_carbs"] = max(
        0, nutrients["carbs"] - nutrients["fibre"]
    )
    nutrients["omega_3"] = (
        nutrients["ala"] + nutrients["epa"] + nutrients["dha"]
    )
    nutrients["omega_6"] = (
        nutrients["linoleic_acid"] + nutrients["arachidonic_acid"]
    )
    return {
        "name": name.title() if name.isupper() else name,
        "barcode": re.sub(r"\D", "", str(food.get("gtinUpc") or "")),
        "brand": str(food.get("brandName") or food.get("brandOwner") or "").strip(),
        "quantity": " ".join(
            str(value)
            for value in (food.get("servingSize"), food.get("servingSizeUnit"))
            if value
        ),
        "image_url": "",
        "source": f"USDA FoodData Central - {food.get('dataType', 'Food')}",
        "source_url": (
            f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients"
        ),
        "serving_name": "100 g",
        "nutrients": nutrients,
        "fdc_id": str(fdc_id),
    }


def local_network_ip() -> str:
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(("8.8.8.8", 80))
        return str(connection.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        connection.close()


def fetch_usda_foods(
    query: str, api_key: str, page_size: int = 15, branded_only: bool = False
) -> list[dict]:
    def search(data_types: list[str], size: int) -> list[dict]:
        request = Request(
            f"{USDA_FDC_BASE}/foods/search?{urlencode({'api_key': api_key})}",
            data=json.dumps(
                {
                    "query": query,
                    "pageSize": size,
                    "dataType": data_types,
                }
            ).encode("utf-8"),
            headers={
                "User-Agent": "Habitline/2.0 (local nutrition tracker)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [
            product
            for raw in payload.get("foods", [])
            if (product := usda_food_product(raw))
        ]

    try:
        if branded_only:
            return search(["Branded"], page_size)
        common_size = max(8, page_size // 2 + 1)
        common = search(
            ["Foundation", "SR Legacy", "Survey (FNDDS)"], common_size
        )
        branded = search(["Branded"], max(5, page_size - len(common)))
        return (common + branded)[:page_size]
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ValueError(
            "USDA FoodData Central could not be reached. Check the API key and internet connection."
        ) from error


class HabitStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.habits: list[dict] = []
        self.exercises: list[dict] = []
        self.workouts: list[dict] = []
        self.workout_days: list[dict] = []
        self.foods: list[dict] = []
        self.food_entries: list[dict] = []
        self.nutrition_goals: dict = dict(DEFAULT_NUTRITION_GOALS)
        self.body_entries: list[dict] = []
        self.recovery_entries: list[dict] = []
        self.meals: list[dict] = []
        self.planner_events: list[dict] = []
        self.shopping_items: list[dict] = []
        self.journal_entries: list[dict] = []
        self.goals: list[dict] = []
        self.kickboxing_sessions: list[dict] = []
        self.trash: list[dict] = []
        self.weekly_schedule: list[dict] = json.loads(
            json.dumps(DEFAULT_WEEKLY_SCHEDULE)
        )
        self.settings: dict = default_settings()
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.habits = data.get("habits", [])
            self.exercises = data.get("exercises", [])
            self.workouts = data.get("workouts", [])
            self.workout_days = data.get("workout_days", [])
            self.foods = data.get("foods", [])
            self.food_entries = data.get("food_entries", [])
            self.body_entries = data.get("body_entries", [])
            self.recovery_entries = data.get("recovery_entries", [])
            self.meals = data.get("meals", [])
            self.planner_events = data.get("planner_events", [])
            self.shopping_items = data.get("shopping_items", [])
            self.journal_entries = data.get("journal_entries", [])
            self.goals = data.get("goals", [])
            self.kickboxing_sessions = data.get("kickboxing_sessions", [])
            self.trash = data.get("trash", [])
            self.weekly_schedule = data.get(
                "weekly_schedule", json.loads(json.dumps(DEFAULT_WEEKLY_SCHEDULE))
            )
            original_schedule_count = len(self.weekly_schedule)
            self.weekly_schedule = [
                item
                for item in self.weekly_schedule
                if not str(item.get("id", "")).startswith("schedule_steps_")
                and str(item.get("title", "")).strip().lower() not in {
                    "20k steps",
                    "20,000 steps",
                }
            ]
            loaded_settings = data.get("settings", {})
            loaded_profile = loaded_settings.get("profile", {})
            loaded_rewards = dict(loaded_settings.get("xp_rewards", {}))
            if not loaded_rewards:
                loaded_rewards = dict(loaded_profile.get("xp_rewards", {}))
            loaded_rewards = {
                key: value
                for key, value in loaded_rewards.items()
                if key in DEFAULT_XP_REWARDS
            }
            loaded_offset = loaded_settings.get(
                "xp_offset", loaded_profile.get("xp_offset", 0)
            )
            self.settings = {
                **default_settings(),
                **loaded_settings,
                "profile": {
                    **default_settings()["profile"],
                    **loaded_profile,
                },
                "xp_rewards": {
                    **DEFAULT_XP_REWARDS,
                    **loaded_rewards,
                },
                "xp_offset": max(0, int(loaded_offset or 0)),
                "xp_balance": max(0, int(loaded_settings.get("xp_balance", 0) or 0)),
                "xp_awards": (
                    loaded_settings.get("xp_awards", {})
                    if isinstance(loaded_settings.get("xp_awards", {}), dict)
                    else {}
                ),
            }
            if "xp_rewards" in loaded_profile:
                self.settings["profile"]["xp_rewards"] = {
                    **DEFAULT_XP_REWARDS,
                    **loaded_rewards,
                }
            if "xp_balance" not in loaded_settings:
                self.settings["xp_balance"] = max(
                    0, self._legacy_raw_xp() - self.settings["xp_offset"]
                )
                self.settings["xp_awards"] = self._legacy_award_markers()
            zero_awards_cleared = False
            if (
                "xp_balance" in loaded_settings
                and self.settings["xp_balance"] == 0
                and self.settings["xp_awards"]
                and all(
                    int(award.get("amount", 0) or 0) == 0
                    for award in self.settings["xp_awards"].values()
                    if isinstance(award, dict)
                )
            ):
                self.settings["xp_awards"] = {}
                zero_awards_cleared = True
            schema_changed = any(
                key not in data
                for key in (
                    "workout_days",
                    "foods",
                    "food_entries",
                    "nutrition_goals",
                    "body_entries",
                    "recovery_entries",
                    "meals",
                    "planner_events",
                    "shopping_items",
                    "journal_entries",
                    "goals",
                    "kickboxing_sessions",
                    "trash",
                    "weekly_schedule",
                    "settings",
                )
            ) or any(
                key not in loaded_settings
                for key in ("xp_rewards", "xp_offset", "xp_balance", "xp_awards")
            ) or len(self.weekly_schedule) != original_schedule_count or zero_awards_cleared
            self.nutrition_goals = {
                **DEFAULT_NUTRITION_GOALS,
                **data.get("nutrition_goals", {}),
            }
            if not self.foods:
                self.foods = json.loads(json.dumps(DEFAULT_FOODS))
                self.save()
            else:
                changed = schema_changed
                defaults_by_id = {food["id"]: food for food in DEFAULT_FOODS}
                existing_ids = {food.get("id") for food in self.foods}
                for default_food in DEFAULT_FOODS:
                    if default_food["id"] not in existing_ids:
                        self.foods.append(json.loads(json.dumps(default_food)))
                        changed = True
                for food in self.foods:
                    nutrients = food.setdefault("nutrients", {})
                    default_nutrients = defaults_by_id.get(food.get("id"), {}).get(
                        "nutrients", {}
                    )
                    for key in NUTRIENT_KEYS:
                        if key not in nutrients:
                            nutrients[key] = default_nutrients.get(key, 0)
                            changed = True
                if changed:
                    self.save()
        except FileNotFoundError:
            self.habits = [
                {
                    "id": uuid.uuid4().hex,
                    "name": "Walk 20k steps",
                    "type": "number",
                    "target": 20_000,
                    "unit": "steps",
                    "color": DEFAULT_COLORS[0],
                    "entries": {},
                }
            ]
            self.exercises = []
            self.workouts = []
            self.workout_days = []
            self.foods = json.loads(json.dumps(DEFAULT_FOODS))
            self.food_entries = []
            self.nutrition_goals = dict(DEFAULT_NUTRITION_GOALS)
            self.body_entries = []
            self.recovery_entries = []
            self.meals = []
            self.planner_events = []
            self.shopping_items = []
            self.journal_entries = []
            self.goals = []
            self.kickboxing_sessions = []
            self.trash = []
            self.weekly_schedule = json.loads(json.dumps(DEFAULT_WEEKLY_SCHEDULE))
            self.settings = default_settings()
            self.save()
        except (json.JSONDecodeError, OSError, TypeError):
            self.habits = []
            self.exercises = []
            self.workouts = []
            self.workout_days = []
            self.foods = json.loads(json.dumps(DEFAULT_FOODS))
            self.food_entries = []
            self.nutrition_goals = dict(DEFAULT_NUTRITION_GOALS)
            self.body_entries = []
            self.recovery_entries = []
            self.meals = []
            self.planner_events = []
            self.shopping_items = []
            self.journal_entries = []
            self.goals = []
            self.kickboxing_sessions = []
            self.trash = []
            self.weekly_schedule = json.loads(json.dumps(DEFAULT_WEEKLY_SCHEDULE))
            self.settings = default_settings()

    def _habit_met(self, habit: dict, value) -> bool:
        if habit.get("type") == "check":
            return bool(value)
        try:
            return float(value or 0) >= float(habit.get("target", 0))
        except (TypeError, ValueError):
            return False

    def _workout_reward_key(self, workout: dict) -> str:
        exercise_rows = sorted(
            (
                (position, item)
                for position, item in enumerate(self.workouts)
                if item.get("exercise_id") == workout.get("exercise_id")
            ),
            key=lambda row: (row[1].get("date", ""), row[0]),
        )
        index = next(
            (
                position
                for position, (_, item) in enumerate(exercise_rows)
                if item["id"] == workout["id"]
            ),
            0,
        )
        if index == 0:
            return "workout_first"
        previous = exercise_rows[index - 1][1]
        if any(
            float(workout.get(key, 0)) > float(previous.get(key, 0))
            for key in ("weight", "sets", "reps")
        ):
            return "workout_improvement"
        return "workout_standard"

    def _legacy_raw_xp(self) -> int:
        rewards = self.settings.get("xp_rewards", DEFAULT_XP_REWARDS)
        total = 0
        for habit in self.habits:
            total += sum(
                int(rewards.get("habit", 0))
                for value in habit.get("entries", {}).values()
                if self._habit_met(habit, value)
            )
        for workout in self.workouts:
            total += int(rewards.get(self._workout_reward_key(workout), 0))
        total += len(self.journal_entries) * int(rewards.get("journal", 0))
        total += sum(
            int(rewards.get("goal", 0))
            for goal in self.goals
            if goal.get("completed")
        )
        total += sum(
            kickboxing_grade_xp(item.get("belt", "")) * int(item.get("attempts", 1))
            for item in self.kickboxing_sessions
            if item.get("mode") == "audio-drill"
        )
        return total

    def _legacy_award_markers(self) -> dict:
        markers: dict[str, dict] = {}
        for habit in self.habits:
            for day, value in habit.get("entries", {}).items():
                if self._habit_met(habit, value):
                    markers[f"habit:{habit['id']}:{day}"] = {
                        "amount": 0,
                        "active": True,
                    }
        for workout in self.workouts:
            markers[f"workout:{workout['id']}"] = {"amount": 0, "active": True}
        for entry in self.journal_entries:
            markers[f"journal:{entry['id']}"] = {"amount": 0, "active": True}
        for goal in self.goals:
            if goal.get("completed"):
                markers[f"goal:{goal['id']}"] = {"amount": 0, "active": True}
        for session in self.kickboxing_sessions:
            if session.get("mode") == "audio-drill":
                markers[f"kickboxing:{session['id']}"] = {
                    "amount": 0,
                    "active": True,
                }
        return markers

    def set_xp_award(self, key: str, amount: int, active: bool = True) -> int:
        amount = max(0, int(amount))
        awards = self.settings.setdefault("xp_awards", {})
        current = awards.get(key)
        before = int(current.get("amount", 0)) if current and current.get("active") else 0
        if current is None:
            current = {"amount": amount, "active": bool(active)}
            awards[key] = current
        else:
            current["active"] = bool(active)
            current["amount"] = amount
        after = int(current.get("amount", 0)) if current.get("active") else 0
        change = after - before
        self.settings["xp_balance"] = max(
            0, int(self.settings.get("xp_balance", 0)) + change
        )
        self.save()
        return change

    def revoke_xp_prefix(self, prefix: str) -> int:
        change = 0
        for key, award in self.settings.setdefault("xp_awards", {}).items():
            if key.startswith(prefix) and award.get("active"):
                change -= int(award.get("amount", 0))
                award["active"] = False
        self.settings["xp_balance"] = max(
            0, int(self.settings.get("xp_balance", 0)) + change
        )
        self.save()
        return change

    def reset_xp(self) -> None:
        self.settings["xp_balance"] = 0
        self.settings["xp_awards"] = {}
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "habits": self.habits,
                    "exercises": self.exercises,
                    "workouts": self.workouts,
                    "workout_days": self.workout_days,
                    "foods": self.foods,
                    "food_entries": self.food_entries,
                    "nutrition_goals": self.nutrition_goals,
                    "body_entries": self.body_entries,
                    "recovery_entries": self.recovery_entries,
                    "meals": self.meals,
                    "planner_events": self.planner_events,
                    "shopping_items": self.shopping_items,
                    "journal_entries": self.journal_entries,
                    "goals": self.goals,
                    "kickboxing_sessions": self.kickboxing_sessions,
                    "trash": self.trash,
                    "weekly_schedule": self.weekly_schedule,
                    "settings": self.settings,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def add(self, habit: dict) -> None:
        with self.lock:
            self.habits.append(habit)
            self.save()

    def delete(self, habit_id: str) -> bool:
        with self.lock:
            before = len(self.habits)
            self.habits = [habit for habit in self.habits if habit["id"] != habit_id]
            if len(self.habits) != before:
                self.save()
                return True
            return False

    def get(self, habit_id: str) -> dict | None:
        return next((habit for habit in self.habits if habit["id"] == habit_id), None)

    def update(self, habit_id: str, changes: dict) -> dict | None:
        with self.lock:
            habit = self.get(habit_id)
            if not habit:
                return None
            habit.update(changes)
            self.save()
            return habit

    def set_entry(self, habit_id: str, day: str, value) -> dict | None:
        with self.lock:
            habit = self.get(habit_id)
            if not habit:
                return None
            if value is None:
                habit["entries"].pop(day, None)
            else:
                habit["entries"][day] = value
            self.save()
            return habit

    def get_exercise(self, exercise_id: str) -> dict | None:
        return next(
            (exercise for exercise in self.exercises if exercise["id"] == exercise_id),
            None,
        )

    def add_exercise(self, exercise: dict) -> None:
        with self.lock:
            self.exercises.append(exercise)
            self.save()

    def update_exercise(self, exercise_id: str, changes: dict) -> dict | None:
        with self.lock:
            exercise = self.get_exercise(exercise_id)
            if not exercise:
                return None
            exercise.update(changes)
            self.save()
            return exercise

    def delete_exercise(self, exercise_id: str) -> bool:
        with self.lock:
            before = len(self.exercises)
            self.exercises = [
                exercise
                for exercise in self.exercises
                if exercise["id"] != exercise_id
            ]
            if len(self.exercises) == before:
                return False
            self.workouts = [
                workout
                for workout in self.workouts
                if workout["exercise_id"] != exercise_id
            ]
            for workout_day in self.workout_days:
                workout_day["exercise_ids"] = [
                    saved_id
                    for saved_id in workout_day.get("exercise_ids", [])
                    if saved_id != exercise_id
                ]
            self.save()
            return True

    def get_workout(self, workout_id: str) -> dict | None:
        return next(
            (workout for workout in self.workouts if workout["id"] == workout_id),
            None,
        )

    def add_workout(self, workout: dict) -> None:
        with self.lock:
            self.workouts.append(workout)
            self.save()

    def update_workout(self, workout_id: str, changes: dict) -> dict | None:
        with self.lock:
            workout = self.get_workout(workout_id)
            if not workout:
                return None
            workout.update(changes)
            self.save()
            return workout

    def delete_workout(self, workout_id: str) -> bool:
        with self.lock:
            before = len(self.workouts)
            self.workouts = [
                workout for workout in self.workouts if workout["id"] != workout_id
            ]
            if len(self.workouts) == before:
                return False
            self.save()
            return True

    def get_workout_day(self, workout_day_id: str) -> dict | None:
        return next(
            (
                workout_day
                for workout_day in self.workout_days
                if workout_day["id"] == workout_day_id
            ),
            None,
        )

    def add_workout_day(self, workout_day: dict) -> None:
        with self.lock:
            self.workout_days.append(workout_day)
            self.save()

    def update_workout_day(
        self, workout_day_id: str, changes: dict
    ) -> dict | None:
        with self.lock:
            workout_day = self.get_workout_day(workout_day_id)
            if not workout_day:
                return None
            workout_day.update(changes)
            self.save()
            return workout_day

    def delete_workout_day(self, workout_day_id: str) -> bool:
        with self.lock:
            before = len(self.workout_days)
            self.workout_days = [
                workout_day
                for workout_day in self.workout_days
                if workout_day["id"] != workout_day_id
            ]
            if len(self.workout_days) == before:
                return False
            self.save()
            return True

    def get_food(self, food_id: str) -> dict | None:
        return next((food for food in self.foods if food["id"] == food_id), None)

    def add_food(self, food: dict) -> None:
        with self.lock:
            self.foods.append(food)
            self.save()

    def update_food(self, food_id: str, changes: dict) -> dict | None:
        with self.lock:
            food = self.get_food(food_id)
            if not food:
                return None
            food.update(changes)
            self.save()
            return food

    def delete_food(self, food_id: str) -> bool:
        with self.lock:
            before = len(self.foods)
            self.foods = [food for food in self.foods if food["id"] != food_id]
            if len(self.foods) == before:
                return False
            self.food_entries = [
                entry for entry in self.food_entries if entry["food_id"] != food_id
            ]
            self.save()
            return True

    def get_food_entry(self, entry_id: str) -> dict | None:
        return next(
            (entry for entry in self.food_entries if entry["id"] == entry_id), None
        )

    def add_food_entry(self, entry: dict) -> None:
        with self.lock:
            self.food_entries.append(entry)
            self.save()

    def update_food_entry(self, entry_id: str, changes: dict) -> dict | None:
        with self.lock:
            entry = self.get_food_entry(entry_id)
            if not entry:
                return None
            entry.update(changes)
            self.save()
            return entry

    def delete_food_entry(self, entry_id: str) -> bool:
        with self.lock:
            before = len(self.food_entries)
            self.food_entries = [
                entry for entry in self.food_entries if entry["id"] != entry_id
            ]
            if len(self.food_entries) == before:
                return False
            self.save()
            return True

    def update_nutrition_goals(self, goals: dict) -> dict:
        with self.lock:
            self.nutrition_goals = goals
            self.save()
            return self.nutrition_goals

    def all_data(self, include_trash: bool = True) -> dict:
        payload = {
            "app_version": APP_VERSION,
            "habits": self.habits,
            "exercises": self.exercises,
            "workouts": self.workouts,
            "workout_days": self.workout_days,
            "foods": self.foods,
            "food_entries": self.food_entries,
            "nutrition_goals": self.nutrition_goals,
            "body_entries": self.body_entries,
            "recovery_entries": self.recovery_entries,
            "meals": self.meals,
            "planner_events": self.planner_events,
            "shopping_items": self.shopping_items,
            "journal_entries": self.journal_entries,
            "goals": self.goals,
            "kickboxing_sessions": self.kickboxing_sessions,
            "weekly_schedule": self.weekly_schedule,
            "settings": self.settings,
        }
        if include_trash:
            payload["trash"] = self.trash
        return payload

    def collection(self, name: str) -> list[dict]:
        allowed = {
            "body_entries",
            "recovery_entries",
            "meals",
            "planner_events",
            "shopping_items",
            "journal_entries",
            "goals",
            "kickboxing_sessions",
            "weekly_schedule",
        }
        if name not in allowed:
            raise ValueError("Unknown collection.")
        return getattr(self, name)

    def add_item(self, collection: str, item: dict) -> dict:
        with self.lock:
            self.collection(collection).append(item)
            self.save()
            return item

    def update_item(self, collection: str, item_id: str, changes: dict) -> dict | None:
        with self.lock:
            item = next(
                (row for row in self.collection(collection) if row["id"] == item_id),
                None,
            )
            if not item:
                return None
            item.update(changes)
            self.save()
            return item

    def delete_item(self, collection: str, item_id: str) -> bool:
        with self.lock:
            rows = self.collection(collection)
            item = next((row for row in rows if row["id"] == item_id), None)
            if not item:
                return False
            setattr(
                self,
                collection,
                [row for row in rows if row["id"] != item_id],
            )
            self.trash.append(
                {
                    "id": uuid.uuid4().hex,
                    "collection": collection,
                    "item": item,
                    "deleted_at": time.time(),
                }
            )
            self.trash = self.trash[-30:]
            self.save()
            return True

    def restore_item(self, trash_id: str) -> dict | None:
        with self.lock:
            deleted = next(
                (row for row in self.trash if row["id"] == trash_id), None
            )
            if not deleted:
                return None
            collection = self.collection(deleted["collection"])
            item = deleted["item"]
            if not any(row["id"] == item["id"] for row in collection):
                collection.append(item)
            self.trash = [row for row in self.trash if row["id"] != trash_id]
            self.save()
            return item

    def import_data(self, payload: dict) -> None:
        required = {"habits", "exercises", "workouts"}
        if not required.issubset(payload):
            raise ValueError("This is not a valid Habitline backup.")
        with self.lock:
            for key in (
                "habits",
                "exercises",
                "workouts",
                "workout_days",
                "foods",
                "food_entries",
                "body_entries",
                "recovery_entries",
                "meals",
                "planner_events",
                "shopping_items",
                "journal_entries",
                "goals",
                "kickboxing_sessions",
                "trash",
                "weekly_schedule",
            ):
                if key in payload and isinstance(payload[key], list):
                    setattr(self, key, payload[key])
            if isinstance(payload.get("nutrition_goals"), dict):
                self.nutrition_goals = {
                    **DEFAULT_NUTRITION_GOALS,
                    **payload["nutrition_goals"],
                }
            if isinstance(payload.get("settings"), dict):
                imported_settings = payload["settings"]
                imported_profile = imported_settings.get("profile", {})
                imported_rewards = dict(imported_settings.get("xp_rewards", {}))
                if not imported_rewards:
                    imported_rewards = dict(imported_profile.get("xp_rewards", {}))
                imported_rewards = {
                    key: value
                    for key, value in imported_rewards.items()
                    if key in DEFAULT_XP_REWARDS
                }
                self.settings = {
                    **default_settings(),
                    **imported_settings,
                    "profile": {
                        **default_settings()["profile"],
                        **imported_profile,
                    },
                    "xp_rewards": {
                        **DEFAULT_XP_REWARDS,
                        **imported_rewards,
                    },
                    "xp_offset": max(
                        0,
                        int(
                            imported_settings.get(
                                "xp_offset", imported_profile.get("xp_offset", 0)
                            )
                            or 0
                        ),
                    ),
                }
                if "xp_rewards" in imported_profile:
                    self.settings["profile"]["xp_rewards"] = {
                        **DEFAULT_XP_REWARDS,
                        **imported_rewards,
                    }
                if "xp_balance" not in imported_settings:
                    self.settings["xp_balance"] = max(
                        0, self._legacy_raw_xp() - self.settings["xp_offset"]
                    )
                    self.settings["xp_awards"] = self._legacy_award_markers()
            self.weekly_schedule = [
                item
                for item in self.weekly_schedule
                if not str(item.get("id", "")).startswith("schedule_steps_")
                and str(item.get("title", "")).strip().lower()
                not in {"20k steps", "20,000 steps"}
            ]
            self.save()

    def update_settings(self, changes: dict) -> dict:
        with self.lock:
            profile = changes.get("profile")
            if isinstance(profile, dict):
                self.settings["profile"] = {
                    **self.settings.get("profile", {}),
                    **profile,
                }
            if "usda_api_key" in changes:
                key = str(changes["usda_api_key"]).strip()
                self.settings["usda_api_key"] = key or "DEMO_KEY"
            rewards = changes.get("xp_rewards")
            if isinstance(rewards, dict):
                validated = {}
                for name, default in DEFAULT_XP_REWARDS.items():
                    try:
                        value = int(rewards.get(name, self.settings["xp_rewards"].get(name, default)))
                    except (TypeError, ValueError) as error:
                        raise ValueError("XP rewards must be whole numbers.") from error
                    if value < 0 or value > 10000:
                        raise ValueError("XP rewards must be between 0 and 10,000.")
                    validated[name] = value
                self.settings["xp_rewards"] = validated
            if "xp_offset" in changes:
                try:
                    offset = int(changes["xp_offset"])
                except (TypeError, ValueError) as error:
                    raise ValueError("XP reset value must be a whole number.") from error
                self.settings["xp_offset"] = max(0, offset)
            if changes.get("reset_xp"):
                self.settings["xp_balance"] = 0
                self.settings["xp_awards"] = {}
            self.save()
            return self.settings


def validate_workout(body: dict, store: HabitStore) -> dict:
    exercise_id = str(body.get("exercise_id", ""))
    if not store.get_exercise(exercise_id):
        raise ValueError("Choose an exercise.")
    workout_date = str(body.get("date", ""))
    try:
        date.fromisoformat(workout_date)
    except ValueError as error:
        raise ValueError("Choose a valid workout date.") from error
    weight = parse_number(body.get("weight", 0))
    sets = int(body.get("sets", 0))
    reps = int(body.get("reps", 0))
    if sets <= 0 or reps <= 0:
        raise ValueError("Sets and reps must be greater than zero.")
    return {
        "exercise_id": exercise_id,
        "date": workout_date,
        "weight": weight,
        "sets": sets,
        "reps": reps,
        "notes": str(body.get("notes", "")).strip(),
    }


def validate_workout_day(body: dict, store: HabitStore) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise ValueError("Give this workout day a name.")
    exercise_ids = []
    for exercise_id in body.get("exercise_ids", []):
        exercise_id = str(exercise_id)
        if store.get_exercise(exercise_id) and exercise_id not in exercise_ids:
            exercise_ids.append(exercise_id)
    if not exercise_ids:
        raise ValueError("Add at least one exercise to this workout day.")
    return {"name": name, "exercise_ids": exercise_ids}


def validate_workout_day_log(body: dict, store: HabitStore) -> tuple[str, list[dict]]:
    workout_day_id = str(body.get("workout_day_id", ""))
    workout_day = store.get_workout_day(workout_day_id)
    if not workout_day:
        raise ValueError("Workout day not found.")
    workout_date = str(body.get("date", ""))
    try:
        date.fromisoformat(workout_date)
    except ValueError as error:
        raise ValueError("Choose a valid workout date.") from error
    rows = []
    allowed = set(workout_day["exercise_ids"])
    for row in body.get("exercises", []):
        if str(row.get("exercise_id", "")) not in allowed:
            continue
        rows.append(
            validate_workout(
                {**row, "date": workout_date},
                store,
            )
        )
    if not rows:
        raise ValueError("Add values for at least one exercise.")
    return workout_day_id, rows


def validate_food(body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise ValueError("Give this food a name.")
    nutrients = {}
    supplied = body.get("nutrients", {})
    for key in NUTRIENT_KEYS:
        nutrients[key] = parse_number(supplied.get(key, 0))
    return {
        "name": name,
        "serving_name": "100 g",
        "nutrients": nutrients,
        "barcode": re.sub(r"\D", "", str(body.get("barcode", ""))),
        "brand": str(body.get("brand", "")).strip(),
        "quantity": str(body.get("quantity", "")).strip(),
        "image_url": str(body.get("image_url", "")).strip(),
        "source": str(body.get("source", "")).strip(),
        "source_url": str(body.get("source_url", "")).strip(),
    }


def validate_food_entry(body: dict, store: HabitStore) -> dict:
    food_id = str(body.get("food_id", ""))
    if not store.get_food(food_id):
        raise ValueError("Choose a food.")
    entry_date = str(body.get("date", ""))
    try:
        date.fromisoformat(entry_date)
    except ValueError as error:
        raise ValueError("Choose a valid food date.") from error
    amount_g = parse_number(body.get("amount_g", 0))
    if amount_g <= 0:
        raise ValueError("The food amount must be greater than zero.")
    return {
        "food_id": food_id,
        "date": entry_date,
        "amount_g": amount_g,
    }


def validate_nutrition_goals(body: dict) -> dict:
    goals = {}
    for key in NUTRIENT_KEYS:
        goals[key] = parse_number(body.get(key, DEFAULT_NUTRITION_GOALS[key]))
    return goals


def valid_date(value, message: str = "Choose a valid date.") -> str:
    result = str(value or "")
    try:
        date.fromisoformat(result)
    except ValueError as error:
        raise ValueError(message) from error
    return result


def validate_body_entry(body: dict) -> dict:
    result = {
        "date": valid_date(body.get("date")),
        "weight": parse_number(body.get("weight", 0)),
        "body_fat": parse_number(body.get("body_fat", 0)),
        "waist": parse_number(body.get("waist", 0)),
        "chest": parse_number(body.get("chest", 0)),
        "hips": parse_number(body.get("hips", 0)),
        "arm": parse_number(body.get("arm", 0)),
        "note": str(body.get("note", "")).strip(),
        "photo": str(body.get("photo", "")),
    }
    if result["weight"] <= 0:
        raise ValueError("Weight must be greater than zero.")
    if len(result["photo"]) > 4_000_000:
        raise ValueError("That progress photo is too large.")
    return result


def validate_recovery_entry(body: dict) -> dict:
    result = {
        "date": valid_date(body.get("date")),
        "sleep_hours": parse_number(body.get("sleep_hours", 0)),
        "sleep_quality": int(body.get("sleep_quality", 0)),
        "energy": int(body.get("energy", 0)),
        "soreness": int(body.get("soreness", 0)),
        "stress": int(body.get("stress", 0)),
        "mood": int(body.get("mood", 0)),
        "note": str(body.get("note", "")).strip(),
    }
    if result["sleep_hours"] > 24:
        raise ValueError("Sleep hours must be between 0 and 24.")
    for key in ("sleep_quality", "energy", "soreness", "stress", "mood"):
        if result[key] < 1 or result[key] > 5:
            raise ValueError("Recovery ratings must be from 1 to 5.")
    return result


def validate_meal(body: dict, store: HabitStore) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise ValueError("Give this meal or recipe a name.")
    items = []
    for row in body.get("items", []):
        food_id = str(row.get("food_id", ""))
        amount_g = parse_number(row.get("amount_g", 0))
        if store.get_food(food_id) and amount_g > 0:
            items.append({"food_id": food_id, "amount_g": amount_g})
    if not items:
        raise ValueError("Add at least one food to this meal.")
    return {
        "name": name,
        "items": items,
        "servings": max(1, int(body.get("servings", 1))),
        "instructions": str(body.get("instructions", "")).strip(),
    }


def validate_planner_event(body: dict) -> dict:
    event_type = str(body.get("type", "note"))
    if event_type not in ("workout", "meal", "habit", "note"):
        raise ValueError("Choose a valid planner type.")
    title = str(body.get("title", "")).strip()
    if not title:
        raise ValueError("Give this planner item a title.")
    reminder = str(body.get("reminder", "")).strip()
    if reminder and not re.fullmatch(r"\d{2}:\d{2}", reminder):
        raise ValueError("Choose a valid reminder time.")
    start = str(body.get("start", reminder)).strip()
    end = str(body.get("end", "")).strip()
    time_pattern = r"(?:[01]\d|2[0-3]):[0-5]\d"
    if start and not re.fullmatch(time_pattern, start):
        raise ValueError("Choose a valid start time.")
    if end and not re.fullmatch(time_pattern, end):
        raise ValueError("Choose a valid end time.")
    if start and end and end <= start:
        raise ValueError("The end time must be after the start time.")
    return {
        "date": valid_date(body.get("date")),
        "type": event_type,
        "title": title,
        "reference_id": str(body.get("reference_id", "")),
        "reminder": reminder or start,
        "start": start,
        "end": end,
        "done": bool(body.get("done", False)),
        "note": str(body.get("note", "")).strip(),
    }


def validate_weekly_schedule_item(body: dict) -> dict:
    title = str(body.get("title", "")).strip()
    if not title:
        raise ValueError("Give this repeating activity a title.")
    try:
        weekday = int(body.get("weekday", -1))
    except (TypeError, ValueError) as error:
        raise ValueError("Choose a day of the week.") from error
    if weekday < 0 or weekday > 6:
        raise ValueError("Choose a day of the week.")
    event_type = str(body.get("type", "note"))
    if event_type not in ("workout", "meal", "habit", "note"):
        raise ValueError("Choose a valid activity type.")
    start = str(body.get("start", "")).strip()
    end = str(body.get("end", "")).strip()
    time_pattern = r"(?:[01]\d|2[0-3]):[0-5]\d"
    if start and not re.fullmatch(time_pattern, start):
        raise ValueError("Choose a valid start time.")
    if end and not re.fullmatch(time_pattern, end):
        raise ValueError("Choose a valid end time.")
    if end and not start:
        raise ValueError("Add a start time before the end time.")
    if start and end and end <= start:
        raise ValueError("The end time must be after the start time.")
    color = str(body.get("color", DEFAULT_COLORS[0])).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = DEFAULT_COLORS[0]
    return {
        "weekday": weekday,
        "title": title,
        "start": start,
        "end": end,
        "type": event_type,
        "color": color,
    }


def validate_shopping_item(body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise ValueError("Give this shopping item a name.")
    return {
        "name": name,
        "amount": str(body.get("amount", "")).strip(),
        "checked": bool(body.get("checked", False)),
    }


def validate_journal_entry(body: dict) -> dict:
    entry_date = valid_date(body.get("date"))
    title = str(body.get("title", "")).strip() or "Daily reflection"
    content = str(body.get("content", "")).strip()
    if not content:
        raise ValueError("Write something before saving your journal entry.")
    mood = int(body.get("mood", 3))
    if mood < 1 or mood > 5:
        raise ValueError("Mood must be between 1 and 5.")
    return {
        "date": entry_date,
        "title": title[:100],
        "content": content[:10000],
        "mood": mood,
        "gratitude": str(body.get("gratitude", "")).strip()[:1000],
        "win": str(body.get("win", "")).strip()[:1000],
    }


def validate_goal(body: dict) -> dict:
    title = str(body.get("title", "")).strip()
    if not title:
        raise ValueError("Give this goal a title.")
    category = str(body.get("category", "personal"))
    if category not in ("body", "strength", "running", "nutrition", "habit", "personal"):
        category = "personal"
    deadline = str(body.get("deadline", "")).strip()
    if deadline:
        deadline = valid_date(deadline, "Choose a valid goal deadline.")
    target_value = parse_number(body.get("target_value", 0))
    current_value = parse_number(body.get("current_value", 0))
    return {
        "title": title[:100],
        "category": category,
        "target_value": target_value,
        "current_value": current_value,
        "unit": str(body.get("unit", "")).strip()[:30],
        "deadline": deadline,
        "completed": bool(body.get("completed", False)),
        "notes": str(body.get("notes", "")).strip()[:1000],
    }


def validate_kickboxing_session(body: dict) -> dict:
    score = max(0, int(body.get("score", 0)))
    attempts = max(1, int(body.get("attempts", 1)))
    hits = max(0, min(attempts, int(body.get("hits", 0))))
    belt = str(body.get("belt", "White")).strip()[:30] or "White"
    return {
        "date": valid_date(body.get("date")),
        "score": score,
        "attempts": attempts,
        "hits": hits,
        "accuracy": round(hits / attempts * 100, 1),
        "belt": belt,
        "mode": str(body.get("mode", "rhythm")).strip()[:30],
        "combo": str(body.get("combo", "")).strip()[:300],
    }


class HabitHandler(BaseHTTPRequestHandler):
    store: HabitStore
    static_root: Path
    off_cache: dict[str, tuple[float, dict]] = {}

    def log_message(self, _format: str, *_args) -> None:
        return

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _touch(self) -> None:
        self.server.last_seen = time.monotonic()

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status)

    def _open_food_facts(self, url: str) -> dict:
        cached = self.off_cache.get(url)
        if cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        payload = fetch_open_food_facts(url)
        self.off_cache[url] = (time.monotonic(), payload)
        return payload

    def _authorized(self, parsed) -> bool:
        if self.client_address[0] in ("127.0.0.1", "::1"):
            return True
        supplied = self.headers.get("X-Habitline-Token", "")
        if not supplied:
            supplied = (parse_qs(parsed.query).get("token") or [""])[0]
        return supplied == self.store.settings.get("sync_token")

    def _require_api_access(self, parsed) -> bool:
        if parsed.path.startswith("/api/") and not self._authorized(parsed):
            self._error("This phone link is missing or no longer valid.", 403)
            return False
        return True

    def do_GET(self) -> None:
        self._touch()
        parsed = urlparse(self.path)
        path = parsed.path
        if not self._require_api_access(parsed):
            return
        if path == "/api/ping":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/api/version":
            self._send_json({"name": APP_NAME, "version": APP_VERSION})
            return
        if path == "/api/habits":
            self._send_json({"habits": self.store.habits})
            return
        if path == "/api/data":
            self._send_json(self.store.all_data())
            return
        if path == "/api/sync-info":
            network_ip = local_network_ip()
            token = self.store.settings.get("sync_token", "")
            self._send_json(
                {
                    "phone_url": f"http://{network_ip}:{self.server.server_port}/?token={token}",
                    "network_ip": network_ip,
                    "port": self.server.server_port,
                    "requires_same_wifi": True,
                }
            )
            return
        if path == "/api/export":
            body = json.dumps(self.store.all_data(), indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="habitline-backup-{date.today().isoformat()}.json"',
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/foods/search":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            if len(query) < 2:
                self._error("Enter at least two characters to search.")
                return
            products = [
                {
                    **food,
                    "local_id": food["id"],
                    "source": food.get("source") or "Habitline offline food library",
                    "source_url": food.get("source_url", ""),
                }
                for food in search_offline_foods(self.store.foods, query)
            ]
            self._send_json(
                {
                    "products": products,
                    "source": "Habitline offline food library",
                    "offline": True,
                }
            )
            return
        if path == "/api/usda/search":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            if len(query) < 2:
                self._error("Enter at least two characters to search.")
                return
            try:
                products = fetch_usda_foods(
                    query, self.store.settings.get("usda_api_key", "DEMO_KEY")
                )
                self._send_json(
                    {
                        "products": products,
                        "source": "USDA FoodData Central",
                        "source_url": "https://fdc.nal.usda.gov/",
                    }
                )
            except ValueError as error:
                fallback = [
                    {
                        **food,
                        "local_id": food["id"],
                        "source": "Habitline offline food library",
                        "source_url": "",
                    }
                    for food in search_offline_foods(self.store.foods, query, 12)
                ]
                if fallback:
                    self._send_json(
                        {
                            "products": fallback,
                            "source": "Habitline built-in foods",
                            "warning": str(error),
                        }
                    )
                else:
                    self._error(str(error), 503)
            return
        usda_barcode_match = re.fullmatch(r"/api/usda/barcode/(\d{8,14})", path)
        if usda_barcode_match:
            barcode = usda_barcode_match.group(1)
            local = next(
                (food for food in self.store.foods if food.get("barcode") == barcode),
                None,
            )
            if local:
                self._send_json(
                    {
                        "product": {
                            **local,
                            "local_id": local["id"],
                            "source": local.get("source")
                            or "Habitline offline food library",
                        }
                    }
                )
                return
            try:
                products = fetch_usda_foods(
                    barcode,
                    self.store.settings.get("usda_api_key", "DEMO_KEY"),
                    25,
                    branded_only=True,
                )
                exact = next(
                    (product for product in products if product["barcode"] == barcode),
                    None,
                )
                if not exact:
                    self._error("USDA did not have an exact match for that barcode.", 404)
                    return
                self._send_json({"product": exact})
            except ValueError as error:
                self._error(str(error), 503)
            return
        barcode_match = re.fullmatch(
            r"/api/open-food-facts/barcode/(\d{8,14})", path
        )
        if barcode_match:
            try:
                barcode = barcode_match.group(1)
                fields = urlencode({"fields": OPEN_FOOD_FACTS_FIELDS})
                payload = self._open_food_facts(
                    f"{OPEN_FOOD_FACTS_BASE}/api/v2/product/{barcode}.json?{fields}"
                )
                product = open_food_facts_product(payload.get("product") or {})
                if not product:
                    self._error("No product was found for that barcode.", 404)
                    return
                self._send_json({"product": product})
            except ValueError as error:
                self._error(str(error), 503)
            return
        if path == "/api/open-food-facts/search":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            if len(query) < 2:
                self._error("Enter at least two characters to search.")
                return
            try:
                parameters = urlencode(
                    {
                        "search_terms": query,
                        "search_simple": 1,
                        "action": "process",
                        "json": 1,
                        "page_size": 12,
                        "fields": OPEN_FOOD_FACTS_FIELDS,
                    }
                )
                payload = self._open_food_facts(
                    f"{OPEN_FOOD_FACTS_BASE}/cgi/search.pl?{parameters}"
                )
            except ValueError:
                fallback_parameters = urlencode(
                    {
                        "categories_tags_en": query,
                        "page_size": 12,
                        "fields": OPEN_FOOD_FACTS_FIELDS,
                    }
                )
                try:
                    payload = self._open_food_facts(
                        f"{OPEN_FOOD_FACTS_BASE}/api/v2/search?{fallback_parameters}"
                    )
                except ValueError as error:
                    self._error(str(error), 503)
                    return
            try:
                products = [
                    product
                    for raw_product in payload.get("products", [])
                    if (product := open_food_facts_product(raw_product))
                ]
                self._send_json(
                    {
                        "products": products,
                        "source": "Open Food Facts",
                        "source_url": OPEN_FOOD_FACTS_BASE,
                    }
                )
            except ValueError as error:
                self._error(str(error), 503)
            return
        static_files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/manifest.json": ("manifest.json", "application/manifest+json"),
            "/service-worker.js": ("service-worker.js", "text/javascript; charset=utf-8"),
            "/icon-192.png": ("icon-192.png", "image/png"),
            "/icon-512.png": ("icon-512.png", "image/png"),
        }
        if path in static_files:
            filename, content_type = static_files[path]
            target = self.static_root / filename
            if not target.exists():
                self._error("Not found.", 404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header(
                "Cache-Control",
                "no-store" if filename == "index.html" else "public, max-age=3600",
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self._error("Not found.", 404)

    def do_POST(self) -> None:
        self._touch()
        parsed = urlparse(self.path)
        if not self._require_api_access(parsed):
            return
        path = parsed.path
        try:
            body = self._json_body()
            if path == "/api/habits":
                habit_type = body.get("type")
                name = str(body.get("name", "")).strip()
                if not name:
                    raise ValueError("Give this habit a name.")
                if habit_type not in ("check", "number"):
                    raise ValueError("Choose checkbox or number goal.")
                target = (
                    parse_number(body.get("target", 1))
                    if habit_type == "number"
                    else 1
                )
                if target <= 0:
                    raise ValueError("The target must be greater than zero.")
                habit = {
                    "id": uuid.uuid4().hex,
                    "name": name,
                    "type": habit_type,
                    "target": target,
                    "unit": str(body.get("unit", "")).strip()
                    if habit_type == "number"
                    else "",
                    "color": str(body.get("color") or DEFAULT_COLORS[0]),
                    "entries": {},
                }
                self.store.add(habit)
                self._send_json(habit, 201)
                return
            if path == "/api/exercises":
                name = str(body.get("name", "")).strip()
                if not name:
                    raise ValueError("Give this exercise a name.")
                exercise = {
                    "id": uuid.uuid4().hex,
                    "name": name,
                    "unit": str(body.get("unit", "kg")).strip() or "kg",
                    "color": str(body.get("color") or DEFAULT_COLORS[0]),
                    "muscle_group": str(
                        body.get("muscle_group", "Other")
                    ).strip()
                    or "Other",
                    "secondary_muscles": [
                        str(value)
                        for value in body.get("secondary_muscles", [])
                        if str(value).strip()
                    ],
                }
                self.store.add_exercise(exercise)
                self._send_json(exercise, 201)
                return
            if path == "/api/workouts":
                workout = {
                    "id": uuid.uuid4().hex,
                    **validate_workout(body, self.store),
                }
                self.store.add_workout(workout)
                reward_key = self.store._workout_reward_key(workout)
                xp_change = self.store.set_xp_award(
                    f"workout:{workout['id']}",
                    self.store.settings["xp_rewards"][reward_key],
                )
                self._send_json(
                    {
                        **workout,
                        "xp_change": xp_change,
                        "xp_total": self.store.settings["xp_balance"],
                        "xp_reward_key": reward_key,
                    },
                    201,
                )
                return
            if path == "/api/workout-days":
                workout_day = {
                    "id": uuid.uuid4().hex,
                    **validate_workout_day(body, self.store),
                }
                self.store.add_workout_day(workout_day)
                self._send_json(workout_day, 201)
                return
            if path == "/api/workout-day-log":
                workout_day_id, rows = validate_workout_day_log(body, self.store)
                session_id = uuid.uuid4().hex
                workouts = []
                with self.store.lock:
                    for row in rows:
                        workout = {
                            "id": uuid.uuid4().hex,
                            **row,
                            "workout_day_id": workout_day_id,
                            "session_id": session_id,
                        }
                        self.store.workouts.append(workout)
                        workouts.append(workout)
                    self.store.save()
                xp_change = 0
                for workout in workouts:
                    reward_key = self.store._workout_reward_key(workout)
                    xp_change += self.store.set_xp_award(
                        f"workout:{workout['id']}",
                        self.store.settings["xp_rewards"][reward_key],
                    )
                self._send_json(
                    {
                        "session_id": session_id,
                        "workouts": workouts,
                        "xp_change": xp_change,
                        "xp_total": self.store.settings["xp_balance"],
                        "xp_reward_keys": [
                            self.store._workout_reward_key(workout)
                            for workout in workouts
                        ],
                    },
                    201,
                )
                return
            if path == "/api/foods":
                barcode = re.sub(r"\D", "", str(body.get("barcode", "")))
                if barcode:
                    existing = next(
                        (
                            food
                            for food in self.store.foods
                            if food.get("barcode") == barcode
                        ),
                        None,
                    )
                    if existing:
                        self._send_json(existing)
                        return
                food = {"id": uuid.uuid4().hex, **validate_food(body)}
                self.store.add_food(food)
                self._send_json(food, 201)
                return
            if path == "/api/food-entries":
                entry = {
                    "id": uuid.uuid4().hex,
                    **validate_food_entry(body, self.store),
                }
                self.store.add_food_entry(entry)
                self._send_json(entry, 201)
                return
            collection_routes = {
                "/api/body-entries": ("body_entries", validate_body_entry),
                "/api/recovery-entries": (
                    "recovery_entries",
                    validate_recovery_entry,
                ),
                "/api/meals": (
                    "meals",
                    lambda value: validate_meal(value, self.store),
                ),
                "/api/planner-events": ("planner_events", validate_planner_event),
                "/api/shopping-items": ("shopping_items", validate_shopping_item),
                "/api/journal-entries": (
                    "journal_entries",
                    validate_journal_entry,
                ),
                "/api/goals": ("goals", validate_goal),
                "/api/kickboxing-sessions": (
                    "kickboxing_sessions",
                    validate_kickboxing_session,
                ),
                "/api/schedule-items": (
                    "weekly_schedule",
                    validate_weekly_schedule_item,
                ),
            }
            if path in collection_routes:
                collection, validator = collection_routes[path]
                item = {"id": uuid.uuid4().hex, **validator(body)}
                xp_amount = 0
                xp_key = ""
                if path == "/api/journal-entries":
                    xp_amount = self.store.settings["xp_rewards"]["journal"]
                    xp_key = f"journal:{item['id']}"
                elif path == "/api/goals" and item.get("completed"):
                    xp_amount = self.store.settings["xp_rewards"]["goal"]
                    xp_key = f"goal:{item['id']}"
                elif (
                    path == "/api/kickboxing-sessions"
                    and item.get("mode") == "audio-drill"
                ):
                    xp_amount = kickboxing_grade_xp(item.get("belt", "")) * int(
                        item.get("attempts", 1)
                    )
                    item["xp_awarded"] = xp_amount
                    xp_key = f"kickboxing:{item['id']}"
                self.store.add_item(collection, item)
                xp_change = (
                    self.store.set_xp_award(xp_key, xp_amount)
                    if xp_key
                    else 0
                )
                self._send_json(
                    {
                        **item,
                        "xp_change": xp_change,
                        "xp_total": self.store.settings["xp_balance"],
                    },
                    201,
                )
                return
            restore_match = re.fullmatch(r"/api/trash/([a-f0-9]+)/restore", path)
            if restore_match:
                item = self.store.restore_item(restore_match.group(1))
                if not item:
                    self._error("Deleted item not found.", 404)
                    return
                self._send_json(item)
                return
            if path == "/api/import":
                self.store.import_data(body)
                self._send_json(self.store.all_data())
                return
            self._error("Not found.", 404)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._error(str(error))

    def do_PUT(self) -> None:
        self._touch()
        parsed = urlparse(self.path)
        if not self._require_api_access(parsed):
            return
        path = parsed.path
        entry_match = re.fullmatch(
            r"/api/habits/([a-f0-9]+)/entries/(\d{4}-\d{2}-\d{2})", path
        )
        habit_match = re.fullmatch(r"/api/habits/([a-f0-9]+)", path)
        exercise_match = re.fullmatch(r"/api/exercises/([a-f0-9]+)", path)
        workout_match = re.fullmatch(r"/api/workouts/([a-f0-9]+)", path)
        workout_day_match = re.fullmatch(r"/api/workout-days/([a-f0-9]+)", path)
        food_match = re.fullmatch(r"/api/foods/([a-z0-9_]+)", path)
        food_entry_match = re.fullmatch(r"/api/food-entries/([a-f0-9]+)", path)
        generic_match = re.fullmatch(
            r"/api/(body-entries|recovery-entries|meals|planner-events|shopping-items|journal-entries|goals|kickboxing-sessions|schedule-items)/([a-z0-9_]+)",
            path,
        )
        try:
            body = self._json_body()
            if path == "/api/nutrition-goals":
                self._send_json(
                    self.store.update_nutrition_goals(
                        validate_nutrition_goals(body)
                    )
                )
                return
            if path == "/api/settings":
                profile = body.get("profile", {})
                if profile:
                    age = int(profile.get("age", 0) or 0)
                    if age and not 13 <= age <= 100:
                        raise ValueError("Age must be between 13 and 100.")
                    profile["age"] = age
                    profile["body_weight"] = parse_number(
                        profile.get("body_weight", 0)
                    )
                    profile["weight_unit"] = (
                        "lb" if profile.get("weight_unit") == "lb" else "kg"
                    )
                    profile["height_cm"] = parse_number(
                        profile.get("height_cm", 0)
                    )
                    profile["sex"] = (
                        "female" if profile.get("sex") == "female" else "male"
                    )
                    profile["activity_level"] = (
                        profile.get("activity_level")
                        if profile.get("activity_level")
                        in ("inactive", "low", "active", "very")
                        else "active"
                    )
                    profile["goal_type"] = (
                        profile.get("goal_type")
                        if profile.get("goal_type")
                        in ("lose", "maintain", "recomposition", "gain", "performance")
                        else "recomposition"
                    )
                    profile["training_experience"] = (
                        profile.get("training_experience")
                        if profile.get("training_experience")
                        in ("beginner", "intermediate", "advanced")
                        else "beginner"
                    )
                    profile["auto_nutrition"] = bool(
                        profile.get("auto_nutrition", True)
                    )
                self._send_json(self.store.update_settings(body))
                return
            if entry_match:
                habit_id, day = entry_match.groups()
                habit = self.store.get(habit_id)
                if not habit:
                    self._error("Habit not found.", 404)
                    return
                value = body.get("value")
                if value is not None:
                    value = bool(value) if habit["type"] == "check" else parse_number(value)
                updated = self.store.set_entry(habit_id, day, value)
                xp_change = self.store.set_xp_award(
                    f"habit:{habit_id}:{day}",
                    self.store.settings["xp_rewards"]["habit"],
                    self.store._habit_met(habit, value),
                )
                self._send_json(
                    {
                        "habit": updated,
                        "xp_change": xp_change,
                        "xp_total": self.store.settings["xp_balance"],
                    }
                )
                return
            if habit_match:
                habit_id = habit_match.group(1)
                current = self.store.get(habit_id)
                if not current:
                    self._error("Habit not found.", 404)
                    return
                habit_type = body.get("type", current["type"])
                if habit_type not in ("check", "number"):
                    raise ValueError("Choose checkbox or number goal.")
                name = str(body.get("name", current["name"])).strip()
                if not name:
                    raise ValueError("Give this habit a name.")
                target = (
                    parse_number(body.get("target", current["target"]))
                    if habit_type == "number"
                    else 1
                )
                if target <= 0:
                    raise ValueError("The target must be greater than zero.")
                changes = {
                    "name": name,
                    "type": habit_type,
                    "target": target,
                    "unit": str(body.get("unit", current.get("unit", ""))).strip()
                    if habit_type == "number"
                    else "",
                    "color": str(body.get("color", current["color"])),
                }
                if habit_type != current["type"]:
                    changes["entries"] = {}
                    self.store.revoke_xp_prefix(f"habit:{habit_id}:")
                self._send_json(self.store.update(habit_id, changes))
                return
            if exercise_match:
                exercise_id = exercise_match.group(1)
                current = self.store.get_exercise(exercise_id)
                if not current:
                    self._error("Exercise not found.", 404)
                    return
                name = str(body.get("name", current["name"])).strip()
                if not name:
                    raise ValueError("Give this exercise a name.")
                changes = {
                    "name": name,
                    "unit": str(body.get("unit", current.get("unit", "kg"))).strip()
                    or "kg",
                    "color": str(body.get("color", current["color"])),
                    "muscle_group": str(
                        body.get("muscle_group", current.get("muscle_group", "Other"))
                    ).strip()
                    or "Other",
                    "secondary_muscles": [
                        str(value)
                        for value in body.get(
                            "secondary_muscles",
                            current.get("secondary_muscles", []),
                        )
                        if str(value).strip()
                    ],
                }
                self._send_json(self.store.update_exercise(exercise_id, changes))
                return
            if workout_match:
                workout_id = workout_match.group(1)
                current = self.store.get_workout(workout_id)
                if not current:
                    self._error("Workout not found.", 404)
                    return
                merged = {**current, **body}
                updated = self.store.update_workout(
                    workout_id, validate_workout(merged, self.store)
                )
                reward_key = self.store._workout_reward_key(updated)
                xp_change = self.store.set_xp_award(
                    f"workout:{workout_id}",
                    self.store.settings["xp_rewards"][reward_key],
                )
                self._send_json(
                    {
                        **updated,
                        "xp_change": xp_change,
                        "xp_total": self.store.settings["xp_balance"],
                        "xp_reward_key": reward_key,
                    }
                )
                return
            if workout_day_match:
                workout_day_id = workout_day_match.group(1)
                if not self.store.get_workout_day(workout_day_id):
                    self._error("Workout day not found.", 404)
                    return
                self._send_json(
                    self.store.update_workout_day(
                        workout_day_id,
                        validate_workout_day(body, self.store),
                    )
                )
                return
            if food_match:
                food_id = food_match.group(1)
                if not self.store.get_food(food_id):
                    self._error("Food not found.", 404)
                    return
                self._send_json(
                    self.store.update_food(food_id, validate_food(body))
                )
                return
            if food_entry_match:
                entry_id = food_entry_match.group(1)
                current = self.store.get_food_entry(entry_id)
                if not current:
                    self._error("Food entry not found.", 404)
                    return
                self._send_json(
                    self.store.update_food_entry(
                        entry_id,
                        validate_food_entry({**current, **body}, self.store),
                    )
                )
                return
            if generic_match:
                route, item_id = generic_match.groups()
                configurations = {
                    "body-entries": ("body_entries", validate_body_entry),
                    "recovery-entries": (
                        "recovery_entries",
                        validate_recovery_entry,
                    ),
                    "meals": (
                        "meals",
                        lambda value: validate_meal(value, self.store),
                    ),
                    "planner-events": (
                        "planner_events",
                        validate_planner_event,
                    ),
                    "shopping-items": (
                        "shopping_items",
                        validate_shopping_item,
                    ),
                    "journal-entries": (
                        "journal_entries",
                        validate_journal_entry,
                    ),
                    "goals": ("goals", validate_goal),
                    "kickboxing-sessions": (
                        "kickboxing_sessions",
                        validate_kickboxing_session,
                    ),
                    "schedule-items": (
                        "weekly_schedule",
                        validate_weekly_schedule_item,
                    ),
                }
                collection, validator = configurations[route]
                current = next(
                    (
                        row
                        for row in self.store.collection(collection)
                        if row["id"] == item_id
                    ),
                    None,
                )
                if not current:
                    self._error("Item not found.", 404)
                    return
                updated = self.store.update_item(
                    collection, item_id, validator({**current, **body})
                )
                xp_change = 0
                if route == "goals":
                    xp_change = self.store.set_xp_award(
                        f"goal:{item_id}",
                        self.store.settings["xp_rewards"]["goal"],
                        bool(updated.get("completed")),
                    )
                self._send_json(
                    {
                        **updated,
                        "xp_change": xp_change,
                        "xp_total": self.store.settings["xp_balance"],
                    }
                )
                return
            self._error("Not found.", 404)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._error(str(error))

    def do_DELETE(self) -> None:
        self._touch()
        parsed = urlparse(self.path)
        if not self._require_api_access(parsed):
            return
        path = parsed.path
        habit_match = re.fullmatch(r"/api/habits/([a-f0-9]+)", path)
        exercise_match = re.fullmatch(r"/api/exercises/([a-f0-9]+)", path)
        workout_match = re.fullmatch(r"/api/workouts/([a-f0-9]+)", path)
        workout_day_match = re.fullmatch(r"/api/workout-days/([a-f0-9]+)", path)
        food_match = re.fullmatch(r"/api/foods/([a-z0-9_]+)", path)
        food_entry_match = re.fullmatch(r"/api/food-entries/([a-f0-9]+)", path)
        generic_match = re.fullmatch(
            r"/api/(body-entries|recovery-entries|meals|planner-events|shopping-items|journal-entries|goals|kickboxing-sessions|schedule-items)/([a-z0-9_]+)",
            path,
        )
        if habit_match and self.store.get(habit_match.group(1)):
            habit_id = habit_match.group(1)
            self.store.revoke_xp_prefix(f"habit:{habit_id}:")
            self.store.delete(habit_id)
            self._send_json({"deleted": True})
            return
        if exercise_match and self.store.delete_exercise(exercise_match.group(1)):
            self._send_json({"deleted": True})
            return
        if workout_match and self.store.get_workout(workout_match.group(1)):
            workout_id = workout_match.group(1)
            self.store.set_xp_award(f"workout:{workout_id}", 0, False)
            self.store.delete_workout(workout_id)
            self._send_json({"deleted": True})
            return
        if workout_day_match and self.store.delete_workout_day(
            workout_day_match.group(1)
        ):
            self._send_json({"deleted": True})
            return
        if food_match and self.store.delete_food(food_match.group(1)):
            self._send_json({"deleted": True})
            return
        if food_entry_match and self.store.delete_food_entry(
            food_entry_match.group(1)
        ):
            self._send_json({"deleted": True})
            return
        if generic_match:
            route, item_id = generic_match.groups()
            collection = (
                "weekly_schedule"
                if route == "schedule-items"
                else route.replace("-", "_")
            )
            current = next(
                (
                    item
                    for item in self.store.collection(collection)
                    if item.get("id") == item_id
                ),
                None,
            )
            if current:
                prefix = {
                    "journal-entries": "journal:",
                    "goals": "goal:",
                    "kickboxing-sessions": "kickboxing:",
                }.get(route)
                if prefix:
                    self.store.set_xp_award(f"{prefix}{item_id}", 0, False)
            if current and self.store.delete_item(collection, item_id):
                self._send_json(
                    {"deleted": True, "trash": self.store.trash[-1]}
                )
                return
        self._error("Item not found.", 404)


def run_server(
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    data_root: Path | None = None,
) -> None:
    app_root = Path(__file__).resolve().parent
    data_root = data_root or app_root / "data"
    HabitHandler.store = HabitStore(data_root / "habits.json")
    HabitHandler.static_root = app_root

    occupied_by_other_version = False
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/version", timeout=0.4) as response:
            running = json.loads(response.read().decode("utf-8"))
        if running.get("name") == APP_NAME and running.get("version") == APP_VERSION:
            if open_browser:
                webbrowser.open(f"http://127.0.0.1:{port}")
            return
        occupied_by_other_version = True
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    server = None
    selected_port = port
    first_candidate = port + 1 if occupied_by_other_version else port
    for candidate in range(first_candidate, port + 21):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", candidate), HabitHandler)
            selected_port = candidate
            break
        except OSError:
            continue
    if server is None:
        if open_browser:
            webbrowser.open(f"http://127.0.0.1:{port}")
        return
    url = f"http://127.0.0.1:{selected_port}"
    server.last_seen = time.monotonic()

    def stop_when_unused() -> None:
        while True:
            time.sleep(5)
            if time.monotonic() - server.last_seen > 45:
                server.shutdown()
                return

    threading.Thread(target=stop_when_unused, daemon=True).start()
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    print(f"{APP_NAME} is running at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Habitline habit tracker.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    arguments = parser.parse_args()
    run_server(arguments.port, not arguments.no_browser, arguments.data_dir)


if __name__ == "__main__":
    main()
