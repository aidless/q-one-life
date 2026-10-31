#!/usr/bin/env python3
"""Generate the 1000+ metric specification catalog.

Layered as domain -> category -> real members.  Every member is a real,
nameable item (nutrient, exercise, expense line, PANAS item, school subject,
...) rather than a synthetic label.  Each category carries one or more
measurement templates (amount / score / days / ...) that are themselves real
measures.  The generator asserts uniqueness of ``domain:metric`` keys and a
total count of at least 1000 before writing ``examples/metric-spec.json``.

Run:  python3 scripts/generate_metric_specs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# A template is (suffix, min, max, direction, unit, target, weight, target_count)
# suffix="" means the metric name is the member name itself (single measure).
T = tuple

CATALOG: dict[str, list[tuple[str, list[T], list[str] | list[tuple[str, float]]]]] = {
    "health": [
        ("vitamins_minerals", [
            ("intake", 0, 2000, "higher", "mg", None, 1.0, 7),
            ("days", 0, 7, "higher", "days", None, 0.8, 7),
        ], [
            "vitamin_a", "vitamin_c", "vitamin_d", "vitamin_e", "vitamin_k",
            "vitamin_b1", "vitamin_b2", "vitamin_b3", "vitamin_b5", "vitamin_b6",
            "vitamin_b9", "vitamin_b12", "calcium", "iron", "zinc", "magnesium",
            "potassium", "sodium", "selenium", "iodine", "copper", "manganese",
            "chromium", "phosphorus", "folate", "choline", "biotin",
        ]),
        ("vitals", [
            ("value", 0, 200, "target", "__member_unit__", None, 1.0, 7),
        ], [
            ("systolic", 120, "mmHg"), ("diastolic", 80, "mmHg"),
            ("resting_heart_rate", 65, "bpm"), ("blood_glucose", 90, "mg/dL"),
            ("body_temperature", 36.5, "degC"), ("blood_oxygen", 98, "pct"),
            ("respiratory_rate", 16, "breaths"), ("waist_circumference", 80, "cm"),
            ("hip_circumference", 95, "cm"), ("bmi", 22, "kg/m2"),
            ("body_fat", 20, "pct"), ("muscle_mass", 40, "kg"),
            ("bone_mass", 2.5, "kg"), ("body_water", 60, "pct"),
            ("visceral_fat", 8, "index"),
        ]),
        ("exercise", [
            ("minutes", 0, 300, "higher", "minutes", None, 1.0, 7),
            ("sessions", 0, 14, "higher", "times", None, 0.7, 7),
        ], [
            "running", "walking", "cycling", "swimming", "strength_training",
            "yoga", "stretching", "hiit", "jump_rope", "rowing", "hiking",
            "pilates", "boxing", "dancing", "badminton", "tennis", "basketball",
            "football", "climbing", "skating", "golf", "table_tennis",
        ]),
        ("body_parts", [
            ("minutes", 0, 120, "higher", "minutes", None, 0.8, 7),
        ], [
            "neck", "shoulders", "lower_back", "wrists", "eyes", "knees",
            "hips", "ankles", "head", "abdomen", "feet", "elbows",
        ]),
        ("food_groups", [
            ("servings", 0, 12, "higher", "servings", None, 0.9, 7),
        ], [
            "grains", "vegetables", "fruits", "protein", "dairy",
            "legumes", "nuts", "oils", "water", "whole_grain", "seafood",
            "eggs", "mushrooms", "soy", "herbs", "fermented", "dark_leafy",
            "berries", "citrus", "whole_foods", "processed_food", "sugary_drink",
        ]),
        ("sleeping", [
            ("hours", 0, 24, "target", "hours", None, 0.9, 7),
        ], [
            ("night_sleep", 8), ("afternoon_nap", 0.5), ("time_to_fall_asleep", 0.25),
            ("time_in_bed", 8), ("night_wakeups", 1), ("bedtime", 23),
            ("wake_time", 7), ("sleep_quality", 8), ("deep_sleep", 1.5),
            ("rem_sleep", 2), ("light_sleep", 4.5), ("sleep_regularity", 0.8),
            ("sleep_environment_score", 8), ("mattress_score", 7), ("pillow_score", 7),
        ]),
    ],
    "finance": [
        ("expenses", [
            ("daily_amount", 0, 1000, "lower", "CNY", None, 1.0, 7),
            ("weekly_days", 0, 7, "lower", "days", None, 0.7, 7),
        ], [
            "dining", "transport", "housing", "utilities", "telecom",
            "entertainment", "education", "medical", "clothing", "daily_goods",
            "travel", "pets", "insurance", "taxes", "gifts", "repairs",
            "beauty", "fitness", "books", "stationery", "express", "housekeeping",
            "medicine", "smoking", "coffee", "takeout", "taxi", "rent",
            "mortgage", "subscriptions", "snacks", "charity",
        ]),
        ("income", [
            ("monthly_amount", 0, 100000, "higher", "CNY", None, 1.0, 30),
            ("months", 0, 12, "higher", "months", None, 0.8, 30),
        ], [
            "salary", "bonus", "part_time", "investment", "rental", "royalty",
            "dividend", "interest", "subsidy", "reimbursement", "writing_fee",
            "teaching", "consulting", "outsourcing", "cashback", "grant",
        ]),
        ("assets", [
            ("amount", 0, 10000000, "higher", "CNY", None, 1.0, 30),
            ("allocation", 0, 1, "higher", "ratio", None, 0.6, 30),
        ], [
            "cash", "demand_deposit", "fixed_deposit", "money_fund", "bond_fund",
            "stock_fund", "index_fund", "stock", "bond", "real_estate",
            "gold", "bitcoin", "pension", "housing_fund", "precious_metal",
        ]),
        ("debts", [
            ("balance", 0, 10000000, "lower", "CNY", None, 1.0, 30),
        ], [
            "credit_card", "mortgage", "car_loan", "consumer_loan", "huabei",
            "jiedai", "baitiao", "student_loan", "pawn", "campus_loan",
        ]),
        ("budget_lines", [
            ("budget", 0, 100000, "target", "CNY", None, 0.8, 30),
            ("actual", 0, 100000, "lower", "CNY", None, 0.8, 30),
        ], [
            ("dining_budget", 2000), ("transport_budget", 500), ("entertainment_budget", 500),
            ("education_budget", 1000), ("housing_budget", 3000), ("utilities_budget", 500),
            ("medical_budget", 300), ("clothing_budget", 300), ("travel_budget", 1000),
            ("misc_budget", 500), ("daily_goods_budget", 500), ("fitness_budget", 200),
            ("subs_budget", 100), ("gift_budget", 200), ("pet_budget", 300),
            ("telecom_budget", 150), ("repairs_budget", 300), ("beauty_budget", 200),
        ]),
    ],
    "learning": [
        ("subjects", [
            ("hours", 0, 8, "higher", "hours", None, 1.0, 7),
            ("mastery", 0, 10, "higher", "score", None, 0.8, 7),
        ], [
            "mathematics", "physics", "chemistry", "biology", "english",
            "chinese", "history", "geography", "politics", "programming",
            "economics", "psychology", "philosophy", "literature", "law",
            "medicine", "engineering", "design", "music", "art", "physical_ed",
            "statistics", "logic", "astronomy", "geology", "linguistics",
            "sociology", "anthropology", "neuroscience", "finance_study",
        ]),
        ("skills", [
            ("hours", 0, 8, "higher", "hours", None, 1.0, 7),
            ("level", 0, 10, "higher", "score", None, 0.8, 7),
        ], [
            "reading", "writing", "speaking", "listening", "translation",
            "algorithm", "system_design", "data_analysis", "communication",
            "leadership", "negotiation", "programming_lang", "framework",
            "tooling", "notetaking", "shorthand", "search", "analysis",
            "modeling", "experiment", "paper_writing", "code_review",
            "testing", "deployment", "public_speaking", "teaching",
        ]),
        ("study_tools", [
            ("minutes", 0, 240, "higher", "minutes", None, 0.8, 7),
            ("usage_days", 0, 7, "higher", "days", None, 0.6, 7),
        ], [
            "textbook", "notes", "problem_bank", "video_course", "podcast",
            "paper", "documentation", "code_repo", "online_course",
            "laboratory", "flashcards", "simulator",
        ]),
        ("reading", [
            ("pages", 0, 500, "higher", "pages", None, 0.8, 7),
            ("minutes", 0, 300, "higher", "minutes", None, 0.7, 7),
        ], [
            "fiction", "nonfiction", "academic", "technical", "biography",
            "history_book", "philosophy_book", "poetry", "essay", "manga",
            "news_article", "blog", "newsletter", "magazine", "manual",
            "report", "tutorial", "diary",
        ]),
    ],
    "work": [
        ("tasks", [
            ("hours", 0, 8, "higher", "hours", None, 1.0, 7),
            ("completion", 0, 1, "higher", "ratio", None, 0.8, 7),
        ], [
            "coding", "code_review", "meeting", "documentation", "testing",
            "deployment", "research", "design", "debugging", "performance_opt",
            "refactoring", "requirement_analysis", "design_review", "reporting",
            "recruiting", "training", "incident_response", "planning",
        ]),
        ("projects", [
            ("hours", 0, 8, "higher", "hours", None, 1.0, 7),
            ("progress", 0, 1, "higher", "ratio", None, 0.8, 7),
        ], [
            "frontend", "backend", "data", "algorithm", "infrastructure",
            "security", "testing_eng", "operations", "mobile", "desktop",
            "api", "database", "docs_site", "monitoring", "ci", "release",
            "machine_learning", "llm",
        ]),
        ("meetings", [
            ("duration", 0, 240, "lower", "minutes", None, 0.7, 7),
        ], [
            "standup", "weekly", "monthly", "quarterly", "review",
            "retrospective", "one_on_one", "client", "vendor", "interview",
            "sync", "all_hands",
        ]),
        ("tools", [
            ("hours", 0, 8, "higher", "hours", None, 0.7, 7),
            ("proficiency", 0, 10, "higher", "score", None, 0.6, 7),
        ], [
            "git", "vim", "docker", "kubernetes", "jupyter", "sql", "spark",
            "linux", "ci_cd", "terraform", "ansible", "grafana", "prometheus",
            "kafka", "redis", "postgresql", "mongodb", "elasticsearch",
            "airflow", "dbt", "snowflake", "databricks",
        ]),
        ("deliverables", [
            ("count", 0, 50, "higher", "items", None, 0.7, 7),
        ], [
            "feature", "bugfix", "pull_request", "release", "migration",
            "schema_change", "incident", "hotfix", "docs_page", "test_case",
            "commit", "code_snippet", "architecture_doc", "runbook",
        ]),
    ],
    "social": [
        ("relationships", [
            ("hours", 0, 8, "higher", "hours", None, 1.0, 7),
            ("quality", 0, 10, "higher", "score", None, 0.8, 7),
        ], [
            "family", "parents", "partner", "children", "friends",
            "colleagues", "mentor", "students", "clients", "partners",
            "neighbors", "classmates", "online_friends", "hometown_friends",
            "coach", "advisor", "teammates", "alumni",
        ]),
        ("channels", [
            ("minutes", 0, 240, "lower", "minutes", None, 0.7, 7),
            ("contacts", 0, 100, "higher", "times", None, 0.6, 7),
        ], [
            "wechat", "phone", "email", "face_to_face", "video",
            "sms", "voice", "forum", "community", "dm",
        ]),
        ("activities", [
            ("duration", 0, 480, "higher", "minutes", None, 0.7, 7),
        ], [
            "dining", "sports", "outing", "movie", "games", "tea", "coffee",
            "shopping", "hiking", "camping", "concert", "exhibition",
            "board_game", "escape_room", "kayaking", "barbecue",
        ]),
        ("communities", [
            ("hours", 0, 8, "higher", "hours", None, 0.7, 7),
            ("members", 0, 1000, "higher", "people", None, 0.5, 30),
        ], [
            "study_group", "running_club", "book_club", "volunteer",
            "church", "hobby_group", "online_community", "gym", "choir",
            "chess_club", "language_exchange", "hackathon_team", "cooking_club",
            "photography_group", "startup_community", "alumni_assoc",
        ]),
    ],
    "emotion": [
        ("panas", [
            ("score", 1, 5, "higher", "score", None, 0.8, 7),
        ], [
            "interested", "alert", "excited", "enthusiastic", "inspired",
            "determined", "attentive", "active", "proud", "strong",
            "afraid", "hostile", "guilty", "ashamed", "upset",
            "irritable", "anxious", "jittery", "nervous", "scared",
        ]),
        ("moods", [
            ("score", 0, 10, "higher", "score", None, 0.8, 7),
            ("frequency", 0, 7, "lower", "days", None, 0.6, 7),
        ], [
            "happy", "calm", "content", "grateful", "hopeful", "optimistic",
            "fearful", "stressed", "tired", "lonely", "angry", "sad",
            "bored", "jealous", "remorseful", "disgusted", "cheerful", "satisfied",
        ]),
        ("stressors", [
            ("severity", 0, 10, "lower", "score", None, 0.8, 7),
        ], [
            "work", "finance", "health", "relationship", "family",
            "environment", "academic", "social", "sleep", "time_pressure",
            "responsibility", "uncertainty", "conflict", "deadline", "relocation",
            "noise", "procrastination",
        ]),
        ("self_image", [
            ("score", 0, 10, "higher", "score", None, 0.7, 7),
        ], [
            "confidence", "self_esteem", "body_image", "self_worth", "resilience",
            "optimism", "purpose", "meaning", "identity", "self_efficacy",
            "self_compassion", "growth_mindset", "self_awareness", "assertiveness",
            "gratitude", "forgiveness", "patience", "curiosity",
        ]),
    ],
    "environment": [
        ("air_quality", [
            ("index", 0, 500, "lower", "index", None, 0.9, 7),
        ], [
            "pm25", "pm10", "o3", "no2", "so2", "co", "co2", "voc",
            "formaldehyde", "pollen", "radon", "asbestos",
        ]),
        ("living_comfort", [
            ("value", 0, 1000, "target", "index", None, 0.8, 7),
            ("comfort", 0, 10, "higher", "score", None, 0.7, 7),
        ], [
            ("temperature", 22), ("humidity", 50), ("noise", 30),
            ("illuminance", 500), ("airflow", 50), ("dust", 20),
            ("mold", 10), ("emf", 20), ("odor", 10), ("vibration", 10),
        ]),
        ("commute", [
            ("minutes", 0, 180, "lower", "minutes", None, 0.9, 7),
            ("times", 0, 30, "lower", "times", None, 0.6, 7),
        ], [
            "subway", "bus", "walk", "cycling", "driving", "taxi",
            "shared_bike", "high_speed_rail", "flight", "ferry", "tram",
        ]),
        ("weather", [
            ("value", 0, 1100, "target", "index", None, 0.6, 7),
            ("days", 0, 7, "higher", "days", None, 0.5, 7),
        ], [
            ("temperature_c", 22), ("humidity_pct", 50), ("wind_kmh", 15),
            ("rain_mm", 2), ("snow_cm", 0, None, "lower"), ("sun_hours", 6), ("uv_index", 3),
            ("visibility_km", 10), ("pressure_hpa", 1013), ("air_quality", 50),
        ]),
        ("home", [
            ("minutes", 0, 240, "higher", "minutes", None, 0.7, 7),
            ("quality", 0, 10, "higher", "score", None, 0.6, 7),
        ], [
            "cleaning", "cooking", "laundry", "dishes", "gardening",
            "repair", "organizing", "decluttering", "waste_recycling",
            "plant_care", "pet_care", "grocery", "errand", "budgeting_work",
            "caring", "mail",
        ]),
    ],
    "energy": [
        ("sleep_stages", [
            ("minutes", 0, 480, "higher", "minutes", None, 1.0, 7),
            ("score", 0, 10, "higher", "score", None, 0.8, 7),
        ], [
            "deep_sleep", "light_sleep", "rem", "awake", "sleep_latency",
            "sleep_efficiency", "sleep_duration", "time_in_bed",
            "sleep_regularity", "nap", "bedtime", "wake_time",
        ]),
        ("drainers", [
            ("amount", 0, 10, "lower", "score", None, 0.8, 7),
        ], [
            "caffeine", "alcohol", "nicotine", "sugar", "sedentary",
            "screen", "late_night", "bright_light", "noise", "dehydration",
            "overwork", "caffeine_afternoon",
        ]),
        ("boosters", [
            ("minutes", 0, 120, "higher", "minutes", None, 0.7, 7),
        ], [
            "morning_light", "exercise", "hydration", "nutrition",
            "socializing", "music", "nature", "power_nap", "breathing",
            "stretching", "cold_shower", "sunlight",
        ]),
        ("circadian", [
            ("score", 0, 10, "higher", "score", None, 0.7, 7),
            ("minutes", 0, 120, "higher", "minutes", None, 0.6, 7),
        ], [
            "morning_alertness", "evening_fatigue", "meal_timing",
            "caffeine_cutoff", "light_exposure", "chronotype_score",
        ]),
    ],
    "recovery": [
        ("techniques", [
            ("minutes", 0, 180, "higher", "minutes", None, 0.8, 7),
            ("quality", 0, 10, "higher", "score", None, 0.7, 7),
        ], [
            "meditation", "breathing", "mindfulness", "walk", "massage",
            "hot_bath", "music", "reading", "nap", "yoga", "stretching",
            "journaling", "venting", "gardening", "petting", "cooking",
            "tea", "aromatherapy", "sauna", "acupuncture",
        ]),
        ("metrics", [
            ("value", 0, 100, "higher", "index", None, 0.9, 7),
            ("score", 0, 10, "higher", "score", None, 0.7, 7),
        ], [
            "heart_rate_variability", "resting_heart_rate", "muscle_soreness",
            "fatigue", "attention", "memory", "reaction_time", "stress_index",
            "recovery_quality", "sleep_debt",
        ]),
        ("rest_days", [
            ("days", 0, 7, "higher", "days", None, 0.7, 7),
        ], [
            "full_rest", "active_rest", "digital_detox", "nature_day",
            "social_rest", "creative_rest", "silent_rest",
        ]),
    ],
    "other": [
        ("digital_life", [
            ("hours", 0, 16, "lower", "hours", None, 0.9, 7),
            ("score", 0, 10, "lower", "score", None, 0.6, 7),
        ], [
            "screen_time", "phone_usage", "social_media", "video", "gaming",
            "shopping", "news", "email", "notifications", "short_video",
            "browsing", "streaming",
        ]),
        ("habits", [
            ("days", 0, 7, "higher", "days", None, 0.9, 7),
        ], [
            "early_rise", "exercise", "reading", "hydration", "budgeting",
            "planning", "review", "decluttering", "saving", "studying",
            "meditation", "writing", "gratitude", "tidying", "walking",
            "flossing", "stretching",
        ]),
        ("goals", [
            ("progress", 0, 1, "higher", "ratio", None, 0.9, 30),
            ("days", 0, 30, "higher", "days", None, 0.6, 30),
        ], [
            "weekly_goal", "monthly_goal", "yearly_goal", "study_goal",
            "fitness_goal", "savings_goal", "reading_goal", "skill_goal",
            "project_goal", "health_goal", "career_goal", "social_goal",
        ]),
        ("leisure", [
            ("minutes", 0, 480, "higher", "minutes", None, 0.7, 7),
        ], [
            "games", "music", "movie", "tv", "anime", "photography",
            "drawing", "craft", "cooking_fun", "puzzle", "collecting",
            "diary", "garden_fun", "pet_fun", "travel_fun", "fishing",
            "billiards", "darts",
        ]),
        ("consumption", [
            ("amount", 0, 5000, "lower", "CNY", None, 0.7, 7),
            ("days", 0, 7, "lower", "days", None, 0.6, 7),
        ], [
            "delivery_food", "bubble_tea", "cigarettes", "lottery", "online_games",
            "livestream_gift", "impulse_buy", "snack_food", "fast_food", "alcohol",
            "candy", "energy_drink",
        ]),
    ],
}


def _slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def build_catalog() -> list[dict]:
    specs: list[dict] = []
    for domain, categories in CATALOG.items():
        for category_name, templates, members in categories:
            for member in members:
                if isinstance(member, (tuple, list)) and len(member) >= 2 and not isinstance(member[0], (int, float)):
                    member_name, target, *rest = member
                    member_unit = rest[0] if rest else None
                    member_direction = rest[1] if len(rest) > 1 else None
                else:
                    member_name, target, member_unit = member, None, None
                    member_direction = None
                for suffix, lo, hi, direction, unit, tmpl_target, weight, tc in templates:
                    metric_name = _slugify(member_name) + (f"_{suffix}" if suffix else "")
                    eff_direction = member_direction or direction
                    spec = {
                        "domain": domain,
                        "metric": metric_name,
                        "minimum": lo,
                        "maximum": hi,
                        "weight": weight,
                        "target_count": tc,
                        "direction": eff_direction,
                        "unit": unit if unit != "__member_unit__" else (member_unit or ""),
                        "aggregation": "mean",
                    }
                    eff_target = target if eff_direction == "target" else None
                    if eff_direction == "target":
                        spec["target"] = eff_target
                    specs.append(spec)
    return specs


def main() -> int:
    specs = build_catalog()
    total = len(specs)
    keys = [f"{s['domain']}:{s['metric']}" for s in specs]
    if len(set(keys)) != len(keys):
        print(f"ERROR: duplicate keys ({len(keys) - len(set(keys))} dupes)", file=sys.stderr)
        return 2
    if total < 1000:
        print(f"ERROR: only {total} metrics, need >= 1000", file=sys.stderr)
        return 2
    out = Path(__file__).resolve().parent.parent / "examples" / "metric-spec.json"
    out.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {total} metrics to {out}")
    print(f"Domains: {sorted({s['domain'] for s in specs})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
