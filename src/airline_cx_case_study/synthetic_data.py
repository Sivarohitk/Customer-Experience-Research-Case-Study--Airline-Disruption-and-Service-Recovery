"""Generate reproducible synthetic airline feedback for fallback analysis."""

from argparse import ArgumentParser
from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

from .config import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_SYNTHETIC_ROW_COUNT,
    STANDARD_REVIEW_COLUMNS,
    SYNTHETIC_SOURCE_FILE,
)
from .utils import ensure_directories, write_csv


AIRLINES = [
    "Delta",
    "United",
    "American",
    "Southwest",
    "JetBlue",
    "Alaska",
    "Spirit",
    "Frontier",
    "Air Canada",
    "British Airways",
    "Lufthansa",
    "Emirates",
]

ROUTES = [
    "PHX-ATL",
    "JFK-LAX",
    "SEA-ORD",
    "BOS-DEN",
    "DFW-SFO",
    "LAX-LAS",
    "ORD-MCO",
    "ATL-BOS",
    "SFO-EWR",
    "PHL-AUS",
    "MIA-JFK",
    "DEN-SAN",
    "CLT-LGA",
    "MSP-SEA",
    "IAD-MIA",
]

TRAVELER_TYPES = [
    "Business",
    "Solo Leisure",
    "Couple Leisure",
    "Family Leisure",
    "Visiting Friends and Relatives",
]

SEAT_TYPES = [
    "Economy",
    "Premium Economy",
    "Business Class",
    "First Class",
]

ISSUE_WEIGHTS = {
    "delay": 0.22,
    "cancellation": 0.18,
    "refund": 0.13,
    "baggage": 0.13,
    "communication": 0.13,
    "rebooking": 0.11,
    "customer_support": 0.10,
}

SENTIMENT_WEIGHTS = {
    "delay": {"negative": 0.60, "neutral": 0.22, "positive": 0.18},
    "cancellation": {"negative": 0.72, "neutral": 0.18, "positive": 0.10},
    "refund": {"negative": 0.68, "neutral": 0.20, "positive": 0.12},
    "baggage": {"negative": 0.62, "neutral": 0.22, "positive": 0.16},
    "communication": {"negative": 0.66, "neutral": 0.20, "positive": 0.14},
    "rebooking": {"negative": 0.70, "neutral": 0.18, "positive": 0.12},
    "customer_support": {"negative": 0.70, "neutral": 0.18, "positive": 0.12},
}


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    """Return a key from a weight mapping using a deterministic random generator."""
    items = list(weights.items())
    choices, probabilities = zip(*items)
    return rng.choices(list(choices), weights=list(probabilities), k=1)[0]


def traveler_context(traveler_type: str) -> str:
    """Add light context so synthetic reviews feel more like real submissions."""
    mapping = {
        "Business": "I was traveling for work and had a time-sensitive schedule.",
        "Solo Leisure": "I was traveling alone for a short personal trip.",
        "Couple Leisure": "My partner and I were traveling for a weekend getaway.",
        "Family Leisure": "I was traveling with family, which made the disruption harder to manage.",
        "Visiting Friends and Relatives": "I was traveling to visit family and needed predictable timing.",
    }
    return mapping.get(traveler_type, "I needed the trip to run smoothly.")


def route_phrase(route: str) -> str:
    """Convert route formatting into plain language for natural text."""
    origin, destination = route.split("-")
    return f"{origin} to {destination}"


def rating_and_recommendation(sentiment: str, rng: random.Random) -> tuple[int, bool]:
    """Keep rating and recommendation roughly aligned with the synthetic sentiment."""
    if sentiment == "negative":
        return rng.choice([1, 1, 2, 2]), rng.random() < 0.08
    if sentiment == "neutral":
        return rng.choice([3, 3, 4]), rng.random() < 0.40
    return rng.choice([4, 4, 5]), rng.random() < 0.88


def random_review_date(rng: random.Random) -> str:
    """Generate a realistic review date within a recent two-year window."""
    start = date(2024, 1, 1)
    end = date(2026, 2, 28)
    offset = rng.randint(0, (end - start).days)
    return (start + timedelta(days=offset)).isoformat()


def build_delay_review(
    rng: random.Random,
    airline: str,
    route: str,
    traveler_type: str,
    seat_type: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate a delay-focused review with service-recovery details."""
    delay_hours = rng.choice([2, 3, 4, 5, 6, 7])
    update_gap = rng.choice([20, 30, 45, 60])
    if sentiment == "negative":
        title = rng.choice([
            "Long delay and almost no communication",
            "Hours late and no realistic departure time",
            "Delay turned into a missed connection mess",
        ])
        text = (
            f"My {seat_type.lower()} flight on {airline} from {route_phrase(route)} left {delay_hours} hours late. "
            f"The app kept changing and gate agents only gave updates after passengers started lining up at the desk. "
            f"{traveler_context(traveler_type)} I missed my connection and no one offered a useful recovery option."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Delay was frustrating but manageable",
            "Late departure with mixed communication",
            "Significant delay, average recovery",
        ])
        text = (
            f"Our {airline} flight from {route_phrase(route)} was delayed about {delay_hours} hours. "
            f"Updates came every {update_gap} minutes, but only after people kept asking for information. "
            f"The crew stayed polite and we eventually got where we needed to go."
        )
    else:
        title = rng.choice([
            "Delay handled better than expected",
            "Strong recovery during a weather delay",
            "Late departure but clear updates throughout",
        ])
        text = (
            f"We still departed {delay_hours} hours late on {airline} from {route_phrase(route)}, but this was one of the better recoveries I have seen. "
            f"The airline sent text updates every {update_gap} minutes, gate staff explained the reason for the delay, and an agent protected my onward connection before boarding."
        )
    return title, text


def build_cancellation_review(
    rng: random.Random,
    airline: str,
    route: str,
    traveler_type: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate a cancellation review with re-accommodation context."""
    wait_minutes = rng.choice([25, 40, 55, 70, 95])
    if sentiment == "negative":
        title = rng.choice([
            "Cancelled flight and chaotic recovery",
            "Cancellation with no clear next steps",
            "App, gate, and phone support all disagreed",
        ])
        text = (
            f"My {airline} flight from {route_phrase(route)} was cancelled after repeated rolling delays. "
            f"The app showed one itinerary, the gate desk suggested another, and phone support disconnected me twice. "
            f"{traveler_context(traveler_type)} I ended up paying for my own hotel and finding a backup flight myself."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Cancellation eventually resolved",
            "Cancelled flight with average service recovery",
            "Not smooth, but I was rebooked",
        ])
        text = (
            f"The flight from {route_phrase(route)} on {airline} was cancelled the same evening. "
            f"It took around {wait_minutes} minutes to get rebooked and the process was not especially organized, but an airport agent eventually placed me on a flight the next morning."
        )
    else:
        title = rng.choice([
            "Cancellation, but the agent took ownership",
            "Cancelled flight recovered well",
            "Same-day cancellation with surprisingly clear support",
        ])
        text = (
            f"My flight from {route_phrase(route)} on {airline} was cancelled, but the recovery was handled well. "
            f"Within {wait_minutes} minutes the desk agent rebooked me, issued a hotel or meal voucher, and clearly explained baggage and boarding instructions for the new itinerary."
        )
    return title, text


def build_refund_review(
    rng: random.Random,
    airline: str,
    route: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate refund and compensation reviews."""
    refund_days = rng.choice([7, 10, 14, 21, 28, 35])
    if sentiment == "negative":
        title = rng.choice([
            "Refund took far too long",
            "Confusing voucher and refund policy",
            "Every agent gave a different answer on the refund",
        ])
        text = (
            f"After my disrupted trip on {airline} from {route_phrase(route)}, the refund process became a second problem. "
            f"It took {refund_days} days to get the money back, the voucher rules were unclear, and customer service kept telling me to wait for another email."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Refund eventually came through",
            "Slow but successful refund process",
            "Refund handled, just not quickly",
        ])
        text = (
            f"I did receive a refund for the disrupted {airline} trip from {route_phrase(route)}, but it took about {refund_days} days and required multiple follow-up messages. "
            f"The outcome was fine even though the process felt more manual than it should have been."
        )
    else:
        title = rng.choice([
            "Refund process was clear",
            "Compensation request handled well",
            "Surprisingly smooth refund experience",
        ])
        text = (
            f"I still needed a refund after the disruption on {airline}, but this part was handled well. "
            f"The airline confirmed eligibility quickly, processed the refund in about {refund_days} days, and sent clear updates so I knew what to expect."
        )
    return title, text


def build_baggage_review(
    rng: random.Random,
    airline: str,
    route: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate baggage disruption reviews with delivery or claim details."""
    bag_days = rng.choice([1, 2, 3, 4])
    if sentiment == "negative":
        title = rng.choice([
            "Baggage issue with almost no visibility",
            "Lost luggage and poor follow-up",
            "Bag never arrived when promised",
        ])
        text = (
            f"My checked bag did not arrive after flying {airline} from {route_phrase(route)}. "
            f"The baggage desk opened a claim, but tracking updates were vague and phone support kept sending me back to the airport team. "
            f"The luggage finally showed up {bag_days} days later with no proactive communication."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Delayed bag, average recovery",
            "Baggage arrived later than promised",
            "Bag delay was handled, but slowly",
        ])
        text = (
            f"My suitcase missed the connection on a {airline} itinerary from {route_phrase(route)} and arrived {bag_days} days later. "
            f"The claim process was straightforward, but status updates were sparse until the delivery driver finally called."
        )
    else:
        title = rng.choice([
            "Delayed baggage but solid follow-up",
            "Bag issue resolved professionally",
            "Baggage recovery was better than expected",
        ])
        text = (
            f"My bag was delayed after flying {airline} from {route_phrase(route)}, but the recovery was well handled. "
            f"The baggage team sent updates, confirmed the tracing number, and delivered the luggage within {bag_days} day instead of leaving me to chase multiple teams."
        )
    return title, text


def build_communication_review(
    rng: random.Random,
    airline: str,
    route: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate communication-specific disruption reviews."""
    if sentiment == "negative":
        title = rng.choice([
            "Communication failed at every step",
            "Conflicting information from app and gate staff",
            "No proactive updates during the disruption",
        ])
        text = (
            f"The biggest issue on my {airline} trip from {route_phrase(route)} was communication. "
            f"The app kept refreshing with conflicting information, announcements came after each promised boarding time passed, and the gate team had no consistent script when people asked what was happening."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Communication improved too late",
            "Some updates, but not enough",
            "Mixed communication during the disruption",
        ])
        text = (
            f"Communication during my {airline} trip from {route_phrase(route)} was inconsistent. "
            f"There were updates, but they usually arrived after the situation had already changed. Once a supervisor stepped in, the explanations became clearer."
        )
    else:
        title = rng.choice([
            "Clear communication made a big difference",
            "Good updates during an otherwise stressful trip",
            "Strong communication during service recovery",
        ])
        text = (
            f"This was still a disrupted {airline} trip from {route_phrase(route)}, but communication stood out in a good way. "
            f"The airline used clear text alerts, staff repeated the same message at the gate, and the final rebooking instructions were easy to follow."
        )
    return title, text


def build_rebooking_review(
    rng: random.Random,
    airline: str,
    route: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate rebooking-friction reviews."""
    wait_minutes = rng.choice([20, 35, 50, 75, 100])
    if sentiment == "negative":
        title = rng.choice([
            "Rebooking process was exhausting",
            "Missed connection and poor rebooking support",
            "Standby and app rebooking both failed",
        ])
        text = (
            f"After a disruption on {airline} from {route_phrase(route)}, the rebooking process was the most frustrating part. "
            f"I waited about {wait_minutes} minutes in line, the kiosk could not confirm the new itinerary, and the app kept removing the seat it had just offered me."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Rebooking took effort but worked",
            "Eventually rebooked after a long wait",
            "Average recovery after a missed connection",
        ])
        text = (
            f"I missed my onward flight after traveling {route_phrase(route)} with {airline}. "
            f"Rebooking took around {wait_minutes} minutes and required both the app and an airport agent, but I eventually got a confirmed seat later that day."
        )
    else:
        title = rng.choice([
            "Rebooking was handled efficiently",
            "Missed connection recovered well",
            "Agent fixed the itinerary quickly",
        ])
        text = (
            f"I still had a disruption on {airline} from {route_phrase(route)}, but the rebooking part was solid. "
            f"An agent rebuilt the itinerary in about {wait_minutes} minutes, confirmed the seat assignment, and explained how standby would work if the earlier option opened up."
        )
    return title, text


def build_customer_support_review(
    rng: random.Random,
    airline: str,
    route: str,
    sentiment: str,
) -> tuple[str, str]:
    """Generate support-channel reviews covering phone, chat, and desk interactions."""
    hold_minutes = rng.choice([25, 45, 60, 85, 110])
    if sentiment == "negative":
        title = rng.choice([
            "Customer support kept sending me in circles",
            "Long hold times and conflicting advice",
            "Support experience made the disruption worse",
        ])
        text = (
            f"Customer support was the hardest part of my disrupted {airline} trip from {route_phrase(route)}. "
            f"I spent about {hold_minutes} minutes on hold, was transferred multiple times, and each agent contradicted the previous one about rebooking, vouchers, and baggage status."
        )
    elif sentiment == "neutral":
        title = rng.choice([
            "Support was polite but not especially effective",
            "Slow help from customer service",
            "Support eventually solved it",
        ])
        text = (
            f"I contacted customer support after my {airline} trip from {route_phrase(route)} went off track. "
            f"The team was polite, but it still took roughly {hold_minutes} minutes and multiple contacts before someone actually resolved the case."
        )
    else:
        title = rng.choice([
            "Support agent finally took ownership",
            "Customer service recovered the situation well",
            "Helpful support after a rough start",
        ])
        text = (
            f"My disrupted {airline} trip from {route_phrase(route)} started badly, but customer support recovered it. "
            f"After about {hold_minutes} minutes, one agent took ownership, documented the case clearly, and stayed with it until the rebooking or refund was confirmed."
        )
    return title, text


BUILDERS = {
    "delay": build_delay_review,
    "cancellation": build_cancellation_review,
    "refund": build_refund_review,
    "baggage": build_baggage_review,
    "communication": build_communication_review,
    "rebooking": build_rebooking_review,
    "customer_support": build_customer_support_review,
}


def create_synthetic_record(index: int, rng: random.Random) -> dict[str, object]:
    """Create one realistic synthetic review row."""
    airline = rng.choice(AIRLINES)
    route = rng.choice(ROUTES)
    traveler_type = rng.choice(TRAVELER_TYPES)
    seat_type = rng.choices(SEAT_TYPES, weights=[0.62, 0.16, 0.18, 0.04], k=1)[0]
    disruption_type = weighted_choice(rng, ISSUE_WEIGHTS)
    sentiment = weighted_choice(rng, SENTIMENT_WEIGHTS[disruption_type])
    rating, recommended = rating_and_recommendation(sentiment, rng)

    builder = BUILDERS[disruption_type]
    if disruption_type == "delay":
        review_title, review_text = builder(rng, airline, route, traveler_type, seat_type, sentiment)
    elif disruption_type == "cancellation":
        review_title, review_text = builder(rng, airline, route, traveler_type, sentiment)
    else:
        review_title, review_text = builder(rng, airline, route, sentiment)

    raw_text = f"{review_title} | {review_text}"
    return {
        "review_id": f"synthetic_{index:05d}",
        "source": "Synthetic Fallback Dataset",
        "airline": airline,
        "review_date": random_review_date(rng),
        "review_title": review_title,
        "review_text": review_text,
        "rating": rating,
        "traveler_type": traveler_type,
        "route": route,
        "seat_type": seat_type,
        "recommended": recommended,
        "disruption_type": disruption_type,
        "raw_text": raw_text,
        "is_synthetic": True,
    }


def generate_synthetic_feedback(
    row_count: int = DEFAULT_SYNTHETIC_ROW_COUNT,
    seed: int = DEFAULT_RANDOM_SEED,
) -> pd.DataFrame:
    """Generate a reproducible synthetic dataset for fallback analysis."""
    rng = random.Random(seed)
    records: list[dict[str, object]] = []
    seen_texts: set[str] = set()

    while len(records) < row_count:
        candidate = create_synthetic_record(index=len(records) + 1, rng=rng)
        if candidate["raw_text"] in seen_texts:
            continue
        seen_texts.add(str(candidate["raw_text"]))
        records.append(candidate)

    synthetic_df = pd.DataFrame(records)
    return synthetic_df[STANDARD_REVIEW_COLUMNS]


def generate_synthetic_feedback_file(
    output_path: Path = SYNTHETIC_SOURCE_FILE,
    row_count: int = DEFAULT_SYNTHETIC_ROW_COUNT,
    seed: int = DEFAULT_RANDOM_SEED,
    force_regenerate: bool = False,
) -> Path:
    """Write the synthetic dataset to data/raw for pipeline reuse."""
    ensure_directories()
    if output_path.exists() and not force_regenerate:
        return output_path

    synthetic_df = generate_synthetic_feedback(row_count=row_count, seed=seed)
    write_csv(synthetic_df, output_path)
    return output_path


def main() -> None:
    """Expose synthetic data generation as a standalone command."""
    parser = ArgumentParser(description="Generate synthetic airline feedback.")
    parser.add_argument("--rows", type=int, default=DEFAULT_SYNTHETIC_ROW_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--output", type=str, default=str(SYNTHETIC_SOURCE_FILE))
    args = parser.parse_args()

    output_path = generate_synthetic_feedback_file(
        output_path=Path(args.output),
        row_count=args.rows,
        seed=args.seed,
        force_regenerate=True,
    )
    print(f"Wrote synthetic fallback dataset to {output_path}")


if __name__ == "__main__":
    main()
