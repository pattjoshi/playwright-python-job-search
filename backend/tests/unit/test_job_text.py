from job_search.services.job_text import clean_description

POSTING = """About Acme
Acme is a leading product company founded in 1999 with offices in 12 countries and 5000 people.
Responsibilities:
Build RAG pipelines with LangChain
Ship   FastAPI   services
Ship   FastAPI   services
Requirements
About 3 years of Python
Benefits
Free lunch, gym and health insurance for your family
Acme is an equal opportunity employer. Apply now!"""


def test_company_intro_benefits_and_eeo_are_dropped():
    assert clean_description(POSTING, 1200) == (
        "Responsibilities:\nBuild RAG pipelines with LangChain\nShip FastAPI services\nRequirements\nAbout 3 years of Python"
    )


def test_cut_at_a_word_and_never_empty():
    assert clean_description("Python " * 50, 20) == "Python Python Python"
    intro_only = "About us\n" + "We build AI products for banks and insurers across India and Europe. " * 8
    assert "We build AI products" in clean_description(intro_only, 1200)  # no job heading: keep the text


def test_one_line_descriptions_keep_their_text():
    naukri = "Build UI & API automation with Python. Skills: Python, Playwright"
    assert clean_description(naukri, 1200) == naukri
