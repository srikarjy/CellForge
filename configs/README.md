# Experiment configuration

Future typed configurations will declare dataset and version, task, split, model or baseline, seeds, preprocessing, metrics, and artifact paths. Preserve model/inference options, control policies, and evaluation settings needed to interpret a comparison.

Track intentional configuration files and human-readable methodological choices in Git. A run should snapshot its resolved settings so later changes to defaults cannot alter its meaning. Secrets belong outside committed configuration.

Stage 1 contains no configuration parser, finalized schema, fake production configuration, or executable example. Configuration syntax will follow real dataset and model requirements.
