// Lesson 3.4: a tour of MuJoCo's JavaScript (WebAssembly) bindings, and their traps.
//
// INPUT   @mujoco/mujoco 3.14.0 from npm; a small model written below
// PROCESS (1) load the module and check its version;
//         (2) call a function with an output array the wrong way and the right way;
//         (3) read contacts (a copy, delete it) and warnings (a live reference, do not);
//         (4) read a boolean model field directly and through the named accessor;
//         (5) store a view of qpos, grow the WebAssembly heap, and look at the view again;
//         (6) free everything
// OUTPUT  printed results for each step
//
// Run:  npm install && node bindings_tour.mjs

import loadMujoco from "@mujoco/mujoco";

const XML = `
<mujoco>
  <compiler angle="radian"/>
  <worldbody>
    <geom name="floor" type="plane" size="1 1 .1"/>
    <body name="arm" pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0" range="-1 1"/>
      <geom type="capsule" fromto="0 0 0 .5 0 0" size=".02"/>
      <site name="tip" pos=".5 0 0"/>
    </body>
    <body name="box" pos="0.5 0.3 0.2"><freejoint/><geom type="box" size=".05 .05 .05"/></body>
  </worldbody>
</mujoco>`;

const mj = await loadMujoco();
console.log("1. version:", mj.mj_versionString());

const model = mj.MjModel.from_xml_string(XML);
const data = new mj.MjData(model);
mj.mj_forward(model, data);

// 2. Output arrays. A plain typed array is copied in and the result is thrown away.
const site = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE.value, "tip");
const plain = new Float64Array(3 * model.nv);
mj.mj_jacSite(model, data, plain, null, site);
const buf = new mj.DoubleBuffer(3 * model.nv);          // size in numbers; read with GetView()
mj.mj_jacSite(model, data, buf, null, site);
// The tip moves along -z when the hinge (axis +y) turns, so row z (the third row) is the informative one.
const rowZ = (arr) => Array.from(arr.slice(2 * model.nv, 3 * model.nv)).map((v) => v.toFixed(3)).join(" ");
console.log("2. Jacobian row z, plain Float64Array:", rowZ(plain));
console.log("   Jacobian row z, DoubleBuffer:      ", rowZ(buf.GetView()));

// 3. Contacts are returned as a copy: read, then delete. Warnings are a live reference: never delete.
for (let i = 0; i < 300; i++) mj.mj_step(model, data);
const contacts = data.contact;                           // copy of the contact vector
const first = contacts.get(0);
console.log(`3. ncon = ${data.ncon}; contact 0 between geoms ${first.geom1} and ${first.geom2}, dist ${(1000 * first.dist).toFixed(3)} mm`);
first.delete();
contacts.delete();
const warnings = data.warning;                           // reference into mjData: do NOT call warnings.delete()
const badqacc = warnings.get(mj.mjtWarning.mjWARN_BADQACC.value);
console.log("   bad-acceleration warnings so far:", badqacc.number);
badqacc.delete();                                        // the element is a copy and may be deleted

// 4. Boolean model fields: the array getter throws in 3.14.0, the named accessor works.
try {
  console.log("4. model.jnt_limited:", model.jnt_limited);
} catch (err) {
  console.log("4. model.jnt_limited throws:", String(err.message).slice(0, 60));
}
const joint = model.jnt("hinge");
console.log("   model.jnt('hinge').limited =", joint.limited, "range =", Array.from(joint.range));
joint.delete();

// 5. Views over WebAssembly memory go dead when the heap grows.
const stored = data.qpos;
const big = [];
let xml = "<mujoco><worldbody>";
for (let i = 0; i < 200; i++) xml += `<body pos="${i} 0 0"><freejoint/><geom size=".1"/></body>`;
xml += "</worldbody></mujoco>";
const before = stored.length;
const m2 = mj.MjModel.from_xml_string(xml);
const d2 = new mj.MjData(m2);                            // a large arena: the heap grows
big.push(m2, d2);
console.log(`5. stored view length before: ${before}, after the heap grew: ${stored.length}; fresh view length: ${data.qpos.length}`);

// 6. Free what we created: nothing here is garbage collected.
for (const obj of [buf, d2, m2, data, model]) obj.delete();
console.log("6. freed");
