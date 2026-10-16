# Third-party material

## RoboDojo task recipes

`tasks/RoboDojo/recipe/` contains 42 Markdown task recipes from
[RoboProbe/RoboProbe](https://github.com/RoboProbe/RoboProbe), commit
`52300752080325086095854e01977a8cf281b684`, path
`policy/RoboDojo_Agent_L3_Inspect/recipes`.

Recipe contents and the upstream Apache-2.0 [license](tasks/RoboDojo/recipe/LICENSE)
are preserved verbatim. [The manifest](tasks/RoboDojo/recipe/manifest.json) records
the upstream repository, revision and file checksums. These recipes are supplied
task knowledge, not skills learned by EmbodiedEvo.

## External dependencies

RoboDojo, XPolicyLab, Isaac Sim, Isaac Lab, CuRobo, assets, agent CLI binaries and
model services are external dependencies. Their source, assets and binaries are
not bundled here. Use their upstream installation procedures and terms. Runtime
provisioning records local revisions and any pre-existing patches.

The recipe license does not assign a license to the rest of this project.

## The Robot Studio SO101 model

The optional MuJoCo backend downloads `robotstudio_so101` through the pinned
[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) Python package.
The model derives from The Robot Studio SO-ARM100/SO-101 description and is licensed
under Apache-2.0. Model XML and meshes remain in the ignored runtime cache; they are not
redistributed by this repository. The pinned package exposes its model revision (`oid`)
during provisioning for experiment records.
