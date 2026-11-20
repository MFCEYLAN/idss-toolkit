"""Run after installation: python examples/quickstart.py"""
from pathlib import Path
from idss import IDSS


def main():
    csv_path = Path(__file__).with_name("models.csv")
    result = IDSS(csv_path)
    print(result)
    print("Best candidates:", result.best)
    custom = IDSS(csv_path, weights={"quality": 0.5, "latency": 0.3, "size": 0.2})
    print(custom)
    standard = IDSS(csv_path, profile="quality_priority")
    print(standard)
    print("Available profiles:", IDSS.profiles())
    result.save("idss_results")
    print("Open idss_results/report.html")


if __name__ == "__main__":
    main()
