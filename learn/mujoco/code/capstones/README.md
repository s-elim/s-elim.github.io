# Capstones

The seven capstones (A to G) and the final capstone are specified in Lesson 22.1
(`lessons/22.1-capstones.md`, on the site at `#/lesson/22.1`): objective, what each builds on,
acceptance criteria, common failures and extensions, with the rubric and reporting standard they share.

They are specifications. The course provides no reference solutions for them; it provides the tools
(`mjcourse.envs`, `mjcourse.control`, `mjcourse.experiment`, `mjcourse.stats`) and the automatic part of
the acceptance check:

    python -m mjcourse.capstone module:Class --kwargs '{"action_mode": "ee_delta"}' --object BODY

which runs Gymnasium's checker and the course's environment checks and prints the model fingerprint.
Put each capstone in its own folder here (for example `a_drawer/`) with its protocol, code, run records
and report.
