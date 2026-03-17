"""
Seed script to populate the database with mock data for Sunshine Dental Care.
Run: python -m app.mock_api.data
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.database import init_pool, close_pool, execute, fetchval


async def seed():
    await init_pool()

    # Check if already seeded
    count = await fetchval("SELECT COUNT(*) FROM practices")
    if count > 0:
        print("Database already seeded. Skipping.")
        await close_pool()
        return

    # --- Practice ---
    hours = {
        "Monday": "8:00 AM - 5:00 PM",
        "Tuesday": "8:00 AM - 5:00 PM",
        "Wednesday": "9:00 AM - 6:00 PM",
        "Thursday": "8:00 AM - 5:00 PM",
        "Friday": "8:00 AM - 3:00 PM",
        "Saturday": "9:00 AM - 1:00 PM",
        "Sunday": "Closed",
    }
    await execute(
        """INSERT INTO practices (id, name, address, phone, email, website, practice_type, hours)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        "default",
        "Sunshine Dental Care",
        "1234 Health Ave, Suite 100, San Diego, CA 92101",
        "(619) 555-0123",
        "info@sunshinedentalcare.com",
        "www.sunshinedentalcare.com",
        "General & Cosmetic Dentistry",
        json.dumps(hours),
    )
    print("Seeded practice.")

    # --- Providers ---
    providers = [
        {
            "id": "prov_001",
            "name": "Dr. Sarah Chen",
            "specialty": "General Dentistry",
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "working_hours": {
                "default": "8:00 AM - 5:00 PM",
                "Wednesday": "9:00 AM - 6:00 PM",
            },
        },
        {
            "id": "prov_002",
            "name": "Dr. Michael Rodriguez",
            "specialty": "Cosmetic Dentistry, Orthodontics",
            "available_days": ["Monday", "Tuesday", "Thursday", "Friday"],
            "working_hours": {"default": "8:00 AM - 5:00 PM"},
        },
        {
            "id": "prov_003",
            "name": "Dr. Emily Nakamura",
            "specialty": "Pediatric Dentistry",
            "available_days": ["Monday", "Wednesday", "Thursday", "Saturday"],
            "working_hours": {
                "default": "8:00 AM - 5:00 PM",
                "Wednesday": "9:00 AM - 6:00 PM",
                "Saturday": "9:00 AM - 1:00 PM",
            },
        },
        {
            "id": "prov_004",
            "name": "Lisa Park, RDH",
            "specialty": "Dental Hygienist",
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "working_hours": {
                "default": "8:00 AM - 5:00 PM",
                "Wednesday": "9:00 AM - 6:00 PM",
                "Friday": "8:00 AM - 3:00 PM",
            },
        },
    ]
    for p in providers:
        await execute(
            """INSERT INTO providers (id, practice_id, name, specialty, available_days, working_hours)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            p["id"],
            "default",
            p["name"],
            p["specialty"],
            p["available_days"],
            json.dumps(p["working_hours"]),
        )
    print(f"Seeded {len(providers)} providers.")

    # --- Appointment Types ---
    appointment_types = [
        ("Cleaning", 60, "prov_001"),
        ("Cleaning", 60, "prov_004"),
        ("Exam", 30, "prov_001"),
        ("Exam", 30, "prov_002"),
        ("Exam", 30, "prov_003"),
        ("Filling", 45, "prov_001"),
        ("Crown", 90, "prov_001"),
        ("Root Canal", 120, "prov_001"),
        ("Whitening", 60, "prov_002"),
        ("Veneers Consultation", 45, "prov_002"),
        ("Invisalign Consultation", 30, "prov_002"),
        ("Cosmetic Consultation", 30, "prov_002"),
        ("Child Exam", 30, "prov_003"),
        ("Child Cleaning", 45, "prov_003"),
        ("Sealants", 30, "prov_003"),
        ("Fluoride Treatment", 15, "prov_003"),
        ("Periodontal Maintenance", 60, "prov_004"),
    ]
    for name, duration, provider_id in appointment_types:
        await execute(
            """INSERT INTO appointment_types (name, duration_minutes, provider_id)
               VALUES ($1, $2, $3)""",
            name,
            duration,
            provider_id,
        )
    print(f"Seeded {len(appointment_types)} appointment types.")

    # --- Insurance Plans ---
    insurance_plans = [
        ("Delta Dental PPO", "PPO"),
        ("Delta Dental HMO", "HMO"),
        ("Cigna Dental", "PPO"),
        ("MetLife Dental", "PPO"),
        ("Aetna DMO", "HMO"),
        ("Aetna PPO", "PPO"),
        ("Guardian Dental", "PPO"),
        ("United Healthcare Dental", "PPO"),
        ("Humana Dental", "PPO"),
        ("Blue Cross Blue Shield Dental", "PPO"),
        ("Anthem Blue Cross", "PPO"),
        ("Medi-Cal Dental (Denti-Cal)", "Medicaid"),
        ("TRICARE Dental", "Government"),
    ]
    for name, plan_type in insurance_plans:
        await execute(
            """INSERT INTO insurance_plans (practice_id, name, type)
               VALUES ($1, $2, $3)""",
            "default",
            name,
            plan_type,
        )
    print(f"Seeded {len(insurance_plans)} insurance plans.")

    # --- Sample Patients ---
    patients = [
        ("John Smith", "(619) 555-1001", "john.smith@email.com"),
        ("Maria Garcia", "(619) 555-1002", "maria.garcia@email.com"),
        ("David Lee", "(619) 555-1003", "david.lee@email.com"),
        ("Emma Wilson", "(619) 555-1004", "emma.wilson@email.com"),
        ("James Brown", "(619) 555-1005", "james.brown@email.com"),
        ("Sofia Martinez", "(619) 555-1006", "sofia.martinez@email.com"),
        ("Robert Johnson", "(619) 555-1007", "robert.johnson@email.com"),
        ("Ana Lopez", "(619) 555-1008", "ana.lopez@email.com"),
        ("Michael Davis", "(619) 555-1009", "michael.davis@email.com"),
        ("Sarah Kim", "(619) 555-1010", "sarah.kim@email.com"),
        ("Carlos Reyes", "(619) 555-1011", "carlos.reyes@email.com"),
        ("Jennifer Wang", "(619) 555-1012", "jennifer.wang@email.com"),
        ("Luis Hernandez", "(619) 555-1013", "luis.hernandez@email.com"),
    ]
    for name, phone, email in patients:
        await execute(
            "INSERT INTO patients (name, phone, email) VALUES ($1, $2, $3)",
            name,
            phone,
            email,
        )
    print(f"Seeded {len(patients)} patients.")

    # --- Pre-populated Appointments (relative to current week) ---
    # Times are defined in the practice's local timezone (Pacific), then stored as UTC
    pacific = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific).replace(hour=0, minute=0, second=0, microsecond=0)
    # Find next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.weekday() != 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    if today.weekday() == 0:
        next_monday = today

    mon = next_monday
    tue = mon + timedelta(days=1)
    wed = mon + timedelta(days=2)
    thu = mon + timedelta(days=3)
    fri = mon + timedelta(days=4)
    sat = mon + timedelta(days=5)

    def _local(day, hour):
        """Create a local-time datetime and convert to UTC for storage."""
        return day.replace(hour=hour).astimezone(timezone.utc)

    appointments = [
        ("John Smith", "(619) 555-1001", "prov_001", "Exam", _local(mon, 9), 30),
        ("Maria Garcia", "(619) 555-1002", "prov_004", "Cleaning", _local(mon, 10), 60),
        ("David Lee", "(619) 555-1003", "prov_002", "Invisalign Consultation", _local(mon, 11), 30),
        ("Emma Wilson", "(619) 555-1004", "prov_003", "Child Exam", _local(mon, 13), 30),
        ("James Brown", "(619) 555-1005", "prov_001", "Filling", _local(tue, 8), 45),
        ("Sofia Martinez", "(619) 555-1006", "prov_004", "Periodontal Maintenance", _local(tue, 9), 60),
        ("Robert Johnson", "(619) 555-1007", "prov_001", "Crown", _local(wed, 10), 90),
        ("Ana Lopez", "(619) 555-1008", "prov_003", "Child Cleaning", _local(wed, 11), 45),
        ("Michael Davis", "(619) 555-1009", "prov_002", "Whitening", _local(thu, 14), 60),
        ("Sarah Kim", "(619) 555-1010", "prov_004", "Cleaning", _local(thu, 8), 60),
        ("Carlos Reyes", "(619) 555-1011", "prov_001", "Root Canal", _local(fri, 9), 120),
        ("Jennifer Wang", "(619) 555-1012", "prov_004", "Cleaning", _local(fri, 10), 60),
        ("Luis Hernandez", "(619) 555-1013", "prov_003", "Sealants", _local(sat, 9), 30),
    ]
    for patient_name, phone, provider_id, appt_type, starts_at, duration in appointments:
        await execute(
            """INSERT INTO appointments (practice_id, patient_name, patient_phone, provider_id,
               appointment_type, starts_at, duration_minutes, status, booked_via)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            "default",
            patient_name,
            phone,
            provider_id,
            appt_type,
            starts_at,
            duration,
            "confirmed",
            "seed",
        )
    print(f"Seeded {len(appointments)} appointments.")

    await close_pool()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
