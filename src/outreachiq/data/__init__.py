"""Contact data loading, mapping, validation, cleaning, duplicates, and export."""
from .column_mapping import (
    CANONICAL_FIELDS,
    FieldSuggestion,
    MappingResult,
    apply_mapping,
    save_mapped,
    suggest_mapping,
)
from .cleaning import clean, clean_company, clean_name
from .duplicates import apply_exclude, detect
from .export import (
    cleaned_csv_bytes,
    cleaned_subset,
    cleaned_xlsx_bytes,
    export_columns,
    report_csv_bytes,
    report_to_dataframe,
    report_xlsx_bytes,
    save_cleaned,
    save_report,
)
from .loader import (
    SUPPORTED_EXTENSIONS,
    LoaderError,
    load_dataframe,
    save_upload,
)
from .quality_report import build_report, problem_rows
from .validation import email_clean, email_issue, email_valid, validate
from .designation import CATEGORIES, CATEGORY_RULES, categorize, categorize_title, normalize_title
from .insights import (
    CLEANED_FILE,
    campaign_history,
    category_counts,
    distinct_titles,
    eligible_for_campaign,
    email_status_counts,
    kpis,
    load_cleaned,
    missing_per_field,
    top_companies,
    with_flags,
)

__all__ = [
    # column mapping
    "CANONICAL_FIELDS", "FieldSuggestion", "MappingResult",
    "apply_mapping", "save_mapped", "suggest_mapping",
    # loader
    "SUPPORTED_EXTENSIONS", "LoaderError", "load_dataframe", "save_upload",
    # validation
    "email_clean", "email_valid", "email_issue", "validate",
    # cleaning
    "clean", "clean_name", "clean_company",
    # duplicates
    "detect", "apply_exclude",
    # quality report
    "build_report", "problem_rows",
    # export
    "cleaned_subset", "export_columns", "cleaned_csv_bytes", "cleaned_xlsx_bytes",
    "save_cleaned", "report_to_dataframe", "report_csv_bytes", "report_xlsx_bytes",
    "save_report",
    # designation
    "CATEGORIES", "CATEGORY_RULES", "categorize", "categorize_title", "normalize_title",
    # insights
    "CLEANED_FILE", "campaign_history", "category_counts", "distinct_titles",
    "eligible_for_campaign", "email_status_counts", "kpis", "load_cleaned",
    "missing_per_field", "top_companies", "with_flags",
]
