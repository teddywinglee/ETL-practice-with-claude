Run the ETL pipeline (extract + transform + load only — no generation) on existing data in `data/posts.jsonl`.

The user may pass `--theme "some theme"`. If not provided, defaults to "Social Media".

Run this command from the `etl-pipeline` directory:

```
cd F:/project/ETL-claude && uv run main.py $ARGUMENTS
```

Replace `$ARGUMENTS` with whatever the user passed. After it completes, let the user know the report is at `output/report.html`.
