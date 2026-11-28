"""The Baseline page's pace chart geometry: log-scale ticks, dots, labels, and diagonal guides (#252)."""

import math

TOP = 10
"""How many rows at the head of a board take the accent, in the pace chart and at their rank in the list."""

LABELLED = 5
"""How many of those the pace chart names by rank beside their dot."""


def _ticks(low: float, high: float) -> list[float]:
    """The powers of ten from `low` to `high` inclusive, for a log axis: 1, 10, 100, 1000. Always at least one
    decade, so that a board whose rows all sit at one pace still has an axis."""
    first = int(math.floor(math.log10(low)))
    last = max(int(math.ceil(math.log10(high))), first + 1)
    return [10.0**power for power in range(first, last + 1)]


def pace_chart(rows: list[dict]) -> dict | None:
    """The board's one chart: every row placed by its usual pace (across) against its recent pace (up), both in stars
    a day on log scales, so that a row's score, recent pace ÷ usual pace, is how far above the diagonal of its own pace
    it sits. The diagonals of 3×, 10×, 100×, and 1,000× are drawn as guides.

    The site computes no score: the usual pace is the divisor the file gives (`divided_by`, the baseline or the floor
    of 1 star a day), and the recent pace is the file's score times that divisor, which is the file's recent stars over
    its recent days. Positions are percentages of the plot, so the page can stretch the chart to any shape and keep
    its dots round and its labels at their own size. None for a board with no rows, or rows without the numbers.
    """
    if not rows or "score" not in rows[0]:
        return None
    points = [(row["divided_by"], row["score"] * row["divided_by"]) for row in rows]
    xs, ys = _ticks(min(x for x, _ in points), max(x for x, _ in points)), _ticks(1, max(y for _, y in points))
    x0, x1, y0, y1 = math.log10(xs[0]), math.log10(xs[-1]), math.log10(ys[0]), math.log10(ys[-1])
    # A little room inside the frame, so that the dots at the floor and at the top clear the axes.
    x0, x1 = x0 - (x1 - x0) * 0.03, x1 + (x1 - x0) * 0.01

    def left(x: float) -> float:
        return round((math.log10(x) - x0) / (x1 - x0) * 100, 2)

    def top(y: float) -> float:
        return round((y1 - math.log10(y)) / (y1 - y0) * 100, 2)

    dots = [{"left": left(x), "top": top(y), "rank": row["rank"]} for row, (x, y) in zip(rows, points, strict=True)]
    # The labelled dots, by rank. Dots that sit close together share one label, "1, 2", placed at the first of them,
    # so that no label lands on another or drifts from its dot.
    labels: list[dict] = []
    for dot in dots[:LABELLED]:
        near = next(
            (label for label in labels if abs(label["left"] - dot["left"]) < 6 and abs(label["top"] - dot["top"]) < 6),
            None,
        )
        if near:
            near["text"] += f", {dot['rank']}"
        else:
            labels.append({"text": str(dot["rank"]), "left": dot["left"], "top": dot["top"]})
    guides = []
    for multiple in (1, 3, 10, 100, 1000):
        # The diagonal y = multiple · x, clipped to the plot: in log space, a line of slope 1.
        shift = math.log10(multiple)
        start, end = max(x0, y0 - shift), min(x1, y1 - shift)
        if start >= end:
            continue
        # On a phone, "own pace" is set beside its line, at a point 60% of the way along it, and not at the line's
        # end: there the 3× line leaves the chart too, and the two labels printed on top of each other (#34). The
        # area below and to the right of the line is the board's emptiest, since a row is there only when its recent
        # pace is under its usual one.
        beside = start + (end - start) * 0.6
        guides.append(
            {
                "multiple": multiple,
                "x1": left(10**start),
                "y1": top(10 ** (start + shift)),
                "x2": left(10**end),
                "y2": top(10 ** (end + shift)),
                "bx": left(10**beside),
                "by": top(10 ** (beside + shift)),
                "label": "own pace" if multiple == 1 else f"{multiple:,}×",
            }
        )
    return {
        # Every dot as one path, in the board's order, the top rows in their own: a zero-length stroke with a round
        # cap is a dot, placed to a tenth of a percent. One path costs about 12 bytes a row, where an element for each
        # dot cost several times that. baseline.js reads the dots back from these, in order.
        "lead": "".join(f"M{round(dot['left'], 1):g} {round(dot['top'], 1):g}h0" for dot in dots[:TOP]),
        "rest": "".join(f"M{round(dot['left'], 1):g} {round(dot['top'], 1):g}h0" for dot in dots[TOP:]),
        "count": len(dots),
        "labels": labels,
        "guides": guides,
        "xticks": [{"at": left(x), "text": f"{x:,.0f}"} for x in xs],
        "yticks": [{"at": top(y), "text": f"{y:,.0f}"} for y in ys],
        "floor": sum(1 for x, _ in points if x == 1),
    }
