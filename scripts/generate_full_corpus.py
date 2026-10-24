import json
import os

def generate_corpus():
    print("[+] Generating Full Institutional Test Corpus for Research Benchmarking...")
    
    os.makedirs('data/syllabi', exist_ok=True)
    os.makedirs('data/policies', exist_ok=True)
    os.makedirs('data/emails', exist_ok=True)

    # 1. Expand Syllabi to 50 diverse samples across STEM, Humanities, Business, Health
    syllabi = []
    departments = ["CS", "MATH", "ENG", "BUS", "NURS", "HIST", "PHYS", "ECON", "PSY", "CHEM"]
    for i in range(1, 51):
        dept = departments[(i - 1) % len(departments)]
        syllabi.append({
            "id": f"SYL-{i:03d}",
            "course_code": f"{dept} {100 + i}",
            "text": f"Course Syllabus for {dept} {100 + i}. Instructor: Dr. Faculty {i}. Office Hours: Mon/Wed 2-4 PM in Hall {i}. Grading Breakdown: Assignments 30.0%, Midterm 30.0%, Final 40.0%. Key Policy: Late submissions incur a 10% penalty per 24 hours."
        })
    with open('data/syllabi/batch_syllabi.json', 'w', encoding='utf-8') as f:
        json.dump(syllabi, f, indent=2)
    print(f"[?] Generated {len(syllabi)} full-scale syllabi in data/syllabi/batch_syllabi.json")

    # 2. Expand Policies to 40 institutional governance documents
    policies = []
    policy_topics = [
        "Undergraduate Attendance", "Academic Integrity", "Grade Appeal", "IT Acceptable Use", 
        "ADA Accessibility", "FERPA Privacy", "Student Code of Conduct", "Campus Safety", 
        "Housing Regulations", "Financial Aid Eligibility"
    ]
    for i in range(1, 41):
        topic = policy_topics[(i - 1) % len(policy_topics)]
        policies.append({
            "id": f"POL-{i:03d}",
            "title": f"Institutional Policy on {topic} v{i}",
            "text": f"Official University Policy regarding {topic}. All university members must adhere to strict compliance guidelines. Notice periods require 24 hours or 48 hours for emergencies. Non-compliance exceeding 20% triggers a review by the Dean within 5 business days.",
            "constraints": ["24 hours", "48 hours", "20%", "5 business days"]
        })
    with open('data/policies/batch_policies.json', 'w', encoding='utf-8') as f:
        json.dump(policies, f, indent=2)
    print(f"[?] Generated {len(policies)} full-scale institutional policies in data/policies/batch_policies.json")

    # 3. Expand Tickets to 300 helpdesk inquiries
    tickets = []
    categories = [
        "LMS Access", "Grade Disputes", "Online Proctoring", "Accessibility/Captions", 
        "Course Enrollment", "Login/Account Lockout", "Exam Rescheduling", "General Inquiries"
    ]
    for i in range(1, 301):
        cat = categories[(i - 1) % len(categories)]
        tickets.append({
            "id": f"TICK-{i:03d}",
            "category": cat,
            "text": f"Support request #{i} regarding {cat.lower()}. The student reports an operational blocker in the university portal requiring administrative intervention."
        })
    with open('data/emails/synthetic_tickets.json', 'w', encoding='utf-8') as f:
        json.dump(tickets, f, indent=2)
    print(f"[?] Generated {len(tickets)} full-scale helpdesk support tickets in data/emails/synthetic_tickets.json")

if __name__ == "__main__":
    generate_corpus()
