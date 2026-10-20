"""ML & NLP Intelligence - Classification, Evaluation, Keywords, Priority, Quality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from outreachiq.config import LABELLED_DIR, PROJECT_ROOT  # noqa: E402
from outreachiq.data.designation import categorize  # noqa: E402
from outreachiq.data.insights import eligible_for_campaign  # noqa: E402
from outreachiq.ml.classifier import CONF_THRESHOLD, predict, train  # noqa: E402
from outreachiq.ml.evaluation import LIMITATIONS_TEXT, evaluate  # noqa: E402
from outreachiq.ml.labels import append_labels, export_labels, load_labelled  # noqa: E402
from outreachiq.ml.nlp import top_keywords_per_category  # noqa: E402
from outreachiq.ml.quality_intel import ml_quality_summary  # noqa: E402
from outreachiq.ml.scoring import score_contacts, scores_to_dataframe  # noqa: E402
from outreachiq.ui.components import (  # noqa: E402
    CHART_COLORS, load_contacts, page_header, style_plotly_fig,
)

page_header("ML & NLP Intelligence", "Explainable classification, scoring and keywords")

df = load_contacts()
no_data = df is None or len(df) == 0

LABELLED_DEST = LABELLED_DIR / "reviewed_labels.csv"
SAMPLE_LABELLED = PROJECT_ROOT / "sample_data" / "labelled_titles_synthetic.csv"

(
    tab_class, tab_eval, tab_kw, tab_score, tab_quality
) = st.tabs(["Classification", "Evaluation", "Keywords", "Priority Scores", "Data Quality"])

# ── TAB 1: Classification ─────────────────────────────────────────────────────
with tab_class:
    if no_data:
        st.info("Load and clean contacts in Contact Data Lab first.")
    else:
        df_c = categorize(df.copy())
        titles = df_c["title"].fillna("").astype(str).tolist()
        preds = predict(titles)

        pred_df = pd.DataFrame([
            {
                "original_title": p.title,
                "predicted_category": p.category,
                "confidence": round(p.confidence, 3),
                "source": p.source,
                "needs_review": p.needs_review,
            }
            for p in preds
        ])
        st.write(f"{len(pred_df)} contacts classified. "
                 f"Source: **{preds[0].source if preds else '—'}**. "
                 f"Needs review: **{pred_df['needs_review'].sum()}**")
        st.dataframe(pred_df, use_container_width=True, hide_index=True)

        st.subheader("Review and label")
        st.caption("Select rows that need correction and assign the correct category below.")
        with st.form("label_review"):
            review_title = st.text_input("Title to label")
            new_label = st.selectbox(
                "Correct category",
                [None] + list(
                    __import__("outreachiq.data.designation", fromlist=["CATEGORIES"]).CATEGORIES
                ),
            )
            save_review = st.form_submit_button("Save label")
        if save_review and review_title and new_label:
            append_labels([{"title": review_title, "label": new_label}], LABELLED_DEST)
            st.success(f"Saved label for '{review_title}' -> {new_label}")

        if LABELLED_DEST.exists():
            current = load_labelled(LABELLED_DEST)
            st.caption(f"Saved labels: {len(current)} rows in {LABELLED_DEST.name}")
            raw = current.to_csv(index=False).encode("utf-8")
            st.download_button("Export labels CSV", raw,
                               file_name="reviewed_labels.csv", mime="text/csv",
                               key="dl_labels")

# ── TAB 2: Evaluation ─────────────────────────────────────────────────────────
with tab_eval:
    st.caption("Train on a labelled file, see per-class metrics. "
               "Vectorizer fits on the training split only (no leakage).")
    labelled_files = [SAMPLE_LABELLED] + (
        sorted(LABELLED_DIR.glob("*.csv")) if LABELLED_DIR.exists() else []
    )
    file_names = [str(f) for f in labelled_files]
    chosen = st.selectbox("Labelled file", file_names, key="eval_file")
    col1, col2 = st.columns(2)
    run_eval = col1.button("Evaluate (no model saved)", key="btn_eval")
    run_train = col2.button("Train and save model", type="primary", key="btn_train")

    if run_eval or run_train:
        lab = load_labelled(chosen)
        if len(lab) < 4:
            st.error("Not enough labelled data.")
        else:
            import warnings
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                report = evaluate(lab)
            for w in caught:
                st.warning(str(w.message))
            for w in report.get("warnings", []):
                st.warning(w)

            st.write(f"**Macro F1:** {report['macro_f1']} "
                     f"(train {report['train_size']}, test {report['test_size']})")
            if report["per_class"]:
                st.dataframe(
                    pd.DataFrame(report["per_class"]).T.reset_index().rename(
                        columns={"index": "class"}
                    ),
                    use_container_width=True, hide_index=True,
                )
            if report["confusion_matrix"]:
                cm_df = pd.DataFrame(
                    report["confusion_matrix"],
                    index=report["class_names"],
                    columns=report["class_names"],
                )
                fig = style_plotly_fig(
                    px.imshow(cm_df, color_continuous_scale="Greens",
                              title="Confusion matrix")
                )
                st.plotly_chart(fig, use_container_width=True)

            dist_df = pd.DataFrame(
                list(report["class_distribution"].items()),
                columns=["category", "count"],
            )
            fig2 = style_plotly_fig(
                px.bar(dist_df, x="category", y="count",
                       color_discrete_sequence=[CHART_COLORS[0]])
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.info(LIMITATIONS_TEXT)

            if run_train:
                try:
                    saved = train(lab)
                    st.success(f"Model saved to `{saved}`.")
                except Exception as exc:
                    st.error(f"Training failed: {exc}")

# ── TAB 3: Keywords ───────────────────────────────────────────────────────────
with tab_kw:
    if no_data:
        st.info("Load contacts first.")
    else:
        df_kw = categorize(df.copy())
        kw_map = top_keywords_per_category(df_kw)
        if not kw_map:
            st.info("No title_category column found — run classification first.")
        else:
            for cat, pairs in kw_map.items():
                if not pairs:
                    continue
                kw_df = pd.DataFrame(pairs, columns=["token", "count"])
                fig = style_plotly_fig(
                    px.bar(kw_df, x="count", y="token", orientation="h",
                           title=cat, color_discrete_sequence=[CHART_COLORS[1]])
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)

# ── TAB 4: Priority Scores ────────────────────────────────────────────────────
with tab_score:
    if no_data:
        st.info("Load contacts first.")
    else:
        df_s = categorize(df.copy())
        preds_s = predict(df_s["title"].fillna("").astype(str).tolist())
        df_s["title_category"] = [p.category for p in preds_s]
        scored = score_contacts(df_s)
        sc_df = scores_to_dataframe(scored).sort_values(
            "priority_score", ascending=False
        ).reset_index(drop=True)
        st.write(f"Priority scores for {len(sc_df)} contacts. "
                 "Called 'priority score', not a response or hiring probability.")
        st.dataframe(sc_df, use_container_width=True, hide_index=True)

        top_n = st.number_input("Top N for campaign", min_value=1,
                                max_value=len(sc_df), value=min(20, len(sc_df)),
                                key="top_n")
        if st.button("Store top N in campaign_selection", type="primary", key="btn_score_camp"):
            top_rows = sc_df.head(int(top_n))
            # Merge back to full df to get validity flags
            sel = df_s.iloc[[s.index for s in scored[:int(top_n)]]]
            eligible, n_ex = eligible_for_campaign(sel)
            st.session_state["campaign_selection"] = eligible
            st.success(f"Stored {len(eligible)} contacts. "
                       f"{n_ex} excluded (invalid email or excluded duplicate).")

# ── TAB 5: Data Quality ───────────────────────────────────────────────────────
with tab_quality:
    if no_data:
        st.info("Load contacts first.")
    else:
        preds_q = predict(df["title"].fillna("").astype(str).tolist())
        summary = ml_quality_summary(df, preds_q, conf_threshold=CONF_THRESHOLD)
        rows = [
            ("Total rows", summary["total_rows"]),
            ("Valid emails", summary["valid_emails"]),
            ("Invalid emails", summary["invalid_emails"]),
            ("Duplicate rows", summary["duplicate_rows"]),
            ("Rows with missing fields", summary["excluded_rows"]),
            ("Low-confidence classifications", summary["low_confidence_classifications"]),
            ("Needs-review classifications", summary["needs_review_classifications"]),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["Indicator", "Value"]),
            use_container_width=True, hide_index=True,
        )
