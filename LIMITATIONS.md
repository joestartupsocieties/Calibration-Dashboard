# Limitations

The current normalized dataset covers **35 detected zone profile records** and **35 normalized indicator records** based on the source digest. The source digest says the normalized CSV was created from detected zone profile rows and 2026 colonization metrics where reliable normalization was possible.

Exact row-level verification should use the original workbook. The MVP preserves uncertainty and data-quality flags rather than pretending the data is complete.

- Legal fields are placeholders pending D4 legal review.
- Fiscal exposure fields are placeholders pending fiscal authority validation.
- Recommendation outputs are provisional triage signals, not final legal or fiscal determinations.
- Missing, contradictory, or placeholder fields lower confidence and appear in the explanation trail.
- Generated outputs should be regenerated from `/data` and `/config` rather than treated as source truth.

