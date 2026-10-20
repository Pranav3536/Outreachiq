"""ML/NLP intelligence: classification, evaluation, scoring, keywords."""
from .classifier import CONF_THRESHOLD, MODEL_PATH, PredictionResult, predict, train
from .evaluation import LIMITATIONS_TEXT, MIN_CLASS_SAMPLES, evaluate
from .features import build_feature_union
from .labels import LABEL_COLUMNS, append_labels, export_labels, load_labelled
from .nlp import token_frequency, top_keywords_per_category
from .quality_intel import ml_quality_summary
from .scoring import SCORE_WEIGHTS, ScoredContact, score_contacts, scores_to_dataframe
from .templates_map import CATEGORY_TEMPLATE_MAP, suggest_template

__all__ = [
    # classifier
    "CONF_THRESHOLD", "MODEL_PATH", "PredictionResult", "predict", "train",
    # evaluation
    "LIMITATIONS_TEXT", "MIN_CLASS_SAMPLES", "evaluate",
    # features
    "build_feature_union",
    # labels
    "LABEL_COLUMNS", "append_labels", "export_labels", "load_labelled",
    # nlp
    "token_frequency", "top_keywords_per_category",
    # quality_intel
    "ml_quality_summary",
    # scoring
    "SCORE_WEIGHTS", "ScoredContact", "score_contacts", "scores_to_dataframe",
    # templates_map
    "CATEGORY_TEMPLATE_MAP", "suggest_template",
]
