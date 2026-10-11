"""
rehearsal_timer.py
------------------
Stopwatch for the team rehearsal. Press Enter to start each segment and
Enter again when it ends. Prints a Markdown table for REHEARSAL_LOG.md.

Usage:  python rehearsal_timer.py
"""

import time

SEGMENTS = [
    ("Overview", "team"),
    ("Detection", "Tarun / Vaibhav"),
    ("Mapping and migration", "Uday"),
    ("Risk and recommendation", "Yatharth"),
    ("Live Shor's demo", "Yatharth"),
    ("Conclusion", "team"),
]


def fmt(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def main() -> None:
    slot = input("Slot length in minutes (blank to skip): ").strip()
    rows, total = [], 0.0
    for name, speaker in SEGMENTS:
        input(f"\n[{name} - {speaker}] Press Enter to START...")
        t0 = time.perf_counter()
        input("   running... press Enter to STOP")
        elapsed = time.perf_counter() - t0
        total += elapsed
        rows.append((name, speaker, elapsed))
        print(f"   {fmt(elapsed)}   (total so far {fmt(total)})")

    print("\n| Segment | Speaker | Time |\n|---|---|---|")
    for name, speaker, elapsed in rows:
        print(f"| {name} | {speaker} | {fmt(elapsed)} |")
    print(f"| **Total** | | **{fmt(total)}** |")
    if slot.isdigit():
        verdict = "yes" if total <= int(slot) * 60 else "no"
        print(f"\nWithin {slot}-minute slot: {verdict}")


if __name__ == "__main__":
    main()