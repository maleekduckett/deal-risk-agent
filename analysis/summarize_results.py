"""
Summarize the deal risk agent's output into the views a sales leader asks for.

Reads:
  data/sample_deals.csv    the synthetic deals the agents scored (one row per deal)
  data/sample_results.csv  the agents' scores (one row per deal)
  data/run_usage.csv       tokens, latency, and cost for every Claude call

Prints:
  1. Risk mix: how many deals and how much pipeline sit in each risk level
  2. Risk by stage: where in the funnel the risky deals are
  3. Biggest deals at risk: High risk deals ranked by amount, with the next step
  4. Good fit, at risk: strong ICP fit but High overall risk (the deals worth saving)
  5. Cost and speed: tokens, latency, and cost per agent from data/run_usage.csv

Run it from the repo root:
  pip install -r requirements.txt
  python analysis/summarize_results.py
"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"


def load() -> pd.DataFrame:
    """Join each deal to its scores on deal_id, the same key the n8n merge uses."""
    deals = pd.read_csv(DATA / "sample_deals.csv")
    results = pd.read_csv(DATA / "sample_results.csv")

    # validate="one_to_one" makes pandas raise an error if a deal_id appears twice
    # on either side, so a bad join fails loudly instead of quietly double counting.
    df = deals.merge(results, on="deal_id", how="left", validate="one_to_one")

    missing = df["overall_risk"].isna().sum()
    if missing:
        print(f"Warning: {missing} deals have no score and are left out.\n")
        df = df.dropna(subset=["overall_risk"])
    return df


def money(x: float) -> str:
    return f"${x:,.0f}"


def risk_mix(df: pd.DataFrame) -> None:
    print("1. Risk mix")
    order = ["Low", "Medium", "High"]
    mix = (
        df.groupby("overall_risk")
        .agg(deals=("deal_id", "count"), pipeline=("deal_amount", "sum"))
        .reindex(order)
        .fillna(0)
    )
    mix["share_of_pipeline"] = mix["pipeline"] / mix["pipeline"].sum()
    for level, row in mix.iterrows():
        print(f"   {level:<7} {int(row.deals):>3} deals   {money(row.pipeline):>12}   "
              f"{row.share_of_pipeline:.0%} of pipeline")
    print()


def risk_by_stage(df: pd.DataFrame) -> None:
    print("2. Risk by stage (deal counts)")
    # crosstab counts rows for every stage and risk combination, like a pivot table.
    table = pd.crosstab(df["stage"], df["overall_risk"]).reindex(
        columns=["Low", "Medium", "High"], fill_value=0
    )
    print(table.to_string())
    print()


def biggest_at_risk(df: pd.DataFrame, top: int = 10) -> None:
    print(f"3. Biggest deals at risk (top {top} High risk by amount)")
    high = df[df["overall_risk"] == "High"].sort_values("deal_amount", ascending=False)
    if high.empty:
        print("   None.\n")
        return
    for _, d in high.head(top).iterrows():
        print(f"   {d.deal_id}  {d.company_name:<26} {money(d.deal_amount):>10}  {d.stage}")
        print(f"            Next: {d.recommended_action}")
    print(f"   Total High risk pipeline: {money(high['deal_amount'].sum())}\n")


def good_fit_at_risk(df: pd.DataFrame) -> None:
    print("4. Good fit, at risk (Strong ICP fit but High overall risk)")
    save = df[(df["icp_fit"] == "Strong") & (df["overall_risk"] == "High")]
    if save.empty:
        print("   None.\n")
        return
    for _, d in save.sort_values("deal_amount", ascending=False).iterrows():
        print(f"   {d.deal_id}  {d.company_name:<26} {money(d.deal_amount):>10}  "
              f"engagement: {d.engagement_risk}, competitive: {d.competitive_risk}")
    print()


def cost_summary() -> None:
    print("5. Cost and speed by agent")
    usage = pd.read_csv(DATA / "run_usage.csv")
    by_agent = usage.groupby("agent").agg(
        calls=("deal_id", "count"),
        avg_input=("input_tokens", "mean"),
        avg_output=("output_tokens", "mean"),
        avg_seconds=("latency_ms", lambda ms: ms.mean() / 1000),
        cost=("cost_usd", "sum"),
    )
    print(by_agent.round(2).to_string())

    # Output tokens are priced 5x higher than input ($10 vs $2 per million),
    # so a small share of tokens can be a large share of the bill.
    output_cost = usage["output_tokens"].sum() * 10 / 1_000_000
    total = usage["cost_usd"].sum()
    deals = usage["deal_id"].nunique()
    print(f"   Total ${total:.2f} for {deals} deals, ${total / deals:.3f} per deal")
    print(f"   Output tokens are {output_cost / total:.0%} of the cost\n")


if __name__ == "__main__":
    data = load()
    print(f"Scored {len(data)} deals, {money(data['deal_amount'].sum())} total pipeline\n")
    risk_mix(data)
    risk_by_stage(data)
    biggest_at_risk(data)
    good_fit_at_risk(data)
    cost_summary()
