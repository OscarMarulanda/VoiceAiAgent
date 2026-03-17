# Mock Data

All mock data used to simulate a MacPractice healthcare practice.

---

## Practice: Sunshine Dental Care

### Practice Info

| Field | Value |
|-------|-------|
| Name | Sunshine Dental Care |
| Address | 1234 Health Ave, Suite 100, San Diego, CA 92101 |
| Phone | (619) 555-0123 |
| Email | info@sunshinedentalcare.com |
| Website | www.sunshinedentalcare.com |
| Practice Type | General & Cosmetic Dentistry |

### Hours of Operation

| Day | Hours |
|-----|-------|
| Monday | 8:00 AM – 5:00 PM |
| Tuesday | 8:00 AM – 5:00 PM |
| Wednesday | 9:00 AM – 6:00 PM |
| Thursday | 8:00 AM – 5:00 PM |
| Friday | 8:00 AM – 3:00 PM |
| Saturday | 9:00 AM – 1:00 PM |
| Sunday | Closed |

---

## Providers

### Dr. Sarah Chen
| Field | Value |
|-------|-------|
| ID | prov_001 |
| Specialty | General Dentistry |
| Available Days | Mon, Tue, Wed, Thu, Fri |
| Working Hours | 8:00 AM – 5:00 PM (Wed: 9:00 AM – 6:00 PM) |
| Appointment Types | Cleaning, Exam, Filling, Crown, Root Canal |

### Dr. Michael Rodriguez
| Field | Value |
|-------|-------|
| ID | prov_002 |
| Specialty | Cosmetic Dentistry, Orthodontics |
| Available Days | Mon, Tue, Thu, Fri |
| Working Hours | 8:00 AM – 5:00 PM |
| Appointment Types | Whitening, Veneers, Invisalign Consultation, Cosmetic Consultation |

### Dr. Emily Nakamura
| Field | Value |
|-------|-------|
| ID | prov_003 |
| Specialty | Pediatric Dentistry |
| Available Days | Mon, Wed, Thu, Sat |
| Working Hours | 8:00 AM – 5:00 PM (Wed: 9:00 AM – 6:00 PM, Sat: 9:00 AM – 1:00 PM) |
| Appointment Types | Child Exam, Child Cleaning, Sealants, Fluoride Treatment |

### Lisa Park, RDH
| Field | Value |
|-------|-------|
| ID | prov_004 |
| Specialty | Dental Hygienist |
| Available Days | Mon, Tue, Wed, Thu, Fri |
| Working Hours | 8:00 AM – 5:00 PM (Wed: 9:00 AM – 6:00 PM, Fri: 8:00 AM – 3:00 PM) |
| Appointment Types | Cleaning, Periodontal Maintenance |

---

## Appointment Types & Durations

| Type | Duration | Providers |
|------|----------|-----------|
| Cleaning | 60 min | Lisa Park, Dr. Chen |
| Exam | 30 min | Dr. Chen, Dr. Rodriguez, Dr. Nakamura |
| Filling | 45 min | Dr. Chen |
| Crown | 90 min | Dr. Chen |
| Root Canal | 120 min | Dr. Chen |
| Whitening | 60 min | Dr. Rodriguez |
| Veneers Consultation | 45 min | Dr. Rodriguez |
| Invisalign Consultation | 30 min | Dr. Rodriguez |
| Cosmetic Consultation | 30 min | Dr. Rodriguez |
| Child Exam | 30 min | Dr. Nakamura |
| Child Cleaning | 45 min | Dr. Nakamura |
| Sealants | 30 min | Dr. Nakamura |
| Fluoride Treatment | 15 min | Dr. Nakamura |
| Periodontal Maintenance | 60 min | Lisa Park |

---

## Pre-Populated Appointments (Sample Week)

These simulate an already partially-booked schedule. Dates should be dynamically generated relative to "today" when the server starts.

| Patient | Provider | Day | Time | Type | Status |
|---------|----------|-----|------|------|--------|
| John Smith | Dr. Chen | Mon | 9:00 AM | Exam | Confirmed |
| Maria Garcia | Lisa Park | Mon | 10:00 AM | Cleaning | Confirmed |
| David Lee | Dr. Rodriguez | Mon | 11:00 AM | Invisalign Consultation | Confirmed |
| Emma Wilson | Dr. Nakamura | Mon | 1:00 PM | Child Exam | Confirmed |
| James Brown | Dr. Chen | Tue | 8:00 AM | Filling | Confirmed |
| Sofia Martinez | Lisa Park | Tue | 9:00 AM | Periodontal Maintenance | Confirmed |
| Robert Johnson | Dr. Chen | Wed | 10:00 AM | Crown | Confirmed |
| Ana Lopez | Dr. Nakamura | Wed | 11:00 AM | Child Cleaning | Confirmed |
| Michael Davis | Dr. Rodriguez | Thu | 2:00 PM | Whitening | Confirmed |
| Sarah Kim | Lisa Park | Thu | 8:00 AM | Cleaning | Confirmed |
| Carlos Reyes | Dr. Chen | Fri | 9:00 AM | Root Canal | Confirmed |
| Jennifer Wang | Lisa Park | Fri | 10:00 AM | Cleaning | Confirmed |
| Luis Hernandez | Dr. Nakamura | Sat | 9:00 AM | Sealants | Confirmed |

---

## Accepted Insurance Plans

| Plan Name | Type |
|-----------|------|
| Delta Dental PPO | PPO |
| Delta Dental HMO | HMO |
| Cigna Dental | PPO |
| MetLife Dental | PPO |
| Aetna DMO | HMO |
| Aetna PPO | PPO |
| Guardian Dental | PPO |
| United Healthcare Dental | PPO |
| Humana Dental | PPO |
| Blue Cross Blue Shield Dental | PPO |
| Anthem Blue Cross | PPO |
| Medi-Cal Dental (Denti-Cal) | Medicaid |
| TRICARE Dental | Government |

**Note:** Patients without insurance are welcome. Cash/self-pay pricing available.

---

## Sample Patients (for lookup testing)

| Name | Phone | Email |
|------|-------|-------|
| John Smith | (619) 555-1001 | john.smith@email.com |
| Maria Garcia | (619) 555-1002 | maria.garcia@email.com |
| David Lee | (619) 555-1003 | david.lee@email.com |
| Emma Wilson | (619) 555-1004 | emma.wilson@email.com |
| James Brown | (619) 555-1005 | james.brown@email.com |
| Sofia Martinez | (619) 555-1006 | sofia.martinez@email.com |

---

## Why San Diego / Dental?

- San Diego has a large bilingual (English/Spanish) population — perfect for demonstrating bilingual support
- Dental is one of MacPractice's primary verticals
- The data is realistic enough to demonstrate the concept without being complex enough to slow development
