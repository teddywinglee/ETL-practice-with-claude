Run the full ETL pipeline (generate + extract + transform + load) using the provided arguments.

The user may pass arguments like `--count 20 --theme "electric vehicles" --languages "English,Spanish"`. If no arguments are given, use the defaults (count=10, theme="general social media").

Run this command from the `etl-pipeline` directory:

```
cd F:/project/ETL-claude && uv run run_all.py $ARGUMENTS
```

Replace `$ARGUMENTS` with whatever the user passed. After it completes, let the user know the report is at `output/report.html`.
