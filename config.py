import os


MODEL = os.getenv("COUNCILQ_MODEL", "gemini-2.0-flash")
REVIEW_MODEL = os.getenv("COUNCILQ_REVIEW_MODEL", MODEL)
HUMAN_REVIEW_INTERRUPT_ID = "councilq_human_review"
