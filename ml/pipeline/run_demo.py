"""CLI Demonstration Utility for the Unified Feedback Intelligence Pipeline (Step 7).

Executes sample feedback analyses across diverse college feedback categories
and negation scenarios, displaying structured sentiment and category predictions.
"""

from pathlib import Path
import sys

# Ensure project base directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.pipeline.feedback_intelligence import FeedbackIntelligencePipeline


def run_pipeline_demo() -> None:
    """Demonstrates unified feedback intelligence inference on representative student feedback."""
    print("=" * 80)
    print("CAMPUSVOICE - STEP 8.2: UNIFIED FEEDBACK INTELLIGENCE & PRIORITY SCORING DEMO")
    print("=" * 80)
    print("Initializing pipeline and loading in-memory model artifacts...")

    pipeline = FeedbackIntelligencePipeline(sentiment_model="best", category_model="best")
    print(f"Loaded sentiment model: {pipeline._sentiment_model_name}")
    print(f"Loaded category model:  {pipeline._category_model_name}")
    print("=" * 80)

    # Representative sample feedback across all 6 categories including negations
    feedback_samples = [
        "The professor explains difficult concepts clearly and is always accessible.",
        "The curriculum should include more modern cloud computing technologies.",
        "The examination timetable was published too late and schedules clashed.",
        "The laboratory computers are outdated and the equipment is not functioning well.",
        "The library has an excellent collection of reference books and quiet study areas.",
        "There should be more technical hackathons and cultural extracurricular activities.",
        "The faculty is not helpful and the explanations are not clear at all.",
    ]

    for i, sample in enumerate(feedback_samples, 1):
        result = pipeline.analyze_feedback(sample)

        print(f"\n[Sample {i}]")
        print(f"  Raw Input:       \"{result['feedback']}\"")
        print(f"  Cleaned Text:    \"{result['clean_text']}\"")

        # Sentiment summary
        sent = result["sentiment"]
        sent_top_probs = ""
        if sent["probabilities"]:
            top_sent = sorted(sent["probabilities"].items(), key=lambda x: x[1], reverse=True)
            sent_top_probs = ", ".join(f"{k}: {v:.1%}" for k, v in top_sent)
        print(f"  Sentiment:       {sent['name'].upper()} (Label: {sent['label']}, Confidence: {sent['confidence']:.2%})")
        if sent_top_probs:
            print(f"                   [{sent_top_probs}]")

        # Category summary
        cat = result["category"]
        cat_top_probs = ""
        if cat["probabilities"]:
            top_cat = sorted(cat["probabilities"].items(), key=lambda x: x[1], reverse=True)[:3]
            cat_top_probs = ", ".join(f"{k}: {v:.1%}" for k, v in top_cat)
        print(f"  Category:        {cat['name']} (Confidence: {cat['confidence']:.2%})")
        if cat_top_probs:
            print(f"                   Top 3 -> [{cat_top_probs}]")

        # Priority summary (Step 8.1 / Step 8.2)
        prio = result["priority"]
        print(f"  Priority:        {prio['level'].upper()} (Score: {prio['score']}/100)")
        print(f"                   Reason: \"{prio['reason']}\"")

        print(f"  Models:          Sentiment={result['models']['sentiment']}, Category={result['models']['category']}")

    print("\n" + "=" * 80)
    print("Demonstration completed successfully. Pipeline is ready for application integration.")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline_demo()
