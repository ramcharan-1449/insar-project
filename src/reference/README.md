# Reference decision checkpoint

Reference-point selection and reference QC are a separate, mandatory scientific checkpoint. They are deliberately not part of HyP3 job submission.

The decision record is `config/insar_reference_config.json`. Review and approve it for every production pair before spatial extraction. Its independently runnable structural check is:

```powershell
python src/reference/validate_reference_decision.py
```

The existing development scripts in `src/spatial/create_reference_qc.py` and `src/spatial/apply_insar_reference.py` remain legacy pair-specific tools until they are parameterized for the production product inventory. They must not be used as a substitute for an approved production reference decision.
