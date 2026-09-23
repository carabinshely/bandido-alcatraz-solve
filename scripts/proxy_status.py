from dataclasses import asdict
import json
from pathlib import Path

from bandido_alcatraz.proxy_data import load_proxy, proxy_status


ROOT = Path(__file__).parents[1]


def main() -> None:
    data = load_proxy(ROOT / "data" / "proxy-bandido-covid-v0.json")
    print(json.dumps(asdict(proxy_status(data)), sort_keys=True))


if __name__ == "__main__":
    main()
