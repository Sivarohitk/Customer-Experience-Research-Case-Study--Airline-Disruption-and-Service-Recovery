"""Create portfolio-ready charts from processed airline feedback summaries."""

from pathlib import Path
import textwrap
from typing import Callable

import matplotlib.pyplot as plt
import pandas as pd

from .config import (
    CLEANED_FILE,
    COMBINATION_FIGURE,
    DASHBOARD_FIGURE,
    DISRUPTION_FIGURE,
    NEGATIVE_PHRASE_FILE,
    NEGATIVE_THEME_FIGURE,
    PAIN_POINT_COMBINATIONS_FILE,
    RATING_DISTRIBUTION_FILE,
    RATING_FIGURE,
    SENTIMENT_BY_THEME_FILE,
    SENTIMENT_FIGURE,
    SENTIMENT_SUMMARY_FILE,
    TERM_FIGURE,
    THEME_FIGURE,
    THEME_FREQUENCY_FILE,
    VISUALIZATION_NOTE_FILE,
)
from .frequency_analysis import PAIN_POINT_THEMES
from .utils import read_csv


plt.style.use("seaborn-v0_8-whitegrid")

PALETTE = {
    "pain_points": "#1f4e79",
    "negative": "#b03a2e",
    "neutral": "#7f8c8d",
    "positive": "#2e8b57",
    "negative_theme": "#8c2d04",
    "combination": "#5f6f7a",
    "combination_focus": "#8e244d",
    "rating": "#6c5b7b",
    "phrases": "#c77d00",
    "legacy": "#457b9d",
}


def wrap_label(text: object, width: int = 28) -> str:
    """Wrap long labels so they remain readable in saved figures."""
    value = "" if pd.isna(text) else str(text)
    return "\n".join(textwrap.wrap(value, width=width)) if value else "Unknown"


def format_count(value: float) -> str:
    """Format chart labels without unnecessary decimals."""
    return f"{int(round(value)):,}"


def prep_top_pain_points(theme_frequency: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    """Focus the main pain-point chart on disruption-related themes."""
    pain_points = theme_frequency[theme_frequency["theme"].isin(PAIN_POINT_THEMES)].copy()
    return pain_points.sort_values("count", ascending=False).head(limit).reset_index(drop=True)


def prep_negative_theme_summary(sentiment_by_theme: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    """Highlight the themes most associated with negative sentiment."""
    summary = sentiment_by_theme.copy()
    summary = summary[summary["review_count"] > 0]
    summary = summary.sort_values(["negative_share_pct", "review_count"], ascending=[False, False])
    return summary.head(limit).reset_index(drop=True)


def prep_combinations(combinations_df: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    """Blend the named focus combinations with the most common overall pairs."""
    focus_pairs = combinations_df[combinations_df["is_focus_combination"]].copy()
    top_pairs = combinations_df.sort_values("count", ascending=False).copy()
    selected = pd.concat([focus_pairs, top_pairs], ignore_index=True)
    selected = selected.drop_duplicates(subset=["combination_label"]).head(limit).reset_index(drop=True)
    return selected


def plot_horizontal_bars(
    ax: plt.Axes,
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    color: str,
    xlabel: str,
    limit: int = 8,
    annotation_fn: Callable[[pd.Series], str] | None = None,
    color_col: str | None = None,
) -> None:
    """Draw a clean horizontal bar chart for long theme labels."""
    data = df.head(limit).copy()
    if data.empty:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=11)
        ax.set_axis_off()
        return

    labels = [wrap_label(value) for value in data[label_col]]
    values = data[value_col].tolist()
    colors = data[color_col].tolist() if color_col else [color] * len(data)

    bars = ax.barh(labels, values, color=colors)
    ax.set_title(title, fontsize=13, weight="bold")
    ax.set_xlabel(xlabel)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_value = max(values) if values else 0
    offset = max(max_value * 0.01, 0.5)
    for index, bar in enumerate(bars):
        value = values[index]
        label = annotation_fn(data.iloc[index]) if annotation_fn else format_count(value)
        ax.text(value + offset, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=9)


def plot_vertical_bars(
    ax: plt.Axes,
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    color_map: dict[str, str] | None = None,
    default_color: str = "#4c78a8",
    ylabel: str = "Count",
) -> None:
    """Draw a compact vertical bar chart with readable annotations."""
    if df.empty:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=11)
        ax.set_axis_off()
        return

    labels = [wrap_label(value, width=14) for value in df[label_col]]
    values = df[value_col].tolist()
    colors = [color_map.get(str(value), default_color) for value in df[label_col]] if color_map else default_color

    bars = ax.bar(labels, values, color=colors)
    ax.set_title(title, fontsize=13, weight="bold")
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_value = max(values) if values else 0
    offset = max(max_value * 0.02, 0.5)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + offset, format_count(value), ha="center", fontsize=9)


def save_chart(draw_fn: Callable[[plt.Axes], None], output_path: Path, figsize: tuple[int, int]) -> None:
    """Create and save one figure while keeping formatting consistent."""
    fig, ax = plt.subplots(figsize=figsize)
    draw_fn(ax)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_legacy_disruption_chart(cleaned: pd.DataFrame, output_path: Path) -> None:
    """Retain the old disruption chart so the existing report step stays compatible."""
    if cleaned.empty or "disruption_type" not in cleaned.columns:
        return

    disruption_summary = (
        cleaned["disruption_type"]
        .fillna("unknown")
        .value_counts()
        .head(8)
        .rename_axis("disruption_type")
        .reset_index(name="count")
    )

    save_chart(
        lambda ax: plot_horizontal_bars(
            ax=ax,
            df=disruption_summary,
            label_col="disruption_type",
            value_col="count",
            title="Mentioned Disruption Categories",
            color=PALETTE["legacy"],
            xlabel="Reviews",
        ),
        output_path,
        figsize=(10, 5),
    )


def save_top_pain_points_chart(theme_frequency: pd.DataFrame, output_path: Path) -> None:
    """Show the most common CX pain points mentioned in reviews."""
    pain_points = prep_top_pain_points(theme_frequency)
    save_chart(
        lambda ax: plot_horizontal_bars(
            ax=ax,
            df=pain_points,
            label_col="theme",
            value_col="count",
            title="Top Customer Pain Points In Airline Disruptions",
            color=PALETTE["pain_points"],
            xlabel="Reviews",
            annotation_fn=lambda row: f"{format_count(row['count'])} ({row['share_of_reviews_pct']:.1f}%)",
        ),
        output_path,
        figsize=(11, 6),
    )


def save_sentiment_chart(sentiment_summary: pd.DataFrame, output_path: Path) -> None:
    """Show overall sentiment balance across the analyzed review set."""
    save_chart(
        lambda ax: plot_vertical_bars(
            ax=ax,
            df=sentiment_summary,
            label_col="sentiment",
            value_col="count",
            title="Overall Sentiment Distribution",
            color_map={
                "negative": PALETTE["negative"],
                "neutral": PALETTE["neutral"],
                "positive": PALETTE["positive"],
            },
        ),
        output_path,
        figsize=(8, 5),
    )


def save_negative_by_theme_chart(sentiment_by_theme: pd.DataFrame, output_path: Path) -> None:
    """Show which themes are most associated with negative sentiment."""
    summary = prep_negative_theme_summary(sentiment_by_theme)
    save_chart(
        lambda ax: plot_horizontal_bars(
            ax=ax,
            df=summary,
            label_col="theme",
            value_col="negative_share_pct",
            title="Themes Most Associated With Negative Sentiment",
            color=PALETTE["negative_theme"],
            xlabel="Negative Reviews Within Theme (%)",
            annotation_fn=lambda row: f"{row['negative_share_pct']:.1f}% | n={format_count(row['review_count'])}",
        ),
        output_path,
        figsize=(11, 6),
    )


def save_combination_chart(combinations_df: pd.DataFrame, output_path: Path) -> None:
    """Show co-occurring service-recovery issues that commonly appear together."""
    combo_summary = prep_combinations(combinations_df)
    combo_summary = combo_summary.copy()
    combo_summary["bar_color"] = combo_summary["is_focus_combination"].map(
        lambda is_focus: PALETTE["combination_focus"] if is_focus else PALETTE["combination"]
    )
    save_chart(
        lambda ax: plot_horizontal_bars(
            ax=ax,
            df=combo_summary,
            label_col="combination_label",
            value_col="count",
            title="Common Co-Occurring Airline Pain Points",
            color=PALETTE["combination"],
            xlabel="Reviews",
            annotation_fn=lambda row: f"{format_count(row['count'])} ({row['share_of_reviews_pct']:.1f}%)",
            color_col="bar_color",
        ),
        output_path,
        figsize=(12, 6),
    )


def save_rating_distribution_chart(rating_distribution: pd.DataFrame, output_path: Path) -> None:
    """Plot observed ratings when rating data is available."""
    if rating_distribution.empty:
        return

    ordered = rating_distribution.sort_values("rating").copy()
    save_chart(
        lambda ax: plot_vertical_bars(
            ax=ax,
            df=ordered,
            label_col="rating",
            value_col="count",
            title="Observed Rating Distribution",
            default_color=PALETTE["rating"],
            ylabel="Rated Reviews",
        ),
        output_path,
        figsize=(10, 5),
    )


def save_phrase_chart(negative_phrases: pd.DataFrame, output_path: Path) -> None:
    """Visualize high-signal negative-review language for the report and dashboard."""
    phrases = negative_phrases.head(10).copy()
    save_chart(
        lambda ax: plot_horizontal_bars(
            ax=ax,
            df=phrases,
            label_col="term",
            value_col="count",
            title="Top Negative Review Words And Phrases",
            color=PALETTE["phrases"],
            xlabel="Negative Reviews Mentioning Term",
        ),
        output_path,
        figsize=(10, 5),
    )


def save_dashboard(
    theme_frequency: pd.DataFrame,
    sentiment_summary: pd.DataFrame,
    sentiment_by_theme: pd.DataFrame,
    combinations_df: pd.DataFrame,
    rating_distribution: pd.DataFrame,
    negative_phrases: pd.DataFrame,
    output_path: Path,
) -> None:
    """Assemble a single dashboard-style figure for the case study deck or README."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    fig.suptitle("Airline Disruption And Service Recovery: Research Dashboard", fontsize=18, weight="bold")

    plot_horizontal_bars(
        ax=axes[0, 0],
        df=prep_top_pain_points(theme_frequency, limit=6),
        label_col="theme",
        value_col="count",
        title="Top Pain Points",
        color=PALETTE["pain_points"],
        xlabel="Reviews",
    )
    plot_vertical_bars(
        ax=axes[0, 1],
        df=sentiment_summary,
        label_col="sentiment",
        value_col="count",
        title="Sentiment Distribution",
        color_map={
            "negative": PALETTE["negative"],
            "neutral": PALETTE["neutral"],
            "positive": PALETTE["positive"],
        },
    )
    plot_horizontal_bars(
        ax=axes[0, 2],
        df=prep_negative_theme_summary(sentiment_by_theme, limit=6),
        label_col="theme",
        value_col="negative_share_pct",
        title="Most Negative Themes",
        color=PALETTE["negative_theme"],
        xlabel="Negative Share (%)",
    )

    combo_summary = prep_combinations(combinations_df, limit=6).copy()
    combo_summary["bar_color"] = combo_summary["is_focus_combination"].map(
        lambda is_focus: PALETTE["combination_focus"] if is_focus else PALETTE["combination"]
    )
    plot_horizontal_bars(
        ax=axes[1, 0],
        df=combo_summary,
        label_col="combination_label",
        value_col="count",
        title="Co-Occurring Issues",
        color=PALETTE["combination"],
        xlabel="Reviews",
        color_col="bar_color",
    )

    if rating_distribution.empty:
        axes[1, 1].text(0.5, 0.5, "No rating data available", ha="center", va="center", fontsize=11)
        axes[1, 1].set_axis_off()
    else:
        plot_vertical_bars(
            ax=axes[1, 1],
            df=rating_distribution.sort_values("rating").copy(),
            label_col="rating",
            value_col="count",
            title="Rating Distribution",
            default_color=PALETTE["rating"],
            ylabel="Rated Reviews",
        )

    plot_horizontal_bars(
        ax=axes[1, 2],
        df=negative_phrases.head(6),
        label_col="term",
        value_col="count",
        title="Negative Review Language",
        color=PALETTE["phrases"],
        xlabel="Reviews Mentioning Term",
    )

    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_visualization_note(figures_created: list[tuple[str, Path]]) -> str:
    """Document the generated charts so the repo stays easy to navigate."""
    lines = [
        "# Visualization Figure Guide",
        "",
        "The visualization step creates the following figures in `outputs/figures/`:",
        "",
    ]
    lines.extend([f"- `{name}`: `{path.name}`" for name, path in figures_created])
    lines.append("")
    return "\n".join(lines)


def create_visualizations() -> list[Path]:
    """Generate individual charts plus one dashboard figure for the case study."""
    cleaned = read_csv(CLEANED_FILE) if CLEANED_FILE.exists() else pd.DataFrame()
    theme_frequency = read_csv(THEME_FREQUENCY_FILE)
    sentiment_summary = read_csv(SENTIMENT_SUMMARY_FILE)
    sentiment_by_theme = read_csv(SENTIMENT_BY_THEME_FILE)
    combinations_df = read_csv(PAIN_POINT_COMBINATIONS_FILE)
    rating_distribution = read_csv(RATING_DISTRIBUTION_FILE) if RATING_DISTRIBUTION_FILE.exists() else pd.DataFrame()
    negative_phrases = read_csv(NEGATIVE_PHRASE_FILE) if NEGATIVE_PHRASE_FILE.exists() else pd.DataFrame()
    has_rating_data = not rating_distribution.empty

    save_legacy_disruption_chart(cleaned, DISRUPTION_FIGURE)
    save_top_pain_points_chart(theme_frequency, THEME_FIGURE)
    save_sentiment_chart(sentiment_summary, SENTIMENT_FIGURE)
    save_negative_by_theme_chart(sentiment_by_theme, NEGATIVE_THEME_FIGURE)
    save_combination_chart(combinations_df, COMBINATION_FIGURE)
    save_rating_distribution_chart(rating_distribution, RATING_FIGURE)
    save_phrase_chart(negative_phrases, TERM_FIGURE)
    save_dashboard(
        theme_frequency=theme_frequency,
        sentiment_summary=sentiment_summary,
        sentiment_by_theme=sentiment_by_theme,
        combinations_df=combinations_df,
        rating_distribution=rating_distribution,
        negative_phrases=negative_phrases,
        output_path=DASHBOARD_FIGURE,
    )

    figures_created = [
        ("Legacy disruption summary", DISRUPTION_FIGURE),
        ("Top customer pain points", THEME_FIGURE),
        ("Overall sentiment distribution", SENTIMENT_FIGURE),
        ("Negative sentiment by theme", NEGATIVE_THEME_FIGURE),
        ("Common pain-point combinations", COMBINATION_FIGURE),
        ("Negative review terms and phrases", TERM_FIGURE),
        ("Summary dashboard", DASHBOARD_FIGURE),
    ]
    if has_rating_data:
        figures_created.insert(5, ("Observed rating distribution", RATING_FIGURE))
    VISUALIZATION_NOTE_FILE.write_text(build_visualization_note(figures_created), encoding="utf-8")
    return [path for _, path in figures_created if path.exists()]


if __name__ == "__main__":
    figure_paths = create_visualizations()
    print("Saved figures:")
    for path in figure_paths:
        print(path)
    print(f"Wrote figure guide to {VISUALIZATION_NOTE_FILE}")
