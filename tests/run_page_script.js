// Runs the script that a built page carries, under Node, for tests/test_old_board.py. Node is the GitHub runner
// image's own, as it is for deploy.yml's deploy job, and this file needs no package.
//
// Standard input is JSON: the script's text, as the built page holds it, and a list of runs. Each run gives the
// clock, in milliseconds since 1970 in UTC, and the elements of the page that the script may look up: each by its
// id, with its attributes and its text, and the root element's attributes. Each run has a context of its own,
// which holds a stand-in for the document and a Date whose clock is the run's, and nothing else: no fetch, no
// timers, no require. Standard output is JSON: for each run, the elements' attributes and text once the script
// has run, the error it threw if it threw one, and every property of the document or of an element that it read
// or wrote, in order, so that a test can check it touched nothing else.

"use strict";

const vm = require("node:vm");

function stand_in(name, attributes, text, operations) {
  const state = { attributes: { ...attributes }, text };
  const methods = {
    getAttribute(key) {
      operations.push(`${name}.getAttribute(${key})`);
      return Object.hasOwn(state.attributes, key) ? state.attributes[key] : null;
    },
    setAttribute(key, value) {
      operations.push(`${name}.setAttribute(${key})`);
      state.attributes[key] = String(value);
    },
    removeAttribute(key) {
      operations.push(`${name}.removeAttribute(${key})`);
      delete state.attributes[key];
    },
  };
  const proxy = new Proxy(
    {},
    {
      get(_, key) {
        if (Object.hasOwn(methods, key)) return methods[key];
        operations.push(`${name}.${String(key)}`);
        return key === "textContent" ? state.text : undefined;
      },
      set(_, key, value) {
        operations.push(`${name}.${String(key)}=`);
        if (key === "textContent") state.text = String(value);
        return true;
      },
    },
  );
  return { proxy, state };
}

function run(script, { now, elements, root }) {
  const operations = [];
  const found = Object.fromEntries(
    Object.entries(elements).map(([id, element]) => [id, stand_in(id, element.attributes, element.text, operations)]),
  );
  const html = stand_in("root", root.attributes, "", operations);
  const document = new Proxy(
    {},
    {
      get(_, key) {
        if (key === "getElementById") {
          return (id) => {
            operations.push(`document.getElementById(${id})`);
            return Object.hasOwn(found, id) ? found[id].proxy : null;
          };
        }
        operations.push(`document.${String(key)}`);
        return key === "documentElement" ? html.proxy : undefined;
      },
      set(_, key) {
        operations.push(`document.${String(key)}=`);
        return true;
      },
    },
  );
  // The clock passed in: Date.now() gives it, and so does a Date made with no argument.
  class Clock extends Date {
    constructor(...moment) {
      super(...(moment.length ? moment : [now]));
    }
    static now() {
      return now;
    }
  }
  let error = null;
  try {
    vm.runInContext(script, vm.createContext({ document, Date: Clock }), { timeout: 1000 });
  } catch (thrown) {
    error = String(thrown);
  }
  return {
    elements: Object.fromEntries(Object.entries(found).map(([id, { state }]) => [id, state])),
    root: html.state.attributes,
    operations,
    error,
  };
}

const chunks = [];
process.stdin.on("data", (chunk) => chunks.push(chunk));
process.stdin.on("end", () => {
  const { script, runs } = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  process.stdout.write(JSON.stringify(runs.map((each) => run(script, each))));
});
