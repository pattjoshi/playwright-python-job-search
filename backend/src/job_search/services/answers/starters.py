"""The questions application forms ask most often, added to a new Answer Bank in one click.

Each has a few other wordings forms use, so they match even before the AI sees them.
"""

STARTER_QUESTIONS: list[dict] = [
    # personal
    {"question": "Full name", "category": "personal", "wordings": ["Your name", "Name"]},
    {"question": "Email address", "category": "personal", "wordings": ["Email", "E-mail"]},
    {"question": "Phone number", "category": "personal", "wordings": ["Mobile number", "Contact number", "Phone"]},
    {"question": "Current city", "category": "personal", "wordings": ["Current location", "Where are you based?"]},
    {"question": "LinkedIn profile URL", "category": "personal", "wordings": ["LinkedIn profile", "LinkedIn"]},
    {"question": "GitHub or portfolio URL", "category": "personal", "wordings": ["Portfolio", "Website", "GitHub profile"]},
    # experience
    {"question": "Total years of experience", "category": "experience", "kind": "number",
     "wordings": ["How many years of work experience do you have?", "Total experience", "Years of experience"]},
    {"question": "Current job title", "category": "experience", "wordings": ["Current designation", "Current role"]},
    {"question": "Current company", "category": "experience", "wordings": ["Current employer", "Current organization"]},
    {"question": "Highest qualification", "category": "experience",
     "wordings": ["Highest education", "Education", "What is your highest level of education?"]},
    {"question": "Key skills", "category": "experience", "wordings": ["Skills", "Primary skills"]},
    # compensation
    {"question": "Current CTC (per year)", "category": "compensation",
     "wordings": ["Current salary", "Current CTC", "What is your current annual compensation?"]},
    {"question": "Expected CTC (per year)", "category": "compensation",
     "wordings": ["Expected salary", "Expected CTC", "What are your salary expectations?"]},
    {"question": "Is your expected salary negotiable?", "category": "compensation", "kind": "yes_no",
     "wordings": ["Is your salary negotiable?"]},
    # availability
    {"question": "Notice period", "category": "availability",
     "wordings": ["What is your notice period?", "How soon can you join?", "Notice period (in days)"]},
    {"question": "Earliest date you can join", "category": "availability", "wordings": ["Earliest start date", "When can you start?"]},
    {"question": "Are you currently serving your notice period?", "category": "availability", "kind": "yes_no",
     "wordings": ["Are you serving notice period?"]},
    {"question": "Are you willing to relocate?", "category": "availability", "kind": "yes_no",
     "wordings": ["Are you open to relocation?", "Willing to relocate"]},
    {"question": "Preferred way of working (remote, hybrid or office)", "category": "availability",
     "wordings": ["Preferred work mode", "Are you comfortable working from the office?"]},
    {"question": "Are you comfortable with night or rotational shifts?", "category": "availability", "kind": "yes_no",
     "wordings": ["Are you open to working in shifts?"]},
    # work authorization
    {"question": "Are you legally authorized to work in India?", "category": "work_authorization", "kind": "yes_no",
     "wordings": ["Are you authorized to work in India?"]},
    {"question": "Will you now or in the future require visa sponsorship?", "category": "work_authorization", "kind": "yes_no",
     "wordings": ["Do you require visa sponsorship?", "Do you need sponsorship?"]},
    {"question": "Do you have a valid passport?", "category": "work_authorization", "kind": "yes_no", "wordings": []},
    # other
    {"question": "Why are you looking for a change?", "category": "other",
     "wordings": ["Reason for leaving your current job", "Reason for job change"]},
    {"question": "How did you hear about this job?", "category": "other", "wordings": ["Where did you find this job?"]},
]
