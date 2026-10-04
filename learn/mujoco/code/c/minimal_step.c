// minimal_step.c: the smallest useful MuJoCo program in C (Lesson 20.4).
// Loads a model, resets it to its first keyframe, steps it 1000 times and prints the state.
//
// Build against the headers and library that ship with the Python package:
//   MJ=$(python -c "import mujoco, os; print(os.path.dirname(mujoco.__file__))")
//   cc minimal_step.c -I"$MJ/include" -L"$MJ" -l:libmujoco.so.3.14.0 -Wl,-rpath,"$MJ" -o minimal_step
//   ./minimal_step ../src/mjcourse/models/cartpole.xml

#include <stdio.h>

#include <mujoco/mujoco.h>

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s model.xml\n", argv[0]);
    return 1;
  }

  char error[1000] = "";
  mjModel* m = mj_loadXML(argv[1], NULL, error, sizeof(error));
  if (!m) {
    fprintf(stderr, "could not load %s: %s\n", argv[1], error);
    return 1;
  }
  mjData* d = mj_makeData(m);
  if (m->nkey > 0) {
    mj_resetDataKeyframe(m, d, 0);
  }

  for (int k = 0; k < 1000; k++) {
    mj_step(m, d);
  }

  printf("MuJoCo %s: after 1000 steps t = %.3f s, qpos =", mj_versionString(), d->time);
  for (int i = 0; i < m->nq; i++) {
    printf(" %.17g", d->qpos[i]);
  }
  printf("\n");

  mj_deleteData(d);
  mj_deleteModel(m);
  return 0;
}
