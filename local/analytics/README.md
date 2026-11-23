# Analytics examples

The SQL files answer business questions directly from Gold tables. To regenerate
the portfolio chart from the latest readable vacancy-event interval, run from
`local/`:

```bash
.venv/bin/python -m analytics.generate_vacancy_changes_chart
```

The command writes `docs/assets/vacancy-changes-by-occupation.svg`. The chart
groups events by stable CZ-ISCO ID and uses occupation labels from the newer
snapshot. It contains aggregates only, not vacancy-level or contact data.
