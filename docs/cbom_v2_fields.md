# CBOM v2 fields (draft)

Values are filled from outputs/risk_scores.json once the score engine runs. null means not yet available.

```json
{
  "component": "RSA (textbook, no padding)",
  "project": "image",
  "layer": "L1",
  "file_line": null,
  "risk_percent": null,
  "band": null,
  "quantum_risk_percent": null,
  "classical_weakness_percent": null,
  "recommendation": "ML-KEM-768 + AES-256-GCM",
  "post_migration_risk_percent": null,
  "scenario_range_z5_z10_z20": [null, null, null],
  "scanner_version": "v0.4.0",
  "pinned_commit": null
}
```

Fields required by the plan: risk percent, band, layer, recommendation, post-migration risk.
The other fields are suggestions to agree with Yatharth and Tarun.