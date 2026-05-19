from pathlib import Path

import pandas as pd

from dataprep.pipelines.fees import pipeline as fees_pipeline


class FakeQueue:
    def __init__(self) -> None:
        self.items: list[object] = []

    def put(self, value: object) -> None:
        self.items.append(value)

    def get(self) -> object:
        if not self.items:
            raise RuntimeError("Queue is empty")
        return self.items.pop(0)


class FakeProcess:
    def __init__(self, target, args) -> None:
        self.target = target
        self.args = args
        self.pid = 1
        self.exitcode: int | None = None

    def start(self) -> None:
        self.target(*self.args)
        self.exitcode = 0

    def join(self) -> None:
        return


class FakeContext:
    def Queue(self) -> FakeQueue:  # noqa: N802
        return FakeQueue()

    def Process(self, target, args):  # noqa: N802
        return FakeProcess(target, args)


def test_run_retries_failed_records_and_skips_success(tmp_path: Path, monkeypatch) -> None:
    input_csv = tmp_path / "geocoded_records.csv"
    output_csv = tmp_path / "scraped_fees.csv"

    pd.DataFrame(
        {
            "record_number": ["R1", "R2", "R3"],
            "address": ["a", "b", "c"],
        }
    ).to_csv(input_csv, index=False)

    pd.DataFrame(
        {
            "record_number": ["R1", "R2"],
            "paid": [1.0, 0.0],
            "outstanding": [0.0, 2.0],
            "scrape_status": ["success", "failed"],
        }
    ).to_csv(output_csv, index=False)

    def fake_worker_loop(worker_id, headless, record_queue, result_queue):
        while True:
            record_number = record_queue.get()
            if record_number is None:
                break
            result_queue.put(
                (
                    {
                        "record_number": record_number,
                        "paid": 10.0,
                        "outstanding": 0.0,
                        "scrape_status": "success",
                    },
                    True,
                )
            )

    monkeypatch.setattr(fees_pipeline.mp, "get_context", lambda _: FakeContext())
    monkeypatch.setattr(fees_pipeline, "worker_loop", fake_worker_loop)

    fees_pipeline.run(input_csv=input_csv, output_csv=output_csv, workers=1)

    result_df = pd.read_csv(output_csv)
    assert list(result_df["record_number"]) == ["R1", "R2", "R3"]
    assert result_df.loc[result_df["record_number"] == "R1", "paid"].item() == 1.0
    assert result_df.loc[result_df["record_number"] == "R2", "paid"].item() == 10.0
